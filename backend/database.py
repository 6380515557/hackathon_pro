from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

MONGO_DETAILS = os.getenv("MONGO_URI")

# Global variables to hold the MongoDB client and database instance
client: AsyncIOMotorClient = None
database = None

async def connect_to_mongo():
    global client, database
    try:
        client = AsyncIOMotorClient(MONGO_DETAILS)
        # Choose your database name
        database = client.get_database("production_db")
        # Optional: Ensure unique index for username when the app starts
        await database["users"].create_index("username", unique=True)
    except Exception as e:
        print(f"Could not connect to MongoDB: {e}")
        # Optionally re-raise or handle more gracefully in a real app
        raise

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")

def get_database() -> AsyncIOMotorClient:
    """Dependency to get the database instance."""
    if database is None:
        raise Exception("Database not connected. Call connect_to_mongo() first.")
    return database