# Change: cloudlink-310-runtime-session-corrections

## Why

Read-only live research against a real CloudLink Bar 310 disproved a protocol assumption that is currently normative in the archived `cloudlink-live-microphone-metering` contract. The Bar meter endpoint does not yield usable data through the current legacy Basic/action.cgi session. The vendor WebUI instead establishes a modern authenticated context with `POST /v1/login/session`, then `POST /v1/login/account`, retains the returned `data.acCSRFToken` in memory, and transmits it as `X-Access-Token`. The same modern session successfully served the Bar meter, call history, codec-local system time, login/status state, and the exact read-only action.cgi version/MAC/mailbox requests verified during research.

The current polling model also contains assumptions contradicted by the same evidence. It chooses the first `HD-AI` microphone record even when a later HD-AI group is connected; it reads sleep through a legacy endpoint even though modern state exposes confirmed `state.isSleep`; and the legacy call-state key/enum does not match modern `state.callState`. The call-history implementation also falls back to computer-local time even though the device exposes a reliable local calendar clock.

CloudLink Box 310 is already an approved exact application model in the same shared CloudLink 310 protocol lifecycle. The project owner explicitly confirmed that the corrected common read behavior shall apply to Box 310 as well, while preserving the Box-specific live-meter source and preserving existing mutation paths unless this change explicitly disables them.

## What Changes

- Define one application-selected CloudLink handler generation that may own a modern read subcontext plus a legacy compatibility/control subcontext.
- Establish the modern read subcontext with `POST /v1/login/session` followed by `POST /v1/login/account`, with in-memory cookies/token and `X-Access-Token`.
- Limit normative modern action.cgi compatibility to the exact live-verified reads: `WEB_GetVersionInfoAPI`, `WEB_GetSystemMacAddrAPI`, and `WEB_GetMailboxDataAPI`. Keep existing audio, line/SIP, presentation, camera, and other unverified read-only action.cgi operations on the legacy compatibility path unless a later approved change proves modern compatibility.
- Keep existing supported state-changing action.cgi operations on the legacy compatibility/control path; do not infer mutation compatibility from read-only evidence.
- Explicitly disable CloudLink Bar/Box microphone-gain mutation in this change. The current `/v1/mediacontrol/mic/devices` PUT/POST target selection, fixed device fallback, and first-HD-AI readback are not sufficiently authoritative for safe mutation/reconciliation.
- Correct Bar live metering to use the modern read context while leaving the existing `/v1/mediacontrol/mic/current-volume` normalizer unchanged.
- Preserve Box live metering exactly as `POST action.cgi?ActionID=WEB_GetCurrentAudioParam` with the existing closed Box field set.
- Use modern `GET /v1/login/status` for proved sleep/call semantics only: `isSleep 1/0` and case-sensitive `callState 0/1/2/3`.
- Remove first-HD-AI/list-order/`gainVolume` authority for user-visible microphone connection/gain.
- Use `GET /v1/om/config/systemtime` as CloudLink codec-local `reference_now` when available, preserving the existing explicit computer-time fallback only on failure/unavailability.
- Normalize `cameraVersion` and `micVersion` deterministically as vendor lists: empty list means built-in; a non-empty list must contain only Mapping entries with exact non-empty string `version`; `name` is ignored for presentation; distinct normalized versions are preserved in source order and joined with `; `; any malformed non-empty entry makes that peripheral evidence unavailable.
- Render structured-empty versions exactly as `Встроенная камера` / `Встроенный микрофон`; never parse vendor WebUI `--` as protocol evidence.
- Add visible `Режим сна`, `Версия камеры`, and `Версия микрофона` rows while preserving GUI rendering-only responsibility and stale-context protection.
- Preserve application-owned credential selection/fallback, exact Bar/Box identity isolation, typed failures, bounded recovery, background I/O, and secret redaction.

## Impact

Affected specifications:

- `cloudlink-live-microphone-metering`
- `device-diagnostics-and-control`
- `request-lifecycle-and-recovery`

The existing `codec-call-log-usage-statistics` device-time semantic contract remains correct; implementation must be brought into compliance rather than weakening that requirement.

Expected implementation areas include:

- `handlers/huawei/bar310.py`
- `core/workers/codec_polling.py`
- `core/parser.py`
- CloudLink interactive/session composition code
- `gui/screens/codec_screen.py`
- focused CloudLink meter/status/call-history/session tests

Out of scope:

- automatic Bar-versus-Box network detection;
- changing the Box meter source;
- proving modern-session compatibility for unverified audio/line/presentation/camera reads;
- enabling CloudLink microphone-gain mutation before an authoritative target/readback contract exists;
- inventing camera-state semantics from `state.camera`;
- inventing microphone connection/gain semantics from `state.mic`, `MIC1`, `HD-AI`, `plugStatus`, `gainVolume`, or device-list order;
- changing credential ownership/order or sharing success memory between Bar and Box;
- Graphify artifacts or workflow.
