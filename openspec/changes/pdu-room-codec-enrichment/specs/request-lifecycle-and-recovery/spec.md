## ADDED Requirements

### Requirement: Independent related-codec request context

Automatic related-codec status work started from an accepted PDU refresh SHALL have an
application-owned request context independent from the PDU refresh/mutation lanes, generic
`_active_request`, global `current_worker`, and the user codec interactive-session context.

The immutable context SHALL bind at least the enrichment generation/operation identity,
accepted PDU generation and refresh operation identity, PDU model/IP, immutable inventory
`snapshot_id`, selected PDU/codec record identities, authoritative room ID, codec model/IP,
and non-secret credential-context revisions or equivalent freshness tokens.

A repeat accepted user PDU refresh SHALL create a new enrichment generation even when the
PDU model and IP are unchanged. A PDU model/IP/context change, relevant credential change,
inventory revision replacement, or application shutdown SHALL supersede the old generation.

#### Scenario: Repeat Refresh uses the same PDU identity

- **GIVEN** related-codec work is active for one accepted PDU refresh
- **WHEN** a later user refresh for the same PDU model/IP is accepted
- **THEN** the later refresh creates a new enrichment generation
- **AND** the earlier generation cannot update presentation or credential/profile memory

#### Scenario: User codec session has another context

- **GIVEN** `CodecScreen` owns an interactive session for codec A
- **WHEN** PDU enrichment starts related-codec status for codec B
- **THEN** the two operations use distinct context generations and session ownership
- **AND** neither context invalidates, reuses, or authorizes callbacks for the other

### Requirement: Related-codec stale work is suppressed before network I/O

Queued related-codec work SHALL recheck its captured application-owned context immediately
before handler acquisition. When handler construction/preparation and first network I/O are
separate phases, it SHALL recheck again immediately before first network I/O.

A stale queued operation SHALL be dropped without constructing or acquiring a handler,
opening HTTP/HTTPS/SSH or another transport, or sending a device request. Background code
SHALL NOT read Qt widget values as freshness authority.

If related-codec network I/O was already in flight when the context became stale, its result,
error, progress, completion, credential index, and connection profile SHALL NOT change the
current presentation, PDU state, or successful credential/profile memory. Cleanup SHALL
still occur on the execution lane that owns the resources.

#### Scenario: Queued enrichment is superseded before execution

- **WHEN** related-codec status is queued and a new enrichment generation is published before it reaches the head of the lane
- **THEN** the queued operation is dropped before handler acquisition
- **AND** it performs zero network I/O

#### Scenario: Context changes after handler preparation

- **WHEN** a related-codec handler is prepared and the context becomes stale before first network I/O
- **THEN** the final freshness check prevents transport open and device request
- **AND** prepared resources are released safely

#### Scenario: Old status returns after a new PDU context

- **WHEN** in-flight related-codec status from an old PDU context completes after a newer context is active
- **THEN** old status does not update the related-room section, PDU status, dialogs, refresh controls, or credential/profile memory

### Requirement: Bounded read-only related-codec recovery

Related-codec status SHALL execute outside the Qt GUI thread through one dedicated serialized
application-owned lane. The operation SHALL use read-only semantics and SHALL permit at most
one reconnect cycle and one replay after successful recovery. Recovery SHALL not recurse.

A confirmed established-session invalidation SHALL first invalidate the old handler/session
and reconnect with the same assigned credential using supported saved-first transport order.
Credential advancement MAY occur only when a new login during acquisition/recovery produces
a structured confirmed authentication rejection and another unattempted candidate remains.
Transport, session, authentication, protocol, and unavailable-status failures SHALL remain
separately classified.

#### Scenario: Related-codec session expires

- **WHEN** the read-only status operation detects confirmed invalidation of an established related-codec session
- **THEN** the lane invalidates that session and performs at most one reconnect cycle
- **AND** successful reconnect permits at most one replay of the status read

#### Scenario: Reconnect cannot restore status

- **WHEN** the one permitted reconnect cycle fails or the replay fails
- **THEN** one terminal redacted diagnostic outcome is produced
- **AND** no recursive reconnect or replay starts

#### Scenario: Transport fallback is available

- **WHEN** one supported transport fails without structured authentication rejection and another supported transport remains
- **THEN** acquisition may continue with the same assigned credential on the next transport
- **AND** no credential advancement occurs from the transport failure

### Requirement: Related-codec resource release

The dedicated related-codec lane SHALL invalidate and release its handler, HTTP opener,
cookies, Session ID, CSRF/access token, SSH client/channel, and other model-specific
session/transport resources on terminal success, terminal failure, context supersession,
relevant credential change, and application shutdown.

Network/session cleanup SHALL run on the background execution lane that owns those resources.
GUI invalidation SHALL publish cancellation/currentness changes without blocking the Qt GUI
thread on network cleanup. Cleanup SHALL be idempotent or exactly once, and callbacks after
supersession SHALL remain stale.

#### Scenario: Successful bounded read completes

- **WHEN** current related-codec status succeeds and its result is accepted
- **THEN** the bounded related-codec session is invalidated or closed according to the focused controller lifecycle
- **AND** no persistent user codec session is affected

#### Scenario: Application closes during related-codec work

- **WHEN** the application close path supersedes active related-codec work
- **THEN** the context is invalidated immediately
- **AND** resource cleanup runs on the owning background lane
- **AND** no later callback updates the closing or destroyed GUI
