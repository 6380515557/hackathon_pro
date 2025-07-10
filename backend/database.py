# backend/database.py

import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, CollectionInvalid
from dotenv import load_dotenv

load_dotenv()

MONGO_DETAILS = os.getenv("MONGO_DETAILS")
if not MONGO_DETAILS:
    raise ValueError("MONGO_DETAILS environment variable not set. Please set it in your .env file.")

# ...
DATABASE_NAME = os.getenv("DATABASE_NAME", "production_tracker_db") # <--- Make sure this has your actual DB name
# ...
# --- END ADDITION ---

client = None
database = None

async def connect_to_mongo():
    """Establishes connection to MongoDB."""
    global client, database
    try:
        print(f"Attempting to connect to MongoDB with URI: {MONGO_DETAILS}")
        client = AsyncIOMotorClient(MONGO_DETAILS)
        await client.admin.command('ping') # Test connection

        # --- MODIFIED LINE ---
        database = client[DATABASE_NAME] # Explicitly select the database using the name from .env
        # --- END MODIFIED LINE ---

        print("Successfully connected to MongoDB!")
    except ServerSelectionTimeoutError as err:
        print(f"Could not connect to MongoDB (Server Selection Timeout): {err}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during MongoDB connection: {e}")
        raise

async def close_mongo_connection():
    """Closes the MongoDB connection."""
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")

def get_database():
    """Returns the MongoDB database instance."""
    global database
    if database is None:
        raise Exception("Database not initialized. Call connect_to_mongo() first.")
    return database

async def ensure_unique_indexes():
    """
    Ensures that necessary unique indexes are created in MongoDB.
    Currently, creates a unique index on 'username' in the 'users' collection.
    """
    db = get_database()
    try:
        await db["users"].create_index("username", unique=True)
        print("Ensured unique index on 'users.username'")
    except CollectionInvalid as e:
        print(f"Error ensuring unique index (CollectionInvalid): {e}")
    except Exception as e:
        print(f"An unexpected error occurred while ensuring indexes: {e}")