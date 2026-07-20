## ADDED Requirements

### Requirement: PDU controller credential policy delegation
The existing application/composition credential boundary SHALL remain the sole
owner of PDU credential candidate resolution, successful credential index
memory, request-scoped credential fallback authority, successful-index
persistence, and the non-secret credential-context revision. Extracting PDU
operation lifecycle into `PDUController` SHALL NOT create a second independent
credential manager.

`PDUController` MAY consume focused application-owned callbacks or providers for
obtaining an already resolved ordered candidate sequence, obtaining the valid
starting successful candidate index, advancing a request-scoped candidate only
after an approved structured authentication and operation-safety gate,
committing a successful candidate only after an approved accepted success gate,
and obtaining the current non-secret credential-context revision. The
controller SHALL NOT parse credential-provider storage, maintain an independent
successful-index store, wrap candidate iteration, or infer credential fallback
from user-facing text, exception-message substrings, `auth`, `401`, `403`, an
empty successful-outlet list, or absence of success.

Each PDU worker and handler SHALL continue to receive only one assigned
credential for one attempt and SHALL NOT select or advance credential
candidates. Transport fallback and credential fallback SHALL remain separate;
all transport attempts belonging to one credential attempt SHALL use the same
assigned credential.

Public PDU controller contexts, intents, signals, results, errors, logs, and
status messages SHALL NOT contain credential values, credential dictionaries,
profile secrets, cookies, Session IDs, CSRF tokens, handler/session objects, or
transport objects.

PCS4i SHALL preserve its existing password-only and credentialless semantics
through the controller boundary. The controller SHALL NOT invent a username,
SHALL NOT turn the absence of an assigned credential into a confirmed credential
rejection, and SHALL NOT persist a credential candidate as successful when the
PCS4i operation completed without using that credential.

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
- **WHEN** a current, non-stale PDU operation reaches an existing approved final success gate with a credential that was used according to the operation contract
- **THEN** `PDUController` may ask the application-owned credential boundary to persist that successful candidate index for the exact device/IP context
- **AND** the controller does not maintain a second successful-index store

#### Scenario: Stale or incomplete outcome cannot persist credential success
- **WHEN** a PDU result is stale, partial, failed, ambiguous, or otherwise outside the existing successful credential gate
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
