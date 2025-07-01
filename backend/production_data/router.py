from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Annotated, Optional
from ..database import get_database
from ..schemas import ProductionDataCreate, ProductionDataResponse, ProductionDataUpdate, ProductionDataFilter, UserResponse
from ..auth.router import get_current_user, role_required
from . import crud
from starlette.responses import StreamingResponse # Import StreamingResponse
import io # For creating an in-memory file-like object

router = APIRouter()

@router.post("/", response_model=ProductionDataResponse, status_code=status.HTTP_201_CREATED)
async def create_new_production_entry(
    data: ProductionDataCreate,
    current_user: UserResponse = Depends(role_required(["operator", "supervisor", "admin"])),
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
    filters: Annotated[ProductionDataFilter, Depends()],
    current_user: UserResponse = Depends(get_current_user),
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
    current_user: UserResponse = Depends(role_required(["operator", "supervisor", "admin"])),
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
    current_user: UserResponse = Depends(role_required(["admin", "supervisor", "operator"])),
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

# --- NEW API ENDPOINT: Export CSV ---
@router.get("/export/csv")
async def export_production_data_csv(
    filters: Annotated[ProductionDataFilter, Depends()],
    current_user: UserResponse = Depends(role_required(["supervisor", "admin"])), # Only supervisors and admins can export
    db = Depends(get_database)
):
    """
    Exports filtered production data to a CSV file.
    Requires 'supervisor' or 'admin' role.
    """
    # Fetch data using the existing CRUD function
    entries = await crud.get_production_entries(db, filters, current_user.role, current_user.username)

    # Prepare CSV data in memory
    output = io.StringIO()
    # Write CSV header (using keys from ProductionDataResponse for consistency)
    # Exclude '_id' and 'model_config' from headers, map 'id' to '_id'
    headers = [
        "id", "production_date", "shift", "machineId", "productName",
        "quantityProduced", "remarks", "operatorName", "createdAt"
    ]
    output.write(",".join(headers) + "\n")

    # Write data rows
    for entry in entries:
        # Convert ObjectId to string for CSV
        entry['id'] = str(entry['_id'])
        # Convert datetime to ISO format string for CSV
        entry['createdAt'] = entry['createdAt'].isoformat()
        # Convert date to ISO format string for CSV
        entry['production_date'] = entry['production_date'].isoformat()

        # Ensure all fields are present for consistency, use empty string if None
        row_values = [
            str(entry.get('id', '')),
            str(entry.get('production_date', '')),
            str(entry.get('shift', '')),
            str(entry.get('machineId', '')),
            str(entry.get('productName', '')),
            str(entry.get('quantityProduced', '')),
            str(entry.get('remarks', '')),
            str(entry.get('operatorName', '')),
            str(entry.get('createdAt', ''))
        ]
        # Basic CSV escaping: wrap values with commas in quotes
        escaped_values = [f'"{val}"' if ',' in val else val for val in row_values]
        output.write(",".join(escaped_values) + "\n")

    output.seek(0) # Rewind to the beginning of the stream

    # Return as StreamingResponse
    filename = f"production_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
