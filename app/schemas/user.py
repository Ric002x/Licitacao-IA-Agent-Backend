import re
from typing import Annotated
from pydantic import BaseModel, EmailStr, StringConstraints, field_validator


class UserRead(BaseModel):
    id: int
    email: str
    username: str
    is_superuser: bool

    class Config:
        from_attributes = True


class UserBody(BaseModel):
    email: EmailStr
    username: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=5, max_length=16
        )
    ]

    class Config:
        from_attributes = True


class UserCreate(UserBody):
    password: Annotated[
        str,
        StringConstraints(
            min_length=8
        )
    ]

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        regex = r'(?=^.{8,}$)((?=.*\d)|(?=.*\W+))^(?![.\n])(?=.*[A-Z]).*$'
        if not re.match(regex, v):
            raise ValueError("The password must have...")
        return v


class UserUpdate(UserBody):
    password: Annotated[
        str | None,
        StringConstraints(
            min_length=8
        )
    ] = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if v is None:
            return v
        regex = r'(?=^.{8,}$)((?=.*\d)|(?=.*\W+))^(?![.\n])(?=.*[A-Z]).*$'
        if not re.match(regex, v):
            raise ValueError("The password must have...")
        return v
