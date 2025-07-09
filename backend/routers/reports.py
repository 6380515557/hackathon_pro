# backend/routers/reports.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import date, datetime, timedelta, timezone

from ..database import get_database
from ..schemas import DailyProductionSummary, MonthlyProductionSummary, MachinePerformanceSummary, ProductProductionSummary, OperatorProductionSummary, ProductionOverviewSummary, UserResponse # Import ProductionOverviewSummary
from ..auth.router import role_required

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])

@router.get("/daily-summary", response_model=List[DailyProductionSummary])
async def get_daily_production_summary(
    start_date: Optional[date] = Query(None, description="Start date for the summary (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for the summary (YYYY-MM-DD)"),
    current_user: UserResponse = Depends(role_required(["admin", "supervisor"])),
    db = Depends(get_database)
):
    """
    Retrieves a daily summary of production data.
    Aggregates total quantity produced and number of records per day.
    Requires 'admin' or 'supervisor' role.
    """
    production_collection = db["production_data"]

    pipeline = []

    date_match_query = {}
    if start_date:
        date_match_query["$gte"] = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    if end_date:
        date_match_query["$lte"] = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    if date_match_query:
        pipeline.append({"$match": {"production_date": date_match_query}})

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

    pipeline.append({"$sort": {"_id": 1}})

    summary_cursor = production_collection.aggregate(pipeline)
    daily_summaries = await summary_cursor.to_list(None)

    return [DailyProductionSummary(**summary) for summary in daily_summaries]

@router.get("/monthly-summary", response_model=List[MonthlyProductionSummary])
async def get_monthly_production_summary(
    start_date: Optional[date] = Query(None, description="Start date for the summary (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for the summary (YYYY-MM-DD)"),
    current_user: UserResponse = Depends(role_required(["admin", "supervisor"])),
    db = Depends(get_database)
):
    """
    Retrieves a monthly summary of production data.
    Aggregates total quantity produced and number of records per month.
    Requires 'admin' or 'supervisor' role.
    """
    production_collection = db["production_data"]

    pipeline = []

    # Match stage for date filtering
    date_match_query = {}
    if start_date:
        date_match_query["$gte"] = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    if end_date:
        date_match_query["$lte"] = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    if date_match_query:
        pipeline.append({"$match": {"production_date": date_match_query}})

    # Group stage to aggregate by year-month
    pipeline.append({
        "$group": {
            "_id": {
                "$dateToString": {
                    "format": "%Y-%m", # Group by Year-Month
                    "date": "$production_date"
                }
            },
            "totalQuantity": {"$sum": "$quantityProduced"},
            "numRecords": {"$sum": 1}
        }
    })

    # Sort by year-month
    pipeline.append({"$sort": {"_id": 1}})

    # Execute the aggregation pipeline
    summary_cursor = production_collection.aggregate(pipeline)
    monthly_summaries = await summary_cursor.to_list(None)

    # Convert the results to Pydantic models
    return [MonthlyProductionSummary(**summary) for summary in monthly_summaries]

@router.get("/machine-performance", response_model=List[MachinePerformanceSummary])
async def get_machine_performance_summary(
    start_date: Optional[date] = Query(None, description="Start date for the summary (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for the summary (YYYY-MM-DD)"),
    current_user: UserResponse = Depends(role_required(["admin", "supervisor"])),
    db = Depends(get_database)
):
    """
    Retrieves a summary of production performance per machine.
    Aggregates total quantity, average quantity per record, and average time taken per record.
    Requires 'admin' or 'supervisor' role.
    """
    production_collection = db["production_data"]

    pipeline = []

    # Match stage for date filtering
    date_match_query = {}
    if start_date:
        date_match_query["$gte"] = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    if end_date:
        date_match_query["$lte"] = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    if date_match_query:
        pipeline.append({"$match": {"production_date": date_match_query}})

    # Group stage to aggregate by machineId
    pipeline.append({
        "$group": {
            "_id": "$machineId", # Group by machineId
            "totalQuantity": {"$sum": "$quantityProduced"},
            "numRecords": {"$sum": 1},
            "totalTimeTakenMinutes": {"$sum": "$timeTakenMinutes"} # Sum of time taken
        }
    })

    # Project stage to calculate averages
    pipeline.append({
        "$project": {
            "_id": 0, # Exclude _id from the final output
            "machineId": "$_id", # Rename _id to machineId
            "totalQuantity": 1,
            "numRecords": 1,
            "avgQuantityPerRecord": {
                "$cond": [
                    {"$eq": ["$numRecords", 0]},
                    0,
                    {"$divide": ["$totalQuantity", "$numRecords"]}
                ]
            },
            "avgTimeTakenMinutes": {
                "$cond": [
                    {"$eq": ["$numRecords", 0]},
                    None, # Or 0, depending on desired behavior for no records
                    {"$divide": ["$totalTimeTakenMinutes", "$numRecords"]}
                ]
            }
        }
    })

    # Sort by machineId
    pipeline.append({"$sort": {"machineId": 1}})

    # Execute the aggregation pipeline
    summary_cursor = production_collection.aggregate(pipeline)
    machine_summaries = await summary_cursor.to_list(None)

    # Convert the results to Pydantic models
    return [MachinePerformanceSummary(**summary) for summary in machine_summaries]

@router.get("/product-summary", response_model=List[ProductProductionSummary])
async def get_product_production_summary(
    start_date: Optional[date] = Query(None, description="Start date for the summary (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for the summary (YYYY-MM-DD)"),
    current_user: UserResponse = Depends(role_required(["admin", "supervisor"])),
    db = Depends(get_database)
):
    """
    Retrieves a summary of production data aggregated by product.
    Aggregates total quantity produced and number of records per product.
    Requires 'admin' or 'supervisor' role.
    """
    production_collection = db["production_data"]

    pipeline = []

    # Match stage for date filtering
    date_match_query = {}
    if start_date:
        date_match_query["$gte"] = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    if end_date:
        date_match_query["$lte"] = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    if date_match_query:
        pipeline.append({"$match": {"production_date": date_match_query}})

    # Group stage to aggregate by productName
    pipeline.append({
        "$group": {
            "_id": "$productName", # Group by productName
            "totalQuantity": {"$sum": "$quantityProduced"},
            "numRecords": {"$sum": 1}
        }
    })

    # Project stage to rename _id to productName
    pipeline.append({
        "$project": {
            "_id": 0, # Exclude _id from the final output
            "productName": "$_id", # Rename _id to productName
            "totalQuantity": 1,
            "numRecords": 1
        }
    })

    # Sort by productName
    pipeline.append({"$sort": {"productName": 1}})

    # Execute the aggregation pipeline
    summary_cursor = production_collection.aggregate(pipeline)
    product_summaries = await summary_cursor.to_list(None)

    # Convert the results to Pydantic models
    return [ProductProductionSummary(**summary) for summary in product_summaries]

@router.get("/operator-summary", response_model=List[OperatorProductionSummary])
async def get_operator_production_summary(
    start_date: Optional[date] = Query(None, description="Start date for the summary (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for the summary (YYYY-MM-DD)"),
    current_user: UserResponse = Depends(role_required(["admin", "supervisor"])),
    db = Depends(get_database)
):
    """
    Retrieves a summary of production data aggregated by operator.
    Aggregates total quantity produced and number of records per operator.
    Requires 'admin' or 'supervisor' role.
    """
    production_collection = db["production_data"]

    pipeline = []

    # Match stage for date filtering
    date_match_query = {}
    if start_date:
        date_match_query["$gte"] = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    if end_date:
        date_match_query["$lte"] = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    if date_match_query:
        pipeline.append({"$match": {"production_date": date_match_query}})

    # Group stage to aggregate by operatorId
    pipeline.append({
        "$group": {
            "_id": "$operatorId", # Group by operatorId
            "totalQuantity": {"$sum": "$quantityProduced"},
            "numRecords": {"$sum": 1}
        }
    })

    # Project stage to rename _id to operatorId
    pipeline.append({
        "$project": {
            "_id": 0, # Exclude _id from the final output
            "operatorId": "$_id", # Rename _id to operatorId
            "totalQuantity": 1,
            "numRecords": 1
        }
    })

    # Sort by operatorId
    pipeline.append({"$sort": {"operatorId": 1}})

    # Execute the aggregation pipeline
    summary_cursor = production_collection.aggregate(pipeline)
    operator_summaries = await summary_cursor.to_list(None)

    # Convert the results to Pydantic models
    return [OperatorProductionSummary(**summary) for summary in operator_summaries]

# --- NEW API ENDPOINT: Production Overview Summary ---
@router.get("/overview-summary", response_model=ProductionOverviewSummary) # Note: response_model is a single object, not a list
async def get_production_overview_summary(
    start_date: Optional[date] = Query(None, description="Start date for the summary (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for the summary (YYYY-MM-DD)"),
    current_user: UserResponse = Depends(role_required(["admin", "supervisor"])),
    db = Depends(get_database)
):
    """
    Retrieves a high-level summary of total quantity produced and total number of records
    across all production data within a specified date range.
    Requires 'admin' or 'supervisor' role.
    """
    production_collection = db["production_data"]

    pipeline = []

    # Match stage for date filtering
    date_match_query = {}
    if start_date:
        date_match_query["$gte"] = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    if end_date:
        date_match_query["$lte"] = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

    if date_match_query:
        pipeline.append({"$match": {"production_date": date_match_query}})

    # Group stage to aggregate overall totals (using a fixed _id to get a single document)
    pipeline.append({
        "$group": {
            "_id": None, # Group all documents into a single group
            "totalQuantityOverall": {"$sum": "$quantityProduced"},
            "totalRecordsOverall": {"$sum": 1}
        }
    })

    # Project stage to remove the _id field from the final output
    pipeline.append({
        "$project": {
            "_id": 0,
            "totalQuantityOverall": 1,
            "totalRecordsOverall": 1
        }
    })

    # Execute the aggregation pipeline
    summary_cursor = production_collection.aggregate(pipeline)
    overview_summary = await summary_cursor.to_list(None) # to_list will return a list, even if it has one item

    # If there's a summary, return the first (and only) item.
    # If no records match, overview_summary will be empty, so return a default.
    if overview_summary:
        return ProductionOverviewSummary(**overview_summary[0])
    else:
        # Return a default summary if no data matches the criteria
        return ProductionOverviewSummary(totalQuantityOverall=0, totalRecordsOverall=0)
