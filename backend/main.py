# backend/main.py

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Import your database connection functions and global collection variables
from .database import (
    connect_to_mongo, 
    close_mongo_connection,
)

# Import routers
from .auth.router import router as auth_router
from .routers.notifications import router as notifications_router
from .routers.reference_data import router as reference_data_router

# UNCOMMENT AND ADD THIS LINE to include production data router!
from .routers.production_data import router as production_data_router


app = FastAPI(
    title="Manufacturing Operations API", # Updated title
    description="API for managing manufacturing production data, users, notifications, and reference data.",
    version="0.1.0",
)

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000", # Example for a React/Vue/Angular frontend
    # Add your frontend domain here when deployed
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

# --- Include Routers ---
app.include_router(auth_router)
app.include_router(notifications_router)
app.include_router(reference_data_router)
app.include_router(production_data_router) # <--- UNCOMMENTED AND ADDED THIS LINE!


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Manufacturing Operations API!"} # Updated message