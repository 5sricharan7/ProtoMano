"""Task 4A — Welfare intelligence: historical data retrieval service.

Collects one authorized personnel's longitudinal welfare/workload history from
the EXISTING MongoDB collections into a single deterministic, chronological,
sanitized envelope.

Separation of concerns: this layer only reads storage.  It is deliberately
separate from feature engineering (``lib/feature_engineering.py``) and model
inference (``lib/inference.py``) — it never derives features and never runs the
model.

Authorization contract (mirrors the Phase 3 RBAC gates at the service boundary
for defense in depth):
- WELFARE_OFFICER may retrieve an authorized individual's welfare history.
- PERSONNEL can never retrieve another person's history via this service.
- COMMANDER remains aggregate-only and is refused here.

Sensitive-data rule: responses never include passwords, JWTs, secrets, raw
credentials or internal model artifacts.  Stored risk assessments are minimized
exactly like ``OfficerAssessment`` (the 44-feature vector, ``date_key``,
``is_latest`` and ``confidence_basis`` are stripped), and every payload is
recursively scrubbed of credential-like keys.

Missing vs zero-valued data: ``present`` marks whether any document was found
for the personnel in a collection.  Missing data is never fabricated; zero or
null record values are still returned as real historical data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from lib.db import db

# Fixed section order — the response dict preserves insertion order.
COLLECTION_ORDER = (
    "wellness_logs",
    "workload_records",
    "deployment_history",
    "leave_requests",
    "risk_assessments",
)

# Recursive payload scrub: any mapping key matching one of these tokens is
# dropped before the record leaves the service.  Defense in depth — welfare
# payloads contain voluntary wellness/workload data, never credentials.
_SENSITIVE_KEY_TOKENS = (
    "password",
    "passwd",
    "jwt",
    "token",
    "secret",
    "cookie",
    "authorization",
    "credential",
    "apikey",
    "api_key",
    "private_key",
)

# Static personnel fields a welfare officer may see.  Auth-only or unknown
# fields are never forwarded, even if a personnel document carries extras.
_PERSONNEL_SAFE_FIELDS = (
    "id",
    "name",
    "service_number",
    "rank",
    "unit",
    "posting",
    "created_at",
    "is_demo_data",
)

# Wrapper fields produced by the shared record-creation helper; flattened away
# so the wrapped payload is what the officer sees.
_RECORD_INTERNAL_FIELDS = {"_id", "id", "personnel_id", "created_at", "timestamp"}

# Internal/technical assessment fields stripped exactly like OfficerAssessment.
_ASSESSMENT_INTERNAL_FIELDS = {"features", "date_key", "is_latest", "confidence_basis", "_id"}


class HistoryAccessError(PermissionError):
    """Raised when the authenticated caller lacks welfare-history access.

    The router role gate normally rejects before the service is reached; the
    service re-checks so a direct call can never bypass RBAC.
    """


def _is_sensitive_key(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in _SENSITIVE_KEY_TOKENS)


def _sanitize(value: Any) -> Any:
    """Recursively drop credential-like mapping keys from a payload."""
    if isinstance(value, dict):
        return {key: _sanitize(val) for key, val in value.items() if not _is_sensitive_key(key)}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _coerce_datetime(value: Any) -> datetime | None:
    """Normalize a stored timestamp to a timezone-aware datetime.

    Naive datetimes are interpreted as UTC (matching the welfare router's
    trajectory logic); ISO-format strings are parsed; anything else is None.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _sort_field(collection: str) -> str:
    return "assessed_at" if collection == "risk_assessments" else "created_at"


def _minimize_personnel(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    return {field: doc[field] for field in _PERSONNEL_SAFE_FIELDS if field in doc}


def _minimize_assessment(doc: dict[str, Any]) -> dict[str, Any]:
    """Officer-facing assessment shape — identical to OfficerAssessment.

    Strips the 44-feature vector, date_key, is_latest and confidence_basis so
    internal model material never leaves the service.
    """
    return {
        "id": doc.get("id"),
        "personnel_id": doc.get("personnel_id"),
        "assessed_at": doc.get("assessed_at"),
        "predicted_band": doc.get("predicted_band"),
        "risk_probability": doc.get("risk_probability"),
        "prediction_confidence": doc.get("prediction_confidence"),
        "class_probabilities": doc.get("class_probabilities", []),
        "top_contributing_factors": doc.get("top_contributing_factors", []),
        "data_trust": doc.get("data_trust"),
        "decision_support": doc.get("decision_support"),
        "model_version": doc.get("model_version"),
        "feature_version": doc.get("feature_version"),
    }


def _record_payload(doc: dict[str, Any]) -> dict[str, Any]:
    payload = doc.get("payload")
    if isinstance(payload, dict):
        return dict(payload)
    return {key: value for key, value in doc.items() if key not in _RECORD_INTERNAL_FIELDS}


def _to_history_record(doc: dict[str, Any], collection: str) -> dict[str, Any]:
    if collection == "risk_assessments":
        payload = _minimize_assessment(doc)
        event_at = _coerce_datetime(doc.get("assessed_at") or doc.get("created_at"))
    else:
        payload = _record_payload(doc)
        event_at = _coerce_datetime(doc.get("created_at") or doc.get("timestamp"))
    return {
        "id": str(doc.get("id", "")),
        "collection": collection,
        "event_at": event_at,
        "payload": _sanitize(payload),
    }


def _chronological_key(record: dict[str, Any]) -> tuple:
    """Deterministic ascending order: timestamped records first (oldest first),
    then untimestamped records ordered by id."""
    if record["event_at"] is not None:
        return (0, record["event_at"].timestamp(), record["id"])
    return (1, 0.0, record["id"])


async def _fetch_section(
    collection: str,
    personnel_id: str,
    limit: int,
) -> dict[str, Any]:
    """Read one collection for the personnel and return a HistorySection dict.

    A missing or unreadable collection degrades to ``present=false`` with an
    empty list rather than failing the whole retrieval.
    """
    empty = {"present": False, "record_count": 0, "records": []}
    collection_obj = getattr(db, collection, None)
    if collection_obj is None:
        return empty
    try:
        cursor = collection_obj.find({"personnel_id": personnel_id})
        docs = await cursor.sort(_sort_field(collection), 1).to_list(limit)
    except Exception:
        return empty
    records = [_to_history_record(doc, collection) for doc in docs]
    records.sort(key=_chronological_key)
    return {
        "present": bool(records),
        "record_count": len(records),
        "records": records,
    }


async def get_personnel_history(
    personnel_id: str,
    current_user: dict[str, Any] | None = None,
    max_records_per_section: int = 100,
) -> dict[str, Any]:
    """Collect an authorized personnel's longitudinal welfare history.

    Args:
        personnel_id: The personnel record to retrieve.  Never guessed or
            invented — only documents already stored are returned.
        current_user: The authenticated identity dict (``user_id``, ``role``).
        max_records_per_section: Upper bound of records returned per collection
            (timestamps are preserved; ordering is deterministic ascending).

    Returns:
        A JSON-ready envelope with ``personnel`` static info, one
        ``HistorySection`` per collection in fixed order, a ``generated_at``
        timestamp and explanatory ``notes``.

    Raises:
        ValueError: empty personnel_id.
        HistoryAccessError: non-WELFARE_OFFICER caller (defense in depth).
    """
    if not isinstance(personnel_id, str) or not personnel_id.strip():
        raise ValueError("personnel_id is required")

    role = (current_user or {}).get("role")
    if role != "WELFARE_OFFICER":
        raise HistoryAccessError(
            "Only a WELFARE_OFFICER may retrieve an individual welfare history"
        )

    try:
        limit = max(int(max_records_per_section), 1)
    except (TypeError, ValueError):
        limit = 100

    personnel_doc = await db.personnel.find_one({"id": personnel_id})

    sections: dict[str, dict[str, Any]] = {}
    for collection in COLLECTION_ORDER:
        sections[collection] = await _fetch_section(collection, personnel_id, limit)

    return {
        "personnel_id": personnel_id,
        "personnel": _minimize_personnel(personnel_doc),
        "sections": sections,
        "generated_at": datetime.now(timezone.utc),
        "notes": [
            "A section with present=false means no documents were found for this personnel_id in that collection; missing history is never fabricated.",
            "present=true does not imply non-zero values: zero or null record values are returned exactly as stored.",
            "Stored risk assessments are minimized (no feature vector, date_key, is_latest or confidence_basis); histories are chronological within each section.",
        ],
    }