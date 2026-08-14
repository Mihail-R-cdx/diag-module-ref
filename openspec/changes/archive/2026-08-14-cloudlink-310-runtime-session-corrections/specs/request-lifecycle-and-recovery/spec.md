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

Call history, system time, and Bar meter use their separately specified modern endpoints. The Box meter `WEB_GetCurrentAudioParam` is not part of this modern allowlist and remains on the existing legacy compatibility subcontext. `GET /v1/mediacontrol/mic/devices` has no user-visible connection/gain authority in this change.

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

#### Scenario: Configuration endpoint exists in the command map

- **GIVEN** `get_config` or `get_config_default` remains available for another handler purpose
- **WHEN** ordinary Bar 310 status refresh runs
- **THEN** the refresh does not invoke that configuration endpoint
- **AND** command-map membership alone does not grant polling authority

#### Scenario: Box meter remains on legacy compatibility context

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** live metering executes `WEB_GetCurrentAudioParam`
- **THEN** the existing legacy compatibility subcontext remains authoritative
- **AND** this change does not add that endpoint to the modern action.cgi allowlist

#### Scenario: Optional presentation read is unavailable

- **GIVEN** required version evidence and other status observations succeeded
- **WHEN** the optional presentation endpoint has an endpoint-local unsuccessful or malformed outcome
- **THEN** the handler preserves the already collected canonical fields
- **AND** it omits `presentation` from that refresh result
- **AND** it does not return an empty mapping
- **AND** generic endpoint failure does not authorize credential fallback

#### Scenario: Established session is rejected during optional read

- **GIVEN** Bar 310 shared session establishment and required core response succeeded
- **WHEN** an optional established-session request returns HTTP 401 or 403
- **THEN** status collection raises `SessionInvalidError`
- **AND** bounded same-credential recovery remains authoritative
- **AND** partial status is not emitted as final success evidence

#### Scenario: Optional read has a transport failure

- **WHEN** an optional Bar 310 request times out or loses transport
- **THEN** status collection raises `ConnectionError`
- **AND** the handler does not downgrade the transport failure to partial success

### Requirement: CloudLink Bar 310 optional field ownership and precedence are closed

For the closed Bar/Box family, canonical status SHALL use these boundaries:

| Observation | Canonical fields |
| --- | --- |
| required version response | `model`, `version`; optional `serial_number`; normalized camera/microphone version-or-built-in evidence |
| MAC read | `mac_address` |
| legacy-compatible audio read | existing approved `mic_mute`, `speaker_mute`, `speaker_volume` only |
| legacy-compatible line/SIP read | existing approved `uptime`, `sip_server`, `sip_number`, primary `sip_status` |
| modern `WEB_GetMailboxDataAPI` read | fallback `sip_status` only when line/SIP produced no valid SIP observation |
| modern `GET /v1/login/status` | `call_status`, `sleep_mode`; no camera/microphone physical semantics |
| legacy-compatible presentation read | `presentation` |
| independently approved legacy camera read, when usable | existing `camera_status`; never `state.camera` |

Version core validation remains unchanged: `softVersion` is required usable software-version evidence and canonical model is exact trusted identity derived from already assigned application model.

`WEB_GetSystemMacAddrAPI` SHALL preserve the existing MAC precedence: use the first non-empty observed value in this exact order:

```text
system_wanMAC_addr
system_lanMAC_addr
```

Line/SIP evidence SHALL preserve the existing precedence. A valid line-state SIP observation is authoritative. Mailbox/call-state `state.sip == 1` MAY populate `sip_status = On` and `state.sip == 0` MAY populate `sip_status = Off` only when line-state produced no valid `sip_status`. Mailbox evidence SHALL NOT overwrite valid line-state evidence; on disagreement line-state wins.

The independently approved legacy camera read SHALL preserve the existing exact mapping:

```text
localInMainSource == 255 -> camera_status = On
localInMainSource == 0   -> camera_status = Off
```

A missing or unsupported `localInMainSource` is an endpoint-local protocol failure and `camera_status` is omitted. Modern `state.camera` does not replace this mapping.

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

The legacy lowercase `callstate` mapper SHALL NOT parse modern state. The accepted modern `state.isSleep` observation is canonical sleep read authority for both ordinary full-status publication and interactive sleep readback. Existing Wake remains a state-changing operation on the legacy compatibility/control path and is not migrated by this read-authority change.

The previous first-HD-AI rule is removed as user-visible microphone authority. This change SHALL NOT create `mic_connection_status` or diagnostic `mic_volume` from first-HD-AI, first-plugged, `MIC1`, `state.mic`, `plugStatus`, `gainVolume`, fixed IDs, or list order.

Failure/absence of one optional observation SHALL NOT delete or manufacture fields owned by another observation.

#### Scenario: MAC WAN value has priority

- **GIVEN** a successful MAC response contains non-empty `system_wanMAC_addr` and `system_lanMAC_addr`
- **WHEN** canonical MAC is composed
- **THEN** `system_wanMAC_addr` is used

#### Scenario: MAC falls back to LAN value

- **GIVEN** a successful MAC response has no usable `system_wanMAC_addr`
- **AND** has non-empty `system_lanMAC_addr`
- **WHEN** canonical MAC is composed
- **THEN** `system_lanMAC_addr` is used

#### Scenario: Line and call SIP observations agree

- **GIVEN** line-state produced a valid SIP observation
- **AND** the modern shared-state/mailbox fallback source produced the same SIP observation
- **WHEN** canonical status is composed
- **THEN** the line-state value remains canonical
- **AND** the fallback source does not overwrite it

#### Scenario: Line and call SIP observations conflict

- **GIVEN** line-state produced a valid SIP observation
- **AND** the modern shared-state/mailbox fallback source produced the opposite SIP observation
- **WHEN** canonical status is composed
- **THEN** line-state wins
- **AND** the fallback source does not overwrite `sip_status`

#### Scenario: Call SIP fallback is used

- **GIVEN** line-state produced no valid SIP observation
- **AND** mailbox reports `state.sip == 1` or `state.sip == 0`
- **WHEN** canonical status is composed
- **THEN** mailbox supplies fallback `sip_status`

#### Scenario: Modern call state is connected

- **WHEN** accepted modern state reports `callState == 2`
- **THEN** canonical `call_status` is `Connected`
- **AND** legacy enum does not invert it

#### Scenario: Modern sleep zero is observed

- **WHEN** accepted modern state reports `isSleep == 0`
- **THEN** canonical `sleep_mode` is `Off`
- **AND** zero is not unavailable

#### Scenario: Modern sleep is interactive read authority

- **WHEN** ordinary status or interactive sleep readback obtains accepted modern `state.isSleep`
- **THEN** both paths use the same `1 -> On`, `0 -> Off` normalization
- **AND** the existing Wake mutation remains on the legacy control path

#### Scenario: Structured camera version is empty

- **WHEN** required version succeeds with `cameraVersion == []`
- **THEN** canonical presentation evidence is built-in camera
- **AND** no camera state is inferred

#### Scenario: Camera endpoint is unavailable

- **WHEN** the approved legacy camera endpoint is not successfully observed
- **THEN** `camera_status` is omitted
- **AND** the parser does not manufacture `Статус камеры = Подключена`

#### Scenario: Camera is observed disconnected

- **WHEN** the approved legacy camera read reports `localInMainSource == 0`
- **THEN** canonical `camera_status` is `Off`
- **AND** modern `state.camera` does not override it
- **AND** parser display status is `Не подключена`

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

#### Scenario: Successful HD-AI list is empty

- **WHEN** `/mic/devices` succeeds with a valid empty `deviceList` or no HD-AI entries
- **THEN** no `mic_connection_status` or diagnostic `mic_volume` is published from that response
- **AND** an observed disconnected microphone or numeric zero is not inferred
- **AND** live meter availability remains governed by its separate approved endpoint

#### Scenario: HD-AI microphone is physically disconnected

- **WHEN** an HD-AI entry reports `plugStatus == 0`
- **THEN** that field does not establish user-visible microphone connection authority
- **AND** no `mic_connection_status` or diagnostic `mic_volume` is manufactured

#### Scenario: Connected HD-AI microphone reports zero gain

- **WHEN** an HD-AI entry reports `plugStatus == 1` and `gainVolume == 0`
- **THEN** those fields do not establish user-visible connection or gain authority
- **AND** no diagnostic `mic_volume` is published from `gainVolume`
- **AND** zero remains available only when observed by the separate approved live-meter endpoint

#### Scenario: HD-AI list is malformed

- **WHEN** `/mic/devices` succeeds but `deviceList` is malformed
- **THEN** no `mic_connection_status` or diagnostic `mic_volume` is published from that response
- **AND** already collected canonical fields remain available

### Requirement: CloudLink Bar 310 normalization distinguishes unavailable from observed state

For exact Bar/Box operations, canonical fields SHALL be populated only from successful structured observations whose semantics are approved. Unavailable optional observations omit their fields rather than manufacture defaults.

Observed zero values such as `isSleep == 0`, `callState == 0`, or approved speaker-volume zero remain present.

Presentation normalization SHALL preserve the existing exact legacy mapping:

```text
isSendAux == auxOpen  -> Start
isSendAux == auxClose -> Stop
```

Unsupported or malformed presentation values are endpoint-local protocol failures and `presentation` is omitted. The same presentation normalization SHALL be used by ordinary full status and interactive presentation readback.

Sleep read normalization SHALL use accepted modern `state.isSleep` only:

```text
state.isSleep == 1 -> On
state.isSleep == 0 -> Off
```

Unsupported/malformed/missing modern sleep evidence is unavailable rather than guessed. Ordinary full status and interactive sleep readback SHALL use this same modern normalization. The existing state-changing Wake operation remains on the legacy compatibility/control path.

Structured version normalization SHALL distinguish empty from unavailable exactly as defined above. Vendor display dashes are not protocol input. Separate semantics remain separate: version/type does not become connection/activity; live meter does not become gain; `state.mic` does not become connection; `state.camera` does not become camera state.

#### Scenario: Modern state endpoint unavailable

- **WHEN** modern general-state observation is unavailable
- **THEN** `call_status` and `sleep_mode` are omitted
- **AND** absence is not converted into `No Call` or awake

#### Scenario: Presentation is observed inactive

- **WHEN** a successful structured presentation response reports `isSendAux == auxClose`
- **THEN** canonical `presentation` is `Stop`
- **AND** ordinary status and interactive readback use the same result

#### Scenario: Presentation endpoint is absent from a partial result

- **WHEN** legacy presentation observation is unavailable or malformed
- **THEN** `presentation` is omitted
- **AND** absence is not converted into `Stop`

#### Scenario: Sleep endpoint reports active sleep

- **WHEN** accepted modern state reports `isSleep == 1`
- **THEN** canonical `sleep_mode` is `On`
- **AND** ordinary status and interactive sleep readback produce the same value

#### Scenario: Observed speaker volume is zero

- **WHEN** a successful approved audio response reports a valid speaker volume of zero
- **THEN** canonical speaker volume remains present with value zero
- **AND** zero is not treated as unavailable data

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

Those reads use the proved modern session/header and body `acCSRFToken` shape. Other action.cgi reads SHALL remain on the legacy compatibility path until separately approved. In particular, Box meter `WEB_GetCurrentAudioParam` remains on the existing legacy compatibility subcontext under this change and SHALL NOT be routed through the modern action.cgi token shape.

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

#### Scenario: Box meter is not modernized by the common read allowlist

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** meter read requires `WEB_GetCurrentAudioParam`
- **THEN** it remains on the legacy compatibility subcontext
- **AND** modern read authorization for version/MAC/mailbox does not extend to that endpoint

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
