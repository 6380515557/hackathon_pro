# backend/database.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB connection details
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "production_tracker_db") # Default database name

# Global client and database instances
client: AsyncIOMotorClient = None
database = None

async def connect_to_mongo():
    """Establishes connection to MongoDB."""
    global client, database
    try:
        print(f"Attempting to connect to MongoDB with URI: {MONGO_URI}")
        client = AsyncIOMotorClient(MONGO_URI)
        await client.admin.command('ping') # Test connection
        database = client[DATABASE_NAME]
        print("Successfully connected to MongoDB!")

        # Optional: Create unique index for username on startup if it doesn't exist
        # This ensures usernames are unique
        try:
            await database["users"].create_index("username", unique=True)
            print("Ensured unique index on 'users.username'")
        except Exception as e:
            print(f"Could not create unique index on users.username (might already exist): {e}")

    except ServerSelectionTimeoutError as err:
        print(f"Could not connect to MongoDB: {err}")
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
    if database is None:
        # This case should ideally not happen if connect_to_mongo is called on startup
        # but provides a fallback or indicates an issue with startup sequence
        raise Exception("Database not initialized. Call connect_to_mongo() first.")
    return database
