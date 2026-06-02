"""
Schemas de autenticação
"""
from pydantic import BaseModel, EmailStr
from app.schemas.user import UserRead


class AuthBody(BaseModel):
    email: EmailStr
    password: str

    class Config:
        from_attributes = True


class TokenPayload(BaseModel):
    """Payload decodificado do JWT token"""
    user_id: str
    exp: float


class Token(BaseModel):
    """Response com o token de acesso"""
    user: UserRead
    access_token: str
