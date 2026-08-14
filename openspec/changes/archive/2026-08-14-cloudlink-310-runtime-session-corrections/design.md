# Design: CloudLink 310 runtime session corrections

## Context

`CloudLink Bar 310` and `CloudLink Box 310` remain distinct exact application models served by the shared `CloudLinkBar310Handler`. Credential selection and fallback remain application/composition-owned.

Read-only Bar research proved a modern WebUI read session established by `/v1/login/session` followed by `/v1/login/account`, with the returned in-memory session token transmitted as `X-Access-Token`. The same Bar session successfully served the Bar meter, call history, codec-local time, general state, and exactly these read-only action.cgi operations: version, MAC, and mailbox.

Modern compatibility was not proved for legacy audio, line/SIP, presentation, camera, or the Box-specific meter `WEB_GetCurrentAudioParam`. The project owner confirmed that common proven read behavior applies to Box where applicable, while the Box meter remains an explicit legacy-context exception.

## Goals

- Correct the CloudLink modern read-session contract without broadening unproved endpoints.
- Keep one application-selected credential and exact Bar/Box identity.
- Preserve legacy-compatible reads and mutations where modern compatibility is unproved.
- Correct proved sleep, call-state, device-time, version, and built-in presentation semantics.
- Remove first-HD-AI/gain assumptions rather than replace them with guesses.

## Non-goals

- automatic Bar/Box network detection;
- modernizing unproved reads or state-changing operations;
- deriving camera state from `state.camera`;
- deriving microphone connection/gain from `/mic/devices`;
- migrating the Box meter to modern authentication;
- handler-owned credential iteration.

## Session architecture

One exact model/IP/credential/generation owns one handler generation with two internal resources:

```text
modern read subcontext
legacy compatibility/control subcontext
```

Both use the same application-assigned credential. Superseding model/IP/credential/generation invalidates both. Handler and worker never choose another credential or model.

The modern subcontext is authoritative only for the explicitly approved modern read set. The legacy subcontext remains authoritative for all other existing read-only action.cgi operations and supported non-gain mutations.

## Exact modern read set

New modern authorization is closed to:

```text
WEB_GetVersionInfoAPI
WEB_GetSystemMacAddrAPI
WEB_GetMailboxDataAPI
GET /v1/login/status
GET /v1/meeting/calls/history
GET /v1/om/config/systemtime
GET /v1/mediacontrol/mic/current-volume   # Bar meter
```

`GET /v1/mediacontrol/mic/devices` may be used only as internal/research data in this change and has no new product gain/connection authority.

The following remain legacy-compatible:

```text
WEB_InitAudioCtrlParamsAPI
WEB_GetLineStateInfoAPI
WEB_IsSendAuxStreamAPI
WEB_GetCurCtrlCamSrcAPI
WEB_GetCurrentAudioParam                  # Box meter
other unverified action.cgi reads
```

## Meter ownership

Bar meter:

```text
GET /v1/mediacontrol/mic/current-volume
-> modern read subcontext
```

Its existing max-valid-`curVolume` normalizer remains unchanged, including valid zero and device ID 18.

Box meter:

```text
WEB_GetCurrentAudioParam
-> existing legacy compatibility subcontext
```

Its approved closed Box field set remains unchanged. Modern version/MAC/mailbox compatibility does not authorize modern routing for this endpoint.

## Preserved legacy normalization

This change preserves unrelated approved semantics while changing session ownership.

MAC precedence remains:

```text
system_wanMAC_addr
-> fallback system_lanMAC_addr
```

SIP precedence remains:

```text
line-state valid sip_status -> authoritative
otherwise mailbox state.sip 1/0 -> fallback On/Off
```

Mailbox never overwrites valid line-state SIP evidence.

Legacy camera mapping remains:

```text
localInMainSource == 255 -> On
localInMainSource == 0   -> Off
```

`state.camera` is not a replacement.

Presentation remains legacy-compatible and preserves:

```text
isSendAux == auxOpen  -> Start
isSendAux == auxClose -> Stop
```

Ordinary status and interactive presentation readback use the same mapping; malformed/unavailable evidence remains unavailable.

## Modern state ownership

`GET /v1/login/status` owns only proved canonical fields:

```text
callState 0 -> No Call
callState 1 -> Calling
callState 2 -> Connected
callState 3 -> Disconnected
isSleep 1 -> On
isSleep 0 -> Off
```

Accepted modern `isSleep` is canonical for both ordinary status and interactive sleep readback. Existing Wake remains a legacy mutation. The legacy lowercase call-state mapper must not parse modern `callState`.

## Peripheral versions

`cameraVersion` and `micVersion` normalize independently:

```text
absent/non-list -> unavailable
[] -> built-in
non-empty list -> every entry must provide a non-empty string version
                  malformed sibling makes the whole observation unavailable
                  strip, source-order deduplicate, join with "; "
```

GUI renders exact empty-list fallbacks:

```text
Встроенная камера
Встроенный микрофон
```

Vendor WebUI `--` is not protocol evidence. Version/type does not imply camera activity, microphone connection, mute, gain, or signal.

## Microphone gain

First-HD-AI, first-plugged, fixed IDs, `MIC1`, `plugStatus`, `gainVolume`, `state.mic`, and list order are not user-visible connection/gain authority.

CloudLink microphone-gain mutation is disabled before network I/O for Bar and Box until a later approved target/mutation/readback contract exists. The independent live meter remains enabled.

## Call-history time

CloudLink call history obtains codec-local calendar time from `/v1/om/config/systemtime` through the modern read context and uses it as device `reference_now`. Computer-local time remains an explicit fallback only when device-local time is unavailable after allowed bounded recovery. No timezone offset is invented.

## Failure and security boundary

Established-session HTTP 401/403 remains typed session invalidation with bounded same-credential recovery. Generic HTTP-200 `success: 0`, arbitrary text, or unapproved error/code fields do not authorize credential fallback or model switching.

Modern session artifacts remain memory-only and secret-free in logs, dialogs, public errors, OpenSpec evidence, and tests. Cleanup is best-effort and local resource release remains mandatory.

## GUI boundary

The codec screen adds visible rows:

```text
Режим сна
Версия камеры
Версия микрофона
```

The GUI renders canonical values only, performs no device I/O, does not choose credentials/model, and remains protected by existing generation/currentness rules. No automatic Bar/Box detector is added.

## Regression strategy

Implementation must cover:

- modern login/session lifecycle, secret redaction, 401/403 bounded recovery, and conservative `success:0` handling;
- exact modern allowlist and legacy routing for audio/line/presentation/camera plus Box meter;
- MAC WAN→LAN fallback, line-primary/mailbox SIP fallback, legacy camera 255/0, and presentation ordinary/interactive parity;
- Bar meter modern context and Box meter legacy context;
- modern sleep/call mappings and modern sleep authority for interactive readback while Wake remains legacy mutation;
- deterministic peripheral version normalization and built-in labels;
- removal of first-HD-AI/gain authority and disabled gain mutation with zero device mutation I/O;
- codec-local time and explicit fallback;
- exact Bar/Box identity, GUI currentness, and no automatic model detection.

## Archive applicability

This change uses `MODIFIED Requirements`; independent validation must perform the repository-required disposable archive-applicability check on the exact validated remote feature HEAD before `READY FOR ARCHIVE`.
