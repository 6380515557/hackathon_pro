# backend/auth/security.py

import os
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from motor.motor_asyncio import AsyncIOMotorCollection
from passlib.context import CryptContext # For password hashing

# Assuming these are defined in backend/schemas.py
from ..schemas import TokenData, UserResponse

# Import the users_collection directly from database.py for use in authenticate_user
from ..database import users_collection

# --- Password Hashing Configuration ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# --- JWT Configuration ---
# Get these from environment variables. Raise an error if SECRET_KEY is not set.
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256") # Default to HS256 if not set
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)) # Default to 30 minutes

if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is not set. Please set it in your .env file.")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token") # This should match your router's tokenUrl

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Authentication Functions ---

async def authenticate_user(
    collection: AsyncIOMotorCollection, # This will be the users_collection passed from the dependency
    username: str,
    password: str
) -> Optional[UserResponse]:
    """
    Authenticates a user by checking username and password against the database.
    """
    user_data = await collection.find_one({"username": username})
    if not user_data:
        return None
    
    # Assuming 'hashed_password' is the field storing the hashed password in the DB
    if not verify_password(password, user_data.get("hashed_password")):
        return None
    
    # Convert MongoDB ObjectId to 'id' string and remove '_id'
    if '_id' in user_data:
        user_data['id'] = str(user_data.pop('_id'))
    
    return UserResponse(**user_data)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """
    Decodes the JWT token and returns the current user's data.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_role: str = payload.get("role", "user") # Default role if not in token
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username, role=user_role)
    except JWTError:
        raise credentials_exception
    
    # Fetch user from DB to ensure they are still valid and get full details
    # We use the global users_collection directly from database.py for this
    user_data = await users_collection.find_one({"username": token_data.username})
    if user_data is None:
        raise credentials_exception
    
    # Convert MongoDB ObjectId to 'id' string and remove '_id'
    if '_id' in user_data:
        user_data['id'] = str(user_data.pop('_id'))
    
    return UserResponse(**user_data)

async def get_current_active_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """
    Dependency to ensure the current user is active.
    """
    # Assuming UserResponse schema has an 'is_active' field, default to True if not present
    if not getattr(current_user, 'is_active', True): 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

def role_required(required_roles: List[str]):
    """
    Dependency to check if the current user has one of the required roles.
    """
    def role_checker(current_user: UserResponse = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user
    return role_checker