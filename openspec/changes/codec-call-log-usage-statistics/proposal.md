# Change: codec-call-log-usage-statistics

## Why

The current codec call-log dialog is presentation-only and truncates the returned journal to ten rows. It does not provide any usage history, and at least one supported protocol path also requests only ten records from the device. This makes it impossible to answer the operational question of how heavily a room codec has been used over recent calendar periods.

The application already exposes call logs for exact models `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, `CloudLink Box 310`, and `Polycom RPG 310`, but their transport/session ownership is intentionally not uniform: Huawei call-log reads use the shared interactive-session recovery path while Polycom call-log loading remains owned by its short-lived dedicated worker. The new capability must therefore unify normalized history, calculations, and presentation without collapsing those approved lifecycle boundaries.

Usage calculations also require machine-readable call timestamps and durations rather than the current display-only strings. Deep history retrieval must be bounded, must stay read-only and off the Qt GUI thread, and must degrade transparently when the product-imposed 100-record ceiling prevents complete 30/90-day coverage.

## What Changes

- Add a common call-history snapshot and usage-calculation contract for the five existing call-log codec models.
- Preserve literal call-log semantics: completed successful, unanswered, and failed entries remain eligible; incoming and outgoing entries are treated equally; overlapping legitimate records are summed independently rather than merged.
- Preserve active calls in the visible chronology while excluding them from usage calculations until they become completed call-log records.
- Retrieve history newest-first only as deeply as needed, stopping when the 90-day boundary is covered, the device reports end-of-journal, or 100 call records have been accepted, whichever occurs first.
- Treat an authoritative end-of-journal as meaning there are no older calls for this feature; do not infer an undocumented retention policy.
- Use the codec's own current local time as the calendar authority when the protocol can obtain it reliably. Fall back to the computer's local time only when codec time is unavailable, and expose that fallback as a warning in the GUI.
- Calculate usage over calendar-date windows including today. A 30-day window is today plus the preceding 29 calendar dates; a 90-day window is today plus the preceding 89 dates.
- Count only the temporal overlap of each completed call with the applicable calculation interval.
- Calculate normative working capacity as `8 hours * count(Monday..Friday calendar dates touched by the interval)`. Holidays and shifted workdays are intentionally ignored, the current weekday contributes the full eight hours, and a partial first weekday in a degraded interval also contributes the full eight hours.
- Permit utilization percentages above 100%; display usage hours with one decimal place and percentage as a whole number.
- When the 100-record ceiling truncates a target period, shorten that statistic to the exact interval from the oldest accepted record timestamp to current reference time, change the displayed day count to the number of calendar dates touched by that interval, and recalculate both duration and denominator for that actual interval.
- If the 100-record ceiling covers at least 30 but fewer than 90 calendar dates, keep the complete 30-day row and degrade only the longer row. If it covers fewer than 30 calendar dates, show one degraded usage row instead of two duplicate rows.
- Keep malformed-duration records visible but exclude them from usage totals and show a partial-calculation warning.
- A successful empty journal is valid data and produces `0.0` hours / `0%` for both full target periods.
- Redesign the dialog with two always-visible latest-call rows using the existing four fields, usage summary rows, and an initially collapsed `Журнал звонков` section showing up to the latest 20 records total, including the two preview records.
- Show `Загрузка журнала звонков...` during initial acquisition and `Расчёт статистики использования...` while deeper history/calculation continues.
- Preserve current fresh-load semantics on each explicit dialog opening; expanding/collapsing the already loaded journal within that dialog must not re-query the codec.
- Add focused offline regression coverage for all period, 100-record, boundary, active-call, overlap, malformed-data, empty-history, partial-failure, and time-fallback cases.
- Add read-only live protocol research/validation for available real devices to establish actual pagination/limit/end-of-journal and device-time behavior. Live devices are not required to contain 100 calls or 90 days of history; synthetic fixtures remain authority for deterministic edge-case regression tests.

## Impact

Affected specifications:

- new `codec-call-log-usage-statistics`

Expected implementation areas include:

- a focused normalized call-history/statistics model or helper in the application/core layer
- `handlers/huawei/te20.py`
- `handlers/huawei/te40.py`
- `handlers/huawei/bar310.py` for both exact CloudLink 310 identities
- `handlers/polycom/rpg310.py`
- `core/interactive_session.py` only if a narrow read-only operation/result contract extension is needed
- `core/workers/codec_call_logs.py`
- `gui/screens/codec_screen.py`
- `gui/dialogs/call_log_window.py`
- focused handler, worker/controller, calculation, and GUI tests

This change does not alter codec model recognition, equipment inventory, PDU room/codec resolution, credential selection/fallback ownership, transport retry policy, state-changing codec operations, microphone metering, DMP behavior, Graphify artifacts, or unrelated diagnostic/status presentation.
