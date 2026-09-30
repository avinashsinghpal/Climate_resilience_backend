import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

from app.database import get_database
from app.models.user import UserRole, UserInDB, UserOut

load_dotenv()

# JWT Configuration from environment
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    # Fallback only for local dev warning
    JWT_SECRET = "fcap_dev_insecure_jwt_secret_key_change_in_production_environment"

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

http_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, role: UserRole, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a signed JWT access token.
    Payload contains ONLY minimal necessary claims:
    - sub (user id)
    - role (PUBLIC or OFFICIAL)
    - exp (expiration timestamp)
    - iat (issued at)
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "role": role.value if isinstance(role, UserRole) else str(role),
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decodes and validates a signed JWT token.
    Raises HTTPException 401 on expired or invalid signature.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_token_from_request(
    request: Request,
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer_scheme)
) -> str:
    """
    Extracts JWT from Authorization Bearer header or access_token cookie.
    """
    if auth_credentials and auth_credentials.credentials:
        return auth_credentials.credentials
    
    # Fallback to cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials were not provided",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(get_token_from_request),
    db = Depends(get_database)
) -> UserInDB:
    """
    Validates the JWT token and fetches the user from the database.
    """
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        )

    user_doc = await db["users"].find_one({"id": user_id})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Ensure role is validated
    role_val = user_doc.get("role", "PUBLIC")
    try:
        user_role = UserRole(role_val)
    except ValueError:
        user_role = UserRole.PUBLIC

    return UserInDB(
        id=user_doc["id"],
        name=user_doc["name"],
        email=user_doc["email"],
        password_hash=user_doc["password_hash"],
        role=user_role,
        created_at=user_doc.get("created_at", datetime.now(timezone.utc)),
    )


def require_role(allowed_roles: List[UserRole]):
    """
    Dependency factory that checks if current user has one of the allowed roles.
    """
    async def role_checker(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Required role {' or '.join([r.value for r in allowed_roles])}",
            )
        return current_user
    return role_checker


async def require_official_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Dependency that restricts route strictly to OFFICIAL users."""
    if current_user.role != UserRole.OFFICIAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: OFFICIAL role required",
        )
    return current_user


async def require_public_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Dependency that restricts route strictly to PUBLIC users."""
    if current_user.role != UserRole.PUBLIC:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: PUBLIC role required",
        )
    return current_user
