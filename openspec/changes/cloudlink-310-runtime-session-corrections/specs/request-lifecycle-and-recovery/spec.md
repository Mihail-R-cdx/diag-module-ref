# request-lifecycle-and-recovery Specification

## MODIFIED Requirements

### Requirement: CloudLink Bar 310 polling uses a closed resilient status plan

For the closed exact `CloudLink Bar 310` / `CloudLink Box 310` protocol family, ordinary status refresh SHALL execute an explicit reviewed read-only plan and SHALL NOT iterate every handler command.

The required core observation remains version. Modern read context is normative only for exact operations live-verified by this change:

```text
POST action.cgi?ActionID=WEB_GetVersionInfoAPI
POST action.cgi?ActionID=WEB_GetSystemMacAddrAPI
POST action.cgi?ActionID=WEB_GetMailboxDataAPI
GET /v1/login/status
```

Call history, system time, and Bar meter use their separately specified modern endpoints. `GET /v1/mediacontrol/mic/devices` has no user-visible connection/gain authority in this change.

Existing safe read-only action.cgi audio, line/SIP, presentation, camera, and other operations not live-verified on modern authentication SHALL remain on the legacy compatibility subcontext. This change SHALL NOT migrate them to modern authentication merely because other action.cgi requests succeeded there.

Configuration requests, state-changing operations, future command-map entries, camera-state guesses, and microphone connection/gain guesses SHALL NOT enter ordinary polling merely because a handler method exists.

After required core success, endpoint-local `CommandError`/`ProtocolError` for optional observations omits only fields owned by that observation. `AuthenticationError`, `SessionInvalidError`, and `ConnectionError` remain terminal typed failures under existing phase-aware policy. Generic HTTP-200 `success: 0` without approved auth discriminator does not authorize credential fallback.

Exact assigned Bar/Box identity remains authoritative; shared polling SHALL NOT detect, relabel, retry, or fall back to the other family member.

#### Scenario: Live-verified action.cgi read uses modern context

- **WHEN** ordinary refresh executes version, MAC, or mailbox action.cgi read
- **THEN** it may use the proved modern header/body-token request shape
- **AND** exact model identity remains unchanged

#### Scenario: Unverified audio read remains legacy-compatible

- **WHEN** ordinary refresh needs existing audio status
- **THEN** this change does not migrate `WEB_InitAudioCtrlParamsAPI` to modern auth
- **AND** the existing legacy compatibility read path remains authoritative

#### Scenario: Unverified line or presentation read remains legacy-compatible

- **WHEN** ordinary refresh needs existing line/SIP or presentation observation
- **THEN** this change does not migrate those action.cgi requests to modern auth
- **AND** their existing legacy compatibility path remains authoritative

#### Scenario: Optional read is unavailable

- **GIVEN** required version evidence succeeded
- **WHEN** one optional read has endpoint-local unsuccessful/malformed outcome
- **THEN** its fields are omitted
- **AND** already collected status remains available
- **AND** generic endpoint failure does not authorize credential fallback

#### Scenario: Established modern read returns HTTP 401 or 403

- **WHEN** reviewed established modern read returns HTTP 401 or 403
- **THEN** status collection raises `SessionInvalidError`
- **AND** bounded same-credential recovery remains authoritative
- **AND** partial status is not emitted as final success evidence

### Requirement: CloudLink Bar 310 optional field ownership and precedence are closed

For the closed Bar/Box family, canonical status SHALL use these boundaries:

| Observation | Canonical fields |
| --- | --- |
| required version response | `model`, `version`; optional `serial_number`; normalized camera/microphone version-or-built-in evidence |
| MAC read | `mac_address` |
| legacy-compatible audio read | existing approved `mic_mute`, `speaker_mute`, `speaker_volume` only |
| legacy-compatible line/SIP read | existing approved `uptime`, `sip_server`, `sip_number`, primary `sip_status` |
| modern `GET /v1/login/status` | `call_status`, `sleep_mode`; no camera/microphone physical semantics |
| legacy-compatible presentation read | `presentation` |
| independently approved legacy camera read, when usable | existing `camera_status`; never `state.camera` |

Version core validation remains unchanged: `softVersion` is required usable software-version evidence and canonical model is exact trusted identity derived from already assigned application model.

Peripheral version normalization is exact and independent for `cameraVersion` and `micVersion`:

```text
absent -> unavailable
non-list -> malformed/unavailable
[] -> built-in
non-empty list:
    every entry must be Mapping
    exact entry["version"] must be string
    strip() must be non-empty
    ignore name/other fields for presentation authority
    any malformed entry -> whole peripheral observation unavailable
    otherwise strip all versions, de-duplicate exact texts preserving first source order,
    join with exact separator "; "
```

A valid empty list publishes built-in presentation evidence. Missing/malformed evidence publishes neither real version nor built-in claim.

Modern state mappings:

```text
callState 0 -> No Call
callState 1 -> Calling
callState 2 -> Connected
callState 3 -> Disconnected
isSleep 1 -> On
isSleep 0 -> Off
```

The legacy lowercase `callstate` mapper SHALL NOT parse modern state. Line-state SIP retains existing precedence unless later approved modern SIP semantics exist.

The previous first-HD-AI rule is removed as user-visible microphone authority. This change SHALL NOT create `mic_connection_status` or diagnostic `mic_volume` from first-HD-AI, first-plugged, `MIC1`, `state.mic`, `plugStatus`, `gainVolume`, fixed IDs, or list order.

The previous legacy camera-source mapping is not replaced by `state.camera`. If no independently approved canonical camera-state observation succeeds, `camera_status` remains unavailable.

Failure/absence of one optional observation SHALL NOT delete or manufacture fields owned by another observation.

#### Scenario: Modern call state is connected

- **WHEN** accepted modern state reports `callState == 2`
- **THEN** canonical `call_status` is `Connected`
- **AND** legacy enum does not invert it

#### Scenario: Modern sleep zero is observed

- **WHEN** accepted modern state reports `isSleep == 0`
- **THEN** canonical `sleep_mode` is `Off`
- **AND** zero is not unavailable

#### Scenario: Structured camera version is empty

- **WHEN** required version succeeds with `cameraVersion == []`
- **THEN** canonical presentation evidence is built-in camera
- **AND** no camera state is inferred

#### Scenario: Valid multiple microphone versions are present

- **WHEN** non-empty `micVersion` list contains valid version strings including duplicates
- **THEN** duplicates are removed preserving first occurrence
- **AND** remaining versions join with `; `

#### Scenario: Partially malformed version list is rejected

- **WHEN** any element of non-empty peripheral version list violates required Mapping/`version` shape
- **THEN** whole peripheral observation is unavailable
- **AND** valid siblings are not partially published
- **AND** built-in is not inferred

#### Scenario: Multiple HD-AI records are present

- **WHEN** `/mic/devices` contains multiple HD-AI records
- **THEN** list position does not select user-visible connection/gain
- **AND** no unapproved `mic_connection_status` or `mic_volume` is manufactured

### Requirement: CloudLink Bar 310 normalization distinguishes unavailable from observed state

For exact Bar/Box operations, canonical fields SHALL be populated only from successful structured observations whose semantics are approved. Unavailable optional observations omit their fields rather than manufacture defaults.

Observed zero values such as `isSleep == 0`, `callState == 0`, or approved speaker-volume zero remain present.

Structured version normalization SHALL distinguish empty from unavailable exactly as defined above. Vendor display dashes are not protocol input. Separate semantics remain separate: version/type does not become connection/activity; live meter does not become gain; `state.mic` does not become connection; `state.camera` does not become camera state.

#### Scenario: Modern state endpoint unavailable

- **WHEN** modern general-state observation is unavailable
- **THEN** `call_status` and `sleep_mode` are omitted
- **AND** absence is not converted into `No Call` or awake

#### Scenario: Peripheral version field is malformed

- **WHEN** peripheral version evidence violates the approved list shape
- **THEN** its presentation remains unavailable
- **AND** built-in fallback is not manufactured

## ADDED Requirements

### Requirement: CloudLink 310 modern read context is bounded, in-memory, and application-credential-owned

For exact `CloudLink Bar 310` and `CloudLink Box 310`, modern read context SHALL be created only with the credential assigned by application/composition. Handler/worker SHALL NOT resolve, reorder, iterate, or persist credential candidates.

Modern establishment SHALL use exactly:

```text
POST /v1/login/session
POST /v1/login/account
```

Account request carries required credential fields `account` and `password` plus non-secret vendor context. Successful login provides usable `data.acCSRFToken`, retained only in memory and transmitted as `X-Access-Token` for approved modern reads.

The only action.cgi reads newly authorized on the modern context by this change are:

```text
WEB_GetVersionInfoAPI
WEB_GetSystemMacAddrAPI
WEB_GetMailboxDataAPI
```

Those reads use the proved modern session/header and body `acCSRFToken` shape. Other action.cgi reads SHALL remain on the legacy compatibility path until separately approved.

Modern token/cookies/login payload/Authorization/raw auth responses SHALL NOT be persisted or logged. Safe diagnostics may report endpoint, method, HTTP status, typed category, and non-secret structural outcome.

Owning model/IP/credential/generation invalidation makes modern resources unusable for new work. Cleanup closes local session and SHOULD best-effort `DELETE /v1/login/session` when appropriate.

Established modern HTTP 401/403 SHALL be `SessionInvalidError` and may invoke only existing bounded same-credential recovery. Generic HTTP-200 `success: 0` and arbitrary exception/error/code/message without approved vendor discriminator SHALL NOT authorize credential advancement/model switching/string-heuristic auth classification.

If same handler generation owns legacy compatibility/control subcontext, both remain internal resources of one exact operation identity. Protocol equivalence does not merge Bar/Box application identities or success memory.

#### Scenario: Modern read login succeeds

- **WHEN** modern login succeeds for application-assigned exact model/IP/credential
- **THEN** handler retains access token only in memory
- **AND** only approved modern reads use it
- **AND** handler does not advance credentials

#### Scenario: Generic success zero occurs after login

- **WHEN** established modern request returns HTTP 200 with `success: 0`
- **AND** no approved auth discriminator exists
- **THEN** result does not authorize credential fallback
- **AND** response-string heuristics do not change model/credential

#### Scenario: Unverified action.cgi endpoint is requested

- **WHEN** an existing read-only action.cgi endpoint outside version/MAC/mailbox is required
- **THEN** this change does not authorize modern header/body-token routing for it
- **AND** existing legacy compatibility path remains authoritative

### Requirement: CloudLink 310 microphone gain is fail-closed until target and readback semantics are approved

For exact `CloudLink Bar 310` and exact `CloudLink Box 310`, interactive microphone-gain mutation SHALL be unavailable/disabled under this change.

Application/controller SHALL prevent the operation before device network I/O. Implementation SHALL NOT send `PUT` or `POST /v1/mediacontrol/mic/devices` for gain, SHALL NOT fall back between mutation methods, SHALL NOT target fixed device IDs such as `4/5/6`, and SHALL NOT select target/reconciliation from first-HD-AI, first-plugged, `MIC1`, `plugStatus`, `gainVolume`, `state.mic`, or list order.

No unavailable/ambiguous outcome may be resolved by blind replay. Re-enabling gain requires a later approved contract that defines authoritative target identity, mutation method, success semantics, and safe readback/reconciliation.

Live microphone meter remains a separate read-only semantic and SHALL remain available according to the meter specification.

#### Scenario: User attempts CloudLink microphone gain

- **WHEN** user attempts microphone-gain control for Bar 310 or Box 310
- **THEN** control is disabled or operation is rejected as unavailable before device I/O
- **AND** no gain PUT/POST is sent
- **AND** no alternate-method replay or first-HD-AI readback occurs

#### Scenario: Meter continues while gain is disabled

- **WHEN** CloudLink live microphone meter is active
- **THEN** gain-control unavailability does not disable the independent live meter observation
