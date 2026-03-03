"""
Auth router – login, signup, forgot-password, reset-password, token validation.
Uses Supabase PostgreSQL via SQLAlchemy (db.py is NOT modified).
"""

import uuid, random, string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_engine
from app.services.email import send_reset_code_email
from app.models.schemas import (
    LoginRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter()

# ── Password hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ── DB engine (reuses your existing db.py) ─────────────────────────────────────
engine = get_engine()


# ── Helper: generate username from name ────────────────────────────────────────
def _make_username(name: str) -> str:
    """e.g. 'John Doe' → 'john_doe' """
    base = name.strip().lower().replace(" ", "_")
    # Append random digits to avoid collisions
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{base}_{suffix}"


# ── Helper: generate 6-digit reset code ────────────────────────────────────────
def _generate_reset_code() -> str:
    return "".join(random.choices(string.digits, k=6))


# ── Helper: password utilities ─────────────────────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


# ── JWT ────────────────────────────────────────────────────────────────────────
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ── Dependency: current user from JWT ──────────────────────────────────────────
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

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, name, email, username, phone, avatar_url FROM users WHERE email = :email"),
            {"email": email},
        ).fetchone()

    if row is None:
        raise credentials_exception

    return UserOut(
        id=str(row[0]),
        name=row[1],
        email=row[2],
        username=row[3],
        phone=row[4],
        avatar_url=row[5],
    )


# ══════════════════════════════════════════════════════════════════════════════
#  POST /register
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/register")
async def register(body: RegisterRequest):
    with engine.connect() as conn:
        # Check if email already exists
        existing = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": body.email},
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered.",
            )

        user_id = str(uuid.uuid4())
        username = _make_username(body.name)
        hashed = hash_password(body.password)
        avatar_url = f"https://ui-avatars.com/api/?name={body.name.replace(' ', '+')}&background=7c3aed&color=fff&size=80"

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
        conn.commit()

    return {"message": "Account created successfully."}


# ══════════════════════════════════════════════════════════════════════════════
#  POST /login
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, name, email, username, phone, avatar_url, hashed_password FROM users WHERE email = :email"),
            {"email": body.email},
        ).fetchone()

    if not row or not verify_password(body.password, row[6]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": row[2]})
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=str(row[0]),
            name=row[1],
            email=row[2],
            username=row[3],
            phone=row[4],
            avatar_url=row[5],
        ),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  POST /forgot-password
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": body.email},
        ).fetchone()

        if not row:
            # Don't reveal if the email exists – always return success
            return {"message": "If that email is registered, a reset code has been sent."}

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
        conn.commit()

    # ── Send the reset code via email ────────────────────────────────────────
    try:
        send_reset_code_email(to_email=body.email, reset_code=code)
    except RuntimeError as exc:
        # Log the error but don't expose internals to the client
        print(f"[AUTH] Email send error for {body.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the reset email. Please check your SMTP settings.",
        )

    return {"message": "If that email is registered, a reset code has been sent."}


# ══════════════════════════════════════════════════════════════════════════════
#  POST /reset-password
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, reset_code, reset_code_expires FROM users WHERE email = :email"),
            {"email": body.email},
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email or code.",
            )

        stored_code = row[1]
        expires = row[2]

        if not stored_code or stored_code != body.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset code.",
            )

        if expires and expires < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset code has expired. Please request a new one.",
            )

        # Update password and clear the reset code
        new_hash = hash_password(body.new_password)
        conn.execute(
            text(
                """
                UPDATE users
                SET hashed_password = :pw, reset_code = NULL, reset_code_expires = NULL
                WHERE email = :email
                """
            ),
            {"pw": new_hash, "email": body.email},
        )
        conn.commit()

    return {"message": "Password reset successfully."}


# ══════════════════════════════════════════════════════════════════════════════
#  GET /me
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/me", response_model=UserOut)
async def get_me(current_user: UserOut = Depends(get_current_user)):
    return current_user


# ══════════════════════════════════════════════════════════════════════════════
#  POST /logout
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/logout")
async def logout():
    # Stateless JWT — client just discards the token
    return {"message": "Logged out successfully"}
