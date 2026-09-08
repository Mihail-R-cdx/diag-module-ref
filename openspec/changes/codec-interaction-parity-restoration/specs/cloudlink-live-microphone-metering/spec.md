## MODIFIED Requirements

### Requirement: CloudLink live microphone metering has a closed model and protocol contract

Live microphone metering SHALL support exactly one diagnostic model in this change:

```text
CloudLink Bar 310
```

`CloudLink Box 310` microphone LIVE is explicitly `UNSUPPORTED / DEFERRED` in this change. The exact Box registration SHALL advertise no post-cycle LIVE binding, application/composition SHALL create no Box meter context, and current production work SHALL perform zero Box live-sample network I/O.

The capability SHALL reuse the application-selected credential and the shared CloudLink 310 handler/session boundary. It SHALL NOT create a credential source, select or iterate credential candidates in the handler/worker, alias Bar and Box identities, or persist successful credential/profile memory from meter-only telemetry.

For `CloudLink Bar 310`, the live sample source SHALL remain exactly:

```text
GET /v1/mediacontrol/mic/current-volume
```

Before the Bar request, the current CloudLink handler generation SHALL have established the modern read context through:

```text
POST /v1/login/session
POST /v1/login/account
```

using only the credential already assigned by the application/composition layer. The successful modern login SHALL yield a usable `data.acCSRFToken` retained only as in-memory session material. The Bar meter request SHALL transmit that token as `X-Access-Token` in the established modern HTTP session. The token is not a new credential, SHALL NOT be persisted, and SHALL NOT authorize handler-owned credential fallback.

After response decoding, Bar `data["curMicVouumeList"]` SHALL be a list. Every Mapping entry in the complete list SHALL be eligible regardless of `deviceId`. Every non-negative numeric `curVolume` SHALL contribute an observation, and the raw microphone level SHALL be the maximum valid `curVolume` across all entries. The implementation SHALL NOT exclude `deviceId == 18`, assume a fixed identifier range, select one preferred device, or use list position as channel authority.

The historical Box transport boundary:

```text
POST action.cgi?ActionID=WEB_GetCurrentAudioParam
```

MAY remain documented in the shared handler/legacy compatibility code as dormant protocol knowledge, but it SHALL NOT be invoked by a Box LIVE lifecycle in this change. The former fixed Box `mic1ValueIndex` / `micArray*_ValIdx` parser contract is not authoritative for current Box hardware and SHALL NOT be used to re-enable Box metering. Earlier `{deviceId, curVolume}` Box observations are discovery evidence only and likewise SHALL NOT authorize `max(all curVolume)` or any other production parser until a later reviewed Box-specific change establishes the full response envelope, microphone record selection, numeric validity, aggregation, normalization, and unavailable/error semantics.

An empty Bar list or a Bar list with no valid `curVolume` SHALL be an unavailable sample and SHALL NOT be represented as numeric zero. A successfully observed Bar raw numeric `0` SHALL remain an available sample at 0%.

An established Bar-session HTTP 401/403 SHALL remain a typed session invalidation under the existing bounded same-credential recovery policy. A generic HTTP-200 application response with `success: 0`, arbitrary exception/message text, or another unapproved discriminator SHALL NOT by itself authorize credential fallback, token discovery, model switching, or string-heuristic session invalidation.

#### Scenario: Bar established session needs no meter-specific token

- **GIVEN** the application has assigned exact `CloudLink Bar 310` and one credential
- **AND** the shared handler established its modern read context successfully
- **WHEN** live metering requests `GET /v1/mediacontrol/mic/current-volume`
- **THEN** the request reuses that modern session and cookies
- **AND** it transmits the shared in-memory modern token as `X-Access-Token`
- **AND** it does not create, acquire, persist, refresh, discover, or select a separate meter-specific credential or token
- **AND** it does not introduce handler-owned credential iteration

#### Scenario: Bar sample includes device ID 18

- **GIVEN** a successful Bar sample contains valid `curVolume` observations including `deviceId == 18`
- **WHEN** the raw level is normalized
- **THEN** every valid list entry participates in the maximum
- **AND** `deviceId == 18` is not excluded

#### Scenario: Bar device identifiers are sparse or reordered

- **WHEN** a successful Bar 310 list contains valid entries with arbitrary, sparse, or reordered `deviceId` values
- **THEN** every Mapping entry with a valid non-negative numeric `curVolume` participates in the maximum
- **AND** the maximum valid `curVolume` wins
- **AND** `deviceId == 18` remains eligible
- **AND** device identifier value, order, and list position do not select or exclude a line

#### Scenario: Bar observed silence is available

- **WHEN** a successful Bar payload has valid observations whose maximum is numeric zero
- **THEN** the sample is available
- **AND** raw level is zero
- **AND** the display fraction is 0%

#### Scenario: Box meter keeps its approved source and legacy context

- **GIVEN** the exact current model is `CloudLink Box 310`
- **WHEN** application composition resolves post-cycle microphone LIVE capability in this change
- **THEN** no Box LIVE capability/binding is advertised
- **AND** no meter context is created
- **AND** `WEB_GetCurrentAudioParam` is not invoked as a live-sample request
- **AND** the historical endpoint remains only dormant legacy-compatibility knowledge for a future reviewed Box restoration change

#### Scenario: Box payload contains microphone and non-microphone inputs

- **GIVEN** historical Box evidence contains audio records or fields whose authoritative microphone roles are not fully established
- **WHEN** the current change evaluates Box microphone LIVE
- **THEN** no production Box live parser or aggregation is admitted
- **AND** no fixed-field Bar/legacy schema is treated as current Box authority
- **AND** no `max(all curVolume)` rule is inferred
- **AND** Box remains live-meter unsupported until a later approved change proves the complete parser contract

#### Scenario: Bar meter endpoint rejects the established session

- **WHEN** the established Bar meter request receives HTTP 401 or 403
- **THEN** the failure remains typed session invalidation
- **AND** same-credential bounded recovery remains authoritative
- **AND** the handler does not advance credentials or switch Bar/Box identity
- **AND** response-string authentication heuristics do not change that handling

#### Scenario: Application-level unsuccessful sample has no approved auth discriminator

- **WHEN** an established Bar meter request returns HTTP 200 with generic `success: 0`
- **AND** no separately approved structured authentication discriminator is present
- **THEN** the cycle is treated as an endpoint command/protocol outcome according to the common failure boundary
- **AND** arbitrary response strings do not authorize credential fallback or model switching

#### Scenario: No valid microphone observation exists

- **WHEN** a successful Bar response contains no valid microphone-level observation
- **THEN** the sample is unavailable
- **AND** numeric zero is not manufactured

### Requirement: CloudLink microphone level normalization distinguishes zero, unavailable, and display clipping

For the supported `CloudLink Bar 310` meter, a valid canonical raw microphone level SHALL be a non-negative numeric observation. The display scale for this change SHALL use a fixed ceiling of `20` and SHALL normalize as equivalent to:

```text
fraction = clamp(raw_level / 20, 0.0, 1.0)
```

An observed raw value of `0` SHALL be available data and SHALL render at 0%. An unavailable sample SHALL contain no authoritative numeric raw level and SHALL render as unavailable/inactive rather than as observed silence. A raw value greater than `20` SHALL remain a valid raw observation while only its presentation fraction is clipped to 100%.

This normalization contract SHALL NOT be applied to Box 310 in this change because Box microphone LIVE is unsupported/deferred and no Box sample is admitted.

The GUI SHALL NOT display a fabricated dB, dBFS, percentage text, or physical-unit label because this change does not establish such a calibration.

#### Scenario: Observed silence is zero

- **WHEN** a successful supported Bar sample produces raw level `0`
- **THEN** the sample remains available
- **AND** its meter fraction is 0%
- **AND** it is distinguishable from unavailable telemetry

#### Scenario: Level reaches the temporary ceiling

- **WHEN** supported Bar raw level is `20`
- **THEN** the display fraction is 100%

#### Scenario: Level exceeds the temporary ceiling

- **WHEN** supported Bar raw level is greater than `20`
- **THEN** the raw observation remains valid
- **AND** the display fraction is clipped to 100%

### Requirement: CloudLink microphone metering uses one-second serialized background polling

The application/composition layer SHALL own the live microphone-meter context only for a current exact `CloudLink Bar 310` context. Network I/O SHALL execute outside the Qt GUI thread.

One active Bar meter context SHALL be bound to immutable authority including exact model, exact IP address, meter generation or operation identity, and relevant credential-context identity. It SHALL use at most one sample operation in flight at a time and SHALL target a cadence of one completed sample cycle per second. A new cycle SHALL NOT overlap an unfinished prior sample request merely to maintain wall-clock cadence.

The current Bar meter SHALL be invalidated when the model changes, IP changes, current codec diagnostic/page context is superseded or deactivated, relevant credential context changes, repeat diagnostic refresh replaces the context, or application shutdown begins.

Queued stale work SHALL be dropped before handler acquisition and before first network I/O where separable. Currentness SHALL be checked before every new sample request and before publication. Stale result, error, completion, credential metadata, or profile metadata SHALL NOT update the current UI or credential/profile memory. Background freshness SHALL NOT depend on reading Qt widgets.

For exact `CloudLink Box 310`, this change SHALL create no meter polling context, schedule no one-second live cycle, acquire no handler/session for meter work, and send no `WEB_GetCurrentAudioParam` request as post-cycle LIVE.

#### Scenario: Meter cycle takes less than one second

- **WHEN** a current Bar sample completes before the next one-second cadence point
- **THEN** the next sample is scheduled no faster than the approved cadence
- **AND** no second sample overlaps the first

#### Scenario: Meter cycle takes longer than one second

- **WHEN** one Bar sample operation is still running after the nominal next cadence point
- **THEN** another sample is not started concurrently
- **AND** the next cycle begins only after the previous operation reaches an allowed completion boundary and currentness is rechecked

#### Scenario: Codec IP changes before queued work starts

- **WHEN** an old Bar meter operation is queued and the authoritative codec IP changes before handler acquisition
- **THEN** the old operation is dropped
- **AND** it acquires no handler and performs zero meter network I/O

#### Scenario: Stale sample returns after replacement

- **WHEN** an old Bar-context sample returns after a newer model/IP/generation is authoritative
- **THEN** the stale sample does not update the meter
- **AND** it does not modify credential index or connection-profile memory

#### Scenario: Box 310 has no polling context

- **GIVEN** exact current model is `CloudLink Box 310`
- **WHEN** post-cycle room interaction becomes active
- **THEN** no CloudLink microphone-meter polling context is created for Box
- **AND** no one-second Box meter timer/cycle is scheduled
- **AND** no `WEB_GetCurrentAudioParam` request is sent by LIVE

### Requirement: Live meter failure is isolated from ordinary codec status

Supported Bar 310 live microphone sampling SHALL remain separate from ordinary CloudLink `get_status()` collection and SHALL NOT make ordinary codec status refresh long-lived.

An endpoint-local unsuccessful Bar sample, malformed sample payload, or sample-specific command/protocol outcome on an otherwise usable established session SHALL mark only that Bar meter cycle unavailable. It SHALL preserve already accepted ordinary codec data and SHALL allow the next scheduled Bar sample cycle to attempt the read again.

Structured authentication rejection, established-session invalidation, and transport/session failures SHALL preserve their typed categories and existing bounded read-only recovery rules. The Bar meter SHALL NOT create an unbounded one-second reconnect/login loop. If approved bounded recovery cannot restore the Bar meter session, the meter SHALL remain unavailable until a new authoritative Bar diagnostic context starts.

Because Box 310 has no live meter lifecycle in this change, ordinary Box diagnostic failure/success SHALL NOT be reclassified through this meter-failure contract and no optional Box meter failure state is produced.

Meter failure or success SHALL NOT advance credential candidates from string heuristics, SHALL NOT persist successful credential/profile memory, SHALL NOT erase accepted codec data, and SHALL NOT open an automatic modal error solely because optional live telemetry is unavailable. Secrets SHALL remain redacted from meter logs, errors, signals, and presentation payloads.

#### Scenario: One sample payload is malformed

- **GIVEN** ordinary Bar codec status is already accepted
- **WHEN** a Bar live sample response is malformed while the established session remains usable
- **THEN** the meter becomes unavailable for that cycle
- **AND** accepted codec status remains visible and successful
- **AND** the next scheduled Bar cycle may attempt another sample

#### Scenario: Meter transport cannot recover

- **WHEN** a structured Bar meter transport/session failure exhausts the existing bounded read-only recovery budget
- **THEN** the live meter remains unavailable until a new authoritative Bar context starts
- **AND** ordinary accepted codec status is not converted into failure
- **AND** no unbounded reconnect loop starts

### Requirement: Codec page renders CloudLink microphone level as a live meter

For exact current `CloudLink Bar 310` context, the codec page `Параметры и управление` card SHALL contain exactly one row labelled `Уровень микрофонов` in this order:

```text
Статус микрофона
Уровень микрофонов
Журнал звонков
```

The row SHALL render a horizontal live meter with no numeric text overlay and with the same user-visible meter semantics as the existing DMP meter presentation: an available sample controls fill amount and unavailable telemetry has a distinct inactive/unavailable appearance.

The legacy codec-page live microphone row SHALL be hidden for every unsupported codec model, including exact `CloudLink Box 310`. In the modern room codec dashboard, Box's permanent `Микрофон (уровень)` slot SHALL instead render the explicit unsupported state required by `diagnostic-ui-presentation`; neither surface SHALL imply a Box LIVE lifecycle.

Codec parameter-widget reconstruction SHALL NOT duplicate the row, retain a deleted/pending-deletion meter widget as current, or permit old-context callbacks to update a newly reconstructed current row.

The screen SHALL remain a rendering boundary and SHALL NOT choose credentials, iterate credential candidates, infer another model, or perform blocking device I/O on the Qt GUI thread.

#### Scenario: Bar 310 page is active

- **WHEN** the current exact diagnostic model is `CloudLink Bar 310`
- **THEN** one `Уровень микрофонов` meter row appears after `Статус микрофона` and before `Журнал звонков`
- **AND** accepted samples update the horizontal meter

#### Scenario: Unsupported codec page is active

- **WHEN** the current codec model is not `CloudLink Bar 310`, including exact `CloudLink Box 310`
- **THEN** the legacy live microphone-meter row is hidden
- **AND** existing non-meter codec rows retain their prior behavior
- **AND** Box does not start or imply a live microphone lifecycle

#### Scenario: Codec layout rebuild occurs during metering

- **WHEN** codec-owned controls are reconstructed for a new current context
- **THEN** exactly one legacy live meter row exists only when the new exact model is `CloudLink Bar 310`
- **AND** no live meter row is constructed for Box 310
- **AND** callbacks bound to the prior meter context cannot update the new row
