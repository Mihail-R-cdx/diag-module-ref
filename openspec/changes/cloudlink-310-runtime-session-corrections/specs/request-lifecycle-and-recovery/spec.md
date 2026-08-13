# request-lifecycle-and-recovery Specification

## MODIFIED Requirements

### Requirement: CloudLink Bar 310 polling uses a closed resilient status plan

For the closed exact `CloudLink Bar 310` / `CloudLink Box 310` protocol family, an ordinary status refresh SHALL execute an explicit reviewed read-only plan through the corrected modern CloudLink read context rather than iterate every handler command or depend on the legacy control-session handshake.

The required core observation SHALL remain the version read represented by `get_version`. Reviewed optional ordinary-refresh enrichment SHALL be limited to the existing safe MAC, audio, line/SIP, presentation data and the modern general state needed for call/sleep, plus other fields explicitly listed by this change. Configuration endpoints, every state-changing request, unreviewed command-map entries, camera-state guesses, and microphone connection/gain guesses SHALL NOT run as authoritative ordinary-polling semantics merely because a handler method exists.

The shared handler MAY use modern-read-compatible action.cgi endpoints for required version, MAC, mailbox, audio, line/SIP, and presentation observations where their existing field semantics remain approved. Read-only action.cgi requests on the modern context SHALL use the proven modern session/header plus body-token shape. `GET /v1/login/status` SHALL own modern call/sleep observation. `GET /v1/mediacontrol/mic/devices` SHALL NOT supply user-visible microphone connection/gain in this change.

After required core success, an endpoint-specific optional `CommandError`, unsuccessful optional response, or optional payload `ProtocolError` SHALL omit only fields owned by that observation and SHALL NOT erase already collected canonical status. `AuthenticationError`, `SessionInvalidError`, and `ConnectionError` remain terminal typed failures according to the common phase-aware policy.

The exact already assigned Bar/Box application identity remains authoritative. Shared polling SHALL NOT detect, relabel, retry, or fall back to the other family member.

#### Scenario: Bar ordinary refresh uses the modern read context

- **GIVEN** exact model is `CloudLink Bar 310`
- **WHEN** ordinary status refresh runs
- **THEN** reviewed read-only operations use the modern read context
- **AND** state-changing/configuration operations are not added by command-map enumeration

#### Scenario: Box ordinary refresh uses the shared corrected plan

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** ordinary status refresh runs
- **THEN** it uses the same corrected reviewed read plan where the shared protocol operation applies
- **AND** exact Box identity is preserved
- **AND** no Bar fallback or auto-detection occurs

#### Scenario: Optional read is unavailable

- **GIVEN** required version evidence succeeded
- **WHEN** one optional endpoint returns an endpoint-local unsuccessful/malformed outcome
- **THEN** fields owned by that optional observation are omitted
- **AND** already collected canonical status remains available
- **AND** generic endpoint failure does not authorize credential fallback

#### Scenario: Established read session returns HTTP 401 or 403

- **WHEN** an optional or required established-session read returns HTTP 401 or 403
- **THEN** status collection raises `SessionInvalidError`
- **AND** existing bounded same-credential recovery remains authoritative
- **AND** partial status is not emitted as successful final evidence

#### Scenario: Generic application-level unsuccessful response occurs

- **WHEN** a read returns HTTP 200 with generic `success: 0`
- **AND** no approved structured authentication discriminator exists
- **THEN** it remains an endpoint command/protocol failure
- **AND** arbitrary exception/message text does not advance credentials or switch models

### Requirement: CloudLink Bar 310 optional field ownership and precedence are closed

For the closed Bar/Box 310 family, canonical ordinary status SHALL use the following corrected ownership boundaries:

| Observation | Canonical fields |
| --- | --- |
| required version response | `model`, `version`; optional `serial_number`; structured camera/microphone version-or-built-in evidence |
| MAC read | `mac_address` |
| audio read | existing proved `mic_mute`, `speaker_mute`, `speaker_volume` fields only |
| line/SIP read | existing proved `uptime`, `sip_server`, `sip_number`, primary `sip_status` |
| modern `GET /v1/login/status` | `call_status`, `sleep_mode`; no new camera/microphone physical semantics |
| presentation read | `presentation` |

Version core validation remains unchanged: `softVersion` is required usable software-version evidence and the canonical model is the exact trusted handler/parser/display identity derived from the already assigned exact application model.

For successfully observed structured peripheral-version data, normalization SHALL distinguish usable version, structurally empty version, and unavailable/malformed evidence. Structurally empty `cameraVersion` SHALL publish canonical built-in-camera presentation evidence; structurally empty `micVersion` SHALL publish canonical built-in-microphone presentation evidence. Missing/malformed evidence SHALL publish neither a real version nor a built-in claim.

Modern state SHALL use exact case-sensitive key `callState` with this enum:

```text
0 -> No Call
1 -> Calling
2 -> Connected
3 -> Disconnected
```

The legacy lowercase `callstate` key and its prior 2/3 mapping SHALL NOT be used to parse modern state. Modern sleep SHALL use only:

```text
isSleep == 1 -> sleep_mode = On
isSleep == 0 -> sleep_mode = Off
```

Line-state SIP remains authoritative under its existing precedence rules unless a later approved change establishes modern-state SIP semantics.

The previous first-HD-AI selection rule is removed as user-visible microphone authority. A `/v1/mediacontrol/mic/devices` list MAY be retained for future evidence/research, but this change SHALL NOT create `mic_connection_status` or `mic_volume` from first HD-AI, first plugged HD-AI, `MIC1`, `state.mic`, `plugStatus`, `gainVolume`, list order, or another unapproved heuristic.

The previous legacy camera-source mapping is not replaced by `state.camera`. If no independently approved canonical camera-state source succeeds, `camera_status` remains unavailable. Camera version/type presentation is independent of camera activity/connection state.

Failure or absence of one optional observation SHALL NOT delete or manufacture fields owned by another observation. Parser/GUI boundaries SHALL NOT add endpoint-owned fields absent from the canonical handler mapping.

#### Scenario: Modern call state is connected

- **WHEN** accepted modern state reports `callState == 2`
- **THEN** canonical `call_status` is `Connected`
- **AND** the legacy enum does not invert it to `Disconnected`

#### Scenario: Modern call state is disconnected

- **WHEN** accepted modern state reports `callState == 3`
- **THEN** canonical `call_status` is `Disconnected`
- **AND** the legacy enum does not invert it to `Connected`

#### Scenario: Modern sleep state is zero

- **WHEN** accepted modern state reports `isSleep == 0`
- **THEN** canonical `sleep_mode` is `Off`
- **AND** zero remains an observed awake state rather than unavailable data

#### Scenario: Multiple HD-AI records are present

- **WHEN** microphone devices contain multiple HD-AI records with different plug/gain observations
- **THEN** list position does not select a user-visible microphone connection/gain
- **AND** no unapproved `mic_connection_status` or `mic_volume` is manufactured

#### Scenario: Camera state bit is present but unproved

- **WHEN** modern general state contains `camera`
- **THEN** this change does not convert that bit into canonical `camera_status`
- **AND** camera version/type presentation remains a separate semantic

#### Scenario: Structured camera version is empty

- **WHEN** required version response succeeds and its reviewed `cameraVersion` evidence is structurally empty
- **THEN** canonical presentation evidence represents built-in camera
- **AND** it does not imply a camera On/Off/connected state

#### Scenario: Structured microphone version is empty

- **WHEN** required version response succeeds and its reviewed `micVersion` evidence is structurally empty
- **THEN** canonical presentation evidence represents built-in microphone
- **AND** it does not imply connection, mute, gain, or signal level

### Requirement: CloudLink Bar 310 normalization distinguishes unavailable from observed state

For exact Bar/Box 310 operations, canonical status fields SHALL be populated only from successful structured observations whose semantics are approved. An unavailable optional observation SHALL cause its fields to be omitted rather than replaced with semantic defaults.

Legitimate numeric/boolean-like values such as `isSleep == 0`, `callState == 0`, speaker volume zero, or another approved observed zero SHALL remain present and SHALL NOT be mistaken for missing data.

Modern state normalization SHALL use the exact sleep/call mappings defined by this change. Unsupported modern values are endpoint-local protocol/unavailable outcomes rather than guessed states. The legacy sleep strings and lowercase legacy call mapper SHALL NOT override a successfully accepted modern state observation.

Structured version normalization SHALL distinguish empty from unavailable. Successfully observed empty camera/microphone version evidence may produce the approved built-in presentation state, while absence caused by failed/malformed/unavailable evidence SHALL remain unavailable. Vendor display dashes are not protocol input.

Separate semantics SHALL remain separate: version/type evidence SHALL NOT become connection/activity evidence; live meter evidence SHALL NOT become gain; `state.mic` SHALL NOT become physical connection; and `state.camera` SHALL NOT become camera connection/activity without a later contract.

#### Scenario: Modern state endpoint is unavailable

- **WHEN** the modern general-state observation is not successfully accepted
- **THEN** `call_status` and `sleep_mode` owned by that observation are omitted
- **AND** absence is not converted into `No Call` or awake

#### Scenario: Observed no-call state is zero

- **WHEN** modern state reports `callState == 0`
- **THEN** canonical call status remains `No Call`
- **AND** zero is not treated as unavailable

#### Scenario: Peripheral version evidence is missing because the response is malformed

- **WHEN** camera or microphone version evidence is absent/unusable because the observation is malformed or unavailable
- **THEN** the corresponding canonical presentation remains unavailable
- **AND** the application does not call the peripheral built-in merely from absence

## ADDED Requirements

### Requirement: CloudLink 310 modern read context is bounded, in-memory, and application-credential-owned

For exact `CloudLink Bar 310` and exact `CloudLink Box 310`, a modern read context SHALL be created only with the credential already assigned by the application/composition layer. The handler/worker SHALL NOT resolve, reorder, iterate, or persist credential candidates.

Modern read establishment SHALL use exactly the reviewed sequence:

```text
POST /v1/login/session
POST /v1/login/account
```

The account request SHALL carry only the required credential fields `account` and `password` plus non-secret vendor request context. A successful login SHALL provide a usable `data.acCSRFToken`. That value is in-memory session material and SHALL be transmitted as `X-Access-Token` for reviewed modern reads. Reviewed read-only action.cgi requests MAY additionally carry the same token in JSON field `acCSRFToken` according to the proven read shape.

The modern token, cookies, login payload, Authorization data, and raw authentication responses SHALL NOT be persisted or logged. Safe diagnostics MAY report endpoint, method, HTTP status, typed category, and non-secret structural outcome.

The modern read context SHALL be bound to the same exact model/IP/credential/generation identity as its owning CloudLink handler. When the owning context is superseded, its modern token/cookies/session become unusable for new work. Cleanup SHALL close the local session and SHOULD issue the owned temporary/vendor logout `DELETE /v1/login/session` best-effort before closure when appropriate.

An established modern read HTTP 401/403 SHALL be `SessionInvalidError` and may invoke only the existing bounded same-credential recovery path. Generic HTTP-200 `success: 0`, arbitrary `exception`, `error`, `code`, or `message` values without an approved vendor discriminator SHALL NOT authorize credential advancement, model switching, or string-heuristic authentication classification.

If the same handler generation also owns a legacy control subcontext, both are internal resources of the one exact operation identity. Context invalidation SHALL prevent either from being reused by stale work. State-changing operations remain subject to their existing no-blind-replay/reconciliation contract and SHALL NOT be moved to the modern read path by this requirement.

Protocol equivalence does not merge application identities. Bar and Box retain separate exact credential-success and connection-profile memory. Failure for one exact model never retries as the other.

#### Scenario: Modern read login succeeds

- **GIVEN** the application assigned one exact CloudLink model/IP and credential
- **WHEN** modern read login succeeds
- **THEN** the handler retains its access token only in memory
- **AND** reviewed reads use that session material
- **AND** no credential candidate is advanced or persisted by the handler

#### Scenario: Modern read login rejects the assigned credential

- **WHEN** the new-login boundary produces a structured `AuthenticationError`
- **THEN** the handler exposes that typed failure
- **AND** only the application-owned credential policy may consider the next candidate

#### Scenario: Established modern read returns HTTP 403

- **WHEN** a reviewed read on an established modern context returns HTTP 403
- **THEN** it raises `SessionInvalidError`
- **AND** same-credential bounded session recovery occurs before any credential advancement is considered

#### Scenario: Generic success zero occurs after login

- **WHEN** an established modern request returns HTTP 200 with `success: 0`
- **AND** no approved structured authentication discriminator is available
- **THEN** the result is not sufficient authority for credential fallback
- **AND** no response-string heuristic changes model or credential

#### Scenario: CloudLink context changes before queued read begins

- **WHEN** queued read work becomes stale because exact model, IP, credential context, or generation changed
- **THEN** it is dropped before handler acquisition/network I/O where separable
- **AND** old modern session material does not update or authenticate the replacement context

#### Scenario: Box and Bar success memory remains separate

- **GIVEN** the modern read context succeeds for exact `CloudLink Box 310`
- **WHEN** application-owned success memory is updated after the qualifying operation
- **THEN** only the exact Box model/IP memory may change
- **AND** no Bar credential index/profile is updated solely because the protocol implementation is shared
