import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Response, status
from app.database import get_database
from app.models.user import (
    UserRegister,
    UserLogin,
    UserOut,
    UserInDB,
    TokenResponse,
    UserRole,
)
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (PUBLIC or OFFICIAL)",
)
async def register(
    user_data: UserRegister,
    response: Response,
    db=Depends(get_database),
):
    """
    Register a new user with either PUBLIC or OFFICIAL role.
    Validates input, checks for duplicate email, hashes password,
    creates JWT token, sets HttpOnly cookie, and returns session token.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not established",
        )

    # Check for existing email (case-insensitive)
    existing_user = await db["users"].find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    hashed = hash_password(user_data.password)

    user_doc = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "password_hash": hashed,
        "role": user_data.role.value,
        "created_at": now,
    }

    await db["users"].insert_one(user_doc)

    # Generate JWT
    token = create_access_token(user_id=user_id, role=user_data.role)

    # Set HttpOnly cookie
    max_age = JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=max_age,
        expires=max_age,
        samesite="lax",
        secure=False,  # Set to True in production HTTPS
        path="/",
    )

    user_out = UserOut(
        id=user_id,
        name=user_data.name,
        email=user_data.email,
        role=user_data.role,
        created_at=now,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_out,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and return JWT session",
)
async def login(
    credentials: UserLogin,
    response: Response,
    db=Depends(get_database),
):
    """
    Authenticate user using email and password.
    Returns JWT and user profile with role (PUBLIC or OFFICIAL).
    Sets HttpOnly cookie for session persistence.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not established",
        )

    user_doc = await db["users"].find_one({"email": credentials.email})
    if not user_doc or not verify_password(credentials.password, user_doc.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Resolve user role
    role_val = user_doc.get("role", "PUBLIC")
    try:
        user_role = UserRole(role_val)
    except ValueError:
        user_role = UserRole.PUBLIC

    token = create_access_token(user_id=user_doc["id"], role=user_role)

    # Set HttpOnly cookie
    max_age = JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=max_age,
        expires=max_age,
        samesite="lax",
        secure=False,  # Set to True in production HTTPS
        path="/",
    )

    user_out = UserOut(
        id=user_doc["id"],
        name=user_doc["name"],
        email=user_doc["email"],
        role=user_role,
        created_at=user_doc.get("created_at", datetime.now(timezone.utc)),
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user_out,
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current authenticated user profile",
)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    """
    Returns the currently authenticated user's profile and verified role.
    """
    return UserOut(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
    )


@router.post(
    "/logout",
    summary="Log out and clear session cookie",
)
async def logout(response: Response):
    """
    Clears the HttpOnly access_token cookie.
    """
    response.delete_cookie(key="access_token", path="/", samesite="lax")
    return {"message": "Successfully logged out"}
