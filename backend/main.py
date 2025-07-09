# backend/main.py

import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import your database connection functions
from .database import (
    connect_to_mongo, 
    close_mongo_connection,
)

# Import routers
from .auth.router import router as auth_router
from .routers.notifications import router as notifications_router
from .routers.reference_data import router as reference_data_router
from .production_data.router import router as production_data_router
from .routers.reports import router as reports_router # NEW: Import the reports router


app = FastAPI(
    title="Manufacturing Operations API",
    description="API for managing manufacturing production data, users, notifications, and reference data.",
    version="0.1.0",
)

# CORS configuration
origins = [
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Connection Events ---
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# --- Include Routers with Prefixes ---
app.include_router(auth_router, prefix="/api/auth")
app.include_router(notifications_router, prefix="/api/notifications")
app.include_router(reference_data_router, prefix="/api/reference_data")
app.include_router(production_data_router, prefix="/api/production_data")
app.include_router(reports_router, prefix="/api/reports") # NEW: Include reports router


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Manufacturing Operations API!"}
