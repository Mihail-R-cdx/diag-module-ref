# Design: CloudLink 310 runtime session corrections

## Context

Current `master` routes exact application models `CloudLink Bar 310` and `CloudLink Box 310` through the shared `CloudLinkBar310Handler` lifecycle while retaining distinct trusted product identities. Existing architecture correctly keeps credential selection/fallback in the application/composition layer, but its Bar read-session assumptions are stale.

Read-only protocol research established the following Bar facts without persisting credentials, cookies, tokens, or raw responses:

```text
POST /v1/login/session
POST /v1/login/account {account, password}
    -> data.acCSRFToken

subsequent read requests
    -> X-Access-Token: <modern token>
```

The same vendor-equivalent modern session successfully read:

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

The tested read-only action.cgi shape used vendor browser headers including `X-Access-Token` and the same token in JSON field `acCSRFToken`. Static WebUI source did not perform the legacy `WEB_RequestSessionIDAPI` / `WEB_RequestCertificateAPI` handshake for that read context.

The project owner has confirmed that the corrected common read-only command/session behavior shall apply to the already supported Box 310 family member as well. This is a product/architecture decision built on the existing approved shared-protocol-family contract; it is not represented as separate live Box hardware evidence.

## Goals

- Make the CloudLink 310 read path match the proven vendor session contract.
- Preserve one application-selected credential and exact-model authority.
- Preserve the existing legacy state-changing control path until mutation compatibility is separately proven.
- Correct read-only runtime fields whose semantics are now established.
- Remove contradicted microphone-selection assumptions rather than replace them with new guesses.
- Keep Bar and Box exact identities distinct despite shared protocol implementation.

## Non-goals

- Automatic Bar/Box model detection.
- Broad protocol modernization of state-changing commands.
- Deriving camera state from `state.camera`.
- Deriving physical microphone connection or user gain from the current `/mic/devices` list.
- Changing Box live-meter payload semantics.
- Introducing a handler-owned credential chain or a second credential source.

## Decision 1: one handler generation owns two bounded internal subcontexts

For exact `CloudLink Bar 310` or `CloudLink Box 310`, one application-selected credential creates one shared handler generation bound to immutable exact model, IP, credential-context identity, and operation/session generation.

The handler may own two internal protocol subcontexts:

```text
CloudLink handler generation
├─ modern read subcontext
│  ├─ HTTP session/cookies
│  └─ in-memory modern access token
└─ legacy control subcontext
   └─ existing state-changing action.cgi session artifacts
```

The modern read subcontext is authoritative for the reviewed read-only operations defined by this change. The legacy control subcontext remains authoritative for existing mutations. It may be established lazily when a mutation actually needs it.

Both subcontexts use the same credential already assigned by the application. Neither handler nor worker may iterate credentials, advance credential candidates, change the exact model, or persist successful credential/profile memory. Superseding model/IP/credential/generation invalidates both subcontexts as one handler generation.

## Decision 2: modern read login and teardown are closed

Modern read authentication SHALL use this sequence:

```text
POST /v1/login/session
POST /v1/login/account
JSON fields: account, password
```

A successful login must yield a usable `data.acCSRFToken`. The token is session material, not a credential source, and remains only in memory. Reviewed modern reads send it as `X-Access-Token`. Reviewed read-only action.cgi calls also send it in body field `acCSRFToken` when that request family requires the proven shape.

Modern teardown uses the vendor `DELETE /v1/login/session` for the owned modern context when feasible, followed by local HTTP-session closure. Teardown is best-effort and idempotent; failure to log out must not leak the token or block local cleanup.

No token, cookie, Authorization header, credential, login payload, or raw response body may be written to logs, dialogs, public errors, tests, OpenSpec artifacts, or validation evidence.

## Decision 3: failure classification remains conservative

HTTP 401/403 during new modern login is authentication failure only when the login boundary can classify it as such. HTTP 401/403 after the session is established is `SessionInvalidError` and enters the existing bounded same-credential recovery policy.

Live research did not establish a unique structured discriminator that maps HTTP 200 plus `success: 0` to expired authentication. Therefore generic `success: 0`, arbitrary `exception`/`message` text, and strings containing `auth`, `401`, or `403` SHALL NOT authorize credential fallback or session-invalid classification. Such outcomes remain endpoint command/protocol failures unless a later approved structured vendor discriminator is added.

This preserves the existing rule that credential advancement is application-owned and occurs only after a structured new-login authentication failure.

## Decision 4: common reviewed read set applies to Bar and Box

After exact model assignment, both CloudLink 310 family members may use the modern read context for the reviewed common reads supported by the shared lifecycle, including version, MAC, mailbox state, call history, system time, and general status fields described by this change.

Protocol sharing does not alias identities:

```text
CloudLink Bar 310 -> Huawei CloudLink Bar 310
CloudLink Box 310 -> Huawei CloudLink Box 310
```

Bar failure never retries as Box and Box failure never retries as Bar. Credential index/profile memory stays scoped to exact model + IP.

If inventory cannot resolve an exact supported model, the existing purpose-bound fallback dialog remains required. This change performs no network model probing and creates no automatic Bar/Box detector.

## Decision 5: meter remains model-specific

Bar meter source remains exactly:

```text
GET /v1/mediacontrol/mic/current-volume
```

but now runs through the modern read context and therefore transmits the modern `X-Access-Token`. The already implemented normalization remains authoritative: `data.curMicVouumeList` must be a list, every Mapping entry is eligible regardless of `deviceId`, the maximum non-negative numeric `curVolume` is the raw observation, and raw zero is available silence.

Box meter source remains exactly:

```text
POST action.cgi?ActionID=WEB_GetCurrentAudioParam
```

with the already approved closed Box microphone field set. This change does not redirect Box metering to the Bar `/v1` endpoint and does not broaden Box field discovery.

## Decision 6: modern state owns only proved sleep and call semantics

The reviewed general state source is:

```text
GET /v1/login/status
```

A cache-busting `rmd` query parameter may be used as transport anti-cache detail but has no product semantics.

Approved mappings:

```text
state.isSleep == 1 -> sleep_mode = On
state.isSleep == 0 -> sleep_mode = Off

state.callState == 0 -> call_status = No Call
state.callState == 1 -> call_status = Calling
state.callState == 2 -> call_status = Connected
state.callState == 3 -> call_status = Disconnected
```

Missing, non-integral, or unsupported values are unavailable/endpoint-local protocol outcomes; they are not guessed.

The modern key is case-sensitive `callState`. It SHALL NOT be passed through the legacy lowercase `callstate` mapper whose 2/3 enum meaning differs.

Other observed state members such as `camera`, `mic`, `speaker`, `sip`, `shareState`, and `viSourceState` receive no new product authority from this change. In particular, `state.camera` is not camera connection/state evidence and `state.mic` is not physical microphone connection evidence.

## Decision 7: version/type presentation uses structured evidence

The version response may expose `cameraVersion` and `micVersion` as structured vendor values.

The normalization boundary distinguishes three states for each peripheral:

1. usable version evidence -> publish the usable version text;
2. structurally successful but empty peripheral-version evidence -> publish an explicit built-in marker;
3. absent/malformed/unavailable version evidence -> publish no authoritative value.

GUI presentation is exact:

```text
camera built-in -> Встроенная камера
microphone built-in -> Встроенный микрофон
usable version -> real normalized version text
unavailable -> existing unavailable presentation
```

Vendor WebUI display text `--` is not parsed or used as machine authority. Empty structured evidence is the machine boundary. Built-in version/type presentation does not assert mute, physical connection, camera activity, microphone gain, or live signal level.

## Decision 8: first-HD-AI is removed from product authority

Live `/v1/mediacontrol/mic/devices` evidence contained multiple HD-AI groups where an earlier group was unplugged and a later group was plugged. Therefore list order and `first HD-AI` are disproven authority.

This change SHALL stop publishing `mic_connection_status` or `mic_volume` from the current first-HD-AI algorithm. It SHALL NOT replace that rule with `first plugged`, `MIC1`, `state.mic`, or a `gainVolume` guess. `/mic/devices` may remain a future research source, but its role/aggregation/gain semantics require a later approved contract before becoming user-visible authority.

The live signal meter remains a separate semantic and is unaffected by this removal.

## Decision 9: codec-local reference time is used when available

For CloudLink call history, the modern read context obtains:

```text
GET /v1/om/config/systemtime
```

A successful response with valid integer calendar components produces a naive codec-local `datetime` coherent with the CloudLink call-history timestamps and is passed as `reference_now` with `reference_time_source = device`.

The existing call-log specification remains authoritative: if device time is unavailable/malformed after allowed bounded recovery, computer-local time is used with the existing explicit non-modal fallback warning. No timezone offset is invented because the observed endpoint did not provide one.

## Decision 10: GUI is a rendering boundary

For exact Bar/Box contexts, the codec page adds visible rows:

```text
Режим сна
Версия камеры
Версия микрофона
```

The screen renders normalized canonical values only. It does not perform login, parse vendor protocol containers, inspect `--`, choose credentials, infer model, or run blocking network I/O. Existing stale-context/generation checks apply to all new values and live-meter callbacks.

Camera connection/status remains unavailable unless some independently approved canonical `camera_status` exists. This change does not manufacture one from version presence or `state.camera`.

## Testing strategy

Implementation must add regression coverage for:

- modern login sequence, token extraction/header/body placement, logout, redaction, and cleanup;
- Bar/Box exact identity and credential-memory isolation;
- bounded session invalidation and no fallback from generic `success: 0`;
- modern read-only action.cgi compatibility while legacy mutations remain on the legacy path;
- Bar meter modern auth with unchanged normalization and Box meter source preservation;
- `isSleep` and modern `callState` mappings, including unsupported/missing values;
- removal of first-HD-AI product authority;
- codec-local time success and explicit system fallback;
- structured built-in/version/unavailable camera/microphone presentation;
- GUI row visibility, rebuild/currentness, and no stale callback updates;
- no automatic Bar/Box detection introduced.

## Archive applicability

This change uses `MODIFIED Requirements` against existing root capabilities. Independent validation therefore must perform the repository-required disposable archive-applicability check from the exact validated remote feature HEAD before `READY FOR ARCHIVE`.
