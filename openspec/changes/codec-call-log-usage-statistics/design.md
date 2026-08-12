# Design: Codec call-log usage statistics

## Context

The codec page already exposes `Журнал звонков` for exactly five diagnostic models:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

`CallLogWindow` currently renders one four-column table and truncates presentation to ten rows. Existing handlers mostly return display-oriented strings, which are not a safe arithmetic source for 30/90-day interval calculations.

The transport paths are intentionally different. TE20, TE40, Bar 310, and Box 310 call-log reads use the shared Huawei interactive-session recovery path. Polycom call-log loading remains a separate short-lived worker/session path. This change unifies normalized history, calculation, and presentation while preserving those lifecycle boundaries.

Call-log ordering also does not automatically prove full interval completeness. If a source is ordered only by `start_at`, seeing a record before a requested boundary does not prove that an unseen older, longer call cannot cross back into that requested interval. At the same time, the product has explicitly chosen a simpler and useful rule when the **hard cap of 100 accepted records** is reached: compute a statistic from the capped available history beginning at the exact oldest accepted `start_at`, with a warning that the history was limited to 100 records. These are intentionally different semantics.

## Goals

1. Provide one identical call-log/statistics presentation for all five supported models.
2. Introduce machine-readable normalized call history without parsing GUI strings back into arithmetic values.
3. Calculate 30-day and 90-day usage under the agreed calendar/weekday rules.
4. Bound each explicit load to at most 100 accepted records.
5. Require interval-safe proof for early **full-period** completeness.
6. Preserve the explicitly agreed **product-limit degradation** at the hard cap without requiring an additional completeness proof for the degraded lower bound.
7. Distinguish clean EoJ, product cap, source-history limitation/no-progress, and typed operational failure.
8. Preserve literal call-log semantics, active-call presentation, existing credential authority, stale suppression, and background-only network I/O.
9. Make live protocol research useful without requiring physical devices to contain 100 calls or old history.

## Non-goals

- Do not add call-log support to another codec model.
- Do not change codec identity/model recognition or inventory matching.
- Do not route Polycom call-log work through the Huawei shared interactive controller.
- Do not move credential selection/fallback into handlers, workers, dialogs, or calculation helpers.
- Do not change state-changing-operation or transport-retry policy.
- Do not manufacture real-device calls/history for validation.
- Do not infer Russian holidays or shifted workdays.
- Do not merge simultaneous legitimate records into one occupied interval.
- Do not persist call history across separate dialog openings.
- Do not make Graphify part of this workflow.

## Decision 1: One closed five-model presentation contract

The capability supports exactly:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

All five use the same external dialog structure and calculation semantics. Vendor-specific request, parser, pagination, and device-time details stay behind model-specific read-only boundaries.

Visible call fields remain:

```text
Номер комнаты
Дата и время начала
Продолжительность
Скорость
```

The dialog shows up to the two newest records always visible. Below the usage summary, an initially collapsed section labelled exactly `Журнал звонков` shows up to the latest 20 records total, including the same top two. Fewer than 20 records produce no blank padding.

## Decision 2: Acquisition produces a machine-readable normalized snapshot

Usage calculation SHALL NOT parse user-facing date/duration strings. The normalized snapshot is equivalent to:

```text
reference_now              codec-local current datetime when reliable,
                           otherwise computer-local current datetime
reference_time_source      device | system_fallback
records[]:
  source_identity          optional opaque vendor identity
  start_at                 normalized local datetime on the same calendar basis
  duration_seconds         non-negative numeric duration, or unavailable
  active                   boolean
  room_number              presentation value
  speed                    presentation value
  display fields as needed
termination_reason         coverage_proven | source_ended | product_limit_reached |
                           source_history_limited | operational_failure
coverage_lower_bound       optional timestamp for interval-safe full coverage
coverage_basis             optional non-secret invariant identifier
warnings[]                 non-secret structured warnings
```

The exact Python representation is an implementation choice. Arithmetic values remain machine-readable through calculation.

Pagination may repeat a source record. Only a duplicate proven to be the same vendor/source record may be suppressed. Distinct calls are never deduplicated merely because times, participants, or intervals overlap.

The 100-record ceiling counts active records and visible records with unavailable duration. Proven transport duplicates do not count twice.

## Decision 3: Full-period coverage proof is interval-safe

For a normal target lower bound `B`, `coverage_proven` before clean EoJ means current source/documentation or read-only protocol research establishes a testable invariant that no not-yet-retrieved older source record can overlap `B`.

This alone is insufficient:

```text
oldest_retrieved.start_at < B
```

Example:

```text
boundary B: 10:00
record A: start 09:00, duration 20 min
record B: start 08:00, duration 3 h
```

If the source is ordered only by start time, receiving A does not prove completeness at 10:00 because unseen B still overlaps the requested interval.

Safe early proof may come from a researched guarantee such as:

- ordering by call end time with a guarantee that all remaining entries end before the bound;
- a server-side query returning every record intersecting the requested interval;
- another model-specific ordering/duration/continuation invariant strong enough to exclude unseen overlap.

The implementation SHALL NOT infer such a guarantee from typical chronological appearance. If no interval-safe invariant exists, retrieval continues until clean EoJ, the hard 100-record cap, structured source-history limitation/no-progress, or typed operational failure.

This decision controls claims of **normal full 30/90 completeness**. It does not redefine the separate product-limit degradation rule in Decision 7.

## Decision 4: Newest-first retrieval is hard-bounded at 100 accepted records

Each explicit dialog opening starts a fresh read-only acquisition. Records are requested newest-first using only actual researched protocol mechanics.

Retrieval stops on the first applicable condition:

1. interval-safe coverage of the 90-day normal lower bound is proven;
2. clean end-of-journal/no more records is reported;
3. exactly 100 accepted records have been obtained;
4. a structured `source_history_limited`/no-progress state prevents deeper retrieval without clean EoJ;
5. a typed operational failure prevents continuation.

No 101st accepted record may be fetched merely to improve statistics.

Clean EoJ is treated by product decision as `there were no older calls` for this feature. The application does not infer an undocumented retention policy from an early source end.

## Decision 5: `source_history_limited` is separate from the product cap

Some sources may expose only a fixed batch, ignore pagination, repeat the same page, or otherwise make no progress without explicitly reporting EoJ. After bounded protocol-specific continuation attempts, these cases produce structured `source_history_limited`.

Examples include:

- pagination/cursor/offset is unavailable;
- a continuation parameter is ignored;
- the same source page repeats with no new unique records;
- a fixed/result-limited batch is exposed without a clean EoJ guarantee.

This state is not authentication, transport, or generic command failure. Recent accepted records remain visible.

`source_history_limited` does **not** automatically receive the 100-record product convention. Any normal target whose interval-safe coverage was already proven remains valid. Otherwise affected statistics are incomplete/unavailable with a warning, unless a separate proven shorter interval exists.

## Decision 6: Vendor protocol facts are researched before implementation is locked

For each relevant model/family, inspect current source and use read-only live research where source/fixtures are insufficient to establish:

- call-log endpoint/command;
- actual ordering key;
- maximum batch/page size;
- pagination/cursor/start/offset behavior;
- clean EoJ indication;
- repeated-page/no-progress behavior;
- stable record identity if available;
- raw timestamp/duration encoding;
- active-call representation if present;
- reliable codec-local time acquisition;
- any interval-safe invariant used to claim normal full-period coverage.

Live research is observational and read-only. It SHALL NOT place calls, delete history, alter time/configuration, or mutate credentials. Production IPs, credentials, cookies, tokens, captures, HAR files, or sensitive response bodies are not repository artifacts.

A device with only a few recent records is sufficient to establish observable wire behavior. Synthetic tests prove unavailable 100+/old/no-progress/boundary cases.

## Decision 7: Hard-cap 100 uses the agreed product-limit degradation convention

This rule is intentionally different from full-period completeness.

When the 100th accepted record is reached before the normal 90-day acquisition goal completes, acquisition stops immediately. The application defines the capped available-history interval as:

```text
available_lower_bound = oldest_of_100.start_at
available_interval    = [available_lower_bound, reference_now]
```

No additional interval-safe proof is required for `available_lower_bound`. The statistic is explicitly a **calculation from the accepted history limited to 100 records**, not a claim that all device calls intersecting that interval are known.

The application calculates numerator and denominator from the accepted records and this exact interval, and shows a non-modal warning that history depth was limited to 100 records.

The displayed day count is the inclusive number of calendar dates touched from `oldest_of_100.start_at.date()` through `reference_now.date()`.

Product presentation rules are fixed:

- If the oldest accepted record reaches at least 90 calendar dates back, show normal `30 days` and `90 days` rows using the capped dataset and display the 100-record history-limit warning.
- If the capped available interval touches at least 30 but fewer than 90 calendar dates, show `30 days` plus one actual-day row for the capped interval, for example `47 days`.
- If the capped available interval touches fewer than 30 calendar dates, show exactly one actual-day row, for example `18 days`, rather than duplicate 30/90 rows.

The 30-day row in the second case is part of the same explicitly capped-data product convention when normal interval-safe completeness has not independently been proven. The warning makes clear that the source dataset itself was capped at 100 records.

A partial first weekday still contributes a full eight hours to the denominator even though numerator arithmetic begins at the exact oldest accepted timestamp.

This convention applies only to `product_limit_reached == 100`. It SHALL NOT be silently reused for `source_history_limited`, typed failure, or any smaller arbitrary batch.

## Decision 8: Calendar authority is codec time with explicit system fallback

Preferred `reference_now` is the codec's own current local date/time obtained through a reliable read-only mechanism. Call timestamps and `reference_now` are normalized onto one coherent calendar basis.

If reliable codec time is unavailable, use computer-local current time and show an explicit non-modal warning that system time was used.

For normal target period `N` (`30` or `90`):

```text
period_end   = reference_now
period_start = 00:00:00 on reference_now.date - (N - 1) calendar days
```

Today is included and is not prorated.

## Decision 9: Numerator follows literal completed-record overlap

A completed record with valid start and non-negative duration participates regardless of success/failure/unanswered state or direction.

For each eligible completed record:

```text
call_end = start_at + duration_seconds
counted_duration = duration(intersection([start_at, call_end], calculation_interval))
```

A boundary-crossing call contributes only the in-interval overlap. Night, weekend, and holiday time remains eligible numerator time.

An active record remains in chronology, may occupy preview/latest-20 positions, counts toward the 100-record ceiling, is visibly marked `Активный`, and contributes zero until completed on a later fresh load.

A record with unavailable/unparseable duration remains visible, contributes zero, and causes an explicit partial-calculation warning. One malformed record does not fail the journal.

Distinct overlapping records are summed independently; no interval union occurs. Utilization may therefore exceed 100%.

## Decision 10: Denominator is touched weekdays times eight hours

For any calculation interval:

```text
working_capacity_hours = 8 * count(touched calendar dates whose weekday is Monday..Friday)
utilization_percent = 100 * counted_call_hours / working_capacity_hours
```

Rules:

- Saturday/Sunday add zero denominator hours.
- Monday-Friday each add exactly eight hours.
- Public holidays and shifted workdays are ignored.
- Calls are not clipped to a nominal 09:00-17:00 range.
- Today contributes the full eight hours when it is a weekday, regardless of current clock time.
- A degraded/capped interval beginning partway through a weekday gives that touched day the full eight-hour denominator.
- If no weekdays are touched, retain calculated usage duration but display percentage as unavailable with an explanatory warning.
- Hours display with one decimal place; percentage displays as a whole number and is never clamped to 100%.

## Decision 11: Clean empty history and partial failures are isolated

A successful empty journal with clean EoJ is valid complete data and produces normal 30-day and 90-day `0.0 hours / 0%` rows.

A typed deep-retrieval failure does not discard recent records. Any normal target already interval-safe proven remains authoritative; unproven longer targets are incomplete/unavailable with a warning.

`source_history_limited` follows Decision 5. `product_limit_reached` follows Decision 7. These outcomes are deliberately distinct.

## Decision 12: GUI has two loading stages and no disclosure refetch

Initial open shows:

```text
Загрузка журнала звонков...
```

After recent rows can be shown while deeper history/statistics work continues:

```text
Расчёт статистики использования...
```

Completed information hierarchy is conceptually:

```text
latest call row 1
latest call row 2
usage summary row(s)
Журнал звонков   [collapsed by default]
```

Warnings for system-time fallback, 100-record cap, malformed duration, source limitation, or partial retrieval are non-modal and redacted.

Expand/collapse uses already loaded data and causes no network query. Reopening the dialog starts a new fresh acquisition; no cross-open history cache is introduced.

## Decision 13: Existing Huawei and Polycom lifecycle ownership remains authoritative

Huawei TE20/TE40/Bar310/Box310 deep call-history work remains read-only on the shared interactive-session/controller path with existing bounded invalid-session reconnect/replay semantics.

Polycom RPG310 call-history work remains owned by its short-lived dedicated call-log worker/session path.

The common boundary is normalized history/statistics, not network ownership.

All handler acquisition, device-time reads, history I/O, pagination, recovery, and cleanup execute outside the Qt GUI thread. Stale callbacks are rejected under existing currentness rules.

Credential selection/fallback remains application/composition-owned. Call-log strings, HTTP-status text, participant names, or GUI warnings do not become credential-fallback signals. Secrets remain redacted.

## Decision 14: Testing separates protocol reality from deterministic edge cases

Synthetic automated coverage must prove at minimum:

- normal 30/90 calendar boundaries and inclusion of today;
- hidden older long call showing why `start_at < boundary` is insufficient for normal full coverage;
- clean EoJ semantics and successful empty journal;
- exact hard stop at 100 with no 101st accepted record;
- hard-cap `47 days -> 30 + 47` behavior;
- hard-cap `18 days -> one 18-day row` behavior;
- hard-cap oldest record at Monday 15:00: numerator starts exactly 15:00 and Monday contributes full 8h denominator;
- hard-cap degradation without an interval-safe proof for the capped lower bound;
- `source_history_limited` from repeated page/no progress remaining distinct from hard-cap degradation;
- active, malformed-duration, overlapping, success/failure/unanswered, incoming/outgoing records;
- weekend/night numerator inclusion and >100% percentage;
- codec-time authority and system-time fallback;
- partial deep failure preserving recent rows and already proven normal statistics;
- latest-two preview, collapsed latest-20 total, fewer-than-20 behavior, loading stages, warnings, no disclosure refetch, fresh later open;
- Huawei shared-session ownership/recovery and Polycom dedicated-worker ownership;
- no GUI-thread network I/O and no stale publication.

Live validation confirms only observable protocol assumptions. Missing edge cases on real devices are not waived; synthetic tests remain deterministic authority for those algorithmic contracts.

## Archive applicability

This change adds a new root capability. Independent validation must perform the repository-required disposable archive-applicability check from the exact current remote feature HEAD before any `READY FOR ARCHIVE` decision, inspect the prospective archive/root-spec delta against then-current root specs, and discard the disposable archive output without publishing it.
