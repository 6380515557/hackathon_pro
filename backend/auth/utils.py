# backend/auth/utils.py
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from jose import jwt
from passlib.context import CryptContext

# Import the get_database function to interact with MongoDB
from ..database import get_database

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration (ensure these environment variables are set in your .env file)
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)) # Default to 30 mins

if not SECRET_KEY or not ALGORITHM:
    raise ValueError("JWT_SECRET_KEY and JWT_ALGORITHM environment variables must be set.")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def authenticate_user(db: Any, username: str, password: str):
    """
    Authenticates a user by username and password.
    Returns the user document if authenticated, None otherwise.
    """
    user_doc = await db["users"].find_one({"username": username})
    if not user_doc:
        return None
    if not verify_password(password, user_doc["hashed_password"]):
        return None
    return user_doc # Return the user document, not just True/False