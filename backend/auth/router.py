# backend/auth/router.py

from datetime import timedelta
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorCollection # Import this for type hinting
from jose import jwt, JWTError # Keep these if you use them for token decoding
from bson import ObjectId # Required for ObjectId handling if converting directly

from ..database import users_collection # CORRECTED IMPORT: Import the specific collection
from ..schemas import UserCreate, UserResponse, Token, TokenData # Ensure TokenData is here
from .utils import get_password_hash, verify_password, create_access_token # Assuming these are in backend/auth/utils.py
from .security import authenticate_user, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user, get_current_active_user # Assuming these are in backend/auth/security.py

# Initialize the APIRouter
router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token") # Ensure this matches your token URL

# NEW DEPENDENCY: To get the users collection
async def get_users_collection() -> AsyncIOMotorCollection:
    """Dependency function to provide the users collection."""
    return users_collection

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    collection: AsyncIOMotorCollection = Depends(get_users_collection) # Use the new dependency
):
    """
    Authenticates a user and returns an access token.
    """
    user = await authenticate_user(collection, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, # Include role in token data
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    collection: AsyncIOMotorCollection = Depends(get_users_collection) # Use the new dependency
):
    """
    Registers a new user in the database.
    """
    existing_user = await collection.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user_data.password)
    user_data_dict = user_data.model_dump()
    user_data_dict["hashed_password"] = hashed_password # Store hashed password
    del user_data_dict["password"] # Remove plain password
    user_data_dict["is_active"] = True # Default for new users
    # Ensure a default role is set if not provided in UserCreate, e.g., "user"
    if "role" not in user_data_dict:
        user_data_dict["role"] = "user" # Default role for new registrations

    try:
        result = await collection.insert_one(user_data_dict)
        created_user = await collection.find_one({"_id": result.inserted_id})
        if created_user:
            # Convert ObjectId to string for response
            created_user["id"] = str(created_user.pop("_id"))
            return UserResponse(**created_user)
        raise HTTPException(status_code=500, detail="User registration failed")
    except Exception as e:
        # Catching DuplicateKeyError specifically might be better here if applicable
        if "duplicate key" in str(e).lower(): # Generic check for duplicate key errors
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        raise HTTPException(status_code=500, detail=f"User registration failed: {e}")

@router.get("/users/me/", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_active_user)):
    """
    Retrieves the details of the currently authenticated active user.
    """
    return current_user

# NEW API ENDPOINT: Get All Users (Requires admin/supervisor role)
def role_required(required_roles: List[str]):
    """Dependency to check user role."""
    def role_checker(current_user: UserResponse = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user
    return role_checker

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: UserResponse = Depends(role_required(["admin", "supervisor"])), # Only admins and supervisors
    collection: AsyncIOMotorCollection = Depends(get_users_collection) # Use the new dependency
):
    """
    Retrieve a list of all registered users.
    Requires 'admin' or 'supervisor' role.
    """
    # Fetch all users from the database, excluding 'hashed_password' and '_id' from the initial projection
    all_users_cursor = collection.find({}, {"hashed_password": 0})
    all_users_data = await all_users_cursor.to_list(None) # Fetch all documents

    users_for_response = []
    for user_doc in all_users_data:
        # Convert ObjectId to string for 'id' field, and remove '_id'
        user_doc['id'] = str(user_doc.pop('_id'))
        users_for_response.append(UserResponse(**user_doc))
        
    return users_for_response