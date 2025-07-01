from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import Optional, Literal, Annotated, Any
from datetime import date, datetime, timezone
from bson import ObjectId
from pydantic_core import core_schema # <--- NEW: Import core_schema

# Custom Pydantic type for MongoDB's ObjectId
# This is the Pydantic V2 recommended way for custom types
class PyObjectId(ObjectId): # <--- PyObjectId is now a class inheriting ObjectId
    @classmethod
    def __get_validators__(cls):
        # This part is for legacy Pydantic V1 compatibility if needed,
        # but with __get_pydantic_core_schema__ it might be redundant.
        # However, keeping it doesn't hurt.
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> ObjectId:
        """
        Validator function for PyObjectId.
        Handles converting string or existing ObjectId to ObjectId instance.
        """
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId format")

    # <--- NEW: Implement __get_pydantic_core_schema__ for Pydantic V2
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        """
        Generate the Pydantic CoreSchema for PyObjectId.
        This tells Pydantic how to handle this type during schema generation.
        It defines a string type that also accepts ObjectId instances.
        """
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(), # Treat it as a string for schema generation
            serialization=core_schema.to_string_ser_schema(), # Serialize to string
        )

    model_config = ConfigDict(arbitrary_types_allowed=True) # Allow custom types


# --- Auth Schemas ---
class UserBase(BaseModel):
    username: str
    role: Literal["admin", "supervisor", "operator"]

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: PyObjectId = Field(alias="_id")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str}
    )

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[Literal["admin", "supervisor", "operator"]] = None


# --- Production Data Schemas ---
class ProductionDataCreate(BaseModel):
    production_date: Annotated[date, Field(..., example="2025-07-01", description="Date of production (YYYY-MM-DD)")]
    # --- CHANGE THIS LINE ---
    shift: Annotated[Literal["Morning", "Afternoon", "Night"], Field(..., example="Morning", description="Production shift")]
    # --- END CHANGE ---
    machineId: str = Field(..., example="DISA-3", description="ID of the machine used")
    productName: str = Field(..., example="Gear Casting", description="Name or type of the product produced")
    quantityProduced: int = Field(..., ge=0, example=150, description="Number of units produced (must be non-negative)")
    remarks: Optional[str] = Field(None, example="Minor mold defect on 5 units", description="Any additional comments or issues")

    model_config = ConfigDict()


class ProductionDataResponse(ProductionDataCreate):
    """Schema for returning production data, including ID and backend-generated fields."""
    id: PyObjectId = Field(alias="_id")
    operatorName: str = Field(..., example="Ravi Kumar", description="Name of the operator who entered the data")
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of when the record was created (UTC)")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str, datetime: lambda dt: dt.isoformat()}
    )


class ProductionDataUpdate(BaseModel):
    date: Optional[date] = None
    shift: Optional[Literal["Morning", "Afternoon", "Night"]] = None
    machineId: Optional[str] = None
    productName: Optional[str] = None
    quantityProduced: Optional[int] = None
    remarks: Optional[str] = None

    model_config = ConfigDict(
        # json_encoders={ObjectId: str}
    )

class ProductionDataFilter(BaseModel):
    startDate: Optional[date] = None
    endDate: Optional[date] = None
    machineId: Optional[str] = None
    shift: Optional[Literal["Morning", "Afternoon", "Night"]] = None
    operatorName: Optional[str] = None
    
    model_config = ConfigDict(
        #json_encoders={ObjectId: str}
    )

# backend/schemas.py

# ... (your existing imports, including from datetime import date, datetime, timezone)
# ... (your existing PyObjectId, User, ProductionDataCreate, ProductionDataResponse etc.)

# --- NEW SCHEMAS FOR REPORTING & ANALYTICS ---

class DailyProductionSummary(BaseModel):
    # CHANGE THIS LINE: Rename 'date' field to 'summary_date'
    summary_date: Annotated[date, Field(..., alias="_id", description="Date of the summary")]
    totalQuantity: int = Field(..., description="Total quantity produced on this date")
    numRecords: int = Field(..., description="Number of production records on this date")

    model_config = ConfigDict(populate_by_name=True) # Allows mapping '_id' from MongoDB to 'summary_date'

# The MonthlyProductionSummary and MachinePerformanceSummary classes should be fine
# as their _id aliases ('month', 'machineId') are strings and don't clash with types.
class MonthlyProductionSummary(BaseModel):
    month: str = Field(..., alias="_id", description="Month of the summary (YYYY-MM)")
    # ... rest of fields ...

class MachinePerformanceSummary(BaseModel):
    machineId: str = Field(..., alias="_id", description="Machine ID")
    # ... rest of fields ...