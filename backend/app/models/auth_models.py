from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional

class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="Valid work/personal email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 characters)")

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return clean

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return str(v).strip().lower()

class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")
    remember_me: bool = Field(default=False, description="Persist extended 30-day session")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return str(v).strip().lower()

class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered account email")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return str(v).strip().lower()

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, description="Expiring single-use reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New secure password")

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: Optional[str] = None

class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    expires_in: int
    message: str

class ForgotPasswordResponse(BaseModel):
    message: str
    status: str
    smtp_configured: bool
    dev_reset_token: Optional[str] = None

class MessageResponse(BaseModel):
    message: str
    status: str = "success"
