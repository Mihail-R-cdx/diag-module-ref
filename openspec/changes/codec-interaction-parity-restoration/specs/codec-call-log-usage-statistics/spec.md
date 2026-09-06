## ADDED Requirements

### Requirement: Explicit codec call-log acquisition remains independent from automatic preview

For each supported exact codec model, explicitly opening the call log SHALL always start the approved fresh model-specific read-only acquisition for that exact current row, regardless of whether automatic dashboard preview is empty, deferred, stale, or previously failed.

Automatic preview is presentation enrichment and SHALL NOT become a prerequisite, cache authority, or failure gate for the explicit journal. The implementation SHOULD reuse the proven model-specific retrieval/normalization behavior that existed before `codec-diagnostic-modern-ui` where current device evidence confirms it remains valid.

An ordinary automatic-preview failure SHALL NOT permanently disable explicit journal opening, degrade an otherwise connected row, or strand the serialized room lane. An explicit journal failure SHALL follow existing typed auxiliary-failure rules and bounded cleanup.

#### Scenario: Automatic preview is unavailable

- **GIVEN** the codec dashboard has no automatic preview data
- **WHEN** the operator presses the explicit journal/expand action
- **THEN** a fresh exact-row call-log acquisition starts through the approved model-specific retrieval path
- **AND** missing preview data does not block the request

#### Scenario: Automatic preview failed earlier

- **GIVEN** a previous automatic preview attempt failed without proving connection/session loss
- **WHEN** the same connected exact row remains current and the operator explicitly opens the journal
- **THEN** the explicit acquisition is still available
- **AND** it is not satisfied from the failed preview attempt
- **AND** its result may populate the dialog normally
