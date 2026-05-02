"""
Auth Router — /auth endpoints
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from api.auth import authenticate_user, create_token, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Login and get JWT token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_token({"sub": user["email"], "role": user["role"]})
    return TokenResponse(
        access_token=token,
        role=user["role"],
        name=user["name"],
    )


@router.get("/me", summary="Get current user info")
def me(current_user=Depends(__import__("api.auth", fromlist=["get_current_user"]).get_current_user)):
    return {
        "user_id":     current_user.user_id,
        "name":        current_user.name,
        "email":       current_user.email,
        "role":        current_user.role,
        "employee_id": current_user.employee_id,
    }
