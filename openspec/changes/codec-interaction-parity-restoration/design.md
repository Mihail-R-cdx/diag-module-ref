# Design: Codec interaction parity restoration

## Context

The current room codec dashboard is visually acceptable but user testing shows that key codec interactions no longer behave like the pre-redesign application. Static comparison between `c442152...` and current `master` shows that the protocol handlers changed very little while the room composition, dashboard, coordinator, dispatch descriptors, and presentation lifecycle changed substantially.

The design therefore restores proven behavior at the application/composition boundary while preserving the current room architecture: exact-row authority, one serialized network lane, currentness tokens, background I/O, typed failure handling, and no Qt-thread network I/O.

## Source of truth

Authority remains:

`RULES.md -> current root OpenSpec -> approved change -> source/tests -> Git diff -> runbooks -> agent reports`

For this regression family, `c442152077dd8aa6251f1d8be9fc98b765406dbd` is additionally a **behavioral oracle** for operations that were demonstrably supported before `codec-diagnostic-modern-ui`. It is not architectural authority and shall not override current security/currentness rules.

## Confirmed forensic findings

### 1. Protocol layer is not the primary regression boundary

The Huawei/Polycom handler files changed minimally across the redesign compared with large changes in `gui/main_window.py`, `gui/room_diagnostic_tree.py`, `core/room_interaction.py`, dispatch, and related controller code. The retained `gui/screens/codec_screen.py` still contains the proven pre-redesign interaction composition.

### 2. Automatic call-log preview competes with LIVE

Current row expansion performs:

```text
expand row
-> coordinator.expand(record_id)
-> eligible LIVE may start
-> request_codec_preview()
```

The serialized interaction lane retires active LIVE before admitting an auxiliary read. Therefore an automatic preview can immediately retire a newly started CloudLink meter. If preview or retirement cleanup stalls, the live microphone meter is starved indefinitely.

### 3. TE20/TE40 live audio was dropped from room presentation

The pre-redesign codec screen owned a 2-second timer and submitted `get_live_audio_status`, presenting `MicValueIndex` and `SpeakerValueIndex`. The new room codec dashboard only exposes a live microphone bar for models with `cloudlink_room_live`; TE20/TE40 lost their proven model-specific live-audio behavior.

### 4. Fixed dashboard affordances and registry capability can disagree

The shared codec dashboard may render microphone adjust/reboot controls while the exact-model `CodecControlDescriptor` declares those operations unsupported. A clickable-looking control that is guaranteed to be rejected is not acceptable parity.

### 5. Mutation/readback became heavier than the proven behavior

The old codec screen serialized an interactive operation with model method + targeted authoritative readback (for example `set_speaker_volume` + `get_speaker_volume`). Current room mutation composition may create a temporary session, shut it down, then launch a full one-shot diagnostic reconciliation. This adds failure and cleanup boundaries unrelated to the field being changed.

## Architectural decisions

### A. Preserve current dashboard; restore behavior beneath it

Do not resurrect `CodecScreen` as room authority and do not route room widgets directly to handlers. The current dashboard continues to emit safe intents. Composition resolves those intents using the exact model registry and application-owned controller/session objects.

The legacy codec screen is a reference implementation only. Proven interaction logic should be extracted/shared or reimplemented at the controller/application layer with current exact-row/currentness rules.

### B. Exact-model capability matrix must match visible actionable controls

`diagnostic_dispatch` remains the sole capability authority.

For each codec model, the descriptor must distinguish at least:

- speaker volume adjust/readback;
- speaker mute semantics where supported;
- microphone mute semantics where supported;
- microphone gain adjust where supported;
- reboot where supported;
- call log;
- live microphone/audio telemetry.

A dashboard control that represents an unsupported network operation must be disabled/hidden or unmistakably local-only; it must not look like a normal actionable device control and then fail after admission.

CloudLink microphone gain remains unsupported unless a later approved change establishes target selection and authoritative reconciliation. This parity change must not smuggle that capability back in merely because the old widget had `+/-` affordances.

### C. LIVE has priority over automatic preview

Automatic call-log preview is presentation enrichment, not a reason to destroy live telemetry.

When a codec row is expanded and LIVE is supported:

1. LIVE may acquire the serialized lane.
2. Automatic preview must **not** request retirement of that LIVE owner.
3. Preview may be populated from already-authoritative/cached acquisition data when available.
4. Otherwise preview stays `Нет данных`/loading-neutral or is deferred until a naturally idle boundary; it must not block or starve LIVE.
5. Explicit operator action `Развернуть` / `Журнал звонков` remains an auxiliary read. It may retire LIVE under the existing serialized-lane contract, and LIVE must resume after bounded cleanup if the row remains current and usable.

No concurrent network owner is introduced.

### D. Restore model-specific live telemetry

#### CloudLink Bar 310 / Box 310

Continue to use the existing `CloudLinkMicrophoneMeter` / `WEB_GetCurrentAudioParam` compatibility path under one room LIVE owner. Accepted samples update only the approved live presentation field and must not be overwritten by unrelated preview bookkeeping.

#### Huawei TE20 / TE40

Introduce/restore a room-owned live binding equivalent to the proven pre-redesign `get_live_audio_status` behavior. It should preserve the established 2-second cadence unless device evidence requires another bounded cadence. The reusable `CodecScreen` timer is not reused as authority; the room live owner owns start/stop/currentness/cleanup.

#### Polycom RPG 310

Do not fabricate a live microphone meter merely for visual symmetry. Restore only behavior proven by the pre-redesign implementation or current hardware evidence.

### E. Explicit call log uses proven retrieval ownership

Explicit call-log opening remains a fresh auxiliary acquisition bound to the exact current row. The model-specific retrieval methods and normalization that worked before redesign remain authoritative unless hardware evidence disproves them.

Automatic preview and explicit dialog acquisition are separate product intents. Failure of preview must not disable explicit journal opening; failure of an ordinary journal parse/business operation must not permanently degrade an otherwise connected row.

### F. Codec audio mutations use targeted authoritative reconciliation

For supported codec audio operations, use the proven model method and smallest authoritative readback that confirms the changed field.

Example speaker-volume flow:

```text
safe dashboard intent
-> exact-model capability/currentness validation
-> retire LIVE through bounded cleanup
-> one serialized InteractiveSessionController generation
-> set_speaker_volume(target)
-> get_speaker_volume() authoritative readback
-> publish reconciled canonical speaker field
-> release operation
-> resume LIVE if still eligible
```

A full diagnostic worker refresh is not required merely to confirm one audio field when the model already exposes an authoritative targeted getter. If the target cannot be confirmed, keep previous authoritative state as stale/unconfirmed and follow current blocked/unconfirmed safety rules; do not blindly replay the mutation.

### G. No indefinite locks

Every Local Refresh, explicit journal, codec mutation, reconciliation, and LIVE retirement path must have a deterministic terminal or bounded-abandonment path that restores the lock matrix when safe.

Tests must cover:

- success;
- typed authentication rejection/fallback;
- ordinary protocol/parse failure;
- transport/session loss;
- user cancellation/collapse;
- cleanup timeout;
- late callback after currentness revocation.

The GUI must never remain permanently disabled because a worker/session cleanup signal was missed.

## Validation strategy

### Offline regression layers

1. **Protocol/handler regression:** existing handler methods remain callable with expected normalized outputs.
2. **Composition integration:** exercise real `MainWindow`/room coordinator/controller/`InteractiveSessionController` path, replacing only device transport with deterministic fake handlers. Tests must assert real signal/callback/cleanup ordering rather than manually invoking terminal callbacks on mocks.
3. **Presentation regression:** accepted canonical values appear in the new dashboard and exact-model unsupported controls are not falsely actionable.
4. **Cross-lifecycle regression:** automatic preview never retires LIVE; explicit call log retires/resumes LIVE correctly; mutations release locks and resume LIVE only after reconciliation.

Snapshot-only tests are useful but cannot be the sole evidence for any affected defect.

### Hardware acceptance

Before affected codec defects are marked complete, execute the relevant scenario on a real device of the affected exact model where available. Record at minimum:

```text
model
operation
request path/method (non-secret)
raw outcome category or success marker
normalized field/result
GUI result
whether UI unlocked afterward
```

Minimum user-visible acceptance set:

- CloudLink Box 310: open journal, display microphone/speaker values, live microphone bar, speaker +/- and mute where supported, Local Refresh;
- CloudLink Bar 310: same supported CloudLink scenarios;
- Huawei TE20/TE40: journal, speaker/microphone supported controls, restored live-audio fields, Local Refresh;
- Polycom RPG 310: journal and supported audio/refresh controls without fabricated unsupported live meter.

If a model is unavailable during implementation, the exact defect remains unverified for hardware acceptance and must not be represented as proven fixed solely from mocks.

## Risks

- Reusing old widget code directly would create duplicate authority. Mitigation: reuse behavior at controller/session layer only.
- Targeted reconciliation could accidentally update unrelated cache fields. Mitigation: define per-operation canonical field merge and preserve prior snapshot for untouched fields.
- Deferring automatic preview may leave the preview card empty longer. This is acceptable; live telemetry and explicit journal correctness have priority.
- Hardware differences/firmware can invalidate old assumptions. Mitigation: old behavior is an oracle only for already-proven operations; contradictory real-device evidence wins and must be documented before architecture changes.

## Rollback

Implementation is isolated to codec room interaction composition, dispatch capability declarations, and related tests/presentation. If a fix introduces new regressions, revert the focused implementation commit(s); do not revert the entire room UI redesign or protocol handlers.
