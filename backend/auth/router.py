from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pymongo.errors import DuplicateKeyError
from jose import jwt, JWTError
import os
from bson import ObjectId
from typing import List # Import List for returning a list of users

from ..database import get_database
from ..schemas import UserCreate, UserResponse, Token, TokenData
from .utils import get_password_hash, verify_password, create_access_token
from datetime import timedelta

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

async def get_user_from_db(username: str):
    db = get_database()
    user = await db["users"].find_one({"username": username})
    if user:
        user_data_for_response = user.copy()
        user_data_for_response['id'] = str(user_data_for_response['_id'])
        del user_data_for_response['_id']
        return UserResponse(**user_data_for_response)
    return None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("JWT_ALGORITHM")])
        username: str = payload.get("sub")
        user_role: str = payload.get("role")
        if username is None or user_role is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=user_role)
    except JWTError:
        raise credentials_exception
    user = await get_user_from_db(token_data.username)
    if user is None:
        raise credentials_exception
    return user

def role_required(required_roles: list[str]):
    """Dependency to check user role."""
    def role_checker(current_user: UserResponse = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user
    return role_checker

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate):
    db = get_database()
    users_collection = db["users"]

    existing_user = await users_collection.find_one({"username": user_in.username})
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    hashed_password = get_password_hash(user_in.password)
    user_dict = user_in.model_dump()
    user_dict["hashed_password"] = hashed_password
    del user_dict["password"]

    try:
        result = await users_collection.insert_one(user_dict)
        created_user = await users_collection.find_one({"_id": result.inserted_id})

        if created_user:
            user_data_for_response = {
                "id": str(created_user["_id"]),
                "username": created_user["username"],
                "role": created_user["role"],
            }
            return UserResponse(**user_data_for_response)

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve created user")
    except DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered (DB constraint violation)")
    except Exception as e:
        if isinstance(e, ValueError) and "Invalid ObjectId" in str(e):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Data validation error after creation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register user: {e}")


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user_from_db(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password): # Assuming user object from DB has 'hashed_password'
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")))
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_user)):
    """Retrieve current authenticated user's details."""
    return current_user

# --- NEW API ENDPOINT: Get All Users ---
@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: UserResponse = Depends(role_required(["admin", "supervisor"])), # Only admins and supervisors can view all users
    db = Depends(get_database)
):
    """
    Retrieve a list of all registered users.
    Requires 'admin' or 'supervisor' role.
    """
    users_collection = db["users"]
    
    # Fetch all users from the database
    # Project only necessary fields (excluding hashed_password)
    # Using to_list(None) to fetch all documents from the cursor
    all_users_cursor = users_collection.find({}, {"hashed_password": 0}) # Exclude hashed_password
    all_users_data = await all_users_cursor.to_list(None) # Fetch all documents

    # Convert each user document to UserResponse schema
    # The get_user_from_db function already handles the ObjectId conversion,
    # so we can reuse that logic or do it directly here.
    # Let's do it directly here for clarity for this specific endpoint.
    users_for_response = []
    for user_doc in all_users_data:
        user_doc['id'] = str(user_doc['_id']) # Convert ObjectId to string
        del user_doc['_id'] # Remove the original ObjectId field
        users_for_response.append(UserResponse(**user_doc))
        
    return users_for_response
