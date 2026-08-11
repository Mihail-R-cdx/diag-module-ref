# cloudlink-live-microphone-metering Specification

## Purpose
TBD - created by archiving change cloudlink-live-microphone-metering. Update Purpose after archive.
## Requirements
### Requirement: CloudLink live microphone metering has a closed model and protocol contract

Live microphone metering SHALL support exactly these diagnostic models:

```text
CloudLink Bar 310
CloudLink Box 310
```

The capability SHALL reuse the existing authenticated CloudLink handler/session boundary and SHALL NOT create a new credential source, login authority, or handler-owned credential iteration.

For `CloudLink Bar 310`, the live sample source SHALL be exactly:

```text
GET /v1/mediacontrol/mic/current-volume
```

The Bar request SHALL run only after the existing CloudLink handler connection has established the normal HTTP-Basic-backed `requests.Session` and current CloudLink session context. The approved protocol contract for this change is that this established session can obtain HTTP `200` with a valid `curMicVouumeList` without `X-Access-Token`. The implementation SHALL NOT add, acquire, persist, refresh, infer, or transmit an `X-Access-Token` or another meter-specific access token. Existing `acCSRFToken` behavior remains action.cgi session material and does not become a new meter credential.

A structured authentication or established-session rejection from the Bar meter endpoint SHALL remain a typed failure under the existing bounded recovery policy. Such rejection SHALL NOT authorize token discovery, an alternate login flow, handler-owned credential fallback, or another authentication mechanism. Any future requirement for such a mechanism requires a separately reviewed OpenSpec change.

After the existing response decoding boundary, `data["curMicVouumeList"]` SHALL be a list. Every Mapping entry in the complete list SHALL be eligible regardless of `deviceId`. Every non-negative numeric `curVolume` SHALL contribute an observation, and the raw microphone level SHALL be the maximum valid `curVolume` across all entries. The implementation SHALL NOT exclude `deviceId == 18`, assume a fixed device-ID range, select one preferred device, or use list position as channel authority.

For `CloudLink Box 310`, the live sample source SHALL be exactly:

```text
POST action.cgi?ActionID=WEB_GetCurrentAudioParam
```

using the existing established CloudLink session request context. Only this closed field set SHALL contribute:

```text
mic1ValueIndex
mic2ValueIndex
mic3ValueIndex
mic4ValueIndex
micArray1_01ValIdx
micArray1_02ValIdx
micArray1_03ValIdx
micArray2_01ValIdx
micArray2_02ValIdx
micArray2_03ValIdx
micArray3_01ValIdx
micArray3_02ValIdx
micArray3_03ValIdx
```

Each present non-negative numeric value SHALL contribute an observation and the raw microphone level SHALL be the maximum valid value. The implementation SHALL NOT scan arbitrary field names or include TRS, RCA, HDMI, Bluetooth, UAC, `m220w_porwer_hint`, or another unreviewed non-microphone audio field.

An empty Bar list, a Bar list with no valid `curVolume`, or a Box payload with no valid value from the closed microphone set SHALL be an unavailable sample and SHALL NOT be represented as numeric zero.

#### Scenario: Bar established session needs no meter-specific token

- **GIVEN** the normal Bar 310 handler connection has established its current authenticated session
- **WHEN** live metering requests `GET /v1/mediacontrol/mic/current-volume`
- **THEN** the request reuses the established session
- **AND** no `X-Access-Token` or other meter-specific access token is acquired or transmitted
- **AND** successful HTTP `200` response decoding proceeds through the existing response boundary

#### Scenario: Bar meter endpoint rejects the established session

- **WHEN** the Bar meter endpoint returns a structured authentication or established-session rejection
- **THEN** the existing typed failure and bounded recovery policy remains authoritative
- **AND** the implementation does not begin token discovery, an alternate login flow, or handler-owned credential fallback

#### Scenario: Bar sample includes device ID 18

- **GIVEN** a successful Bar 310 sample contains valid `curVolume` values for several entries including `deviceId == 18`
- **WHEN** the raw level is normalized
- **THEN** the maximum is calculated across every valid list entry
- **AND** `deviceId == 18` is not excluded

#### Scenario: Bar device identifiers are sparse or reordered

- **WHEN** a successful Bar 310 list contains valid entries with arbitrary or reordered `deviceId` values
- **THEN** every valid `curVolume` participates in the maximum
- **AND** device identifier order does not select or exclude a line

#### Scenario: Box payload contains microphone and non-microphone inputs

- **GIVEN** a Box 310 response contains microphone fields plus TRS, RCA, HDMI, Bluetooth, or UAC values
- **WHEN** the raw meter level is calculated
- **THEN** only the exact approved microphone fields participate
- **AND** a larger non-microphone input value cannot raise the microphone meter

#### Scenario: No valid microphone observation exists

- **WHEN** the model-specific successful response contains no valid microphone-level observation
- **THEN** the sample is unavailable
- **AND** raw level zero is not manufactured

### Requirement: CloudLink microphone level normalization distinguishes zero, unavailable, and display clipping

A valid canonical raw microphone level SHALL be a non-negative numeric observation. The display scale for this change SHALL use a fixed ceiling of `20` and SHALL normalize as equivalent to:

```text
fraction = clamp(raw_level / 20, 0.0, 1.0)
```

An observed raw value of `0` SHALL be available data and SHALL render at 0%. An unavailable sample SHALL contain no authoritative numeric raw level and SHALL render as unavailable/inactive rather than as observed silence. A raw value greater than `20` SHALL remain a valid raw observation while only its presentation fraction is clipped to 100%.

The GUI SHALL NOT display a fabricated dB, dBFS, percentage text, or physical-unit label because this change does not establish such a calibration.

#### Scenario: Observed silence is zero

- **WHEN** a successful model-specific sample produces raw level `0`
- **THEN** the sample remains available
- **AND** its meter fraction is 0%
- **AND** it is distinguishable from unavailable telemetry

#### Scenario: Level reaches the temporary ceiling

- **WHEN** raw level is `20`
- **THEN** the display fraction is 100%

#### Scenario: Level exceeds the temporary ceiling

- **WHEN** raw level is greater than `20`
- **THEN** the raw observation remains valid
- **AND** the display fraction is clipped to 100%

### Requirement: CloudLink microphone metering uses one-second serialized background polling

The application/composition layer SHALL own the live microphone-meter context for a current codec-page CloudLink diagnostic context. Network I/O SHALL execute outside the Qt GUI thread.

One active meter context SHALL be bound to immutable authority including exact model, exact IP address, meter generation or operation identity, and relevant credential-context identity. It SHALL use at most one sample operation in flight at a time and SHALL target a cadence of one completed sample cycle per second. A new cycle SHALL NOT overlap an unfinished prior sample request merely to maintain wall-clock cadence.

The current meter SHALL be invalidated when the model changes, IP changes, current codec diagnostic/page context is superseded or deactivated, relevant credential context changes, repeat diagnostic refresh replaces the context, or application shutdown begins.

Queued stale work SHALL be dropped before handler acquisition and before first network I/O where separable. Currentness SHALL be checked before every new sample request and before publication. Stale result, error, completion, credential metadata, or profile metadata SHALL NOT update the current UI or credential/profile memory. Background freshness SHALL NOT depend on reading Qt widgets.

#### Scenario: Meter cycle takes less than one second

- **WHEN** a current sample completes before the next one-second cadence point
- **THEN** the next sample is scheduled no faster than the approved cadence
- **AND** no second sample overlaps the first

#### Scenario: Meter cycle takes longer than one second

- **WHEN** one sample operation is still running after the nominal next cadence point
- **THEN** another sample is not started concurrently
- **AND** the next cycle begins only after the previous operation reaches an allowed completion boundary and currentness is rechecked

#### Scenario: Codec IP changes before queued work starts

- **WHEN** an old meter operation is queued and the authoritative codec IP changes before handler acquisition
- **THEN** the old operation is dropped
- **AND** it acquires no handler and performs zero meter network I/O

#### Scenario: Stale sample returns after replacement

- **WHEN** an old-context sample returns after a newer model/IP/generation is authoritative
- **THEN** the stale sample does not update the meter
- **AND** it does not modify credential index or connection-profile memory

### Requirement: Live meter failure is isolated from ordinary codec status

Live microphone sampling SHALL remain separate from ordinary CloudLink `get_status()` collection and SHALL NOT make ordinary codec status refresh long-lived.

An endpoint-local unsuccessful sample, malformed sample payload, or sample-specific command/protocol outcome on an otherwise usable established session SHALL mark only that meter cycle unavailable. It SHALL preserve already accepted ordinary codec data and SHALL allow the next scheduled sample cycle to attempt the read again.

Structured authentication rejection, established-session invalidation, and transport/session failures SHALL preserve their typed categories and existing bounded read-only recovery rules. The meter SHALL NOT create an unbounded one-second reconnect/login loop. If approved bounded recovery cannot restore the meter session, the meter SHALL remain unavailable until a new authoritative diagnostic context starts.

Meter failure or success SHALL NOT advance credential candidates from string heuristics, SHALL NOT persist successful credential/profile memory, SHALL NOT erase accepted codec data, and SHALL NOT open an automatic modal error solely because optional live telemetry is unavailable. Secrets SHALL remain redacted from meter logs, errors, signals, and presentation payloads.

#### Scenario: One sample payload is malformed

- **GIVEN** ordinary codec status is already accepted
- **WHEN** a live sample response is malformed while the established session remains usable
- **THEN** the meter becomes unavailable for that cycle
- **AND** accepted codec status remains visible and successful
- **AND** the next scheduled cycle may attempt another sample

#### Scenario: Meter transport cannot recover

- **WHEN** a structured meter transport/session failure exhausts the existing bounded read-only recovery budget
- **THEN** the live meter remains unavailable until a new authoritative codec context starts
- **AND** ordinary accepted codec status is not converted into failure
- **AND** no unbounded reconnect loop starts

### Requirement: Codec page renders CloudLink microphone level as a live meter

For exact current `CloudLink Bar 310` or `CloudLink Box 310` context, the codec page `Параметры и управление` card SHALL contain exactly one row labelled `Уровень микрофонов` in this order:

```text
Статус микрофона
Уровень микрофонов
Журнал звонков
```

The row SHALL render a horizontal live meter with no numeric text overlay and with the same user-visible meter semantics as the existing DMP meter presentation: an available sample controls fill amount and unavailable telemetry has a distinct inactive/unavailable appearance.

The row SHALL be hidden for unsupported codec models. Codec parameter-widget reconstruction SHALL NOT duplicate the row, retain a deleted/pending-deletion meter widget as current, or permit old-context callbacks to update a newly reconstructed current row.

The screen SHALL remain a rendering boundary and SHALL NOT choose credentials, iterate credential candidates, infer another model, or perform blocking device I/O on the Qt GUI thread.

#### Scenario: Bar 310 page is active

- **WHEN** the current exact diagnostic model is `CloudLink Bar 310`
- **THEN** one `Уровень микрофонов` meter row appears after `Статус микрофона` and before `Журнал звонков`
- **AND** accepted samples update the horizontal meter

#### Scenario: Unsupported codec page is active

- **WHEN** the current codec model is not `CloudLink Bar 310` or `CloudLink Box 310`
- **THEN** the live microphone-meter row is hidden
- **AND** existing codec rows retain their prior behavior

#### Scenario: Codec layout rebuild occurs during metering

- **WHEN** codec-owned controls are reconstructed for a new current context
- **THEN** exactly one live meter row exists when the new model supports it
- **AND** callbacks bound to the prior meter context cannot update the new row
