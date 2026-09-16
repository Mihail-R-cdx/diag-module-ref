## ADDED Requirements

### Requirement: Target-search visual label describes room and equipment IP input

The sole existing target-search `QLineEdit` SHALL have the visible label exactly `Введите название помещения или IP-адрес оборудования`. It remains the same one field for partial room-name search, IPv4 input, autocomplete, explicit selection, and top Refresh; no second input or model selector is introduced. Existing raw-query, selected-room, inventory-resolution, diagnostic-start, and Refresh authority remains unchanged. Placeholder and accessibility text MAY remain where they do not conflict with this visible-label contract. Rendering the label and field starts zero new I/O.

#### Scenario: Target search uses the descriptive visible label

- **WHEN** the main diagnostic window is constructed
- **THEN** the one persistent target-search field has visible label `Введите название помещения или IP-адрес оборудования`
- **AND** no visible field label exactly `IP-адрес` remains
- **AND** partial room-name search, IPv4 input, autocomplete, explicit selection, and top Refresh retain their existing behavior and authority
- **AND** constructing or rendering the label starts zero new I/O
