# request-lifecycle-and-recovery Specification

## ADDED Requirements

### Requirement: CloudLink Bar 310 polling uses a closed resilient status plan

An ordinary CloudLink Bar 310 status refresh SHALL execute an explicit reviewed read-only polling plan rather than iterate every entry in the handler command map.

The required core request SHALL be exactly `get_version`. The optional read-only enrichment requests SHALL be limited to MAC, audio, line/SIP, call, presentation, sleep, camera, and HD-AI microphone status. Configuration requests including `get_config_default` and `get_config`, every state-changing request, and future command-map-only entries SHALL NOT run during ordinary status refresh unless added to the reviewed polling plan by a later approved change.

After the required core request succeeds, an endpoint-specific optional `CommandError`, unsuccessful optional response, or optional payload `ProtocolError` SHALL omit only the fields owned by that endpoint and SHALL NOT erase already collected canonical status. The handler MAY emit a safe redacted diagnostic for the unavailable optional endpoint.

`AuthenticationError`, `SessionInvalidError`, and `ConnectionError` SHALL remain terminal typed failures from every phase of status collection. An established-session HTTP 401 or 403 SHALL therefore remain `SessionInvalidError`, and a transport failure during an optional read SHALL remain `ConnectionError`. Unexpected exceptions SHALL NOT be converted into an empty successful payload.

#### Scenario: Configuration endpoint exists in the command map

- **GIVEN** `get_config` or `get_config_default` remains available for another handler purpose
- **WHEN** ordinary Bar 310 status refresh runs
- **THEN** the refresh does not invoke that configuration endpoint
- **AND** command-map membership alone does not grant polling authority

#### Scenario: Optional presentation read is unavailable

- **GIVEN** the required version response and other status responses succeeded
- **WHEN** the optional presentation endpoint returns an endpoint-specific unsuccessful or malformed response
- **THEN** the handler preserves the already collected canonical fields
- **AND** it omits `presentation` from that refresh result
- **AND** it does not return an empty mapping
- **AND** it does not authorize credential fallback

#### Scenario: Established session is rejected during optional read

- **GIVEN** Bar 310 login completed and the required core response succeeded
- **WHEN** an optional established-session request returns HTTP 401 or 403
- **THEN** status collection raises `SessionInvalidError`
- **AND** the failure remains available to the application-owned same-credential recovery policy
- **AND** partial status is not emitted as successful evidence

#### Scenario: Optional read has a transport failure

- **WHEN** an optional Bar 310 request times out or loses transport
- **THEN** status collection raises `ConnectionError`
- **AND** the handler does not downgrade the transport failure to partial success

### Requirement: CloudLink Bar 310 required core evidence is exact

A successful `get_version` observation SHALL require all of the following:

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

`softVersion` SHALL be the only approved software-version source key. The handler SHALL NOT use another response key, `Unknown`, `N/A`, an empty value, a model constant, or another manufactured default as software-version evidence.

After the exact core gate succeeds, the handler result SHALL contain exactly:

```text
model == "Huawei CloudLink Bar 310"
version == data["softVersion"].strip()
```

The model string SHALL NOT be copied from a free-form device response or changed to another spelling. The same successful response MAY add `serial_number` from observed `data["lisence"]` and `mic_version` from observed `data["micVersion"]`; absence of those optional values SHALL NOT invalidate core success and SHALL NOT create `N/A` defaults.

An unsuccessful required core response SHALL raise `CommandError`. Missing/non-Mapping core data, a missing `softVersion`, `None`, a non-string value, an empty or whitespace-only string, or a case-insensitive `Unknown` value SHALL raise `ProtocolError`. No result mapping SHALL be returned as success for those outcomes.

#### Scenario: Required core response is successful

- **WHEN** `get_version.data["softVersion"]` is a non-empty string after `strip()` and is not `Unknown`
- **THEN** handler `model` is exactly `Huawei CloudLink Bar 310`
- **AND** handler `version` is exactly the stripped `softVersion`
- **AND** no response-provided model label or manufactured version default is used

#### Scenario: Required core response is unsuccessful

- **WHEN** the required version endpoint returns `success != 1`
- **THEN** status collection raises `CommandError`
- **AND** no result mapping is returned as success

#### Scenario: Required core version key is absent

- **WHEN** successful core data lacks exact key `softVersion`
- **THEN** status collection raises `ProtocolError`
- **AND** another version key does not satisfy the gate

#### Scenario: Required core version value is unusable

- **WHEN** `softVersion` is `None`, non-string, empty, whitespace-only, or case-insensitive `Unknown`
- **THEN** status collection raises `ProtocolError`
- **AND** canonical model/version defaults are not manufactured

### Requirement: CloudLink Bar 310 optional field ownership and precedence are closed

The canonical handler result SHALL use this exact endpoint ownership map:

| Endpoint | Canonical fields |
| --- | --- |
| `get_version` | required `model`, required `version`; optional `serial_number`, `mic_version` |
| `get_mac` | `mac_address` |
| `get_audio_status` | `mic_mute`, `speaker_mute`, `speaker_volume` |
| `get_line_state` | `uptime`, `sip_server`, `sip_number`, primary `sip_status` |
| `get_call_status` | `call_status`; fallback `sip_status` only when line-state produced no valid SIP observation |
| `get_presentation` | `presentation` |
| `get_sleep_mode` | `sleep_mode` |
| `get_camera_status` | `camera_status` |
| `GET /v1/mediacontrol/mic/devices` | `mic_connection_status`, `mic_volume` |

`get_mac` SHALL use the first non-empty observed value in this order: `system_wanMAC_addr`, then `system_lanMAC_addr`.

Line-state SIP evidence SHALL be authoritative for the refresh. Call-state `state.sip == 1` MAY populate `sip_status = On` and `state.sip == 0` MAY populate `sip_status = Off` only when line-state produced no valid `sip_status`. Call-state evidence SHALL NOT overwrite line-state evidence. On disagreement, line-state SHALL win.

Camera normalization SHALL map only `localInMainSource == 255` to `camera_status = On` and `localInMainSource == 0` to `camera_status = Off`. A missing or unsupported value SHALL be an endpoint-local protocol failure and `camera_status` SHALL be omitted.

For a successful HD-AI microphone response, decoded `data` SHALL be a Mapping and `data["deviceList"]` SHALL be a list. The handler SHALL keep Mapping entries whose `groupName == "HD-AI"`, preserve source list order, and use the first matching entry. A successfully observed empty filtered list SHALL produce `mic_connection_status = "Микрофон не подключён"` and SHALL omit `mic_volume`.

For the selected HD-AI entry:

```text
str(plugStatus) == "0"
    -> mic_connection_status = "Микрофон не подключён"
    -> mic_volume omitted

str(plugStatus) == "1"
    -> mic_connection_status = "Подключён"
    -> mic_volume = observed gainVolume, including numeric zero
```

Missing/unsupported `plugStatus`, malformed `deviceList`, or a connected entry with absent/`None` `gainVolume` SHALL be endpoint-local `ProtocolError` outcomes and both microphone fields SHALL be omitted. Endpoint unavailability SHALL NOT be converted into an observed disconnected microphone.

Failure or absence of one optional endpoint SHALL NOT delete or manufacture fields owned by another endpoint. The parser SHALL NOT add an endpoint-owned field that was absent from the canonical handler mapping.

#### Scenario: Line and call SIP observations agree

- **GIVEN** line-state produced a valid SIP observation
- **AND** call-state produced the same SIP observation
- **WHEN** the refresh result is composed
- **THEN** the line-state value remains canonical
- **AND** call-state does not overwrite it

#### Scenario: Line and call SIP observations conflict

- **GIVEN** line-state produced a valid SIP observation
- **AND** call-state produced the opposite observation
- **WHEN** the refresh result is composed
- **THEN** line-state wins
- **AND** call-state does not overwrite `sip_status`

#### Scenario: Call SIP fallback is used

- **GIVEN** line-state produced no valid SIP observation
- **AND** call-state reports `state.sip == 1` or `state.sip == 0`
- **WHEN** the refresh result is composed
- **THEN** call-state supplies the fallback `sip_status`

#### Scenario: Successful HD-AI list is empty

- **WHEN** the HD-AI endpoint succeeds with a valid empty `deviceList` or no `HD-AI` entries
- **THEN** `mic_connection_status` is `Микрофон не подключён`
- **AND** `mic_volume` is omitted
- **AND** this observed state remains distinguishable from endpoint unavailability

#### Scenario: HD-AI microphone is physically disconnected

- **WHEN** the selected HD-AI entry reports `plugStatus == 0`
- **THEN** `mic_connection_status` is `Микрофон не подключён`
- **AND** `mic_volume` is omitted

#### Scenario: Connected HD-AI microphone reports zero gain

- **WHEN** the selected HD-AI entry reports `plugStatus == 1` and `gainVolume == 0`
- **THEN** `mic_connection_status` is `Подключён`
- **AND** `mic_volume` remains present with value zero

#### Scenario: HD-AI list is malformed

- **WHEN** the HD-AI endpoint succeeds but `deviceList` is not a list
- **THEN** the endpoint has a local `ProtocolError`
- **AND** both microphone fields are omitted
- **AND** already collected fields remain available

#### Scenario: Camera endpoint is unavailable

- **WHEN** the camera endpoint is not successfully observed
- **THEN** `camera_status` is omitted
- **AND** the parser does not manufacture `Статус камеры = Подключена`

#### Scenario: Camera is observed disconnected

- **WHEN** a successful camera response reports `localInMainSource == 0`
- **THEN** canonical `camera_status` is `Off`
- **AND** parser display status is `Не подключена`

### Requirement: CloudLink Bar 310 normalization distinguishes unavailable from observed state

CloudLink Bar 310 canonical status fields SHALL be populated only from successful structured endpoint observations. An unavailable optional endpoint SHALL cause its canonical fields to be omitted rather than replaced with semantic defaults such as `Off`, `Stop`, `No Call`, `Подключена`, `Микрофон не подключён`, or zero.

A successful endpoint value that is legitimately zero, false, idle, stopped, muted, disconnected, or sleeping SHALL remain present and SHALL NOT be mistaken for missing data.

Presentation normalization SHALL map only `isSendAux == auxOpen` to `Start` and `isSendAux == auxClose` to `Stop`. Sleep normalization SHALL map only `isSystemSleep == sleep` to `On` and `isSystemSleep == unsleep` to `Off`. Unsupported or malformed values SHALL be endpoint-specific protocol failures rather than guessed states.

The same presentation and sleep normalization logic SHALL be used by ordinary full status refresh and interactive readback methods.

#### Scenario: Presentation endpoint is absent from a partial result

- **WHEN** the presentation endpoint was not successfully observed
- **THEN** canonical presentation is omitted
- **AND** the parser does not convert absence into `Stop`

#### Scenario: Presentation is observed inactive

- **WHEN** a successful structured presentation response reports `auxClose`
- **THEN** canonical presentation is `Stop`
- **AND** the value remains distinguishable from an unavailable endpoint

#### Scenario: Sleep endpoint reports active sleep

- **WHEN** a successful structured sleep response reports `sleep`
- **THEN** canonical sleep mode is `On`
- **AND** ordinary polling and interactive readback produce the same value

#### Scenario: Observed speaker volume is zero

- **WHEN** a successful audio response reports a valid speaker volume of zero
- **THEN** canonical speaker volume remains present with value zero
- **AND** zero is not treated as unavailable data

### Requirement: CloudLink Bar 310 parser and worker success require exact usable canonical status

`HuaweiBar310DataParser` SHALL reject raw data unless it is a Mapping with exact `model == "Huawei CloudLink Bar 310"` and a non-empty string `version` that is not `Unknown`.

The parser SHALL produce these exact required display fields without defaults:

```text
"Модель" == "Huawei CloudLink Bar 310"
"Версия ПО" is non-empty and derived from raw_data["version"]
```

A missing/different model, missing/non-string/empty version, `Unknown`, or a version that becomes empty after display cleanup SHALL raise `ParseError`. Optional display fields SHALL be emitted only when their canonical handler fields are present. In particular, `Статус камеры`, SIP, call, presentation, sleep, microphone status, and microphone volume SHALL NOT be manufactured from absence.

`HuaweiBar310Worker` SHALL defensively raise `ProtocolError` for an empty Mapping, non-Mapping payload, payload without exact usable core model/version evidence, or metadata-only payload. It SHALL add technical `ip_address` and `connection_profile` fields only after raw and parsed payload validation succeeds.

Raw-payload `ProtocolError` and parser `ParseError` SHALL pass through the existing typed codec failure classifier and SHALL emit exact machine category:

```text
protocol_error
```

The worker SHALL NOT represent these contract failures with `ValueError`, a generic exception, an explicit `connection_error`, or another transport category.

For an unusable payload, the worker SHALL emit no result signal, SHALL emit `protocol_error`, SHALL disconnect any created handler, and SHALL emit completion. For a usable partial payload, the worker SHALL emit the canonical result and preserve the existing cleanup/completion lifecycle.

The application/composition layer SHALL remain the authority for stale-result acceptance and successful credential-index/profile persistence. An unusable Bar 310 payload SHALL NOT become successful-operation evidence for that policy.

#### Scenario: Handler returns an empty mapping

- **WHEN** `handler.get_status()` returns `{}`
- **THEN** the worker raises `ProtocolError`
- **AND** it emits no success result
- **AND** it emits error category `protocol_error`
- **AND** it disconnects the handler before completion
- **AND** technical metadata is not used to turn the payload into success

#### Scenario: Handler returns technical metadata without core status

- **WHEN** a payload contains an IP address or connection profile but lacks exact usable core model/version evidence
- **THEN** the worker raises `ProtocolError`
- **AND** it emits error category `protocol_error`
- **AND** successful credential or profile memory is not updated from that attempt

#### Scenario: Parser result lacks required display fields

- **WHEN** parser output lacks exact `Модель` or a non-empty derived `Версия ПО`
- **THEN** parsing raises `ParseError`
- **AND** worker error category is `protocol_error`
- **AND** no result signal is emitted

#### Scenario: Required core and some optional reads succeed

- **GIVEN** the exact required version response succeeded
- **AND** at least one optional endpoint was unavailable without a terminal session or transport failure
- **WHEN** the handler returns the usable partial canonical mapping
- **THEN** parser `Модель` is exactly `Huawei CloudLink Bar 310`
- **AND** parser `Версия ПО` is a non-empty value derived from handler `version`
- **AND** the worker emits a success result containing observed fields
- **AND** unavailable optional fields remain omitted
- **AND** cleanup and completion follow the normal success lifecycle
