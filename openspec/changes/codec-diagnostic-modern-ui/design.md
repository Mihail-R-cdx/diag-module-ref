# Design: Modern codec diagnostic UI

## Context

Current `master` already contains the common modern room foundation and the dedicated Audio DSP and Matrix room dashboards. The current codec branch of `RoomReadOnlyPresentation` is still a flat generic field projection with `Локальный опрос`, `Журнал звонков` and Debug controls above it.

The unified exact application registry currently owns the five codec registrations and already declares room Local Refresh and call-log auxiliary bindings for all five; CloudLink Bar/Box also declare their existing room live binding. Standalone `CodecScreen` already has safe typed interactive operations for speaker/microphone reads and desired-state changes, but standalone capabilities are not room capabilities merely because the same model is displayed there.

This change therefore has two coupled responsibilities:

1. a codec-family presentation redesign inside the expanded exact room row; and
2. explicit registry/lifecycle promotion of only the already-proven safe codec interactions needed by that new room presentation.

The supplied screenshot is normative only for the expanded codec area. The common room header, search, network card, other equipment rows and footer are outside the visual reference for this change.

## Goals

- One shared codec dashboard for all five current exact codec registrations.
- About 90% visual correspondence at the existing `1440 x 900` baseline to the supplied codec-expanded reference by structure, order, relative proportions, density, field names, indicators and control placement.
- Missing model-specific data remains explicit as `Нет данных` without layout collapse.
- Existing room exact-row authority, credential ownership, stale protection, single serialized network lane and Qt-thread safety remain unchanged.
- Call-log preview appears automatically after safe acquisition for the current expanded codec row.
- Existing safe audio controls become room interactions without direct calls from the presentation to handlers/sessions.

## Non-goals

- Pixel-perfect reproduction of font rasterization or every source-image spacing value.
- Family-specific codec dashboards.
- New protocol commands solely to populate absent reference fields.
- A new generic reboot protocol.
- Parallel codec support tables outside the unified exact-model registry.
- Concurrent LIVE and AUXILIARY/MUTATION ownership.
- Optimistic device state after mutation.
- Changes to the outer room shell or other device-family dashboards.

## Decision 1: one five-card codec dashboard

At baseline size the expanded codec content SHALL render one horizontal dashboard in this exact order:

```text
Состояние | Вызов и презентация | Аудио | Журнал вызовов | Действия
```

The accepted target width weights are approximately:

```text
Состояние              23
Вызов и презентация    17
Аудио                  18
Журнал вызовов         25
Действия               17
```

Implementation MAY tune each share by about four percentage points to accommodate Qt metrics while preserving the same visual hierarchy: call-log/state remain substantial, Audio remains compact, and Actions remains the narrow right card. Cards have aligned tops and approximately one visual height at baseline. At the existing minimum supported room window, controlled reflow/scrolling is permitted, but card order and all controls/data slots remain reachable.

Dark theme is the reference acceptance theme. Light theme SHALL keep the same layout geometry and use the shared theme semantic styling rather than a separate layout.

### `Состояние`

Rows are permanent and appear in this order:

1. `Модель`
2. `MAC-адрес`
3. `Серийный номер`
4. `Платформа`
5. `Версия ПО`
6. `Микрофон`
7. `Камера`

Each absent/unusable current value renders `Нет данных`. The card does not disappear or shrink based on model family.

### `Вызов и презентация`

Permanent rows, in order:

1. `Статус звонка`
2. `Презентация`
3. `Регистрация SIP/H.323`

Missing/unusable values render `Нет данных`. Registration and other statuses may use semantic indicators, but textual/accessibility meaning remains available and color is never the only cue.

### `Аудио`

The card contains:

- `Микрофон (уровень)` horizontal current-level indicator;
- `Громкость микрофона` value plus `−`, `+`, mute control;
- `Громкость динамиков` value plus `−`, `+`, mute control.

The layout is uniform across codec models. A missing level/value renders `Нет данных`; the control positions remain present.

The microphone level consumes only current accepted/live evidence already produced by the model's approved codec lifecycle (for example the existing CloudLink live microphone sample). This change SHALL NOT create a new meter poll merely because the reference contains a meter. Models without current compatible level evidence show `Нет данных`.

### `Журнал вызовов`

The preview area contains at most the three newest accepted call records. Each visible entry presents direction/non-color cue, safe peer/number/display identity when available, and timestamp when available. Missing subfields show `Нет данных`; zero accepted records or unavailable preview data shows `Нет данных`.

`Развернуть` is mandatory and opens the existing detailed call-log window under the lifecycle rules below.

### `Действия`

Two permanent actions:

- `Обновить статус`
- `Перезагрузить устройство`

`Обновить статус` is an alias of the existing exact-row Local Refresh and does not create another refresh implementation.

`Перезагрузить устройство` is always present. When the existing interaction lock matrix otherwise permits user input, it remains clickable even if the exact model has no reboot capability; unsupported click shows local information and starts no network lifecycle. A supported reboot requires a separate confirmation because it is disruptive.

## Decision 2: unified registry remains the only codec operation capability authority

No `CODEC_AUDIO_MODELS`, `CODEC_REBOOT_MODELS`, widget-type branch or model substring list may decide room capability.

Each exact codec registration SHALL expose one composition-owned codec-control capability/binding descriptor (or equivalent registry-owned typed structure) that explicitly declares support/absence for the room operations used by the dashboard:

```text
speaker_adjust
speaker_mute
microphone_adjust
microphone_mute
reboot
```

The descriptor is part of the existing exact registration authority, not an independent registry. Startup/composition SHALL fail closed if an operation is declared supported but its required operation adapter/readback/cleanup binding cannot be resolved.

The five current exact codec registrations are acceptance oracles. Tests SHALL exercise each registration and prove that every dashboard operation is explicitly `SUPPORTED` or `UNSUPPORTED`; runtime SHALL NOT infer support from the presence of a method on a widget/handler.

Current standalone behavior is useful implementation evidence but is not automatically promoted. The room binding may reuse the same safe application/core operation semantics only where the existing method/readback contract is actually supported. Unsupported operations use the local information path. Unsupported controls are not permanently disabled solely due to capability absence, but all common controls still obey temporary lifecycle locks required by the existing serialized room interaction matrix.

## Decision 3: audio button semantics are typed desired-state operations

The presentation emits only safe typed intent bound to the exact current room row. It does not compute credentials, construct handlers, call handler methods or parse response strings.

`+`/`−` SHALL resolve from current accepted authoritative volume evidence into an absolute target before the mutation is admitted. Model-specific step/range policy may be supplied by the registry-bound codec-control adapter, including the existing larger Polycom speaker step where applicable. If current value/range cannot be proven, the action performs no device I/O and reports a safe informational/unavailable result rather than defaulting to a fabricated starting value.

Mute/unmute SHALL be represented as an explicit desired state, not a blind toggle. Where the existing approved device contract represents mute by an absolute volume/mute state, the adapter maps the intent to that state and supplies model-appropriate readback.

The click on an eligible non-disruptive audio desired-state control is itself the explicit operator confirmation for that audio mutation; the room GUI SHALL NOT place a second modal confirmation dialog on every volume/mute click. This still enters the existing `MUTATION -> RECONCILIATION` lifecycle and obeys all of its stronger safety rules.

Only accepted model-appropriate readback confirming the requested state may update authoritative row data and resume normal interaction/live. Ambiguous/unconfirmed outcomes block row network interaction until top full Refresh exactly as the existing room mutation contract requires.

For a supported reboot, the action card SHALL use a separate explicit confirmation dialog before mutation admission. Cancel is a no-op. Reboot is unsupported unless an already-approved safe typed reboot and reconciliation contract exists; this change invents no reboot wire protocol.

## Decision 4: automatic call-log preview uses the existing AUXILIARY_READ lane

A current connected codec row SHALL obtain one automatic preview after the room cycle is terminal and the row is current/expanded/eligible. If the codec is already expanded before the automatic room cycle terminates, expansion itself starts no I/O; once the cycle becomes terminal, one preview is admitted if that same exact row is still eligible.

The preview lifecycle SHALL:

1. bind to immutable current room generation + `record_id` + exact model/IP + operation token;
2. invalidate/retire active LIVE before auxiliary I/O;
3. reuse the existing room call-log acquisition/normalization and application-owned credential rules;
4. accept the full normalized call-log result into application-owned auxiliary presentation state for that exact row/generation;
5. project only the three newest records into the card;
6. perform bounded cleanup before eligible LIVE may start/resume.

No second call-log network owner or parallel preview controller is allowed. The current `RoomCodecCallLogController` may be refactored so data acquisition/result ownership is independent from the side effect of showing a child window.

### Duplicate suppression

One preview completion is current for the exact row/generation. Re-render, hover, theme switch, resize or duplicate Qt expansion notification does not refetch it. A new preview is allowed only after the exact preview authority has been invalidated by a new row/generation/context or after an explicit fresh acquisition is required by the existing cancelled-child-window rule.

### Supersession and cancellation

- Collapse or switch to another row invalidates the preview and starts no stale follow-up I/O.
- Top full Refresh supersedes the preview under the existing auxiliary rule.
- Target/context invalidation makes all preview callbacks stale immediately.
- Late callbacks cannot update another row, reopen a window, or start LIVE for an old context.
- An ordinary preview parse/business failure that does not prove session loss shows `Нет данных` and preserves connection context; typed terminal connection/authentication failures follow the existing auxiliary degradation contract.

### `Развернуть`

When a current accepted full preview exists for the exact row/generation, `Развернуть` SHALL open/populate the existing `CallLogWindow` from that result without another network request.

If no current accepted preview exists, pressing `Развернуть` SHALL perform the existing normal call-log auxiliary acquisition and SHALL open/populate the child window only after current accepted data arrives. It SHALL NOT bypass the serialized lane.

After the user directly closes an active call-log child request, the existing cancellation rule remains authoritative: that request is invalidated/retired and a later explicit network opening after that cancelled request starts fresh acquisition rather than resurrecting it.

## Decision 5: room codec data normalization is presentation-safe

The dashboard consumes current accepted exact-row snapshot/live/auxiliary data. Presentation adapters may map safe existing field aliases into the fixed reference slots, but SHALL NOT invent model facts.

The adapter SHALL distinguish absent/unusable evidence from legitimate zero/false values. User-visible fallback is `Нет данных`, not model-specific `Unknown`, fabricated zero, or a hidden row.

The five exact codec models use one visual schema even where their parser payload names differ. Model-specific parser/adapter normalization remains below the shared dashboard; shared Qt code SHALL NOT determine semantic meaning by localized/model-specific string substrings when a typed status exists.

## Decision 6: interaction ownership and safety remain unchanged

All network-backed codec operations preserve current room contracts:

- application/composition owns credential candidate selection/fallback;
- worker/handler receives one assigned credential attempt;
- fallback requires structured authentication failure and applicable operation-safety gate;
- target authority is exact current row, never target-search text or a standalone screen;
- stale operations are rejected before handler/session acquisition and before first I/O;
- LIVE/LOCAL_REFRESH/AUXILIARY_READ/MUTATION/RECONCILIATION remain one serialized room lane;
- network I/O and cleanup never block the Qt GUI thread;
- secrets never enter public presentation/errors/logs;
- state-changing operations are never blindly replayed after ambiguous possible delivery.

Unsupported-operation informational dialogs are pure local presentation and therefore do not enter the room interaction lane or stop/resume live. Temporary disabled states imposed by an active/retiring lifecycle remain authoritative over the common visual controls.

## Validation strategy

Architecture validation:

```powershell
.\openspec.cmd validate codec-diagnostic-modern-ui --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
git diff --check origin/master...HEAD
```

Implementation tests SHALL cover:

- all five exact codec registrations using the one dashboard;
- fixed card/field order and `Нет данных` persistence;
- baseline width proportions/order and dark/light geometry;
- microphone-level no-fabrication behavior;
- supported/unsupported operation resolution from unified registry only;
- temporary lifecycle locks still disabling common controls when required;
- audio target construction from authoritative current values and no secondary confirmation dialog;
- supported reboot confirmation and unsupported reboot no-I/O path;
- no I/O on unsupported or unprovable action;
- existing mutation/reconciliation safety for supported audio/reboot operations;
- automatic call-log preview for both post-terminal expansion and a codec already expanded when the cycle becomes terminal;
- exactly three newest preview rows, accepted-preview reuse and empty state;
- duplicate-preview suppression across repeated renders;
- LIVE retirement/resume around preview;
- collapse/switch/top-Refresh/target-change stale cancellation;
- `Развернуть` existing child-window behavior;
- Local Refresh alias through `Обновить статус`;
- full offline suite and strict OpenSpec validation.

Manual visual acceptance SHALL run the application at the common `1440 x 900` baseline in dark theme and compare only the expanded codec area against the supplied reference. Acceptance targets approximately 90% correspondence in the specified structure/proportions/labels/indicators/density/control placement. A light-theme capture SHALL verify the same geometry and readable semantic states. Screenshots are local validation aids and are not repository artifacts unless explicitly requested.

Because this change adds requirements to existing root specs, independent validation SHALL perform the disposable archive-applicability check before `READY FOR ARCHIVE` under `RULES.md`.
