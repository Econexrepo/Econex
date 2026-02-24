"""
Settings router – user profile management
"""
from fastapi import APIRouter, Depends
from app.routers.auth import get_current_user, USERS_DB
from app.models.schemas import UserOut, UpdateProfileRequest

router = APIRouter()


@router.get("/profile", response_model=UserOut)
async def get_profile(current_user: UserOut = Depends(get_current_user)):
    return current_user


@router.patch("/profile", response_model=UserOut)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: UserOut = Depends(get_current_user),
):
    user = USERS_DB.get(current_user.email)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    # Apply updates
    if body.first_name or body.last_name:
        first = body.first_name or user["name"].split()[0]
        last  = body.last_name  or (user["name"].split()[1] if len(user["name"].split()) > 1 else "")
        user["name"] = f"{first} {last}".strip()
    if body.username:
        user["username"] = body.username
    if body.phone:
        user["phone"] = body.phone

    return UserOut(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        username=user["username"],
        phone=user.get("phone"),
        avatar_url=user.get("avatar_url"),
    )
