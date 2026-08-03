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

The connection and request layers already produce structured failures such as `AuthenticationError`, `SessionInvalidError`, `ConnectionError`, `CommandError`, `ProtocolError`, and `ParseError`. The defect is above that classification boundary:

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
2. Preserve typed authentication, session, transport, command, protocol, and parser failures for existing application-owned policy.
3. Preserve useful already collected data when one optional status field is unavailable.
4. Define an exact minimum usable core result so an empty, defaulted, core-less, or metadata-only payload cannot be emitted as success.
5. Define closed endpoint ownership and precedence for every canonical optional field.
6. Normalize presentation and sleep from actual structured device responses rather than defaults.
7. Keep unavailable data distinct from observed negative or zero state.
8. Preserve cleanup, background execution, stale-result suppression, and credential ownership boundaries.
9. Make the behavior testable without a real Bar 310.

## Non-goals

- Do not change credential candidate ordering, fallback authority, or successful credential-index memory.
- Do not add handler-owned credential iteration or reconnect loops.
- Do not change the supported Bar 310 connection profile or login handshake.
- Do not add general transport retry beyond existing approved recovery policy.
- Do not redesign `CodecScreen` or add a new user-visible warning panel.
- Do not change interactive serialization, operation identifiers, or stale callback acceptance.
- Do not change TE20, TE40, Polycom, PDU, Matrix, audio-DSP, inventory, or Graphify behavior.
- Do not use string matching on `auth`, `401`, or `403` as retry authority.
- Do not add alternative Bar 310 software-version keys without a later approved OpenSpec change.

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

## Decision 2: The required core gate is exact

A successful `get_version` observation requires all of the following:

```text
outer response is a Mapping
outer response["success"] == 1
outer response["data"] is a Mapping
"softVersion" exists in data
data["softVersion"] is a string
version = data["softVersion"].strip()
version is non-empty
version.casefold() != "unknown"
```

`softVersion` is the only approved software-version source key in this change. The handler SHALL NOT fall back to another key, `Unknown`, `N/A`, an empty string, the canonical model name, or another manufactured value. A later device-firmware discovery that requires another source key needs a later approved OpenSpec change with explicit priority.

After the exact core gate succeeds, the canonical handler fields are exactly:

```text
model   == "Huawei CloudLink Bar 310"
version == data["softVersion"].strip()
```

The exact canonical model string is a handler/application model identity, not text copied from the device response. It SHALL NOT use another spelling such as `CloudLink Bar 310`, `Huawei Bar 310`, or a response-provided free-form label.

The same successful version response may add these optional fields only when their values are actually observed:

```text
serial_number <- data["lisence"]
mic_version   <- data["micVersion"]
```

Missing optional version subfields do not invalidate the core response and do not receive `N/A` defaults.

Failure of the required core request is terminal for the refresh:

```text
HTTP/session/transport failure -> preserve its structured exception
success != 1                   -> CommandError
missing/non-Mapping data       -> ProtocolError
missing softVersion            -> ProtocolError
None or non-string softVersion -> ProtocolError
empty/whitespace softVersion   -> ProtocolError
softVersion == Unknown         -> ProtocolError
```

The handler SHALL NOT convert any of these outcomes to an empty mapping.

## Decision 3: Endpoint ownership and precedence are closed

The ordinary polling result uses this exact ownership map:

| Source endpoint | Canonical fields owned | Required precedence and observation rules |
| --- | --- | --- |
| `get_version` | required `model`, required `version`; optional `serial_number`, `mic_version` | The exact core gate in Decision 2 is the only authority for `model` and `version`. |
| `get_mac` | `mac_address` | Use the first non-empty observed value in this order: `system_wanMAC_addr`, then `system_lanMAC_addr`. If neither is observed, omit `mac_address`. |
| `get_audio_status` | `mic_mute`, `speaker_mute`, `speaker_volume` | Preserve observed `speakerValue == 0`. Missing or malformed individual observations are not replaced with zero or an On/Off default. |
| `get_line_state` | `uptime`, `sip_server`, `sip_number`, primary `sip_status` | A valid line-state `sip_status` is authoritative over call-state SIP evidence for the same refresh. Missing line SIP evidence leaves `sip_status` unowned until the call fallback rule below is evaluated. |
| `get_call_status` | `call_status`; fallback `sip_status` only | `state.callstate` owns `call_status`. `state.sip` may populate `sip_status` only when `get_line_state` produced no valid `sip_status`. It never overwrites a line-state observation. On conflict, line-state wins and a safe diagnostic may record the conflict. |
| `get_presentation` | `presentation` | Use the shared exact `isSendAux` normalizer in Decision 5. |
| `get_sleep_mode` | `sleep_mode` | Use the shared exact `isSystemSleep` normalizer in Decision 5. |
| `get_camera_status` | `camera_status` | `localInMainSource == 255` means `On`; `localInMainSource == 0` means `Off`; missing or another value is an endpoint-local protocol failure. |
| `GET /v1/mediacontrol/mic/devices` | `mic_connection_status`, `mic_volume` | Apply the exact HD-AI observation rules below. No other endpoint may manufacture these fields. |

For SIP precedence, valid call fallback values are exactly:

```text
state.sip == 1 -> sip_status = On
state.sip == 0 -> sip_status = Off
```

A missing or unsupported `state.sip` value does not create a fallback. When both line and call observations exist, they may agree or conflict, but call evidence never overwrites line evidence.

The HD-AI endpoint rules are exactly:

1. The response must be successful and its decoded `data` must be a Mapping.
2. `data["deviceList"]` must be a list; otherwise the endpoint has a local `ProtocolError` and both microphone fields are omitted.
3. Keep only Mapping entries whose `groupName == "HD-AI"`.
4. Preserve source list order and use the first matching HD-AI entry as the status observation.
5. A successfully observed empty filtered list means no HD-AI microphone is connected:

```text
mic_connection_status = "Микрофон не подключён"
mic_volume is omitted
```

6. For the selected entry:

```text
str(plugStatus) == "0"
    -> mic_connection_status = "Микрофон не подключён"
    -> mic_volume omitted

str(plugStatus) == "1"
    -> mic_connection_status = "Подключён"
    -> mic_volume = observed gainVolume, including numeric zero

missing/unsupported plugStatus
    -> endpoint-local ProtocolError
    -> both fields omitted
```

7. A connected observation requires `gainVolume` to be present and not `None`; numeric zero is valid. Missing connected gain is an endpoint-local `ProtocolError`, not a disconnected or zero observation.

An optional endpoint owns only the fields in this table. Failure or absence of one endpoint cannot delete fields owned by another endpoint. The parser SHALL NOT add an owned field that was absent from the canonical handler mapping.

## Decision 4: Optional endpoint failures are local unless the session or transport failed

After the required core gate succeeds, each optional endpoint is evaluated independently.

Endpoint-local outcomes include:

- response `success != 1`;
- malformed or unsupported optional endpoint data;
- endpoint-specific `CommandError`;
- endpoint-specific `ProtocolError`.

An endpoint-local outcome omits only the canonical fields owned by that endpoint under Decision 3. It may produce a safe redacted terminal-log message, but it does not erase fields already collected and does not authorize credential fallback.

The following remain terminal regardless of which endpoint was active:

- `AuthenticationError`;
- `SessionInvalidError`;
- `ConnectionError`;
- cancellation or a stale-operation decision made by the owning lifecycle boundary.

An established-session HTTP 401 or 403 therefore escapes as `SessionInvalidError` so the existing application-owned same-credential recovery policy can run. A transport timeout while reading an optional field escapes as `ConnectionError`; it is not downgraded to partial success because the validity of the established session and remaining reads is no longer authoritative.

Unexpected exceptions also SHALL NOT be converted to `{}`. They proceed through the worker error path and remain non-authoritative for credential advancement unless already classified by the approved structured policy.

## Decision 5: Partial status contains observations, not guessed states

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

camera endpoint unavailable
    -> omit camera_status
    -> parser does not publish Статус камеры

camera endpoint reports localInMainSource == 0
    -> publish camera_status = Off
    -> parser publishes Статус камеры = Не подключена

HD-AI endpoint unavailable or malformed
    -> omit mic_connection_status and mic_volume

successful HD-AI endpoint has no HD-AI entries
    -> publish observed Микрофон не подключён
    -> omit mic_volume

audio endpoint reports speakerValue = 0
    -> publish speaker_volume = 0

connected HD-AI microphone reports gainVolume = 0
    -> publish mic_volume = 0
```

Zero, false, muted, idle, stopped, disconnected, and sleeping values are valid only when derived from a successful structured response. The parser and GUI may display an existing neutral unavailable representation for omitted fields, but omission must not be converted into an observed negative state.

The public result does not rely on dynamic keys such as `get_presentation_isSendAux` as parser authority. Endpoint-specific raw data may be retained locally for redacted diagnostics if useful, but canonical parsing is performed once at the handler boundary.

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

## Decision 6: Parser output preserves the exact core contract

`HuaweiBar310DataParser.parse_raw_data()` SHALL accept only a Mapping that already passed or independently satisfies the exact handler core contract.

Its required canonical display fields are exactly:

```text
parsed["Модель"] == "Huawei CloudLink Bar 310"
parsed["Версия ПО"] is a non-empty string derived from raw_data["version"]
```

The parser SHALL NOT supply a model or version default. It SHALL reject a missing or different model, missing/non-string/empty version, `Unknown`, or a version that becomes empty after the existing display cleanup. Parser contract rejection SHALL raise `ParseError`.

Optional display fields are emitted only when their canonical handler fields are present. In particular:

- `Статус камеры` is omitted when `camera_status` is absent; it is not unconditionally `Подключена`;
- `SIP регистрация` is omitted when `sip_status` is absent;
- `Статус звонка` is omitted when `call_status` is absent;
- `Режим презентации` is omitted when `presentation` is absent;
- `Режим сна` is omitted when `sleep_mode` is absent;
- microphone status and volume are omitted unless the HD-AI endpoint produced their canonical fields;
- valid zero values remain present.

## Decision 7: Handler success and worker success are separate typed boundaries

On successful collection the handler returns a Mapping containing exactly usable core evidence:

```text
model == "Huawei CloudLink Bar 310"
version is the validated stripped softVersion
```

Optional canonical fields are additive.

The worker SHALL defensively reject these raw payloads by raising `ProtocolError`:

- an empty Mapping;
- a non-Mapping payload;
- a payload without exact `model == "Huawei CloudLink Bar 310"`;
- a payload without a non-empty string `version`;
- a payload whose version is `Unknown`;
- a payload containing only technical metadata.

The parser SHALL raise `ParseError` when its output lacks either exact required display field from Decision 6. `ProtocolError` and `ParseError` are both classified by the existing `classify_codec_failure()` boundary as:

```text
protocol_error
```

The worker SHALL call the existing typed error path so every unusable raw or parsed payload produces exact machine category `protocol_error`. It SHALL NOT pass a `ValueError`, generic exception, or explicit `connection_error` category for these contract failures.

Technical metadata does not satisfy the gate. The worker adds:

```text
ip_address
connection_profile
```

only after the raw payload and parsed canonical result pass validation.

An unusable payload follows the exact error lifecycle:

```text
raise ProtocolError or ParseError
no result signal
error signal category == protocol_error
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

## Decision 8: Cleanup and secret boundaries remain mandatory

The worker disconnects the handler in `finally` for success, partial success, terminal typed failure, raw-payload `ProtocolError`, parser `ParseError`, and unexpected exception.

Logs and errors must continue through existing redaction helpers. Optional endpoint diagnostics may name the safe command and failure class but must not include username, password, CSRF token, cookie, full response body, or request payload.

This change does not move network I/O into the Qt GUI thread and does not add widget reads to the worker or handler.

## Implementation shape

A preferred implementation shape is:

```text
CloudLinkBar310Handler.get_status
    -> collect required core response
    -> validate exact softVersion gate
    -> create exact model/version fields
    -> for each explicit optional collector
         preserve terminal typed failures
         localize endpoint command/protocol failure
         merge only endpoint-owned observed fields
    -> return non-empty canonical Mapping

HuaweiBar310DataParser
    -> validate exact model/version core evidence
    -> map required Модель and Версия ПО without defaults
    -> map only present optional fields
    -> preserve valid zero/false values

HuaweiBar310Worker
    -> reject unusable raw payload with ProtocolError
    -> parse and reject unusable canonical display result with ParseError
    -> add technical metadata
    -> emit result
```

Focused private collector/helper functions are encouraged. Concrete private names are not architecture contracts.

## Regression coverage

A new synthetic module `tests/test_bar310_status_polling.py` SHALL cover at least:

- the exact required and optional plan;
- proof that configuration and mutation endpoints are not called;
- exact required core source key `softVersion` and exact handler model string;
- missing `softVersion`, `None`, non-string, empty, whitespace-only, and case-insensitive `Unknown` values raising `ProtocolError`;
- proof that another version key or a manufactured default cannot satisfy the core gate;
- exact parser fields `Модель` and `Версия ПО`, no parser defaults, and `ParseError` for missing/invalid core display evidence;
- successful core plus failing presentation still returns core and other observed fields;
- successful core plus optional `success == 0` omits only that endpoint fields;
- successful core plus optional malformed data omits only that endpoint fields;
- established-session 401/403 escapes as `SessionInvalidError`;
- optional transport timeout escapes as `ConnectionError`;
- required core unsuccessful response raises `CommandError`;
- no broad exception path returns `{}`;
- raw empty/non-Mapping/core-less/metadata-only payload raises `ProtocolError`, emits `protocol_error`, and emits no result;
- invalid parser result raises `ParseError`, emits `protocol_error`, and emits no result;
- endpoint ownership: one endpoint failure cannot remove fields owned by another endpoint;
- line-state SIP primary behavior, call-state SIP fallback when line evidence is absent, agreement, and line-wins conflict behavior;
- successful empty HD-AI list;
- malformed `deviceList`;
- HD-AI `plugStatus == 0`;
- connected HD-AI microphone with `gainVolume == 0`;
- unavailable camera endpoint versus observed `localInMainSource == 0` and `255`;
- parser omission of unavailable camera and microphone fields;
- unavailable presentation/sleep/call/audio fields omitted rather than defaulted;
- valid zero/false values remain present;
- `auxOpen`, `auxClose`, `sleep`, and `unsleep` canonical mappings;
- shared helper behavior in full polling and interactive readback;
- usable partial payload emits a result;
- handler disconnect and `finished` emission on every terminal path;
- redaction of credentials, tokens, cookies, payloads, and response bodies.

The full offline test suite must prove no regression in other codec refresh, interactive recovery, credential memory, stale operation handling, and GUI rendering.

## Rollout

No data migration or configuration change is required. The implementation changes runtime polling behavior only. Real-device verification should confirm the exact software version, normal Bar 310 refresh, presentation active/inactive, sleep active/inactive, SIP/call precedence, camera connected/disconnected, HD-AI microphone connected/disconnected/zero gain, and a safely displayed unavailable optional field. Real-device access does not replace synthetic regression tests or independent validation.
