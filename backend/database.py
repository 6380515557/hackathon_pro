# backend/database.py

import os
import pathlib
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = pathlib.Path(__file__).parent.absolute() / ".env"
load_dotenv(dotenv_path=dotenv_path)

MONGO_DETAILS = os.getenv("MONGO_URI")

print(f"Attempting to connect to MongoDB with URI: {MONGO_DETAILS}")

# Global variables to hold the MongoDB client, database instance, and collections
db_client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None
production_data_collection: AsyncIOMotorCollection = None
users_collection: AsyncIOMotorCollection = None
reference_data_collection: AsyncIOMotorCollection = None
notifications_collection: AsyncIOMotorCollection = None # <--- ADDED THIS LINE HERE!

async def connect_to_mongo():
    """Establishes connection to MongoDB and initializes collections."""
    # Ensure notifications_collection is in the global statement
    global db_client, db, production_data_collection, users_collection, reference_data_collection, notifications_collection
    try:
        if not MONGO_DETAILS:
            raise ValueError("MONGO_URI environment variable is not set or loaded correctly.")

        db_client = AsyncIOMotorClient(MONGO_DETAILS)
        await db_client.admin.command('ping')
        print("MongoDB connection successful!")

        db = db_client.get_database("production_db") # Use your desired database name

        # Initialize collections
        users_collection = db.get_collection("users")
        production_data_collection = db.get_collection("production_data")
        reference_data_collection = db.get_collection("reference_data")
        notifications_collection = db.get_collection("notifications")

        # Optional: Ensure unique index for username when the app starts
        await users_collection.create_index("username", unique=True)
        print("MongoDB collections initialized and indexes created.")

    except Exception as e:
        print(f"Could not connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Closes the MongoDB connection."""
    global db_client
    if db_client:
        db_client.close()
        print("MongoDB connection closed.")

# The `get_database()` function is no longer needed as collections are imported directly.
# If you still have dependencies using `get_database`, you need to update them
# to import the specific collection directly (e.g., `users_collection`).