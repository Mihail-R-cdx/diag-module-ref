# codec-call-log-usage-statistics Specification

## Purpose
TBD - created by archiving change codec-call-log-usage-statistics. Update Purpose after archive.
## Requirements
### Requirement: Codec call history has one normalized presentation and calculation contract

The call-log usage capability SHALL support exactly these existing diagnostic models:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

All supported models SHALL expose the same user-visible call-log hierarchy and usage-calculation semantics. Vendor-specific request, pagination, timestamp, and parser differences SHALL remain behind model-specific read-only retrieval/normalization boundaries.

Each normalized record used for arithmetic SHALL retain machine-readable start time, active/completed state, and non-negative duration in seconds when available. Calculation code SHALL NOT parse GUI-formatted date or duration strings back into arithmetic values.

Visible call fields SHALL remain:

```text
Номер комнаты
Дата и время начала
Продолжительность
Скорость
```

Separate legitimate source records SHALL remain separate even when their intervals overlap. The implementation SHALL NOT merge overlapping calls or filter otherwise valid records because they are incoming, outgoing, successful, unanswered, or failed. Only a duplicate proven to be the same source record repeated by transport/pagination MAY be suppressed.

#### Scenario: Different supported models open the journal

- **WHEN** the operator opens `Журнал звонков` for any supported exact model
- **THEN** the same dialog hierarchy and calculation semantics apply
- **AND** model-specific protocol details do not create different product behavior

#### Scenario: Two legitimate calls overlap

- **GIVEN** two distinct call-log records overlap in time
- **WHEN** usage is calculated
- **THEN** each record contributes its own eligible duration independently
- **AND** the intervals are not unioned

### Requirement: Normal full-period coverage proof is interval-safe

A normal calculation lower bound `B` SHALL be considered fully covered before clean end-of-journal only when current source/documentation or read-only protocol research establishes a testable invariant proving that no not-yet-retrieved older source record can overlap `B`.

The following observation SHALL NOT by itself prove normal full-period coverage:

```text
oldest_retrieved.start_at < B
```

If the source is ordered only by call start time, an unseen record with an even older start and a longer duration may still overlap `B`.

An acceptable early-coverage invariant MAY be based on proven end-time ordering, a server-side interval-intersection query, or another vendor-specific ordering/duration/continuation guarantee that proves unseen records cannot overlap the lower bound. The implementation SHALL NOT invent such an invariant from typical chronological appearance.

This Requirement governs claims that the normal requested 30-day or 90-day interval is complete. It SHALL NOT override the separate product-limit convention defined for exactly 100 accepted records.

#### Scenario: Older-start long call still crosses the normal boundary

- **GIVEN** the normal lower bound is 10:00
- **AND** a retrieved record starts at 09:00 and lasts 20 minutes
- **AND** a not-yet-retrieved record can start at 08:00 and last three hours
- **WHEN** the source is ordered only by `start_at`
- **THEN** observing the 09:00 record does not prove normal coverage of 10:00
- **AND** acquisition does not stop solely because `09:00 < 10:00`

#### Scenario: Protocol proves normal interval coverage

- **GIVEN** researched protocol/query semantics guarantee that every not-yet-retrieved record cannot overlap the requested lower bound
- **WHEN** that invariant becomes true
- **THEN** normal coverage of that lower bound is proven
- **AND** acquisition may stop for that bound

### Requirement: Call-history acquisition is newest-first and limited to 100 accepted records

Every explicit call-log dialog opening SHALL begin a fresh read-only acquisition. The implementation SHALL obtain records newest-first and SHALL stop requesting older history at the first applicable condition:

1. interval-safe coverage of the normal 90-day lower bound is proven;
2. the codec reports clean end-of-journal/no more records;
3. exactly 100 accepted call-log records have been obtained;
4. deeper history reaches structured `source_history_limited`/no-progress without clean EoJ;
5. a typed operational failure prevents continuation.

The product ceiling SHALL be exactly 100 accepted visible call-log records per load. Active records and visible records with unavailable duration SHALL count toward that ceiling. A proven transport duplicate SHALL not count twice. The implementation SHALL NOT accept a 101st record merely to improve statistics.

Clean end-of-journal before a 30-day or 90-day boundary SHALL be treated, by product decision, as meaning the older remainder contains no calls. The application SHALL NOT infer an undocumented retention policy solely from early clean EoJ.

#### Scenario: Normal ninety-day coverage is safely proven before the cap

- **WHEN** interval-safe protocol semantics prove normal coverage of the 90-day lower bound before 100 accepted records are needed
- **THEN** no further history request is issued
- **AND** normal 30-day and 90-day statistics may be calculated

#### Scenario: The hundredth accepted record is reached first

- **WHEN** the 100th accepted record is reached before acquisition otherwise completes
- **THEN** acquisition stops immediately
- **AND** no 101st record is accepted
- **AND** statistics follow the product-limit degradation contract rather than requiring another completeness proof for the capped lower bound

### Requirement: Source-history limitation or no progress is explicit and distinct from the product cap

When deeper history cannot be obtained and clean end-of-journal has not been proven, acquisition SHALL produce structured `source_history_limited` rather than silently declaring history complete or retrying without bound.

This includes bounded cases where:

- pagination/cursor/offset is unavailable;
- a continuation parameter is ignored and the same page repeats;
- continuation yields no new unique records and no useful progress;
- a fixed/result-limited source batch is exposed without clean EoJ semantics.

`source_history_limited` SHALL remain distinct from authentication, transport, session, generic command failure, and `product_limit_reached` at exactly 100 accepted records. Already accepted recent records SHALL remain usable.

Any normal target whose interval-safe coverage was already proven before `source_history_limited` SHALL remain authoritative. An unproven target SHALL NOT be displayed as a normal complete percentage. The application SHALL NOT silently apply the hard-cap 100 product convention to a smaller arbitrary source-limited batch.

#### Scenario: Pagination repeats the same page before 100 records

- **GIVEN** continuation returns no new unique source records
- **AND** clean EoJ is not indicated
- **AND** fewer than 100 records have been accepted
- **WHEN** the bounded no-progress rule is reached
- **THEN** acquisition terminates as `source_history_limited`
- **AND** recent records remain visible
- **AND** the result is not treated as the 100-record product degradation

### Requirement: The hard 100-record cap uses the agreed capped-available-history product convention

When `product_limit_reached` occurs at exactly 100 accepted records, the application SHALL intentionally define the available-history interval as:

```text
available_lower_bound = oldest_of_100.start_at
available_interval    = [available_lower_bound, reference_now]
```

No additional interval-safe proof SHALL be required for `available_lower_bound` in this product-limit case. The resulting statistic is explicitly a calculation from the accepted history limited to 100 records; it SHALL NOT be represented as proof that all device calls intersecting that interval are known.

The application SHALL calculate numerator and denominator from the accepted records and the selected capped interval, and SHALL show a clear non-modal warning that history depth was limited to 100 records.

The displayed actual-day count SHALL be the inclusive number of calendar dates touched from `oldest_of_100.start_at.date()` through `reference_now.date()`.

Presentation SHALL follow these rules:

- if the capped available interval reaches at least 90 calendar dates, show `30 days` and `90 days` rows from the capped dataset and show the 100-record warning;
- if the capped available interval reaches at least 30 but fewer than 90 calendar dates, show one `30 days` row plus one actual-day capped row, for example `47 days`;
- if the capped available interval reaches fewer than 30 calendar dates, show exactly one actual-day capped row, for example `18 days`, rather than duplicate 30/90 rows.

The `30 days` row in the middle case MAY be displayed under this explicit capped-data product convention even when normal interval-safe completeness of 30 days has not independently been proven. The warning SHALL make the capped source dataset explicit.

This Requirement applies only when exactly 100 accepted records cause `product_limit_reached`. It SHALL NOT be reused for `source_history_limited`, typed operational failure, or a smaller arbitrary batch.

#### Scenario: One hundred records span forty-seven calendar dates

- **GIVEN** exactly 100 accepted records cause `product_limit_reached`
- **AND** `oldest_of_100.start_at` is 47 calendar dates before `reference_now`
- **WHEN** statistics are rendered
- **THEN** a `30 days` row is shown
- **AND** a `47 days` capped row is shown instead of a `90 days` row
- **AND** both values are calculated from the capped accepted dataset
- **AND** the GUI warns that history was limited to 100 records
- **AND** no additional interval-safe proof is required for the 47-day capped lower bound

#### Scenario: One hundred records span only eighteen calendar dates

- **GIVEN** exactly 100 accepted records cause `product_limit_reached`
- **AND** `oldest_of_100.start_at` is 18 calendar dates before `reference_now`
- **WHEN** statistics are rendered
- **THEN** exactly one `18 days` capped row is shown
- **AND** duplicate 30-day and 90-day rows are not shown
- **AND** the GUI warns that history was limited to 100 records

#### Scenario: Oldest capped record begins Monday at 15:00

- **GIVEN** the capped interval starts at the exact oldest accepted record at 15:00 on Monday
- **WHEN** capped usage is calculated
- **THEN** numerator arithmetic begins at exactly 15:00
- **AND** that Monday contributes the full eight hours to normative working capacity

### Requirement: Calendar periods use codec-local current time with explicit system-time fallback

Preferred `reference_now` SHALL be the codec's own current local date/time obtained by a reliable read-only mechanism. Call timestamps and `reference_now` SHALL be normalized onto one coherent calendar basis.

If codec-local current time cannot be obtained reliably, the application SHALL use computer-local current time and display a non-modal warning that system time was used. The fallback SHALL NOT be silent.

For a normal `N`-day target where `N` is 30 or 90:

```text
period_end   = reference_now
period_start = 00:00:00 on reference_now.date - (N - 1) calendar days
```

The current calendar date is included and is not prorated.

#### Scenario: Reliable codec-local time defines normal calendar periods

- **GIVEN** a reliable read-only codec-local current time is available
- **WHEN** call-log statistics are calculated
- **THEN** that time is used as `reference_now`
- **AND** it determines today and the normal 30-day and 90-day boundaries
- **AND** call timestamps and boundaries remain on the same coherent calendar basis
- **AND** computer-local time does not replace the available codec-local time

#### Scenario: Codec-local time is unavailable

- **GIVEN** codec-local current time cannot be obtained reliably
- **WHEN** call-log statistics are calculated
- **THEN** computer-local current time is used as `reference_now`
- **AND** a clear non-modal system-time fallback warning is displayed
- **AND** the fallback is not silent
- **AND** codec-local and computer-local calendar bases are not mixed

### Requirement: Usage duration counts only completed-record overlap with the calculation interval

For each completed record with valid start time and valid non-negative duration, the application SHALL derive the call interval and add only its temporal intersection with the calculation interval.

A call crossing the beginning of the interval SHALL contribute only the portion inside the interval. Call time at night, on weekends, or on holidays SHALL not be removed from the numerator.

An active call SHALL remain a normal chronological record, MAY occupy preview/latest-20 positions, SHALL count toward the 100-record ceiling, SHALL be visibly marked `Активный`, and SHALL contribute zero usage until it later appears completed.

A record whose duration is missing or unparseable SHALL remain visible, SHALL contribute zero, and SHALL cause an explicit partial-calculation warning for affected statistics. Remaining valid records SHALL still be calculated.

Distinct legitimate overlapping records SHALL be summed independently.

#### Scenario: Call crosses the 30-day boundary

- **GIVEN** a completed call starts before the 30-day period start and ends after it
- **WHEN** 30-day usage is calculated
- **THEN** only the in-period overlap contributes

#### Scenario: Active call is newest

- **WHEN** the newest source record is active
- **THEN** it remains in normal chronology
- **AND** it is marked `Активный`
- **AND** it contributes zero to usage totals
- **AND** it counts toward the 100-record ceiling

### Requirement: Working-time percentage uses eight hours for every touched Monday-through-Friday date

For every calculation interval, normative working capacity SHALL be equivalent to:

```text
working_capacity_hours = 8 * count(touched calendar dates whose weekday is Monday..Friday)
utilization_percent = 100 * counted_call_hours / working_capacity_hours
```

Saturday and Sunday SHALL contribute zero denominator hours. Monday through Friday SHALL each contribute exactly eight hours. Russian public holidays and shifted working days SHALL be ignored.

The numerator SHALL not be clipped to a notional working-day clock range. Calls at night, in the evening, on weekends, or on holidays remain fully eligible when inside the interval.

If the current date is Monday-Friday, it SHALL contribute the full eight hours regardless of current clock time. When a capped/degraded interval starts partway through a weekday, that touched first date SHALL also contribute the full eight hours.

Usage hours SHALL display with one decimal place. Utilization SHALL display as a whole percent and SHALL NOT be clamped to 100%. If an interval touches zero Monday-Friday dates, the application SHALL avoid division by zero, retain calculated duration, and mark percentage unavailable with an explanatory warning.

#### Scenario: Degraded interval begins partway through a weekday

- **GIVEN** a capped or degraded calculation interval begins at 15:00 on Monday
- **WHEN** usage is calculated
- **THEN** numerator arithmetic begins at the exact 15:00 timestamp
- **AND** that touched Monday contributes the full eight hours to the denominator

#### Scenario: Calculation interval touches no weekdays

- **GIVEN** a calculation interval touches only Saturday and Sunday
- **WHEN** usage is calculated
- **THEN** working capacity is zero hours
- **AND** division by zero does not occur
- **AND** calculated usage duration is retained
- **AND** utilization percentage is displayed as unavailable
- **AND** the user receives an explanatory warning

### Requirement: Clean empty history and partial retrieval outcomes remain usable

A successful empty journal with clean EoJ SHALL be valid complete data and SHALL produce normal 30-day and 90-day zero-usage rows.

A typed operational failure during deeper retrieval SHALL NOT discard already accepted recent records. Any normal target whose interval-safe coverage was already proven SHALL remain authoritative. Unproven longer targets SHALL be marked incomplete/unavailable with a non-secret warning.

`source_history_limited` SHALL follow its separate Requirement. `product_limit_reached` at 100 SHALL follow the capped-data Requirement. These outcomes SHALL NOT be conflated.

#### Scenario: Journal is successfully empty

- **WHEN** the codec successfully reports an empty journal and clean EoJ
- **THEN** the normal 30-day row shows `0.0` hours and `0%`
- **AND** the normal 90-day row shows `0.0` hours and `0%`

### Requirement: Call-log dialog shows two preview rows, usage summary, and a collapsed latest-twenty journal

The dialog SHALL show up to the two newest call records as always-visible rows using the existing four fields. Applicable usage row(s) SHALL appear below the preview.

The dialog SHALL contain an initially collapsed expandable section labelled exactly `Журнал звонков`. When expanded, it SHALL show at most the latest 20 records total, including the same preview records. If fewer than 20 exist, all available records SHALL be shown with no artificial empty rows.

The initial loading state SHALL display `Загрузка журнала звонков...`. After recent call data can be presented and while deeper history/statistics work remains, the dialog SHALL display `Расчёт статистики использования...`.

Expanding/collapsing within the current load SHALL use already acquired data and SHALL NOT trigger another device request. A later explicit opening SHALL start a fresh acquisition; no cross-open call-history cache is introduced.

Warnings for system-time fallback, hard-cap 100, malformed duration, source limitation, or partial retrieval SHALL be non-modal, non-secret, and clear.

#### Scenario: Codec has seven records

- **WHEN** seven records finish loading
- **THEN** the two newest are always visible
- **AND** expanding `Журнал звонков` shows all seven
- **AND** no blank rows are added

### Requirement: Existing Huawei and Polycom call-log lifecycle ownership remains authoritative

For `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, and `CloudLink Box 310`, call-history acquisition SHALL remain read-only work on the existing shared Huawei interactive-session/controller path. Existing approved invalid-cached-session recovery remains bounded: reconnect once and replay the read once. Deep history SHALL NOT create handler-owned credential iteration or an unbounded reconnect/login loop.

For `Polycom RPG 310`, call-history acquisition SHALL remain owned by the existing short-lived Polycom call-log worker/session path and SHALL NOT be routed through the Huawei/shared controller merely to share history/statistics code.

The common boundary SHALL be normalized history/statistics, not network-session ownership.

All handler acquisition, device-time reads, history requests, pagination, bounded recovery, and network/session cleanup SHALL execute outside the Qt GUI thread. Existing currentness/stale-result rules SHALL prevent superseded results from updating a replaced context.

Credential selection/fallback SHALL remain application/composition-owned. Call-log strings, HTTP-status text, participant names, or GUI warnings SHALL NOT become credential-fallback signals. Secrets SHALL remain redacted.

#### Scenario: Huawei-family call history remains on the shared interactive path

- **GIVEN** call history is requested for `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, or `CloudLink Box 310`
- **WHEN** acquisition needs history work or bounded invalid-session recovery
- **THEN** the existing shared interactive-session/controller path remains the owner
- **AND** reconnect and replay remain bounded to one reconnect and one replay
- **AND** the handler does not start its own credential fallback
- **AND** credential selection and fallback remain application/composition-owned

#### Scenario: Polycom call history remains on its dedicated worker path

- **GIVEN** call history is requested for `Polycom RPG 310`
- **WHEN** acquisition is performed
- **THEN** the existing short-lived dedicated Polycom call-log worker/session remains the owner
- **AND** the operation is not routed through the Huawei/shared interactive controller
- **AND** only normalized history and statistics are shared across the model boundaries

### Requirement: Real-device validation proves protocol facts while offline tests prove bounded edge cases

Implementation and independent validation SHALL use read-only live device access, when the relevant physical device is available, to confirm observable protocol facts such as request success, record shape/order, pagination/end/no-progress, timestamp encoding, codec-local time acquisition, and any claimed normal full-coverage invariant.

Live validation SHALL NOT require 100 calls, 90-day history, an active call, a malformed record, or another accidental edge case. It SHALL NOT manufacture those cases by placing calls, deleting history, changing time/configuration, or altering credentials.

Deterministic automated regression coverage SHALL use synthetic histories and fake handlers/sessions to prove the 100-record ceiling, `30 + 47`, single `18`, exact partial-first-weekday behavior, hidden long boundary-crossing records for normal coverage, source no-progress, active/malformed/overlapping records, empty history, time fallback, lifecycle ownership, stale suppression, partial failure, and GUI behavior.

Production IP addresses, credentials, tokens, cookies, raw device captures, or sensitive response bodies SHALL NOT be committed as fixtures or validation artifacts.

#### Scenario: A live device has only a small recent journal

- **GIVEN** read-only live validation accesses a device with only a small or recent journal
- **WHEN** the observed protocol behavior is recorded
- **THEN** validation may prove request success, response and record shape, ordering, pagination or cursor or offset behavior, clean end-of-journal, repeated-page or no-progress behavior, timestamp and duration encoding, and codec-local time retrieval
- **AND** it may prove the normal full-coverage invariant only when that invariant is actually observable and established
- **AND** it does not require the device to contain 100 calls, 90 days of history, an active call, malformed duration, or other synthetic edge cases
- **AND** those bounded edge cases are proved with deterministic synthetic histories, fake handlers, or fake sessions
- **AND** live validation remains read-only and does not place calls, delete history, change device time, configuration, credentials, or validation state
