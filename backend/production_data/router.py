# backend/production_data/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime, date, timezone # Import timezone
from bson import ObjectId # For working with ObjectIds

from ..database import get_database
from ..schemas import (
    ProductionDataCreate,
    ProductionDataResponse,
    ProductionDataUpdate, # Keep this for future PUT/PATCH
    ProductionDataFilter, # Keep this for GET / with filters
    UserResponse
)
from ..auth.router import role_required # Assuming role_required is in ..auth.router
from starlette.responses import StreamingResponse # For CSV export
import io # For CSV export

router = APIRouter(prefix="/production_data", tags=["Production Data"])

# Helper function to convert MongoDB document to ProductionDataResponse
def production_doc_to_response(doc: dict) -> ProductionDataResponse:
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return ProductionDataResponse(**doc)

@router.post("/", response_model=ProductionDataResponse, status_code=status.HTTP_201_CREATED)
async def create_production_entry(
    production_in: ProductionDataCreate,
    current_user: UserResponse = Depends(role_required(["admin", "supervisor", "operator"])), # All these roles can create
    db = Depends(get_database)
):
    """
    Create a new production data entry.
    Requires 'admin', 'supervisor', or 'operator' role.
    """
    production_collection = db["production_data"]

    production_data_dict = production_in.model_dump(by_alias=True, exclude_unset=True)
    
    # Ensure production_date is stored as UTC datetime
    if isinstance(production_data_dict.get("production_date"), date):
        production_data_dict["production_date"] = datetime.combine(
            production_data_dict["production_date"],
            datetime.min.time(), # Set to start of day
            tzinfo=timezone.utc # Ensure it's timezone-aware UTC
        )
    elif isinstance(production_data_dict.get("production_date"), datetime) and production_data_dict["production_date"].tzinfo is None:
        # If it's a naive datetime, assume UTC and make it timezone-aware
        production_data_dict["production_date"] = production_data_dict["production_date"].replace(tzinfo=timezone.utc)

    # Add creation timestamp and operator name
    production_data_dict["createdAt"] = datetime.utcnow().replace(tzinfo=timezone.utc)
    production_data_dict["operatorName"] = current_user.username # Store the username of the operator

    result = await production_collection.insert_one(production_data_dict)
    created_entry = await production_collection.find_one({"_id": result.inserted_id})

    if created_entry:
        return production_doc_to_response(created_entry)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create production entry")

@router.get("/", response_model=List[ProductionDataResponse])
async def get_all_production_data(
    productName: Optional[str] = Query(None, description="Filter by product name"),
    machineId: Optional[str] = Query(None, description="Filter by machine ID"),
    operatorId: Optional[str] = Query(None, description="Filter by operator ID"),
    shift: Optional[str] = Query(None, description="Filter by shift (Morning, Afternoon, Night)"),
    minQuantity: Optional[int] = Query(None, ge=0, description="Filter by minimum quantity produced"),
    maxQuantity: Optional[int] = Query(None, ge=0, description="Filter by maximum quantity produced"),
    startDate: Optional[date] = Query(None, description="Filter by production start date (YYYY-MM-DD)"),
    endDate: Optional[date] = Query(None, description="Filter by production end date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Number of records to skip (for pagination)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: UserResponse = Depends(role_required(["admin", "supervisor", "operator", "viewer"])), # All roles can view
    db = Depends(get_database)
):
    """
    Retrieve a list of production data entries with optional filters and pagination.
    Accessible by all authenticated users.
    """
    production_collection = db["production_data"]
    query = {}

    # Role-based access for 'operator' to see only their own entries
    if "operator" in current_user.roles and not any(role in ["admin", "supervisor"] for role in current_user.roles):
        query["operatorName"] = current_user.username # Assuming operatorName is stored in the document

    if productName:
        query["productName"] = productName
    if machineId:
        query["machineId"] = machineId
    if operatorId: # This filter applies only if the user is not a restricted operator
        query["operatorId"] = operatorId
    if shift:
        query["shift"] = shift

    if minQuantity is not None or maxQuantity is not None:
        quantity_query = {}
        if minQuantity is not None:
            quantity_query["$gte"] = minQuantity
        if maxQuantity is not None:
            quantity_query["$lte"] = maxQuantity
        query["quantityProduced"] = quantity_query

    if startDate or endDate:
        date_query = {}
        if startDate:
            date_query["$gte"] = datetime.combine(startDate, datetime.min.time(), tzinfo=timezone.utc)
        if endDate:
            date_query["$lte"] = datetime.combine(endDate, datetime.max.time(), tzinfo=timezone.utc)
        query["production_date"] = date_query

    # Fetch data from MongoDB
    # Sort by creation date descending to get most recent first
    production_entries_cursor = production_collection.find(query).sort("createdAt", -1).skip(skip).limit(limit)
    production_data = await production_entries_cursor.to_list(None)

    # Convert documents to ProductionDataResponse schemas
    return [production_doc_to_response(doc) for doc in production_data]

# --- NEW API ENDPOINT: Get Single Production Data Entry by ID ---
@router.get("/{entry_id}", response_model=ProductionDataResponse)
async def get_production_entry_by_id(
    entry_id: str,
    current_user: UserResponse = Depends(role_required(["admin", "supervisor", "operator", "viewer"])), # All roles can view
    db = Depends(get_database)
):
    """
    Retrieve a single production data entry by ID.
    Accessible by all authenticated users. Operators can only view their own entries.
    """
    production_collection = db["production_data"]

    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entry ID format")

    query = {"_id": ObjectId(entry_id)}

    # Role-based access for 'operator' to see only their own entries
    if "operator" in current_user.roles and not any(role in ["admin", "supervisor"] for role in current_user.roles):
        query["operatorName"] = current_user.username # Assuming operatorName is stored in the document

    entry_doc = await production_collection.find_one(query)

    if entry_doc:
        return production_doc_to_response(entry_doc)
    
    # Differentiate between not found and unauthorized if an operator tries to access another's entry
    if "operator" in current_user.roles and not any(role in ["admin", "supervisor"] for role in current_user.roles):
        # If an operator searched for an ID that exists but doesn't belong to them
        # We can't easily distinguish if it's "not found" or "unauthorized" without another query.
        # For security, it's better to return 404 to avoid leaking information about other entries.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production entry not found.")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production entry not found.")

# --- NEW API ENDPOINT: Update Production Data Entry by ID ---
@router.put("/{entry_id}", response_model=ProductionDataResponse)
async def update_production_entry(
    entry_id: str,
    production_update: ProductionDataUpdate,
    current_user: UserResponse = Depends(role_required(["admin", "supervisor", "operator"])), # Operator can update their own
    db = Depends(get_database)
):
    """
    Update an existing production data entry by ID.
    Requires 'admin', 'supervisor', or 'operator' role. Operators can only update their own entries.
    """
    production_collection = db["production_data"]

    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entry ID format")

    query = {"_id": ObjectId(entry_id)}

    # Role-based access for 'operator' to update only their own entries
    if "operator" in current_user.roles and not any(role in ["admin", "supervisor"] for role in current_user.roles):
        query["operatorName"] = current_user.username

    update_data = production_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    # Handle datetime conversion for production_date if present in update
    if "production_date" in update_data and isinstance(update_data["production_date"], date):
        update_data["production_date"] = datetime.combine(
            update_data["production_date"],
            datetime.min.time(),
            tzinfo=timezone.utc
        )
    elif "production_date" in update_data and isinstance(update_data["production_date"], datetime) and update_data["production_date"].tzinfo is None:
        update_data["production_date"] = update_data["production_date"].replace(tzinfo=timezone.utc)

    result = await production_collection.update_one(
        query, # Use the query with ownership check
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production entry not found or unauthorized to update")

    updated_entry_doc = await production_collection.find_one(query) # Fetch using the same query
    if updated_entry_doc:
        return production_doc_to_response(updated_entry_doc)
    
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated production entry")

# --- NEW API ENDPOINT: Delete Production Data Entry by ID ---
@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production_entry(
    entry_id: str,
    current_user: UserResponse = Depends(role_required(["admin", "supervisor", "operator"])), # Operator can delete their own
    db = Depends(get_database)
):
    """
    Delete a production data entry by ID.
    Requires 'admin', 'supervisor', or 'operator' role. Operators can only delete their own entries.
    """
    production_collection = db["production_data"]

    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entry ID format")

    query = {"_id": ObjectId(entry_id)}

    # Role-based access for 'operator' to delete only their own entries
    if "operator" in current_user.roles and not any(role in ["admin", "supervisor"] for role in current_user.roles):
        query["operatorName"] = current_user.username

    result = await production_collection.delete_one(query) # Use the query with ownership check

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production entry not found or unauthorized to delete")
    
    return {} # 204 No Content response

# --- CSV Export API (already existing, but moved below CRUD for logical flow) ---
@router.get("/export/csv")
async def export_production_data_csv(
    productName: Optional[str] = Query(None, description="Filter by product name"),
    machineId: Optional[str] = Query(None, description="Filter by machine ID"),
    operatorId: Optional[str] = Query(None, description="Filter by operator ID"),
    shift: Optional[str] = Query(None, description="Filter by shift (Morning, Afternoon, Night)"),
    minQuantity: Optional[int] = Query(None, ge=0, description="Filter by minimum quantity produced"),
    maxQuantity: Optional[int] = Query(None, ge=0, description="Filter by maximum quantity produced"),
    startDate: Optional[date] = Query(None, description="Filter by production start date (YYYY-MM-DD)"),
    endDate: Optional[date] = Query(None, description="Filter by production end date (YYYY-MM-DD)"),
    current_user: UserResponse = Depends(role_required(["supervisor", "admin"])), # Only supervisors and admins can export
    db = Depends(get_database)
):
    """
    Exports filtered production data to a CSV file.
    Requires 'supervisor' or 'admin' role.
    """
    production_collection = db["production_data"]
    query = {}

    # Role-based access for 'operator' to see only their own entries (though export is admin/supervisor only)
    # This check is mostly redundant here due to role_required, but good for consistency if roles change
    if "operator" in current_user.roles and not any(role in ["admin", "supervisor"] for role in current_user.roles):
        query["operatorName"] = current_user.username

    if productName:
        query["productName"] = productName
    if machineId:
        query["machineId"] = machineId
    if operatorId:
        query["operatorId"] = operatorId
    if shift:
        query["shift"] = shift

    if minQuantity is not None or maxQuantity is not None:
        quantity_query = {}
        if minQuantity is not None:
            quantity_query["$gte"] = minQuantity
        if maxQuantity is not None:
            quantity_query["$lte"] = maxQuantity
        query["quantityProduced"] = quantity_query

    if startDate or endDate:
        date_query = {}
        if startDate:
            date_query["$gte"] = datetime.combine(startDate, datetime.min.time(), tzinfo=timezone.utc)
        if endDate:
            date_query["$lte"] = datetime.combine(endDate, datetime.max.time(), tzinfo=timezone.utc)
        query["production_date"] = date_query

    # Fetch all matching data for export (no skip/limit)
    production_entries_cursor = production_collection.find(query).sort("createdAt", -1)
    entries = await production_entries_cursor.to_list(None)

    # Prepare CSV data in memory
    output = io.StringIO()
    
    # Write CSV header
    headers = [
        "id", "production_date", "shift", "machineId", "productName",
        "quantityProduced", "remarks", "operatorName", "createdAt", "comments", "timeTakenMinutes" # Added comments and timeTakenMinutes
    ]
    output.write(",".join(headers) + "\n")

    # Write data rows
    for entry in entries:
        # Convert ObjectId to string for CSV
        entry_id = str(entry.get('_id', ''))
        # Convert datetime to ISO format string for CSV, handle missing
        production_date_str = entry.get('production_date', '').isoformat() if isinstance(entry.get('production_date'), datetime) else str(entry.get('production_date', ''))
        createdAt_str = entry.get('createdAt', '').isoformat() if isinstance(entry.get('createdAt'), datetime) else str(entry.get('createdAt', ''))

        # Ensure all fields are present for consistency, use empty string if None
        row_values = [
            entry_id,
            production_date_str,
            str(entry.get('shift', '')),
            str(entry.get('machineId', '')),
            str(entry.get('productName', '')),
            str(entry.get('quantityProduced', '')),
            str(entry.get('remarks', '')), # Use 'remarks'
            str(entry.get('operatorName', '')),
            createdAt_str,
            str(entry.get('comments', '')), # Still include 'comments' for backward compatibility if data exists
            str(entry.get('timeTakenMinutes', ''))
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
