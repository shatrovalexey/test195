from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from schemas import ResourceCreate, ResourceResponse, PermissionGrant, MessageResponse
from database import db
from utils.security import generate_resource_id
from dependencies import get_current_active_user, get_current_admin_user

router = APIRouter(prefix="/resources", tags=["resources"])

def check_resource_access(user_id: int, resource_id: str, permission: str = "read") -> bool:
    """Проверка доступа пользователя к ресурсу"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Администратор имеет доступ ко всем ресурсам
            cur.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if user and user['is_admin']:
                return True
            
            # Проверка прав
            cur.execute("""
                SELECT 1 FROM resource_permissions
                WHERE user_id = %s 
                AND resource_id = %s 
                AND permission_type IN (%s, 'manage')
                AND is_active = TRUE
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """, (user_id, resource_id, permission))
            
            return cur.fetchone() is not None

@router.post("/", response_model=ResourceResponse)
async def create_resource(
    resource_data: ResourceCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Создание нового ресурса"""
    resource_id = generate_resource_id()
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO resources (id, metadata)
                VALUES (%s, %s)
                RETURNING id, created_at, updated_at, metadata
            """, (resource_id, resource_data.metadata))
            
            resource = cur.fetchone()
            
            # Создаём права на ресурс для создателя
            cur.execute("""
                INSERT INTO resource_permissions (user_id, resource_id, permission_type, granted_by)
                VALUES (%s, %s, 'manage', %s)
            """, (current_user['user_id'], resource_id, current_user['user_id']))
            
            return resource

@router.get("/", response_model=List[ResourceResponse])
async def get_all_resources(current_user: dict = Depends(get_current_active_user)):
    """Получение всех доступных ресурсов"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            if current_user['is_admin']:
                # Админ видит все ресурсы
                cur.execute("""
                    SELECT id, created_at, updated_at, metadata
                    FROM resources
                    ORDER BY created_at DESC
                """)
                return cur.fetchall()
            else:
                # Обычный пользователь видит только ресурсы с правами
                cur.execute("""
                    SELECT DISTINCT r.id, r.created_at, r.updated_at, r.metadata
                    FROM resources r
                    JOIN resource_permissions rp ON r.id = rp.resource_id
                    WHERE rp.user_id = %s 
                    AND rp.is_active = TRUE
                    AND (rp.expires_at IS NULL OR rp.expires_at > CURRENT_TIMESTAMP)
                    ORDER BY r.created_at DESC
                """, (current_user['user_id'],))
                return cur.fetchall()

@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Получение ресурса по ID (проверка прав доступа)"""
    if not check_resource_access(current_user['user_id'], resource_id, "read"):
        raise HTTPException(403, "Access denied to this resource")
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, created_at, updated_at, metadata
                FROM resources WHERE id = %s
            """, (resource_id,))
            resource = cur.fetchone()
            
            if not resource:
                raise HTTPException(404, "Resource not found")
            
            return resource

@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: str,
    resource_data: ResourceCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Обновление ресурса (требуются права write или manage)"""
    if not check_resource_access(current_user['user_id'], resource_id, "write"):
        raise HTTPException(403, "Access denied to modify this resource")
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE resources 
                SET metadata = %s
                WHERE id = %s
                RETURNING id, created_at, updated_at, metadata
            """, (resource_data.metadata, resource_id))
            
            resource = cur.fetchone()
            if not resource:
                raise HTTPException(404, "Resource not found")
            
            return resource

@router.delete("/{resource_id}", response_model=MessageResponse)
async def delete_resource(
    resource_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Удаление ресурса (требуются права manage или админ)"""
    # Для удаления требуются права manage или админ
    if not current_user['is_admin'] and not check_resource_access(current_user['user_id'], resource_id, "manage"):
        raise HTTPException(403, "Access denied to delete this resource")
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resources WHERE id = %s RETURNING id", (resource_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Resource not found")
            
            return {"message": "Resource deleted successfully"}

@router.post("/{resource_id}/permissions", response_model=MessageResponse)
async def grant_permission(
    resource_id: str,
    permission: PermissionGrant,
    current_user: dict = Depends(get_current_active_user)
):
    """Выдача прав на ресурс другому пользователю (требуются права manage)"""
    if not check_resource_access(current_user['user_id'], resource_id, "manage"):
        raise HTTPException(403, "Access denied to manage permissions for this resource")
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Проверяем существование пользователя
            cur.execute("SELECT id FROM users WHERE id = %s", (permission.user_id,))
            if not cur.fetchone():
                raise HTTPException(404, "User not found")
            
            # Проверяем существование ресурса
            cur.execute("SELECT id FROM resources WHERE id = %s", (resource_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Resource not found")
            
            # Выдаём или обновляем права
            cur.execute("""
                INSERT INTO resource_permissions (user_id, resource_id, permission_type, granted_by, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, resource_id, permission_type) 
                DO UPDATE SET 
                    granted_by = EXCLUDED.granted_by,
                    granted_at = CURRENT_TIMESTAMP,
                    expires_at = EXCLUDED.expires_at,
                    is_active = TRUE
            """, (permission.user_id, resource_id, permission.permission_type, 
                  current_user['user_id'], permission.expires_at))
            
            return {"message": f"Permission '{permission.permission_type}' granted successfully"}

@router.delete("/{resource_id}/permissions/{user_id}/{permission_type}", response_model=MessageResponse)
async def revoke_permission(
    resource_id: str,
    user_id: int,
    permission_type: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Отзыв прав на ресурс (требуются права manage)"""
    if not check_resource_access(current_user['user_id'], resource_id, "manage"):
        raise HTTPException(403, "Access denied to manage permissions for this resource")
    
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE resource_permissions
                SET is_active = FALSE
                WHERE resource_id = %s AND user_id = %s AND permission_type = %s
            """, (resource_id, user_id, permission_type))
            
            return {"message": "Permission revoked successfully"}
