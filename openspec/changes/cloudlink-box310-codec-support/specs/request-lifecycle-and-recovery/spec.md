# request-lifecycle-and-recovery Specification

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

For both products, the currently approved Bar 310 required-core version gate, explicit optional read-only polling plan, endpoint field ownership and precedence, optional command/protocol failure isolation, terminal authentication/session/transport failures, presentation/sleep normalization, observed-zero preservation, parser success gate, worker cleanup, and secret-redaction requirements SHALL apply unchanged except for the exact expected product identity above.

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
