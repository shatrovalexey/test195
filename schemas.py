from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime

class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    registered_at: datetime
    updated_at: datetime
    is_admin: bool
    is_blocked: bool

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    is_blocked: Optional[bool] = None

class UserAdminUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    is_admin: Optional[bool] = None
    is_blocked: Optional[bool] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenRefresh(BaseModel):
    refresh_token: str

class ResourceCreate(BaseModel):
    metadata: Optional[Dict[str, Any]] = None

class ResourceResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]]

class PermissionGrant(BaseModel):
    user_id: int
    permission_type: str = Field(..., pattern="^(read|write|delete|manage)$")
    expires_at: Optional[datetime] = None

class MessageResponse(BaseModel):
    message: str