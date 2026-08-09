# request-lifecycle-and-recovery Specification

## MODIFIED Requirements

### Requirement: CloudLink Bar 310 required core evidence is exact

For the closed CloudLink Bar/Box 310 protocol family, a successful `get_version` observation SHALL require all of the following:

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

`softVersion` SHALL remain the only approved software-version source key. The shared handler SHALL NOT use another response key, `Unknown`, `N/A`, an empty value, a model constant, or another manufactured default as software-version evidence.

Before the shared Bar/Box protocol path executes, the already assigned exact application model SHALL determine one trusted expected handler/parser/display identity through this closed mapping:

```text
CloudLink Bar 310 -> Huawei CloudLink Bar 310
CloudLink Box 310 -> Huawei CloudLink Box 310
```

No other input SHALL select or alter that identity. In particular, device response text, source inventory text, model substrings, handler availability, protocol success/failure, prior requests, or the other family member SHALL NOT become model-identity authority.

After the exact core gate succeeds, the shared handler result SHALL contain exactly:

```text
model == expected handler/parser/display identity for the already assigned application model
version == data["softVersion"].strip()
```

The model string SHALL NOT be copied from a free-form device response or changed to another spelling. The same successful response MAY add `serial_number` from observed `data["lisence"]` and `mic_version` from observed `data["micVersion"]`; absence of those optional values SHALL NOT invalidate core success and SHALL NOT create `N/A` defaults.

An unsuccessful required core response SHALL raise `CommandError`. Missing/non-Mapping core data, a missing `softVersion`, `None`, a non-string value, an empty or whitespace-only string, or a case-insensitive `Unknown` value SHALL raise `ProtocolError`. No result mapping SHALL be returned as success for those outcomes.

#### Scenario: Bar 310 required core response is successful

- **GIVEN** the already assigned application model is exactly `CloudLink Bar 310`
- **WHEN** `get_version.data["softVersion"]` is a non-empty string after `strip()` and is not `Unknown`
- **THEN** handler `model` is exactly `Huawei CloudLink Bar 310`
- **AND** handler `version` is exactly the stripped `softVersion`
- **AND** no response-provided model label or manufactured version default is used

#### Scenario: Box 310 required core response is successful

- **GIVEN** the already assigned application model is exactly `CloudLink Box 310`
- **WHEN** `get_version.data["softVersion"]` is a non-empty string after `strip()` and is not `Unknown`
- **THEN** handler `model` is exactly `Huawei CloudLink Box 310`
- **AND** handler `version` is exactly the stripped `softVersion`
- **AND** no response-provided model label or Bar identity is used

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

### Requirement: CloudLink Bar 310 parser and worker success require exact usable canonical status

For each operation in the closed Bar/Box 310 protocol family, `HuaweiBar310DataParser` and `HuaweiBar310Worker` SHALL validate against the trusted expected handler/parser/display identity derived from the already assigned exact application model:

```text
CloudLink Bar 310 -> Huawei CloudLink Bar 310
CloudLink Box 310 -> Huawei CloudLink Box 310
```

`HuaweiBar310DataParser` SHALL reject raw data unless it is a Mapping with exact `model == expected handler/parser/display identity` and a non-empty string `version` that is not `Unknown`.

The parser SHALL produce these exact required display fields without defaults:

```text
"Модель" == expected handler/parser/display identity
"Версия ПО" is non-empty and derived from raw_data["version"]
```

A missing model, a model different from the expected identity for the bound operation, a missing/non-string/empty version, `Unknown`, or a version that becomes empty after display cleanup SHALL raise `ParseError`. Accepting either Bar or Box identity without checking which exact application model owns the operation SHALL NOT satisfy this requirement. Optional display fields SHALL be emitted only when their canonical handler fields are present. In particular, `Статус камеры`, SIP, call, presentation, sleep, microphone status, and microphone volume SHALL NOT be manufactured from absence.

`HuaweiBar310Worker` SHALL defensively raise `ProtocolError` for an empty Mapping, non-Mapping payload, payload whose exact `model` differs from the expected identity for its already assigned application model, payload without a non-empty usable `version`, or metadata-only payload. It SHALL add technical `ip_address` and `connection_profile` fields only after raw and parsed payload validation succeeds.

Raw-payload `ProtocolError` and parser `ParseError` SHALL pass through the existing typed codec failure classifier and SHALL emit exact machine category:

```text
protocol_error
```

The worker SHALL NOT represent these contract failures with `ValueError`, a generic exception, an explicit `connection_error`, or another transport category.

For an unusable payload, the worker SHALL emit no result signal, SHALL emit `protocol_error`, SHALL disconnect any created handler, and SHALL emit completion. For a usable partial payload, the worker SHALL emit the canonical result and preserve the existing cleanup/completion lifecycle.

The application/composition layer SHALL remain the authority for stale-result acceptance and successful credential-index/profile persistence. An unusable Bar/Box 310 payload SHALL NOT become successful-operation evidence for that policy.

#### Scenario: Handler returns an empty mapping

- **WHEN** `handler.get_status()` returns `{}`
- **THEN** the worker raises `ProtocolError`
- **AND** it emits no success result
- **AND** it emits error category `protocol_error`
- **AND** it disconnects the handler before completion
- **AND** technical metadata is not used to turn the payload into success

#### Scenario: Handler returns technical metadata without core status

- **WHEN** a payload contains an IP address or connection profile but lacks exact usable core model/version evidence for the bound Bar/Box operation
- **THEN** the worker raises `ProtocolError`
- **AND** it emits error category `protocol_error`
- **AND** successful credential or profile memory is not updated from that attempt

#### Scenario: Bar context rejects Box identity

- **GIVEN** the operation is bound to exact application model `CloudLink Bar 310`
- **WHEN** raw or parsed canonical identity is `Huawei CloudLink Box 310`
- **THEN** the worker or parser rejects the mismatch through `ProtocolError` or `ParseError` as applicable
- **AND** no result signal is emitted
- **AND** the operation is not rewritten or retried as Box 310

#### Scenario: Box context rejects Bar identity

- **GIVEN** the operation is bound to exact application model `CloudLink Box 310`
- **WHEN** raw or parsed canonical identity is `Huawei CloudLink Bar 310`
- **THEN** the worker or parser rejects the mismatch through `ProtocolError` or `ParseError` as applicable
- **AND** no result signal is emitted
- **AND** the operation is not rewritten or retried as Bar 310

#### Scenario: Parser result lacks required display fields

- **WHEN** parser output lacks exact expected `Модель` or a non-empty derived `Версия ПО`
- **THEN** parsing raises `ParseError`
- **AND** worker error category is `protocol_error`
- **AND** no result signal is emitted

#### Scenario: Bar required core and some optional reads succeed

- **GIVEN** the operation is bound to exact `CloudLink Bar 310`
- **AND** the exact required version response succeeded
- **AND** at least one optional endpoint was unavailable without a terminal session or transport failure
- **WHEN** the handler returns the usable partial canonical mapping
- **THEN** parser `Модель` is exactly `Huawei CloudLink Bar 310`
- **AND** parser `Версия ПО` is a non-empty value derived from handler `version`
- **AND** the worker emits a success result containing observed fields
- **AND** unavailable optional fields remain omitted
- **AND** cleanup and completion follow the normal success lifecycle

#### Scenario: Box required core and some optional reads succeed

- **GIVEN** the operation is bound to exact `CloudLink Box 310`
- **AND** the exact required version response succeeded
- **AND** at least one optional endpoint was unavailable without a terminal session or transport failure
- **WHEN** the shared handler returns the usable partial canonical mapping
- **THEN** parser `Модель` is exactly `Huawei CloudLink Box 310`
- **AND** parser `Версия ПО` is a non-empty value derived from handler `version`
- **AND** the worker emits a success result containing observed fields
- **AND** unavailable optional fields remain omitted
- **AND** cleanup and completion follow the normal success lifecycle

## ADDED Requirements

### Requirement: CloudLink Box 310 reuses the approved CloudLink Bar 310 protocol lifecycle with distinct identity

For an application request whose already assigned exact canonical model is `CloudLink Box 310`, the codec lifecycle SHALL use the same management protocol implementation, supported transport profile, command semantics, polling plan, endpoint ownership, normalization, typed failure behavior, recovery policy, cleanup, and redaction boundaries already approved for `CloudLink Bar 310`.

The shared protocol lifecycle SHALL preserve distinct trusted product identity. The exact mapping SHALL be:

```text
application model CloudLink Bar 310
    -> handler/parser/display model Huawei CloudLink Bar 310

application model CloudLink Box 310
    -> handler/parser/display model Huawei CloudLink Box 310
```

The expected handler/parser/display identity SHALL be derived only from the already assigned exact application model through a closed reviewed mapping or equivalent exact construction parameter. It SHALL NOT be inferred from device response text, source inventory text, model substrings, handler availability, protocol success/failure, or another family member.

`CloudLinkBar310Handler` SHALL remain the shared protocol implementation for both approved products. Implementation SHALL NOT create a second independent Box 310 copy of the Bar command map, polling plan, endpoint normalizers, or transport/session logic solely to support the additional name.

For both products, the currently approved Bar 310 required-core version gate, explicit optional read-only polling plan, endpoint field ownership and precedence, optional command/protocol failure isolation, terminal authentication/session/transport failures, presentation/sleep normalization, observed-zero preservation, parser success gate, worker cleanup, and secret-redaction requirements SHALL apply unchanged except for the exact expected product identity defined by the modified requirements above.

All existing application paths that select protocol capability by exact Bar 310 model SHALL treat `CloudLink Bar 310` and `CloudLink Box 310` as one closed protocol family while preserving the exact assigned model in operation context. This includes ordinary status refresh, supported interactive codec operations, related-codec read-only status acquisition, and existing Bar-supported SIP-server configuration behavior.

The application SHALL continue to own credentials and successful connection memory by exact canonical model and IP. Protocol equivalence SHALL NOT authorize implicit credential sharing, credential fallback, successful-index sharing, connection-profile sharing, or model switching between Bar 310 and Box 310. A deployment MAY explicitly configure the same credential profile for both exact models, but that is configuration rather than runtime alias behavior.

A failure in a Box 310 operation SHALL remain a failure of the already assigned Box 310 path under existing typed policy. No authentication, session, transport, protocol, parser, timeout, or ambiguous-result failure SHALL cause the application, worker, handler, parser, or interactive controller to retry the operation as `CloudLink Bar 310`. The inverse restriction applies to Bar 310.

#### Scenario: Box 310 ordinary refresh uses the shared protocol implementation

- **GIVEN** application dispatch assigned exact model `CloudLink Box 310`
- **WHEN** ordinary codec refresh acquires the Bar/Box protocol implementation
- **THEN** it uses the same approved Bar 310 transport and polling semantics
- **AND** the canonical raw status model is exactly `Huawei CloudLink Box 310`
- **AND** parsed GUI model is exactly `Huawei CloudLink Box 310`
- **AND** no second Box-specific command map or polling plan is required

#### Scenario: Existing Bar 310 identity remains unchanged

- **GIVEN** application dispatch assigned exact model `CloudLink Bar 310`
- **WHEN** the shared protocol implementation completes a usable refresh
- **THEN** the canonical raw status model remains exactly `Huawei CloudLink Bar 310`
- **AND** parsed GUI model remains exactly `Huawei CloudLink Bar 310`
- **AND** Box 310 support does not weaken the existing Bar identity gate

#### Scenario: Shared implementation receives the wrong expected identity

- **GIVEN** an operation is bound to exact application model `CloudLink Box 310`
- **WHEN** the worker or parser observes/receives canonical protocol identity `Huawei CloudLink Bar 310` instead of the expected Box identity
- **THEN** the operation fails through the existing protocol/parser error path
- **AND** it does not silently rewrite the result, accept the other family identity, or change the assigned model

#### Scenario: Box 310 interactive operation uses the Bar protocol capability

- **GIVEN** the current interactive context model is exactly `CloudLink Box 310`
- **WHEN** an operation supported by the existing Bar 310 handler is submitted
- **THEN** handler acquisition uses the shared `CloudLinkBar310Handler` implementation and the approved Box transport profile
- **AND** the interactive context and result model remain exactly `CloudLink Box 310`
- **AND** stale and retry policy remains unchanged

#### Scenario: Box 310 is the related room codec

- **GIVEN** PDU room resolution returns exact `codec_diagnostic_model = CloudLink Box 310`
- **WHEN** related-codec read-only status is acquired
- **THEN** the controller resolves credentials and connection memory for exact Box 310 model/IP
- **AND** it uses the same Bar 310 call/presentation command semantics
- **AND** accepted presentation still reports exact `CloudLink Box 310`

#### Scenario: Bar and Box credential success is not shared implicitly

- **GIVEN** a credential candidate succeeds for `CloudLink Box 310` at one IP
- **WHEN** application success memory is persisted
- **THEN** only the exact Box 310 model/IP successful index and connection profile are updated
- **AND** no `CloudLink Bar 310` credential index or connection profile is changed solely because the protocol is shared

#### Scenario: Box failure does not retry as Bar

- **GIVEN** an operation is bound to exact model `CloudLink Box 310`
- **WHEN** the operation fails with authentication, session, transport, protocol, parser, timeout, or ambiguous-result failure
- **THEN** existing retry/recovery policy applies only within the Box 310 operation context
- **AND** no component changes the model to `CloudLink Bar 310` as fallback
