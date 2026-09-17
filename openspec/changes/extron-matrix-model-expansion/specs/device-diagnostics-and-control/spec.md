## MODIFIED Requirements

### Requirement: Matrix diagnostics use authoritative per-device capability profiles

The application SHALL collect Matrix diagnostics and control data through an authoritative Extron capability/profile selected from current device identity and, where required, current installed-hardware evidence.

A profile SHALL define or discover at least:

- exact/family identity;
- logical input IDs;
- logical output IDs;
- actually available input IDs;
- actually available output IDs;
- independently routable outputs;
- supported diagnostic reads;
- route command syntax;
- input/output HDCP response interpretation.

A command that is not proven for the active family/profile SHALL NOT be sent merely because a similar Extron family supports it.

#### Scenario: Unknown model does not inherit a nearby profile

- **WHEN** an Extron device identity cannot be resolved to an approved capability profile
- **THEN** the application does not silently select IN1804, IN1808, IN1608, DTP CrossPoint, XTP CrossPoint, or XTP II behavior by nearest-looking substring
- **AND** unsupported diagnostics and route mutations remain unavailable.

#### Scenario: Unproven diagnostic read is not guessed

- **WHEN** the selected profile has no authoritative command for a diagnostic field
- **THEN** the handler sends no speculative SIS command for that field
- **AND** normalized state represents the field as unavailable/unknown according to the existing presentation contract.

### Requirement: Matrix routing authority is multi-output normalized state

Authoritative Matrix routing state SHALL be represented as a mapping from logical output ID to current input ID or explicit untied state.

The previous single `current_connection` scalar SHALL NOT remain authoritative for multi-output-capable devices.

A compatibility projection MAY expose the only output's current input for existing single-output consumers during migration.

#### Scenario: Multiple outputs can route independently

- **GIVEN** a Matrix with available outputs `1`, `2`, `3`, and `4`
- **AND** current routes `{1: 2, 2: 2, 3: 7, 4: None}`
- **WHEN** routing state is normalized
- **THEN** outputs `1` and `2` both independently reference input `2`
- **AND** output `3` references input `7`
- **AND** output `4` remains explicitly untied
- **AND** no scalar current route is used as the multi-output authority.

### Requirement: Matrix topology distinguishes logical routing from physical connectors

The application SHALL distinguish logical independently routable outputs from physical output connectors/endpoints.

GUI route columns and route validation SHALL use available logical routing output IDs, not raw physical connector count.

#### Scenario: Duplicated physical connectors share one logical route

- **WHEN** a supported presentation switcher exposes multiple physical connectors driven by one logical main route
- **THEN** the normalized topology contains one logical route output for that main route
- **AND** the GUI exposes one main routing column rather than one column per physical connector.

### Requirement: XTP and XTP II topology is derived from read-only installed-hardware evidence

For XTP CrossPoint and XTP II CrossPoint, the application SHALL combine authoritative matrix-dimension information with installed input/output board evidence to derive available logical IDs.

State-changing route commands SHALL NOT be used for topology discovery.

Empty board slots SHALL preserve numbering gaps; later installed I/O SHALL NOT be renumbered downward.

#### Scenario: Missing output board preserves logical IDs

- **GIVEN** an XTP-family frame whose installed-board evidence shows that the board serving outputs `13..16` is absent
- **AND** a later board serving outputs `17..20` is installed
- **WHEN** topology is derived
- **THEN** outputs `13..16` are unavailable
- **AND** outputs `17..20` retain those exact logical IDs
- **AND** the application does not compress them to `13..16`.

### Requirement: Extron route commands are selected by approved profile

The handler layer SHALL select route query and mutation syntax from the active approved profile.

At minimum the following profiles SHALL be represented:

- IN1804 working compatibility profile: read `!`, set `<I>*1!`;
- IN1808 profile: read `1!`, set `<I>*1!`;
- IN1608 xi profile: read `!`, set `<I>!`;
- CrossPoint multi-output profile: read `<O>!`, set `<I>*<O>!`, untie `0*<O>!`.

The existing IN1804 working profile SHALL be preserved even where a manual documents an alternate accepted route form.

#### Scenario: IN1808 route read targets main logical output

- **WHEN** the application reads the current IN1808 main route
- **THEN** it sends `1!` before transport termination is appended
- **AND** it does not use the IN1804 bare `!` query.

#### Scenario: IN1608 mutation uses its own profile

- **WHEN** input `5` is selected on a supported IN1608 xi
- **THEN** the state-changing SIS command before transport termination is `5!`
- **AND** the application does not substitute `5*1!` merely because IN1804/IN1808 accept that form.

#### Scenario: CrossPoint mutation addresses explicit output

- **WHEN** input `3` is routed to output `7` on a supported CrossPoint profile
- **THEN** the state-changing SIS command before transport termination is `3*7!`.

### Requirement: IN1804 hardware-confirmed SIS behavior remains compatible

The currently deployed IN1804 profile SHALL preserve the existing hardware-confirmed diagnostic/control commands:

- `1I` model identity;
- `W20STAT` temperature;
- `WI<N>VNAM` input names;
- `WO1VNAM` output name;
- `W0LS` signal presence;
- `WE<N>HDCP` HDCP authorization;
- `WI<N>HDCP` input HDCP status;
- `WO1HDCP` output HDCP status;
- `!` current route;
- `<I>*1!` route mutation.

Normal command termination remains the responsibility of the common Extron transport.

#### Scenario: Existing IN1804 full status remains hardware compatible

- **WHEN** a current IN1804 record is refreshed after this change
- **THEN** the profile uses the same hardware-confirmed commands listed above
- **AND** the change does not replace them solely to match an alternate canonical notation from documentation.

### Requirement: Input HDCP status is normalized by profile-specific semantics

Raw Extron input HDCP values SHALL be interpreted by the active profile rather than one global raw-value mapping.

IN1804 and IN1808 SHALL interpret raw input HDCP as:

- `0` source absent;
- `1` source present without HDCP;
- `2` source present with HDCP.

IN1608 xi, DTP CrossPoint, XTP CrossPoint and XTP II CrossPoint SHALL interpret raw input HDCP as:

- `0` source absent;
- `1` source present and HDCP-compliant/present;
- `2` source present and not HDCP-compliant/absent.

Normalized input state SHALL distinguish at least absent, HDCP present, HDCP absent, and unknown.

HDCP authorization/configuration SHALL remain distinct from actual input HDCP status.

#### Scenario: Raw value 1 differs by generation

- **WHEN** raw input HDCP value `1` is received from IN1808
- **THEN** normalized state is `PRESENT_NO_HDCP`
- **WHEN** raw input HDCP value `1` is received from XTP CrossPoint
- **THEN** normalized state is `PRESENT_HDCP`.

### Requirement: Signal presence is normalized against available input IDs

Signal-presence reads SHALL be mapped only to authoritative available input IDs from the active topology.

A missing board slot or otherwise unavailable input SHALL NOT be synthesized as an active supported input merely because the chassis has a larger maximum capacity.

#### Scenario: XTP signal list respects board gaps

- **GIVEN** runtime topology identifies a gap in available XTP input IDs
- **WHEN** signal-presence evidence is normalized
- **THEN** only authoritative available IDs are exposed as supported input rows
- **AND** unavailable IDs are not silently renumbered or fabricated.

### Requirement: Matrix route mutation preserves existing ambiguity safety

Generalizing Matrix route mutation to explicit output IDs SHALL preserve the existing state-changing command safety boundary.

After a route command may have been sent, the application SHALL NOT blindly replay it solely to recover transport/session state.

Successful mutation SHALL be reconciled with an authoritative read of the targeted output route.

#### Scenario: Possible-send CrossPoint route is not replayed

- **WHEN** a CrossPoint route command may have reached the device but its response is lost
- **THEN** the same state-changing command is not automatically sent again
- **AND** the UI does not claim a confirmed route until authoritative reconciliation succeeds.