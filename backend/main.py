from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Import CORS
from .database import connect_to_mongo, close_mongo_connection
from .auth.router import router as auth_router
from .production_data.router import router as production_data_router # Import production data routes
#hello
app = FastAPI(
    title="Production Data Management API",
    description="API for digitalizing production data entry in factories.",
    version="1.0.0",
)

# Configure CORS to allow your frontend to communicate with your backend
# For development, you might allow all origins. In production, restrict to your frontend's domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Event handlers for connecting/disconnecting MongoDB
@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    print("Connected to MongoDB!")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    print("Disconnected from MongoDB.")

# Include routers for different parts of your API
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(production_data_router, prefix="/api/production-data", tags=["Production Data"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Production Data Management API!"}

# To run this from the 'your_project_name' root directory:
# uvicorn backend.main:app --reload

# To run this from inside the 'backend' directory:
# uvicorn main:app --reload