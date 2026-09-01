# Change: Modern codec diagnostic UI

## Why

The common room UI foundation and the dedicated Audio DSP and Matrix redesigns are already merged to `master`. The expanded codec row still uses the older generic field projection plus a separate call-log button, so it no longer matches the modern room visual hierarchy.

The codec redesign must cover every current exact codec registration with one deterministic room-mode layout while preserving the application-owned room interaction lifecycle. Existing standalone codec controls are not automatically room capabilities; any room audio control or reboot action must be admitted through the unified exact-model registry and the serialized exact-row lifecycle.

The supplied external screenshot remains product-design input only. The repository-local OpenSpec text is the complete normative visual acceptance contract, so implementation and independent validation do not depend on access to this conversation or an external image.

## What Changes

- Replace the expanded room-mode codec projection with one five-card dashboard for all current codec models:
  - `Состояние`;
  - `Вызов и презентация`;
  - `Аудио`;
  - `Журнал вызовов`;
  - `Действия`.
- Keep the fixed field order and render unavailable values as `Нет данных` instead of hiding rows/cards.
- Define repository-local baseline geometry, typography, indicator, call-log-row and control-placement ranges sufficient for independent visual review without the original screenshot.
- Reuse current accepted/live codec evidence for the microphone-level presentation. This change adds no new meter polling solely to fill the visual slot.
- Promote only the current baseline codec operations proven by approved source/contracts into room mode through unified-registry-owned operation support and the existing serialized exact-row lifecycle.
- Keep unsupported codec network capabilities unavailable while allowing the fixed common codec dashboard to retain local-only visual affordances that resolve before interaction admission and perform zero device I/O.
- Split normalized audio authority into numeric volume and typed mute state, with room-owned restore evidence for volume-zero speaker mute/unmute and no widget-local/default restore values.
- Automatically attempt one call-log preview per exact row/generation/expansion epoch through the existing bounded `AUXILIARY_READ` lane. A terminal ordinary failure completes that automatic attempt and cannot be retriggered by render/theme/resize events.
- Use the existing typed `CallHistorySnapshot` chronology authority: normalized records are newest-first by comparable `start_at`, with missing chronology after proven timestamps.
- Map `Обновить статус` to the existing exact-row Local Refresh.
- Render `Перезагрузить устройство` as part of the common codec action card. Current baseline reboot is unsupported for all five codecs; no reboot protocol is invented.

## Current exact codec scope

The unified template applies to these current exact registrations, without creating a second runtime model list:

- `Huawei TE20`
- `Huawei TE40`
- `CloudLink Bar 310`
- `CloudLink Box 310`
- `Polycom RPG 310`

These names and their operation matrix are acceptance/test oracles for the current `master` baseline. Runtime capability authority remains the unified exact-model registry.

## Non-goals

- Redesigning the common room shell, network card, accordion header, Audio DSP or Matrix dashboards.
- Adding family-specific codec layouts in this change.
- Adding new codec protocol commands merely to fill a visual slot.
- Making standalone `CodecScreen` widget state, model-name strings, handler type checks or duplicated support lists into room capability authority.
- Adding a second room interaction lane or bypassing existing credential, stale-operation, reconciliation, cleanup or Qt-thread safety contracts.
- Re-enabling CloudLink microphone-gain mutation.
- Fabricating speaker unmute restore targets such as `1`, minimum volume or another widget's remembered value.
- Claiming a reboot capability for a model that has no existing approved typed reboot operation.

## Impact

Affected root capabilities after archive:

- `diagnostic-ui-presentation`
- `room-device-interaction-lifecycle`
- `device-diagnostics-and-control`

The `device-diagnostics-and-control` delta intentionally MODIFIES the existing `Limited device control` and `Model-specific interactive codec session paths` requirements so fixed local-only unsupported codec affordances do not contradict the root capability contract while CloudLink microphone-gain network I/O remains prohibited.

Implementation will touch the room codec presentation/composition path, registry-bound codec interaction capability declarations, normalized audio projection, call-log preview orchestration and regression tests. Production implementation is not part of this architecture commit.
