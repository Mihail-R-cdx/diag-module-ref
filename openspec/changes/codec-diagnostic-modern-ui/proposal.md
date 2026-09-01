# Change: Modern codec diagnostic UI

## Why

The common room UI foundation and the dedicated Audio DSP and Matrix redesigns are already merged to `master`. The expanded codec row still uses the older generic field projection plus a separate call-log button, so it no longer matches the modern room visual hierarchy or the approved codec reference.

The codec redesign must cover every current exact codec registration with one deterministic room-mode layout while preserving the application-owned room interaction lifecycle. Existing standalone codec controls are not automatically room capabilities; any room audio control or reboot action must be admitted through the unified exact-model registry and the serialized exact-row lifecycle.

## What Changes

- Replace the expanded room-mode codec projection with one five-card dashboard for all current codec models:
  - `Состояние`;
  - `Вызов и презентация`;
  - `Аудио`;
  - `Журнал вызовов`;
  - `Действия`.
- Keep the reference field order and render unavailable values as `Нет данных` instead of hiding rows/cards.
- Make the baseline dark-theme expanded codec area approximately 90% consistent with the supplied reference in structure, relative card widths, labels, indicators, density and control placement; light theme preserves the same geometry.
- Reuse current accepted/live codec evidence for the microphone-level presentation. This change adds no new meter polling solely to fill the reference slot.
- Promote existing safe codec speaker/microphone control operations into room mode only through unified-registry-owned operation support and the existing serialized exact-row lifecycle. Unsupported operations remain visibly clickable and produce a local informational message without handler acquisition or device I/O.
- Automatically acquire call-log preview data when the current codec row is expanded, using the existing bounded `AUXILIARY_READ` lane. Show the three newest accepted entries; `Развернуть` opens the existing detailed call-log window.
- Map `Обновить статус` to the existing exact-row Local Refresh.
- Render `Перезагрузить устройство` as part of the common codec action card. A reboot may execute only if an exact registry binding and an already-approved safe typed operation exist; otherwise clicking the visible action reports that the operation is unsupported and performs no I/O.

## Current exact codec scope

The unified template applies to these current exact registrations, without creating a second runtime model list:

- `Huawei TE20`
- `Huawei TE40`
- `CloudLink Bar 310`
- `CloudLink Box 310`
- `Polycom RPG 310`

These names are acceptance/test oracles for the current `master` baseline. Runtime capability authority remains the unified exact-model registry.

## Non-goals

- Redesigning the common room shell, network card, accordion header, Audio DSP or Matrix dashboards.
- Adding family-specific codec layouts in this change.
- Adding new codec protocol commands merely to fill a visual slot.
- Making standalone `CodecScreen` widget state, model-name strings, handler type checks or duplicated support lists into room capability authority.
- Adding a second room interaction lane or bypassing existing credential, stale-operation, reconciliation, cleanup or Qt-thread safety contracts.
- Claiming a reboot capability for a model that has no existing approved typed reboot operation.

## Impact

Affected root capabilities after archive:

- `diagnostic-ui-presentation`
- `room-device-interaction-lifecycle`
- `device-diagnostics-and-control`

Implementation will touch the room codec presentation/composition path, registry-bound codec interaction capability declarations, call-log preview orchestration and regression tests. Production implementation is not part of this architecture commit.
