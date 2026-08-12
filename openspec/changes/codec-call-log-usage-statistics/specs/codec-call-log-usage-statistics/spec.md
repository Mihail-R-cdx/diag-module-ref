# codec-call-log-usage-statistics Specification

## ADDED Requirements

### Requirement: Codec call history has one normalized presentation and calculation contract

The call-log usage capability SHALL support exactly these existing diagnostic models:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

All supported models SHALL expose the same user-visible call-log dialog structure and the same usage-calculation semantics. Vendor-specific request, pagination, timestamp, coverage, and parser differences SHALL remain behind model-specific read-only retrieval/normalization boundaries.

Each normalized record used for calculation SHALL retain a machine-readable start time, active/completed state, and non-negative duration in seconds when available. Calculation code SHALL NOT parse the GUI-formatted date or duration strings back into arithmetic values.

The visible call record SHALL preserve the existing fields:

```text
Номер комнаты
Дата и время начала
Продолжительность
Скорость
```

Separate legitimate source records SHALL remain separate even when their time intervals overlap. The implementation SHALL NOT merge overlapping calls or filter records because they are incoming, outgoing, successful, unanswered, or failed. Only a duplicate proven to be the same source record repeated by the transport/pagination boundary MAY be suppressed.

Acquisition completeness SHALL be explicit. A normalized acquisition result SHALL distinguish at least:

```text
coverage_proven
source_ended
product_limit_reached
source_history_limited
operational_failure
```

and SHALL retain a lower-bound timestamp only when interval-safe coverage of that lower bound is actually proven.

#### Scenario: Different supported models open the journal

- **WHEN** the operator opens `Журнал звонков` for any of the five supported exact models
- **THEN** the same dialog information hierarchy and calculation semantics apply
- **AND** model-specific protocol details are not exposed as different GUI behavior

#### Scenario: Two legitimate calls overlap

- **GIVEN** two distinct call-log records overlap in time
- **WHEN** usage is calculated
- **THEN** each record contributes its own eligible duration independently
- **AND** the intervals are not unioned into one occupied-time interval

#### Scenario: Call outcome differs

- **GIVEN** completed journal records include successful, unanswered, or failed calls and may be incoming or outgoing
- **WHEN** usage is calculated
- **THEN** outcome and direction do not exclude otherwise valid records

### Requirement: Coverage proof is interval-safe and cannot rely only on oldest start time

A calculation lower bound `B` SHALL be considered covered before clean end-of-journal only when current source/documentation or read-only protocol research establishes a testable invariant proving that no not-yet-retrieved older source record can overlap `B`.

The following observation SHALL NOT by itself prove coverage:

```text
oldest_retrieved.start_at < B
```

If the source is ordered only by call start time, an unseen record with an even older start time and a sufficiently long duration may still overlap `B`. Because legitimate overlapping records are summed independently, such a record cannot be ignored.

An acceptable early coverage invariant MAY be based on proven end-time ordering, a server-side query that guarantees all records intersecting the requested interval, or another vendor-specific ordering/duration/continuation guarantee that proves unseen records cannot overlap the lower bound. The implementation SHALL NOT invent such an invariant from typical chronological appearance.

If no interval-safe invariant is established, acquisition SHALL continue past records whose start time is older than the target boundary until another explicit stop condition occurs.

#### Scenario: Older-start long call still crosses the boundary

- **GIVEN** the target lower bound is 10:00
- **AND** a retrieved record starts at 09:00 and lasts 20 minutes
- **AND** a not-yet-retrieved record can start at 08:00 and last three hours
- **WHEN** the source is ordered only by `start_at`
- **THEN** observing the 09:00 record does not prove coverage of 10:00
- **AND** acquisition does not stop solely because `09:00 < 10:00`

#### Scenario: Protocol proves interval-safe coverage

- **GIVEN** researched protocol/query semantics guarantee that every not-yet-retrieved record ends before the target lower bound
- **WHEN** that invariant becomes true for the current acquisition
- **THEN** coverage of that lower bound is proven
- **AND** the application may stop requesting older history for that bound

### Requirement: Call-history acquisition is newest-first and limited to 100 accepted records

Every explicit call-log dialog opening SHALL begin a fresh read-only acquisition. The implementation SHALL obtain records newest-first and SHALL stop requesting older history at the first applicable condition:

1. interval-safe coverage of the 90-day target lower bound is proven;
2. the codec reports clean end-of-journal/no more records;
3. exactly 100 accepted call-log records have been obtained;
4. deeper history reaches a structured `source_history_limited`/no-progress state;
5. a typed operational failure prevents continuation.

The product ceiling SHALL be exactly 100 accepted visible call-log records per load. Active records and visible records with unavailable duration SHALL count toward that ceiling. A transport duplicate proven to be the same source record repeated across pages SHALL not count twice. The implementation SHALL NOT accept a 101st journal record merely to improve statistics.

When clean end-of-journal occurs before a 30-day or 90-day boundary, the application SHALL treat the older remainder of the requested interval as containing no calls. It SHALL NOT infer or warn about an undocumented retention policy solely from an early clean source end.

#### Scenario: Ninety-day coverage is safely proven before the record ceiling

- **WHEN** interval-safe protocol semantics prove coverage of the 90-day lower bound before 100 accepted records are needed
- **THEN** no further history request is issued
- **AND** both normal target periods may be calculated from the accepted history

#### Scenario: The hundredth record is accepted first

- **WHEN** the 100th accepted record is reached before the longest target interval is proven complete
- **THEN** history acquisition stops
- **AND** no 101st record is accepted merely to extend the calculation period
- **AND** affected statistics follow the proof-aware product-limit contract

#### Scenario: Codec returns no more records early

- **WHEN** the codec reports clean end-of-journal after a small number of records
- **THEN** history acquisition stops
- **AND** older portions of the requested 30/90-day intervals are treated as zero usage
- **AND** the statistic is not degraded solely because the journal ended early

### Requirement: Source-history limitation or no progress is explicit and does not masquerade as clean end-of-journal

When deeper history cannot be obtained and the source has not proven clean end-of-journal, the acquisition SHALL produce a structured `source_history_limited` outcome rather than silently declaring history complete or retrying without bound.

This outcome SHALL include at least protocol cases where:

- pagination/cursor/offset is unavailable for the current source;
- a continuation parameter is ignored and the same page is returned again;
- bounded continuation produces no new unique source records and no interval-coverage progress;
- the source exposes only a fixed/result-limited history batch without a clean EoJ guarantee.

`source_history_limited` SHALL remain distinct from authentication, transport, session, and generic command failures. Already accepted recent records SHALL remain usable.

Any target interval whose lower-bound coverage was already proven before the limitation SHALL remain authoritative. An unproven target interval SHALL NOT be displayed as a normal complete percentage.

If a shorter interval has its own interval-safe proven lower bound, the application MAY display that actual-period statistic with an explicit source-history limitation warning. If no shorter lower bound can be proven complete, the journal SHALL remain visible while the affected statistic is marked incomplete/unavailable.

#### Scenario: Pagination repeats the same page

- **GIVEN** a continuation request returns no new unique source records
- **AND** clean end-of-journal is not indicated
- **WHEN** the bounded no-progress rule is reached
- **THEN** acquisition terminates as `source_history_limited`
- **AND** it does not retry indefinitely
- **AND** it does not treat the repeated page as clean EoJ

#### Scenario: Thirty-day coverage was proven before source limitation

- **GIVEN** interval-safe coverage of the complete 30-day window has already been proven
- **WHEN** deeper retrieval for the longer period becomes `source_history_limited`
- **THEN** the 30-day statistic remains authoritative
- **AND** the unproven longer statistic is incomplete/unavailable unless a shorter proven lower bound exists

### Requirement: Calendar periods use codec-local current time with an explicit system-time fallback

The preferred `reference_now` for call-log usage SHALL be the codec's own current local date/time obtained by a reliable read-only protocol mechanism. Call timestamps and `reference_now` SHALL be normalized onto one coherent calendar basis before period arithmetic.

If codec-local current time cannot be obtained reliably, the application SHALL use the computer's current local date/time as the fallback reference and SHALL display a non-modal warning that system time was used. The fallback SHALL NOT be silent.

For a normal `N`-day target where `N` is 30 or 90:

```text
period_end   = reference_now
period_start = 00:00:00 on reference_now.date - (N - 1) calendar days
```

The current calendar date is therefore included.

#### Scenario: Codec time is available

- **WHEN** the codec supplies reliable current local time
- **THEN** that device-local time defines `today`, the 30-day boundary, and the 90-day boundary
- **AND** the computer's local clock does not replace it

#### Scenario: Codec time is unavailable

- **WHEN** reliable codec-local current time cannot be obtained
- **THEN** the computer's local current time becomes the reference
- **AND** the dialog warns that system time was used
- **AND** call timestamps and boundaries remain on one coherent calculation basis

### Requirement: Usage duration counts only completed-record overlap with the calculation interval

For each completed record with a valid start time and valid non-negative duration, the application SHALL derive the call interval and add only its temporal intersection with the calculation interval.

A call that crosses the beginning of the period SHALL contribute only the portion inside the period. Call time inside nights, weekends, or holidays SHALL not be removed from the numerator.

An active call SHALL remain a normal chronological journal record, MAY occupy one of the two newest preview positions and one of the latest-20 positions, SHALL count toward the 100-record acquisition ceiling, and SHALL contribute zero usage until it appears as a completed record on a later fresh acquisition. Its visible duration/state SHALL clearly indicate `Активный`.

A record whose duration is missing or cannot be parsed SHALL remain visible, SHALL contribute zero usage, and SHALL cause an explicit partial-calculation warning for affected statistics. The remaining valid records SHALL still be calculated.

#### Scenario: Call crosses the 30-day boundary

- **GIVEN** a completed call starts before the 30-day period start and ends after it
- **WHEN** 30-day usage is calculated
- **THEN** only the duration after the period start contributes

#### Scenario: Active call is newest

- **WHEN** the newest source record represents an active call
- **THEN** it remains in its normal chronological preview/journal position
- **AND** it is marked `Активный`
- **AND** it contributes zero to usage totals
- **AND** it still counts toward the 100-record ceiling

#### Scenario: One duration is malformed

- **WHEN** a visible completed record has no parseable duration
- **THEN** that record remains visible
- **AND** it contributes zero to usage totals
- **AND** other valid records remain usable
- **AND** the affected statistics carry a partial-calculation warning

### Requirement: Working-time percentage uses eight hours for every touched Monday-through-Friday date

For every calculation interval, normative working capacity SHALL be equivalent to:

```text
working_capacity_hours = 8 * count(calendar dates touched by the interval whose weekday is Monday..Friday)
utilization_percent = 100 * counted_call_hours / working_capacity_hours
```

Saturday and Sunday SHALL contribute zero denominator hours. Monday through Friday SHALL each contribute exactly eight hours. Russian public holidays and shifted working days SHALL be ignored.

The numerator SHALL not be clipped to a notional working-day clock range. Calls at night, in the evening, on weekends, or on holidays remain fully eligible when they lie inside the calculation interval.

If the current calendar date is Monday through Friday, it SHALL contribute the full eight denominator hours even though `reference_now` is before the end of the day. When a proven degraded interval starts partway through a Monday-through-Friday date, that touched first date SHALL also contribute the full eight hours.

Usage hours SHALL be displayed with one decimal place. Utilization SHALL be displayed as a whole percent and SHALL NOT be clamped to 100%. If an interval has zero Monday-through-Friday dates, the application SHALL avoid division by zero, retain the calculated duration, and mark the percentage unavailable with an explanatory warning.

#### Scenario: Current weekday is only partially elapsed

- **GIVEN** today is a weekday and the current codec time is before the end of the day
- **WHEN** working capacity is calculated
- **THEN** today contributes the full eight hours

#### Scenario: Weekend call occurs

- **GIVEN** an eligible completed call occurs on Saturday
- **WHEN** usage is calculated
- **THEN** its in-period duration contributes to the numerator
- **AND** Saturday contributes zero hours to the denominator

#### Scenario: Utilization exceeds one hundred percent

- **WHEN** independently summed eligible call durations exceed normative working capacity
- **THEN** the displayed utilization may be greater than `100%`
- **AND** it is not clamped

### Requirement: The 100-record ceiling degrades only intervals whose lower bound is proven complete

Reaching the 100-record ceiling SHALL stop acquisition but SHALL NOT by itself prove that the requested 30-day, 90-day, or shortened interval is complete.

For the agreed product-limit degradation, the desired shortened calculation interval SHALL start at the exact start timestamp of the oldest accepted record and end at `reference_now`. That shortened interval MAY be shown as an authoritative numeric statistic only when interval-safe protocol/query semantics prove that no unseen older record can overlap that exact oldest-record timestamp.

For a proven degraded interval, the displayed day count SHALL be the inclusive number of calendar dates touched from the lower-bound date through `reference_now`'s date. Usage duration SHALL use the exact timestamp interval. The denominator SHALL use the normal eight-hours-per-touched-weekday rule, including a full eight hours for a first weekday touched only after the lower-bound time.

If the complete 30-day interval is proven and the exact oldest-record shortened interval is also proven but the complete 90-day interval is not, the GUI SHALL show:

- one normal 30-day usage row; and
- one degraded longer-period row labelled with its actual covered calendar-day count and calculated against that same actual interval.

If the exact oldest-record shortened interval is proven but the complete 30-day interval is not, the GUI SHALL show exactly one degraded actual-period usage row rather than two duplicate rows.

Every product-limit degraded row SHALL display a clear non-modal warning that the calculation depth was limited by the 100-record ceiling.

If the 100-record ceiling is reached and no interval-safe proof exists for the affected target or shortened interval, the application SHALL preserve the accepted journal records but mark the affected statistic incomplete/unavailable. It SHALL NOT display an authoritative-looking percentage based only on the span of retrieved `start_at` values.

#### Scenario: One hundred records safely cover forty-seven calendar dates

- **GIVEN** the 100-record ceiling is reached
- **AND** interval-safe semantics prove the full 30-day window and prove the shortened interval beginning at the exact oldest accepted record
- **AND** that shortened interval touches 47 calendar dates but the full 90-day lower bound is not proven
- **WHEN** statistics are rendered
- **THEN** the normal 30-day row remains
- **AND** the longer row is labelled as 47 days rather than 90 days
- **AND** both its numerator and denominator are recalculated for the exact proven shortened interval

#### Scenario: One hundred records safely cover only eighteen calendar dates

- **GIVEN** the 100-record ceiling is reached before the 30-day lower bound is proven
- **AND** the exact oldest-record shortened interval is itself interval-safe/proven
- **AND** it touches 18 calendar dates
- **WHEN** statistics are rendered
- **THEN** exactly one 18-day degraded row is shown
- **AND** duplicate 30-day and 90-day rows are not shown

#### Scenario: Oldest accepted record begins partway through a weekday

- **GIVEN** a proven degraded interval begins at the oldest accepted record at 15:00 on a Monday
- **WHEN** the degraded percentage is calculated
- **THEN** usage arithmetic begins at that exact 15:00 timestamp
- **AND** that Monday contributes the full eight hours to normative working capacity

#### Scenario: One hundred start-time-ordered records do not prove the shortened interval

- **GIVEN** the source is ordered only by start time
- **AND** no interval-safe duration/end-time/range invariant is known
- **WHEN** the 100-record ceiling is reached
- **THEN** the journal remains usable
- **AND** the oldest accepted `start_at` is not treated as a proven lower bound
- **AND** the affected statistic is marked incomplete/unavailable rather than shown as an authoritative degraded percentage

### Requirement: Clean empty history, source limitation, and partial operational failure have distinct semantics

A successful empty journal with clean end-of-journal SHALL be valid complete data. Under the normal 30-day and 90-day windows it SHALL produce zero usage duration and zero utilization percentage for both rows.

A `source_history_limited` outcome or typed operational failure during deeper retrieval SHALL NOT discard already accepted recent call records. Any target interval whose coverage was already proven before termination SHALL remain authoritative and visible. An interval whose coverage was not proven SHALL NOT be presented as a normal complete percentage.

A source-limited shortened interval MAY be shown numerically only when its lower bound is independently interval-safe/proven; otherwise it SHALL be incomplete/unavailable. A typed operational failure SHALL not be converted into a source-history limitation.

Warnings caused by system-time fallback, malformed duration, 100-record degradation, source-history limitation/no-progress, or deeper operational failure SHALL not convert an otherwise usable call journal into a modal failure.

#### Scenario: Journal is successfully empty

- **WHEN** the codec successfully reports an empty call journal and clean end-of-journal
- **THEN** the normal 30-day row shows `0.0` hours and `0%`
- **AND** the normal 90-day row shows `0.0` hours and `0%`
- **AND** no insufficient-history warning is emitted solely because there are no records

#### Scenario: Thirty days are complete before deeper retrieval fails

- **GIVEN** interval-safe coverage of the complete 30-day interval was already proven
- **WHEN** a later read needed for the longer interval fails
- **THEN** the 30-day statistic remains authoritative
- **AND** already accepted journal records remain visible
- **AND** the longer unproven statistic is marked incomplete/unavailable with a warning

### Requirement: Call-log dialog shows two preview rows, usage summary, and a collapsed latest-twenty journal

The dialog SHALL show up to the two newest call records as always-visible rows using the existing four visible fields. It SHALL show the applicable authoritative usage summary row or rows below the recent-call preview and explicit warnings/incomplete states where applicable.

The dialog SHALL contain an initially collapsed expandable section labelled exactly `Журнал звонков`. When expanded, it SHALL show at most the latest 20 call-log records total, including the same records already present in the two-row preview. The expandable section SHALL NOT represent 20 additional records. If fewer than 20 records exist, all available records SHALL be shown with no artificial empty rows.

The initial loading state SHALL display `Загрузка журнала звонков...`. After recent call data can be presented and while deeper history and/or statistics work remains in progress, the dialog SHALL display `Расчёт статистики использования...`.

Expanding or collapsing `Журнал звонков` within the current load SHALL use already acquired data and SHALL NOT perform another device request merely because disclosure state changed. A later explicit dialog opening SHALL begin a fresh acquisition; this change SHALL NOT introduce a cross-opening call-history cache.

Exact spacing, typography, card style, and disclosure-control widget MAY follow existing GUI conventions as long as the required hierarchy, fields, values, warnings, and states remain clear and identical across all five supported models.

#### Scenario: Codec has seven records

- **WHEN** the dialog finishes loading seven records
- **THEN** the two newest are always visible in the preview
- **AND** expanding `Журнал звонков` shows all seven records
- **AND** no empty placeholder rows are added

#### Scenario: Codec has more than twenty records

- **WHEN** the current load contains more than 20 accepted records
- **THEN** the preview shows the newest two
- **AND** expanded `Журнал звонков` shows the newest 20 total including those two

#### Scenario: Operator toggles journal disclosure

- **WHEN** the operator expands and collapses `Журнал звонков` after the current load has acquired its records
- **THEN** disclosure uses the already loaded history
- **AND** no additional codec history request is triggered solely by the toggle

### Requirement: Existing Huawei and Polycom call-log lifecycle ownership remains authoritative

For `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, and `CloudLink Box 310`, call-history acquisition SHALL remain read-only work on the existing shared Huawei interactive-session/controller path. The existing approved invalid-cached-session behavior remains bounded: reconnect once and replay the read once. Deep history SHALL NOT create handler-owned credential iteration or an unbounded reconnect/login loop.

For `Polycom RPG 310`, call-history acquisition SHALL remain owned by the existing short-lived Polycom call-log worker/session path and SHALL NOT be routed through the Huawei/shared controller merely to share history/statistics code.

The common boundary between the families SHALL be normalized history/statistics, not network-session ownership.

All handler acquisition, device-time reads, history requests, pagination, bounded recovery, and network/session cleanup SHALL run outside the Qt GUI thread. Existing currentness/stale-result rules SHALL prevent superseded call-log results from updating a replaced current context.

Credential selection and fallback SHALL remain application/composition-owned. Call-log strings, HTTP-status text, participant names, or GUI warnings SHALL NOT become credential-fallback signals. Secrets SHALL remain redacted from logs, public errors, warnings, and normalized presentation payloads.

#### Scenario: Huawei cached session is invalid

- **WHEN** a Huawei deep call-history read detects an invalid cached session
- **THEN** the existing shared interactive controller performs only its approved bounded reconnect/replay behavior
- **AND** no handler-owned credential iteration is introduced

#### Scenario: Polycom call history is loaded

- **WHEN** Polycom RPG310 call history and usage data are acquired
- **THEN** the short-lived Polycom call-log worker remains owner of that network operation
- **AND** normalized records may use the common calculation/presentation layer
- **AND** the operation is not routed through the Huawei/shared call-log controller

#### Scenario: Dialog context is superseded

- **WHEN** a call-history result from an old context completes after a newer authoritative codec/dialog context exists
- **THEN** the stale result does not update the current dialog
- **AND** no stale callback mutates credential/profile memory

### Requirement: Real-device validation proves protocol facts while offline tests prove bounded edge cases

Implementation and independent validation SHALL use read-only live device access, when the relevant physical device is available, to confirm only protocol facts that can actually be observed without mutating device state, including request success, record shape/order, page/batch continuation or clean end behavior, repeated-page/no-progress behavior where observable, timestamp encoding, codec-local time acquisition, and any claimed interval-safe coverage invariant.

Live validation SHALL NOT require a device to contain 100 calls, a call older than 90 days, an active call, a malformed record, or another accidental edge case. It SHALL NOT manufacture those cases by placing calls, deleting history, changing time/configuration, or altering credentials.

Deterministic automated regression coverage SHALL use synthetic histories and fake handlers/sessions to prove the 100-record ceiling, 30/90-day boundaries, interval-safe coverage rules, degraded periods, source-history limitation/no-progress, active/malformed/overlapping records, page failure, empty history, time fallback, lifecycle ownership, stale suppression, and GUI behavior. The canonical offline suite SHALL remain network-independent.

Production IP addresses, credentials, tokens, cookies, raw device captures, or sensitive response bodies SHALL NOT be committed as fixtures or validation artifacts.

#### Scenario: Real device has only a small recent journal

- **GIVEN** a physical codec exposes only a few recent calls
- **WHEN** read-only live validation is performed
- **THEN** observable protocol facts may still be confirmed from that device
- **AND** missing 100-record or 90-day cases do not block validation when deterministic synthetic coverage proves those algorithmic contracts

#### Scenario: Hundred-record edge case is tested

- **WHEN** regression coverage proves the hard 100-record boundary and proof-aware degraded behavior
- **THEN** it uses deterministic synthetic history/fake protocol responses
- **AND** no physical codec is required to contain or generate 100 calls
