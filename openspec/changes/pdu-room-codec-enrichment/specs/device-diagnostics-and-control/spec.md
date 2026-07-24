## ADDED Requirements

### Requirement: PDU diagnostics include optional related-room codec context

After a current user PDU refresh is accepted, the existing PDU screen SHALL be able to
present optional inventory-derived room context and related VCS codec diagnostic state. The
presentation SHALL include, when available and current:

```text
room_id
room_name
codec source/display model
codec diagnostic model
codec IP address
call status
presentation/broadcast status
```

The related-room section SHALL be contextual enrichment of the accepted PDU diagnostics,
not a replacement device diagnostic request. A not-found, ambiguous, unsupported,
unavailable, authentication, transport, protocol, or stale enrichment outcome SHALL NOT
change the accepted PDU diagnostic result into failure, clear outlet records, or disable
otherwise valid PDU control capabilities.

#### Scenario: PDU and related codec both succeed

- **WHEN** a supported PDU refresh succeeds, inventory resolves one room and one supported codec, and related-codec status succeeds
- **THEN** `PDUScreen` retains the PDU device/outlet data
- **AND** it also displays current room identity plus normalized codec call and presentation status

#### Scenario: PDU succeeds but room cannot be resolved

- **WHEN** accepted PDU diagnostics succeeds and inventory resolution is not found, ambiguous, mismatched, or missing room identity
- **THEN** `PDUScreen` retains successful PDU diagnostics and controls
- **AND** the related-room section displays the safe structured resolution state

#### Scenario: PDU succeeds but related codec fails

- **WHEN** room/codec resolution succeeds but related-codec authentication, transport, protocol, or status normalization fails
- **THEN** accepted PDU diagnostics remains successful and usable
- **AND** only the related-codec section displays the diagnostic failure
- **AND** no automatic modal device-connection error is shown

### Requirement: Related-codec status reuses supported codec protocol boundaries

Automatic related-codec status SHALL use the existing supported handler and transport
boundaries for Huawei TE20, Huawei TE40, CloudLink Bar 310, and Polycom RPG 310. It SHALL
reuse existing status methods and parser normalization where available and SHALL NOT invent
a protocol from `source_model`, a manufacturer substring, or an unsupported inventory
record.

The focused related-codec adapter SHALL expose only normalized call and presentation status
to PDU presentation. Complete raw status and model-specific session artifacts SHALL remain
inside the handler/session/adapter boundary.

#### Scenario: Huawei related codec is resolved

- **WHEN** the inventory resolves an exact supported Huawei codec model/IP
- **THEN** automatic status uses that model's existing supported handler and saved-first transport order
- **AND** normalized call and presentation status are derived through the existing parser or an equivalent focused adapter

#### Scenario: Polycom related codec is resolved

- **WHEN** the inventory resolves exact `Polycom RPG 310`
- **THEN** automatic status uses the existing Polycom status/session protocol boundary
- **AND** it does not reuse or alter the user codec interactive session

#### Scenario: Inventory codec is unsupported

- **WHEN** a canonical `video_codec` record has no exact supported VCS `diagnostic_model`
- **THEN** the related-codec section reports unsupported
- **AND** no handler is guessed or constructed from source text

### Requirement: Related-codec diagnostics are read-only

The automatic room-codec operation SHALL be read-only. It SHALL not expose or execute
presentation control, Wake, volume, mute, SIP update, call placement, call termination, or
another state-changing codec command. Its only device purpose in this change is to obtain
status required for the PDU/room context.

#### Scenario: Related-codec status is requested

- **WHEN** room/codec resolution succeeds
- **THEN** the application submits only the approved read-only status operation
- **AND** it does not send any codec state-changing command

#### Scenario: Status recovery is required

- **WHEN** the read-only status loses its session and bounded reconnect succeeds
- **THEN** the application may replay the read once
- **AND** no state-changing codec operation is introduced during recovery
