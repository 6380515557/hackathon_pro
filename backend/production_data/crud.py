from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional, Dict, Any
from bson import ObjectId
from ..schemas import ProductionDataCreate, ProductionDataUpdate, ProductionDataFilter
from datetime import datetime, date

async def create_production_entry(db: AsyncIOMotorClient, data: ProductionDataCreate, operator_name: str) -> Dict:
    """Creates a new production data entry."""
    production_data_collection = db["production_data"]
    # Convert Pydantic model to dictionary, add operatorName and createdAt
    data_dict = data.model_dump()
    data_dict["operatorName"] = operator_name
    data_dict["createdAt"] = datetime.utcnow() # Store creation timestamp

    result = await production_data_collection.insert_one(data_dict)
    created_entry = await production_data_collection.find_one({"_id": result.inserted_id})
    return created_entry

async def get_production_entries(db: AsyncIOMotorClient, filters: ProductionDataFilter, current_user_role: str, current_username: str) -> List[Dict]:
    """Retrieves production data entries with optional filtering, respecting user roles."""
    production_data_collection = db["production_data"]
    query = {}

    # Apply filters if provided
    if filters.startDate:
        # MongoDB date queries often use ISODate, so ensure proper comparison
        if "createdAt" not in query:
            query["createdAt"] = {}
        query["createdAt"]["$gte"] = datetime.combine(filters.startDate, datetime.min.time()) # Start of day

    if filters.endDate:
        if "createdAt" not in query:
            query["createdAt"] = {}
        query["createdAt"]["$lte"] = datetime.combine(filters.endDate, datetime.max.time()) # End of day

    if filters.machineId:
        query["machineId"] = filters.machineId

    if filters.shift:
        query["shift"] = filters.shift

    if filters.operatorName:
        query["operatorName"] = filters.operatorName

    # Role-based access control for viewing data
    if current_user_role == "operator":
        # Operators can only see their own entries
        query["operatorName"] = current_username
    # Admins and supervisors can see all (no additional query filter needed)

    cursor = production_data_collection.find(query).sort("createdAt", -1) # Sort by most recent first
    return [entry async for entry in cursor]

async def get_production_entry_by_id(db: AsyncIOMotorClient, entry_id: str, current_user_role: str, current_username: str) -> Optional[Dict]:
    """Retrieves a single production data entry by ID, respecting user roles."""
    production_data_collection = db["production_data"]
    try:
        obj_id = ObjectId(entry_id)
    except Exception:
        return None # Invalid ObjectId format

    entry = await production_data_collection.find_one({"_id": obj_id})

    if entry:
        # Role-based access check
        if current_user_role == "operator" and entry.get("operatorName") != current_username:
            return None # Operator cannot view others' entries
        return entry
    return None

async def update_production_entry(db: AsyncIOMotorClient, entry_id: str, data: ProductionDataUpdate, current_user_role: str, current_username: str) -> Optional[Dict]:
    """Updates an existing production data entry, respecting user roles."""
    production_data_collection = db["production_data"]
    try:
        obj_id = ObjectId(entry_id)
    except Exception:
        return None

    # Retrieve existing entry to check permissions
    existing_entry = await production_data_collection.find_one({"_id": obj_id})
    if not existing_entry:
        return None

    # Only operator who created it or admin/supervisor can update
    if current_user_role == "operator" and existing_entry.get("operatorName") != current_username:
        return None # Operator cannot update others' entries

    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None} # Only update provided fields

    if update_data:
        await production_data_collection.update_one({"_id": obj_id}, {"$set": update_data})
        updated_entry = await production_data_collection.find_one({"_id": obj_id})
        return updated_entry
    return existing_entry # No updates made, return original

async def delete_production_entry(db: AsyncIOMotorClient, entry_id: str, current_user_role: str, current_username: str) -> bool:
    """Deletes a production data entry, respecting user roles."""
    production_data_collection = db["production_data"]
    try:
        obj_id = ObjectId(entry_id)
    except Exception:
        return False # Invalid ObjectId format

    # Retrieve existing entry to check permissions
    existing_entry = await production_data_collection.find_one({"_id": obj_id})
    if not existing_entry:
        return False

    # Only admin/supervisor can delete, or the operator who created it
    if current_user_role == "operator" and existing_entry.get("operatorName") != current_username:
        return False # Operator cannot delete others' entries

    result = await production_data_collection.delete_one({"_id": obj_id})
    return result.deleted_count == 1