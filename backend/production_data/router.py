from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Annotated, Optional
from ..database import get_database
from ..schemas import ProductionDataCreate, ProductionDataResponse, ProductionDataUpdate, ProductionDataFilter, UserResponse
from ..auth.router import get_current_user, role_required
from . import crud # Import the crud operations

router = APIRouter()

@router.post("/", response_model=ProductionDataResponse, status_code=status.HTTP_201_CREATED)
async def create_new_production_entry(
    data: ProductionDataCreate,
    current_user: UserResponse = Depends(role_required(["operator", "supervisor", "admin"])), # Only these roles can create
    db = Depends(get_database)
):
    """
    Create a new production data entry.
    Requires 'operator', 'supervisor', or 'admin' role.
    """
    new_entry = await crud.create_production_entry(db, data, current_user.username)
    if new_entry:
        return ProductionDataResponse(**new_entry)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create production entry")

@router.get("/", response_model=List[ProductionDataResponse])
async def get_all_production_entries(
    filters: Annotated[ProductionDataFilter, Depends()], # Use Pydantic model for query params
    current_user: UserResponse = Depends(get_current_user), # All roles can get entries (with restrictions)
    db = Depends(get_database)
):
    """
    Retrieve all production data entries, with optional filters.
    'admin' and 'supervisor' can view all; 'operator' can view their own.
    """
    entries = await crud.get_production_entries(db, filters, current_user.role, current_user.username)
    return [ProductionDataResponse(**entry) for entry in entries]

@router.get("/{entry_id}", response_model=ProductionDataResponse)
async def get_production_entry(
    entry_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Retrieve a single production data entry by ID.
    Access restricted based on user role and ownership.
    """
    entry = await crud.get_production_entry_by_id(db, entry_id, current_user.role, current_user.username)
    if entry:
        return ProductionDataResponse(**entry)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production entry not found or unauthorized access")

@router.put("/{entry_id}", response_model=ProductionDataResponse)
async def update_production_entry(
    entry_id: str,
    data: ProductionDataUpdate,
    current_user: UserResponse = Depends(role_required(["operator", "supervisor", "admin"])), # Can update if they created it or higher role
    db = Depends(get_database)
):
    """
    Update an existing production data entry by ID.
    Requires 'operator', 'supervisor', or 'admin' role, with ownership check for 'operator'.
    """
    updated_entry = await crud.update_production_entry(db, entry_id, data, current_user.role, current_user.username)
    if updated_entry:
        return ProductionDataResponse(**updated_entry)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production entry not found or unauthorized to update")

@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production_entry(
    entry_id: str,
    current_user: UserResponse = Depends(role_required(["admin", "supervisor", "operator"])), # Can delete if they created it or higher role
    db = Depends(get_database)
):
    """
    Delete a production data entry by ID.
    Requires 'admin', 'supervisor', or 'operator' role, with ownership check for 'operator'.
    """
    deleted = await crud.delete_production_entry(db, entry_id, current_user.role, current_user.username)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production entry not found or unauthorized to delete")
    return {"message": "Production entry deleted successfully"}