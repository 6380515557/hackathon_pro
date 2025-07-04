# backend/routers/production_data.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, date, timedelta, timezone # Import timezone here

# Import schemas
from ..schemas import (
    ProductionDataCreate,
    ProductionDataResponse,
    ProductionDataUpdate,
    ProductionDataFilter,
    UserResponse,
    DailyProductionSummary,
    MonthlyProductionSummary,
    MachinePerformanceSummary,
    ProductionOverviewSummary,
    ProductProductionSummary,
    OperatorProductionSummary
)

# Import database collection and security dependencies
# CORRECTED IMPORT: Remove get_database and directly import production_data_collection
from ..database import production_data_collection
from ..auth.security import get_current_active_user, role_required

router = APIRouter(
    prefix="/production_data",
    tags=["Production Data"],
)

# Dependency to get the production data collection
async def get_production_data_collection() -> AsyncIOMotorCollection:
    """Dependency function to provide the production data collection."""
    # This now directly returns the imported collection
    return production_data_collection

# --- CRUD Operations for Production Data ---

@router.post("/", response_model=ProductionDataResponse, status_code=status.HTTP_201_CREATED)
async def create_production_record(
    record_in: ProductionDataCreate,
    current_user: UserResponse = Depends(role_required(["admin", "operator"])), # Admins or Operators can create
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection)
):
    """
    Creates a new production data record.
    Requires 'admin' or 'operator' role.
    """
    record_data = record_in.model_dump(by_alias=True, exclude_unset=True)
    result = await collection.insert_one(record_data)
    created_record = await collection.find_one({"_id": result.inserted_id})

    if created_record:
        return ProductionDataResponse(**created_record)
    raise HTTPException(status_code=500, detail="Failed to create production record.")


@router.get("/", response_model=List[ProductionDataResponse])
async def get_all_production_records(
    current_user: UserResponse = Depends(get_current_active_user), # All active users can read
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(100, description="Maximum number of records to return for pagination"),
    # Filtering parameters
    productName: Optional[str] = None,
    machineId: Optional[str] = None,
    operatorId: Optional[str] = None,
    shift: Optional[str] = None,
    minQuantity: Optional[int] = None,
    maxQuantity: Optional[int] = None,
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
):
    """
    Retrieves all production data records with optional filtering and pagination.
    Accessible to all authenticated active users.
    """
    query = {}
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

    if startDate is not None or endDate is not None:
        date_query = {}
        if startDate is not None:
            # For date range, consider the start of the day in UTC
            date_query["$gte"] = datetime.combine(startDate, datetime.min.time(), tzinfo=timezone.utc)
        if endDate is not None:
            # For date range, consider the end of the day in UTC
            date_query["$lte"] = datetime.combine(endDate + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        query["production_date"] = date_query

    records_cursor = collection.find(query).skip(skip).limit(limit).sort("production_date", -1) # Sort by date descending
    all_records = await records_cursor.to_list(length=None)

    return [ProductionDataResponse(**record) for record in all_records]


@router.get("/{record_id}", response_model=ProductionDataResponse)
async def get_production_record_by_id(
    record_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection)
):
    """
    Retrieves a single production record by its ID.
    Accessible to all authenticated active users.
    """
    if not ObjectId.is_valid(record_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid record ID format.")

    record = await collection.find_one({"_id": ObjectId(record_id)})
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production record with ID '{record_id}' not found."
        )
    return ProductionDataResponse(**record)


@router.put("/{record_id}", response_model=ProductionDataResponse)
async def update_production_record(
    record_id: str,
    record_update: ProductionDataUpdate,
    current_user: UserResponse = Depends(role_required(["admin", "operator"])), # Admins or Operators can update
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection)
):
    """
    Updates an existing production data record by its ID.
    Requires 'admin' or 'operator' role.
    """
    if not ObjectId.is_valid(record_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid record ID format.")

    update_data = record_update.model_dump(by_alias=True, exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update.")

    update_result = await collection.update_one(
        {"_id": ObjectId(record_id)},
        {"$set": update_data}
    )

    if update_result.modified_count == 0:
        # Check if record exists but no changes were made (data was identical)
        if await collection.find_one({"_id": ObjectId(record_id)}):
            # Record found, but no modification. Return its current state.
            updated_record = await collection.find_one({"_id": ObjectId(record_id)})
            return ProductionDataResponse(**updated_record)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Production record with ID '{record_id}' not found.")

    updated_record = await collection.find_one({"_id": ObjectId(record_id)})
    if updated_record:
        return ProductionDataResponse(**updated_record)
    raise HTTPException(status_code=500, detail="Production record updated but could not be retrieved.")


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production_record(
    record_id: str,
    current_user: UserResponse = Depends(role_required(["admin"])), # Only Admins can delete
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection)
):
    """
    Deletes a production data record by its ID.
    Requires 'admin' role.
    """
    if not ObjectId.is_valid(record_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid record ID format.")

    delete_result = await collection.delete_one({"_id": ObjectId(record_id)})

    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production record with ID '{record_id}' not found."
        )
    return # 204 No Content response

# --- Aggregation and Reporting Endpoints (for Dashboards) ---

@router.get("/reports/daily_summary", response_model=List[DailyProductionSummary])
async def get_daily_production_summary(
    current_user: UserResponse = Depends(get_current_active_user),
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection),
    start_date: Optional[date] = Query(None, description="Start date for summary (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for summary (YYYY-MM-DD)"),
):
    """
    Generates a daily production summary (total quantity and record count per day).
    Optionally filter by date range.
    Accessible to all authenticated active users.
    """
    pipeline = []
    match_stage = {}

    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        if end_date:
            date_filter["$lt"] = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        match_stage["production_date"] = date_filter
    
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.extend([
        {
            "$group": {
                "_id": { "$dateToString": { "format": "%Y-%m-%d", "date": "$production_date" } },
                "totalQuantity": { "$sum": "$quantityProduced" },
                "numRecords": { "$sum": 1 }
            }
        },
        { "$sort": { "_id": 1 } } # Sort by date ascending
    ])

    summary_cursor = collection.aggregate(pipeline)
    summary_list = await summary_cursor.to_list(length=None)
    return [DailyProductionSummary(**item) for item in summary_list]


@router.get("/reports/monthly_summary", response_model=List[MonthlyProductionSummary])
async def get_monthly_production_summary(
    current_user: UserResponse = Depends(get_current_active_user),
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection),
    year: Optional[int] = Query(None, description="Filter by year"),
):
    """
    Generates a monthly production summary (total quantity and record count per month).
    Optionally filter by year.
    Accessible to all authenticated active users.
    """
    pipeline = []
    match_stage = {}
    
    if year:
        match_stage["production_date"] = {
            "$gte": datetime(year, 1, 1, tzinfo=timezone.utc),
            "$lt": datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        }
    
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.extend([
        {
            "$group": {
                "_id": { "$dateToString": { "format": "%Y-%m", "date": "$production_date" } },
                "totalQuantity": { "$sum": "$quantityProduced" },
                "numRecords": { "$sum": 1 }
            }
        },
        { "$sort": { "_id": 1 } } # Sort by year-month ascending
    ])

    summary_cursor = collection.aggregate(pipeline)
    summary_list = await summary_cursor.to_list(length=None)
    return [MonthlyProductionSummary(**item) for item in summary_list]


@router.get("/reports/machine_performance", response_model=List[MachinePerformanceSummary])
async def get_machine_performance_summary(
    current_user: UserResponse = Depends(get_current_active_user),
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection),
    machine_id: Optional[str] = Query(None, description="Filter by a specific machine ID")
):
    """
    Generates a summary of production performance per machine.
    Accessible to all authenticated active users.
    """
    pipeline = []
    if machine_id:
        pipeline.append({"$match": {"machineId": machine_id}})

    pipeline.extend([
        {
            "$group": {
                "_id": "$machineId",
                "totalQuantity": { "$sum": "$quantityProduced" },
                "numRecords": { "$sum": 1 },
                "avgTimeTakenMinutes": { "$avg": "$timeTakenMinutes" } # Avg of a nullable field is fine
            }
        },
        {
            "$project": {
                "_id": 1,
                "totalQuantity": 1,
                "numRecords": 1,
                "avgTimeTakenMinutes": 1,
                "avgQuantityPerRecord": { "$cond": [{ "$ne": ["$numRecords", 0] }, { "$divide": ["$totalQuantity", "$numRecords"] }, 0] }
            }
        },
        { "$sort": { "totalQuantity": -1 } } # Sort by total quantity descending
    ])

    summary_cursor = collection.aggregate(pipeline)
    summary_list = await summary_cursor.to_list(length=None)
    return [MachinePerformanceSummary(**item) for item in summary_list]


@router.get("/dashboard/overview", response_model=ProductionOverviewSummary)
async def get_production_overview(
    current_user: UserResponse = Depends(get_current_active_user),
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection)
):
    """
    Provides a high-level overview of total production quantity and record count.
    Accessible to all authenticated active users.
    """
    pipeline = [
        {
            "$group": {
                "_id": None, # Group all documents
                "totalQuantityOverall": { "$sum": "$quantityProduced" },
                "totalRecordsOverall": { "$sum": 1 }
            }
        },
        { "$project": { "_id": 0, "totalQuantityOverall": 1, "totalRecordsOverall": 1 } }
    ]
    
    result = await collection.aggregate(pipeline).to_list(length=1)
    if result:
        return ProductionOverviewSummary(**result[0])
    return ProductionOverviewSummary(totalQuantityOverall=0, totalRecordsOverall=0)


@router.get("/dashboard/product_summary", response_model=List[ProductProductionSummary])
async def get_product_production_summary(
    current_user: UserResponse = Depends(get_current_active_user),
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection)
):
    """
    Aggregates production quantity and records per product.
    Accessible to all authenticated active users.
    """
    pipeline = [
        {
            "$group": {
                "_id": "$productName",
                "totalQuantity": { "$sum": "$quantityProduced" },
                "numRecords": { "$sum": 1 }
            }
        },
        { "$sort": { "totalQuantity": -1 } }
    ]
    summary_cursor = collection.aggregate(pipeline)
    summary_list = await summary_cursor.to_list(length=None)
    return [ProductProductionSummary(**item) for item in summary_list]


@router.get("/dashboard/operator_summary", response_model=List[OperatorProductionSummary])
async def get_operator_production_summary(
    current_user: UserResponse = Depends(get_current_active_user),
    collection: AsyncIOMotorCollection = Depends(get_production_data_collection)
):
    """
    Aggregates production quantity and records per operator.
    Accessible to all authenticated active users.
    """
    pipeline = [
        {
            "$group": {
                "_id": "$operatorId",
                "totalQuantity": { "$sum": "$quantityProduced" },
                "numRecords": { "$sum": 1 }
            }
        },
        { "$sort": { "totalQuantity": -1 } }
    ]
    summary_cursor = collection.aggregate(pipeline)
    summary_list = await summary_cursor.to_list(length=None)
    return [OperatorProductionSummary(**item) for item in summary_list]