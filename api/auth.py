"""
JWT Authentication
Handles login, token creation, and role-based access control.
Roles: ADMIN | MANAGER | EMPLOYEE
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────
SECRET_KEY  = "gps-secret-key-change-in-production-use-env-var"
ALGORITHM   = "HS256"
TOKEN_EXPIRY_MINUTES = 480  # 8 hours

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── Mock user store (replace with Oracle GPS_USERS table) ─────
MOCK_USERS = {
    "admin@acme.com": {
        "user_id": 1, "name": "Admin User",
        "email": "admin@acme.com",
        "hashed_password": pwd_context.hash("admin123"),
        "role": "ADMIN", "employee_id": None,
    },
    "manager@acme.com": {
        "user_id": 2, "name": "Jane Manager",
        "email": "manager@acme.com",
        "hashed_password": pwd_context.hash("manager123"),
        "role": "MANAGER", "employee_id": None,
    },
    "jcarter@acme.com": {
        "user_id": 3, "name": "James Carter",
        "email": "jcarter@acme.com",
        "hashed_password": pwd_context.hash("emp123"),
        "role": "EMPLOYEE", "employee_id": 1,
    },
    "psharma@acme.com": {
        "user_id": 4, "name": "Priya Sharma",
        "email": "psharma@acme.com",
        "hashed_password": pwd_context.hash("emp123"),
        "role": "EMPLOYEE", "employee_id": 2,
    },
}


# ── Pydantic models ───────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = TOKEN_EXPIRY_MINUTES * 60
    role: str
    name: str


class CurrentUser(BaseModel):
    user_id: int
    name: str
    email: str
    role: str
    employee_id: Optional[int] = None


# ── Core auth functions ───────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire  = datetime.utcnow() + (expires_delta or timedelta(minutes=TOKEN_EXPIRY_MINUTES))
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = MOCK_USERS.get(email.lower())
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = MOCK_USERS.get(email)
    if not user:
        raise credentials_exception

    return CurrentUser(
        user_id=user["user_id"],
        name=user["name"],
        email=email,
        role=user["role"],
        employee_id=user.get("employee_id"),
    )


# ── Role guards ───────────────────────────────────────────────

def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_manager_or_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role not in ("ADMIN", "MANAGER"):
        raise HTTPException(status_code=403, detail="Manager or Admin access required")
    return current_user


def require_authenticated(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return current_user
