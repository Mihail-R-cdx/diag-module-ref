## ADDED Requirements

### Requirement: PDU room-codec enrichment composition boundary

`VCSDiagnosticApp` SHALL compose the validated equipment inventory availability state, a
focused room-context resolver, and a dedicated PDU-room-codec enrichment controller. The
main window SHALL remain the owner of credential-provider access, successful credential
index memory, saved codec connection-profile memory, and application shutdown wiring.

The shell SHALL route only non-secret PDU refresh contexts already accepted by
`PDUController` into the enrichment controller. It SHALL NOT start enrichment from generic
worker callbacks, stale PDU results, PDU errors, or PDU mutation reconciliation refreshes.

The enrichment controller SHALL receive only focused providers/callbacks needed to obtain
the immutable inventory, related-codec credential candidates, saved exact model/IP
credential index/profile, and accepted-success persistence. It SHALL NOT become a generic
main-window replacement or take ownership of PDU refresh/mutation lifecycle.

#### Scenario: Application starts with valid inventory

- **WHEN** `VCSDiagnosticApp` is constructed and the canonical inventory snapshot loads successfully
- **THEN** it composes that immutable inventory revision into the focused enrichment boundary
- **AND** existing device diagnostic dispatch remains unchanged until a current user PDU refresh is accepted

#### Scenario: Application starts without valid inventory

- **WHEN** the canonical inventory cannot be loaded
- **THEN** the shell retains the safe structured inventory-load failure for enrichment presentation
- **AND** application startup and existing PDU, codec, Matrix, and audio-DSP diagnostics remain available

#### Scenario: PDU controller accepts a user refresh

- **WHEN** `PDUController` publishes an accepted current user-refresh context
- **THEN** the shell delegates that context to the PDU-room-codec enrichment controller
- **AND** the shell does not perform room lookup or related-codec network I/O itself

#### Scenario: PDU reconciliation is accepted

- **WHEN** a current PDU reconciliation refresh completes after mutation
- **THEN** the shell does not treat it as a new room-codec enrichment trigger

### Requirement: PDUScreen related-room presentation boundary

`PDUScreen` SHALL remain a rendering boundary while presenting accepted PDU-room-codec
enrichment state. It MAY render pending state, room identity/display evidence, related codec
model/IP, normalized call status, normalized presentation status, and safe structured
resolution/diagnostic outcomes.

`PDUScreen` SHALL NOT load or query inventory, interpret zero/one/many multiplicity, select
a codec, resolve credentials, create or submit a codec worker/session, acquire a handler,
perform network I/O, decide enrichment freshness, or persist credential/profile memory.

Automatic enrichment failures SHALL be rendered inline. They SHALL NOT create a modal
connection-error dialog, clear accepted PDU outlet/device data, or change PDU refresh and
mutation authority.

#### Scenario: New PDU context is accepted

- **WHEN** a new current user PDU refresh starts enrichment
- **THEN** `PDUScreen` clears or resets the previous room/codec presentation to the new pending context
- **AND** stale old callbacks cannot restore previous room or codec values

#### Scenario: Enrichment resolution is unavailable

- **WHEN** the controller accepts a current not-found, ambiguous, unsupported, or inventory-unavailable result
- **THEN** `PDUScreen` renders the safe inline outcome
- **AND** it retains the accepted PDU device information, outlet table, controls, and PDU connection state

#### Scenario: Related codec status is accepted

- **WHEN** the controller accepts current normalized call and presentation status
- **THEN** `PDUScreen` renders those values in the related-room/codec section
- **AND** it does not receive raw codec status, credential values, or session objects

#### Scenario: Screen payload is secret-free

- **WHEN** the shell/controller sends an enrichment presentation model to `PDUScreen`
- **THEN** the payload contains no credential values, candidate dictionaries, profile names, cookies, Session IDs, CSRF/access tokens, handlers, workers, transports, or sessions
