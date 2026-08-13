# Change: cloudlink-310-runtime-session-corrections

## Why

Read-only live research against a real CloudLink Bar 310 disproved a protocol assumption that is currently normative in the archived `cloudlink-live-microphone-metering` contract. The Bar meter endpoint does not yield usable data through the current legacy Basic/action.cgi session. The vendor WebUI instead establishes a modern authenticated context with `POST /v1/login/session`, then `POST /v1/login/account`, retains the returned `data.acCSRFToken` in memory, and transmits it as `X-Access-Token`. The same modern session successfully served the Bar meter, call history, codec-local system time, login/status state, and the reviewed read-only action.cgi version/MAC/mailbox requests.

The current polling model also contains assumptions contradicted by the same read-only evidence. It chooses the first `HD-AI` microphone record even when a later HD-AI group is the connected one; it reads sleep through a legacy endpoint even though the vendor state response exposes confirmed `state.isSleep`; and the current legacy call-state key/enum does not match modern `state.callState`. The call-history implementation also falls back to computer-local time even though the device exposes a reliable local calendar clock.

CloudLink Box 310 is already an approved exact application model in the same shared CloudLink 310 protocol lifecycle. This change applies the corrected common read-session and read-only diagnostic behavior to both exact models while preserving their separate identities and credential/profile memory. Model resolution itself is unchanged: if inventory cannot assign an exact model, the existing fallback dialog remains the authority for an explicit operator choice.

## What Changes

- Define a modern CloudLink 310 read subcontext established with `POST /v1/login/session` followed by `POST /v1/login/account`, using the already application-selected credential and an in-memory access token.
- Require reviewed modern read requests to use the established cookies/session plus `X-Access-Token`; reviewed read-only action.cgi requests also carry the same modern token as `acCSRFToken` in the JSON body.
- Keep all existing state-changing CloudLink operations on the already approved legacy control path. This change does not claim modern-session mutation compatibility.
- Treat the modern read context and legacy control context as internal resources of one exact model/IP/credential handler generation; neither context may select or iterate credentials.
- Correct Bar live metering to use the modern read context while retaining the existing `/v1/mediacontrol/mic/current-volume` payload normalizer unchanged.
- Preserve the Box live-meter source exactly as `POST action.cgi?ActionID=WEB_GetCurrentAudioParam` and preserve its existing closed microphone field set and normalization.
- Use modern `GET /v1/login/status` evidence for normalized sleep and call state. Confirmed sleep is `isSleep == 1 -> On` and `isSleep == 0 -> Off`; modern call state is `0 No Call`, `1 Calling`, `2 Connected`, `3 Disconnected`.
- Stop treating the first `HD-AI` record, `state.mic`, or an unproved `gainVolume` as authoritative physical microphone connection/gain evidence. Do not infer camera connection/state from unproved `state.camera`.
- Use reliable `GET /v1/om/config/systemtime` device-local calendar time as the CloudLink call-history `reference_now`; preserve the existing explicit computer-local fallback warning only when device time is unavailable.
- Normalize structured camera/microphone version evidence for presentation. A structurally empty camera version renders `Встроенная камера`; a structurally empty microphone version renders `Встроенный микрофон`; usable version evidence renders the real version; missing/malformed evidence remains unavailable.
- Add visible CloudLink rows for `Режим сна`, `Версия камеры`, and `Версия микрофона` without making the GUI a protocol parser.
- Preserve typed failure, bounded same-credential recovery, secret redaction, background network execution, stale-operation rejection, and exact Bar/Box identity isolation.

## Impact

Affected specifications:

- `cloudlink-live-microphone-metering`
- `device-diagnostics-and-control`
- `request-lifecycle-and-recovery`

The existing `codec-call-log-usage-statistics` requirement that prefers reliable codec-local time remains semantically correct; implementation must be brought into compliance rather than weakening that requirement.

Expected implementation areas include:

- `handlers/huawei/bar310.py`
- `core/workers/codec_polling.py`
- `core/parser.py`
- CloudLink interactive/session composition code
- `gui/screens/codec_screen.py`
- focused CloudLink meter/status/call-history/session tests

Out of scope:

- automatic network probing or automatic Bar-versus-Box model detection;
- changing the Box meter source;
- migrating Wake, presentation mutation, mute, gain, volume, SIP mutation, or another state-changing operation to the modern session;
- inventing camera-state semantics from `state.camera`;
- inventing microphone physical-connection or gain semantics from `state.mic`, `MIC1`, `HD-AI`, `plugStatus`, or `gainVolume` beyond evidence explicitly approved later;
- changing credential candidate ownership/order or sharing credential/profile success between Bar and Box;
- Graphify artifacts or workflow.
