from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.database import get_database

router = APIRouter()

class ReportSubmit(BaseModel):
    pollutionType: str
    description: str
    lat: float
    lng: float
    blurredLat: float
    blurredLng: float
    consentGiven: bool

@router.get("/recent")
async def get_recent_reports(db=Depends(get_database)):
    """Get recent citizen reports."""
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.post("")
async def submit_report(report: ReportSubmit, db=Depends(get_database)):
    """Submit a new citizen pollution report."""
    raise HTTPException(status_code=501, detail="Not Implemented")
