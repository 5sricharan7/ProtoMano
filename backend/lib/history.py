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
from lib.feature_engineering import (
    RAW_NUMERIC_FEATURES,
    REQUIRED_RAW_COLUMNS,
    STATIC_FEATURES,
)

# Fixed section order — the response dict preserves insertion order.
COLLECTION_ORDER = (
    "wellness_logs",
    "workload_records",
    "deployment_history",
    "leave_requests",
    "risk_assessments",
)

# Raw welfare-record collections consumed by the Task 4B window builder.
# risk_assessments is NOT included: it stores engineered vectors, not raw
# weekly records, and its minimized band/probability is welfare-officer
# decision material that must never reach a PERSONNEL response.
RAW_OBSERVATION_COLLECTIONS = (
    "wellness_logs",
    "workload_records",
    "deployment_history",
    "leave_requests",
)

# Static raw-feature fields that may live on a personnel document; the window
# builder falls back to these when no observation payload supplies them.
# Aliased from feature_engineering.STATIC_FEATURES so the Task 4B window can
# never drift from the model's input contract.
_PERSONNEL_STATIC_FIELDS = STATIC_FEATURES

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


def _minimize_personnel_with_static(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """Personnel envelope for the raw-window path.

    Same safe static identity fields as ``_minimize_personnel`` plus the raw
    static feature fields the window builder may fall back to.  The envelope
    is scrubbed of credential-like keys before returning.
    """
    if not doc:
        return None
    keys = tuple(_PERSONNEL_SAFE_FIELDS) + tuple(_PERSONNEL_STATIC_FIELDS)
    return _sanitize({field: doc[field] for field in keys if field in doc})


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


# --- Task 4B: Exact 4-week raw-record intelligence window ---


class WindowBuilderError(ValueError):
    """Raised when the 4-week raw-record window cannot be constructed."""


# The window is exactly 4 weeks (week 0 = oldest ... week 3 = latest) ending
# at the person's latest timestamped observation.
WINDOW_WEEK_COUNT = 4
WINDOW_SPAN_DAYS = 28


def _week_index(observation_date: datetime, anchor_date: datetime) -> int | None:
    """Map an observation datetime to its week (0-3) relative to the anchor.

    Week 3 (latest): 0-6 days before the anchor.
    Week 2: 7-13 days before.  Week 1: 14-20 days before.
    Week 0 (oldest in-window): 21-27 days before.
    Observations at least 28 days before the anchor fall OUTSIDE the selected
    4-week window and return None -- they are excluded, never clipped in.
    """
    days_before = (anchor_date - observation_date).days
    if days_before < 0 or days_before >= WINDOW_SPAN_DAYS:
        return None
    return 3 - days_before // 7


def _build_raw_record(
    personnel_id: str,
    week: int,
    static_fields: dict[str, Any],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble one raw weekly record exactly matching the feature-engineering
    column contract (``REQUIRED_RAW_COLUMNS``).

    ``static_fields`` were resolved ONCE for the whole window, so every week
    repeats identical static personnel values.  ``observations`` are that
    week's 4A history records in deterministic order; their payload fields are
    merged (union, later observations win on duplicate keys) with no
    aggregation, imputation or fabrication.  Unobserved fields stay None so
    feature_engineering's causal imputation path can do its job.
    """
    record: dict[str, Any] = {"personnel_id": personnel_id, "week": week}
    record.update(static_fields)
    merged_payload: dict[str, Any] = {}
    for obs in observations:
        payload = obs.get("payload")
        if isinstance(payload, dict):
            merged_payload.update(payload)
    for field in RAW_NUMERIC_FEATURES:
        record[field] = merged_payload.get(field)
    return record


def _validate_raw_window_contract(raw_records: list[dict[str, Any]]) -> None:
    """Defense in depth: raw records must contain EXACTLY the columns the
    existing feature-engineering contract accepts, with a valid personnel_id
    and numeric week 0-3.  Structural check only -- never engineers features.
    """
    required = set(REQUIRED_RAW_COLUMNS)
    for record in raw_records:
        if set(record) != required:
            raise WindowBuilderError(
                f"raw record for week {record.get('week')} does not match the feature-engineering contract"
            )
        pid = record.get("personnel_id")
        if not isinstance(pid, str) or not pid.strip():
            raise WindowBuilderError("raw record personnel_id must be a non-empty string")
        week = record.get("week")
        if not isinstance(week, int) or week not in range(WINDOW_WEEK_COUNT):
            raise WindowBuilderError("raw record 'week' must be an integer in 0-3")


async def build_four_week_window(
    personnel_id: str,
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the exact 4-week raw-record intelligence window for one personnel.

    Task 4B: converts the Task 4A historical retrieval into the precise raw
    weekly records consumed by ``lib.feature_engineering.records_to_frame`` /
    ``features_for_latest_week`` and ``lib.inference.predict_from_raw_records``.

    Window semantics:
    1. Retrieves the person's history through the Task 4A retrieval layer.
    2. Anchors on the LATEST timestamped observation across the four raw
       welfare collections (never a guessed "today").
    3. Clusters observations into exactly 4 chronological weeks (0=oldest ..
       3=latest) ending at that anchor.
    4. Emits all 4 weekly raw records; weeks without data stay all-missing.
    5. Preserves missingness explicitly (None) -- nothing is imputed,
       averaged, differenced or fabricated here.
    6. Excludes observations older than the 28-day window and never uses any
       record after the anchor, so raw records contain no out-of-window data.
    7. Resolves static personnel fields once and repeats them identically
       across every week.

    Authorization: WELFARE_OFFICER only (defense in depth -- the Task 4A layer
    re-checks the authenticated role before any window is built).

    Returns:
        Envelope with ``personnel_id``, scrubbed ``personnel`` static info,
        ``raw_records`` (weeks 0..3, ready for feature engineering),
        ``window_start`` / ``window_end`` / ``latest_observation_date``,
        ``week_count``, ``weeks_with_data`` and explanatory ``notes``.

    Raises:
        ValueError: empty personnel_id or no usable observations.
        HistoryAccessError: non-WELFARE_OFFICER caller.
        WindowBuilderError: observations are present but unusable.
    """
    if not isinstance(personnel_id, str) or not personnel_id.strip():
        raise ValueError("personnel_id is required")

    history = await get_personnel_history(
        personnel_id, current_user, max_records_per_section=10000
    )

    observations: list[dict[str, Any]] = []
    for collection in RAW_OBSERVATION_COLLECTIONS:
        section = history.get("sections", {}).get(collection) or {}
        for record in section.get("records", []):
            event_at = record.get("event_at")
            if event_at is None:
                # No usable timestamp: placing it would mean guessing a week.
                continue
            observations.append({
                "id": str(record.get("id", "")),
                "collection": collection,
                "event_at": event_at,
                "payload": record.get("payload", {}),
            })

    if not observations:
        raise WindowBuilderError(
            f"No timestamped welfare observations found for personnel_id {personnel_id}; "
            "cannot construct the 4-week raw-record window"
        )

    # Deterministic global order: calendar datetime, then record id. Duplicate
    # record ids are de-duplicated (first in this order wins) so output never
    # depends on insertion order.
    observations.sort(key=lambda obs: (obs["event_at"].timestamp(), obs["id"]))
    deduped: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for obs in observations:
        if obs["id"] in seen_ids:
            continue
        seen_ids.add(obs["id"])
        deduped.append(obs)
    observations = deduped

    anchor_date = observations[-1]["event_at"]

    observations_by_week: dict[int, list[dict[str, Any]]] = {
        week: [] for week in range(WINDOW_WEEK_COUNT)
    }
    window_observations: list[dict[str, Any]] = []
    for obs in observations:
        week = _week_index(obs["event_at"], anchor_date)
        if week is None:
            continue  # outside the selected 4-week window
        observations_by_week[week].append(obs)
        window_observations.append(obs)

    personnel_doc = await db.personnel.find_one({"id": personnel_id})

    # Static personnel fields: resolve ONCE per window so every week is
    # consistent.  Personnel document first, then the first payload in
    # deterministic order, else None (missing stays missing).
    static_fields: dict[str, Any] = {}
    for field in STATIC_FEATURES:
        value = None
        if personnel_doc and field in personnel_doc:
            value = personnel_doc[field]
        else:
            for obs in window_observations:
                payload = obs.get("payload")
                if isinstance(payload, dict) and field in payload:
                    value = payload[field]
                    break
        static_fields[field] = value

    raw_records: list[dict[str, Any]] = [
        _build_raw_record(personnel_id, week, static_fields, observations_by_week[week])
        for week in range(WINDOW_WEEK_COUNT)
    ]
    _validate_raw_window_contract(raw_records)

    weeks_with_data: list[int] = [
        week for week in range(WINDOW_WEEK_COUNT) if observations_by_week[week]
    ]
    window_start = min(obs["event_at"] for obs in window_observations)

    return {
        "personnel_id": personnel_id,
        "personnel": _minimize_personnel_with_static(personnel_doc),
        "raw_records": raw_records,
        "window_start": window_start,
        "window_end": anchor_date,
        "latest_observation_date": anchor_date,
        "week_count": len(weeks_with_data),
        "weeks_with_data": weeks_with_data,
        "notes": [
            "Raw records are chronological: week 0 is the oldest in-window week, week 3 holds the latest observation.",
            "The window always ends at the latest timestamped observation; observations older than 28 days before it are outside the window and excluded.",
            "Observations without a usable timestamp cannot be placed in a week and are excluded rather than guessed.",
            "Missing values are represented as None (null) and are never fabricated; the existing feature-engineering pipeline performs causal imputation.",
            "No record from after the latest observation is used, so raw records never contain future data.",
            "Personnel static fields are resolved once and repeated identically across all weeks.",
            "Duplicate ids are de-duplicated in deterministic (timestamp, id) order; same-week records are merged with later observations winning on shared fields.",
        ],
    }


# Keep a history-matching alias for the same entry point.
get_personnel_raw_window = build_four_week_window
