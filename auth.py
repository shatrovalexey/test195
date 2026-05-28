from datetime import datetime, timedelta
from typing import Optional
from repository import UserRepository
from utils.security import verify_password, create_access_token, create_refresh_token, verify_token

class AuthManager:
    """Менеджер авторизации с JWT токенами"""
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[dict]:
        """Аутентификация пользователя"""
        user = UserRepository.find_by_email(email)
        
        if not user:
            return None
        
        if user['is_blocked']:
            raise Exception("User is blocked")
        
        if verify_password(password, user['password_hash']):
            return user
        return None
    
    @staticmethod
    def create_tokens(user_id: int, email: str, is_admin: bool) -> dict:
        """Создание access и refresh токенов"""
        # Данные для токена
        token_data = {
            "sub": str(user_id),
            "email": email,
            "is_admin": is_admin
        }
        
        # Создание токенов
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Получаем время жизни access токена
        from utils.security import ACCESS_TOKEN_EXPIRE_MINUTES
        expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in
        }
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """Обновление access токена по refresh токену"""
        try:
            # Верификация refresh токена
            payload = verify_token(refresh_token, "refresh")
            
            # Создание новых токенов
            user_id = int(payload.get("sub"))
            email = payload.get("email")
            is_admin = payload.get("is_admin", False)
            
            # Проверка существования пользователя
            user = UserRepository.find_by_id(user_id)
            if not user:
                raise Exception("User not found")
            
            if user['is_blocked']:
                raise Exception("User is blocked")
            
            # Создание новых токенов
            return AuthManager.create_tokens(user_id, email, is_admin)
            
        except Exception as e:
            raise Exception(f"Token refresh failed: {str(e)}")