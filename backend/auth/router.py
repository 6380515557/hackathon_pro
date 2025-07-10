# backend/auth/router.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import os

from ..database import get_database
from ..schemas import Token, UserResponse # TokenData is not directly used here
from .utils import authenticate_user, create_access_token
# Import get_current_user from the centralized dependencies file
from ..dependencies import get_current_user, role_required # Also import role_required if you use it in this router directly

router = APIRouter()

# --- IMPORTANT: get_current_user and role_required are NO LONGER DEFINED HERE ---
# They are now in backend/dependencies.py and imported above.

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return an access token.
    Requires username and password in x-www-form-urlencoded format.
    """
    db = get_database()
    user_doc = await authenticate_user(db, form_data.username, form_data.password)

    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active or disabled
    if not user_doc.get("is_active", True) or user_doc.get("disabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled",
        )

    access_token_expires_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)) # Default to 30 if not set
    access_token_expires = timedelta(minutes=access_token_expires_minutes)
    
    user_roles = user_doc.get("roles", ["viewer"]) # Default role if not specified
    access_token = create_access_token(
        data={"sub": user_doc["username"], "roles": user_roles},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me/", response_model=UserResponse)
async def read_current_user(current_user: UserResponse = Depends(get_current_user)):
    """
    Retrieve current authenticated user's details.
    Requires a valid JWT token in the Authorization header.
    """
    return current_user

# If you have any other endpoints in this router that need role_required,
# you can use it like this (example):
# @router.get("/admin-only", dependencies=[Depends(role_required(["admin"]))])
# async def admin_endpoint():
#     return {"message": "Welcome, Admin!"}