# Design: Bar 310 resilient status polling

## Context

The current CloudLink Bar 310 refresh path is:

```text
application-owned credential attempt
    -> HuaweiBar310Worker
    -> CloudLinkBar310Handler.connect()
    -> CloudLinkBar310Handler.get_status()
    -> HuaweiBar310DataParser
    -> worker result signal
    -> application acceptance and GUI rendering
```

The connection and request layers already produce structured failures such as `AuthenticationError`, `SessionInvalidError`, `ConnectionError`, `CommandError`, and `ProtocolError`. The defect is above that classification boundary:

```text
several successful status responses
    -> one later endpoint raises
    -> get_status catches Exception and returns {}
    -> parser returns {}
    -> worker adds technical metadata
    -> worker emits success result
```

The same method currently treats `command_map` as a polling registry. That map also contains configuration endpoints and is used by interactive commands, so membership in the map is not authority to execute an endpoint during ordinary refresh.

## Goals

1. Make an ordinary Bar 310 refresh execute only a closed reviewed read-only status plan.
2. Preserve typed authentication, session, and transport failures for existing application-owned recovery policy.
3. Preserve useful already collected data when one optional status field is unavailable.
4. Define an explicit minimum usable result so an empty or metadata-only payload cannot be emitted as success.
5. Normalize presentation and sleep from actual structured device responses rather than defaults.
6. Keep unavailable data distinct from observed negative or zero state.
7. Preserve cleanup, background execution, stale-result suppression, and credential ownership boundaries.
8. Make the behavior testable without a real Bar 310.

## Non-goals

- Do not change credential candidate ordering, fallback authority, or successful credential-index memory.
- Do not add handler-owned credential iteration or reconnect loops.
- Do not change the supported Bar 310 connection profile or login handshake.
- Do not add general transport retry beyond existing approved recovery policy.
- Do not redesign `CodecScreen` or add a new user-visible warning panel.
- Do not change interactive serialization, operation identifiers, or stale callback acceptance.
- Do not change TE20, TE40, Polycom, PDU, Matrix, audio-DSP, inventory, or Graphify behavior.
- Do not use string matching on `auth`, `401`, or `403` as retry authority.

## Decision 1: `command_map` is not the polling plan

Ordinary Bar 310 status refresh SHALL use an explicit plan independent of the complete command map.

The required core request is exactly:

```text
get_version -> WEB_GetVersionInfoAPI
```

The optional read-only enrichment requests are exactly:

```text
get_mac           -> WEB_GetSystemMacAddrAPI
get_audio_status  -> WEB_InitAudioCtrlParamsAPI
get_line_state    -> WEB_GetLineStateInfoAPI
get_call_status   -> WEB_GetMailboxDataAPI
get_presentation  -> WEB_IsSendAuxStreamAPI
get_sleep_mode    -> WEB_IsSystemSleepAPI
get_camera_status -> WEB_GetCurCtrlCamSrcAPI
HD-AI microphones -> GET /v1/mediacontrol/mic/devices
```

The following current configuration requests are excluded from refresh:

```text
get_config_default -> WEB_GetTermSpecsInfoAPI
get_config         -> WEB_GetCfgParamAPI
```

Every state-changing endpoint is also excluded. Adding an endpoint to `command_map` later SHALL NOT make it part of refresh. Adding or removing a polling endpoint requires review of the explicit plan and regression coverage.

## Decision 2: One required core identity gate

A successful refresh requires a successful `get_version` response with:

- outer response `success == 1`;
- object-shaped `data` after supported JSON decoding;
- a non-empty software version value;
- canonical model identity set only after that successful response.

The handler may use the supported canonical Bar 310 model constant when the response omits a model label, but it must not return model/version defaults without a successful core response.

Missing optional version subfields such as serial number or microphone firmware do not invalidate the core response. Those fields are omitted when not observed.

Failure of the required core request is terminal for the refresh:

```text
HTTP/session/transport failure -> preserve its structured exception
success != 1                   -> CommandError
missing/malformed core data    -> ProtocolError
```

The handler SHALL NOT convert any of these outcomes to an empty mapping.

## Decision 3: Optional endpoint failures are local unless the session or transport failed

After the required core gate succeeds, each optional endpoint is evaluated independently.

Endpoint-local outcomes include:

- response `success != 1`;
- malformed or unsupported optional endpoint data;
- endpoint-specific `CommandError`;
- endpoint-specific `ProtocolError`.

An endpoint-local outcome omits only the canonical fields owned by that endpoint. It may produce a safe redacted terminal-log message, but it does not erase fields already collected and does not authorize credential fallback.

The following remain terminal regardless of which endpoint was active:

- `AuthenticationError`;
- `SessionInvalidError`;
- `ConnectionError`;
- cancellation or a stale-operation decision made by the owning lifecycle boundary.

An established-session HTTP 401 or 403 therefore escapes as `SessionInvalidError` so the existing application-owned same-credential recovery policy can run. A transport timeout while reading an optional field escapes as `ConnectionError`; it is not downgraded to partial success because the validity of the established session and remaining reads is no longer authoritative.

Unexpected exceptions also SHALL NOT be converted to `{}`. They proceed through the worker error path and remain non-authoritative for credential advancement unless already classified by the approved structured policy.

## Decision 4: Partial status contains observations, not guessed states

The handler result contains canonical fields only when their source response was successfully observed and normalized.

Examples:

```text
presentation endpoint unavailable
    -> omit presentation
    -> do not publish Stop

sleep endpoint unavailable
    -> omit sleep_mode
    -> do not publish Off

call endpoint unavailable
    -> omit call_status
    -> do not publish No Call

audio endpoint reports speakerValue = 0
    -> publish speaker_volume = 0
```

Zero, false, muted, idle, stopped, and sleeping values are valid only when derived from a successful structured response. The parser and GUI may display an existing neutral unavailable representation for omitted fields, but omission must not be converted into an observed negative state.

The public result does not rely on dynamic keys such as `get_presentation_isSendAux` as parser authority. Endpoint-specific raw data may be retained locally for redacted diagnostics if useful, but canonical parsing is performed once at the handler boundary.

## Decision 5: Shared canonical normalizers prevent refresh/readback drift

Presentation normalization is exactly:

```text
isSendAux == auxOpen  -> Start
isSendAux == auxClose -> Stop
anything else         -> endpoint-local ProtocolError
```

Sleep normalization is exactly:

```text
isSystemSleep == sleep   -> On
isSystemSleep == unsleep -> Off
anything else            -> endpoint-local ProtocolError
```

The same pure normalization helpers SHALL be used by:

- ordinary `get_status()` polling;
- `get_presentation_status()` interactive readback;
- `get_sleep_mode()` interactive readback.

Interactive state-changing behavior remains unchanged: a presentation mutation performs one state-changing send, then may perform the existing authoritative readback. The new helpers do not authorize a repeated mutation.

Other canonical endpoint mappings, including call state, SIP registration, mute state, volume, uptime, MAC, and camera state, remain handler-owned and must preserve valid zero/false values.

## Decision 6: Handler success and worker success are separate defensive boundaries

On successful collection the handler returns a mapping containing at least:

```text
model
version
```

Those fields prove that the required core request passed. Optional canonical fields are additive.

The worker and parser SHALL defensively reject:

- an empty mapping;
- a non-mapping payload;
- a payload without usable core model/version evidence;
- a parser result without canonical display fields derived from the core evidence.

Technical metadata does not satisfy this gate. The worker adds:

```text
ip_address
connection_profile
```

only after the raw payload and parsed canonical result pass validation.

An unusable payload follows the error lifecycle:

```text
no result signal
classified or safe generic error signal
handler cleanup
finished signal
```

A usable partial payload follows the success lifecycle:

```text
canonical result signal
handler cleanup
completion lifecycle
```

The application remains the authority for stale-result acceptance and successful credential/profile persistence. Because no result is emitted for an unusable payload, that payload cannot become successful-operation evidence.

## Decision 7: Cleanup and secret boundaries remain mandatory

The worker disconnects the handler in `finally` for success, partial success, terminal typed failure, parser rejection, and unexpected exception.

Logs and errors must continue through existing redaction helpers. Optional endpoint diagnostics may name the safe command and failure class but must not include username, password, CSRF token, cookie, full response body, or request payload.

This change does not move network I/O into the Qt GUI thread and does not add widget reads to the worker or handler.

## Implementation shape

A preferred implementation shape is:

```text
CloudLinkBar310Handler.get_status
    -> collect required core response
    -> normalize core fields
    -> for each explicit optional collector
         preserve terminal typed failures
         localize endpoint command/protocol failure
         merge observed canonical fields
    -> return non-empty canonical mapping

HuaweiBar310DataParser
    -> validate mapping and core evidence
    -> map only present fields
    -> preserve valid zero/false values

HuaweiBar310Worker
    -> collect
    -> validate/parse
    -> add technical metadata
    -> emit result
```

Focused private collector/helper functions are encouraged. Concrete private names are not architecture contracts.

## Regression coverage

A new synthetic module `tests/test_bar310_status_polling.py` SHALL cover at least:

- the exact required and optional plan;
- proof that configuration endpoints are not called;
- successful core plus failing presentation still returns core and other observed fields;
- successful core plus optional `success == 0` omits only that endpoint fields;
- successful core plus optional malformed data omits only that endpoint fields;
- established-session 401/403 escapes as `SessionInvalidError`;
- optional transport timeout escapes as `ConnectionError`;
- required core unsuccessful response raises `CommandError`;
- required core malformed response raises `ProtocolError`;
- no broad exception path returns `{}`;
- unavailable presentation/sleep/call/audio fields are omitted rather than defaulted;
- valid zero/false values remain present;
- `auxOpen`, `auxClose`, `sleep`, and `unsleep` canonical mappings;
- shared helper behavior in full polling and interactive readback;
- empty, non-mapping, and core-less worker payloads emit error and no result;
- usable partial payload emits a result;
- handler disconnect and `finished` emission on every terminal path;
- redaction of credentials, tokens, cookies, payloads, and response bodies.

The full offline test suite must prove no regression in other codec refresh, interactive recovery, credential memory, stale operation handling, and GUI rendering.

## Rollout

No data migration or configuration change is required. The implementation changes runtime polling behavior only. Real-device verification should confirm a normal Bar 310 refresh, presentation active/inactive, sleep active/inactive, SIP/call status, and a safely displayed unavailable optional field, but real-device access does not replace synthetic regression tests or independent validation.
