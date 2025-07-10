# backend/services/user_service.py

from typing import Any, List
from bson import ObjectId

# Corrected imports based on your schemas.py
from ..schemas import UserCreate, UserResponse, UserInDB # Now UserInDB should be available!

# Import the password hashing utility from auth.utils
from ..auth.utils import get_password_hash # This should already be correct

async def get_user_by_username(db: Any, username: str) -> UserInDB | None:
    """
    Fetches a user from the database by username.
    Returns a UserInDB object if found, otherwise None.
    """
    user_doc = await db["users"].find_one({"username": username})
    if user_doc:
        # Ensure _id is correctly mapped to 'id' for Pydantic
        user_doc_processed = user_doc.copy()
        if '_id' in user_doc_processed:
            user_doc_processed['id'] = str(user_doc_processed['_id'])
            del user_doc_processed['_id']
        return UserInDB(**user_doc_processed)
    return None

async def get_user_by_id(db: Any, user_id: str) -> UserInDB | None:
    """
    Fetches a user from the database by their MongoDB _id.
    Returns a UserInDB object if found, otherwise None.
    """
    if not ObjectId.is_valid(user_id):
        return None

    user_doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if user_doc:
        user_doc_processed = user_doc.copy()
        if '_id' in user_doc_processed:
            user_doc_processed['id'] = str(user_doc_processed['_id'])
            del user_doc_processed['_id']
        return UserInDB(**user_doc_processed)
    return None

async def create_user(db: Any, user: UserCreate) -> UserResponse: # Return UserResponse for public view
    """
    Creates a new user in the database.
    Hashes the password before saving.
    Returns the public user data of the created user (UserResponse).
    """
    hashed_password = get_password_hash(user.password)
    user_dict = user.model_dump(exclude_unset=True) # Convert Pydantic model to dict, exclude optional fields not set
    user_dict["hashed_password"] = hashed_password
    
    # Ensure 'roles' is stored as a list, default to ['operator'] if not provided
    if not user_dict.get("roles"):
        user_dict["roles"] = ["operator"]
    
    del user_dict["password"] # Remove plain password before inserting into DB

    result = await db["users"].insert_one(user_dict)
    
    # Fetch the newly created user to return a complete UserResponse object
    created_user_doc = await db["users"].find_one({"_id": result.inserted_id})

    if created_user_doc:
        # Convert ObjectId to string 'id' for UserResponse
        created_user_doc_processed = created_user_doc.copy()
        if '_id' in created_user_doc_processed:
            created_user_doc_processed['id'] = str(created_user_doc_processed['_id'])
            del created_user_doc_processed['_id']
        return UserResponse(**created_user_doc_processed)
    
    raise Exception("Failed to retrieve created user after insertion.")

async def get_all_users(db: Any) -> List[UserResponse]: # Return List[UserResponse] for public view
    """
    Retrieves all users from the database.
    Excludes sensitive data like hashed_password.
    """
    users_cursor = db["users"].find({}, {"hashed_password": 0}) # Exclude hashed_password
    all_users_docs = await users_cursor.to_list(None) # Fetch all documents

    users_public_data = []
    for user_doc in all_users_docs:
        user_doc_processed = user_doc.copy()
        if '_id' in user_doc_processed:
            user_doc_processed['id'] = str(user_doc_processed['_id'])
            del user_doc_processed['_id']
        users_public_data.append(UserResponse(**user_doc_processed))
    return users_public_data

async def update_user(db: Any, user_id: str, update_data: dict) -> UserResponse | None: # Return UserResponse
    """
    Updates an existing user's details in the database.
    Returns the updated UserResponse object if successful, otherwise None.
    """
    if not ObjectId.is_valid(user_id):
        return None

    # Do not allow direct update of password here, handle it separately if needed
    if "password" in update_data:
        del update_data["password"]
    if "username" in update_data: # Username should generally not be updated
        del update_data["username"]

    result = await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        return None # User not found
    
    updated_user_doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if updated_user_doc:
        updated_user_doc_processed = updated_user_doc.copy()
        if '_id' in updated_user_doc_processed:
            updated_user_doc_processed['id'] = str(updated_user_doc_processed['_id'])
            del updated_user_doc_processed['_id']
        return UserResponse(**updated_user_doc_processed)
    return None

async def delete_user(db: Any, user_id: str) -> bool:
    """
    Deletes a user from the database by their ID.
    Returns True if user was deleted, False otherwise.
    """
    if not ObjectId.is_valid(user_id):
        return False

    result = await db["users"].delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count > 0