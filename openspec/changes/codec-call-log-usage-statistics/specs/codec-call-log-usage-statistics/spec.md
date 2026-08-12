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

All supported models SHALL expose the same user-visible call-log dialog structure and the same usage-calculation semantics. Vendor-specific request, pagination, timestamp, and parser differences SHALL remain behind model-specific read-only retrieval/normalization boundaries.

Each normalized record used for calculation SHALL retain a machine-readable start time, active/completed state, and non-negative duration in seconds when available. Calculation code SHALL NOT parse the GUI-formatted date or duration strings back into arithmetic values.

The visible call record SHALL preserve the existing fields:

```text
Номер комнаты
Дата и время начала
Продолжительность
Скорость
```

Separate legitimate source records SHALL remain separate even when their time intervals overlap. The implementation SHALL NOT merge overlapping calls or filter records because they are incoming, outgoing, successful, unanswered, or failed. Only a duplicate proven to be the same source record repeated by the transport/pagination boundary MAY be suppressed.

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

### Requirement: Call-history acquisition is newest-first and limited to 100 accepted records

Every explicit call-log dialog opening SHALL begin a fresh read-only acquisition. The implementation SHALL obtain records newest-first and SHALL stop requesting older history at the first applicable condition:

1. history already proves coverage beyond the start of the 90-day target interval;
2. the codec reports end-of-journal/no more records;
3. exactly 100 accepted call-log records have been obtained;
4. a typed operational failure prevents continuation.

The product ceiling SHALL be exactly 100 accepted visible call-log records per load. Active records and visible records with unavailable duration SHALL count toward that ceiling. A transport duplicate proven to be the same source record repeated across pages SHALL not count twice. The implementation SHALL NOT accept a 101st journal record merely to improve statistics.

When clean end-of-journal occurs before a 30-day or 90-day boundary, the application SHALL treat the older remainder of the requested interval as containing no calls. It SHALL NOT infer or warn about an undocumented retention policy solely from an early clean source end.

#### Scenario: Ninety-day coverage is reached before the record ceiling

- **WHEN** retrieved history proves coverage beyond the start of the 90-day interval before 100 accepted records are needed
- **THEN** no further history request is issued
- **AND** both normal target periods may be calculated from the accepted history

#### Scenario: The hundredth record is accepted first

- **WHEN** the 100th accepted record is reached before the longest target interval is covered
- **THEN** history acquisition stops
- **AND** no 101st record is accepted merely to extend the calculation period
- **AND** the affected statistic follows the 100-record degradation contract

#### Scenario: Codec returns no more records early

- **WHEN** the codec reports clean end-of-journal after a small number of records
- **THEN** history acquisition stops
- **AND** older portions of the requested 30/90-day intervals are treated as zero usage
- **AND** the statistic is not degraded solely because the journal ended early

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

If the current calendar date is Monday through Friday, it SHALL contribute the full eight denominator hours even though `reference_now` is before the end of the day. When a degraded interval starts partway through a Monday-through-Friday date, that touched first date SHALL also contribute the full eight hours.

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

### Requirement: The 100-record ceiling degrades period labels and percentages to actual covered history

When the 100-record ceiling is reached before a requested target period is covered, the affected degraded calculation interval SHALL start at the exact start timestamp of the oldest accepted record and end at `reference_now`.

The displayed degraded day count SHALL be the inclusive number of calendar dates touched from the oldest accepted record's date through `reference_now`'s date. Usage duration SHALL use the exact timestamp interval. The denominator SHALL use the normal eight-hours-per-touched-weekday rule, including a full eight hours for a first weekday that is touched only after the oldest record's time.

If 100 accepted records cover the complete 30-day interval but not the complete 90-day interval, the GUI SHALL show:

- one normal 30-day usage row; and
- one degraded longer-period row labelled with its actual covered calendar-day count and calculated against that same actual interval.

If 100 accepted records do not cover the complete 30-day interval, the GUI SHALL show exactly one degraded actual-period usage row rather than two duplicate rows for the same available interval.

Every 100-record degradation SHALL display a clear non-modal warning that the calculation depth was limited by the 100-record ceiling.

#### Scenario: One hundred records cover forty-seven calendar dates

- **GIVEN** the 100-record ceiling is reached and accepted history covers the full 30-day interval but only 47 calendar dates toward the longer interval
- **WHEN** statistics are rendered
- **THEN** the normal 30-day row remains
- **AND** the longer row is labelled as 47 days rather than 90 days
- **AND** both its numerator and denominator are recalculated for the actual degraded interval

#### Scenario: One hundred records cover only eighteen calendar dates

- **GIVEN** the 100-record ceiling is reached before the 30-day interval is covered
- **WHEN** statistics are rendered
- **THEN** exactly one 18-day degraded row is shown
- **AND** duplicate 30-day and 90-day rows derived from the same 18-day interval are not shown

#### Scenario: Oldest accepted record begins partway through a weekday

- **GIVEN** a degraded interval begins at the oldest accepted record at 15:00 on a Monday
- **WHEN** the degraded percentage is calculated
- **THEN** usage arithmetic begins at that exact 15:00 timestamp
- **AND** that Monday contributes the full eight hours to normative working capacity

### Requirement: Clean empty history and partial operational failure have distinct semantics

A successful empty journal SHALL be valid complete data. Under the normal 30-day and 90-day windows it SHALL produce zero usage duration and zero utilization percentage for both rows.

A typed operational failure during deeper retrieval SHALL NOT discard already accepted recent call records. Any target interval whose coverage was already proven before the failure SHALL remain authoritative and visible. A longer target whose coverage was not proven SHALL NOT be presented as a normal complete percentage; it SHALL be marked incomplete/unavailable with a non-secret warning.

Warnings caused by system-time fallback, malformed duration, 100-record degradation, or deeper retrieval failure SHALL not convert an otherwise usable call journal into a modal failure.

#### Scenario: Journal is successfully empty

- **WHEN** the codec successfully reports an empty call journal and end-of-journal
- **THEN** the normal 30-day row shows `0.0` hours and `0%`
- **AND** the normal 90-day row shows `0.0` hours and `0%`
- **AND** no insufficient-history warning is emitted solely because there are no records

#### Scenario: Thirty days are complete before deeper retrieval fails

- **GIVEN** enough history has already been accepted to prove the complete 30-day interval
- **WHEN** a later read needed for the longer interval fails
- **THEN** the 30-day statistic remains authoritative
- **AND** already accepted journal records remain visible
- **AND** the longer unproven statistic is marked incomplete/unavailable with a warning

### Requirement: Call-log dialog shows two preview rows, usage summary, and a collapsed latest-twenty journal

The dialog SHALL show up to the two newest call records as always-visible rows using the existing four visible fields. It SHALL show the applicable usage summary row or rows below the recent-call preview.

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

Implementation and independent validation SHALL use read-only live device access, when the relevant physical device is available, to confirm only protocol facts that can actually be observed without mutating device state, including request success, record shape/order, page/batch continuation or clean end behavior, timestamp encoding, and codec-local time acquisition.

Live validation SHALL NOT require a device to contain 100 calls, a call older than 90 days, an active call, a malformed record, or another accidental edge case. It SHALL NOT manufacture those cases by placing calls, deleting history, changing time/configuration, or altering credentials.

Deterministic automated regression coverage SHALL use synthetic histories and fake handlers/sessions to prove the 100-record ceiling, 30/90-day boundaries, degraded periods, active/malformed/overlapping records, page failure, empty history, time fallback, lifecycle ownership, stale suppression, and GUI behavior. The canonical offline suite SHALL remain network-independent.

Production IP addresses, credentials, tokens, cookies, raw device captures, or sensitive response bodies SHALL NOT be committed as fixtures or validation artifacts.

#### Scenario: Real device has only a small recent journal

- **GIVEN** a physical codec exposes only a few recent calls
- **WHEN** read-only live validation is performed
- **THEN** observable protocol facts may still be confirmed from that device
- **AND** missing 100-record or 90-day cases do not block validation when deterministic synthetic coverage proves those algorithmic contracts

#### Scenario: Hundred-record edge case is tested

- **WHEN** regression coverage proves the hard 100-record boundary and degraded period behavior
- **THEN** it uses deterministic synthetic history/fake protocol responses
- **AND** no physical codec is required to contain or generate 100 calls
