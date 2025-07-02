# backend/database.py

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import pathlib # <--- NEW: Import pathlib

# Get the absolute path to the directory where database.py resides
# Then construct the path to the .env file
# Assuming .env is in the same directory as database.py (i.e., backend/)
dotenv_path = pathlib.Path(__file__).parent.absolute() / ".env"
load_dotenv(dotenv_path=dotenv_path) # <--- CHANGE: Pass the explicit path

MONGO_DETAILS = os.getenv("MONGO_URI")

# Add a print statement to verify what MONGO_DETAILS is
print(f"Attempting to connect to MongoDB with URI: {MONGO_DETAILS}")


# Global variables to hold the MongoDB client and database instance
client: AsyncIOMotorClient = None
database = None

async def connect_to_mongo():
    global client, database
    try:
        # Check if MONGO_DETAILS is None or empty after loading
        if not MONGO_DETAILS:
            raise ValueError("MONGO_URI environment variable is not set or loaded correctly.")

        client = AsyncIOMotorClient(MONGO_DETAILS)
        # Choose your database name (ensure this matches your Atlas setup if specified in URI)
        # If your Atlas URI includes a database name like ...mongodb.net/my_database?...,
        # then client.get_database() will default to that. Otherwise, specify it here.
        database = client.get_database("production_db") # <--- Make sure "production_db" is the database name you want to use/create in Atlas

        # Optional: Ensure unique index for username when the app starts
        # This operation will fail if the connection itself is not established
        await database["users"].create_index("username", unique=True)
        print("Connected to MongoDB!") # <--- Add success message

    except Exception as e:
        print(f"Could not connect to MongoDB: {e}")
        # Optionally re-raise or handle more gracefully in a real app
        raise # Re-raise the exception to stop startup if connection fails

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