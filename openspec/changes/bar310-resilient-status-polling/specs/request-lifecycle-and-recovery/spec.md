# request-lifecycle-and-recovery Specification

## ADDED Requirements

### Requirement: CloudLink Bar 310 polling uses a closed resilient status plan

An ordinary CloudLink Bar 310 status refresh SHALL execute an explicit reviewed read-only polling plan rather than iterate every entry in the handler command map.

The required core request SHALL be `get_version`. A successful refresh SHALL require a successful core response with object-shaped data and usable software-version evidence. Canonical model identity SHALL be created only after that successful core response. An unsuccessful required core response SHALL raise `CommandError`; missing or malformed required core data SHALL raise `ProtocolError`.

The optional read-only enrichment requests SHALL be limited to MAC, audio, line/SIP, call, presentation, sleep, camera, and HD-AI microphone status. Configuration requests including `get_config_default` and `get_config`, every state-changing request, and future command-map-only entries SHALL NOT run during ordinary status refresh unless added to the reviewed polling plan by a later approved change.

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
- **AND** it omits presentation from that refresh result
- **AND** it does not return an empty mapping
- **AND** it does not authorize credential fallback

#### Scenario: Required core response is unsuccessful

- **WHEN** the required version endpoint returns `success != 1`
- **THEN** status collection raises `CommandError`
- **AND** no result mapping is returned as success

#### Scenario: Required core payload is malformed

- **WHEN** the required version endpoint does not provide object-shaped data with usable software-version evidence
- **THEN** status collection raises `ProtocolError`
- **AND** canonical model/version defaults are not manufactured

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

### Requirement: CloudLink Bar 310 normalization distinguishes unavailable from observed state

CloudLink Bar 310 canonical status fields SHALL be populated only from successful structured endpoint observations. An unavailable optional endpoint SHALL cause its canonical fields to be omitted rather than replaced with semantic defaults such as `Off`, `Stop`, `No Call`, or zero.

A successful endpoint value that is legitimately zero, false, idle, stopped, muted, or sleeping SHALL remain present and SHALL NOT be mistaken for missing data.

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

#### Scenario: Observed volume is zero

- **WHEN** a successful audio response reports a valid speaker volume of zero
- **THEN** canonical speaker volume remains present with value zero
- **AND** zero is not treated as unavailable data

### Requirement: CloudLink Bar 310 worker success requires usable canonical status

`HuaweiBar310Worker` SHALL emit a success result only after the handler payload and parser result contain usable canonical evidence from the required core Bar 310 response.

An empty mapping, non-mapping payload, payload without usable core model/version evidence, or parser result without core canonical display fields SHALL follow the worker error path. Technical fields such as `ip_address` and `connection_profile` SHALL NOT satisfy the success gate and SHALL be added only after canonical payload validation succeeds.

For an unusable payload, the worker SHALL emit no result signal, SHALL emit a safe error outcome, SHALL disconnect any created handler, and SHALL emit completion. For a usable partial payload, the worker SHALL emit the canonical result and preserve the existing cleanup/completion lifecycle.

The application/composition layer SHALL remain the authority for stale-result acceptance and successful credential-index/profile persistence. An unusable Bar 310 payload SHALL NOT become successful-operation evidence for that policy.

#### Scenario: Handler returns an empty mapping

- **WHEN** `handler.get_status()` returns `{}`
- **THEN** the worker emits no success result
- **AND** it emits an error outcome
- **AND** it disconnects the handler before completion
- **AND** technical metadata is not used to turn the payload into success

#### Scenario: Handler returns technical metadata without core status

- **WHEN** a payload contains an IP address or connection profile but lacks usable core model/version evidence
- **THEN** the worker rejects the payload as unusable
- **AND** successful credential or profile memory is not updated from that attempt

#### Scenario: Required core and some optional reads succeed

- **GIVEN** the required version response succeeded
- **AND** at least one optional endpoint was unavailable without a terminal session or transport failure
- **WHEN** the handler returns the usable partial canonical mapping
- **THEN** the worker emits a success result containing observed fields
- **AND** unavailable optional fields remain omitted
- **AND** cleanup and completion follow the normal success lifecycle
