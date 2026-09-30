from fastapi import APIRouter, HTTPException, Depends, Query
from app.database import get_database
from app.utils.security import require_official_user

router = APIRouter(dependencies=[Depends(require_official_user)])

@router.get("")
async def get_forecast(horizon: int = Query(72), db=Depends(get_database)):
    """Get air quality forecast for a given horizon."""
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.get("/drivers")
async def get_forecast_drivers(db=Depends(get_database)):
    """Get the driving factors for the current forecast."""
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.get("/satellite")
async def get_satellite_grid(layer: str = Query("aod"), db=Depends(get_database)):
    """Get satellite data grid for a specific layer."""
    raise HTTPException(status_code=501, detail="Not Implemented")
