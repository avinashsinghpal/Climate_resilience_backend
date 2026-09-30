from fastapi import APIRouter, HTTPException, Depends, Query
from app.database import get_database
from app.utils.security import require_official_user

router = APIRouter(dependencies=[Depends(require_official_user)])

@router.get("")
async def get_sensors(
    protocol: str = Query("all"),
    status: str = Query("all"),
    area: str = Query("all"),
    db=Depends(get_database)
):
    """Get list of sensors with optional filters."""
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.get("/{sensor_id}/readings")
async def get_sensor_readings(sensor_id: str, db=Depends(get_database)):
    """Get historical readings for a specific sensor."""
    raise HTTPException(status_code=501, detail="Not Implemented")
