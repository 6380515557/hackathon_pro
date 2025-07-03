# backend/routers/reference_data.py

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId # Required for working with MongoDB's _id
from typing import List, Optional

# Correctly import schemas
from ..schemas import ReferenceDataCategoryCreate, ReferenceDataCategoryResponse, UserResponse

# Import database collection and security dependencies
from ..database import reference_data_collection
from ..auth.security import get_current_active_user, role_required

router = APIRouter(
    prefix="/reference_data",
    tags=["Reference Data"],
)

# Dependency to get the reference data collection
async def get_reference_data_collection() -> AsyncIOMotorCollection:
    """Dependency function to provide the reference data collection."""
    return reference_data_collection

# --- API Endpoints for Reference Data Management ---

@router.post("/", response_model=ReferenceDataCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_reference_data_category(
    category_in: ReferenceDataCategoryCreate,
    current_user: UserResponse = Depends(role_required(["admin"])), # Only admins can create new categories
    collection: AsyncIOMotorCollection = Depends(get_reference_data_collection)
):
    """
    Creates a new reference data category.
    Requires 'admin' role. Category names must be unique.
    """
    # Check if a category with the same name already exists
    existing_category = await collection.find_one({"category_name": category_in.category_name})
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reference data category '{category_in.category_name}' already exists."
        )

    category_data = category_in.model_dump(by_alias=True, exclude_unset=True)
    
    result = await collection.insert_one(category_data)
    created_category = await collection.find_one({"_id": result.inserted_id})

    if created_category:
        created_category["id"] = str(created_category.pop("_id"))
        return ReferenceDataCategoryResponse(**created_category)
    raise HTTPException(status_code=500, detail="Failed to create reference data category.")


@router.get("/", response_model=List[ReferenceDataCategoryResponse])
async def get_all_reference_data_categories(
    current_user: UserResponse = Depends(get_current_active_user), # All active users can read reference data
    collection: AsyncIOMotorCollection = Depends(get_reference_data_collection)
):
    """
    Retrieves all available reference data categories.
    Accessible to all authenticated active users.
    """
    categories_cursor = collection.find({})
    all_categories = await categories_cursor.to_list(length=None)

    if not all_categories:
        return []
    
    # Convert ObjectId to string for each category
    return [ReferenceDataCategoryResponse(**{**c, "id": str(c["_id"])}) for c in all_categories]


@router.get("/{category_name}", response_model=ReferenceDataCategoryResponse)
async def get_reference_data_by_name(
    category_name: str,
    current_user: UserResponse = Depends(get_current_active_user), # All active users can read reference data
    collection: AsyncIOMotorCollection = Depends(get_reference_data_collection)
):
    """
    Retrieves a specific reference data category by its unique name.
    Accessible to all authenticated active users.
    """
    category = await collection.find_one({"category_name": category_name})
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference data category '{category_name}' not found."
        )
    
    category["id"] = str(category.pop("_id"))
    return ReferenceDataCategoryResponse(**category)


@router.put("/{category_name}", response_model=ReferenceDataCategoryResponse)
async def update_reference_data_category(
    category_name: str,
    category_update: ReferenceDataCategoryCreate, # Use Create schema as update input
    current_user: UserResponse = Depends(role_required(["admin"])), # Only admins can update categories
    collection: AsyncIOMotorCollection = Depends(get_reference_data_collection)
):
    """
    Updates an existing reference data category by its name.
    Requires 'admin' role.
    """
    existing_category = await collection.find_one({"category_name": category_name})
    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference data category '{category_name}' not found."
        )

    # If the category name is being changed, ensure the new name is not taken
    if category_update.category_name != category_name:
        if await collection.find_one({"category_name": category_update.category_name}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"New category name '{category_update.category_name}' already exists."
            )

    update_data = category_update.model_dump(by_alias=True, exclude_unset=True)
    
    update_result = await collection.update_one(
        {"_id": existing_category["_id"]},
        {"$set": update_data}
    )

    if update_result.modified_count == 0:
        # This could mean the document was found but no changes were made (data was identical)
        # or it wasn't found (but we checked for that above).
        # We can fetch it again to return the current state.
        updated_category = await collection.find_one({"_id": existing_category["_id"]})
        if updated_category:
            updated_category["id"] = str(updated_category.pop("_id"))
            return ReferenceDataCategoryResponse(**updated_category)
        raise HTTPException(status_code=500, detail="Failed to retrieve updated category.")


    updated_category = await collection.find_one({"_id": existing_category["_id"]})
    if updated_category:
        updated_category["id"] = str(updated_category.pop("_id"))
        return ReferenceDataCategoryResponse(**updated_category)
    raise HTTPException(status_code=500, detail="Reference data category updated but could not be retrieved.")


@router.delete("/{category_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference_data_category(
    category_name: str,
    current_user: UserResponse = Depends(role_required(["admin"])), # Only admins can delete categories
    collection: AsyncIOMotorCollection = Depends(get_reference_data_collection)
):
    """
    Deletes a reference data category by its unique name.
    Requires 'admin' role.
    """
    delete_result = await collection.delete_one({"category_name": category_name})

    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference data category '{category_name}' not found."
        )
    return # 204 No Content response