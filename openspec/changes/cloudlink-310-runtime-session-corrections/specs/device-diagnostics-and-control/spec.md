# device-diagnostics-and-control Specification

## MODIFIED Requirements

### Requirement: Model-specific interactive codec session paths

The shared interactive controller SHALL preserve the supported transports, session artifacts, and operation boundaries of Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310. A model SHALL use only its supported functions, and functions on a separate worker path SHALL remain separate unless explicitly listed.

CloudLink Bar 310 and CloudLink Box 310 SHALL continue to use the same reviewed `CloudLinkBar310Handler` implementation while retaining exact assigned application model in operation context. Shared protocol capability SHALL NOT authorize Bar/Box aliasing, credential sharing, successful-index/profile sharing, or model switching during recovery.

For the CloudLink 310 family, one application-selected credential SHALL bind one handler generation for the exact model/IP/credential context. That generation MAY own:

```text
modern read subcontext
legacy compatibility/control subcontext
```

The modern read subcontext SHALL be established through `POST /v1/login/session` followed by `POST /v1/login/account`, retain cookies/token in memory only, and service only operations explicitly approved for the modern context. Modern action.cgi compatibility in this change is limited to the exact live-verified read-only requests `WEB_GetVersionInfoAPI`, `WEB_GetSystemMacAddrAPI`, and `WEB_GetMailboxDataAPI`.

Existing unverified read-only action.cgi operations, including audio, line/SIP, presentation, and camera reads, SHALL remain on the existing legacy compatibility path unless a later approved change proves their modern compatibility. The Box-specific live-meter read `WEB_GetCurrentAudioParam` is an explicit member of that legacy compatibility path in this change and is not added to the modern action.cgi allowlist. Existing supported state-changing action.cgi operations SHALL remain on the legacy compatibility/control path and retain their existing mutation-safety rules.

CloudLink microphone-gain mutation is an explicit exception: for exact Bar 310 and Box 310 it SHALL be unavailable/disabled in this change because authoritative target selection and reconciliation are not established. The application/controller SHALL reject or disable that operation before device network I/O. It SHALL NOT issue gain `PUT`/`POST /v1/mediacontrol/mic/devices`, use fixed device IDs, use first-HD-AI/first-plugged selection, or use `gainVolume` as authoritative reconciliation. Re-enabling gain requires a later approved contract.

Both CloudLink subcontexts belong to one handler generation and assigned credential. Model/IP/credential-context/generation invalidation SHALL supersede both. Handler/worker code SHALL NOT iterate credential candidates; application/composition remains credential-selection/fallback authority.

#### Scenario: CloudLink Bar 310 reviewed read uses modern context

- **GIVEN** exact model is `CloudLink Bar 310`
- **WHEN** an operation explicitly approved for the modern read context executes
- **THEN** it uses HTTPS:443 with the application-selected credential and modern session artifacts
- **AND** the context remains exactly `CloudLink Bar 310`

#### Scenario: CloudLink Box 310 reviewed read uses modern context

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** an approved common modern read executes
- **THEN** it uses the shared handler modern read context
- **AND** exact Box identity remains unchanged
- **AND** recovery does not relabel or retry as Bar 310

#### Scenario: Unverified action.cgi read remains legacy-compatible

- **WHEN** CloudLink refresh or interactive work needs existing audio, line/SIP, presentation, camera, or another read-only action.cgi operation not live-verified on modern auth
- **THEN** this change does not migrate that operation to the modern context
- **AND** its existing legacy compatibility path remains authoritative until separately approved

#### Scenario: Box live meter remains legacy-compatible

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** live metering executes `WEB_GetCurrentAudioParam`
- **THEN** the request uses the existing legacy compatibility subcontext
- **AND** this change does not require modern `X-Access-Token` or modern body-token routing for that endpoint

#### Scenario: Existing CloudLink mutation stays on legacy control path

- **WHEN** Bar 310 or Box 310 performs an already supported mutation other than microphone gain, such as Wake, presentation mutation, mute, speaker volume, or SIP configuration
- **THEN** the operation remains on its existing legacy compatibility/control path
- **AND** modern read evidence does not authorize migration or blind replay

#### Scenario: CloudLink microphone gain is disabled

- **GIVEN** exact model is `CloudLink Bar 310` or `CloudLink Box 310`
- **WHEN** user or application attempts microphone-gain mutation
- **THEN** the operation is unavailable/disabled before device network I/O
- **AND** no gain PUT/POST, fixed-ID target, first-HD-AI selection, or gain readback is attempted
- **AND** no ambiguous mutation result can trigger alternate-method replay

#### Scenario: CloudLink generation is invalidated

- **WHEN** exact model, IP, relevant credential context, or generation is superseded
- **THEN** modern-read and legacy-compatibility/control resources are invalidated/closed
- **AND** stale callbacks cannot update the replacement context

#### Scenario: Huawei TE20 interactive session

- **WHEN** TE20 performs live audio, sleep/Wake, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTP:80 and runtime-supported HTTPS:443 candidates with one credential
- **AND** recovery replaces invalid Session ID, cookie, CSRF, and transport state as one handler unit

#### Scenario: Huawei TE40 interactive session

- **WHEN** TE40 performs live audio, sleep-related presentation preparation, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTPS:443 and HTTP:80 candidates with one credential
- **AND** recovery replaces invalid opener, cookie, Session ID, CSRF, and browser-session state as one handler unit

#### Scenario: Polycom interactive controls

- **WHEN** Polycom performs volume, mute, or presentation work
- **THEN** its serialized shared handler uses HTTPS:443 login and the same credential for its lazy SSH:22 control session
- **AND** failure of either sub-session follows bounded interactive recovery

#### Scenario: Polycom call log remains separate

- **WHEN** operator loads Polycom call log
- **THEN** the existing short-lived Polycom call-log worker remains owner
- **AND** it is not routed through Huawei/shared call-log session path

## ADDED Requirements

### Requirement: CloudLink 310 runtime presentation uses proved structured evidence

For exact `CloudLink Bar 310` and exact `CloudLink Box 310`, the codec page SHALL expose visible rows:

```text
Режим сна
Версия камеры
Версия микрофона
```

Sleep SHALL normalize only:

```text
state.isSleep == 1 -> On
state.isSleep == 0 -> Off
```

Unsupported/missing/malformed sleep evidence remains unavailable and SHALL NOT become `Off`.

Peripheral version/type normalization SHALL use exact structured rules for each of `cameraVersion` and `micVersion`:

```text
field absent -> unavailable
field not a list -> malformed/unavailable
[] -> built-in
non-empty list -> every element must be a Mapping with exact non-empty string field "version"
                  ignore "name" and other fields for presentation authority
                  any malformed element makes the whole peripheral observation unavailable
                  otherwise strip versions, remove duplicate texts preserving first source order,
                  join with exact separator "; "
```

Successfully observed empty fields render exactly:

```text
cameraVersion == [] -> Встроенная камера
micVersion == []    -> Встроенный микрофон
```

A valid non-empty list renders the deterministic joined real-version text. Missing/malformed/unavailable evidence remains unavailable. The GUI SHALL NOT parse vendor WebUI `--`.

Version/type evidence SHALL NOT imply camera activity/connection, microphone physical connection, mute, gain, or live signal. `state.camera`, `state.mic`, `/v1/mediacontrol/mic/devices`, HD-AI list position, `MIC1`, `plugStatus`, and `gainVolume` receive no new user-visible physical/gain authority.

The screen remains rendering-only and SHALL NOT establish sessions, choose credentials, infer Bar versus Box, parse vendor containers, or perform blocking device I/O. Existing generation/currentness protects all new rows from stale callbacks.

CloudLink microphone-gain controls SHALL be disabled/unavailable for Bar/Box under this change; the GUI SHALL NOT expose an enabled control that can submit the prohibited gain mutation.

Model resolution remains unchanged. If inventory cannot resolve one exact supported CloudLink model, the existing purpose-bound fallback dialog remains authoritative; no network Bar/Box detector is introduced.

#### Scenario: CloudLink codec is sleeping

- **WHEN** accepted modern state reports `isSleep == 1`
- **THEN** `Режим сна` renders sleeping state
- **AND** GUI does not derive it from a legacy string/default

#### Scenario: CloudLink codec is awake

- **WHEN** accepted modern state reports `isSleep == 0`
- **THEN** `Режим сна` renders awake state
- **AND** zero is not treated as missing

#### Scenario: Camera version list is empty

- **WHEN** successful version response contains `cameraVersion == []`
- **THEN** `Версия камеры` displays `Встроенная камера`
- **AND** no camera activity/connection is inferred

#### Scenario: Microphone version list is empty

- **WHEN** successful version response contains `micVersion == []`
- **THEN** `Версия микрофона` displays `Встроенный микрофон`
- **AND** no connection/mute/gain/live-level state is inferred

#### Scenario: Multiple valid peripheral versions are present

- **WHEN** non-empty peripheral list contains valid version strings with duplicates
- **THEN** duplicate texts are removed preserving first source occurrence
- **AND** remaining texts are joined with `; `
- **AND** `name` does not affect display

#### Scenario: Non-empty peripheral list is partially malformed

- **WHEN** any entry is non-Mapping, lacks exact `version`, or has empty/non-string `version`
- **THEN** the whole peripheral-version observation is unavailable
- **AND** valid siblings are not partially rendered
- **AND** built-in fallback is not manufactured

#### Scenario: Inventory cannot resolve Bar or Box automatically

- **WHEN** existing inventory/model-resolution reaches unresolved fallback
- **THEN** operator may explicitly select `CloudLink Bar 310` or `CloudLink Box 310`
- **AND** this change performs no network model-detection probe
