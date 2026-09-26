## ADDED Requirements

### Requirement: Unified dispatch publishes exact IN1808 Audio capability without changing its screen identity

The unified diagnostic registry SHALL keep canonical `Extron IN1808` on the
existing `matrix` screen and Matrix lifecycle while explicitly publishing
whether the exact model supports the new IN1808 Audio room capability.

The room GUI SHALL consume this application-owned capability. It SHALL NOT
derive Audio support from `screen_key == "matrix"`, a model substring,
handler class, current widget type, or the presence of meter/name fields.

The capability SHALL remain absent for IN1804, IN1806, IN1608 xi and the
supported DTP CrossPoint models under this change.

#### Scenario: Exact IN1808 dispatch exposes Audio mode

- **GIVEN** canonical inventory/application resolution selects exact
  `Extron IN1808`
- **WHEN** unified diagnostic capability is composed
- **THEN** the existing `matrix` screen/lifecycle remains selected
- **AND** the exact IN1808 Audio room capability is available
- **AND** no second top-level screen registration is created

#### Scenario: Other Matrix device remains video-only for this capability

- **GIVEN** unified dispatch selects another currently supported exact Matrix model
- **WHEN** room capability is composed
- **THEN** the IN1808 Audio capability is unavailable
- **AND** presentation cannot promote it from family similarity
