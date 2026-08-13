# device-diagnostics-and-control Specification

## MODIFIED Requirements

### Requirement: Model-specific interactive codec session paths

The shared interactive controller SHALL preserve the supported transports, session artifacts, and operation boundaries of Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310. A model SHALL use only its supported functions, and functions on a separate worker path SHALL remain separate unless explicitly listed.

CloudLink Bar 310 and CloudLink Box 310 SHALL continue to use the same reviewed `CloudLinkBar310Handler` protocol implementation while retaining their exact assigned application model in operation context. Shared protocol capability SHALL NOT authorize Bar/Box model aliasing, credential sharing, successful-index/profile sharing, or model switching during recovery.

For the CloudLink 310 family, one application-selected credential SHALL bind one handler generation for the exact model/IP/credential context. That generation MAY own two internal subcontexts:

```text
modern read subcontext
legacy state-changing control subcontext
```

The modern read subcontext SHALL be established through `POST /v1/login/session` followed by `POST /v1/login/account`, shall retain its cookies and returned token only in memory, and SHALL service the reviewed read-only `/v1` and compatible read-only action.cgi operations. The existing legacy control subcontext SHALL remain the authority for state-changing CloudLink operations unless a later approved change proves and authorizes a different mutation path. The modern-read evidence in this change SHALL NOT authorize replaying, migrating, or probing a mutation through the modern context.

Both CloudLink subcontexts belong to the same handler generation and assigned credential. Model/IP/credential-context/generation invalidation SHALL supersede both. Handler/worker code SHALL NOT iterate credential candidates; application/composition remains the credential-selection and fallback authority.

#### Scenario: Huawei TE20 interactive session

- **WHEN** TE20 performs live audio, sleep/Wake, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTP:80 and runtime-supported HTTPS:443 candidates with one credential
- **AND** recovery replaces invalid Session ID, cookie, CSRF, and transport state as one handler unit

#### Scenario: Huawei TE40 interactive session

- **WHEN** TE40 performs live audio, sleep-related presentation preparation, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTPS:443 and HTTP:80 candidates with one credential
- **AND** recovery replaces invalid opener, cookie, Session ID, CSRF, and browser-session state as one handler unit

#### Scenario: CloudLink Bar 310 read operation uses modern context

- **GIVEN** the exact interactive context model is `CloudLink Bar 310`
- **WHEN** a reviewed read-only CloudLink operation is executed
- **THEN** it uses HTTPS:443 with the application-selected credential and the modern read context
- **AND** the context remains exactly `CloudLink Bar 310`

#### Scenario: CloudLink Box 310 read operation uses modern context

- **GIVEN** the exact interactive context model is `CloudLink Box 310`
- **WHEN** a reviewed common read-only CloudLink operation is executed
- **THEN** it uses the shared handler modern read context
- **AND** the context remains exactly `CloudLink Box 310`
- **AND** recovery does not retry or relabel the operation as Bar 310

#### Scenario: CloudLink mutation stays on the legacy control path

- **WHEN** Bar 310 or Box 310 performs an already supported state-changing operation such as Wake, presentation mutation, mute/gain, volume, or SIP configuration
- **THEN** that operation remains on its existing approved legacy control path
- **AND** this change does not infer modern-session mutation compatibility from read-only evidence
- **AND** the state-changing command is not blindly replayed after an ambiguous result

#### Scenario: CloudLink generation is invalidated

- **WHEN** exact model, IP, relevant credential context, or handler generation is superseded
- **THEN** both modern-read and legacy-control resources owned by that generation are invalidated/closed
- **AND** stale callbacks cannot update the replacement context

#### Scenario: Polycom interactive controls

- **WHEN** Polycom performs volume, mute, or presentation work
- **THEN** its serialized shared handler uses HTTPS:443 login and the same credential for its lazy SSH:22 control session
- **AND** failure of either sub-session follows the bounded interactive recovery contract

#### Scenario: Polycom call log remains separate

- **WHEN** the operator loads the Polycom call log
- **THEN** the existing short-lived Polycom call-log worker remains the owner of that operation
- **AND** it is not routed through the Huawei/shared call-log session path

## ADDED Requirements

### Requirement: CloudLink 310 runtime presentation uses proved structured evidence

For exact `CloudLink Bar 310` and exact `CloudLink Box 310` contexts, the application SHALL present only CloudLink runtime values whose machine semantics are established by the reviewed protocol boundary. The codec page SHALL expose visible rows for:

```text
Режим сна
Версия камеры
Версия микрофона
```

Sleep SHALL be normalized from the reviewed modern state field only as:

```text
state.isSleep == 1 -> On
state.isSleep == 0 -> Off
```

Unsupported, missing, or malformed sleep evidence SHALL remain unavailable and SHALL NOT be replaced with `Off`.

Camera and microphone version/type presentation SHALL distinguish usable structured version evidence, successfully observed structured empty version evidence, and unavailable/malformed evidence. For successfully observed structured empty version evidence, GUI text SHALL be exactly:

```text
cameraVersion empty -> Встроенная камера
micVersion empty    -> Встроенный микрофон
```

Usable version evidence SHALL render the real normalized version text. Missing endpoint evidence, malformed structures, or failed reads SHALL remain unavailable and SHALL NOT be labelled built-in merely because no version was published.

The GUI SHALL NOT parse vendor WebUI display text such as `--` to determine semantics. The built-in labels are presentation of structured version/type evidence only and SHALL NOT imply camera activity, camera connection, microphone physical connection, mute state, gain, or live signal level.

This change establishes no user-visible physical camera state from `state.camera` and no physical microphone connection/gain authority from `state.mic`, `/v1/mediacontrol/mic/devices`, HD-AI list position, `MIC1`, `plugStatus`, or `gainVolume`. Those fields SHALL NOT be promoted into new product semantics without a later approved contract.

The screen SHALL remain a rendering boundary: it SHALL NOT establish sessions, choose/iterate credentials, infer Bar versus Box, parse vendor protocol containers, or perform blocking device I/O. Existing context/generation currentness SHALL protect all new rows from stale callbacks.

Model resolution remains outside this requirement. When inventory does not resolve one exact supported CloudLink model, the existing purpose-bound fallback model dialog remains authoritative; this change SHALL NOT probe the device to auto-detect Bar versus Box.

#### Scenario: CloudLink codec is sleeping

- **GIVEN** current exact model is Bar 310 or Box 310
- **WHEN** accepted modern state reports `isSleep == 1`
- **THEN** `Режим сна` renders the normalized sleeping state
- **AND** the GUI does not derive it from a legacy string or default

#### Scenario: CloudLink codec is awake

- **WHEN** accepted modern state reports `isSleep == 0`
- **THEN** `Режим сна` renders the normalized awake state
- **AND** numeric zero is not treated as missing evidence

#### Scenario: Camera version evidence is structurally empty

- **WHEN** the successful version response contains reviewed empty `cameraVersion` evidence
- **THEN** `Версия камеры` displays `Встроенная камера`
- **AND** no camera activity/connection state is inferred

#### Scenario: Microphone version evidence is structurally empty

- **WHEN** the successful version response contains reviewed empty `micVersion` evidence
- **THEN** `Версия микрофона` displays `Встроенный микрофон`
- **AND** no mute, connection, gain, or live-level state is inferred

#### Scenario: Peripheral version is usable

- **WHEN** successful camera or microphone version evidence contains a usable version
- **THEN** the corresponding row displays that real normalized version
- **AND** it does not display the built-in fallback

#### Scenario: Peripheral version endpoint evidence is unavailable

- **WHEN** version evidence is absent or malformed because the observation is unavailable
- **THEN** the corresponding GUI row remains unavailable
- **AND** absence is not converted into a built-in claim

#### Scenario: Inventory cannot resolve Bar or Box automatically

- **WHEN** the existing inventory/model-resolution flow reaches unresolved fallback
- **THEN** the operator may explicitly select `CloudLink Bar 310` or `CloudLink Box 310` through the existing fallback dialog
- **AND** this change performs no network model-detection probe
