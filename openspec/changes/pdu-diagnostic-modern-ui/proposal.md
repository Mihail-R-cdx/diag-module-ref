# Change: Modern PDU diagnostic UI

## Why

The common room UI foundation and the dedicated Audio DSP, Matrix and codec redesigns are already merged to `master`. The expanded room-mode PDU surface still uses the older generic information/table arrangement, so it is now the remaining device-family presentation that does not match the approved modern room visual hierarchy.

The supplied external screenshot is product-design input only for the area opened by expanding a PDU row. The rest of that screenshot is explicitly out of scope. Implementation and independent validation SHALL be possible from repository-local OpenSpec text without requiring access to the original conversation image.

The redesign must remain a presentation/application-intent change. Existing application-owned PDU refresh, credential, mutation, reconciliation, stale-operation and Qt-thread-safety contracts already provide the correct network behavior and SHALL remain authoritative.

## What Changes

- Replace the expanded room-mode PDU content with one common two-card dashboard for current supported PDU models. Current-baseline acceptance oracles are `Aten PE8208AV` and `Extron IPL T PCS4i`; runtime support remains owned by the existing exact application/PDU capability authority.
- Keep the common accordion header semantics, but when the PDU row is expanded place exactly one PDU local-refresh icon at the far right. Do not add a kebab/overflow menu or a second right-side collapse control.
- Render the left card as `Основная информация` with exactly three permanent rows in this order: `Модель`, `Серийный номер`, `MAC-адрес`. Values come from the exact current room record/accepted PDU context; unavailable serial/MAC evidence renders `—`. No new PDU protocol read is added to fill these fields.
- Render the right card as `Управление розетками` with top actions `Обновить статус`, `Включить всё`, `Выключить всё` and a five-column outlet table: `Розетка`, `Имя розетки`, `Состояние`, `Текущая мощность`, `Действия`.
- Keep `Текущая мощность` as a permanent visual column but render `—` in this change because no authoritative power reading exists in the current PDU path. A later reviewed change may populate the column; its user-facing unit shall be `Вт`.
- Keep outlet rows in deterministic ascending outlet-number order. The baseline visual acceptance uses eight outlets; the layout must support arbitrary current outlet counts through controlled vertical scrolling.
- Keep per-outlet `Вкл`, `Выкл`, `Перезапуск` controls visible in one `Действия` cell. Supported operations call the already-approved existing PDU application logic. An operation unsupported for the exact PDU model resolves locally to an informational popup equivalent to `Команда не поддерживается` before room interaction admission and performs zero device I/O.
- Keep bulk `Включить всё` / `Выключить всё` connected to the existing bulk PDU logic when supported. Unsupported fixed affordances follow the same local zero-I/O behavior; no bulk reboot control is introduced.
- Make the PDU header refresh icon and `Обновить статус` strict aliases of the same existing exact-row `LOCAL_REFRESH` lifecycle; this change creates no second refresh owner or lane.
- Preserve the approved visual semantics: connected/ON green reinforcement, OFF red reinforcement, explicit non-color text, green `Вкл`, red `Выкл`, neutral `Перезапуск`, shared card language, and identical geometry in dark/light themes.
- Define measurable repository-local visual checkpoints sufficient to enforce the product target of approximately 90% correspondence in layout, fields, labels, indicators and controls without treating pixel-level rasterization as normative.

## Current exact PDU scope

The common room-mode layout applies to these current supported exact models:

- `Aten PE8208AV`
- `Extron IPL T PCS4i`

The current operation matrix is an acceptance/test oracle only. Runtime capability authority remains the existing application/PDU capability binding and SHALL NOT be replaced with a second model list.

## Non-goals

- Redesigning the common room shell, target-search, room/network cards, common accordion geometry, Audio DSP, Matrix or codec expanded dashboards.
- Redesigning the legacy/standalone PDU screen as an independent product surface unless minimal shared-widget refactoring is required to preserve current behavior.
- Adding a new PDU model or protocol transport.
- Adding device reads for outlet power, serial number, MAC address, temperature, humidity, overload or other fields merely to reproduce screenshot content.
- Adding device status/power/temperature/humidity/overload rows to `Основная информация`.
- Adding PDU network operations that are not already approved for the exact model.
- Making `Extron IPL T PCS4i` reboot a supported network operation; its fixed `Перезапуск` affordance remains local-only unsupported presentation.
- Adding bulk reboot.
- Bypassing application-owned credential selection, exact-row authority, the serialized room interaction lane, mutation confirmation/reconciliation, stale checks, cleanup or GUI-thread isolation.
- Making widget state authoritative for outlets, capabilities, credentials, request generations or reconciled device state.

## Impact

Affected root capabilities after archive:

- `diagnostic-ui-presentation`
- `device-diagnostics-and-control`
- `room-device-interaction-lifecycle`

`device-diagnostics-and-control` intentionally MODIFIES `Limited device control` so the fixed common PDU dashboard may keep a visible unsupported model-specific affordance only as a local pre-admission informational action. This does not promote unsupported network capability.

Implementation is expected to touch the room-mode PDU presentation/composition path, existing PDU signal/controller wiring as needed, theme styling and regression tests. Production implementation is not part of this architecture commit.
