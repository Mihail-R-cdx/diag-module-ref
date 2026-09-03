# Design: Modern PDU diagnostic UI

## Context

The room-oriented diagnostic shell, Audio DSP dashboard, Matrix dashboard and codec dashboard are already current `master` architecture/implementation. PDU is the remaining expanded device-family surface to receive its dedicated modern visual contract.

Current PDU architecture is already split correctly:

- the exact current room row is target authority;
- application/composition owns credential choice and fallback;
- one serialized room interaction lane owns `LOCAL_REFRESH`, `MUTATION` and `RECONCILIATION`;
- supported PDU mutations are executed by background PDU operations and require the approved reconciliation policy;
- Aten currently supports refresh, individual ON/OFF/REBOOT and bulk ON/OFF;
- PCS4i currently supports refresh, individual ON/OFF and bulk ON/OFF but not reboot;
- room-mode PDU no longer owns related-codec lookup/session/meter behavior.

This change therefore does not redesign PDU networking. It redesigns the room-mode projection and maps every visible network-capable control back to the already-approved application intents.

## Goals

1. Produce a common expanded PDU dashboard whose layout is approximately 90% faithful to the supplied PDU reference in the expanded PDU area only.
2. Keep implementation/review independent of the external screenshot by defining geometry, field order, labels, indicators and acceptance checkpoints in repository-local OpenSpec.
3. Preserve current supported Aten/PCS4i refresh and mutation behavior through existing application ownership.
4. Keep fixed common affordances visually stable when a model does not support a particular command, while resolving unsupported clicks locally before network interaction.
5. Add no new telemetry solely to fill visual placeholders.

## Non-goals

The common room shell, room/network summary cards, target-search, non-PDU device families, protocol handlers, credential semantics and mutation policy are not redesigned here. The screenshot outside the expanded PDU region has no normative effect.

The one intentional common-shell exception is narrowly limited to the **current expanded PDU row header**: the shared accordion-header requirement is explicitly modified so that this row alone may append one far-right Local Refresh affordance. Collapsed PDU rows and every non-PDU row retain the common no-right-action header contract.

## Decision 1: One common two-card PDU dashboard

The current expanded PDU row uses one family template for every supported exact PDU registration. The baseline body is horizontally divided into:

```text
Основная информация | Управление розетками
```

Target relative weights at `1440 x 900` are `22:78`, with approximately ±4 percentage points of Qt/layout tuning permitted. The left card is intentionally narrow and informational; the right card dominates because the outlet table/actions are the primary PDU task.

Both cards use the shared room card border/radius/palette and align their top and bottom edges at baseline. Expected baseline body height is approximately `350-410 px`; controlled vertical scrolling is acceptable when current outlet count or available window height requires it.

Dark theme is baseline. Light theme changes palette only, not information hierarchy or geometry.

## Decision 2: `Основная информация` has exactly three rows

The card permanently renders, in order:

```text
Модель
Серийный номер
MAC-адрес
```

Authority is deliberately conservative:

- `Модель` uses exact current row/application model identity rather than inferring from arbitrary handler/display text;
- `Серийный номер` uses current exact canonical room-record `serial_number` where usable;
- `MAC-адрес` uses current exact canonical room-record `mac_address` where usable.

A current accepted PDU projection may carry equivalent exact-record evidence for presentation, but the view must not create a new competing authority. Missing/unusable serial or MAC renders `—`.

No PDU device request is added for these three visual slots. The card does not render IP, firmware, switch connection, device state, input power, temperature, humidity or overload rows in this redesign.

## Decision 3: Outlet table is fixed to five columns

The `Управление розетками` card has a top action strip followed by this exact table order:

```text
Розетка | Имя розетки | Состояние | Текущая мощность | Действия
```

Target column weights are approximately:

```text
Розетка             9
Имя розетки         24
Состояние           16
Текущая мощность    18
Действия            33
```

Each column may tune by roughly ±3 percentage points as long as labels and action buttons remain readable and the same hierarchy is preserved.

Outlet records are sorted numerically ascending by authoritative outlet number. The baseline screenshot/acceptance fixture uses eight outlets. More rows remain reachable through a vertical scrolling region rather than shrinking rows below the approved density or reordering them.

## Decision 4: Power stays a visual placeholder

Current approved PDU paths do not provide authoritative per-outlet current power. This change does not add a polling endpoint, handler method, worker, timer or network request to populate the column.

Every current `Текущая мощность` cell therefore displays `—`.

A later reviewed change may define authoritative power telemetry. When such data exists, user-facing power uses `Вт`; this future unit decision does not authorize fabricated zero values such as `0 Вт` today.

## Decision 5: Status and action semantics are explicit and non-color-only

Outlet state presentation is:

```text
confirmed ON     -> green semantic dot + `ON`
confirmed OFF    -> red semantic dot + `OFF`
unknown/unusable -> neutral cue + `—`
```

Color reinforces but never replaces text/accessibility meaning.

The `Действия` cell always preserves the visual order:

```text
Вкл | Выкл | Перезапуск
```

`Вкл` uses green semantic styling, `Выкл` red/destructive semantic styling, and `Перезапуск` neutral/secondary styling. Presentation state is not device authority.

## Decision 6: Fixed affordance does not equal supported network capability

The common PDU dashboard intentionally keeps the same action anatomy across models. Support is resolved from existing exact PDU capability authority before room interaction admission.

Supported operation:

```text
visible control
-> safe exact-row application intent
-> existing serialized room interaction lifecycle
-> existing PDU worker/controller path
-> mandatory reconciliation where state changing
```

Unsupported operation:

```text
visible fixed affordance
-> capability check before room interaction admission
-> local informational popup `Команда не поддерживается`
-> zero LIVE invalidation
-> zero credential selection
-> zero handler/session acquisition
-> zero mutation generation
-> zero device I/O
```

This is particularly important for PCS4i: `Перезапуск` remains visible because it is part of the common layout, but PCS4i reboot remains network-unsupported. No bulk reboot control exists.

Programmatic unsupported operations remain fail-closed under the existing core capability checks even if no GUI affordance is involved.

## Decision 7: The common header gets one narrow PDU-only exception and exactly two refresh entry points remain

The foundation accordion header remains the default authority for every row:

```text
chevron -> device icon -> model -> status -> IP
```

Every non-PDU row and every **collapsed** PDU row retains that common no-right-action contract.

Only while a supported PDU row is the **current expanded exact row**, its header appends one small Refresh icon at the far right. This is an explicit modification of the common accordion-header requirement rather than an additional contradictory family rule. There is no kebab menu and no additional right-side collapse button; the common left accordion chevron remains the only expand/collapse affordance. The header Refresh does not collapse/re-expand the row, change current selection or derive a target from displayed text.

The outlet card contains the second refresh entry point, `Обновить статус`.

The modern PDU dashboard removes the previous generic expanded-content `Локальный опрос`/legacy Local Refresh affordance. It must not survive as a third refresh control.

Therefore the complete visible refresh set for an expanded PDU is exactly:

```text
header Refresh icon -------\
                            -> same exact-row LOCAL_REFRESH
Обновить статус -----------/
```

Both controls share eligibility, lock state, cancellation/currentness, stale-result rejection and result handling. Neither creates a second PDU refresh lane or generation, and neither directly acquires a handler or performs I/O. Rendering/theme/hover does not start refresh.

Collapsing the PDU row removes the family header Refresh and leaves the ordinary common collapsed header.

## Decision 8: Bulk actions reuse current sequential policy

`Включить всё` and `Выключить всё` reuse current application-owned bulk PDU semantics, including deterministic outlet sequence, supported individual capability prerequisite, state-changing safety, currentness checks and existing terminal/partial-completion handling.

The dashboard does not implement bulk operations by clicking individual Qt buttons in a loop and does not own timing/retry policy.

## Decision 9: Existing mutation/reconciliation stays authoritative

Individual `Вкл`, `Выкл`, supported `Перезапуск`, and bulk actions continue to use the existing state-changing lifecycle. A visual button press/ACK never updates accepted outlet state directly. Only current accepted mandatory reconciliation may atomically replace the exact PDU row cache.

Ambiguous mutation result remains blocked/unconfirmed under the existing room lifecycle. This change does not make repeated clicking or alternate credentials a retry policy.

## Decision 10: 90% visual target is repository-local and measurable

Independent validation does not require the original screenshot. The PDU presentation spec defines ten visual checkpoints. Mandatory structural/semantic checkpoints must all pass, and at least 9 of 10 total checkpoints must pass at `1440 x 900` in dark theme. Light theme must preserve the same geometry and state semantics.

Pixel-perfect font rasterization, one-pixel antialiasing differences and platform-specific icon glyph rasterization are not failures if the contract ranges/checkpoints pass.

## Implementation boundaries

Likely production touch points include the current room-mode PDU view/composition and the common equipment-row header presentation needed for the single expanded-PDU Refresh exception, plus shared theme styles. Existing `PDUController`, `core.pdu` operation policy and handler transports should be reused rather than copied into a new presentation-specific controller. Minimal refactoring is allowed only where needed to expose safe presentation data/intents without changing ownership.

Implementation must explicitly remove/suppress the old generic room expanded-content `Локальный опрос` for the modern PDU surface so that exactly two refresh entry points remain. It must not alter common header behavior for non-PDU rows or collapsed PDU rows.

Tests must prove that the redesigned dashboard does not accidentally restore legacy PDU-hosted codec enrichment, create a new network lane, add power reads, retain a third generic refresh, or promote PCS4i reboot support.

## Validation strategy

Implementation validation must include focused PDU presentation/controller/operation tests, affected room interaction/theme tests, the full offline suite, repository-local strict OpenSpec validation and Git whitespace checks. Manual visual validation uses an eight-outlet Aten fixture at `1440 x 900` in dark and light themes and records the ten PDU checkpoints in the implementation report; screenshots remain local by default.
