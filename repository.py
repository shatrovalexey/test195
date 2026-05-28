from database import db
from query_loader import query_loader
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json

class UserRepository:
    """Репозиторий для работы с пользователями"""
    
    @staticmethod
    def create(full_name: str, email: str, password_hash: str) -> Optional[Dict[str, Any]]:
        """Создание пользователя"""
        query = query_loader.get_query("users", "create")
        result = db.execute_query(query, (full_name, email, password_hash), fetch_one=True)
        return result
    
    @staticmethod
    def find_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Поиск пользователя по email"""
        query = query_loader.get_query("users", "find_by_email")
        return db.execute_query(query, (email,), fetch_one=True)
    
    @staticmethod
    def find_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Поиск пользователя по ID"""
        query = query_loader.get_query("users", "find_by_id")
        return db.execute_query(query, (user_id,), fetch_one=True)
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """Получение всех пользователей"""
        query = query_loader.get_query("users", "get_all")
        return db.execute_query(query, fetch_all=True)
    
    @staticmethod
    def update(user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновление пользователя"""
        if not updates:
            return UserRepository.find_by_id(user_id)
        
        set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
        query = query_loader.format_query("users", "update", updates=set_clause)
        params = list(updates.values()) + [user_id]
        return db.execute_query(query, tuple(params), fetch_one=True)
    
    @staticmethod
    def delete(user_id: int) -> bool:
        """Удаление пользователя"""
        query = query_loader.get_query("users", "delete")
        result = db.execute_query(query, (user_id,), fetch_one=True)
        return result is not None
    
    @staticmethod
    def check_email_exists(email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Проверка существования email"""
        if exclude_user_id:
            query = query_loader.get_query("users", "check_email_exists")
            result = db.execute_query(query, (email, exclude_user_id), fetch_one=True)
        else:
            query = query_loader.get_query("users", "find_by_email")
            result = db.execute_query(query, (email,), fetch_one=True)
        return result is not None
    
    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Проверка является ли пользователь админом"""
        query = query_loader.get_query("users", "check_admin")
        result = db.execute_query(query, (user_id,), fetch_one=True)
        return result['is_admin'] if result else False

class SessionRepository:
    """Репозиторий для работы с сессиями"""
    
    @staticmethod
    def create(session_id: str, user_id: int, ip_address: str, user_agent: str, expires_at: datetime) -> Dict[str, Any]:
        """Создание сессии"""
        query = query_loader.get_query("sessions", "create")
        return db.execute_query(query, (session_id, user_id, ip_address, user_agent, expires_at), fetch_one=True)
    
    @staticmethod
    def find_by_id(session_id: str) -> Optional[Dict[str, Any]]:
        """Поиск сессии по ID"""
        query = query_loader.get_query("sessions", "find_by_id")
        return db.execute_query(query, (session_id,), fetch_one=True)
    
    @staticmethod
    def update_activity(session_id: str):
        """Обновление активности сессии"""
        query = query_loader.get_query("sessions", "update_activity")
        db.execute_query(query, (session_id,))
    
    @staticmethod
    def revoke(session_id: str):
        """Отзыв сессии"""
        query = query_loader.get_query("sessions", "revoke")
        db.execute_query(query, (session_id,))
    
    @staticmethod
    def revoke_all_user_sessions(user_id: int, exclude_session_id: Optional[str] = None):
        """Отзыв всех сессий пользователя"""
        if exclude_session_id:
            query = query_loader.get_query("sessions", "revoke_all_user")
            db.execute_query(query, (user_id, exclude_session_id))
        else:
            query = query_loader.get_query("sessions", "revoke_all_user_sessions")
            db.execute_query(query, (user_id,))
    
    @staticmethod
    def cleanup_expired():
        """Очистка просроченных сессий"""
        query = query_loader.get_query("sessions", "cleanup_expired")
        return db.execute_query(query)

class ResourceRepository:
    """Репозиторий для работы с ресурсами"""
    
    @staticmethod
    def create(resource_id: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Создание ресурса"""
        query = query_loader.get_query("resources", "create")
        return db.execute_query(query, (resource_id, json.dumps(metadata) if metadata else None), fetch_one=True)
    
    @staticmethod
    def find_by_id(resource_id: str) -> Optional[Dict[str, Any]]:
        """Поиск ресурса по ID"""
        query = query_loader.get_query("resources", "find_by_id")
        return db.execute_query(query, (resource_id,), fetch_one=True)
    
    @staticmethod
    def update(resource_id: str, metadata: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Обновление ресурса"""
        query = query_loader.get_query("resources", "update")
        return db.execute_query(query, (json.dumps(metadata) if metadata else None, resource_id), fetch_one=True)
    
    @staticmethod
    def delete(resource_id: str) -> bool:
        """Удаление ресурса"""
        query = query_loader.get_query("resources", "delete")
        result = db.execute_query(query, (resource_id,), fetch_one=True)
        return result is not None
    
    @staticmethod
    def get_all_admin() -> List[Dict[str, Any]]:
        """Получение всех ресурсов (для админа)"""
        query = query_loader.get_query("resources", "get_all_admin")
        return db.execute_query(query, fetch_all=True)
    
    @staticmethod
    def get_user_resources(user_id: int) -> List[Dict[str, Any]]:
        """Получение ресурсов пользователя"""
        query = query_loader.get_query("resources", "get_user_resources")
        return db.execute_query(query, (user_id,), fetch_all=True)

class PermissionRepository:
    """Репозиторий для работы с правами доступа"""
    
    @staticmethod
    def check_permission(user_id: int, resource_id: str, permission: str) -> bool:
        """Проверка права доступа"""
        query = query_loader.get_query("permissions", "check_permission")
        result = db.execute_query(query, (user_id, resource_id, permission), fetch_one=True)
        return result is not None
    
    @staticmethod
    def grant(user_id: int, resource_id: str, permission_type: str, granted_by: int, expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """Выдача права"""
        query = query_loader.get_query("permissions", "grant")
        return db.execute_query(query, (user_id, resource_id, permission_type, granted_by, expires_at), fetch_one=True)
    
    @staticmethod
    def revoke(resource_id: str, user_id: int, permission_type: str) -> bool:
        """Отзыв права"""
        query = query_loader.get_query("permissions", "revoke")
        result = db.execute_query(query, (resource_id, user_id, permission_type), fetch_one=True)
        return result is not None
    
    @staticmethod
    def get_user_permissions(user_id: int, resource_id: str) -> List[Dict[str, Any]]:
        """Получение прав пользователя на ресурс"""
        query = query_loader.get_query("permissions", "get_user_permissions")
        return db.execute_query(query, (user_id, resource_id), fetch_all=True)