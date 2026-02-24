from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: str
    password: str


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
    last_name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


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
