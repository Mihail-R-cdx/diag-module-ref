# Change: codec-call-log-usage-statistics

## Why

The current codec call-log dialog is presentation-only and truncates the returned journal to ten rows. It does not provide usage statistics, while the supported device families do not expose one uniform history-depth contract. Usage calculations therefore need a normalized machine-readable history model, bounded read-only retrieval, explicit completeness/degradation semantics, and a common GUI without collapsing the already approved Huawei and Polycom network lifecycles.

The product requirement intentionally distinguishes two different concepts:

1. **Full 30/90-day completeness.** A normal full-period statistic is authoritative only when interval-safe coverage of that lower bound is proven or the source reports clean end-of-journal.
2. **Product-limit degradation at exactly 100 accepted records.** The application intentionally stops at the hard cap and computes a useful statistic from the accepted records starting at the exact `start_at` of the oldest accepted record, even though still-older unseen calls might exist. This is a product convention for capped available history, not a claim of mathematically complete device history.

A separate technical state, `source_history_limited`, covers cases where deeper history cannot be obtained before the product cap and clean end-of-journal is not proven. That state must not silently reuse the 100-record product convention.

## What Changes

- Add a common call-history snapshot and usage-calculation contract for exactly these existing call-log models:
  - `Huawei TE20`
  - `Huawei TE40`
  - `CloudLink Bar 310`
  - `CloudLink Box 310`
  - `Polycom RPG 310`
- Preserve Huawei call-log ownership on the existing shared interactive-session/controller path and preserve Polycom call-log ownership on its existing short-lived dedicated worker/session path.
- Preserve literal call-log semantics: completed successful, unanswered, failed, incoming, and outgoing records are all eligible; legitimate overlapping records are summed independently rather than merged.
- Keep active calls in normal chronology and count them toward the 100-record acquisition ceiling, while excluding them from usage totals until completed.
- Keep malformed-duration records visible, exclude those durations from totals, and warn that affected statistics are partial.
- Retrieve newest-first and stop on the first applicable condition: interval-safe 90-day coverage proof, clean end-of-journal, exactly 100 accepted records, structured `source_history_limited`/no-progress, or typed operational failure.
- For **normal full 30/90 statistics**, do not treat `oldest_retrieved.start_at < boundary` as coverage proof by itself. Early completeness requires a researched interval-safe protocol/query invariant or clean end-of-journal.
- For **hard-cap 100 degradation**, deliberately use `oldest_of_100.start_at` as the available-history lower bound without an additional interval-safe proof. Calculate from the accepted records only and display an explicit warning that history was limited to 100 records.
- If the hard cap yields at least 30 but fewer than 90 calendar dates of available history, show a 30-day row plus one actual-day row (for example `47 days`). If it yields fewer than 30 calendar dates, show exactly one actual-day row (for example `18 days`).
- For `source_history_limited` before the hard cap, preserve recent journal data but do not manufacture a full or capped-product percentage for an unproven interval. Already proven target periods remain valid; otherwise affected statistics are incomplete/unavailable with a warning.
- Treat clean end-of-journal as meaning there were no older calls for this feature; do not infer an undocumented retention policy.
- Use codec-local current time as calendar authority when reliably available; otherwise use computer-local current time with a visible non-modal warning.
- Define 30/90-day windows by calendar dates including today. Count only the temporal overlap of each completed call with the applicable interval.
- Calculate normative working capacity as `8 hours * count(Monday..Friday calendar dates touched by the interval)`. Ignore public holidays and shifted workdays, include all eligible call duration regardless of hour/day, give the current weekday and a partial first weekday the full eight-hour denominator, and allow percentages above 100%.
- Display usage hours with one decimal place and percentage as a whole number; avoid division by zero if an interval touches no weekdays.
- Redesign the dialog to show the latest two calls always visible, usage summary row(s), and an initially collapsed `Журнал звонков` section showing the latest 20 records total, including the same top two.
- Show `Загрузка журнала звонков...` during initial acquisition and `Расчёт статистики использования...` while deeper history/statistics work continues.
- Expanding/collapsing the journal uses already acquired records and does not refetch; each later explicit dialog opening starts a fresh acquisition.
- Add deterministic synthetic regression coverage for 30/90 boundaries, hidden long boundary-crossing records, hard-cap 47-day and 18-day degradation, active/malformed/overlapping records, source no-progress, empty history, time fallback, lifecycle ownership, partial failure, and GUI behavior.
- Use available physical devices only for read-only protocol confirmation of request shape/order, pagination/end/no-progress, timestamp encoding, device time, and any claimed full-coverage invariant. Real devices do not need 100 calls or 90 days of history.

## Impact

Affected specifications:

- new `codec-call-log-usage-statistics`

Expected implementation areas include:

- a focused normalized call-history/statistics helper in the application/core layer
- `handlers/huawei/te20.py`
- `handlers/huawei/te40.py`
- `handlers/huawei/bar310.py` for both exact CloudLink 310 identities
- `handlers/polycom/rpg310.py`
- `core/interactive_session.py` only if a narrow read-only operation/result contract extension is needed
- `core/workers/codec_call_logs.py`
- `gui/screens/codec_screen.py`
- `gui/dialogs/call_log_window.py`
- focused handler, worker/controller, calculation, and GUI tests

This change does not alter codec model recognition, equipment inventory, PDU room/codec resolution, credential-selection/fallback ownership, transport retry policy, state-changing codec operations, microphone metering, DMP behavior, Graphify artifacts, or unrelated diagnostic/status presentation.
