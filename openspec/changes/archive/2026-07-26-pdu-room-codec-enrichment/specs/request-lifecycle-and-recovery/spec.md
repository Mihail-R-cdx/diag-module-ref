## ADDED Requirements

### Requirement: Independent related-codec request context

Automatic related-codec status work started from an accepted PDU refresh SHALL have an
application-owned request context independent from PDU refresh/mutation lanes, generic
`_active_request`, global `current_worker`, and the user codec interactive-session context.

The immutable context SHALL bind at least enrichment generation/operation identity, accepted
PDU generation and refresh operation identity, PDU model/IP, immutable inventory
`snapshot_id`, selected PDU/codec record identities, authoritative room ID, codec model/IP,
and non-secret credential-context revisions or equivalent freshness tokens.

A repeat accepted user PDU refresh SHALL create a new enrichment generation even when every
resolved public and credential/profile identity value is unchanged.

PDU model/IP/context change, PDU credential-context change, start of a new or repeat user PDU
refresh, explicit PDU context invalidation/deactivation, inventory replacement, relevant
codec credential change, and application shutdown SHALL supersede old enrichment immediately
through a focused PDU/application lifecycle boundary. Supersession SHALL NOT wait for a new
successful PDU result.

#### Scenario: Repeat Refresh uses the same PDU and codec identity

- **GIVEN** related-codec work is active or queued for one accepted PDU refresh
- **WHEN** a later refresh for the same PDU resolves the same codec model/IP, credential chain/index, and saved profile
- **THEN** the later lifecycle creates a distinct enrichment generation
- **AND** the old generation cannot update presentation or credential/profile memory
- **AND** equal public/session identity does not preserve currentness

#### Scenario: Replacement PDU refresh fails

- **GIVEN** old enrichment was superseded when replacement PDU refresh started
- **WHEN** replacement PDU refresh fails without accepted success
- **THEN** old enrichment remains stale
- **AND** no old related-codec callback or queued operation becomes current again

#### Scenario: User codec session has another context

- **GIVEN** `CodecScreen` owns an interactive session for codec A
- **WHEN** PDU enrichment starts status for codec B
- **THEN** distinct context generations and session ownership are used
- **AND** neither context invalidates, reuses, or authorizes callbacks for the other

### Requirement: Every new enrichment forces dedicated session-generation rollover

Before activating the dedicated related-codec session for every new enrichment generation,
the enrichment controller SHALL invalidate the previous dedicated session context even when
the prospective session identity is unchanged.

The compliant lifecycle SHALL be equivalent to:

```text
new enrichment generation becomes current
    -> dedicated session invalidate_context or equivalent force rollover
    -> dedicated session activate_context
    -> related-codec read submission
```

The implementation MAY add an explicit force-rollover API or include enrichment generation in
private session identity, but it SHALL prove equivalent behavior. Calling the existing
`activate_context()` with equal model/IP/credential identities/start index/saved profile and
accepting its existing generation SHALL NOT satisfy this requirement.

The force rollover SHALL happen synchronously with currentness publication before old queued
work can acquire a handler. Cleanup may remain serialized on the owning execution lane.

#### Scenario: Old operation is queued and next context is identical

- **GIVEN** an old related-codec operation is queued behind other lane work
- **WHEN** repeat PDU Refresh produces an identical related-codec session identity
- **THEN** the dedicated session generation is rolled over before new activation
- **AND** the old operation observes stale generation at the head of the queue
- **AND** handler factory/acquisition is not invoked for that old operation
- **AND** the old operation performs zero network I/O

### Requirement: Related-codec stale work is suppressed before network I/O

Queued related-codec work SHALL recheck both its captured enrichment generation and dedicated
session generation immediately before handler acquisition. When handler preparation and first
network I/O are separate, it SHALL recheck again immediately before first network I/O.

A stale queued operation SHALL be dropped without constructing or acquiring a handler,
opening HTTP/HTTPS/SSH or another transport, or sending a device request. Background code
SHALL NOT read Qt widget values as freshness authority.

If I/O was already in flight when context became stale, its result, error, progress,
completion, credential index, and connection profile SHALL NOT change current presentation,
PDU state, or successful credential/profile memory. Cleanup SHALL still occur on the owning
execution lane.

#### Scenario: Queued enrichment is superseded before execution

- **WHEN** related-codec status is queued and a new enrichment generation is published before it reaches the lane head
- **THEN** the operation is dropped before handler acquisition
- **AND** it performs zero network I/O

#### Scenario: Context changes after handler preparation

- **WHEN** a related-codec handler is prepared and context becomes stale before first network I/O
- **THEN** the final freshness check prevents transport open and device request
- **AND** prepared resources are released safely

#### Scenario: Old status returns after new PDU context

- **WHEN** in-flight status from an old PDU context completes after supersession
- **THEN** old status does not update related-room presentation, PDU state, dialogs, controls, or credential/profile memory

### Requirement: Bounded read-only related-codec recovery

Related-codec status SHALL execute outside the Qt GUI thread through one dedicated serialized
application-owned lane. It SHALL use read-only semantics and permit at most one reconnect
cycle and one replay after successful recovery. Recovery SHALL not recurse.

Confirmed established-session invalidation SHALL first invalidate the old handler/session and
reconnect with the same assigned credential using supported saved-first transport order.
Credential advancement MAY occur only when a new login during acquisition/recovery produces
structured confirmed authentication rejection and another unattempted candidate remains.
Transport, session, authentication, protocol, and unavailable-status failures SHALL remain
separately classified.

#### Scenario: Related-codec session expires

- **WHEN** read-only status detects confirmed established-session invalidation
- **THEN** the lane invalidates that session and performs at most one reconnect cycle
- **AND** successful reconnect permits at most one replay

#### Scenario: Transport fallback is available

- **WHEN** one supported transport fails without structured authentication rejection and another remains
- **THEN** acquisition may continue on the next transport with the same assigned credential
- **AND** no credential advancement occurs from transport failure

### Requirement: Related-codec resource release

The dedicated related-codec lane SHALL invalidate and release its handler, HTTP opener,
cookies, Session ID, CSRF/access token, SSH client/channel, and other model-specific resources
on terminal success, terminal failure, PDU/enrichment supersession, relevant credential
change, inventory replacement, and application shutdown.

Network/session cleanup SHALL run on the owning background lane. GUI invalidation SHALL
publish cancellation/currentness without blocking the Qt GUI thread on network cleanup.
Cleanup SHALL be idempotent or exactly once, and callbacks after supersession SHALL remain
stale.

#### Scenario: Application closes during related-codec work

- **WHEN** shutdown supersedes active related-codec work
- **THEN** enrichment and session contexts are invalidated immediately
- **AND** resource cleanup runs on the owning background lane
- **AND** no later callback updates closing or destroyed GUI
