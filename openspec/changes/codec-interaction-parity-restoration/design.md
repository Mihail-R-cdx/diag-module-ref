# Design: Codec interaction parity restoration

## Context

The current room codec dashboard is visually acceptable but real-device user testing shows that key codec interactions no longer behave like the pre-redesign application. Static comparison between `c442152077dd8aa6251f1d8be9fc98b765406dbd` and current `master` shows that the protocol handlers changed little compared with the room composition, dashboard, coordinator, dispatch descriptors, and presentation lifecycle.

The change restores proven behavior at the application/composition boundary while preserving current exact-row authority, one serialized network lane, currentness tokens, application-owned credential fallback, typed failure handling, redaction, bounded cleanup, and no Qt-thread network I/O.

## Source of truth

Authority remains:

`RULES.md -> current root OpenSpec -> approved change -> source/tests -> Git diff -> runbooks -> agent reports`

For this regression family, `c442152077dd8aa6251f1d8be9fc98b765406dbd` is additionally a **behavioral oracle** for operations that were demonstrably supported immediately before `codec-diagnostic-modern-ui`. It is not architectural authority and does not override current security/currentness rules.

## Confirmed forensic findings

### 1. Protocol layer is not the primary regression boundary

The retained `gui/screens/codec_screen.py` still contains the pre-redesign interaction composition. Existing Huawei/Polycom handlers expose the same proven speaker-volume getters/setters, call-log retrieval paths, TE20/TE40 live-audio reads, and CloudLink meter path that existed before the room codec redesign.

### 2. Automatic call-log preview competes with LIVE

Current row expansion performs:

```text
expand row
-> coordinator.expand(record_id)
-> eligible LIVE may start
-> request_codec_preview()
```

The serialized room lane retires active LIVE before an auxiliary read. Therefore automatic preview can immediately retire a freshly started CloudLink meter. If preview or cleanup stalls, live metering is starved.

### 3. TE20/TE40 live audio was dropped from room presentation

The pre-redesign codec screen owned a 2-second timer and submitted `get_live_audio_status`, presenting `MicValueIndex` and `SpeakerValueIndex`. The new room codec dashboard only exposes a live microphone bar for `cloudlink_room_live`; TE20/TE40 lost their proven model-specific live-audio behavior.

### 4. Dashboard affordances and exact-model capability can disagree

The current shared dashboard can render microphone `-/+` and reboot controls while the exact-model descriptor rejects those operations. A normal clickable-looking control that is guaranteed to be rejected is not parity.

### 5. Mutation/readback became heavier than proven behavior

The pre-redesign screen serialized an operation plus targeted authoritative readback, for example `set_speaker_volume` followed by `get_speaker_volume`. Current room composition may create a temporary interactive session, retire it, and then launch a full codec one-shot reconciliation. This adds unrelated lifecycle failure points.

### 6. Static microphone evidence is not normalized consistently

The current common dashboard consumes canonical `microphone_volume` / `microphone_muted`, but existing model parsers publish different authoritative source fields. In particular CloudLink diagnostic parsing already receives `mic_volume`; TE20/TE40/Polycom primarily expose microphone mute semantics rather than numeric gain. The architecture must define this normalization before implementation.

## Architectural decisions

### A. Preserve current dashboard; restore behavior beneath it

Do not resurrect `CodecScreen` as room authority and do not route room widgets directly to handlers. The current dashboard emits safe intents. Application/controller/session composition resolves those intents from the exact current row and the single exact-model registry.

The legacy codec screen is a reference implementation only. Proven interaction logic may be extracted/shared or reimplemented below the presentation boundary with current exact-row/currentness rules.

### B. Normative exact-model capability matrix

`diagnostic_dispatch` remains the sole codec network-capability authority. Implementation SHALL conform to this matrix; an implementer may not downgrade a `YES` entry to `unsupported` merely because the new room path is difficult to wire.

| Exact model | Speaker adjust | Speaker range / step | Speaker readback | Speaker mute | Mic mute | Mic gain adjust | Reboot | Call log | LIVE telemetry | Local Refresh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Huawei TE20 | YES | `0..21`, step `1` | `get_speaker_volume` | YES, authoritative zero/restore using speaker readback | YES, `set_microphone_mute` + mute-state readback | NO; legacy `set_microphone_volume` is only a mute compatibility wrapper | NO; no proven pre-redesign room capability | YES, fresh `get_call_history_snapshot` path | YES; room-owned `get_live_audio_status`, 2 s cadence, microphone + speaker monitor values | YES, exact-row `room_one_shot_refresh` |
| Huawei TE40 | YES | `0..21`, step `1` | `get_speaker_volume` | YES, authoritative zero/restore using speaker readback | YES, `set_microphone_mute` + mute-state readback | NO; legacy `set_microphone_volume` is only a mute compatibility wrapper | NO; no proven pre-redesign room capability | YES, fresh `get_call_history_snapshot` path | YES; room-owned `get_live_audio_status`, 2 s cadence, microphone + speaker monitor values | YES, exact-row `room_one_shot_refresh` |
| CloudLink Bar 310 | YES | `0..15`, step `1` | `get_speaker_volume` | YES, authoritative zero/restore using speaker readback | NO separate approved mic-mute capability in the current exact-model contract | NO; current root contract explicitly prohibits CloudLink microphone gain mutation | NO; no proven pre-redesign room capability | YES, fresh shared CloudLink call-history path, exact Bar identity retained | YES; `cloudlink_room_live` via existing `CloudLinkMicrophoneMeter` / `WEB_GetCurrentAudioParam` compatibility path | YES, exact-row `room_one_shot_refresh` |
| CloudLink Box 310 | YES | `0..15`, step `1` | `get_speaker_volume` | YES, authoritative zero/restore using speaker readback | NO separate approved mic-mute capability in the current exact-model contract | NO; current root contract explicitly prohibits CloudLink microphone gain mutation | NO; no proven pre-redesign room capability | YES, fresh shared CloudLink call-history path, exact Box identity retained | YES; `cloudlink_room_live` via existing Box microphone normalization / `WEB_GetCurrentAudioParam` compatibility path | YES, exact-row `room_one_shot_refresh` |
| Polycom RPG 310 | YES | `0..100`, step **`2`** | `get_speaker_volume` | YES, authoritative zero/restore using speaker readback | YES, `set_microphone_mute` + mute-state readback | NO; legacy `set_microphone_volume` is only a mute compatibility wrapper | NO; no proven pre-redesign room capability | YES, fresh Polycom call-log worker/session path | NO approved live microphone/audio meter; do not fabricate one | YES, exact-row `room_one_shot_refresh` |

Matrix notes:

- The Polycom speaker step is `2`, matching the pre-redesign `CodecScreen`; the current registry value `1` is a regression to correct.
- `speaker mute = YES` means the existing product semantic of setting authoritative speaker volume to zero and restoring the remembered last positive authoritative value. It does not invent a separate vendor mute command.
- `microphone gain adjust = NO` for all five models in this change. TE20/TE40/Polycom expose mute semantics through the legacy compatibility method; CloudLink gain remains explicitly prohibited by current root contract because authoritative target selection/readback is not established.
- `reboot = NO` for all five models because the pre-redesign room codec surface does not prove that capability and the current exact-model descriptors reject it. The current dashboard reboot affordance must therefore be hidden/disabled or unmistakably local-only; this change does not turn it into network capability.
- The matrix is normative. Changing a value requires architecture review plus source/device evidence, not an implementation-only decision.

### C. Normative static audio normalization matrix

The accepted room snapshot SHALL normalize proven exact-model evidence before the common dashboard consumes it. Presentation SHALL NOT be required to parse vendor/display strings itself.

| Exact model | Existing authoritative source evidence | Required canonical accepted evidence | Dashboard result |
| --- | --- | --- | --- |
| Huawei TE20 | `mic_mute` from handler/parser | `microphone_muted: bool` when source evidence is known; no fabricated numeric `microphone_volume` | render microphone mute state; numeric microphone gain is unavailable by design |
| Huawei TE40 | `mic_mute` from handler/parser | `microphone_muted: bool` when source evidence is known; no fabricated numeric `microphone_volume` | render microphone mute state; numeric microphone gain is unavailable by design |
| CloudLink Bar 310 | diagnostic audio `mic_volume` and, where present, `mic_mute` | `microphone_volume: number` from authoritative `mic_volume`; `microphone_muted` only when authoritative mute evidence exists | render current numeric microphone value instead of `Нет данных` when `mic_volume` was actually received |
| CloudLink Box 310 | diagnostic audio `mic_volume` and, where present, `mic_mute` | `microphone_volume: number` from authoritative `mic_volume`; `microphone_muted` only when authoritative mute evidence exists | render current numeric microphone value instead of `Нет данных` when `mic_volume` was actually received |
| Polycom RPG 310 | SSH/normalized microphone mute evidence (`mic_mute`) | `microphone_muted: bool`; no fabricated numeric `microphone_volume` | render microphone mute state; numeric microphone gain is unavailable by design |

Speaker normalization remains `speaker_volume: number` from authoritative model parser evidence for all five supported codecs. Percentage rendering is derived only from the exact-model range in the capability matrix.

Tests for this contract SHALL exercise:

```text
handler/transport fake at edge
-> actual model parser/normalizer
-> accepted room snapshot
-> common dashboard projection
```

A regression test that manually constructs an already-canonical snapshot with `microphone_volume` does not by itself prove this contract.

### D. LIVE has priority over automatic preview

Automatic call-log preview is presentation enrichment, not a reason to destroy live telemetry.

When a codec row is expanded and LIVE is supported:

1. LIVE may acquire the serialized lane.
2. Automatic preview SHALL NOT request retirement of that LIVE owner.
3. Preview may be populated from already-authoritative/cached acquisition data when available.
4. Otherwise preview remains unavailable/deferred until a naturally idle admissible boundary.
5. Explicit operator action `Развернуть` / `Журнал звонков` remains an auxiliary read. It may retire LIVE under the existing serialized-lane contract; LIVE resumes after bounded cleanup if the same row remains current and usable.

No concurrent network owner is introduced.

### E. Restore model-specific live telemetry

#### CloudLink Bar 310 / Box 310

Continue to use the existing `CloudLinkMicrophoneMeter` / `WEB_GetCurrentAudioParam` compatibility path under one room LIVE owner. Accepted samples update only the approved live presentation field and are not cleared by preview bookkeeping.

#### Huawei TE20 / TE40

Add one room-owned live binding for the proven `get_live_audio_status` behavior. The accepted live payload SHALL retain both microphone and speaker monitor evidence from `MicValueIndex` / `SpeakerValueIndex` under a model-specific live-audio projection. Preserve the proven 2-second cadence unless real-device evidence requires another bounded cadence. `CodecScreen`'s timer is not reused as room authority.

#### Polycom RPG 310

No live meter is authorized. Absence of live telemetry is a negative acceptance case, not a reason to create synthetic values.

### F. Explicit call log uses proven retrieval ownership

Explicit call-log opening remains a fresh auxiliary acquisition bound to the exact current row. Existing model-specific retrieval/normalization that worked before redesign remains authoritative unless current hardware evidence disproves it.

Automatic preview and explicit dialog acquisition are separate intents. Preview failure does not disable explicit journal opening. Ordinary journal parse/business failure does not permanently degrade an otherwise connected row.

### G. Codec audio mutations use targeted authoritative reconciliation

For supported codec audio operations, use the proven model method and the smallest authoritative readback that confirms the changed field.

Example speaker flow:

```text
safe dashboard intent
-> exact-model capability/currentness validation
-> retire LIVE through bounded cleanup
-> one serialized InteractiveSessionController generation
-> set_speaker_volume(target)
-> get_speaker_volume() authoritative readback
-> publish reconciled speaker_volume
-> release operation
-> resume LIVE if still eligible
```

A full diagnostic worker refresh is not required solely to confirm one audio field when the model already exposes an authoritative targeted getter. If readback cannot confirm final state, keep previous authoritative state stale/unconfirmed and apply existing blocked/unconfirmed safety; never blindly replay the mutation.

### H. No indefinite locks

Every Local Refresh, explicit journal, supported codec mutation/reconciliation, and LIVE retirement path has a deterministic terminal or bounded-abandonment path on:

- success;
- structured authentication rejection/fallback;
- ordinary protocol/parse/business failure;
- transport/session loss;
- user cancellation/collapse/switch;
- cleanup timeout;
- late callback after currentness revocation.

The GUI SHALL NOT remain permanently disabled because a cleanup callback or session shutdown signal was missed.

## Explicit defect/action inventory

This matrix separates a reproduced/user-reported defect from regression-only coverage. `Current result = exact-model reproduction required` means the family-level user report exists but the exact model was not identified in the report; implementation may not silently assume success.

| Exact model | User action / evidence | Current result | Pre-redesign / approved result | In scope |
| --- | --- | --- | --- | --- |
| TE20 | `Обновить статус` | family-level error/hang report; exact-model reproduction required | successful exact-model diagnostic refresh path | YES |
| TE40 | `Обновить статус` | family-level error/hang report; exact-model reproduction required | successful exact-model diagnostic refresh path | YES |
| Bar 310 | `Обновить статус` | family-level error/hang report; hardware reproduction required | successful exact-model diagnostic refresh path | YES |
| Box 310 | `Обновить статус` | family-level error/hang report; exact-model reproduction required | successful exact-model diagnostic refresh path | YES |
| RPG 310 | `Обновить статус` | not reported as broken on this exact model; regression guard | successful Polycom refresh/reference behavior | YES as regression guard |
| TE20 | explicit journal / `Развернуть` | family-level journal failure; exact-model reproduction required | fresh Huawei call-log acquisition | YES |
| TE40 | explicit journal / `Развернуть` | family-level journal failure; exact-model reproduction required | fresh Huawei call-log acquisition | YES |
| Bar 310 | explicit journal / `Развернуть` | user-reported journal regression family; hardware reproduction required | fresh CloudLink call-log acquisition | YES |
| Box 310 | explicit journal / `Развернуть` | user-reported journal regression family; exact-model reproduction required | fresh CloudLink call-log acquisition | YES |
| RPG 310 | explicit journal / `Развернуть` | previously working reference | fresh Polycom call-log acquisition | YES as regression guard |
| Bar 310 | live microphone bar | missing/stalled regression family | continuous CloudLink meter path | YES |
| Box 310 | live microphone bar | missing/stalled regression family | continuous CloudLink meter path | YES |
| TE20 | live microphone/speaker audio | current dashboard declares unsupported | 2-second `get_live_audio_status` | YES |
| TE40 | live microphone/speaker audio | current dashboard declares unsupported | 2-second `get_live_audio_status` | YES |
| RPG 310 | live meter | no approved meter | no proven live meter | NO positive capability; YES negative regression guard |
| All five | speaker `-` / `+` | user-reported button error/hang family; exact-model reproduction where not already known | serialized set + `get_speaker_volume`; RPG step 2 | YES |
| All five | speaker mute | runtime/hang class must be checked per exact model | zero/restore through authoritative speaker volume | YES |
| TE20 / TE40 / RPG 310 | microphone mute | runtime/hang class must be checked per exact model | supported mute semantic + readback | YES |
| Bar / Box 310 | microphone `-` / `+` | visible affordance conflicts with capability | current approved contract says gain unsupported | YES only to remove/disable misleading network affordance; NO gain I/O |
| All five | `Перезагрузить устройство` | current dashboard may present actionable control while registry rejects it | no proven pre-redesign room capability | YES only to remove/disable misleading network affordance; NO reboot I/O |
| Models where exposed elsewhere | presentation control / SIP fix / TE20 Wake | no current user-reported regression in this change | preserve existing root/legacy behavior | OUT OF SCOPE for new functionality; regression must not be introduced |

Every `In scope = YES` row requires an acceptance test appropriate to its capability. A user-reported family-level row cannot be closed merely because another model passed.

## Hardware availability and acceptance gate

### Availability at this architecture revision

Availability is an explicit architecture input, not an implementation assumption.

| Exact model | Availability status for this change | Consequence |
| --- | --- | --- |
| CloudLink Bar 310 | **CONFIRMED AVAILABLE** from prior real-device protocol work | affected Bar scenarios MUST pass on the exact published implementation SHA before independent `APPROVE` |
| CloudLink Box 310 | **UNCONFIRMED** | status MUST be resolved to AVAILABLE or UNAVAILABLE before final architecture `APPROVE` |
| Huawei TE20 | **UNCONFIRMED** | status MUST be resolved to AVAILABLE or UNAVAILABLE before final architecture `APPROVE` |
| Huawei TE40 | **UNCONFIRMED** | status MUST be resolved to AVAILABLE or UNAVAILABLE before final architecture `APPROVE` |
| Polycom RPG 310 | **UNCONFIRMED** | status MUST be resolved to AVAILABLE or UNAVAILABLE before final architecture `APPROVE` |

No implementation phase may start while an availability row remains `UNCONFIRMED`.

### Gate rules

1. For every model marked `AVAILABLE`, all affected hardware scenarios are **mandatory independent-validation gates** on the exact published implementation SHA. Missing/failed required hardware evidence yields `CHANGES REQUIRED`; green offline tests cannot override it.
2. Hardware evidence records at minimum:

```text
published implementation SHA
exact model
operation
non-secret request/method path
raw outcome category or success marker
normalized field/result
GUI result
UI unlocked afterward: yes/no
```

3. For a model marked `UNAVAILABLE`, offline integration tests may validate implementation structure, but hardware-specific defects for that model SHALL remain explicitly `hardware-unverified`; the final report, Linear issue state, and merge summary SHALL NOT claim them proven fixed.
4. An unavailable model cannot be silently treated as passing. If the product owner requires full five-model proof before merge, unresolved hardware availability becomes a merge blocker.
5. Hardware evidence from another commit/branch is not acceptance evidence for the current published SHA.

## Validation strategy

### Offline regression layers

1. **Protocol/handler regression:** existing model methods retain expected behavior.
2. **Parser/normalizer integration:** transport-edge fake -> actual parser/normalizer -> accepted room snapshot, including static microphone evidence.
3. **Composition integration:** real `MainWindow` / room coordinator/controller / `InteractiveSessionController` path with only device transport substituted.
4. **Presentation regression:** the new dashboard receives real normalized outputs; unsupported controls are not falsely actionable.
5. **Cross-lifecycle regression:** automatic preview never retires LIVE; explicit journal retires/resumes LIVE correctly; mutations/refreshes release locks on every terminal path.

Snapshot-only tests are useful but cannot be sole evidence for an affected codec defect.

### Hardware acceptance scenarios

For each model marked AVAILABLE, run every applicable `In scope = YES` row from the defect/action inventory. Minimum sets include:

- CloudLink Bar/Box: explicit journal; static microphone/speaker display; live microphone bar; supported speaker `-/+` and mute; Local Refresh; misleading mic-gain/reboot affordances are not network-actionable; UI unlock after success/failure.
- TE20/TE40: explicit journal; speaker controls; microphone mute; restored live microphone/speaker audio; Local Refresh; no permanent lock.
- Polycom RPG 310: explicit journal; speaker `-/+` with step 2; speaker/microphone mute; Local Refresh; no fabricated live meter; no permanent lock.

## Risks

- Reusing old widget code directly would create duplicate authority. Mitigation: reuse behavior below the presentation boundary only.
- Targeted reconciliation could update unrelated cache fields. Mitigation: merge only the confirmed canonical field and preserve the rest of the accepted snapshot.
- Deferring automatic preview may leave the preview card empty longer. This is acceptable; LIVE and explicit journal correctness have priority.
- Hardware/firmware can invalidate an old assumption. Contradictory real-device evidence wins, but changing the matrix requires architecture review rather than an implementation-only downgrade.

## Rollback

Implementation is isolated to codec room interaction composition, dispatch capability declarations, parser/normalization edges, and related tests/presentation. If a fix introduces new regressions, revert focused implementation commits; do not revert the whole room UI redesign or rewrite protocol handlers without evidence.
