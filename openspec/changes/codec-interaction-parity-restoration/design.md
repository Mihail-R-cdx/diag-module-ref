# Design: Codec interaction parity restoration

## Context

The current room codec dashboard is visually acceptable but real-device testing shows that key codec interactions no longer behave like the pre-redesign application. The first implementation of this change reached published SHA `467f2cbb502f698476f047d277052bf5ccb55147` and passed independent offline validation, but hardware testing then exposed several architecture assumptions that were incomplete or incorrect.

This amendment therefore reopens the OpenSpec/design phase. `467f2cbb...` remains a historical pre-hardware baseline, not a final acceptance candidate.

The change continues to preserve current exact-row authority, one serialized network lane, currentness tokens, application-owned credential fallback, typed failure handling, redaction, bounded cleanup, no Qt-thread network I/O, and root blocked/unconfirmed mutation safety.

## Source of truth

Authority remains:

`RULES.md -> current root OpenSpec -> approved change -> source/tests -> Git diff -> runbooks -> agent reports`

For this regression family, `c442152077dd8aa6251f1d8be9fc98b765406dbd` remains a behavioral oracle for operations demonstrably supported immediately before `codec-diagnostic-modern-ui`. It is not architectural authority. Current real-device evidence may invalidate an old assumption, but newly discovered state-changing protocol details must be verified rather than guessed.

## Hardware-discovered findings after `467f2cbb...`

### 1. TE40 numeric microphone gain was incorrectly classified as unsupported

The prior matrix treated TE40 microphone control as mute-only. Hardware/operator evidence and retained handler parsing show that TE40 exposes numeric `micValue` independently from `MicSwitch`. The dashboard currently renders a microphone gain row with `Нет данных`, while numeric gain evidence exists in the device response.

The amended architecture therefore separates:

```text
TE40 microphone gain
  static read evidence -> micValue
  canonical field      -> microphone_volume
  mutation             -> YES, but setter protocol must be verified before implementation

TE40 microphone mute
  static read evidence -> MicSwitch / approved equivalent
  canonical field      -> microphone_muted
  mutation             -> set_microphone_mute / approved mute path
```

A numeric gain value, including `0`, is not mute evidence. The existing compatibility wrapper that maps `0` to mute and positive values to unmute is not an acceptable TE40 gain implementation.

### 2. TE40 gain write protocol is an implementation prerequisite

The accessible Git history proves numeric readback but does not retain a trustworthy independent gain-setting command. Before production implementation, the implementation session must recover/verify the actual TE40 gain setter: method/ActionID, payload, allowed range/step and authoritative post-write numeric readback.

No implementation may guess an endpoint or repurpose `WEB_OpenMicAPI` / `WEB_CloseMicAPI` as gain adjustment. If the setter cannot be proven, implementation stops with a blocking finding and the matrix must return to architecture review rather than silently downgrading the capability.

### 3. TE40 live telemetry presentation is semantically duplicated

`get_live_audio_status` provides live `MicValueIndex` and `SpeakerValueIndex`. The modern dashboard currently has an existing microphone level meter but TE40 can simultaneously render that meter as unsupported while showing separate textual `Live микрофон` / `Live динамик` rows.

The amended presentation contract is:

```text
Микрофон (уровень) <- MicValueIndex live evidence
Динамик (уровень)  <- SpeakerValueIndex live evidence

Громкость микрофона <- static/configured micValue
Громкость динамиков <- static/configured speakerValue
```

Static configuration and live activity are separate authorities. Redundant textual `Live микрофон` / `Live динамик` rows are removed when the meter presentation exists.

### 4. TE40 camera parser incorrectly assumes two camera rows

The current handler enters camera normalization only when `len(itemList) >= 2`. A valid TE40 with one returned camera record can therefore display `Нет данных`.

The amended contract treats `WEB_GetLocalCameraList.itemList` as zero-to-many records. Every present entry is processed independently. A single valid active camera must produce known camera status/model evidence when available.

### 5. Initial call preview must always show the three newest calls

The prior architecture intentionally allowed automatic preview to terminate locally when LIVE had priority. Hardware/product review rejects that behavior: every supported codec must attempt to acquire and display the three newest calls automatically after initial connection, without requiring `Развернуть`.

The amended lifecycle moves network preview acquisition before first LIVE start:

```text
initial room diagnostic accepted/usable
-> one fresh exact-row call-history acquisition
-> normalize newest-first
-> publish up to 3 preview records
-> bounded cleanup
-> start LIVE if model/current row remains eligible
```

The automatic network acquisition is once per current room generation/exact row, not once per expansion. Collapse/re-expand and re-render use accepted preview state and cause zero automatic network I/O. A top full Refresh/new room generation creates a new initial acquisition boundary.

Explicit `Развернуть` remains separate and always fresh:

```text
operator opens detail
-> retire LIVE if active
-> fresh exact-row call-history AUXILIARY_READ
-> accept detailed rows/statistics only from that fresh result
-> bounded cleanup
-> resume LIVE if still eligible/current
```

### 6. Box 310 live parser uses the wrong response shape

Hardware shows `WEB_GetCurrentAudioParam` microphone evidence as records containing `{deviceId, curVolume}`. The current Box normalizer expects fixed fields such as `mic1ValueIndex` and `micArray*_ValIdx`, so valid hardware data can normalize as unavailable.

The Box path remains model-specific:

```text
Box WEB_GetCurrentAudioParam
-> find hardware-observed records containing deviceId + curVolume
-> keep valid non-negative numeric curVolume values
-> raw live level = max(valid curVolume)
-> apply existing display normalization
```

A shared numeric helper may be reused, but Box endpoint/response extraction and exact identity remain independent from Bar 310. The parser must not depend on the superseded fixed-field schema.

## Architectural decisions

### A. Preserve current dashboard and application ownership

Do not resurrect `CodecScreen` as room authority and do not route room widgets directly to handlers. The dashboard emits safe intents. Application/controller/session composition resolves those intents from the exact current row and the single exact-model registry.

`diagnostic_dispatch` remains the sole codec network-capability authority.

### B. Amended exact-model capability matrix

| Exact model | Speaker adjust | Speaker range / step | Speaker readback | Speaker mute | Mic mute | Mic gain adjust | Mic gain readback | Reboot | Call log | LIVE telemetry | Local Refresh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Huawei TE20 | YES | `0..21`, step `1` | `get_speaker_volume` | YES, authoritative zero/restore using proven restore evidence | YES | NO | N/A | NO | YES | YES; room-owned `get_live_audio_status`, 2 s, mic + speaker | YES |
| Huawei TE40 | YES | `0..21`, step `1` | `get_speaker_volume` | YES, authoritative zero/restore using proven restore evidence | YES | **YES, independent numeric gain** | numeric `micValue`; setter contract must be verified before implementation | NO | YES | YES; room-owned `get_live_audio_status`, 2 s, mic + speaker | YES |
| CloudLink Bar 310 | YES | `0..15`, step `1` | `get_speaker_volume` | YES, authoritative zero/restore using proven restore evidence | NO separate approved capability | NO | N/A | NO | YES | YES; existing Bar live path | YES |
| CloudLink Box 310 | YES | `0..15`, step `1` | `get_speaker_volume` | YES, authoritative zero/restore using proven restore evidence | NO separate approved capability | NO | N/A | NO | YES | YES; Box-specific `{deviceId, curVolume}` live extraction | YES |
| Polycom RPG 310 | YES | `0..100`, step **`2`** | `get_speaker_volume` | YES, authoritative zero/restore using proven restore evidence | YES | NO | N/A | NO | YES | NO | YES |

Matrix notes:

- Polycom step remains `2`.
- Speaker mute/unmute remains governed by the root restore-authority contract: positive accepted evidence may be remembered for the same exact row/generation; mute targets `0`; unmute at `0` without proven positive restore evidence is local unavailable with zero I/O.
- TE40 microphone gain and microphone mute are separate. Gain never uses mute readback and mute never infers state from gain.
- TE20, Bar, Box and RPG310 gain support does not change in this amendment.
- Reboot remains unsupported for all five.
- TE30/TE50/TE60 expansion is a later scope and is not inferred here.

### C. Amended static audio normalization

| Exact model | Authoritative source evidence | Canonical accepted evidence | Presentation |
| --- | --- | --- | --- |
| Huawei TE20 | `mic_mute` / approved equivalent | `microphone_muted: bool` | mute state; no numeric gain |
| Huawei TE40 | numeric `micValue`; independent `MicSwitch`/mute evidence | `microphone_volume: number`; independently `microphone_muted: bool` | numeric gain plus separate mute control/state |
| CloudLink Bar 310 | diagnostic `mic_volume`; mute only where authoritative | numeric `microphone_volume`; optional independent mute | numeric value where received |
| CloudLink Box 310 | diagnostic `mic_volume`; mute only where authoritative | numeric `microphone_volume`; optional independent mute | numeric value where received |
| Polycom RPG 310 | authoritative mute evidence | `microphone_muted: bool` | mute state; no numeric gain |

Transport-edge regression tests must exercise actual parser/normalizer -> accepted room snapshot -> common dashboard. Prebuilt canonical snapshots are insufficient sole evidence.

### D. Initial three-call preview precedes LIVE

The previous LIVE-priority local skip is removed. For each call-log-capable current exact row/generation:

1. wait until initial room diagnostic has produced an accepted/usable exact row;
2. admit one fresh serialized call-history preview acquisition;
3. apply existing exact-model retrieval and shared normalization/newest-first chronology;
4. publish at most three newest records into preview-owned state;
5. reach bounded cleanup on success or failure;
6. only then start first LIVE if the exact row remains current/eligible.

If another non-LIVE lifecycle is retiring, preview may wait behind its bounded handoff. No concurrent owner is introduced. Ordinary preview failure does not permanently degrade a connected row and does not prevent LIVE after cleanup; typed connection/session/authentication terminal failures keep existing degradation semantics.

Expansion is presentation-only for automatic preview. Collapse/re-expand, resize, theme switch, duplicate Qt notifications and re-render never cause another automatic acquisition in the same generation.

### E. Explicit call log remains fresh and independent

Every explicit `Развернуть` is a fresh operator intent. Existing three-record preview never substitutes for the detailed result or usage statistics. If LIVE is active, it retires before explicit handler/session acquisition and resumes only after bounded terminal cleanup if the same row remains current/usable.

### F. Live telemetry presentation

#### CloudLink Bar 310

Continue the approved Bar live meter path. Do not change it merely because Box uses a similar record shape.

#### CloudLink Box 310

Use the actual Box endpoint and Box-specific response extraction. Aggregate valid numeric `curVolume` values using `max`. Do not alias exact Box identity to Bar.

#### Huawei TE20 / TE40

Keep one room-owned `get_live_audio_status` binding at the proven 2-second cadence unless hardware requires a bounded change. Accepted live evidence maps:

```text
MicValueIndex     -> live microphone meter
SpeakerValueIndex -> live speaker meter
```

The existing `Микрофон (уровень)` progress meter must accept Huawei TE live microphone evidence. Add/use a dedicated `Динамик (уровень)` meter. Do not render redundant textual live rows when meter presentation is present.

#### Polycom RPG 310

No live meter is authorized.

### G. TE40 microphone-gain mutation lifecycle

Once the actual setter is verified, one gain `+`/`-` intent follows:

```text
safe dashboard intent
-> exact TE40 capability/currentness validation
-> current authoritative numeric microphone_volume
-> compute one target using verified range/step
-> retire LIVE through bounded cleanup
-> one serialized interactive generation
-> verified TE40 gain-set command(target)
-> authoritative numeric micValue readback
-> publish only reconciled microphone_volume
-> cleanup
-> resume LIVE if still eligible
```

If command delivery is ambiguous or numeric readback cannot confirm final state, root blocked/unconfirmed mutation safety applies. Never blindly replay a possibly delivered gain mutation.

Microphone mute uses its own desired-state operation/readback and does not rewrite gain evidence.

### H. TE40 camera parsing

`WEB_GetLocalCameraList.itemList` is zero-to-many. For each entry:

- parse item state independently;
- for active entries, use the existing approved camera type lookup where available;
- normalize available camera connection/model evidence;
- do not require a second entry before publishing the first.

### I. Existing targeted speaker reconciliation and no indefinite locks remain

Speaker `+`/`-`, speaker mute/unmute, Local Refresh, explicit journal, initial preview, TE40 gain mutation and LIVE retirement all keep one serialized owner and bounded release on success, structured auth exhaustion, ordinary parse/business failure, transport/session loss, cancellation, row switch, timeout and stale supersession.

A full diagnostic refresh is not required solely to confirm an audio mutation when a targeted authoritative readback exists.

## Explicit defect/action inventory after hardware discovery

| Exact model | Action/evidence | Current hardware result / concern | Amended required result | In scope |
| --- | --- | --- | --- | --- |
| TE40 | numeric microphone gain display | `Нет данных` despite numeric `micValue` evidence | display authoritative numeric gain | YES |
| TE40 | microphone gain `-` / `+` | not working under current mute-only contract | independent numeric gain mutation + numeric readback after protocol verification | YES |
| TE40 | microphone mute | separate supported function | remain independent from gain | YES |
| TE40 | live microphone presentation | live evidence exists but separate textual row conflicts with meter | `Микрофон (уровень)` meter | YES |
| TE40 | live speaker presentation | live evidence exists as textual row | `Динамик (уровень)` meter | YES |
| TE40 | camera | `Нет данных`; current parser requires >=2 records | process 0..N records; one valid camera is sufficient | YES |
| TE40 | automatic three-call preview | not shown until `Развернуть` | one fresh initial acquisition; show up to 3 newest before LIVE | YES |
| TE40 | explicit journal | fresh data appears on explicit action | preserve fresh explicit acquisition | YES |
| Box 310 | live microphone | hardware data not accepted by fixed-field parser | parse `{deviceId, curVolume}` records and max valid value | YES |
| All five | automatic three-call preview | previous architecture could skip under LIVE | mandatory one fresh initial acquisition per generation before LIVE | YES |
| All five | explicit journal | separate operator action | always fresh; never satisfied by preview | YES |
| All five | speaker `-` / `+` and mute | prior scope | preserve exact range/step/readback and restore-authority rules | YES |
| Bar/Box | microphone gain | unsupported | remain non-actionable, zero gain I/O | YES negative guard |
| All five | reboot | unsupported | remain non-actionable, zero reboot I/O | YES negative guard |
| RPG310 | live meter | unsupported | no fabricated meter | YES negative guard |

All prior in-scope rows from the original design remain required unless explicitly superseded above.

## Hardware availability and acceptance gate

All five exact models remain `AVAILABLE`: Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, Polycom RPG 310.

Hardware observations against `467f2cbb...` are discovery evidence only. Final acceptance must run against the exact published post-amendment implementation SHA. Missing or failed required hardware evidence yields `CHANGES REQUIRED` regardless of offline test count.

Hardware evidence records at minimum:

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

For TE40 microphone gain, hardware evidence must additionally record the verified non-secret setter method/ActionID and prove numeric readback changes by the expected step without altering mute state unintentionally.

## Validation strategy

### Architecture amendment gate

Before implementation:

1. run repository-local strict validation for this change and all changes;
2. perform disposable archive-applicability check because MODIFIED root requirements changed again;
3. obtain a new independent architecture `APPROVE`;
4. record the new approved architecture SHA.

### Implementation/offline regression layers

1. protocol/handler regression;
2. TE40 gain protocol-discovery proof and targeted readback tests;
3. TE40/CloudLink parser-normalizer transport-edge tests;
4. composition integration through room coordinator/controller/session;
5. presentation regression for static gain vs live meters and one-camera TE40;
6. initial-preview-before-LIVE ordering and three-record preview tests for all five;
7. explicit journal retirement/resume and fresh-detail tests;
8. mutation blocked/unconfirmed and no-stuck-lock tests;
9. full offline suite and strict OpenSpec validation.

### Hardware acceptance minimums

- TE40: Local Refresh; three-call initial preview; explicit journal; numeric microphone gain read/set/readback; separate mic mute; live mic/speaker meters; one-camera detection; speaker controls; no-stuck cleanup paths.
- Box310: corrected live microphone parser on actual `{deviceId, curVolume}` response; three-call initial preview; explicit journal; speaker controls; Local Refresh.
- TE20/Bar310/RPG310: regression of existing applicable actions plus mandatory three-call initial preview before LIVE where applicable.

## Risks

- The TE40 setter is not yet recovered in the accessible Git history. Mitigation: protocol discovery is a blocking implementation prerequisite; never guess.
- Moving initial preview before LIVE delays first LIVE start by one bounded auxiliary acquisition. Mitigation: one request per generation, bounded timeout/cleanup, no repeated expansion-driven reads.
- Device firmware may vary in camera/live response shape. Mitigation: normalize actual structured evidence conservatively and cover transport-edge variants without fabricating values.
- Hardware can invalidate another old assumption. Mitigation: contradictory device evidence returns the change to architecture review rather than silent implementation downgrade.

## Rollback

Implementation remains isolated to codec room interaction composition, dispatch capabilities, model parser/normalization edges, presentation and tests. If post-amendment implementation regresses, revert focused implementation commits; do not revert the whole room UI redesign or weaken root lifecycle/security contracts.
