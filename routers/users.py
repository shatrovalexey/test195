from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from schemas import UserResponse, UserUpdate, UserAdminUpdate, MessageResponse
from database import db
from utils.security import hash_password
from dependencies import get_current_user, get_current_active_user, get_current_admin_user
from auth import AuthManager

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: dict = Depends(get_current_active_user)):
    """Получение своего профиля"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, full_name, email, registered_at, updated_at, is_admin, is_blocked
                FROM users WHERE id = %s
            """, (current_user['user_id'],))
            user = cur.fetchone()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return user

@router.put("/me", response_model=MessageResponse)
async def update_my_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Обновление своего профиля"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Формируем динамический UPDATE
            updates = []
            params = []
            
            if update_data.full_name:
                updates.append("full_name = %s")
                params.append(update_data.full_name)
            
            if update_data.email:
                # Проверяем, не занят ли email другим пользователем
                cur.execute("SELECT id FROM users WHERE email = %s AND id != %s", 
                           (update_data.email, current_user['user_id']))
                if cur.fetchone():
                    raise HTTPException(400, "Email already used by another user")
                updates.append("email = %s")
                params.append(update_data.email)
            
            if update_data.password:
                updates.append("password_hash = %s")
                params.append(hash_password(update_data.password))
            
            if updates:
                params.append(current_user['user_id'])
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
                cur.execute(query, params)
            
            return {"message": "Profile updated successfully"}

@router.get("/", response_model=List[UserResponse])
async def get_all_users(admin_user: dict = Depends(get_current_admin_user)):
    """Получение всех пользователей (только админ)"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, full_name, email, registered_at, updated_at, is_admin, is_blocked
                FROM users ORDER BY id
            """)
            return cur.fetchall()

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: dict = Depends(get_current_active_user),
    admin_user: dict = Depends(get_current_admin_user)  # Требуем админа
):
    """Получение пользователя по ID (только админ)"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, full_name, email, registered_at, updated_at, is_admin, is_blocked
                FROM users WHERE id = %s
            """, (user_id,))
            user = cur.fetchone()
            
            if not user:
                raise HTTPException(404, "User not found")
            
            return user

@router.put("/{user_id}", response_model=MessageResponse)
async def update_user_by_admin(
    user_id: int,
    update_data: UserAdminUpdate,
    admin_user: dict = Depends(get_current_admin_user)
):
    """Обновление пользователя (только админ)"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Проверяем существование пользователя
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                raise HTTPException(404, "User not found")
            
            # Формируем динамический UPDATE
            updates = []
            params = []
            
            if update_data.full_name is not None:
                updates.append("full_name = %s")
                params.append(update_data.full_name)
            
            if update_data.email is not None:
                # Проверяем уникальность email
                cur.execute("SELECT id FROM users WHERE email = %s AND id != %s", 
                           (update_data.email, user_id))
                if cur.fetchone():
                    raise HTTPException(400, "Email already used by another user")
                updates.append("email = %s")
                params.append(update_data.email)
            
            if update_data.password is not None:
                updates.append("password_hash = %s")
                params.append(hash_password(update_data.password))
            
            if update_data.is_admin is not None:
                updates.append("is_admin = %s")
                params.append(update_data.is_admin)
            
            if update_data.is_blocked is not None:
                updates.append("is_blocked = %s")
                params.append(update_data.is_blocked)
            
            if updates:
                params.append(user_id)
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
                cur.execute(query, params)
                
                # Если пользователь заблокирован - завершаем все его сессии
                if update_data.is_blocked:
                    AuthManager.revoke_all_user_sessions(user_id)
            
            return {"message": "User updated successfully"}

@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(user_id: int, admin_user: dict = Depends(get_current_admin_user)):
    """Удаление пользователя (только админ)"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Нельзя удалить самого себя
            if user_id == admin_user['user_id']:
                raise HTTPException(400, "Cannot delete yourself")
            
            cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
            if not cur.fetchone():
                raise HTTPException(404, "User not found")
            
            return {"message": "User deleted successfully"}
