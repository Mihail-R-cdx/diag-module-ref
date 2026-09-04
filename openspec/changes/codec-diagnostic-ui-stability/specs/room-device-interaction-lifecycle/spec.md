# room-device-interaction-lifecycle Delta

## MODIFIED Requirements

### Requirement: Debug is local exact-row presentation

The current `Отладка` action in room mode SHALL be bound to the exact current expanded supported row only on device-family presentations that explicitly retain the approved Debug affordance. Opening or closing Debug SHALL NOT by itself create device network I/O, stop live, select credentials, or acquire a handler/session.

When no supported row with an approved visible Debug affordance is current, Debug SHALL be unavailable. Switching/collapsing the row SHALL close/invalidate the row-specific Debug presentation so logs cannot be attributed to another record. Any future Debug sub-action that performs device I/O SHALL explicitly enter an approved auxiliary-read or state-changing lifecycle; this change SHALL NOT create an arbitrary network command console.

The modern expanded **codec** dashboard intentionally exposes no local `Отладка` affordance. The modern expanded **PDU** dashboard continues to expose no local `Отладка` affordance. These are presentation-visibility exceptions only: they do not delete accumulated logs, change codec/PDU network capability, create alternate Debug paths, authorize hidden direct commands, or alter approved exact-row Debug controls for other device families.

For another device family whose approved presentation retains Debug, the action remains local exact-row presentation and remains outside the serialized network lane because it performs no device I/O.

#### Scenario: Modern codec row omits local Debug

- **WHEN** a current supported codec row is expanded in the modern five-card dashboard
- **THEN** no local `Отладка` control is visible
- **AND** no Debug network capability or alternate lifecycle is created
- **AND** removal of the affordance does not delete internal accumulated logs

#### Scenario: Modern PDU row omits local Debug

- **WHEN** a current supported PDU row is expanded in the modern dashboard
- **THEN** no local `Отладка` control is visible
- **AND** no Debug network capability or alternate lifecycle is created

#### Scenario: Another approved device family retains Debug

- **GIVEN** a current expanded supported non-codec/non-PDU row has an approved visible Debug presentation
- **WHEN** the operator opens Debug
- **THEN** Debug shows that exact row's local accumulated log/terminal state
- **AND** opening it creates no device I/O, credential/session acquisition, or change to row authority
- **AND** active live may continue because local Debug creates no network lifecycle

## ADDED Requirements

### Requirement: Codec Local Refresh publishes one typed terminal outcome to presentation

The modern codec `Обновить статус` action SHALL remain only an alias of the existing exact-row `LOCAL_REFRESH` intent and SHALL NOT create a codec-specific refresh controller, second network owner, direct widget-to-handler dispatch, or second credential/retry authority.

For presentation purposes, Local Refresh completion SHALL be classified only after the application lifecycle checks exact row/generation/currentness. Semantics SHALL be equivalent to:

```text
ACCEPTED_SUCCESS
ACCEPTED_TERMINAL_FAILURE
STALE_OR_SUPERSEDED
CANCELLED
```

`ACCEPTED_SUCCESS` SHALL atomically publish the accepted exact-row usable snapshot according to the existing Local Refresh contract and SHALL NOT produce an error modal merely because a lower-level worker emitted an intermediate/final callback.

`ACCEPTED_TERMINAL_FAILURE` SHALL follow the existing terminal Local Refresh row transition (`не удалось подключиться`, blocked row network actions, top full Refresh required). At most one current non-secret user-facing error presentation MAY be emitted for that accepted operation; presentation SHALL NOT independently display the same lower-level failure a second time.

`STALE_OR_SUPERSEDED` and `CANCELLED` SHALL mutate no current row cache/state and SHALL produce no current-row error modal/dialog. A late lower-level callback from such an operation SHALL remain stale and silent for replacement presentation.

Presentation SHALL NOT parse public error strings to reclassify these outcomes. Structured application failure/currentness authority remains decisive.

#### Scenario: Codec Local Refresh succeeds

- **GIVEN** `Обновить статус` starts the existing Local Refresh for the current connected codec row
- **WHEN** current application authority accepts a usable result
- **THEN** that exact row cache is atomically replaced
- **AND** no error modal is shown for the successful operation
- **AND** eligible live may resume only under the existing cleanup/currentness rules

#### Scenario: Codec Local Refresh terminal failure is presented once

- **WHEN** the current exact codec Local Refresh reaches accepted terminal failure
- **THEN** the existing row failure/blocking contract applies
- **AND** at most one non-secret current-operation error presentation is emitted
- **AND** no presentation-owned duplicate failure path exists

#### Scenario: Old codec Local Refresh completes after supersession

- **GIVEN** Local Refresh for row/generation A loses authority before completion
- **WHEN** its result or error arrives after row/generation B is current
- **THEN** A does not update B or the current room cache
- **AND** no error modal for A is shown as a current-row failure

### Requirement: Codec audio controls derive pending and terminal state only from the common mutation lifecycle

For modern room codec speaker-volume `−`/`+` controls, an exact-model supported click SHALL enter only the existing exact-row `MUTATION` -> mandatory `RECONCILIATION` lifecycle. Presentation SHALL NOT own a parallel network operation, pending timer, retry owner, credential fallback, or authoritative pending flag whose lifetime can outlive/disagree with the common room interaction lane.

Before interaction admission, unified exact-model capability authority SHALL resolve support. An unsupported codec audio affordance SHALL use the approved local-only informational path and SHALL perform zero LIVE invalidation, handler/session acquisition, credential selection, mutation generation, or device I/O.

For admitted supported mutation, the common room lifecycle lock state SHALL be the source of button busy/disabled state. A send/ACK alone SHALL NOT make the operation successful or accepted volume current. Only accepted reconciliation may publish final current speaker state/percentage and release normal controls for the same still-current usable row.

If command execution may have been delivered, its outcome is ambiguous, reconciliation fails/times out, or final state cannot be confirmed, the existing blocked/unconfirmed mutation contract SHALL apply. Presentation SHALL NOT clear the state by blind resend, local timeout, optimistic percentage, or direct status request outside the reconciliation owner.

A stale/superseded mutation/reconciliation completion SHALL NOT re-enable controls for a replacement exact row, overwrite replacement percentage, display success for the new row, or start a retry.

#### Scenario: Supported speaker adjustment reconciles successfully

- **GIVEN** the current exact codec registration supports the requested speaker adjustment
- **WHEN** the existing mutation lifecycle sends one operation and reconciliation accepts final exact-row state
- **THEN** the accepted current speaker state/percentage may update
- **AND** common lifecycle authority releases the controls when the same row remains eligible
- **AND** no independent presentation pending timer must be cleared

#### Scenario: Speaker mutation result is ambiguous

- **WHEN** a speaker mutation may have been delivered but final state cannot be authoritatively reconciled
- **THEN** the row follows the existing blocked/unconfirmed mutation contract
- **AND** the GUI does not blindly resend or optimistically accept the requested percentage

#### Scenario: Unsupported speaker action remains local

- **GIVEN** unified exact-model registration marks a speaker operation unsupported
- **WHEN** its common visible affordance is activated while otherwise eligible
- **THEN** the approved local informational result is shown
- **AND** no room network lifecycle starts
