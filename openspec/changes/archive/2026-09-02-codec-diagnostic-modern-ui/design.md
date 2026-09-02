# Design: Modern codec diagnostic UI

## Context

Current `master` already contains the common modern room foundation and the dedicated Audio DSP and Matrix room dashboards. The current codec branch of `RoomReadOnlyPresentation` is still a flat generic field projection with Local Refresh, call-log and Debug controls above it.

The unified exact application registry owns five codec registrations and already declares room Local Refresh and call-log auxiliary bindings for all five; CloudLink Bar/Box also declare their existing room live binding. Standalone `CodecScreen` and current handlers contain useful evidence about existing safe codec operations, but standalone widgets are not room capability authority.

The product reference that motivated this change is an external visual input only. The approved OpenSpec files in this change are the complete normative design. A clean implementation or independent-validation session must be able to reconstruct and judge the target without access to the original conversation/image.

This change therefore has three coupled responsibilities:

1. replace the room codec projection with one self-contained five-card dashboard contract;
2. promote only current proven codec controls through the unified registry/serialized room lifecycle; and
3. make automatic call-log preview one-shot, typed and stale-safe without creating another network owner.

## Goals

- One shared codec dashboard for all five current exact codec registrations.
- Repository-local visual acceptance equivalent to the product's approximately 90% target without an external screenshot dependency.
- Missing model-specific data remains explicit as `Нет данных` without layout collapse.
- Existing room exact-row authority, credential ownership, stale protection, single serialized network lane and Qt-thread safety remain unchanged.
- Automatic call-log preview attempts once per exact expansion epoch and cannot loop after an ordinary failure.
- Existing proven speaker and microphone-mute controls become room interactions only at the exact baseline applicability defined here.
- Numeric volume, typed mute state and speaker restore authority are separate.

## Non-goals

- Pixel-perfect font rasterization.
- Family-specific codec dashboards.
- New protocol commands solely to populate absent visual fields.
- A new generic reboot protocol.
- Re-enabling CloudLink microphone-gain mutation.
- Parallel codec support tables outside the unified exact-model registry.
- Concurrent LIVE and AUXILIARY/MUTATION ownership.
- Optimistic device state after mutation.
- Widget-local remembered volume as room mutation authority.
- Changes to the outer room shell or other device-family dashboards.

## Decision 1: one self-contained five-card codec dashboard

At `1440 x 900` the expanded codec content renders one horizontal dashboard in this exact order:

```text
Состояние | Вызов и презентация | Аудио | Журнал вызовов | Действия
```

Target width weights:

```text
Состояние              23 ±4
Вызов и презентация    17 ±4
Аудио                  18 ±4
Журнал вызовов         25 ±4
Действия               17 ±4
```

Repository-local visual geometry is normative:

```text
card height                    286-326 px
card-to-card gap               10-14 px
card inner padding             14-18 px
header height                  34-42 px
header icon                    18-22 px
title                          11-12 pt semibold equivalent
ordinary body label             9-10 pt
primary value                  10-11 pt
ordinary data row              28-34 px
status dot                      8-10 px when used
```

The detailed presentation spec defines the Audio, call-log and Actions geometry plus a ten-checkpoint visual acceptance oracle. Mandatory structure checkpoints plus at least `9/10` total checkpoints operationalize the approximately 90% product target. External screenshots may inform tuning but are not acceptance authority.

Dark theme is baseline. Light theme preserves geometry/order and shared semantic styling. Minimum-window behavior may scroll/reflow deterministically but cannot hide cards/controls.

### `Состояние`

Permanent rows:

1. `Модель`
2. `MAC-адрес`
3. `Серийный номер`
4. `Платформа`
5. `Версия ПО`
6. `Микрофон`
7. `Камера`

### `Вызов и презентация`

Permanent rows:

1. `Статус звонка`
2. `Презентация`
3. `Регистрация SIP/H.323`

Absent/unusable evidence renders `Нет данных`. The fixed row/card schema does not collapse per model.

### `Аудио`

Order is fixed:

```text
Микрофон (уровень)     horizontal indicator
Громкость микрофона    − | numeric/no-data | + | mute
Громкость динамиков    − | numeric/no-data | + | mute
```

The presentation preserves positions even for unsupported network capabilities. Visible unsupported affordances are explicitly local-only and do not redefine capability support.

### `Журнал вызовов`

The card reserves visual density for three normalized records and shows at most the first three entries of the typed newest-first result. Each record uses direction/non-color cue, primary peer identity and secondary timestamp. `Развернуть` follows the preview region.

### `Действия`

Two vertically stacked actions:

1. `Обновить статус`
2. `Перезагрузить устройство`

Current baseline reboot is unsupported for all five codecs, so reboot is a local-only affordance. No wire protocol is added.

## Decision 2: explicitly modify old unsupported-control contracts rather than silently contradict them

The root `Limited device control` contract says only implemented device operations are exposed. The root `Model-specific interactive codec session paths` contract also explicitly keeps CloudLink microphone gain unavailable/disabled. A fixed common dashboard with visible unsupported affordances cannot be added only as a new requirement without reconciling those existing contracts.

Therefore this change uses `MODIFIED Requirements` for both existing requirements.

The resulting distinction is normative:

```text
SUPPORTED network capability
    -> may enter room interaction lifecycle when otherwise eligible

UNSUPPORTED network capability + fixed codec visual affordance
    -> capability remains unavailable/unsupported
    -> click resolves locally before RoomInteractionCoordinator admission
    -> no LIVE invalidation
    -> no interaction generation
    -> no handler/session
    -> no credential selection
    -> zero device I/O
```

CloudLink microphone gain remains a particularly strict case: Bar/Box `microphone_adjust` is unsupported and gain PUT/POST/readback remains forbidden. The only change is that fixed visual `−/+` affordances may remain present and locally explain that the operation is unsupported.

This is not a general rule that every unsupported device action must be rendered. It is a presentation exception for this approved fixed common codec dashboard.

## Decision 3: current five-codec support matrix is fixed architecture acceptance, not runtime registry

Runtime still resolves capability only through the unified exact-model registration. To prevent implementation from declaring everything unsupported, current approved source/contracts define this acceptance oracle:

| Exact model | speaker_adjust | speaker_mute | microphone_adjust | microphone_mute | reboot |
| --- | --- | --- | --- | --- | --- |
| Huawei TE20 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| Huawei TE40 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| CloudLink Bar 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| CloudLink Box 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| Polycom RPG 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |

Evidence behind the matrix on current `master`:

- TE20/TE40 expose proven speaker absolute volume/readback; their `set_microphone_volume` compatibility surface maps to microphone mute, not numeric gain.
- Bar/Box expose proven speaker absolute volume/readback; root contract explicitly forbids CloudLink microphone gain, and there is no separate approved room microphone-mute mutation binding.
- Polycom exposes speaker absolute volume/readback and explicit microphone mute/readback; its `set_microphone_volume` compatibility surface also maps to mute rather than gain.
- no current codec has an approved typed reboot plus reconciliation operation.

`speaker_mute` is supported for all five through the room-owned volume-zero/restore policy below; this does not claim a separate raw speaker-mute command.

Tests may encode the table as expected values. Production runtime must not consult it as a separate authority. If source contracts materially change before implementation, architecture is re-reviewed instead of silently changing applicability.

## Decision 4: numeric volume, typed mute state and restore target are separate authority

The shared room projection no longer has ambiguous `microphone_volume_or_state` or `speaker_volume_or_state` slots. It exposes:

```text
microphone_volume      Optional[numeric]
microphone_mute_state  MUTED | UNMUTED | UNKNOWN
speaker_volume         Optional[numeric]
speaker_mute_state     MUTED | UNMUTED | UNKNOWN
```

A model adapter may derive speaker mute from zero/non-zero only when its approved semantics establish that relationship. Shared presentation does not parse display strings.

### Relative `+/-`

`+/-` must first prove current accepted numeric value, exact model range and step. It then creates one absolute target before mutation. Missing authority means local unavailable, zero device I/O. Minimum/zero/default/another model/widget state cannot fill the gap.

### Microphone mute

TE20, TE40 and Polycom use typed microphone mute desired state and typed readback. Numeric microphone gain is not invented.

### Speaker mute / unmute

For current codecs the shared desired-state policy is volume zero plus restore:

```text
accepted current speaker_volume > 0 + mute
    -> target 0
    -> remember that accepted non-zero value as current exact-row restore evidence

accepted current speaker_volume == 0 + unmute + accepted restore value
    -> target = restore value

accepted current speaker_volume == 0 + unmute + no restore evidence
    -> local unavailable
    -> zero device I/O
```

The restore value is application/core-owned state keyed to current room generation + record. It can be updated only by a newly accepted current non-zero device value. It is not `CodecScreen.last_unmuted_volume`; requested values/ACKs are not authority; fallback `1`, minimum or other synthetic targets are forbidden. A new room generation/context invalidation clears old restore authority.

All supported mutations still use `MUTATION -> RECONCILIATION`; only matching accepted readback confirms final state.

## Decision 5: automatic call-log preview has expansion-epoch attempt authority

The automatic preview key is semantically:

```text
room generation + exact record_id + expansion epoch
```

An expansion epoch begins only on a real collapsed -> expanded transition under current authority. A pre-terminal expansion carries the same epoch until the room cycle terminates; if still eligible, that epoch gets one automatic attempt after terminal state.

The attempt enters existing `AUXILIARY_READ`; LIVE retires first. The attempt marker becomes terminal after any current terminal outcome:

- success with records;
- success with no records;
- ordinary parse/business/no-data failure;
- typed terminal connection/session/authentication failure.

Therefore an ordinary failure cannot cause:

```text
fail -> render -> auto-read -> fail -> render -> ...
```

After a terminal automatic attempt, render/repaint/theme/resize/hover/duplicate expansion notification/LIVE resume causes zero additional automatic call-log I/O for the same epoch.

A new automatic epoch may arise only from collapse+explicit re-expand, row switch followed by later re-expand, new room generation/top Refresh, or a genuinely new valid context after invalidation.

`Развернуть` is different: after a failed/no-data automatic attempt, an explicit operator click may request a fresh call-log `AUXILIARY_READ`. That explicit request does not reset the automatic marker and cannot cause a new automatic loop.

## Decision 6: call-log chronology is the typed normalized snapshot order

Current `core.codec_call_history.CallHistorySnapshot` already provides the right authority: normalization sorts by typed comparable `start_at` newest-first, places missing chronology after records with timestamps, and preserves deterministic stable order among equivalent chronology keys.

This change makes that behavior an explicit cross-model contract:

```text
1. model adapter returns/uses one typed normalized CallHistorySnapshot (or equivalent preserving it)
2. records with proven start_at sort descending
3. records without proven start_at follow timestamped records
4. equal/missing chronology retains deterministic normalized acceptance/source order
5. display strings are never parsed/sorted lexicographically for chronology
6. preview takes records[0:3]
```

A safe display timestamp may still be shown for a malformed/unknown chronology record, but it cannot elevate the record in ordering.

Tests must cover all five current codec adapters and malformed/missing timestamp cases.

## Decision 7: acquisition result is independent of detailed-window side effect

Automatic preview and `Развернуть` share the same normalized full acquisition result, not separate parsers/capability authorities.

- accepted current automatic result -> inline preview + local `Развернуть` reuse with no second read;
- no accepted current result -> explicit `Развернуть` may start one serialized auxiliary read;
- active detailed-window request closed by user -> existing cancellation/cleanup rule remains authoritative;
- stale callbacks cannot reopen or update another context.

## Decision 8: all interaction ownership/safety remains application-owned

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

Unsupported informational affordances are pure local presentation. Existing lifecycle locks still temporarily disable controls when another network owner is active/retiring.

## Validation strategy

Architecture validation on the exact published feature HEAD:

```powershell
.\openspec.cmd validate codec-diagnostic-modern-ui --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
git diff --check origin/master...HEAD
```

Implementation regression coverage SHALL include:

- all five exact registrations with the exact support matrix above and proof runtime authority remains unified registry;
- fixed card/field order, numeric visual ranges/checkpoints and `Нет данных` persistence;
- all mandatory visual checkpoints and at least `9/10` total at baseline; light-theme geometry parity;
- microphone-level no-fabrication behavior;
- split numeric volume vs typed mute-state projection;
- `+/-` absolute target construction only from current accepted numeric evidence;
- speaker mute/unmute restore from accepted non-zero exact-row state and zero I/O when restore is absent;
- explicit proof no `last_unmuted_volume`, fallback `1`, minimum/default or requested value becomes room restore authority;
- CloudLink microphone `−/+` local-only affordance with zero interaction/network I/O and gain network capability still unsupported;
- supported audio mutation/readback confirmation, ambiguous-outcome blocking and top-Refresh recovery;
- automatic preview both after post-terminal expansion and after a pre-terminal expansion remains current;
- one attempt per expansion epoch for success, zero records and ordinary failure;
- ordinary preview failure followed by repeated render/theme/resize/repaint/duplicate expansion -> zero additional automatic I/O;
- collapse+re-expand -> new epoch may perform one new automatic attempt;
- LIVE retirement/resume and stale suppression across collapse, A->B switch, top Refresh, query/context invalidation and shutdown;
- explicit `Развернуть` after failed automatic preview may perform one fresh auxiliary request without resetting automatic attempt marker;
- typed newest-first chronology for all five current call-log adapters, including malformed/missing timestamps and no display-string sorting;
- Local Refresh alias through `Обновить статус`;
- full offline suite and strict OpenSpec validation.

Manual GUI validation SHALL launch detached per `RULES.md`, set `1440 x 900`, and evaluate the ten repository-local presentation checkpoints in `diagnostic-ui-presentation`. External screenshots are optional comparison aids only and SHALL NOT be required evidence.

Because this change now uses `MODIFIED Requirements`, independent validation MUST perform the disposable archive-applicability check required by `RULES.md` before a permitting archive verdict.
