# backend/routers/production_data.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, date, timedelta, timezone

from ..database import get_database
from ..schemas import (
    ProductionDataCreate, ProductionDataResponse, ProductionDataUpdate, ProductionDataFilter,
    DailyProductionSummary, MonthlyProductionSummary, MachinePerformanceSummary,
    ProductionOverviewSummary, ProductProductionSummary, OperatorProductionSummary # NEW IMPORTS
)
from ..auth.oauth2 import get_current_active_user # Ensure this import is correct

router = APIRouter(
    prefix="/production",
    tags=["Production Data & Analytics"],
    responses={404: {"description": "Not found"}},
)

# Helper function for date filtering in pipelines
def _get_date_match_stage(start_date: Optional[date], end_date: Optional[date]) -> dict:
    date_match = {}
    if start_date:
        # Convert date to datetime at start of day (UTC)
        date_match["$gte"] = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    if end_date:
        # Convert date to datetime at end of day (UTC)
        date_match["$lte"] = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    if date_match:
        return {"$match": {"production_date": date_match}}
    return {}

# --- CRUD Operations (Existing or Placeholder) ---

@router.post("/", response_model=ProductionDataResponse, status_code=status.HTTP_201_CREATED,
             summary="Create Production Record", description="Adds a new production data record.")
async def create_production_data(
    production_data: ProductionDataCreate,
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user)
):
    collection = db["production_data"]
    # Ensure production_date is stored in UTC
    if production_data.production_date.tzinfo is None:
        production_data.production_date = production_data.production_date.replace(tzinfo=timezone.utc)
    new_record = await collection.insert_one(production_data.model_dump(by_name=True))
    created_record = await collection.find_one({"_id": new_record.inserted_id})
    return created_record

@router.get("/", response_model=List[ProductionDataResponse],
            summary="Get All Production Records (with filters)",
            description="Retrieves all production records, with optional filtering by various criteria and date range.")
async def get_all_production_data(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
    productName: Optional[str] = Query(None, description="Filter by product name"),
    machineId: Optional[str] = Query(None, description="Filter by machine ID"),
    operatorId: Optional[str] = Query(None, description="Filter by operator ID"),
    shift: Optional[str] = Query(None, description="Filter by shift (e.g., Day, Night)"),
    minQuantity: Optional[int] = Query(None, description="Minimum quantity produced"),
    maxQuantity: Optional[int] = Query(None, description="Maximum quantity produced"),
    startDate: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Inclusive."),
    endDate: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Inclusive."),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination")
):
    collection = db["production_data"]
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
        query["quantityProduced"] = {}
        if minQuantity is not None:
            query["quantityProduced"]["$gte"] = minQuantity
        if maxQuantity is not None:
            query["quantityProduced"]["$lte"] = maxQuantity

    if startDate is not None or endDate is not None:
        query["production_date"] = {}
        if startDate:
            query["production_date"]["$gte"] = datetime.combine(startDate, datetime.min.time(), tzinfo=timezone.utc)
        if endDate:
            query["production_date"]["$lte"] = datetime.combine(endDate, datetime.max.time(), tzinfo=timezone.utc)

    # Sort by production_date in descending order for most recent first
    records = await collection.find(query).sort("production_date", -1).skip(skip).limit(limit).to_list(None)
    return records

@router.get("/{record_id}", response_model=ProductionDataResponse,
            summary="Get Production Record by ID", description="Retrieves a single production record by its unique ID.")
async def get_production_data_by_id(
    record_id: str,
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user)
):
    collection = db["production_data"]
    if not isinstance(record_id, str) or not record_id:
        raise HTTPException(status_code=400, detail="Invalid record ID format.")
    try:
        obj_id = ObjectId(record_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    record = await collection.find_one({"_id": obj_id})
    if record:
        return record
    raise HTTPException(status_code=404, detail="Production record not found")

@router.put("/{record_id}", response_model=ProductionDataResponse,
            summary="Update Production Record", description="Updates an existing production data record by its ID.")
async def update_production_data(
    record_id: str,
    production_data_update: ProductionDataUpdate,
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user)
):
    collection = db["production_data"]
    try:
        obj_id = ObjectId(record_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    update_data = {k: v for k, v in production_data_update.model_dump(by_name=True).items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update.")

    # If production_date is updated, ensure it's stored in UTC
    if "production_date" in update_data and update_data["production_date"].tzinfo is None:
        update_data["production_date"] = update_data["production_date"].replace(tzinfo=timezone.utc)

    result = await collection.update_one({"_id": obj_id}, {"$set": update_data})
    if result.modified_count == 1:
        updated_record = await collection.find_one({"_id": obj_id})
        return updated_record
    raise HTTPException(status_code=404, detail="Production record not found or no changes made")

@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete Production Record", description="Deletes a production data record by its ID.")
async def delete_production_data(
    record_id: str,
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user)
):
    collection = db["production_data"]
    try:
        obj_id = ObjectId(record_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    result = await collection.delete_one({"_id": obj_id})
    if result.deleted_count == 1:
        return
    raise HTTPException(status_code=404, detail="Production record not found")

# --- Analytics & Reporting Endpoints (Existing) ---

@router.get(
    "/summary/daily",
    response_model=List[DailyProductionSummary],
    summary="Get Daily Production Summary",
    description="Aggregates production data to provide daily summaries of quantity and record count within an optional date range."
)
async def get_daily_production_summary(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Inclusive."),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Inclusive.")
):
    collection = db["production_data"]
    pipeline = []

    date_match_stage = _get_date_match_stage(start_date, end_date)
    if date_match_stage:
        pipeline.append(date_match_stage)

    pipeline.append({
        "$group": {
            "_id": {
                "$dateToString": {
                    "format": "%Y-%m-%d",
                    "date": "$production_date"
                }
            },
            "totalQuantity": {"$sum": "$quantityProduced"},
            "numRecords": {"$sum": 1}
        }
    })
    pipeline.append({"$sort": {"_id": 1}}) # Sort by date

    result = await collection.aggregate(pipeline).to_list(None)
    return result

@router.get(
    "/summary/monthly",
    response_model=List[MonthlyProductionSummary],
    summary="Get Monthly Production Summary",
    description="Aggregates production data to provide monthly summaries of quantity and record count within an optional date range."
)
async def get_monthly_production_summary(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Inclusive."),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Inclusive.")
):
    collection = db["production_data"]
    pipeline = []

    date_match_stage = _get_date_match_stage(start_date, end_date)
    if date_match_stage:
        pipeline.append(date_match_stage)

    pipeline.append({
        "$group": {
            "_id": {
                "year": {"$year": "$production_date"},
                "month": {"$month": "$production_date"}
            },
            "totalQuantity": {"$sum": "$quantityProduced"},
            "numRecords": {"$sum": 1}
        }
    })
    pipeline.append({
        "$project": {
            "_id": 0, # Exclude the default _id
            "year_month": { # Format year and month as YYYY-MM string
                "$concat": [
                    {"$toString": "$_id.year"},
                    "-",
                    {"$cond": { # Add leading zero for single-digit months
                        "if": {"$lt": ["$_id.month", 10]},
                        "then": {"$concat": ["0", {"$toString": "$_id.month"}]},
                        "else": {"$toString": "$_id.month"}
                    }}
                ]
            },
            "totalQuantity": 1,
            "numRecords": 1
        }
    })
    pipeline.append({"$sort": {"year_month": 1}})

    result = await collection.aggregate(pipeline).to_list(None)
    return result

@router.get(
    "/summary/machine_performance",
    response_model=List[MachinePerformanceSummary],
    summary="Get Machine Performance Summary",
    description="Aggregates production data to provide performance metrics per machine, including total quantity, average quantity per record, and average time taken, within an optional date range."
)
async def get_machine_performance_summary(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Inclusive."),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Inclusive.")
):
    collection = db["production_data"]
    pipeline = []

    date_match_stage = _get_date_match_stage(start_date, end_date)
    if date_match_stage:
        pipeline.append(date_match_stage)

    pipeline.append({
        "$group": {
            "_id": "$machineId",
            "totalQuantity": {"$sum": "$quantityProduced"},
            "avgQuantityPerRecord": {"$avg": "$quantityProduced"},
            "avgTimeTakenMinutes": {"$avg": "$timeTakenMinutes"}, # Will be null if timeTakenMinutes is always null
            "numRecords": {"$sum": 1}
        }
    })
    pipeline.append({"$sort": {"_id": 1}}) # Sort by machineId

    result = await collection.aggregate(pipeline).to_list(None)
    return result

# --- NEW Dashboard Specific APIs ---

@router.get(
    "/dashboard/overview",
    response_model=ProductionOverviewSummary,
    summary="Get Overall Production Overview",
    description="Provides total quantity and total number of records for the entire dataset or within a specified date range, for dashboard display."
)
async def get_overall_production_overview(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Inclusive."),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Inclusive.")
):
    collection = db["production_data"]
    pipeline = []

    date_match_stage = _get_date_match_stage(start_date, end_date)
    if date_match_stage:
        pipeline.append(date_match_stage)

    pipeline.append({
        "$group": {
            "_id": None, # Group all documents into a single group
            "totalQuantityOverall": {"$sum": "$quantityProduced"},
            "totalRecordsOverall": {"$sum": 1}
        }
    })
    pipeline.append({
        "$project": {
            "_id": 0, # Exclude the default _id from the response
            "totalQuantityOverall": 1,
            "totalRecordsOverall": 1
        }
    })

    result = await collection.aggregate(pipeline).to_list(None)

    if not result:
        # Return a default summary if no data matches the criteria
        return ProductionOverviewSummary(totalQuantityOverall=0, totalRecordsOverall=0)
    return result[0] # There will only be one document in the result list

@router.get(
    "/dashboard/by_product",
    response_model=List[ProductProductionSummary],
    summary="Get Production Summary by Product",
    description="Aggregates production data to provide total quantity and record count for each product within an optional date range, ideal for product performance dashboards."
)
async def get_production_by_product(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Inclusive."),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Inclusive.")
):
    collection = db["production_data"]
    pipeline = []

    date_match_stage = _get_date_match_stage(start_date, end_date)
    if date_match_stage:
        pipeline.append(date_match_stage)

    pipeline.append({
        "$group": {
            "_id": "$productName",
            "totalQuantity": {"$sum": "$quantityProduced"},
            "numRecords": {"$sum": 1}
        }
    })
    pipeline.append({"$sort": {"totalQuantity": -1}}) # Sort by total quantity descending

    result = await collection.aggregate(pipeline).to_list(None)
    return result

@router.get(
    "/dashboard/by_operator",
    response_model=List[OperatorProductionSummary],
    summary="Get Production Summary by Operator",
    description="Aggregates production data to provide total quantity and record count for each operator within an optional date range, useful for operator performance dashboards."
)
async def get_production_by_operator(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Inclusive."),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Inclusive.")
):
    collection = db["production_data"]
    pipeline = []

    date_match_stage = _get_date_match_stage(start_date, end_date)
    if date_match_stage:
        pipeline.append(date_match_stage)

    pipeline.append({
        "$group": {
            "_id": "$operatorId",
            "totalQuantity": {"$sum": "$quantityProduced"},
            "numRecords": {"$sum": 1}
        }
    })
    pipeline.append({"$sort": {"totalQuantity": -1}}) # Sort by total quantity descending

    result = await collection.aggregate(pipeline).to_list(None)
    return result