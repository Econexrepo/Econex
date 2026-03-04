import re
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


def _validate_strong_password(v: str) -> str:
    """Enforce NIST / OWASP-aligned password rules:
    - Minimum 8 characters
    - At least one uppercase letter  (A-Z)
    - At least one lowercase letter  (a-z)
    - At least one digit             (0-9)
    - At least one special character (!@#$%^&* …)
    """
    if len(v) < 8:
        raise ValueError('Password must be at least 8 characters long.')
    if not re.search(r'[A-Z]', v):
        raise ValueError('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', v):
        raise ValueError('Password must contain at least one lowercase letter.')
    if not re.search(r'\d', v):
        raise ValueError('Password must contain at least one digit.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\'\\/_+=;`~\-]', v):
        raise ValueError('Password must contain at least one special character (e.g. !@#$%^&*).')
    return v


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False   # when True, backend issues a 30-day JWT


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_strong_password(v)


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        return _validate_strong_password(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    username: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    username:   Optional[str] = None
    phone:      Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str

    @field_validator('new_password')
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        return _validate_strong_password(v)


class AvatarUpdateRequest(BaseModel):
    avatar_url: Optional[str] = None   # None / empty string = remove avatar


class ChatMessageIn(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatMessageOut(BaseModel):
    session_id: str
    role: str
    content: str


class DashboardStats(BaseModel):
    gdp_change: float
    wages_change: float
    agriculture_change: float
    unemployment_change: float
    personal_consumption_change: float
    govt_expenditure_change: float


class ChartDataPoint(BaseModel):
    label: str
    value: float


class RSUITrendPoint(BaseModel):
    year: int
    value: float
