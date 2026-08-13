# Design: CloudLink 310 runtime session corrections

## Context

Current `master` routes exact application models `CloudLink Bar 310` and `CloudLink Box 310` through the shared `CloudLinkBar310Handler` lifecycle while retaining distinct trusted identities. Credential selection/fallback correctly remains application/composition-owned, but the Bar read-session assumptions and several status normalizers are stale.

Read-only Bar research established this modern vendor session:

```text
POST /v1/login/session
POST /v1/login/account {account, password}
    -> data.acCSRFToken

reviewed modern requests
    -> X-Access-Token: <modern token>
```

The same vendor-equivalent session successfully read:

```text
GET /v1/mediacontrol/mic/current-volume
GET /v1/mediacontrol/mic/devices
GET /v1/om/config/systemtime
GET /v1/login/status?rmd=<cache-buster>
GET /v1/meeting/calls/history
POST action.cgi?ActionID=WEB_GetVersionInfoAPI
POST action.cgi?ActionID=WEB_GetSystemMacAddrAPI
POST action.cgi?ActionID=WEB_GetMailboxDataAPI
```

Only those exact action.cgi reads are live-verified on the modern context. Existing audio, line/SIP, presentation, camera, and other read-only action.cgi operations were not verified there and therefore remain on the existing legacy compatibility path in this change.

The project owner explicitly confirmed that the corrected common read architecture shall apply to the already supported Box 310 family member. This is a product/architecture decision based on the already approved shared Bar/Box protocol-family contract; it is not represented as separate Box hardware evidence. The Box-specific live-meter protocol remains unchanged.

## Goals

- Match the proven CloudLink modern read-session contract without broadening unverified endpoint claims.
- Preserve one application-selected credential and exact-model authority.
- Preserve existing verified legacy compatibility/control behavior where modern compatibility is unproved.
- Correct proved sleep/call/time/version presentation semantics.
- Remove contradicted microphone-selection assumptions rather than replace them with guesses.
- Make microphone-gain mutation fail closed until an authoritative target/readback contract exists.

## Non-goals

- Automatic Bar/Box model detection.
- Broad protocol modernization of unverified read-only or state-changing endpoints.
- Deriving camera activity/connection from `state.camera`.
- Deriving physical microphone connection or gain from `/mic/devices`.
- Changing Box live-meter payload semantics.
- Handler-owned credential iteration.

## Decision 1: one handler generation owns two bounded internal subcontexts

For exact `CloudLink Bar 310` or `CloudLink Box 310`, one application-selected credential creates one handler generation bound to immutable exact model, IP, credential-context identity, and generation.

```text
CloudLink handler generation
├─ modern read subcontext
│  ├─ modern HTTP session/cookies
│  └─ in-memory modern access token
└─ legacy compatibility/control subcontext
   └─ existing legacy session artifacts
```

The modern subcontext is authoritative only for operations explicitly approved as modern by this change. The legacy compatibility/control subcontext remains authoritative for existing unverified read-only action.cgi operations and existing supported mutations, except CloudLink microphone-gain mutation which this change explicitly disables.

Both subcontexts use the same credential assigned by the application. Neither handler nor worker may iterate credentials, advance candidates, change model identity, or persist successful credential/profile memory. Superseding model/IP/credential/generation invalidates both subcontexts as one handler generation.

## Decision 2: modern read login and teardown are closed

Modern read authentication SHALL use:

```text
POST /v1/login/session
POST /v1/login/account
JSON fields: account, password
```

A successful login must yield usable `data.acCSRFToken`. The token is session material, not a credential source, remains in memory only, and is transmitted as `X-Access-Token` for reviewed modern reads. Live-verified read-only action.cgi calls additionally use the same token in JSON field `acCSRFToken` according to the proved request shape.

Modern teardown uses vendor `DELETE /v1/login/session` best-effort, followed by local session closure. Teardown is idempotent/fail-closed for secrets: no token, cookie, credential, login payload, Authorization header, or raw auth body may be logged, persisted, or surfaced publicly.

## Decision 3: failure classification remains conservative

HTTP 401/403 during a confirmed new-login boundary may classify as `AuthenticationError`. HTTP 401/403 after a modern session is established is `SessionInvalidError` and enters existing bounded same-credential recovery.

Research found no vendor-verified discriminator proving that HTTP 200 plus generic `success: 0` means expired authentication. Therefore generic `success: 0`, arbitrary exception/message/code text, and strings containing `auth`, `401`, or `403` SHALL NOT authorize credential fallback or session-invalid classification.

## Decision 4: the modern reviewed read set is exact

The modern read subcontext is normative for the following proved operations:

```text
POST action.cgi?ActionID=WEB_GetVersionInfoAPI
POST action.cgi?ActionID=WEB_GetSystemMacAddrAPI
POST action.cgi?ActionID=WEB_GetMailboxDataAPI
GET /v1/login/status
GET /v1/meeting/calls/history
GET /v1/om/config/systemtime
GET /v1/mediacontrol/mic/current-volume   # Bar meter only
GET /v1/mediacontrol/mic/devices          # research/internal only; no product gain/connection semantics
```

The following existing read-only action.cgi operations are NOT newly authorized on the modern context by this change and remain on the legacy compatibility subcontext unless separately proved later:

```text
WEB_InitAudioCtrlParamsAPI
WEB_GetLineStateInfoAPI
WEB_IsSendAuxStreamAPI
WEB_GetCurCtrlCamSrcAPI
other unverified read-only action.cgi operations
```

This distinction prevents implementation from moving a working legacy read merely because another action.cgi endpoint succeeded under modern authentication.

## Decision 5: Bar/Box identity remains exact

Protocol sharing does not alias identities:

```text
CloudLink Bar 310 -> Huawei CloudLink Bar 310
CloudLink Box 310 -> Huawei CloudLink Box 310
```

Bar failure never retries as Box and Box failure never retries as Bar. Credential/profile success memory remains exact-model + IP scoped. When inventory cannot resolve an exact model, the existing purpose-bound manual fallback remains authoritative; no network model probe is added.

## Decision 6: meter remains model-specific

Bar meter remains exactly:

```text
GET /v1/mediacontrol/mic/current-volume
```

It now runs through the modern read context. Existing normalization remains authoritative: `data.curMicVouumeList` must be a list; every Mapping entry is eligible regardless of `deviceId`; maximum non-negative numeric `curVolume` is raw level; zero is available silence.

Box meter remains exactly:

```text
POST action.cgi?ActionID=WEB_GetCurrentAudioParam
```

with the already approved closed Box field set. This change does not redirect Box metering to the Bar endpoint.

## Decision 7: modern state owns only proved sleep and call semantics

Reviewed general state source:

```text
GET /v1/login/status
```

Approved mappings:

```text
state.isSleep == 1 -> sleep_mode = On
state.isSleep == 0 -> sleep_mode = Off

state.callState == 0 -> call_status = No Call
state.callState == 1 -> call_status = Calling
state.callState == 2 -> call_status = Connected
state.callState == 3 -> call_status = Disconnected
```

Missing/non-integral/unsupported values are unavailable/endpoint-local protocol outcomes. The modern key is case-sensitive `callState`; it SHALL NOT use the legacy lowercase `callstate` mapper whose 2/3 meanings differ.

`state.camera`, `state.mic`, `state.speaker`, `state.sip`, `shareState`, and `viSourceState` receive no new product authority here.

## Decision 8: peripheral version normalization is deterministic

`cameraVersion` and `micVersion` are normalized independently from a successful version response.

For each field:

```text
field absent
    -> unavailable
field present but not a list
    -> malformed/unavailable
[]
    -> built-in peripheral
non-empty list
    -> every element MUST be a Mapping
    -> every element MUST contain exact field "version"
    -> each version MUST be a string whose strip() is non-empty
    -> field "name" and all other members are ignored for presentation authority
    -> if any element violates the shape, the whole peripheral-version observation is malformed/unavailable
    -> otherwise strip versions, remove duplicate texts while preserving first source occurrence,
       then join remaining version texts with exact separator "; "
```

Thus a non-empty valid list always yields deterministic real version text; an empty list alone yields the built-in semantic. Partial acceptance of a malformed non-empty list is forbidden.

GUI presentation:

```text
cameraVersion == [] -> Встроенная камера
micVersion == []    -> Встроенный микрофон
valid non-empty list -> normalized joined version text
unavailable/malformed -> existing unavailable presentation
```

Vendor WebUI `--` is presentation only and is never parsed as protocol input. Version/type evidence does not imply camera activity, microphone connection, mute, gain, or signal level.

## Decision 9: first-HD-AI and gainVolume are removed from product authority

Live `/v1/mediacontrol/mic/devices` evidence contained multiple HD-AI groups where an earlier group was unplugged and a later group was plugged. Therefore list order/first-HD-AI is disproven authority.

This change stops publishing `mic_connection_status` and diagnostic `mic_volume` from first-HD-AI, first-plugged, `MIC1`, `state.mic`, `plugStatus`, `gainVolume`, or fixed device IDs. `/mic/devices` may remain an internal/research source only until a later approved semantic contract exists.

The live microphone signal meter is separate and remains supported.

## Decision 10: CloudLink microphone-gain mutation is disabled

Current shared-handler gain control performs state-changing `PUT` then fallback `POST` to `/v1/mediacontrol/mic/devices`, chooses target devices from unproved HD-AI semantics (including a fixed `4/5/6` fallback), and reconciles through first-HD-AI `gainVolume`. Those assumptions are incompatible with the corrected evidence boundary.

For exact Bar 310 and Box 310 in this change:

- user/operator microphone-gain mutation is unavailable/disabled;
- application/controller SHALL reject or disable the operation before device network I/O;
- implementation SHALL NOT send `PUT` or `POST /v1/mediacontrol/mic/devices` for gain;
- implementation SHALL NOT use fixed device IDs, first-HD-AI, first-plugged, or `gainVolume` as mutation target/reconciliation authority;
- no blind replay or alternate-method replay is permitted after an ambiguous result.

Re-enabling CloudLink gain requires a later approved change with authoritative target selection, request method, success semantics, and safe readback/reconciliation.

Other already-supported mutations such as Wake, presentation, mute, speaker volume, and SIP configuration remain on their existing legacy compatibility/control path and retain existing mutation-safety rules.

## Decision 11: codec-local reference time is used when available

CloudLink call history obtains:

```text
GET /v1/om/config/systemtime
```

Valid integer calendar components produce a naive codec-local `datetime` coherent with CloudLink call-history timestamps and are passed as device `reference_now`. If unavailable/malformed after allowed bounded recovery, the existing computer-local fallback and explicit warning remain. No timezone offset is invented.

## Decision 12: GUI is rendering-only

For exact Bar/Box contexts, the codec page adds visible rows:

```text
Режим сна
Версия камеры
Версия микрофона
```

The screen renders normalized canonical values only. It does not establish sessions, parse vendor containers, inspect `--`, choose credentials, infer model, or run blocking device I/O. Existing generation/currentness checks apply to all new values and live-meter callbacks.

CloudLink microphone-gain controls are disabled/unavailable under this change; the GUI must not offer an enabled control that can issue the prohibited gain mutation.

Camera connection/status remains unavailable unless an independently approved canonical `camera_status` source succeeds; `state.camera` is not a substitute.

## Testing strategy

Implementation must add regression coverage for:

- modern login/token/header/body/logout/redaction/cleanup;
- exact modern-read allowlist and legacy compatibility routing for unverified audio/line/presentation/camera reads;
- Bar/Box identity and credential-memory isolation;
- 401/403 bounded recovery and no auth inference from generic `success: 0`;
- Bar meter modern auth and unchanged normalization; Box meter preservation;
- modern `isSleep` and `callState` mappings;
- deterministic peripheral version-list normalization, including duplicates and malformed partial lists;
- removal of first-HD-AI/product gain/connection authority;
- disabled CloudLink microphone-gain mutation with proof of zero device I/O;
- codec-local time and explicit fallback;
- GUI rows/currentness/no stale callback updates;
- no automatic Bar/Box detection.

## Archive applicability

This change uses `MODIFIED Requirements`. Independent validation must perform the repository-required disposable archive-applicability check on the exact validated remote feature HEAD before `READY FOR ARCHIVE`.
