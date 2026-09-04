# diagnostic-application-shell Delta

## ADDED Requirements

### Requirement: Modern operator toolbar does not expose the legacy global Debug control

The legacy global `Отладка` control SHALL NOT be visible as an operator toolbar control in the modern diagnostic interface. Its internal legacy implementation MAY remain for compatibility, but it is hidden from the visible toolbar.

This is a presentation-only visibility decision. It SHALL NOT change target authority, perform device I/O, choose credentials, acquire a handler/session, create a lifecycle/generation, or replace approved exact-row Debug presentation for individual device families. Theme, search, Password and top full Refresh semantics remain unchanged.

#### Scenario: Modern toolbar is rendered

- **WHEN** the modern diagnostic operator toolbar is rendered
- **THEN** no visible global `Отладка` control is present
- **AND** target-search, Password, top full Refresh and theme controls retain their existing semantics

#### Scenario: Family Debug remains independent

- **GIVEN** a device family has approved exact-row Debug presentation
- **WHEN** its current row/dashboard is rendered
- **THEN** the hidden global toolbar control does not replace or alter that family-specific Debug contract
