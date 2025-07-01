# backend/routers/production_data.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import date, datetime, timedelta, timezone # Ensure datetime and timezone are imported

from ..dependencies import get_database, get_current_active_user
from ..schemas import (
    ProductionDataCreate, ProductionDataResponse, ProductionDataUpdate, ProductionDataFilter,
    # NEW IMPORTS FOR REPORTING
    DailyProductionSummary, MonthlyProductionSummary, MachinePerformanceSummary
)
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

router = APIRouter(prefix="/production_data", tags=["Production Data"])

# --- Keep your existing CRUD routes for ProductionData here ---
# (e.g., POST /, GET /, GET /{id}, PUT /{id}, DELETE /{id})

# --- NEW REPORTING & ANALYTICS APIs ---

@router.get(
    "/summary/daily",
    response_model=List[DailyProductionSummary],
    summary="Get Daily Production Summary",
    description="Aggregates production data to provide daily summaries of quantity and record count within an optional date range.",
    response_description="A list of daily production summaries."
)
async def get_daily_production_summary(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user), # This ensures the route is protected
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Inclusive."),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Inclusive.")
):
    collection = db["production_data"]
    pipeline = []

    # Match by date range if provided
    date_match = {}
    if start_date:
        # Convert start_date to datetime at the beginning of the day (UTC)
        date_match["$gte"] = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    if end_date:
        # Convert end_date to datetime at the end of the day (UTC)
        date_match["$lte"] = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    if date_match:
        # Use 'production_date' field from your schema
        pipeline.append({"$match": {"production_date": date_match}})

    # Group by date and calculate total quantity and number of records
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

    # Sort by date
    pipeline.append({"$sort": {"_id": 1}})

    result = await collection.aggregate(pipeline).to_list(None)

    # Convert _id string back to date object for Pydantic validation (DailyProductionSummary)
    # The MongoDB $dateToString outputs a string, Pydantic needs a date object
    for item in result:
        item["_id"] = datetime.strptime(item["_id"], "%Y-%m-%d").date()

    return result


@router.get(
    "/summary/monthly",
    response_model=List[MonthlyProductionSummary],
    summary="Get Monthly Production Summary",
    description="Aggregates production data to provide monthly summaries of quantity and record count within an optional date range.",
    response_description="A list of monthly production summaries."
)
async def get_monthly_production_summary(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user), # Protected route
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Inclusive."),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Inclusive.")
):
    collection = db["production_data"]
    pipeline = []

    # Match by date range if provided
    date_match = {}
    if start_date:
        date_match["$gte"] = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    if end_date:
        date_match["$lte"] = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    if date_match:
        pipeline.append({"$match": {"production_date": date_match}})

    # Group by month and calculate total quantity and number of records
    pipeline.append({
        "$group": {
            "_id": {
                "$dateToString": {
                    "format": "%Y-%m", # Format for Year-Month
                    "date": "$production_date"
                }
            },
            "totalQuantity": {"$sum": "$quantityProduced"},
            "numRecords": {"$sum": 1}
        }
    })

    # Sort by month
    pipeline.append({"$sort": {"_id": 1}})

    result = await collection.aggregate(pipeline).to_list(None)
    return result


@router.get(
    "/summary/machine",
    response_model=List[MachinePerformanceSummary],
    summary="Get Machine Production Performance",
    description="Aggregates production data to show performance metrics per machine, optionally within a date range or for a specific machine.",
    response_description="A list of machine production summaries."
)
async def get_machine_performance_summary(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_active_user), # Protected route
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD). Inclusive."),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD). Inclusive."),
    machine_id: Optional[str] = Query(None, description="Filter by a specific Machine ID")
):
    collection = db["production_data"]
    pipeline = []

    # Match by criteria (date range and/or specific machineId)
    match_stage = {}
    if start_date:
        match_stage["production_date"] = {"$gte": datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)}
    if end_date:
        # Use setdefault to handle the case where production_date is already in match_stage
        match_stage.setdefault("production_date", {})["$lte"] = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
    if machine_id:
        match_stage["machineId"] = machine_id

    if match_stage:
        pipeline.append({"$match": match_stage})

    # Group by machineId and calculate aggregates
    pipeline.append({
        "$group": {
            "_id": "$machineId",
            "totalQuantity": {"$sum": "$quantityProduced"},
            "numRecords": {"$sum": 1},
            "averageQuantityPerRecord": {"$avg": "$quantityProduced"}
        }
    })

    # Sort by machineId
    pipeline.append({"$sort": {"_id": 1}})

    result = await collection.aggregate(pipeline).to_list(None)
    return result