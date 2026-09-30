import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection URL from environment or default to local (for development)
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://avinash24013:231avinash@cluster0.rkrxoah.mongodb.net/?appName=Cluster0")
DB_NAME = os.getenv("DB_NAME", "climate_resilience")

class DatabaseState:
    client: AsyncIOMotorClient = None
    db = None

db_state = DatabaseState()

async def connect_to_mongo():
    db_state.client = AsyncIOMotorClient(MONGO_URL)
    db_state.db = db_state.client[DB_NAME]
    print(f"Connected to MongoDB at {MONGO_URL} database {DB_NAME}")
    await ensure_indexes(db_state.db)


async def ensure_indexes(db) -> None:
    """
    Create indexes needed by the API. Best-effort: failures are logged and
    swallowed so a read-only or unreachable DB never blocks app startup.
    """
    from pymongo.errors import PyMongoError

    try:
        await db["reports"].create_index("createdAt")
        await db["integrity_ledger"].create_index("entityId")
        await db["integrity_ledger"].create_index("timestamp")
    except PyMongoError as exc:
        print(f"Warning: could not ensure indexes: {exc}")

async def close_mongo_connection():
    if db_state.client:
        db_state.client.close()
        print("Closed MongoDB connection")

def get_database():
    """
    FastAPI dependency to get the database instance.
    """
    return db_state.db
