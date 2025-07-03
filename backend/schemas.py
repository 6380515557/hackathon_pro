# backend/schemas.py

from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Any, Annotated, Dict
from pydantic import BaseModel, Field, ConfigDict, FieldValidationInfo, field_validator
from bson import ObjectId
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from enum import Enum


# --- MongoDB ObjectId Custom Type ---
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema: dict):
        field_schema.update(type="string")

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: Any
    ) -> JsonSchemaValue:
        return handler(core_schema.str_schema())


# --- User/Auth Schemas ---
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    full_name: Optional[str] = Field(None, max_length=100)
    # Define roles here, e.g., ["admin", "operator", "viewer"]
    roles: List[str] = Field(["viewer"], description="List of roles assigned to the user.")

class UserResponse(BaseModel):
    id: PyObjectId = Field(alias="_id", default=None)
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = False
    is_active: bool = True # Added for consistency with FastAPI security
    roles: List[str] = Field([], description="List of roles assigned to the user.") # Include roles in response

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True, json_schema_extra={
        "example": {
            "username": "johndoe",
            "email": "johndoe@example.com",
            "full_name": "John Doe",
            "disabled": False,
            "is_active": True,
            "roles": ["operator"]
        }
    })

class UserUpdate(BaseModel):
    email: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    disabled: Optional[bool] = None
    roles: Optional[List[str]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "new.email@example.com",
                "full_name": "John D. updated",
                "is_active": True,
                "roles": ["admin", "operator"]
            }
        },
        extra="forbid" # Disallow extra fields
    )


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = [] # Include scopes for finer-grained permissions


# --- Notification Schemas ---

class NotificationSeverity(str, Enum):
    """Defines the severity levels for notifications."""
    INFO = "info"
    WARNING = "warning" # Changed from "Earning" to be more generic for notifications
    ERROR = "error"     # Changed from "Withdrawal"
    CRITICAL = "critical" # Changed from "Recharge"
    
class NotificationBase(BaseModel):
    """Base schema for a notification."""
    user_id: Optional[str] = None # Can be None for global notifications, or specific user ID (MongoDB ObjectId as string)
    username: Optional[str] = None # Store username for easier access if user_id is ObjectId
    message: str
    severity: NotificationSeverity = NotificationSeverity.INFO
    read: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""
    # timestamp and read will be defaulted upon creation

class NotificationResponse(NotificationBase):
    """Schema for returning a notification, including its ID."""
    id: str = Field(alias="_id", description="MongoDB ObjectId as string.") # Map MongoDB's _id to 'id' for API response

    model_config = ConfigDict(
        populate_by_name=True, # Allow population by field name or alias
        arbitrary_types_allowed=True, # Allow ObjectId type from MongoDB
        json_encoders = {datetime: lambda dt: dt.isoformat()} # For proper datetime serialization
    )


# --- Production Data Schemas ---

class ProductionDataCreate(BaseModel):
    productName: str
    machineId: str
    quantityProduced: int
    operatorId: str
    production_date: datetime # Storing as datetime for ISO format in MongoDB
    shift: Optional[str] = None
    comments: Optional[str] = None
    timeTakenMinutes: Optional[int] = None # New field for time tracking

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "productName": "Widget A",
            "machineId": "M-001",
            "quantityProduced": 150,
            "operatorId": "OP-789",
            "production_date": "2024-06-25T10:00:00Z", # Example ISO 8601 UTC
            "shift": "Day",
            "comments": "Smooth run",
            "timeTakenMinutes": 120
        }
    })

class ProductionDataResponse(ProductionDataCreate):
    id: PyObjectId = Field(alias="_id")

    model_config = ConfigDict(arbitrary_types_allowed=True, json_encoders={ObjectId: str}, populate_by_name=True)

class ProductionDataUpdate(BaseModel):
    productName: Optional[str] = None
    machineId: Optional[str] = None
    quantityProduced: Optional[int] = None
    operatorId: Optional[str] = None
    production_date: Optional[datetime] = None
    shift: Optional[str] = None
    comments: Optional[str] = None
    timeTakenMinutes: Optional[int] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "quantityProduced": 160,
            "comments": "Adjusted settings, improved output."
        }
    })

class ProductionDataFilter(BaseModel):
    productName: Optional[str] = None
    machineId: Optional[str] = None
    operatorId: Optional[str] = None
    shift: Optional[str] = None
    minQuantity: Optional[int] = None
    maxQuantity: Optional[int] = None
    startDate: Optional[date] = None # Filter by date only
    endDate: Optional[date] = None   # Filter by date only

# --- Schemas for Reporting & Analytics ---

class DailyProductionSummary(BaseModel):
    summary_date: date = Field(..., alias="_id", description="Date of the summary (YYYY-MM-DD)")
    totalQuantity: int = Field(..., description="Total quantity produced on this date")
    numRecords: int = Field(..., description="Number of production records on this date")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator('summary_date', mode='before')
    @classmethod
    def parse_summary_date(cls, v: Any) -> date:
        if isinstance(v, date):
            return v
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            raise ValueError(f"Invalid date format for summary_date: {v}. Expected YYYY-MM-DD string or date object.")

class MonthlyProductionSummary(BaseModel):
    year_month: str = Field(..., alias="_id", description="Year and Month of the summary (YYYY-MM)")
    totalQuantity: int = Field(..., description="Total quantity produced in this month")
    numRecords: int = Field(..., description="Number of production records in this month")

    model_config = ConfigDict(populate_by_name=True)

class MachinePerformanceSummary(BaseModel):
    machineId: str = Field(..., alias="_id", description="Machine Identifier")
    totalQuantity: int = Field(..., description="Total quantity produced by this machine")
    avgQuantityPerRecord: float = Field(..., description="Average quantity produced per record by this machine")
    avgTimeTakenMinutes: Optional[float] = Field(None, description="Average time taken per record by this machine (minutes)")
    numRecords: int = Field(..., description="Total number of records for this machine")

    model_config = ConfigDict(populate_by_name=True)

# --- Schemas for Dashboard Specific APIs ---

class ProductionOverviewSummary(BaseModel):
    """Provides a high-level summary of total production over a period."""
    totalQuantityOverall: int = Field(..., description="Total quantity produced across the entire period")
    totalRecordsOverall: int = Field(..., description="Total number of production records across the entire period")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "totalQuantityOverall": 12500,
            "totalRecordsOverall": 250
        }
    })

class ProductProductionSummary(BaseModel):
    """Aggregates production quantity per product."""
    productName: str = Field(..., alias="_id", description="Name of the product")
    totalQuantity: int = Field(..., description="Total quantity produced for this product")
    numRecords: int = Field(..., description="Number of records for this product")

    model_config = ConfigDict(populate_by_name=True, json_schema_extra={
        "example": {
            "productName": "Widget A",
            "totalQuantity": 5000,
            "numRecords": 100
        }
    })

class OperatorProductionSummary(BaseModel):
    """Aggregates production quantity per operator."""
    operatorId: str = Field(..., alias="_id", description="Identifier of the operator")
    totalQuantity: int = Field(..., description="Total quantity produced by this operator")
    numRecords: int = Field(..., description="Number of records for this operator")

    model_config = ConfigDict(populate_by_name=True, json_schema_extra={
        "example": {
            "operatorId": "OP-123",
            "totalQuantity": 3000,
            "numRecords": 60
        }
    })


# --- Corrected Reference Data Schemas ---

class ReferenceDataItem(BaseModel):
    """
    Schema for a single item within a reference data category.
    This allows for flexible key-value pairs or more complex data.
    """
    key: str = Field(..., min_length=1, description="Unique identifier for the reference data item within its category (e.g., 'active', 'completed').")
    value: str = Field(..., min_length=1, description="Display value for the reference data item (e.g., 'Active', 'Completed').")
    description: Optional[str] = Field(None, description="Optional description of the reference data item.")
    
    model_config = ConfigDict(extra="allow") 


class ReferenceDataCategoryCreate(BaseModel):
    """
    Schema for creating a new reference data category.
    A category holds a list of ReferenceDataItem.
    """
    category_name: str = Field(..., min_length=1, description="Unique name for the reference data category (e.g., 'MachineType', 'ProductStatus', 'ShiftDefinitions').")
    description: Optional[str] = Field(None, description="Optional description for the category.")
    items: List[ReferenceDataItem] = Field(default_factory=list, description="List of items within this reference data category.")

class ReferenceDataCategoryResponse(ReferenceDataCategoryCreate):
    """
    Schema for returning a reference data category, including its ID.
    """
    id: str = Field(alias="_id", description="MongoDB ObjectId as string.")

    model_config = ConfigDict(
        populate_by_name=True, # Allow population by field name or alias
        arbitrary_types_allowed=True, # Allow ObjectId type from MongoDB
        json_encoders = {datetime: lambda dt: dt.isoformat()} # For proper datetime serialization
    )