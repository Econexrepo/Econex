"""
Auth router – login, signup, forgot-password, reset-password, token validation.
Uses Supabase PostgreSQL via SQLAlchemy.
"""

import uuid, random, string
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_auth_db
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

# ── Password hashing ─────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Helper: generate username ─────────────────────────────────
def _make_username(name: str) -> str:
    base = name.strip().lower().replace(" ", "_")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{base}_{suffix}"


# ── Helper: reset code ───────────────────────────────────────
def _generate_reset_code() -> str:
    return "".join(random.choices(string.digits, k=6))


# ── Password helpers ─────────────────────────────────────────
def _prehash_password(password: str) -> str:
    """
    Convert arbitrary-length password into fixed-length material to avoid
    bcrypt's 72-byte input limit permanently.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(plain: str) -> str:
    """
    New scheme: bcrypt(sha256(password))
    """
    return pwd_context.hash(_prehash_password(plain))


def verify_and_maybe_migrate_password(plain: str, stored_hash: str):
    """
    Seamless migration:
      - New: bcrypt(sha256(password))
      - Old: bcrypt(password)

    Returns: (ok: bool, new_hash: str | None)
      - If new_hash is not None, caller should update DB.
    """
    # Try new scheme first
    if pwd_context.verify(_prehash_password(plain), stored_hash):
        return True, None

    # Fallback: old scheme for existing users
    if pwd_context.verify(plain, stored_hash):
        return True, pwd_context.hash(_prehash_password(plain))

    return False, None


def verify_password(plain: str, stored_hash: str) -> bool:
    """
    Backwards-compatible helper for other routers (e.g., settings.py).
    Uses migration-aware verification.
    """
    ok, _ = verify_and_maybe_migrate_password(plain, stored_hash)
    return ok


# ── JWT ────────────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expire_minutes: int | None = None) -> str:
    to_encode = data.copy()
    minutes = expire_minutes if expire_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ── Get current user ─────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_auth_db),
) -> UserOut:

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

    row = db.execute(
        text(
            "SELECT id, name, email, username, phone, avatar_url FROM users WHERE email = :email"
        ),
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


# ═════════════════════════════════════════════════════════════
# POST /register
# ═════════════════════════════════════════════════════════════
@router.post("/register")
async def register(
    body: RegisterRequest,
    db: Session = Depends(get_auth_db),
):

    existing = db.execute(
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

    avatar_url = (
        f"https://ui-avatars.com/api/?name={body.name.replace(' ', '+')}"
        "&background=7c3aed&color=fff&size=80"
    )

    db.execute(
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

    db.commit()

    return {"message": "Account created successfully."}


# ═════════════════════════════════════════════════════════════
# POST /login
# ═════════════════════════════════════════════════════════════
@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Session = Depends(get_auth_db),
):

    row = db.execute(
        text(
            """
            SELECT id, name, email, username, phone, avatar_url, hashed_password
            FROM users WHERE email = :email
            """
        ),
        {"email": body.email},
    ).fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    ok, new_hash = verify_and_maybe_migrate_password(body.password, row[6])
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # If this user was using the old hashing scheme, upgrade it silently
    if new_hash:
        db.execute(
            text("UPDATE users SET hashed_password = :pw WHERE id = :id"),
            {"pw": new_hash, "id": str(row[0])},
        )
        db.commit()

    # Use 30-day expiry when remember_me is requested, else 60-minute default
    expire_minutes = (
        settings.REMEMBER_ME_EXPIRE_MINUTES if body.remember_me
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token = create_access_token({"sub": row[2]}, expire_minutes=expire_minutes)
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


# ═════════════════════════════════════════════════════════════
# POST /forgot-password
# ═════════════════════════════════════════════════════════════
@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_auth_db),
):

    row = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": body.email},
    ).fetchone()

    if not row:
        return {"message": "If that email is registered, a reset code has been sent."}

    code = _generate_reset_code()
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)

    db.execute(
        text(
            """
            UPDATE users
            SET reset_code = :code, reset_code_expires = :expires
            WHERE email = :email
            """
        ),
        {"code": code, "expires": expires, "email": body.email},
    )

    db.commit()

    try:
        send_reset_code_email(to_email=body.email, reset_code=code)
    except RuntimeError as exc:
        print(f"[AUTH] Email error for {body.email}: {exc}")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the reset email. Check SMTP configuration.",
        )

    return {"message": "If that email is registered, a reset code has been sent."}


# ═════════════════════════════════════════════════════════════
# POST /reset-password
# ═════════════════════════════════════════════════════════════
@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_auth_db),
):

    row = db.execute(
        text(
            """
            SELECT id, reset_code, reset_code_expires
            FROM users WHERE email = :email
            """
        ),
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
            detail="Reset code expired.",
        )

    new_hash = hash_password(body.new_password)

    db.execute(
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

    db.commit()

    return {"message": "Password reset successfully."}


# ═════════════════════════════════════════════════════════════
# GET /me
# ═════════════════════════════════════════════════════════════
@router.get("/me", response_model=UserOut)
async def get_me(current_user: UserOut = Depends(get_current_user)):
    return current_user


# ═════════════════════════════════════════════════════════════
# POST /logout
# ═════════════════════════════════════════════════════════════
@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}