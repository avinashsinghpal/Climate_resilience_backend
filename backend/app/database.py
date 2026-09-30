import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection URL from environment or default to local (for development)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "climate_resilience")

class DatabaseState:
    client: AsyncIOMotorClient = None
    db = None

db_state = DatabaseState()

async def connect_to_mongo():
    db_state.client = AsyncIOMotorClient(MONGO_URL)
    db_state.db = db_state.client[DB_NAME]
    print(f"Connected to MongoDB at {MONGO_URL} database {DB_NAME}")

async def close_mongo_connection():
    if db_state.client:
        db_state.client.close()
        print("Closed MongoDB connection")

def get_database():
    """
    FastAPI dependency to get the database instance.
    """
    return db_state.db
