## ADDED Requirements

### Requirement: DMP polling controller composition boundary

`VCSDiagnosticApp` SHALL compose a DMP-specific polling controller as the application lifecycle boundary for Extron DMP 64 Plus meter diagnostics.

The main window SHALL retain global input validation, generic request composition, credential-provider ownership, successful credential memory, global UI state helpers, and rendering integration. It SHALL delegate DMP polling generation, cancellation publication, worker submission/binding, stale callback authority, DMP credential-attempt coordination, first-complete-snapshot success gating, and DMP shutdown/invalidation to the DMP controller.

`AudioDSPScreen` SHALL remain the rendering boundary for accepted DMP data. It SHALL NOT own DMP worker creation, cancellation authority, credential candidate selection, credential fallback, successful credential persistence, handler/session ownership, or stale callback decisions.

The DMP controller SHALL receive only the focused application callbacks/providers required to obtain public model/IP/request context and application-owned credential policy decisions. It SHALL NOT become a generic shell replacement or a generic device lifecycle manager.

#### Scenario: MainWindow routes DMP refresh to the controller
- **WHEN** global refresh validation and generic request setup succeed for `Extron DMP 64 Plus`
- **THEN** `VCSDiagnosticApp` delegates DMP polling startup to the DMP controller
- **AND** it does not directly construct and bind the authoritative DMP worker lifecycle

#### Scenario: MainWindow delegates DMP invalidation
- **WHEN** model, IP, DMP credential context, repeat Refresh, relevant screen lifecycle, or application shutdown supersedes the active DMP context
- **THEN** the shell delegates DMP invalidation/cancellation to the controller
- **AND** it does not maintain a second independent DMP generation authority

#### Scenario: Generic shell callbacks contain no DMP stale policy
- **WHEN** DMP lifecycle extraction is complete
- **THEN** generic device result, error, progress, status, and finished handlers receive only DMP callbacks already accepted by the DMP controller
- **AND** they do not independently evaluate DMP-specific worker context freshness

#### Scenario: Generic shell error handling does not retry DMP credentials
- **WHEN** a DMP worker reports a failure
- **THEN** DMP retry eligibility and candidate advancement are decided at the DMP controller/application credential boundary
- **AND** generic device-error dispatch does not independently restart DMP polling with another candidate

#### Scenario: AudioDSPScreen remains rendering-only for DMP lifecycle
- **WHEN** the DMP controller accepts a current meter snapshot
- **THEN** `AudioDSPScreen` renders the accepted DMP data
- **AND** it does not decide whether the worker/context is current or manage DMP credentials/sessions