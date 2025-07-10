# backend/main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# Import your database connection functions
from .database import (
    connect_to_mongo,
    close_mongo_connection,
    ensure_unique_indexes, # Ensure this function is in your database.py
)

# Import all your routers
# Using 'from .routers import users' and 'users.router' is cleaner
from .routers import users
from .routers import notifications
from .routers import reference_data
from .routers.production_data import router as production_data_router
from .routers import reports
from .auth.router import router as auth_router


# --- Define the FastAPI app instance ONCE ---
app = FastAPI(
    title="Manufacturing Operations API",
    description="API for managing manufacturing production data, users, notifications, and reference data.",
    version="0.1.0",
)
# --- END FastAPI app definition ---


# --- CORS Configuration ---
origins = [
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
    "http://127.0.0.1:3000",
    # Add any other origins your frontend might run on
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"], # Allows all headers
)


# --- Database Connection Events ---
@app.on_event("startup")
async def startup_db_client():
    print("Connecting to MongoDB...")
    await connect_to_mongo()
    await ensure_unique_indexes() # Ensure unique indexes are created on startup
    print("Application startup complete.")


@app.on_event("shutdown")
async def shutdown_db_client():
    print("Closing MongoDB connection...")
    await close_mongo_connection()


# --- Include Routers with Prefixes ---
# Use consistent prefixes and tags for better OpenAPI documentation
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"]) # Using users.router
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
app.include_router(reference_data.router, prefix="/reference-data", tags=["Reference Data"])
app.include_router(production_data_router, prefix="/production-data", tags=["Production Data"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Manufacturing Operations API! Visit /docs for API documentation."}