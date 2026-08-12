# Design: Codec call-log usage statistics

## Context

The codec page currently exposes `Журнал звонков` for exactly five diagnostic models:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

`CallLogWindow` currently renders one four-column table and truncates presentation to ten rows. The handler boundary returns display-oriented dictionaries containing room/call number, formatted start time, formatted duration, and formatted speed. Those strings are sufficient for the existing table but are not a reliable basis for interval arithmetic.

The protocol paths are intentionally different. TE20, TE40, Bar 310, and Box 310 call-log reads run through the shared Huawei interactive-session controller and its approved bounded invalid-session recovery. Polycom call-log loading remains a separate short-lived worker operation and must not be moved into the Huawei/shared interactive-session path. This change preserves those ownership rules.

Current source also demonstrates that retrieval depth is not yet a generic contract. Polycom explicitly requests `limit=10`; Huawei handlers expose model-specific call-record endpoints/parsers. The real devices available for implementation research may have only a small or recent journal, so live validation can establish wire/protocol behavior but cannot be the sole proof for 30/90-day or 100-record edge cases.

A further correctness constraint is that call-log ordering alone does not automatically prove interval completeness. If a source is ordered only by call start time, seeing one record whose `start_at` lies before a requested boundary does not prove that an unseen still-older record cannot have a long duration that crosses back into the requested period. Because this change intentionally sums separate overlapping records independently, coverage must be proven by an interval-safe protocol/query invariant rather than inferred from one old start timestamp.

## Goals

1. Provide one identical call-log/statistics presentation for all five currently supported codec models.
2. Introduce machine-readable normalized call history while retaining the existing four visible fields.
3. Calculate 30-day and 90-day codec usage according to the agreed calendar/weekday rules.
4. Bound deep retrieval to at most 100 accepted call-log records per explicit dialog load.
5. Stop retrieval early only when interval-safe coverage is proven or another explicit terminal condition is reached.
6. Distinguish clean end-of-journal, product record limit, source-history limitation/no-progress, and typed operational failure.
7. Degrade transparently only when the shortened interval itself is proven complete; never manufacture a complete-looking percentage from unproven history.
8. Keep literal device call-log semantics, including failed/unanswered records and legitimate overlapping records.
9. Keep active calls visible but out of completed-usage totals.
10. Preserve Huawei and Polycom session/worker ownership, typed failures, stale suppression, credential authority, and background-only network I/O.
11. Make real-device protocol validation useful without requiring devices to contain artificial 100-call or 90-day histories.

## Non-goals

- Do not add call-log support to a new codec model.
- Do not change codec identity/model recognition or equipment-inventory matching.
- Do not unify Polycom call-log transport ownership with Huawei interactive sessions.
- Do not move credential selection, credential fallback, or successful-profile memory into handlers, workers, dialogs, or call-log calculation code.
- Do not change transport retry or state-changing operation policy.
- Do not create or mutate calls on real devices merely to manufacture validation history.
- Do not infer Russian public holidays or shifted working days.
- Do not interpret a quiet period as unavailable history when the protocol has returned clean end-of-journal.
- Do not merge simultaneous legitimate call-log records into one occupied-time interval.
- Do not persist call history across separate explicit dialog openings in this change.
- Do not change Graphify artifacts or make Graphify part of validation.

## Decision 1: Presentation support remains a closed five-model set

This capability applies exactly to the five models that already expose `Журнал звонков`:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

All five SHALL present the same external dialog structure and the same calculation semantics. Vendor differences SHALL be isolated behind model-specific read-only retrieval/parsing and normalization boundaries.

The dialog SHALL preserve the existing visible call fields:

```text
Номер комнаты
Дата и время начала
Продолжительность
Скорость
```

The top of the dialog SHALL show up to the two newest call-log records as two always-visible rows. Below the usage summary, an initially collapsed expandable section labelled `Журнал звонков` SHALL expose up to the latest 20 records total. Those 20 include the two preview records; they are not 20 additional records. If fewer than 20 records exist, every available record is shown and no placeholder rows are added.

## Decision 2: Retrieval produces a machine-readable normalized snapshot

Usage calculation SHALL NOT parse the existing user-facing date or duration strings back into machine values. Each model-specific call-log boundary SHALL normalize enough information for a common immutable snapshot equivalent to:

```text
reference_now              codec-local current datetime when reliable,
                           otherwise computer-local current datetime
reference_time_source      device | system_fallback
records[]:
  source_identity          optional opaque vendor record identity
  start_at                 normalized local datetime in the same calendar basis
  duration_seconds         non-negative numeric duration, or unavailable
  active                   boolean
  room_number              presentation value
  speed                    presentation value
  existing display fields as needed
termination_reason         coverage_proven | source_ended | product_limit_reached |
                           source_history_limited | operational_failure
coverage_lower_bound       optional timestamp only when interval-safe coverage is proven
coverage_basis             optional non-secret protocol/query invariant identifier
warnings[]                 non-secret structured completeness/parse/time warnings
```

The exact Python shape is an implementation choice, but arithmetic fields SHALL remain machine-readable until presentation formatting. Completeness SHALL be represented explicitly; it SHALL NOT be inferred later from record count or the oldest visible timestamp alone.

A transport pagination boundary MAY repeat an already returned source record. The retrieval layer SHALL suppress only duplicates proven to be the same vendor/source record, using a stable vendor identity when available or an exact pagination-overlap identity established for that protocol. It SHALL NOT semantically deduplicate separate legitimate call-log entries merely because their times, participants, or intervals overlap.

The accepted-record ceiling counts visible journal records including active records and records with an unavailable duration. It does not count a transport duplicate that has been proven to be the same source record repeated across pages.

## Decision 3: Coverage proof is interval-safe, not start-time-based

A requested interval lower bound `B` is `coverage_proven` only when researched source/query semantics establish that no not-yet-retrieved older source record can overlap `B`.

The following fact alone is explicitly insufficient:

```text
oldest_retrieved.start_at < B
```

For example, if records are sorted only by `start_at`, the sequence may contain:

```text
boundary B: 10:00
record A: start 09:00, duration 20 min
record B: start 08:00, duration 3 h
```

Observing record A does not authorize an early stop because unseen record B still overlaps the interval after 10:00.

An interval-safe proof MAY come from a researched and testable invariant such as:

- source/query ordering by call end time where every not-yet-retrieved entry is guaranteed to end at or before the proof boundary;
- a server-side range/query contract that explicitly returns every record intersecting the requested interval;
- another vendor-specific ordering plus duration/continuation guarantee that is strong enough to prove no unseen record can overlap the lower bound.

The implementation SHALL NOT invent such an invariant from typical behavior, one sample capture, or chronological appearance. It must be established by current source/documentation or read-only live protocol research and encoded in focused tests.

If no interval-safe invariant is available, retrieval SHALL NOT stop merely because start times have crossed the 30- or 90-day boundary. It SHALL continue until clean end-of-journal, the 100-record product ceiling, structured source-history limitation/no-progress, or typed operational failure.

## Decision 4: Deep retrieval is newest-first and hard-bounded at 100 records

Each explicit dialog opening starts a fresh read-only call-history acquisition. The implementation SHALL request records newest-first, using the model's actual supported limit/pagination/cursor mechanism established by source plus read-only protocol research.

Retrieval SHALL stop at the first applicable boundary:

1. interval-safe coverage of the 90-day lower bound is proven;
2. the protocol reports clean end-of-journal/no more records;
3. exactly 100 accepted call-log records have been obtained;
4. the source reaches a structured history limitation/no-progress state in which deeper history cannot be obtained and clean EoJ is not proven;
5. a typed operational failure prevents further retrieval.

No implementation path may accept a 101st call-log record merely to improve statistics.

If a fetched page contains records around a target boundary, another request is still required unless the researched protocol invariant already proves that unseen older records cannot overlap that boundary. A page containing one `start_at` before the boundary is not itself sufficient proof.

An authoritative protocol end-of-journal is treated, by product decision, as `there were no older calls` for this capability. The application SHALL NOT attempt to infer an undocumented retention policy. Therefore an early clean end-of-journal does not by itself degrade the requested 30/90-day periods.

## Decision 5: Source-history limitation/no-progress is distinct from clean EoJ and operational failure

Some devices may expose only a fixed batch, ignore pagination parameters, repeat the same page, or provide no protocol indication that the returned batch is the complete journal. These states SHALL NOT be silently converted to clean end-of-journal and SHALL NOT trigger an unbounded retry loop.

The acquisition boundary SHALL produce a structured `source_history_limited` outcome when, after bounded protocol-specific continuation attempts, it cannot obtain older unique records and cannot prove clean EoJ. Examples include:

- pagination/cursor/offset is unsupported for the current firmware;
- the server ignores a continuation parameter and repeats the same source page;
- the next-page/cursor operation makes no progress in unique source identity or interval coverage;
- the device exposes a documented/observed fixed maximum retained/result batch without an EoJ guarantee.

`source_history_limited` is not an authentication, transport, or generic command failure. Recent accepted records remain usable. Any target interval whose coverage was already independently proven remains authoritative. An unproven target SHALL NOT be shown as a normal complete percentage.

If an actual shortened lower bound has interval-safe coverage proof, the GUI MAY present the same actual-period degradation semantics used for a safely truncated product-limit case, with a source-history limitation warning. If no shortened interval can be proven complete, the journal remains visible but affected statistics are explicitly incomplete/unavailable rather than numerically authoritative.

## Decision 6: Vendor protocol details are established before implementation is locked

The common architecture deliberately does not invent undocumented vendor pagination, coverage, or device-time parameters. Before changing each model-specific retrieval path, the implementation session SHALL inspect current source and, where source/documented fixtures are insufficient, perform read-only live research against the available device family to establish:

- actual call-log request endpoint/command used by current firmware;
- ordering key of returned records, including whether ordering is by start time, end time, ID, or another value;
- maximum/accepted page or batch size;
- pagination/cursor/start/offset semantics, if any;
- exact clean end-of-journal indication, if any;
- no-progress/repeated-page behavior and how it can be detected safely;
- stable record identity, if exposed;
- raw start-time and duration formats;
- active-call representation, if the call log exposes one;
- how codec-local current date/time can be obtained reliably;
- whether call timestamps are absolute epochs, local wall-clock values, or otherwise encoded;
- the exact interval-safe invariant, if any, that permits coverage proof before clean EoJ.

The resulting implementation SHALL keep `reference_now` and `start_at` on one coherent calendar basis. It SHALL NOT silently combine host-local conversion of a vendor epoch with a different device-local calendar boundary.

Live research is observational and read-only. It SHALL NOT place calls, delete history, change device configuration, alter device time, or manipulate credentials merely to create test cases. Secrets, production IPs, cookies, tokens, and raw sensitive response bodies SHALL NOT be committed as fixtures or OpenSpec evidence.

A live device with only a handful of recent records is sufficient to validate real request/response, ordering, continuation/no-progress/end behavior, and time encoding that are actually observable. Synthetic fixtures/fakes SHALL provide deterministic proof for unavailable live edge cases such as 100+ records, hidden long boundary-crossing records, repeated pages, and 90-day history.

## Decision 7: Calendar authority is codec time with explicit system-time fallback

For every load, the preferred calculation reference is the codec's own current local date/time obtained through a reliable read-only device mechanism. Calendar boundaries and `today` are defined from that value.

If codec current time cannot be obtained reliably, the application SHALL use the computer's current local date/time as `reference_now` and SHALL expose a non-modal warning in the call-log dialog that system time was used as fallback.

For a normal target period of `N` days, where `N` is 30 or 90:

```text
period_end   = reference_now
period_start = 00:00:00 on the calendar date (reference_now.date - (N - 1) days)
```

Thus the current calendar date is included. The current day is not prorated.

## Decision 8: Usage numerator follows literal completed call-log duration and interval overlap

A completed call-log record participates in a calculation whenever it has a valid start timestamp and a valid non-negative duration. Successful, unanswered, failed, incoming, and outgoing records are treated alike; outcome text is not a filter.

For each eligible completed record:

```text
call_end = start_at + duration_seconds
counted_duration = duration(intersection([start_at, call_end], calculation_interval))
```

Only that temporal intersection contributes. A call that starts before a period boundary and ends after it contributes only the part after the boundary. A call extending past `reference_now` contributes only through `reference_now` if it is nevertheless represented as a completed record with such timestamps.

An active record remains in chronological presentation and counts toward the 100-record acquisition ceiling, but it contributes zero usage until it becomes a completed record on a later fresh load.

If a visible record lacks a parseable duration, the record remains visible, contributes zero to the total, and the affected statistics SHALL carry a warning that one or more records could not be included. One malformed-duration record SHALL NOT fail the entire journal.

Separate legitimate records are summed independently even when their intervals overlap. No interval union is performed. Consequently the usage numerator, and therefore utilization percentage, may exceed wall-clock occupancy and may exceed 100%.

## Decision 9: Working-capacity denominator is weekday-count times eight hours

For any calculation interval, normative working capacity is:

```text
working_capacity_hours = 8 * number_of_calendar_dates_in_interval_whose_weekday_is_Monday_through_Friday
utilization_percent = 100 * counted_call_hours / working_capacity_hours
```

Rules are intentionally simple:

- Saturday and Sunday contribute zero denominator hours.
- Monday through Friday each contribute exactly eight denominator hours.
- Russian public holidays and shifted working days are ignored.
- Call duration is not clipped to a notional 09:00-17:00 working interval.
- Night, evening, weekend, and holiday calls still contribute fully to the numerator when inside the calculation interval.
- If today is Monday-Friday, today contributes the full eight hours even when `reference_now` is early in the day.
- In a proven degraded interval beginning at an exact timestamp partway through a weekday, that touched weekday still contributes the full eight hours.

If an interval contains zero Monday-Friday dates, the implementation SHALL avoid division by zero and SHALL present the utilization percentage as unavailable with an explanatory warning while still presenting the calculated usage duration.

Hours are formatted for display with one decimal place. Percentage is rounded/formatted as a whole percent. Percentage SHALL NOT be clamped to 100%.

## Decision 10: The 100-record ceiling has explicit, proof-aware degradation semantics

The normal desired summaries are 30 days and 90 days. Reaching the 100-record ceiling stops acquisition immediately, but it does not by itself prove any calculation lower bound.

The agreed actual-period degradation remains valid only when the exact shortened lower bound is interval-safe/proven. For a product-limit degradation, the desired shortened lower bound is the exact `start_at` timestamp of the oldest accepted record. The implementation MAY publish that degraded statistic only if the researched source/query invariant proves that no unseen older record can overlap that exact timestamp.

When such proof exists:

- the degraded interval begins at the exact oldest accepted record timestamp and ends at `reference_now`;
- its label day count is the inclusive number of calendar dates touched from `oldest.start_at.date()` through `reference_now.date()`;
- arithmetic uses the exact timestamp interval;
- the denominator counts every touched Monday-Friday calendar date as a full eight-hour day.

Presentation rules for proven intervals are:

- If the complete 90-day window is proven, show normal 30-day and 90-day rows.
- If the complete 30-day window is proven and the exact oldest-record shortened interval is also proven but the 90-day window is not, show one normal 30-day row plus one degraded row labelled with the actual covered calendar-day count, for example 47 days.
- If the exact oldest-record shortened interval is proven but the 30-day window is not, show exactly one degraded row rather than two duplicate rows derived from the same interval.
- Every product-limit degraded row carries a clear warning that depth was limited by the 100-record ceiling.

If the 100-record ceiling is reached and no interval-safe proof exists for the target or shortened interval, the application SHALL preserve the journal but mark the affected statistic incomplete/unavailable. It SHALL NOT present a percentage that looks authoritative merely because 100 records span a certain number of start-date calendar days.

## Decision 11: Clean source end and empty history are valid complete data

If the codec reports clean end-of-journal before 30 or 90 calendar days are reached, the application treats all older time in those requested windows as zero call usage. Both requested windows remain complete under the product's simplified source-end rule.

A successful empty journal therefore produces normal full-period rows equivalent to:

```text
last 30 days: 0.0 hours, 0%
last 90 days: 0.0 hours, 0%
```

subject only to the zero-working-days guard, which is not expected for 30/90-day windows.

No `Недостаточно данных` warning is emitted solely because the source contains fewer than 20 or fewer than 100 records or because clean end-of-journal occurs early.

## Decision 12: The GUI has two loading stages and partial-result isolation

An explicit call-log open SHALL show `Загрузка журнала звонков...` while the initial journal request is pending. Once enough current data is available to render the recent records, the dialog MAY publish the preview/list and SHALL show `Расчёт статистики использования...` while deeper history acquisition and/or calculation continues.

When complete, the dialog contains in this conceptual order:

```text
latest call row 1
latest call row 2
usage summary row(s)
Журнал звонков   [collapsed by default]
```

Exact spacing, typography, disclosure control, and card/row widgets MAY be adapted to the existing GUI style, but the information hierarchy and semantics above are required.

The expanded `Журнал звонков` uses already acquired data from the current load and performs no extra network query merely because the disclosure control was toggled. Reopening the dialog explicitly begins a fresh load; this change introduces no cross-opening history cache.

A deep-history failure or source-history limitation SHALL NOT discard already accepted recent records. A statistic whose lower-bound coverage had already been proven remains valid. An unproven statistic is warned/incomplete rather than silently calculated from a partial set.

Warnings for system-time fallback, product-limit degradation, source-history limitation/no-progress, malformed durations, or incomplete retrieval SHALL be non-secret and non-modal. They SHALL NOT convert otherwise usable recent call history into a modal operation failure.

## Decision 13: Existing Huawei and Polycom lifecycle ownership is preserved

For Huawei TE20, TE40, CloudLink Bar 310, and CloudLink Box 310, call-history acquisition SHALL remain a read-only operation on the existing shared interactive-session/controller path. A confirmed invalid cached session continues to use the approved single reconnect-and-replay recovery. Deep retrieval SHALL NOT introduce handler-owned credential iteration or an unbounded reconnect loop.

For Polycom RPG 310, call-history acquisition SHALL remain owned by the existing short-lived Polycom call-log worker/session path. It SHALL NOT be routed through the Huawei/shared call-log controller merely to share statistics code.

The common code boundary is normalized history and calculation, not network ownership.

All blocking handler acquisition, device-time reads, history I/O, pagination, bounded recovery, and disconnect/cleanup SHALL execute outside the Qt GUI thread. Stale operation/context results SHALL be rejected under the existing screen/controller currentness rules before they can update a replaced dialog/context.

Credential selection/fallback remains application/composition-owned. No call-log payload string, HTTP code text, participant name, or warning text may become credential-fallback authority. Secrets remain redacted from logs, public errors, GUI warnings, and normalized presentation payloads.

## Decision 14: Testing separates protocol reality from deterministic algorithm coverage

Focused automated tests SHALL use fake handlers/sessions and synthetic call records to prove, at minimum:

- identical supported-model presentation contract;
- latest-two preview and collapsed latest-20 total behavior, including fewer than 20 records;
- newest-first ordering;
- normal 30-day and 90-day boundaries including current date;
- codec-time authority and explicit computer-time fallback warning;
- a call crossing a period boundary contributing only overlap;
- full inclusion of weekend/night call duration in the numerator;
- Monday-Friday-only denominator with eight full hours per touched weekday;
- current weekday and partial first proven degraded weekday both contributing full eight hours;
- whole percentages above 100% without clamping;
- active record visible and counted toward the 100-record cap but excluded from usage;
- successful/unanswered/failed/incoming/outgoing literal records being treated equally;
- legitimate overlapping records summed independently;
- unparseable duration visible, excluded, and warned;
- clean source end before 30/90 days treated as complete zero history before the oldest record;
- successful empty history yielding full-period zero usage;
- interval-safe early-stop proof;
- explicit regression where a more recent record starts before the boundary but an unseen older-start/longer-duration record still overlaps it, proving `start_at < boundary` alone cannot stop retrieval;
- hard stop at exactly 100 accepted records with no 101st accepted record;
- 100-record proven degradation shorter than 30 days producing one degraded row;
- 100-record proven degradation between 30 and 90 days producing one full 30-day row plus one degraded longer row;
- 100-record stop without coverage proof preserving journal but marking affected statistics incomplete;
- `source_history_limited` for unsupported/ignored pagination and repeated-page/no-progress behavior without unbounded retry;
- source-history limitation preserving any already proven statistic and marking only unproven statistics incomplete;
- a deep retrieval operational failure preserving already loaded journal and any already proven shorter statistic;
- transport/page duplicate suppression without semantic deduplication of distinct calls;
- no refetch on expand/collapse inside one load and a fresh acquisition on a later explicit open;
- Huawei invalid-session bounded recovery staying on the shared interactive path;
- Polycom call-log ownership staying on the dedicated worker path;
- no blocking network work on the Qt GUI thread and no stale callback publication.

Live validation SHALL be observational and SHALL confirm the real protocol facts that are actually observable on available devices, including coverage/no-progress assumptions when they can be established. It is not required to manufacture 100 calls, old calls, active calls, malformed records, or 90 days of history. Missing live edge cases SHALL remain covered by deterministic synthetic tests rather than being waived.

## Archive applicability

This change adds a new root capability. Independent validation must therefore perform the repository-required disposable archive-applicability check from the exact current remote feature HEAD before any `READY FOR ARCHIVE` decision, inspect the prospective archive/root-spec delta against then-current root specs, and discard the disposable archive output without publishing it.
