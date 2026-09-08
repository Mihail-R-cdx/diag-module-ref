# Design: Codec interaction parity restoration

## Context and status

The change is back in the OpenSpec / Design phase. Published implementation `467f2cbb502f698476f047d277052bf5ccb55147` passed offline validation but real-device testing exposed architecture defects. Amendment `969e4a55e44a4f6879daa5c664de812141fa1704` then received independent architecture verdict `CHANGES REQUIRED` with four HIGH and one MEDIUM findings. Remediation `918a046a4f525a3f2fede8dc142e6c1e8fbcf295` resolved the root-spec replacement and lifecycle ambiguity findings and left TE40 gain plus Box LIVE protocol facts as explicit discovery gates.

Authorized TE40 hardware discovery is now sufficient to close the TE40 gain gate. This amendment promotes TE40 microphone gain to an exact supported capability with a fixed setter/range/step/readback contract. Box 310 remains a separate unresolved discovery gate because no complete Box response envelope/device-role evidence is currently available.

Authority remains:

`RULES.md -> current root OpenSpec -> approved change -> source/tests -> Git diff -> runbooks -> agent reports`

The legacy `CodecScreen`/`c442152077dd8aa6251f1d8be9fc98b765406dbd` is behavioral evidence only. Current hardware evidence may invalidate a historical assumption. A state-changing capability is approved only when its target semantics and reconciliation boundary are explicit.

## Review findings and architectural resolution

### 1. TE40 microphone gain versus current root capability

Root OpenSpec previously declared `Huawei TE40 microphone_adjust = UNSUPPORTED`. The first amendment incorrectly overlaid that with a second `ADDED` matrix saying `YES`; remediation `918a...` correctly restored archive-compatible root replacement and kept TE40 fail-closed pending proof.

Authorized hardware discovery now proves the missing state-changing contract, so the root-compatible `MODIFIED` matrix becomes:

| Exact model | speaker_adjust | speaker_mute | microphone_adjust | microphone_mute | reboot |
| --- | --- | --- | --- | --- | --- |
| Huawei TE20 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| Huawei TE40 | SUPPORTED | SUPPORTED | **SUPPORTED** | SUPPORTED | UNSUPPORTED |
| CloudLink Bar 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| CloudLink Box 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| Polycom RPG 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |

TE40 keeps two independent authorities:

```text
static configured microphone gain -> micValue -> canonical microphone_volume
microphone mute state              -> MicSwitch / approved equivalent -> canonical microphone_muted
```

Numeric configured gain never becomes mute state merely because the numeric value is zero.

TE20 and RPG310 remain true mute-only microphone mutation models in this scope.

### 2. TE40 gain protocol is now an approved exact state-changing contract

The authorized TE40 web UI and network capture establish the primary room-control target as `MIC1`.

Native display and device/wire domains are:

```text
native configured gain: -12 dB .. +9 dB
native adjustment step: 1 dB
wire mic1Value range:   0 .. 21
wire step:              1
mapping:                gain_db = mic1Value - 12
                        mic1Value = gain_db + 12
```

Observed hardware points include `mic1Value = 21 -> +9 dB` and `mic1Value = 18 -> +6 dB`; the repository's pre-existing TE40 numeric range evidence is `0..21`. One room `-`/`+` intent therefore means exactly `-1 dB` / `+1 dB` and cannot be chosen by implementation.

The setter boundary is:

```text
POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams
```

The native request carries current audio-input state including `micall`, `mic1..mic18` and `mic1Value..mic18Value` fields plus session/CSRF material. A room MIC1 gain mutation SHALL construct the outgoing request from current/fresh accepted audio-control state and change only target `mic1Value`; unrelated channel enable/value state must be preserved rather than replaced by zeros or guessed defaults. Secrets remain under existing credential/session authority and never enter logs/evidence.

Observed success response:

```json
{"success":1,"data":""}
```

is acknowledgement only. It is not final-state authority.

Mandatory post-write reconciliation uses the existing exact-model TE40 `get_audio_status` binding:

```text
WEB_InitAudioCtrlParamsAPI -> numeric micValue
```

The accepted readback must equal the requested wire target for the same exact row/generation/currentness. Missing/malformed/mismatched/stale readback or any ambiguous post-submit outcome enters the root blocked/unconfirmed mutation state. No blind repeat/retry of a possibly delivered gain command is allowed.

Microphone mute remains a separate supported desired-state/readback operation. `WEB_OpenMicAPI` / `WEB_CloseMicAPI` or equivalent approved mute path is not reused for gain.

### 3. Audio-card presentation replaces the conflicting root contract

The previous root contract allowed one modern microphone meter, declared TE20/TE40 unsupported for it, and prohibited a second speaker-level indicator. Hardware shows TE20/TE40 have authoritative live microphone and speaker activity via `get_live_audio_status`.

The root visual requirements are therefore explicitly `MODIFIED` by this change. The fixed Audio-card order remains:

```text
Микрофон (уровень)     <live horizontal meter or explicit unsupported/no-data state>
Динамик (уровень)      <live horizontal meter or explicit unsupported/no-data state>
Громкость микрофона    <configured value> [model-appropriate controls]
Громкость динамиков    [−] <accepted value/percentage or Нет данных> [+] [mute]
```

Live-meter support matrix:

| Exact model | Mic live meter | Speaker live meter |
| --- | --- | --- |
| Huawei TE20 | SUPPORTED from `MicValueIndex` | SUPPORTED from `SpeakerValueIndex` |
| Huawei TE40 | SUPPORTED from `MicValueIndex` | SUPPORTED from `SpeakerValueIndex` |
| CloudLink Bar 310 | SUPPORTED from approved CloudLink mic LIVE | UNSUPPORTED |
| CloudLink Box 310 | target SUPPORTED after Box live-response contract is proven | UNSUPPORTED |
| Polycom RPG 310 | UNSUPPORTED | UNSUPPORTED |

Unavailable supported telemetry renders `Нет данных`; an unsupported meter slot renders `Не поддерживается` or equivalent explicit non-color semantics. Rendering itself performs no network I/O.

For TE40:

```text
Громкость микрофона = static configured micValue transformed to -12..+9 dB
Микрофон (уровень)  = live MicValueIndex
```

These are different authorities. The dashboard must not show redundant textual `Live микрофон` / `Live динамик` rows when the two meter slots are present.

TE40 microphone `-`/`+` is now supported: each eligible click changes exactly `1 dB` through the common mutation lifecycle. The GUI displays dB but does not create mutation authority by reparsing arbitrary display strings; typed target construction comes from current accepted canonical state plus exact-model mapping. Mute remains independent.

### 4. TE40 camera parsing

`WEB_GetLocalCameraList.itemList` is a zero-to-many collection. Parsing must not require `len(itemList) >= 2`.

For each present entry the handler/parser may process state independently and use the existing approved port/type lookup for active cameras. Exactly one valid camera record is sufficient to publish known camera state/model evidence when available.

### 5. Initial three-call preview lifecycle

The product requirement is not a background fetch for every collapsed codec. It is a mandatory preview for the **exact current expanded codec row**.

The lifecycle boundary is explicit and compatible with current root room authority:

```text
entire automatic room cycle reaches terminal state
+ exact codec row is current / expanded / connected / usable / call-log-capable
+ no terminal initial-preview attempt exists for this exact row + room generation
        ↓
one fresh serialized call-history AUXILIARY_READ
        ↓
model-specific retrieval + shared normalization + newest-first
        ↓
publish up to 3 newest preview records
        ↓
bounded cleanup/release
        ↓
first LIVE may start for that exact row if still current/eligible
```

Consequences:

- no call-log network request is started for a collapsed/non-current row merely to prefill its card;
- a row already expanded when the whole automatic room cycle becomes terminal gets the mandatory preview immediately;
- if no codec row is expanded at terminal time, no hidden preview runs; the first later eligible expansion starts its one generation-bound preview before first LIVE for that row;
- switching to another codec row in the same room generation may trigger that row's own first preview if it has not yet completed one;
- collapse/re-expand of the same exact row in the same generation does not create another automatic network acquisition once its generation-bound initial attempt is terminal;
- resize, repaint, theme switch, duplicate Qt signals and rebuild create zero automatic call-log I/O;
- top full Refresh/new room generation creates a new freshness boundary;
- LIVE priority can no longer produce a local automatic-preview skip because the initial preview is ordered before first LIVE.

Ordinary preview parse/business/no-data failure reaches bounded cleanup, keeps an otherwise connected row usable, and then permits first LIVE if still eligible. Typed terminal session/connection/auth failures retain current degradation rules.

### 6. Explicit detailed journal remains separate

Every explicit `Развернуть` is a fresh operator auxiliary intent:

```text
operator opens detail
-> retire LIVE if active
-> bounded cleanup/release
-> fresh exact-row call-history AUXILIARY_READ
-> accept detailed rows/statistics only from that fresh result
-> cleanup
-> resume LIVE only if same row remains current/usable/eligible
```

The inline three-call preview is not detailed/statistics authority and never substitutes for explicit freshness.

### 7. Bar 310 evidence must not be copied into the unresolved Box 310 parser

A current authorized **Bar 310** capture shows `WEB_GetCurrentAudioParam` returning `data` that contains fixed fields including `mic1ValueIndex`, `mic2ValueIndex` and `micArray*_ValIdx`. That evidence belongs to Bar 310 only.

Earlier authorized **Box 310** evidence is different and currently limited to multiple records shaped like:

```json
{"deviceId": <number>, "curVolume": <number>}
```

Because the Box device is not currently available, the complete Box response envelope/container, device-role semantics, microphone filtering and normalization range cannot yet be proven. Therefore:

- the Bar `mic*ValueIndex` schema SHALL NOT be copied to Box;
- the earlier Box `{deviceId, curVolume}` shape remains valid discovery evidence;
- `max(all curVolume)` remains unapproved because not every record is yet proven to be microphone evidence;
- no new Box parser implementation may replace one assumption with another before the Box gate closes.

Before architecture APPROVE, authorized Box discovery must capture a redacted complete response envelope and document one of:

1. the relevant collection is contractually/empirically microphone-only; then `max(valid microphone curVolume)` may use every record in that collection; or
2. the collection mixes roles; then define an authoritative microphone filter/device-role mapping before aggregation.

The eventual Box parser contract must also define the envelope/container path, numeric validity rules, empty/malformed behavior, exact Box identity, aggregation and normalization range.

### 8. Existing room safety remains unchanged

All network work remains under one application-owned serialized room interaction lane. Exact current row/generation/model/IP/credential/currentness authority remains mandatory. State-changing operations still require live retirement, one send, authoritative reconciliation, and root blocked/unconfirmed behavior if final state cannot be confirmed. No blind replay is authorized.

Speaker zero/restore mute remains fail-closed: if current speaker volume is `0` and no proven exact-row/generation positive restore evidence exists, Unmute is local unavailable with zero mutation/session/device I/O.

Polycom speaker step remains `2`. CloudLink microphone gain and reboot for all five codecs remain unsupported.

## Acceptance inventory for the amended design

| Area | Required result |
| --- | --- |
| TE40 static mic | numeric `micValue` reaches canonical `microphone_volume`; UI maps `0..21` to `-12..+9 dB`; mute remains independent |
| TE40 mic mutation | SUPPORTED for MIC1; exactly `1 dB` per +/-; `WEB_SaveAudioMicCtrlParams`; preserve unrelated payload state; ACK not authority; `WEB_InitAudioCtrlParamsAPI.micValue` readback required |
| TE40 LIVE | `MicValueIndex` and `SpeakerValueIndex` feed two meter slots; no duplicate textual live rows |
| TE40 camera | exactly one valid camera entry is processed |
| Auto call preview | current expanded usable codec, after whole room cycle terminal, fresh once per row/generation, before first LIVE, up to 3 newest |
| Explicit journal | always fresh and separate from preview |
| Bar LIVE evidence | current fixed-field capture remains Bar-specific and is not promoted to Box evidence |
| Box LIVE | earlier `{deviceId, curVolume}` evidence retained; final parser waits for full envelope + microphone-role evidence |
| Speaker controls | preserve exact ranges/steps/readback and no-restore safety |
| Bar/Box gain | unsupported, zero gain I/O |
| Reboot | unsupported, zero reboot I/O |
| Cleanup/currentness | no stale publication, no concurrent owner, no permanent UI/lane lock |

## Hardware and validation gates

All five models remain listed as `AVAILABLE` historically, but current immediate hardware access does not include Box 310. Availability claims SHALL NOT substitute for fresh evidence.

Before **architecture APPROVE**:

1. Box 310 full live-response envelope/device-role discovery complete and reflected in OpenSpec;
2. repository-local `.\openspec.cmd validate codec-interaction-parity-restoration --strict` passes;
3. repository-local `.\openspec.cmd validate --all --strict` passes;
4. disposable archive-applicability check passes for all MODIFIED requirements/scenarios;
5. independent architecture review returns a permitting verdict.

TE40 protocol discovery is no longer an open architecture gate; it is now normative contract evidence that must be reviewed with this amendment.

Only after the remaining Box gate and architecture-validation gates close may post-amendment production implementation start.

After implementation, all focused/full offline validation and exact-SHA hardware acceptance must be repeated. Evidence from `467f2cbb...` remains discovery evidence only.
