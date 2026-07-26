## ADDED Requirements

### Requirement: PDU room-codec enrichment composition boundary

`VCSDiagnosticApp` SHALL compose validated equipment-inventory availability, a focused
room-context resolver, and a dedicated PDU-room-codec enrichment controller. The main window
SHALL remain the owner of credential-provider access, successful credential-index memory,
saved codec connection-profile memory, and shutdown wiring.

The shell SHALL consume two focused non-secret lifecycle boundaries owned by
`PDUController`:

```text
accepted current user PDU refresh
PDU context superseded/invalidated
```

The accepted-refresh boundary SHALL be delegated to the enrichment controller only after the
PDU controller has accepted a current successful user refresh. Stale results, PDU errors,
completion without accepted success, and mutation reconciliation refreshes SHALL NOT start
enrichment.

The supersession boundary SHALL be delegated immediately when PDU model, IP, credential
context, repeat/new user refresh, explicit PDU context invalidation/deactivation, or shutdown
supersedes the current PDU context. The shell SHALL NOT wait for a replacement successful PDU
result before invalidating old enrichment.

The shell SHALL NOT infer supersession or background freshness by reading Qt widgets. It
SHALL NOT maintain a second PDU generation authority. It SHALL only forward the PDU-owned
context generation/revision and safe reason, or invoke an equivalent focused controller
method at the PDU lifecycle boundary.

The enrichment controller SHALL receive only focused providers/callbacks needed to obtain the
immutable inventory, codec credential candidates, saved exact model/IP credential index and
profile, accepted-success persistence, and accepted presentation rendering. It SHALL NOT
become a generic main-window replacement or take ownership of PDU refresh/mutation lifecycle.

#### Scenario: Application starts with valid inventory

- **WHEN** the canonical inventory snapshot loads successfully
- **THEN** the shell composes that immutable inventory revision into the focused enrichment boundary
- **AND** existing device dispatch remains unchanged until a current user PDU refresh is accepted

#### Scenario: Application starts without valid inventory

- **WHEN** canonical inventory cannot be loaded
- **THEN** the shell retains the safe structured load failure for enrichment presentation
- **AND** startup and existing PDU, codec, Matrix, and audio-DSP diagnostics remain available

#### Scenario: PDU controller accepts a user refresh

- **WHEN** `PDUController` publishes an accepted current user-refresh context
- **THEN** the shell delegates it to the enrichment controller
- **AND** the shell does not perform room lookup or codec network I/O itself

#### Scenario: PDU context is superseded before replacement success

- **GIVEN** room/codec data from the current PDU are visible or related-codec work is pending
- **WHEN** `PDUController` publishes model/IP/credential/new-refresh/context/shutdown supersession
- **THEN** the shell immediately delegates supersession to the enrichment controller
- **AND** the old dedicated codec lane is invalidated
- **AND** old room/codec presentation is cleared or reset
- **AND** replacement PDU refresh success is not required for that invalidation

#### Scenario: Replacement PDU refresh fails

- **WHEN** a new PDU refresh superseded old enrichment and then completes with error
- **THEN** no accepted-success enrichment is started
- **AND** old room/codec values remain cleared
- **AND** stale old callbacks cannot restore or persist them

#### Scenario: PDU reconciliation is accepted

- **WHEN** current PDU mutation reconciliation completes
- **THEN** the shell does not treat it as a room-codec enrichment trigger

### Requirement: PDUScreen related-room presentation boundary

`PDUScreen` SHALL remain a rendering boundary while presenting accepted PDU-room-codec
state. It MAY render neutral/pending state, room identity/display evidence, related codec
model/IP, normalized call status, normalized presentation status, and safe structured
resolution/diagnostic outcomes.

`PDUScreen` SHALL NOT load/query inventory, interpret multiplicity, select a codec, resolve
credentials, create or submit codec work, acquire a handler, perform network I/O, decide
freshness, or persist credential/profile memory.

Automatic enrichment failures SHALL be inline and non-modal. They SHALL NOT clear accepted
PDU outlet/device data or change PDU refresh/mutation authority.

The related-room section SHALL be reset immediately on PDU-context supersession, including
new/repeat Refresh before its outcome is known. Reset SHALL NOT be deferred until a later
accepted successful refresh.

#### Scenario: New PDU refresh starts

- **GIVEN** old room/codec values are displayed
- **WHEN** PDU context is superseded at new user-refresh start
- **THEN** `PDUScreen` clears or resets the previous related-room section immediately
- **AND** stale old callbacks cannot restore previous values

#### Scenario: Enrichment resolution is unavailable

- **WHEN** the controller accepts current not-found, ambiguous, unsupported, or inventory-unavailable state
- **THEN** `PDUScreen` renders the safe inline outcome
- **AND** accepted PDU information, outlet table, controls, and connection state remain available

#### Scenario: Related codec status is accepted

- **WHEN** the controller accepts current normalized call and presentation status
- **THEN** `PDUScreen` renders those values
- **AND** it receives no raw codec status, credential values, or session objects

#### Scenario: Screen payload is secret-free

- **WHEN** the shell/controller sends an enrichment presentation model
- **THEN** it contains no credential values, candidate dictionaries, profile names, cookies, Session IDs, CSRF/access tokens, handlers, workers, transports, or sessions
