from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pymongo.errors import DuplicateKeyError
from jose import jwt, JWTError # Ensure JWTError is imported
import os

from ..database import get_database
from ..schemas import UserCreate, UserResponse, Token, TokenData # Updated import for UserResponse
from .utils import get_password_hash, verify_password, create_access_token
from datetime import timedelta

router = APIRouter()

# OAuth2PasswordBearer points to the endpoint where the token can be obtained
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

async def get_user_from_db(username: str):
    db = get_database()
    # Ensure you are querying the correct collection, typically 'users'
    user = await db["users"].find_one({"username": username})
    if user:
        return UserResponse(**user) # Use UserResponse to ensure _id is handled correctly
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
        user_role: str = payload.get("role") # Extract role from token
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
    users_collection = db["users"] # Get the users collection

    existing_user = await users_collection.find_one({"username": user_in.username})
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    hashed_password = get_password_hash(user_in.password)
    user_dict = user_in.model_dump() # Use model_dump() for Pydantic v2
    user_dict["hashed_password"] = hashed_password
    del user_dict["password"] # Don't store plain password

    try:
        result = await users_collection.insert_one(user_dict)
        # Retrieve the newly created user to return with the _id
        created_user = await users_collection.find_one({"_id": result.inserted_id})
        return UserResponse(**created_user)
    except DuplicateKeyError:
        # This catch is mostly for safety if unique index creation somehow fails
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered (DB constraint violation)")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register user: {e}")


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user_from_db(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password): # hashed_password is a field in UserInDB
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