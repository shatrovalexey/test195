from datetime import datetime
from typing import Optional, Dict, Any
import json

class JSONSerializable:
    """Базовый класс для JSON-сериализации"""
    
    def to_json(self) -> str:
        """Преобразование объекта в JSON строку"""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование объекта в словарь"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class User(JSONSerializable):
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.full_name = data.get('full_name')
        self.email = data.get('email')
        self.password_hash = data.get('password_hash')
        self.registered_at = data.get('registered_at')
        self.updated_at = data.get('updated_at')
        self.is_admin = data.get('is_admin', False)
        self.is_blocked = data.get('is_blocked', False)
    
    @classmethod
    def create(cls, full_name: str, email: str, password_hash: str) -> Dict[str, Any]:
        return {
            'full_name': full_name,
            'email': email,
            'password_hash': password_hash,
            'is_admin': False,
            'is_blocked': False
        }

class Session(JSONSerializable):
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.ip_address = data.get('ip_address')
        self.user_agent = data.get('user_agent')
        self.created_at = data.get('created_at')
        self.expires_at = data.get('expires_at')
        self.last_activity_at = data.get('last_activity_at')
        self.is_revoked = data.get('is_revoked')

class Resource(JSONSerializable):
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
        self.metadata = data.get('metadata', {})
    
    @classmethod
    def create(cls, resource_id: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        return {
            'id': resource_id,
            'metadata': metadata or {}
        }

class ResourcePermission(JSONSerializable):
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.resource_id = data.get('resource_id')
        self.permission_type = data.get('permission_type')
        self.granted_by = data.get('granted_by')
        self.granted_at = data.get('granted_at')
        self.expires_at = data.get('expires_at')
        self.is_active = data.get('is_active')
