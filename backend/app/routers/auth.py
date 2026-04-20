import random
import string
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text

from app.config import settings
from app.db import get_engine
from app.models.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.services.email import send_reset_code_email

router = APIRouter()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=True,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

engine = get_engine()


def _make_username(name: str) -> str:
    base = name.strip().lower().replace(" ", "*")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{base}_{suffix}"


def _generate_reset_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def _validate_bcrypt_password(password: str) -> None:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long. Maximum allowed length is 72 bytes.",
        )


def verify_password(plain: str, hashed: str) -> bool:
    _validate_bcrypt_password(plain)
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long. Maximum allowed length is 72 bytes.",
        )


def hash_password(plain: str) -> str:
    _validate_bcrypt_password(plain)
    try:
        return pwd_context.hash(plain)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long. Maximum allowed length is 72 bytes.",
        )


def _verify_legacy_sha256_password(plain: str, hashed: str) -> bool:
    candidate = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    return candidate == (hashed or "").strip()


def verify_and_maybe_migrate_password(plain: str, hashed: str) -> Tuple[bool, Optional[str]]:
    """
    Returns:
        (is_valid, new_hash_if_migration_needed)

    Behavior:
    - If stored hash is bcrypt, verify with bcrypt.
    - If stored hash looks like legacy SHA256 hex and matches, return a new bcrypt hash.
    - Otherwise return (False, None).
    """
    if not hashed:
        return False, None

    hashed = hashed.strip()

    if hashed.startswith("$2a$") or hashed.startswith("$2b$") or hashed.startswith("$2y$"):
        return verify_password(plain, hashed), None

    if len(hashed) == 64 and all(c in "0123456789abcdefABCDEF" for c in hashed):
        if _verify_legacy_sha256_password(plain, hashed):
            return True, hash_password(plain)

    return False, None


def create_access_token(data: dict, expire_minutes: int | None = None) -> str:
    to_encode = data.copy()
    minutes = expire_minutes if expire_minutes else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
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
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    uid = payload.get("uid")
    if uid:
        return UserOut(
            id=uid,
            name=payload.get("name", ""),
            email=email,
            username=payload.get("username", ""),
            phone=payload.get("phone"),
            avatar_url=payload.get("avatar_url"),
        )

    # Fallback for tokens issued before this change
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id, name, email, username, phone, avatar_url "
                "FROM users WHERE email = :email"
            ),
            {"email": email},
        ).fetchone()

    if not row:
        raise credentials_exception

    return UserOut(
        id=str(row[0]),
        name=row[1],
        email=row[2],
        username=row[3],
        phone=row[4],
        avatar_url=row[5],
    )


@router.post("/register")
async def register(body: RegisterRequest):
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": body.email},
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user_id = str(uuid.uuid4())
        username = _make_username(body.name)
        hashed = hash_password(body.password)

        avatar_url = (
            "https://ui-avatars.com/api/"
            f"?name={body.name.replace(' ', '+')}&background=7c3aed&color=fff&size=80"
        )

        conn.execute(
            text(
                """
                INSERT INTO users (id, name, email, username, hashed_password, avatar_url)
                VALUES (:id, :name, :email, :username, :hashed_password, :avatar_url)
                """
            ),
            {
                "id": user_id,
                "name": body.name,
                "email": body.email,
                "username": username,
                "hashed_password": hashed,
                "avatar_url": avatar_url,
            },
        )

    return {"message": "Account created successfully"}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT id, name, email, username, phone, avatar_url, hashed_password "
                "FROM users WHERE email = :email"
            ),
            {"email": body.email},
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        is_valid, migrated_hash = verify_and_maybe_migrate_password(body.password, row[6])

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if migrated_hash:
            conn.execute(
                text(
                    """
                    UPDATE users
                    SET hashed_password = :pw
                    WHERE email = :email
                    """
                ),
                {"pw": migrated_hash, "email": body.email},
            )

    expire_minutes = (
        settings.REMEMBER_ME_EXPIRE_MINUTES
        if body.remember_me
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    user = UserOut(
        id=str(row[0]),
        name=row[1],
        email=row[2],
        username=row[3],
        phone=row[4],
        avatar_url=row[5],
    )

    token = create_access_token(
        {
            "sub": user.email,
            "uid": user.id,
            "name": user.name,
            "username": user.username,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
        },
        expire_minutes,
    )

    return TokenResponse(access_token=token, user=user)


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": body.email},
        ).fetchone()

        if not row:
            return {"message": "If the email exists, a reset code has been sent"}

        code = _generate_reset_code()
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)

        conn.execute(
            text(
                """
                UPDATE users
                SET reset_code = :code, reset_code_expires = :expires
                WHERE email = :email
                """
            ),
            {"code": code, "expires": expires, "email": body.email},
        )

    try:
        send_reset_code_email(body.email, code)
    except RuntimeError as exc:
        print("Email error:", exc)
        raise HTTPException(
            status_code=502,
            detail="Email sending failed. Check SMTP settings",
        )

    return {"message": "Reset code sent"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT id, reset_code, reset_code_expires "
                "FROM users WHERE email = :email"
            ),
            {"email": body.email},
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email or code",
            )

        stored_code = row[1]
        expires = row[2]

        if stored_code != body.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset code",
            )

        if expires is not None:
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)

            if expires < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reset code expired",
                )

        new_hash = hash_password(body.new_password)

        conn.execute(
            text(
                """
                UPDATE users
                SET hashed_password = :pw,
                    reset_code = NULL,
                    reset_code_expires = NULL
                WHERE email = :email
                """
            ),
            {"pw": new_hash, "email": body.email},
        )

    return {"message": "Password reset successful"}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: UserOut = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}