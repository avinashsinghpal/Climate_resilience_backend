"""
Integrity ledger helpers.

Computes deterministic SHA-256 hashes over canonicalized data and appends
tamper-evident records to the `integrity_ledger` collection.

Used by routers (e.g. reports) that want their data anchored in the integrity
ledger. The existing integrity router is left untouched.
"""

import hashlib
import json
from datetime import datetime, timezone

# Ledger record proof statuses (mirrors frontend ProofStatus: "Verified" | "Pending" | "Failed")
PROOF_STATUS_PENDING = "Pending"

LEDGER_COLLECTION = "integrity_ledger"


def canonical_json(payload: dict) -> bytes:
    """
    Serialize a dict to deterministic bytes: sorted keys, compact separators,
    UTF-8. Used as the pre-image for hashing so identical data always
    produces an identical hash.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_hash(payload: dict) -> str:
    """
    Deterministic SHA-256 over the canonical JSON of `payload`.
    """
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def compute_report_hash(
    pollution_type: str,
    blurred_lat: float,
    blurred_lng: float,
    description: str,
    created_at: datetime,
) -> str:
    """
    Deterministic hash for a citizen report, over exactly the fields the
    platform anchors: pollution type, blurred coordinates, description and
    timestamp.
    """
    payload = {
        "pollutionType": pollution_type,
        "blurredLat": blurred_lat,
        "blurredLng": blurred_lng,
        "description": description,
        "createdAt": created_at.isoformat(),
        # Domain separator so report hashes can't be confused with hashes of
        # other data kinds that may later join the ledger.
        "domain": "citizen_report",
        "version": 1,
    }
    return compute_hash(payload)


async def append_ledger_record(
    db,
    *,
    entity_id: str,
    entity_type: str,
    data_hash: str,
    anchor_reference: str = "",
    pm25: float = 0.0,
    sensor_id: str = "",
) -> dict:
    """
    Append one record to the integrity ledger collection.

    Mirrors the shape of the frontend `LedgerRecord` type:
    id / sensorId / timestamp / readingHash / proofStatus / anchorReference /
    pm25, plus `entityType`/`entityId` to track what was hashed.

    Returns the inserted ledger document (with its _id).
    """
    now = datetime.now(timezone.utc)
    doc = {
        # sensorId stays the canonical reference field for sensor readings;
        # citizen reports anchor via entityType="report" + entityId=<report id>
        "sensorId": sensor_id,
        "entityType": entity_type,
        "entityId": entity_id,
        "timestamp": now,
        "readingHash": data_hash,
        "proofStatus": PROOF_STATUS_PENDING,
        "anchorReference": anchor_reference,
        "pm25": pm25,
    }
    result = await db[LEDGER_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc
