# backend/routers/reference_data.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from bson import ObjectId # Required for working with MongoDB's _id

# Correctly import schemas
from ..schemas import ReferenceDataCategoryCreate, ReferenceDataCategoryResponse, UserResponse

# Import database connection and security dependencies
from ..database import get_database # CORRECT: Import get_database
# from ..database import reference_data_collection # REMOVED: Direct collection import
from ..auth.router import get_current_user, role_required # CORRECT: Import get_current_user and role_required

router = APIRouter(
    prefix="/reference_data",
    tags=["Reference Data"],
)

# REMOVED: Dependency to get the reference data collection (no longer needed)
# async def get_reference_data_collection() -> AsyncIOMotorCollection:
#     """Dependency function to provide the reference data collection."""
#     return reference_data_collection

# --- API Endpoints for Reference Data Management ---

@router.post("/", response_model=ReferenceDataCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_reference_data_category(
    category_in: ReferenceDataCategoryCreate,
    current_user: UserResponse = Depends(role_required(["admin"])), # Only admins can create new categories
    db = Depends(get_database) # CORRECT: Use get_database dependency
):
    """
    Creates a new reference data category.
    Requires 'admin' role. Category names must be unique.
    """
    ref_data_collection = db["reference_data"] # CORRECT: Access collection via db
    
    # Check if a category with the same name already exists
    existing_category = await ref_data_collection.find_one({"category_name": category_in.category_name})
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reference data category '{category_in.category_name}' already exists."
        )

    category_data = category_in.model_dump(by_alias=True, exclude_unset=True)
    
    result = await ref_data_collection.insert_one(category_data)
    created_category = await ref_data_collection.find_one({"_id": result.inserted_id})

    if created_category:
        created_category["id"] = str(created_category.pop("_id"))
        return ReferenceDataCategoryResponse(**created_category)
    raise HTTPException(status_code=500, detail="Failed to create reference data category.")


@router.get("/", response_model=List[ReferenceDataCategoryResponse])
async def get_all_reference_data_categories(
    current_user: UserResponse = Depends(get_current_user), # CORRECT: Use get_current_user
    db = Depends(get_database) # CORRECT: Use get_database dependency
):
    """
    Retrieves all available reference data categories.
    Accessible to all authenticated active users.
    """
    ref_data_collection = db["reference_data"] # CORRECT: Access collection via db
    categories_cursor = ref_data_collection.find({})
    all_categories = await categories_cursor.to_list(length=None)

    if not all_categories:
        return []
    
    # Convert ObjectId to string for each category
    return [ReferenceDataCategoryResponse(**{**c, "id": str(c["_id"])}) for c in all_categories]


@router.get("/{category_name}", response_model=ReferenceDataCategoryResponse)
async def get_reference_data_by_name(
    category_name: str,
    current_user: UserResponse = Depends(get_current_user), # CORRECT: Use get_current_user
    db = Depends(get_database) # CORRECT: Use get_database dependency
):
    """
    Retrieves a specific reference data category by its unique name.
    Accessible to all authenticated active users.
    """
    ref_data_collection = db["reference_data"] # CORRECT: Access collection via db
    category = await ref_data_collection.find_one({"category_name": category_name})
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
    db = Depends(get_database) # CORRECT: Use get_database dependency
):
    """
    Updates an existing reference data category by its name.
    Requires 'admin' role.
    """
    ref_data_collection = db["reference_data"] # CORRECT: Access collection via db

    existing_category = await ref_data_collection.find_one({"category_name": category_name})
    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference data category '{category_name}' not found."
        )

    # If the category name is being changed, ensure the new name is not taken
    if category_update.category_name != category_name:
        if await ref_data_collection.find_one({"category_name": category_update.category_name}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"New category name '{category_update.category_name}' already exists."
            )

    update_data = category_update.model_dump(by_alias=True, exclude_unset=True)
    
    update_result = await ref_data_collection.update_one(
        {"_id": existing_category["_id"]},
        {"$set": update_data}
    )

    if update_result.modified_count == 0:
        updated_category = await ref_data_collection.find_one({"_id": existing_category["_id"]})
        if updated_category:
            updated_category["id"] = str(updated_category.pop("_id"))
            return ReferenceDataCategoryResponse(**updated_category) # Return current state
        raise HTTPException(status_code=500, detail="Failed to retrieve updated category.")


    updated_category = await ref_data_collection.find_one({"_id": existing_category["_id"]})
    if updated_category:
        updated_category["id"] = str(updated_category.pop("_id"))
        return ReferenceDataCategoryResponse(**updated_category)
    raise HTTPException(status_code=500, detail="Reference data category updated but could not be retrieved.")


@router.delete("/{category_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference_data_category(
    category_name: str,
    current_user: UserResponse = Depends(role_required(["admin"])), # Only admins can delete categories
    db = Depends(get_database) # CORRECT: Use get_database dependency
):
    """
    Deletes a reference data category by its unique name.
    Requires 'admin' role.
    """
    ref_data_collection = db["reference_data"] # CORRECT: Access collection via db

    delete_result = await ref_data_collection.delete_one({"category_name": category_name})

    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference data category '{category_name}' not found."
        )
    return # 204 No Content response
