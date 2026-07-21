## ADDED Requirements

### Requirement: PDU controller credential policy delegation
The existing application/composition credential boundary SHALL remain the sole owner of PDU credential candidate resolution, successful credential index memory, request-scoped credential fallback authority, successful-index persistence, and the non-secret credential-context revision. Extracting PDU operation lifecycle into `PDUController` SHALL NOT create a second independent credential manager.

`PDUController` MAY consume focused application-owned callbacks or providers for obtaining an already resolved ordered candidate sequence, obtaining the valid starting successful candidate index, advancing a request-scoped candidate only after an approved structured authentication and operation-safety gate, committing a successful candidate only after an approved accepted success gate, and obtaining the current non-secret credential-context revision. The controller SHALL NOT parse credential-provider storage, maintain an independent successful-index store, wrap candidate iteration, or infer credential fallback from user-facing text, exception-message substrings, `auth`, `401`, `403`, an empty successful-outlet list, or absence of success.

Each PDU worker and handler SHALL continue to receive only one assigned credential for one attempt and SHALL NOT select or advance credential candidates. Transport fallback and credential fallback SHALL remain separate; all transport attempts belonging to one credential attempt SHALL use the same assigned credential.

Public PDU controller contexts, intents, signals, results, errors, logs, and status messages SHALL NOT contain credential values, credential dictionaries, profile secrets, cookies, Session IDs, CSRF tokens, handler/session objects, or transport objects. Candidate index alone SHALL NOT be freshness authority; non-secret credential-context revision SHALL participate in PDU context currentness.

PCS4i SHALL preserve its existing password-only and credentialless semantics through the controller boundary. The controller SHALL NOT invent a username, SHALL NOT turn the absence of an assigned credential into a confirmed credential rejection, and SHALL NOT persist a credential candidate as successful when the PCS4i operation completed without using that credential.

#### Scenario: Controller consumes application-owned candidate policy
- **WHEN** a PDU operation needs a credential attempt
- **THEN** `PDUController` obtains the resolved ordered candidates and valid starting index through the application-owned credential boundary
- **AND** it does not read provider storage or create a separate successful-credential memory

#### Scenario: Worker receives one assigned credential
- **WHEN** `PDUController` submits a PDU worker attempt for candidate N
- **THEN** that worker and its handler receive only candidate N
- **AND** neither the worker nor handler selects, advances, wraps to, or persists another candidate

#### Scenario: Structured authentication gate controls fallback
- **WHEN** a PDU attempt fails before any state-changing send could be delivered
- **AND** the structured outcome confirms device-side rejection of the assigned credential under the existing PDU contract
- **THEN** the controller may ask the application-owned credential policy to advance the request-scoped attempt
- **AND** generic error text containing `auth`, `401`, `403`, or similar substrings is not fallback authority

#### Scenario: Ambiguous individual mutation does not advance credentials
- **WHEN** an individual outlet mutation was sent, may have been delivered, or has an ambiguous outcome
- **THEN** `PDUController` does not request credential fallback
- **AND** the mutation is not automatically replayed with the same or another credential

#### Scenario: Bulk attempt keeps one credential
- **WHEN** a sequential PDU bulk attempt begins with an assigned credential
- **THEN** the same assigned credential is used for the whole attempt
- **AND** the bulk sequence is not restarted with another credential after any state-changing send was attempted or may have been delivered
- **AND** an empty `successful_outlets` list does not by itself authorize fallback

#### Scenario: Accepted success uses application-owned commit gate
- **WHEN** a current, non-stale PDU operation reaches an approved final success gate with a credential that was used according to the operation contract
- **THEN** `PDUController` may ask the application-owned credential boundary to persist that successful candidate index for the exact device/IP context
- **AND** the controller does not maintain a second successful-index store

#### Scenario: Stale or incomplete outcome cannot persist credential success
- **WHEN** a PDU result is stale, partial, failed, ambiguous, or otherwise outside the approved successful credential gate
- **THEN** `PDUController` does not request successful credential persistence from the application-owned credential boundary

#### Scenario: Credential revision invalidates same-index PDU context
- **GIVEN** a PDU operation context uses candidate index `0`
- **AND** credential configuration changes while the numeric candidate index remains `0`
- **WHEN** the application-owned credential boundary publishes a new non-secret credential-context revision
- **THEN** the old PDU operation context becomes stale
- **AND** candidate index equality alone does not make old callbacks current

#### Scenario: PCS4i credentialless operation remains credentialless
- **WHEN** existing PCS4i composition produces a credentialless attempt
- **THEN** `PDUController` submits that attempt without inventing a username or a credential candidate
- **AND** a later `CredentialRequired` outcome is not reclassified as confirmed rejection of an assigned credential

#### Scenario: PCS4i unused credential is not cached
- **WHEN** PCS4i was assigned a password candidate but completed successfully without requesting or using that password
- **THEN** `PDUController` does not request successful-index persistence for that unused candidate

### Requirement: PDU credential eligibility matrix preservation
PDU lifecycle extraction SHALL preserve the current per-model/per-operation credential fallback and successful-index persistence matrix. The extraction SHALL NOT introduce a generic credential retry or success-commit policy for all PDU operations merely because they are routed through `PDUController`.

For PDU refresh, fallback SHALL remain application-owned and allowed only after structured confirmed device credential rejection while the operation remains read-only/safe for a new credential attempt. Successful credential index SHALL be saved only after accepted final successful refresh for the exact device/IP and only when the assigned credential was actually used where the protocol contract requires it. PCS4i credentialless refresh success and assigned but unused password success SHALL NOT persist a credential index. HTTP outlet-name enrichment failure, including HTTP 401 or 403, SHALL NOT trigger credential fallback and SHALL NOT create an independent credential persistence decision.

For PCS4i individual ON/OFF, existing credential fallback SHALL remain allowed only after structured confirmed PCS4i Telnet credential rejection plus structured proof that no state-changing command send occurred or could have been delivered. After possible send, there SHALL be no fallback and no replay. Successful credential index MAY be committed only if the existing PCS4i success gate permits it and the assigned credential was actually used.

For Aten individual mutation, this structural change SHALL NOT make Aten individual outlet mutations credential-retry-eligible or credential-success-persisting unless that behavior already existed before this change.

For Aten bulk, one assigned credential SHALL be used for the whole attempt. Fallback MAY advance only after structured confirmed authentication rejection and structured execution state proving zero possible state-changing sends. Full accepted successful Aten bulk MAY persist the used assigned credential index according to the existing bulk contract. Partial, failed, ambiguous, or stale bulk outcomes SHALL NOT persist success.

For PCS4i bulk, one assigned credential SHALL be used for the whole attempt. Fallback MAY advance only after structured confirmed authentication rejection and structured execution state proving zero possible state-changing sends. Full accepted PCS4i bulk success MAY persist only when the assigned credential was actually used. Passwordless or assigned-but-unused bulk success SHALL NOT persist success. Partial, failed, ambiguous, or stale bulk outcomes SHALL NOT persist success.

#### Scenario: Refresh credential eligibility is unchanged
- **WHEN** a credential-bearing PDU refresh fails with structured confirmed device credential rejection while still read-only
- **THEN** application-owned policy may advance to the next candidate according to the existing refresh contract
- **AND** final successful refresh may persist only a credential that was actually used where required

#### Scenario: PCS4i refresh unused credential is not persisted
- **WHEN** PCS4i refresh completes successfully without requesting or using the assigned password
- **THEN** no successful credential index is persisted for that unused password candidate

#### Scenario: HTTP enrichment is not credential authority
- **WHEN** PCS4i HTTP outlet-name enrichment fails with HTTP 401, HTTP 403, timeout, or another read-only enrichment failure
- **THEN** no credential fallback starts from that HTTP failure
- **AND** no independent successful-index persistence decision is made from that enrichment outcome

#### Scenario: Aten individual mutation does not gain new fallback
- **WHEN** Aten individual mutation returns an authentication-looking or structured failure
- **THEN** lifecycle extraction does not introduce new credential fallback unless the pre-change production contract explicitly allowed it

#### Scenario: Aten individual mutation does not gain new success persistence
- **WHEN** Aten individual mutation completes successfully
- **THEN** lifecycle extraction does not newly persist successful credential index unless the pre-change production contract explicitly allowed it

#### Scenario: PCS4i individual pre-send rejection may still advance
- **WHEN** PCS4i individual mutation setup receives structured confirmed Telnet credential rejection before any state-changing send could have been delivered
- **THEN** the existing application-owned fallback allowance remains available

#### Scenario: PCS4i individual possible send blocks fallback
- **WHEN** PCS4i individual mutation command was sent, may have been delivered, or has an ambiguous outcome
- **THEN** no credential fallback occurs
- **AND** the command is not automatically replayed

#### Scenario: Aten bulk zero-send auth failure may advance
- **WHEN** Aten bulk fails with structured confirmed authentication rejection and structured execution state proves zero possible state-changing sends
- **THEN** existing bulk fallback may advance through application-owned policy

#### Scenario: Aten bulk full success may persist used credential
- **WHEN** Aten bulk completes with full accepted success using an assigned credential index
- **THEN** successful credential persistence remains allowed according to the existing bulk contract

#### Scenario: PCS4i bulk used credential may persist
- **WHEN** PCS4i bulk completes with full accepted success and the assigned password credential was actually used
- **THEN** successful credential persistence remains allowed according to the existing PCS4i bulk contract

#### Scenario: PCS4i bulk unused credential does not persist
- **WHEN** PCS4i bulk completes with full passwordless success or with an assigned but unused password
- **THEN** no successful credential index is persisted for that unused credential

#### Scenario: Incomplete bulk cannot persist credential
- **WHEN** Aten or PCS4i bulk ends partial, failed, ambiguous, or stale
- **THEN** no successful credential index is persisted from that bulk outcome
