from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_database
from app.ledger import append_ledger_record, compute_report_hash

router = APIRouter()

# Allowed pollution types — mirrors the frontend PollutionType union exactly
# (frontend/src/types/index.ts).
ALLOWED_POLLUTION_TYPES = Literal[
    "open_waste_burning",
    "crop_burning",
    "construction_dust",
    "industrial_emission",
    "vehicle_smoke",
    "other",
]

REPORTS_COLLECTION = "reports"
MAX_DESCRIPTION_LENGTH = 2000
DEFAULT_RECENT_LIMIT = 20


class ReportSubmit(BaseModel):
    """Submission payload sent by the report form (frontend ReportSubmission)."""

    pollutionType: ALLOWED_POLLUTION_TYPES
    description: str = Field(min_length=10, max_length=MAX_DESCRIPTION_LENGTH)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    blurredLat: float = Field(ge=-90, le=90)
    blurredLng: float = Field(ge=-180, le=180)
    consentGiven: bool


@router.post("")
async def submit_report(report: ReportSubmit, db=Depends(get_database)):
    """Submit a new citizen pollution report."""
    if not report.consentGiven:
        raise HTTPException(status_code=422, detail="Consent is required to submit a report.")

    created_at = datetime.now(timezone.utc)

    # Public document only: raw coordinates are intentionally NOT persisted.
    # The blurred coordinates are the public location shown to all users.
    doc = {
        "pollutionType": report.pollutionType,
        "description": report.description,
        "blurredLat": report.blurredLat,
        "blurredLng": report.blurredLng,
        # Kept for audit (proof of consent) but never returned by read routes.
        "consentGiven": report.consentGiven,
        # Server-generated workflow and timestamp fields.
        "status": "pending",
        "createdAt": created_at,
        # TODO: derive a human-readable area from blurred coords (reverse
        # geocode or named grid) once available; frontend renders it as-is.
        "area": "",
    }

    result = await db[REPORTS_COLLECTION].insert_one(doc)
    report_id = str(result.inserted_id)

    # Anchor the report in the integrity ledger: deterministic SHA-256 over
    # exactly the pollution type, blurred coordinates, description, timestamp.
    data_hash = compute_report_hash(
        pollution_type=report.pollutionType,
        blurred_lat=report.blurredLat,
        blurred_lng=report.blurredLng,
        description=report.description,
        created_at=created_at,
    )
    await append_ledger_record(
        db,
        entity_id=report_id,
        entity_type="report",
        data_hash=data_hash,
    )

    return {
        "id": report_id,
        "status": doc["status"],
        "createdAt": created_at.isoformat(),
        "ledgerHash": data_hash,
    }


@router.get("")
async def get_recent_reports(db=Depends(get_database)):
    """Get recent citizen reports (latest first), public fields only.

    Matches the frontend CitizenReport type so lib/api.ts switches from mock
    data to real data without any frontend changes.
    """
    cursor = (
        db[REPORTS_COLLECTION]
        .find({}, {"consentGiven": 0})  # exclude non-public field
        .sort("createdAt", -1)
        .limit(DEFAULT_RECENT_LIMIT)
    )
    reports = []
    async for doc in cursor:
        created_at = doc["createdAt"]
        if created_at.tzinfo is None:
            # MongoDB stores UTC; motor returns naive datetimes, so tag UTC
            # before serializing (frontend parses ISO strings with Date()).
            created_at = created_at.replace(tzinfo=timezone.utc)
        reports.append(
            {
                "id": str(doc["_id"]),
                "pollutionType": doc["pollutionType"],
                "description": doc["description"],
                # Public location IS the blurred one; raw coords never stored.
                "lat": doc["blurredLat"],
                "lng": doc["blurredLng"],
                "status": doc["status"],
                "createdAt": created_at.isoformat(),
                "area": doc.get("area", ""),
            }
        )
    return reports


@router.get("/recent")
async def get_recent_reports_legacy(db=Depends(get_database)):
    """Get recent citizen reports. (Legacy stub path — kept as-is.)"""
    raise HTTPException(status_code=501, detail="Not Implemented")
