# Change: cloudlink-310-runtime-session-corrections

## Why

Read-only live research against a real CloudLink Bar 310 disproved part of the archived CloudLink read-session contract. The Bar meter and several modern `/v1` reads require the vendor modern session/token context; the current legacy-only assumption leaves those operations unavailable.

The same research also disproved first-HD-AI/list-order microphone authority, proved modern sleep/call-state semantics and codec-local time, and showed that the existing call-history implementation should use device-local `reference_now` when available.

CloudLink Box 310 is already an exact supported model in the same shared handler family. Common proven read behavior applies to Box where applicable, but Box-specific protocol details remain explicit exceptions. In particular, its live meter remains `WEB_GetCurrentAudioParam` on the existing legacy compatibility subcontext because modern compatibility for that endpoint was not proved.

## What Changes

- Keep one application-selected credential and one exact Bar/Box handler generation with bounded modern-read and legacy-compatibility/control subcontexts.
- Establish the modern read subcontext through the proved vendor login flow and keep its session token in memory only.
- Limit newly approved modern action.cgi reads to `WEB_GetVersionInfoAPI`, `WEB_GetSystemMacAddrAPI`, and `WEB_GetMailboxDataAPI`.
- Keep unproved audio, line/SIP, presentation, camera, Box-meter, and other action.cgi reads on the legacy compatibility path.
- Keep existing supported non-gain mutations on the legacy control path; disable CloudLink microphone-gain mutation before device I/O until target/readback semantics are approved.
- Run Bar live metering through the modern read context while preserving its existing normalizer.
- Preserve Box live metering exactly as `WEB_GetCurrentAudioParam` with its existing closed field set and legacy compatibility context.
- Use modern `/v1/login/status` for proved `isSleep` and case-sensitive `callState` semantics.
- Preserve unrelated approved legacy normalization: MAC WAN→LAN fallback, line-state-primary/mailbox SIP fallback precedence, legacy camera `localInMainSource` 255/0 mapping, and presentation `auxOpen/auxClose` mapping with ordinary/interactive parity.
- Make modern `state.isSleep` canonical for both ordinary status and interactive sleep readback while leaving Wake on the legacy mutation path.
- Remove first-HD-AI/list-order/`gainVolume` authority for user-visible microphone connection/gain.
- Use `/v1/om/config/systemtime` as CloudLink codec-local `reference_now` when available, retaining explicit computer-time fallback only on failure/unavailability.
- Normalize `cameraVersion` and `micVersion` deterministically; structured empty lists render exactly `Встроенная камера` / `Встроенный микрофон`.
- Add visible `Режим сна`, `Версия камеры`, and `Версия микрофона` rows while preserving rendering-only GUI and stale-context rules.
- Preserve exact Bar/Box identity, application-owned credential fallback, typed failures, bounded recovery, background I/O, and secret redaction.

## Impact

Affected specifications:

- `cloudlink-live-microphone-metering`
- `device-diagnostics-and-control`
- `request-lifecycle-and-recovery`

The existing `codec-call-log-usage-statistics` device-time semantic contract remains valid; implementation must be brought into compliance rather than weakening it.

Expected implementation areas include the shared Huawei CloudLink handler, codec polling/parser path, interactive session composition, CodecScreen rendering, and focused session/status/meter/call-history tests.

Out of scope:

- automatic Bar-versus-Box network detection;
- modern migration of unproved action.cgi reads, including the Box meter;
- enabling CloudLink microphone-gain mutation before an authoritative target/readback contract exists;
- inventing camera-state semantics from `state.camera`;
- inventing microphone connection/gain semantics from `state.mic`, `MIC1`, HD-AI, `plugStatus`, `gainVolume`, or device-list order;
- changing credential ownership/order or sharing success memory between Bar and Box;
- Graphify artifacts or workflow.
