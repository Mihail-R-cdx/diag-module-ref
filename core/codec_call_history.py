"""Normalized codec call history and deterministic usage calculations.

This module deliberately contains no vendor transport or Qt code.  Handlers
publish raw records through :func:`snapshot_from_records`; the GUI only renders
the resulting model and never parses its own display strings for arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any, Iterable, Optional, Sequence


MAX_ACCEPTED_RECORDS = 100
ZERO_WEEKDAY_WARNING = (
    "Процент использования недоступен: период не содержит рабочих дней."
)


class TerminationReason(str, Enum):
    COVERAGE_PROVEN = "coverage_proven"
    SOURCE_ENDED = "source_ended"
    PRODUCT_LIMIT_REACHED = "product_limit_reached"
    SOURCE_HISTORY_LIMITED = "source_history_limited"
    OPERATIONAL_FAILURE = "operational_failure"


@dataclass(frozen=True)
class CallRecord:
    source_identity: Optional[str]
    start_at: Optional[datetime]
    duration_seconds: Optional[int]
    active: bool = False
    room_number: str = ""
    speed: str = ""
    start_display: str = ""
    duration_display: str = ""
    direction: str = "unknown"

    @property
    def has_usable_duration(self) -> bool:
        return (
            not self.active
            and self.start_at is not None
            and self.duration_seconds is not None
            and self.duration_seconds >= 0
        )


@dataclass(frozen=True)
class CallHistorySnapshot:
    reference_now: datetime
    reference_time_source: str
    records: tuple[CallRecord, ...]
    termination_reason: TerminationReason
    coverage_lower_bound: Optional[datetime] = None
    coverage_basis: Optional[str] = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class UsageRow:
    days: int
    hours: float
    percentage: Optional[int]
    complete: bool
    period_start: datetime
    period_end: datetime


def parse_local_datetime(value: Any) -> Optional[datetime]:
    """Parse only known vendor/local representations without timezone mixing."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            seconds = float(value)
            if seconds > 10_000_000_000:
                seconds /= 1000
            return datetime.fromtimestamp(seconds)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    for pattern in ("%d/%m/%Y %H:%M:%S", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            pass
    return None


def duration_seconds(start_at: Optional[datetime], end_at: Optional[datetime]) -> Optional[int]:
    if start_at is None or end_at is None:
        return None
    seconds = int((end_at - start_at).total_seconds())
    return seconds if seconds >= 0 else None


def format_start(value: Optional[datetime], fallback: Any = "") -> str:
    return value.strftime("%d.%m.%Y %H:%M:%S") if value else str(fallback or "")


def format_duration(seconds: Optional[int], active: bool = False) -> str:
    if active:
        return "Активный"
    if seconds is None:
        return ""
    hours, rest = divmod(max(0, seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def normalize_call_direction(value: Any) -> str:
    """Normalize only explicit vendor direction evidence for presentation."""
    if value is None:
        return "unknown"
    text = str(value).strip().casefold()
    if text in {"outgoing", "outbound", "dialed", "placed", "исходящий"}:
        return "outgoing"
    if text in {"incoming", "inbound", "received", "входящий"}:
        return "incoming"
    return "unknown"


def record_from_vendor(
    item: dict[str, Any], *, source_identity: Optional[str] = None,
    start_key: str = "startTime", end_key: str = "endTime",
    room_keys: Sequence[str] = ("room_number", "call_number", "address", "name", "number"),
    speed_key: str = "rate", active_keys: Sequence[str] = ("active", "isActive"),
) -> CallRecord:
    start_raw = item.get(start_key)
    start_at = parse_local_datetime(start_raw)
    active = any(bool(item.get(key)) for key in active_keys)
    raw_duration = item.get("duration")
    if raw_duration not in (None, ""):
        try:
            parsed_seconds = int(raw_duration)
            seconds = parsed_seconds if parsed_seconds >= 0 else None
        except (TypeError, ValueError):
            seconds = None
    else:
        seconds = duration_seconds(start_at, parse_local_datetime(item.get(end_key)))
    room = next((item.get(key) for key in room_keys if item.get(key) not in (None, "")), "")
    speed = item.get(speed_key, "")
    identity = source_identity or item.get("id") or item.get("recordId")
    direction = normalize_call_direction(
        item.get("direction", item.get("callDirection", item.get("call_direction")))
    )
    return CallRecord(
        source_identity=str(identity) if identity not in (None, "") else None,
        start_at=start_at,
        duration_seconds=seconds,
        active=active,
        room_number=str(room), speed=str(speed or ""),
        start_display=format_start(start_at, start_raw),
        duration_display=format_duration(seconds, active),
        direction=direction,
    )


def snapshot_from_records(
    records: Iterable[CallRecord], *, reference_now: Optional[datetime] = None,
    source_ended: bool = False, coverage_lower_bound: Optional[datetime] = None,
    coverage_basis: Optional[str] = None, warnings: Iterable[str] = (),
    termination_reason: Optional[TerminationReason] = None,
    reference_time_source: str = "system_fallback",
) -> CallHistorySnapshot:
    """Build a safe snapshot from one bounded source response.

    A source without documented continuation is never treated as complete after
    returning records. ``source_ended`` is an explicit protocol fact supplied
    by a model-specific boundary; an empty normalized collection alone is not
    evidence of clean EoJ. The generic hard ceiling remains useful to adapters
    that do have real pagination.
    """
    accepted: list[CallRecord] = []
    identities: set[str] = set()
    for record in records:
        if record.source_identity and record.source_identity in identities:
            continue
        if record.source_identity:
            identities.add(record.source_identity)
        accepted.append(record)
    # Source ordering is not evidence of coverage. Normalise the returned
    # batch before any preview/latest-20/product-cap selection.
    accepted.sort(
        key=lambda record: (
            record.start_at is not None,
            record.start_at or datetime.min,
        ),
        reverse=True,
    )
    accepted = accepted[:MAX_ACCEPTED_RECORDS]
    now = (reference_now or datetime.now()).replace(tzinfo=None)
    messages = list(warnings)
    if reference_time_source not in {"device", "system_fallback"}:
        raise ValueError("reference_time_source must be device or system_fallback")
    if reference_time_source == "device" and reference_now is None:
        raise ValueError("device reference time requires an explicit datetime")
    if reference_time_source != "device":
        messages.append("Использовано системное время: время кодека недоступно.")
    if termination_reason is not None:
        # An acquisition boundary may know more than this generic one-batch
        # adapter. Never overwrite its explicit terminal observation.
        reason = termination_reason
    elif source_ended:
        # A clean EoJ observed with the 100th record is completion, not the
        # product cap: no older record remains to retrieve.
        reason = TerminationReason.SOURCE_ENDED
    elif coverage_lower_bound is not None:
        reason = TerminationReason.COVERAGE_PROVEN
    elif len(accepted) == MAX_ACCEPTED_RECORDS:
        reason = TerminationReason.PRODUCT_LIMIT_REACHED
    else:
        reason = TerminationReason.SOURCE_HISTORY_LIMITED
    if reason == TerminationReason.PRODUCT_LIMIT_REACHED:
        messages.append("История ограничена 100 записями.")
    elif reason == TerminationReason.SOURCE_HISTORY_LIMITED:
        messages.append("Глубина истории не подтверждена устройством; расчёт неполный.")
    elif reason == TerminationReason.OPERATIONAL_FAILURE:
        messages.append("Глубокое чтение журнала не завершилось; расчёт может быть неполным.")
    if any(not record.active and record.duration_seconds is None for record in accepted):
        messages.append("Часть длительностей не распознана и не включена в расчёт.")
    return CallHistorySnapshot(
        reference_now=now, reference_time_source=reference_time_source,
        records=tuple(accepted), termination_reason=reason,
        coverage_lower_bound=coverage_lower_bound, coverage_basis=coverage_basis,
        warnings=tuple(dict.fromkeys(messages)),
    )


def snapshot_from_display_records(
    records: Iterable[dict[str, Any]], *, reference_now: Optional[datetime] = None,
    source_ended: bool = False,
    reference_time_source: str = "system_fallback",
) -> CallHistorySnapshot:
    """Compatibility adapter for existing handler call-log contracts.

    It is intentionally kept at the handler/transport boundary: callers get a
    typed snapshot, while legacy ``get_call_records`` clients may continue to
    receive their four display fields.  No GUI string is ever read here.
    """
    normalized = []
    for item in records:
        if not isinstance(item, dict):
            continue
        # Supported handlers retain raw source values under private keys.  The
        # fallback exists only for legacy callers/tests; production arithmetic
        # never reverses the rendered table strings.
        start = parse_local_datetime(item.get("_raw_start", item.get("start_time")))
        duration_text = str(item.get("duration") or "")
        active = bool(item.get("_active", False))
        seconds = None
        if item.get("_duration_seconds") not in (None, ""):
            try:
                candidate = int(item["_duration_seconds"])
                seconds = candidate if candidate >= 0 else None
            except (TypeError, ValueError):
                seconds = None
        elif item.get("_raw_end") not in (None, ""):
            seconds = duration_seconds(start, parse_local_datetime(item.get("_raw_end")))
        # Do not reverse GUI formatting back into data.  Production handlers
        # keep vendor values in the private raw fields above; legacy callers
        # without those fields remain visible but are intentionally excluded
        # from arithmetic as malformed-duration records.
        normalized.append(CallRecord(
            source_identity=str(item.get("source_identity") or "") or None,
            start_at=start, duration_seconds=seconds, active=active,
            room_number=str(item.get("room_number") or ""),
            speed=str(item.get("speed") or ""),
            start_display=str(item.get("start_time") or ""),
            duration_display=duration_text,
            direction=normalize_call_direction(
                item.get("_direction", item.get("direction", item.get("call_direction")))
            ),
        ))
    return snapshot_from_records(
        normalized,
        reference_now=reference_now,
        source_ended=source_ended,
        reference_time_source=reference_time_source,
    )


def record_to_display(record: CallRecord) -> dict[str, str]:
    return {
        "room_number": record.room_number,
        "start_time": record.start_display or format_start(record.start_at),
        "duration": record.duration_display or format_duration(record.duration_seconds, record.active),
        "speed": record.speed,
    }


def normal_period(reference_now: datetime, days: int) -> tuple[datetime, datetime]:
    if days < 1:
        raise ValueError("days must be positive")
    start_date = reference_now.date() - timedelta(days=days - 1)
    return datetime.combine(start_date, time.min), reference_now


def touched_weekday_hours(start: datetime, end: datetime) -> float:
    if end < start:
        return 0.0
    current = start.date()
    total = 0
    while current <= end.date():
        if current.weekday() < 5:
            total += 8
        current += timedelta(days=1)
    return float(total)


def overlap_seconds(record: CallRecord, start: datetime, end: datetime) -> int:
    if not record.has_usable_duration:
        return 0
    call_start = record.start_at
    assert call_start is not None and record.duration_seconds is not None
    call_end = call_start + timedelta(seconds=record.duration_seconds)
    left, right = max(call_start, start), min(call_end, end)
    return max(0, int((right - left).total_seconds()))


def calculate_row(snapshot: CallHistorySnapshot, days: int, *, period_start: Optional[datetime] = None, complete: bool = True) -> UsageRow:
    start, end = (period_start, snapshot.reference_now) if period_start else normal_period(snapshot.reference_now, days)
    assert start is not None
    seconds = sum(overlap_seconds(record, start, end) for record in snapshot.records)
    hours = round(seconds / 3600, 1)
    capacity = touched_weekday_hours(start, end)
    percentage = None if capacity == 0 else round(seconds / 3600 / capacity * 100)
    return UsageRow(days=days, hours=hours, percentage=percentage, complete=complete, period_start=start, period_end=end)


def calculate_usage(snapshot: CallHistorySnapshot) -> tuple[UsageRow, ...]:
    """Return only period rows that are safe for the snapshot's termination."""
    if snapshot.termination_reason == TerminationReason.PRODUCT_LIMIT_REACHED:
        oldest = min((r.start_at for r in snapshot.records if r.start_at), default=None)
        if oldest is None:
            return ()
        actual_days = (snapshot.reference_now.date() - oldest.date()).days + 1
        if actual_days < 30:
            return (calculate_row(snapshot, actual_days, period_start=oldest, complete=False),)
        rows = [calculate_row(snapshot, 30, complete=False)]
        if actual_days < 90:
            rows.append(calculate_row(snapshot, actual_days, period_start=oldest, complete=False))
        else:
            rows.append(calculate_row(snapshot, 90, complete=False))
        return tuple(rows)
    if snapshot.termination_reason in {TerminationReason.SOURCE_ENDED, TerminationReason.COVERAGE_PROVEN}:
        return (calculate_row(snapshot, 30), calculate_row(snapshot, 90))
    # A shorter target can remain usable after a source limit or typed deep
    # failure if its exact interval-safe lower bound was already established.
    if snapshot.coverage_lower_bound:
        rows = []
        for days in (30, 90):
            start, _ = normal_period(snapshot.reference_now, days)
            if snapshot.coverage_lower_bound <= start:
                rows.append(calculate_row(snapshot, days))
        return tuple(rows)
    return ()


def usage_warnings(rows: Iterable[UsageRow]) -> tuple[str, ...]:
    """Return calculation warnings without replacing acquisition warnings."""
    if any(row.percentage is None for row in rows):
        return (ZERO_WEEKDAY_WARNING,)
    return ()
