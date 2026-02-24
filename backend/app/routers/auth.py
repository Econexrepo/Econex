# """
# Auth router – login, token validation
# Uses simple in-memory user store (replace with DB in production)
# """
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.models.schemas import LoginRequest, TokenResponse, UserOut

router = APIRouter()
# ── Password hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ── In-memory user store (swap with SQLAlchemy/SQLite in production) ──────────
USERS_DB = {
    "analyst@econex.lk": {
        "id": "user-001",
        "name": "Rushi Nethmin",
        "email": "analyst@econex.lk",
        "username": "rushi_nethmin",
        "phone": "+94 77 123 4567",
        "avatar_url": "https://ui-avatars.com/api/?name=Rushi+N&background=7c3aed&color=fff&size=80",
        # bcrypt hash of "password123"
        "hashed_password": pwd_context.hash("password123"),
    }
}


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserOut:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = USERS_DB.get(email)
    if user is None:
        raise credentials_exception

    return UserOut(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        username=user["username"],
        phone=user.get("phone"),
        avatar_url=user.get("avatar_url"),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = USERS_DB.get(body.email)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token({"sub": user["email"]})
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            username=user["username"],
            phone=user.get("phone"),
            avatar_url=user.get("avatar_url"),
        ),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: UserOut = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout():
    # Stateless JWT — client just discards the token
    return {"message": "Logged out successfully"}



