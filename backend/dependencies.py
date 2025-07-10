# backend/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta
import os
from jose import jwt, JWTError
from typing import List

# IMPORTANT: Adjust this import path based on where your schemas are relative to backend/dependencies.py
# If schemas is directly under backend (backend/schemas.py), then it's 'from .schemas import ...'
# If schemas is under backend/auth (backend/auth/schemas.py), then it's 'from ..auth.schemas import ...'
# Assuming backend/schemas.py exists for TokenData and UserResponse:
from .schemas import TokenData, UserResponse

# IMPORTANT: Adjust this import path based on where your user_service is relative to backend/dependencies.py
# Assuming backend/services/user_service.py exists:
from .services.user_service import get_user_by_username # This returns UserInDB

# IMPORTANT: Adjust this import path based on where your database.py is relative to backend/dependencies.py
# Assuming backend/database.py exists:
from .database import get_database

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """
    Dependency to get the current authenticated user from a JWT token.
    Returns a UserResponse object if successful, raises HTTPException otherwise.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        secret_key = os.getenv("JWT_SECRET_KEY")
        algorithm = os.getenv("JWT_ALGORITHM")
        if not secret_key or not algorithm:
            raise ValueError("JWT_SECRET_KEY or JWT_ALGORITHM environment variable not set")

        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        username: str = payload.get("sub")
        # Ensure 'roles' key exists in payload; default to empty list if not
        user_roles: List[str] = payload.get("roles", [])
        if username is None or not user_roles:
            raise credentials_exception
        token_data = TokenData(username=username, scopes=user_roles) # 'scopes' aligns with OAuth2 spec for roles

    except JWTError:
        raise credentials_exception
    except ValueError as e: # Catch the ValueError from missing env vars
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
    db = get_database()
    
    # Retrieve user from the database to ensure they still exist and are active
    user_in_db = await get_user_by_username(db, token_data.username) # This returns UserInDB
    if user_in_db is None:
        raise credentials_exception
    
    # Convert UserInDB object to UserResponse object, excluding sensitive hashed_password
    # Use model_dump() for Pydantic v2 or dict() for Pydantic v1
    return UserResponse(**user_in_db.model_dump(exclude={"hashed_password"}))


def role_required(required_roles: List[str]):
    """
    Dependency factory to check if the current user has any of the required roles.
    Usage: Depends(role_required(["admin", "supervisor"]))
    """
    def role_checker(current_user: UserResponse = Depends(get_current_user)):
        # Ensure user has roles (should always be true if user is authenticated via get_current_user)
        if not current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions: User has no roles assigned."
            )
        
        # Check if the user has any of the required roles
        for role in required_roles:
            if role in current_user.roles:
                return current_user # User has at least one of the required roles
        
        # If no required roles are found
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions: Required roles are {required_roles}."
        )
    return role_checker