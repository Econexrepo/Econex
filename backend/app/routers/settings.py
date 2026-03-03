"""
Settings router – fully functional user profile management.
Endpoints:
  GET    /api/settings/profile          – fetch current user profile
  PATCH  /api/settings/profile          – update name / username / phone
  POST   /api/settings/change-password  – change password (requires current password)
  PATCH  /api/settings/avatar           – set or remove avatar URL
"""

import pathlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from sqlalchemy import text

from app.db import get_engine
from app.routers.auth import get_current_user, verify_password, hash_password
from app.models.schemas import (
    UserOut,
    UpdateProfileRequest,
    ChangePasswordRequest,
    AvatarUpdateRequest,
)

router = APIRouter()
engine = get_engine()

# Resolve the uploads folder relative to this file's location
_UPLOADS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "uploads" / "avatars"
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_SIZE_BYTES = 5 * 1024 * 1024   # 5 MB


# ══════════════════════════════════════════════════════════════════════════════
#  GET /profile  – return the currently logged-in user's full profile
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/profile", response_model=UserOut)
async def get_profile(current_user: UserOut = Depends(get_current_user)):
    """Return the JWT-authenticated user's profile straight from the DB."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, name, email, username, phone, avatar_url FROM users WHERE email = :email"),
            {"email": current_user.email},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return UserOut(
        id=str(row[0]),
        name=row[1],
        email=row[2],
        username=row[3],
        phone=row[4],
        avatar_url=row[5],
    )


# ══════════════════════════════════════════════════════════════════════════════
#  PATCH /profile  – update name, username, and/or phone
# ══════════════════════════════════════════════════════════════════════════════
@router.patch("/profile", response_model=UserOut)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: UserOut = Depends(get_current_user),
):
    with engine.connect() as conn:
        # Fetch current values
        row = conn.execute(
            text("SELECT id, name, email, username, phone, avatar_url FROM users WHERE email = :email"),
            {"email": current_user.email},
        ).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # ── Resolve updated fields (fall back to current DB values) ──────────
        current_name  = row[1]
        name_parts    = current_name.split(" ", 1)
        current_first = name_parts[0]
        current_last  = name_parts[1] if len(name_parts) > 1 else ""

        new_first = (body.first_name or "").strip() or current_first
        new_last  = (body.last_name  or "").strip() or current_last
        new_name  = f"{new_first} {new_last}".strip()

        new_username = (body.username or "").strip() or row[3]
        new_phone    = (body.phone    or "").strip() or row[4]

        # ── Username uniqueness check ────────────────────────────────────────
        if new_username != row[3]:
            taken = conn.execute(
                text("SELECT id FROM users WHERE username = :username AND email != :email"),
                {"username": new_username, "email": current_user.email},
            ).fetchone()
            if taken:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="That username is already taken. Please choose another.",
                )

        # ── Regenerate avatar if name changed and user has auto-generated one ─
        new_avatar_url = row[5]
        if new_name != current_name and row[5] and "ui-avatars.com" in (row[5] or ""):
            new_avatar_url = (
                f"https://ui-avatars.com/api/?name={new_name.replace(' ', '+')}"
                f"&background=7c3aed&color=fff&size=80"
            )

        # ── Persist ──────────────────────────────────────────────────────────
        conn.execute(
            text(
                """
                UPDATE users
                SET name       = :name,
                    username   = :username,
                    phone      = :phone,
                    avatar_url = :avatar_url,
                    updated_at = :updated_at
                WHERE email = :email
                """
            ),
            {
                "name":       new_name,
                "username":   new_username,
                "phone":      new_phone,
                "avatar_url": new_avatar_url,
                "updated_at": datetime.now(timezone.utc),
                "email":      current_user.email,
            },
        )
        conn.commit()

    return UserOut(
        id=str(row[0]),
        name=new_name,
        email=row[2],
        username=new_username,
        phone=new_phone,
        avatar_url=new_avatar_url,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  POST /change-password  – verify current password then set new one
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: UserOut = Depends(get_current_user),
):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT hashed_password FROM users WHERE email = :email"),
            {"email": current_user.email},
        ).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # ── Verify current password ──────────────────────────────────────────
        if not verify_password(body.current_password, row[0]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect.",
            )

        # ── Reject if new password is same as old ────────────────────────────
        if body.new_password == body.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from the current password.",
            )

        # ── Minimum length ───────────────────────────────────────────────────
        if len(body.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long.",
            )

        new_hash = hash_password(body.new_password)
        conn.execute(
            text(
                """
                UPDATE users
                SET hashed_password = :pw,
                    updated_at      = :updated_at
                WHERE email = :email
                """
            ),
            {
                "pw":         new_hash,
                "updated_at": datetime.now(timezone.utc),
                "email":      current_user.email,
            },
        )
        conn.commit()

    return {"message": "Password changed successfully."}


# ══════════════════════════════════════════════════════════════════════════════
#  PATCH /avatar  – set a custom avatar URL, or remove avatar (→ initials)
# ══════════════════════════════════════════════════════════════════════════════
@router.patch("/avatar", response_model=UserOut)
async def update_avatar(
    body: AvatarUpdateRequest,
    current_user: UserOut = Depends(get_current_user),
):
    # If avatar_url is empty / null → fall back to auto-generated initials avatar
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, name, email, username, phone FROM users WHERE email = :email"),
            {"email": current_user.email},
        ).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        new_avatar = (body.avatar_url or "").strip() or (
            f"https://ui-avatars.com/api/?name={row[1].replace(' ', '+')}"
            f"&background=7c3aed&color=fff&size=80"
        )

        conn.execute(
            text(
                """
                UPDATE users
                SET avatar_url = :avatar_url,
                    updated_at = :updated_at
                WHERE email = :email
                """
            ),
            {
                "avatar_url": new_avatar,
                "updated_at": datetime.now(timezone.utc),
                "email":      current_user.email,
            },
        )
        conn.commit()

    return UserOut(
        id=str(row[0]),
        name=row[1],
        email=row[2],
        username=row[3],
        phone=row[4],
        avatar_url=new_avatar,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  POST /avatar/upload  – upload an image file as profile picture
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/avatar/upload", response_model=UserOut)
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: UserOut = Depends(get_current_user),
):
    # ── Validate MIME type ───────────────────────────────────────────────────
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. "
                   f"Allowed: JPEG, PNG, WebP, GIF.",
        )

    # ── Read & check size ────────────────────────────────────────────────────
    contents = await file.read()
    if len(contents) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be smaller than 5 MB.",
        )

    # ── Build a unique filename: <user_id>_<timestamp>.<ext> ─────────────────
    ext = file.content_type.split("/")[-1].replace("jpeg", "jpg")
    timestamp = int(datetime.now(timezone.utc).timestamp())
    filename = f"{current_user.id}_{timestamp}.{ext}"
    dest = _UPLOADS_DIR / filename

    # ── Delete any previous uploaded avatar for this user ────────────────────
    for old in _UPLOADS_DIR.glob(f"{current_user.id}_*"):
        try:
            old.unlink()
        except OSError:
            pass

    # ── Save the file ─────────────────────────────────────────────────────────
    dest.write_bytes(contents)

    # ── Build the public URL (e.g. http://localhost:8000/uploads/avatars/...) ─
    base_url = str(request.base_url).rstrip("/")
    avatar_url = f"{base_url}/uploads/avatars/{filename}"

    # ── Persist to DB ─────────────────────────────────────────────────────────
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, name, email, username, phone FROM users WHERE email = :email"),
            {"email": current_user.email},
        ).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        conn.execute(
            text(
                """
                UPDATE users
                SET avatar_url = :avatar_url,
                    updated_at = :updated_at
                WHERE email = :email
                """
            ),
            {
                "avatar_url": avatar_url,
                "updated_at": datetime.now(timezone.utc),
                "email":      current_user.email,
            },
        )
        conn.commit()

    return UserOut(
        id=str(row[0]),
        name=row[1],
        email=row[2],
        username=row[3],
        phone=row[4],
        avatar_url=avatar_url,
    )

