# backend/auth/security.py

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt

# Import your schemas
from ..schemas import TokenData, UserInDB, UserResponse
from ..database import get_database # Import get_database
from motor.motor_asyncio import AsyncIOMotorClient # For type hinting get_database dependency

# Load environment variables (should be loaded in main.py, but good to have a fallback)
# if not os.getenv("JWT_SECRET_KEY"):
#     from dotenv import load_dotenv
#     load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# Ensure SECRET_KEY is set
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable not set. Please set it.")


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scopes={
        "me": "Read information about the current user.",
        "operator": "Perform operator actions (e.g., create/update production data).",
        "admin": "Perform administrative actions (e.g., delete users, full control)."
    }
)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Helper function to get user from DB
async def get_user_from_db(db: AsyncIOMotorClient, username: str) -> Optional[UserInDB]:
    """Fetches a user document from the 'users' collection."""
    users_collection = db["users"]
    user_data = await users_collection.find_one({"username": username})
    if user_data:
        return UserInDB(**user_data)
    return None

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorClient = Depends(get_database)
) -> UserInDB:
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=scopes)
    except JWTError:
        raise credentials_exception
    
    user = await get_user_from_db(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    
    # Check if user is active (not disabled or inactive)
    if user.disabled or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive or disabled user"
        )
    
    # Check scopes (roles assigned to the token)
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return user

async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    # This dependency ensures the user is active (not disabled)
    return current_user

# IMPORTANT CHANGE: This function is NO LONGER ASYNC
def role_required(required_roles: List[str]):
    async def _role_checker(current_user: UserInDB = Depends(get_current_active_user)):
        # Check if the user has any of the required roles
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have any of the required roles: {', '.join(required_roles)}"
            )
        return current_user
    return _role_checker