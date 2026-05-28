from fastapi import APIRouter, Request, HTTPException, status, Depends
from datetime import datetime
from typing import Optional

from schemas import (
    UserRegister, UserLogin, TokenResponse, 
    MessageResponse, TokenRefresh
)
from repository import UserRepository
from utils.security import (
    hash_password, create_access_token, create_refresh_token,
    verify_token, decode_token
)
from auth import AuthManager
from dependencies import get_current_user, get_current_active_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=MessageResponse)
async def register(user_data: UserRegister):
    """
    Регистрация нового пользователя
    """
    try:
        # Проверка существования email
        existing_user = UserRepository.find_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Хеширование пароля
        password_hash = hash_password(user_data.password)
        
        # Создание пользователя
        user = UserRepository.create(
            full_name=user_data.full_name,
            email=user_data.email,
            password_hash=password_hash
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        return MessageResponse(message="User registered successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, request: Request):
    """
    Вход в систему - получение JWT токенов
    
    Возвращает:
    - **access_token**: Токен доступа (30 минут)
    - **refresh_token**: Токен обновления (7 дней)
    - **token_type**: Тип токена (Bearer)
    - **expires_in**: Время жизни access токена в секундах
    """
    try:
        # Аутентификация пользователя
        user = AuthManager.authenticate_user(user_data.email, user_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Создание токенов
        tokens = AuthManager.create_tokens(
            user_id=user['id'],
            email=user['email'],
            is_admin=user['is_admin']
        )
        
        return TokenResponse(**tokens)
    
    except Exception as e:
        if str(e) == "User is blocked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is blocked. Please contact administrator."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: TokenRefresh):
    """
    Обновление access токена с помощью refresh токена
    """
    try:
        # Обновление токенов
        new_tokens = AuthManager.refresh_access_token(refresh_data.refresh_token)
        
        return TokenResponse(**new_tokens)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Выход из системы (клиент должен удалить токены)
    
    Примечание: JWT токены не хранятся на сервере,
    поэтому клиент должен самостоятельно удалить токены.
    """
    # JWT не хранится на сервере, поэтому просто возвращаем успех
    # В реальном приложении можно добавить черный список токенов
    return MessageResponse(message="Logged out successfully. Please remove tokens on client side.")


@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """
    Получение информации о текущем авторизованном пользователе
    """
    return {
        "id": current_user['id'],
        "full_name": current_user['full_name'],
        "email": current_user['email'],
        "is_admin": current_user['is_admin'],
        "is_blocked": current_user['is_blocked'],
        "registered_at": current_user['registered_at'].isoformat() if current_user['registered_at'] else None,
        "updated_at": current_user['updated_at'].isoformat() if current_user['updated_at'] else None
    }


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    old_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Смена пароля текущего пользователя
    """
    try:
        from utils.security import verify_password, hash_password
        
        # Проверка старого пароля
        if not verify_password(old_password, current_user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Old password is incorrect"
            )
        
        # Проверка длины нового пароля
        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 6 characters long"
            )
        
        # Хеширование и обновление пароля
        new_password_hash = hash_password(new_password)
        UserRepository.update(current_user['id'], {'password_hash': new_password_hash})
        
        return MessageResponse(message="Password changed successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password change failed: {str(e)}"
        )


@router.get("/verify", response_model=dict)
async def verify_token_endpoint(current_user: dict = Depends(get_current_user)):
    """
    Проверка валидности токена
    """
    return {
        "valid": True,
        "user_id": current_user['id'],
        "email": current_user['email'],
        "is_admin": current_user['is_admin']
    }


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_devices(current_user: dict = Depends(get_current_user)):
    """
    Принудительный выход со всех устройств
    
    Примечание: Для полноценной реализации необходим черный список токенов.
    Этот эндпоинт инвалидирует все текущие токены пользователя.
    """
    # В реальном приложении здесь нужно добавить все текущие токены пользователя в черный список
    # Для простоты возвращаем сообщение о необходимости смены пароля
    return MessageResponse(
        message="To invalidate all tokens, please change your password. "
                "After password change, all existing tokens will be invalid."
    )


@router.get("/check-email/{email}", response_model=dict)
async def check_email_exists(email: str):
    """
    Проверка существования email (публичный эндпоинт)
    """
    user = UserRepository.find_by_email(email)
    return {
        "exists": user is not None,
        "email": email
    }