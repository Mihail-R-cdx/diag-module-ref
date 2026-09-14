# Design: Codec interaction parity restoration

## Context and status

The change is back in the OpenSpec / Design phase. Published implementation `467f2cbb502f698476f047d277052bf5ccb55147` passed offline validation but real-device testing exposed architecture defects. Amendment `969e4a55e44a4f6879daa5c664de812141fa1704` received independent `CHANGES REQUIRED`; remediation `918a046a4f525a3f2fede8dc142e6c1e8fbcf295` resolved root-spec replacement and lifecycle ambiguity; `df5447abe556d53ce3d7fd2a2a56e1c042918272` then closed the TE40 setter/range/step gap as understood at that stage.

Independent review of `df5447...` found two remaining HIGH findings:

1. Box 310 LIVE was still declared as a target-supported capability without a complete implementable parser contract.
2. TE40 `WEB_SaveAudioMicCtrlParams` could be built from previously accepted full-state audio data and therefore could overwrite a concurrently changed non-target microphone value while reconciling only MIC1.

This amendment resolves both at architecture level. It does not change production code.

After architecture approval of content SHA `11af77b14010c34ae2d33de816678a6724971caa`, real TE40 hardware evidence exposed two in-scope defects: session-bound initial expansion was not adopted by coordinator preview admission, and monitor-audio microphone telemetry may be carried by `micArray<N>_<NN>ValIdx` fields rather than `MicValueIndex` alone. This amendment defines their minimal contracts and requires a new independent architecture review before implementation.

Hardware acceptance of `01226c6620932db01424a06211ba7292c6efc164` found a further TE40 LIVE boundary mismatch: browser-proven dynamic audio uses `WEB_GetCurrentAudioParam`, whose decoded JSON-string payload exposes `mic<N>ValueIndex` as well as `micArray<N>_<NN>ValIdx`. This OpenSpec-only amendment supersedes the prior TE40 `WEB_GetMonitorAudioParam` source authority for initial seed and periodic LIVE; production implementation remains stopped pending review of this exact amendment.

Authority remains:

`RULES.md -> current root OpenSpec -> approved change -> source/tests -> Git diff -> runbooks -> agent reports`

The legacy `CodecScreen`/`c442152077dd8aa6251f1d8be9fc98b765406dbd` is behavioral evidence only.

## 1. Exact codec capability matrix

The root-compatible room-control mutation matrix remains:

| Exact model | speaker_adjust | speaker_mute | microphone_adjust | microphone_mute | reboot |
| --- | --- | --- | --- | --- | --- |
| Huawei TE20 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| Huawei TE40 | SUPPORTED | SUPPORTED | **SUPPORTED** | SUPPORTED | UNSUPPORTED |
| Huawei TE50 | SUPPORTED | SUPPORTED | **SUPPORTED** | SUPPORTED | UNSUPPORTED |
| CloudLink Bar 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| CloudLink Box 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| Polycom RPG 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |

Post-cycle LIVE is a separate optional capability owned by the same exact-model registration. Its amended support matrix is:

| Exact model | microphone LIVE |
| --- | --- |
| Huawei TE20 | SUPPORTED from raw `MicValueIndex`, normalized `0..220 -> 0..100%` |
| Huawei TE40 | SUPPORTED from `WEB_GetCurrentAudioParam`: `max(valid MicValueIndex + valid mic<N>ValueIndex + valid micArray<N>_<NN>ValIdx + rcaLInValueIndex + rcaRInValueIndex)`, normalized `0..220 -> 0..100%` |
| Huawei TE50 | SUPPORTED by exact-model reuse of the TE40 contract; pending TE50 hardware acceptance |
| CloudLink Bar 310 | SUPPORTED from approved Bar-specific LIVE parser |
| CloudLink Box 310 | **UNSUPPORTED / DEFERRED in this change** |
| Polycom RPG 310 | UNSUPPORTED |

The unified exact-model registry SHALL advertise no Box 310 post-cycle LIVE binding in this change. Runtime SHALL NOT infer Box LIVE from shared handler type, endpoint presence, old widget behavior, or historical Bar/Box sharing.

Huawei TE50 is an explicit sixth exact model, not a `TE*` or Huawei-family alias. By declared product protocol equivalence it reuses the approved TE40 handler/session/authentication, static diagnostics, status/uptime, microphone/camera, current-audio decode and normalization, MIC1 gain/mutation/mute, speaker, presentation, call-log/journal, Local Refresh, and preview/currentness/cleanup contracts covered here. The operation context and presented identity remain `Huawei TE50`. TE40 current-audio LIVE has recorded hardware PASS at exact SHA `43fa6ca247898ff661e6e2fbcc4850c561512a2f`; TE50 hardware acceptance remains pending on its own exact implementation SHA. TE30 and TE60 remain out of scope.

## 1A. TE50 inventory recognition boundary

The offline converter, not runtime, converts normalized `Модель` and `Наименование` evidence into canonical `diagnostic_model`. The closed reviewed registry gains one exact entry:

| Canonical `diagnostic_model` | Required components |
| --- | --- |
| `Huawei TE50` | `te` + `50` |

Existing component extraction already yields those exact components from `TE50`, `TE 50`, `TE-50`, `Huawei TE50`, and `Huawei_TE.50`; this amendment adds no special tokenization, alias, fuzzy match, source-model dispatch, manufacturer inference, or protocol behavior. The existing union/cardinality contract remains authoritative: one distinct TE50 match publishes exact canonical `Huawei TE50`; competing matches remain ambiguous; TE40 and TE50 remain distinct.

The importer-side expected-kind registry records `Huawei TE50 -> video_codec` only as consistency evidence. Exact source `Тип модели` remains the sole authority for canonical `device_kind`; recognition must not rewrite it. After an approved implementation of this registry change, the deployment operator regenerates ignored `equipment_inventory.local.json` from the configured organization workbook. Runtime remains JSON-snapshot-only and does not read `.xlsx`.

## 1B. Call-direction presentation boundary

Direction remains authoritative only after vendor-specific retrieval/normalization has produced typed `CallDirection`. This amendment does not change parsers, vendor mappings, acquisition, ordering, statistics, preview lifecycle, or any protocol behavior.

```text
INCOMING -> visible `Входящий` and the existing incoming cue
OUTGOING -> visible `Исходящий` and the existing outgoing cue
UNKNOWN  -> retain typed UNKNOWN; no visible direction text
```

For the detailed journal, `UNKNOWN` renders an empty direction cell rather than a dash, unavailable marker, or unknown-direction phrase. For the three-call room preview, it renders no visible direction title and no empty title row or vertical gap; a neutral icon may remain only if it does not imply incoming or outgoing. Accessibility/internal metadata may retain the unknown-direction meaning, but no visible `Направление неизвестно` text remains.

The GUI SHALL not infer an unknown direction from model, localized strings, peer number, call result, position, icon color, or other presentation heuristics. It must neither reclassify `UNKNOWN` to incoming/outgoing nor mutate the normalized typed state.

## 1C. Headerless upper peer-tile presentation boundary

The existing outer upper peer tiles remain. The left room-summary tile contains only its room-information body: no visible `Информация о комнате` title, section icon, SectionCard header, header spacer, or header chrome. Its first visible content row is `Название комнаты`, followed by `Адрес комнаты`, `Гарантия`, and `Занятость`; VIP remains associated with the name. Removing the header does not make the room body full-bleed against the outer border, so ordinary non-zero body padding remains permitted.

The right tile contains the existing canonical network summary table/tree and nothing else. It has no SectionCard header, network icon, `Сетевые подключения` text, dynamic switch-count title, header spacer, or ordinary inner padding/margins that consume table area. The table/tree fills the available right-tile area and retains headers `Коммутатор (IP)`, `Порты`, and `Подключено устройств`.

No topology, authority, lifecycle, or I/O contract changes. `switch_ip_address`, `switch_port`, deterministic grouping/ordering/counts, disclosure parents and children, same-context disclosure restoration, unknown-switch and empty-state behavior remain canonical presentation evidence under their current contracts. Rendering, reflow, repaint, and disclosure restoration start zero new device/network I/O.

## 1E. Supported codec microphone LIVE cadence

The current supported room microphone LIVE set is exactly Huawei TE20, TE40, TE50, and CloudLink Bar 310. Their shared product-level update cadence is nominally `700 ms`, but scheduler ownership remains model-specific.

Huawei TE20/TE40/TE50 retain the existing periodic room-LIVE `QTimer`: its interval changes from `2000 ms` to `700 ms`, it remains periodic, and it skips submission when the current owner already has one sample in flight. A fast completion does not create a completion-triggered timer; the next eligible submission occurs at the next periodic tick. Current row/generation/credential identity, stale rejection, request semantics, parser, aggregation, and normalization remain unchanged.

CloudLink Bar 310 retains the existing serialized single-shot owner: after a permitted completed sample cycle, its next single-shot delay is `700 ms`. Its `_in_flight` guard, generation/token matching, authentication/session behavior, terminal failure behavior, and no-overlap rule remain unchanged. It is not converted to a Huawei-style repeating timer.

This is a scheduling-only contract. It retains each exact model's approved parser, normalization, authentication/session, currentness, and protocol command boundaries. Box 310 remains explicitly deferred with no meter context/request; Polycom remains unsupported. Matrix, DMP, PDU, general refresh, call-log, authentication, cleanup, application-time-update, and other timers retain their existing cadence and behavior.

## 1D. RCA microphone aggregate and room presentation placeholders

For exact TE40 and exact-model TE50 only, the current-audio extractor additionally admits the two named RCA input fields `rcaLInValueIndex` and `rcaRInValueIndex`. It takes the maximum of all valid finite numeric microphone candidates, including numeric zero, from the existing compatibility/individual/array fields and those two RCA fields. This is not wildcard `*InValueIndex` support: `trs*`, `hdmi*`, `dvi*`, `dp*`, `pstnInValueIndex`, `sdi*`, unrelated inputs, and `SpeakerValueIndex` remain excluded. Missing or invalid candidates do not imply zero; normalization remains the existing single `0..220 -> 0..100%` presentation operation. TE20 remains `MicValueIndex`-only.

The existing one target-search field receives the descriptive visible label `Введите название помещения или IP-адрес оборудования`; all search, autocomplete, selection, Refresh, and authority semantics remain unchanged. The room summary's temporary warranty presentation is fixed as `Гарантия: Нет гарантии`. It is not canonical data and starts no lookup or I/O. Linear `MIH-28` tracks future real warranty data pending a separately reviewed authoritative source and canonical semantics.

## 2. Huawei TE20/TE40/TE50 audio-scale separation and TE40/TE50 static microphone authority

Confirmed product/device scale authority is now explicit and must not be conflated:

```text
Huawei TE20/TE40/TE50 microphone input gain: -12 dB .. +12 dB
Huawei TE20/TE40/TE50 RCA input gain:        -12 dB .. +12 dB
nominal input-gain operating value:           0 dB
Huawei TE20/TE40/TE50 speaker volume:         0 .. 21
```

The Huawei speaker `0..21` range is a separate speaker-volume scale. It is neither a microphone/RCA range nor percentage authority and SHALL NOT be used to derive configured microphone percentages.

TE20 remains without supported numeric microphone adjustment in the current application capability matrix. The confirmed TE20 input-gain scale therefore does not create a TE20 `microphone_adjust` binding or new network operation.

TE40, and exact-model TE50 by the declared reuse contract, keep two independent static microphone authorities:

```text
static configured microphone gain -> mic1Value -> canonical microphone_volume
microphone mute state              -> MicSwitch / approved equivalent -> canonical microphone_muted
```

The already established step/offset relation is retained:

```text
native configured gain: -12 dB .. +12 dB
native adjustment step: 1 dB
wire step:              1
gain_db = mic1Value - 12
mic1Value = gain_db + 12
```

Combining that established relation with the now-confirmed complete device gain range yields an admissible MIC1 wire range of `0..24`; `21` is an observed `+9 dB` point, not the microphone upper bound. Observed device points remain `18 -> +6 dB`, `21 -> +9 dB`; the corrected upper boundary is `24 -> +12 dB` by the same established offset/step relation. Numeric wire zero means `-12 dB`, not mute.

This correction changes no RCA mutation capability: RCA is recorded here only to prevent reuse of the speaker scale for input-gain semantics.

## 3. TE40 MIC1 mutation uses fresh full-state compare-and-preserve

The approved setter boundary is:

```text
POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams
```

The native save payload is full-state: it carries `micall`, microphone enable fields `mic1..mic18`, microphone value fields `mic1Value..mic18Value`, and required session/CSRF material. Therefore a previously accepted room snapshot is **not** safe payload authority.

The exact lifecycle is:

```text
operator confirms TE40/TE50 MIC1 +/-
-> exact MUTATION owns the serialized room lane
-> retire prior LIVE and finish bounded cleanup
-> fresh TE40-compatible full audio-control read
-> validate complete required non-secret save-state fields
-> construct payload only from that fresh pre-write state
-> change only target mic1Value by exactly +/-1 wire unit (= 1 dB), bounded to 0..24
-> one POST WEB_SaveAudioMicCtrlParams
-> ACK remains non-authoritative
-> fresh post-write full audio-control read
-> verify MIC1 target
-> verify preserved non-target fields against fresh pre-write baseline
-> only then publish confirmed result / resume eligible LIVE
```

### Fresh pre-write authority

The pre-write read SHALL use `WEB_InitAudioCtrlParamsAPI` through the approved TE40 audio-control/session path, or an exact already-approved equivalent only if it returns the same complete mutation-required audio-control state.

The mutation-local pre-write snapshot SHALL include every non-secret field required to preserve the save contract:

```text
micall
mic1 .. mic18
mic1Value .. mic18Value
```

Session/CSRF values remain separate secret session material and are not part of compare-state evidence.

If the fresh read is missing, malformed, stale, not current for exact row/generation, or lacks any required save-state field, the POST SHALL NOT be attempted. This is a definite pre-submit failure, not command ambiguity. After bounded cleanup the row may remain usable unless an independent typed session/connection/auth failure requires existing degradation.

### Payload construction

The payload SHALL be a copy/typed projection of the fresh pre-write state plus current required session/CSRF material. For a MIC1 gain mutation, only `mic1Value` may differ from that fresh baseline. No non-target microphone value/enable field may be filled from old room cache, guessed defaults, zeros, widget state, or a prior mutation.

### Post-write reconciliation and collateral safety

A successful response such as:

```json
{"success":1,"data":""}
```

is acknowledgement only.

Post-write reconciliation SHALL perform a fresh full audio-control read from the same authority. Final success requires:

1. exact current row/generation/currentness still matches;
2. target primary gain confirms requested MIC1 wire value through the approved canonical `microphone_volume` projection;
3. every non-target `micall`, `micN`, and `micNValue` field included in the full-state save remains equal to the fresh pre-write baseline, excluding only the intentionally changed target `mic1Value` and any explicitly documented device-derived alias of that target.

If the post-write authority cannot expose enough full state to prove these conditions, the mutation cannot be declared confirmed. Missing/malformed/stale readback, target mismatch, collateral mismatch, cancellation after possible send, or ambiguous send outcome enters the root blocked/unconfirmed state. No blind replay is authorized.

This contract intentionally detects collateral overwrite. It cannot make an external client race impossible, but it prevents the application from knowingly constructing a full-state save from stale non-target data and prevents silent success when post-write evidence shows collateral change.

Microphone mute remains separate and never reuses this gain path.

## 4. Audio-card presentation

The fixed Audio-card order is:

```text
Микрофон (уровень)     <live horizontal meter or explicit unsupported/no-data state>
Громкость микрофона    <configured value> [model-appropriate controls]
Громкость динамиков    [−] <accepted value or Нет данных> [+] [mute]
```

Huawei TE20 uses raw `MicValueIndex` for its normalized microphone LIVE meter from `get_live_audio_status`. TE40, and exact-model TE50 by the declared reuse contract, use one shared `WEB_GetCurrentAudioParam` extractor for initial seed and true LIVE: decode the JSON-string envelope, then take `max(valid MicValueIndex + valid mic<N>ValueIndex + valid micArray<N>_<NN>ValIdx + valid rcaLInValueIndex + valid rcaRInValueIndex)`, followed by the existing one-time `0..220 -> 0..100%` normalization. Configured TE40/TE50 MIC1 gain is rendered in dB separately from live microphone evidence and mute.

For Huawei TE20/TE40/TE50, the speaker configured-value row uses the distinct device scale `0..21`. That value SHALL NOT be relabelled or normalized as configured microphone gain and SHALL NOT be used to manufacture a configured MIC percentage. TE20 continues to show no numeric configured microphone gain because the application does not support that capability.

CloudLink Bar 310 keeps its approved microphone LIVE meter. CloudLink Box 310 renders `Микрофон (уровень) = Не поддерживается` in this change and starts no Box LIVE network lifecycle. Polycom renders its microphone LIVE slot unsupported.

The dashboard SHALL NOT show duplicate textual `Live микрофон` / `Live динамик` rows for Huawei.

## 5. Box 310 LIVE scope reduction

Current Bar hardware evidence proves a Bar-specific fixed-field LIVE response. Earlier Box evidence is limited to `{deviceId, curVolume}` records without a complete envelope or authoritative role mapping. The Box device is not currently available.

Rather than leave an incomplete supported capability, this change explicitly defers Box microphone LIVE restoration.

Current-change contract:

```text
exact model: CloudLink Box 310
post-cycle LIVE binding: absent
room microphone LIVE network I/O: zero
WEB_GetCurrentAudioParam as room LIVE poll: not admitted
Микрофон (уровень): Не поддерживается
```

The existing legacy compatibility transport classification of `WEB_GetCurrentAudioParam` is retained only as dormant protocol knowledge for a future approved change; it does not advertise capability or authorize polling now.

A future dedicated Box LIVE change must prove:

```text
response envelope/container
microphone record selection / device roles
numeric curVolume validity
aggregation
normalization
unavailable/error semantics
exact Box identity and lifecycle currentness
```

The Bar fixed-field response SHALL NOT be copied into that future Box contract. Earlier Box `{deviceId, curVolume}` evidence SHALL NOT become `max(all)` without role proof.

All other current Box behaviors remain in scope: diagnostics, speaker control, call log, automatic three-call preview, explicit journal, Local Refresh, currentness and cleanup.

## 6. TE40 camera parsing

`WEB_GetLocalCameraList.itemList` is a zero-to-many collection. Exactly one valid camera record must be processed; parsing SHALL NOT require `len(itemList) >= 2`.

## 7. Initial three-call preview lifecycle

The mandatory automatic preview applies to the exact current expanded call-log-capable codec row.

```text
entire automatic room cycle terminal
+ exact codec row current / expanded / connected / usable
+ no terminal initial-preview attempt for row + room generation
-> one fresh serialized call-history AUXILIARY_READ
-> normalize newest-first
-> publish up to 3 newest records
-> bounded cleanup/release
-> first eligible LIVE may start only afterward
```

When a generation-current session is bound with an existing `expanded_record_id`, coordinator ownership SHALL accept that application-owned expansion identity without starting network I/O. The normal terminal-cycle boundary, not binding or render, then admits its one preview; no synthetic Qt expand event is required.

For Box 310, the same preview runs, but there is no subsequent Box LIVE start because its live binding is absent.

Collapse/re-expand, repaint, resize, theme switch and duplicate UI events do not create a second automatic preview in the same row/generation. A new full-room generation creates a new freshness boundary.

## 8. Explicit journal

Every explicit `Развернуть` remains a separate fresh exact-row auxiliary acquisition. For models with active LIVE, LIVE retires and may resume after cleanup; for Box 310 there is no LIVE retirement/resume because Box LIVE is deferred.

## 9. Existing safety remains unchanged

All network work remains under one application-owned serialized room interaction lane. Exact row/generation/model/IP/credential/currentness authority remains mandatory. State-changing operations require one send and authoritative reconciliation; ambiguous possible-send outcomes are blocked/unconfirmed; no blind replay.

Speaker zero/restore mute remains fail-closed. Polycom speaker step remains `2`. CloudLink microphone gain and reboot for all six codecs remain unsupported.

## Acceptance inventory

| Area | Required result |
| --- | --- |
| Huawei input/speaker scale separation | TE20/TE40/TE50 MIC and RCA input gain `-12..+12 dB`, nominal `0 dB`; speaker volume `0..21`; speaker scale never becomes MIC/RCA percentage authority |
| TE40/TE50 static mic | numeric `mic1Value` -> canonical `microphone_volume` -> `-12..+12 dB`; established offset/step relation yields `0..24`; mute independent |
| TE20 static mic | numeric microphone adjustment remains unsupported in this application; confirmed device input scale does not create a new capability |
| TE40/TE50 mic mutation | fresh full pre-read after lane ownership; change only `mic1Value`; one save; full target + collateral post-read reconciliation; one-dB target bounded to confirmed `-12..+12 dB` |
| TE40 pre-read failure | no POST; no command-ambiguity block solely from pre-submit failure |
| TE40 collateral mismatch | mutation unconfirmed/blocked; no silent success/replay |
| TE40/TE50 LIVE | `WEB_GetCurrentAudioParam` microphone meter from normalized `max(valid MicValueIndex + valid mic<N>ValueIndex + valid micArray<N>_<NN>ValIdx + valid rcaLInValueIndex + valid rcaRInValueIndex)`; no speaker LIVE meter or duplicate textual live rows |
| TE40 camera | one valid camera entry is sufficient |
| TE50 inventory | `te` + `50` component evidence -> exact canonical `Huawei TE50`; expected kind `video_codec` is non-authoritative consistency evidence |
| Bar LIVE | supported under Bar-specific approved parser |
| Box LIVE | microphone LIVE explicitly unsupported/deferred; no live binding/I/O; room presentation has no speaker LIVE capability |
| Box non-LIVE | diagnostics, speaker, preview/journal, Local Refresh remain in scope |
| Auto call preview | session-bound current expanded usable row accepted without bind/render I/O; whole-cycle terminal, once per row/generation, before first eligible LIVE |
| Explicit journal | always fresh and separate |
| Speaker controls | preserve model ranges/steps/readback and no-restore safety; Huawei TE20/TE40/TE50 speaker range is `0..21` |
| Cleanup/currentness | no stale publication, concurrent owner, or permanent lock |

## Architecture validation gates

The TE40 endpoint, JSON-string envelope, and individual/array microphone fields are hardware-backed evidence; their maximum remains an application aggregation contract derived from that evidence. Before a renewed architecture `APPROVE` for this amendment:

1. `.\openspec.cmd validate codec-interaction-parity-restoration --strict` passes;
2. `.\openspec.cmd validate --all --strict` passes;
3. disposable archive-applicability check passes for all `MODIFIED Requirements` and scenarios;
4. Git hygiene checks pass;
5. independent architecture review of the exact published SHA returns a permitting verdict.

Only then may post-amendment production implementation start.

After implementation, focused/full offline validation and exact-SHA hardware acceptance must be repeated. Evidence from `467f2cbb...` remains discovery evidence only.

## 10. Latest six-model hardware-remediation architecture

This section supersedes earlier availability/pending statements in this design where they conflict with the real-device discovery pass completed on published SHA `6f90bf80671c2cb179deb60ba110e6317452cfb2`. That SHA is hardware-discovery evidence and is not an accepted implementation because in-scope scenarios failed.

### 10.1 Hardware observations and unchanged contracts

The remediation SHALL distinguish actual failures from expected unsupported/no-data states:

- `Polycom RPG 310`: speaker adjustment and speaker mute are failures. The observed `+` action produced no device change and left Audio controls disabled; speaker mute also produced no device change. Numeric microphone gain `Нет данных`, microphone LIVE `Не поддерживается`, and absent camera evidence are not by themselves failures.
- `CloudLink Bar 310`: inactive microphone gain/mute controls are expected because those mutations remain unsupported. The visible supported microphone LIVE meter remaining `Нет данных` is a failure for Bar hardware acceptance. Missing usage percentage in the detailed call-log result is also a failure when the explicit load succeeds without an approved partial/incomplete warning that explains why the percentage is unavailable. Static uptime/microphone/camera no-data values alone are not failures.
- `CloudLink Box 310`: `Микрофон (уровень) = Не поддерживается` and inactive microphone gain/mute controls are expected and confirm the deferred-LIVE presentation. Failure is the missing automatic call preview and the explicit `Развернуть` path producing no journal content. Remediation SHALL NOT create Box LIVE while fixing call-log behavior.
- `Huawei TE20`: unsupported numeric microphone gain controls/no-data are expected; unavailable call/presentation evidence may remain `Нет данных`. Failure is the explicit journal missing `Продолжительность` and usage statistics.
- `Huawei TE50`: hardware is available. The discovery run was initially interpreted as requiring TE50 configured MIC percentage presentation; subsequent product clarification corrected that interpretation. TE50 follows the same Huawei input-gain scale as TE20/TE40 (`-12..+12 dB`), while speaker volume separately uses `0..21`.
- No new TE40 protocol defect was reported in this discovery pass. The audio-scale clarification applies to TE40 as well: MIC/RCA gain is `-12..+12 dB`; speaker volume is `0..21`. Any shared-path production change made for other models still requires appropriate TE40 regression/smoke according to the touched boundary.

### 10.2 Correct Huawei input-gain versus speaker-volume contract

The latest product authority for Huawei TE20/TE40/TE50 is:

```text
microphone input gain = -12 .. +12 dB
RCA input gain        = -12 .. +12 dB
nominal input gain    = 0 dB
speaker volume        = 0 .. 21
```

These are different control domains. The speaker `0..21` scale SHALL NOT be reused as a microphone/RCA range and SHALL NOT be linearly converted into a configured microphone percentage. The previously proposed TE50 formula `floor(100 * V / 21 + 0.5)` and examples `18 -> 86%` are withdrawn and are not implementation authority.

TE20 remains `microphone_adjust = UNSUPPORTED` in the application despite sharing the device input-gain scale; this clarification does not add a TE20 numeric MIC control.

For TE40/TE50 MIC1, the established one-dB step and offset relation remains:

```text
gain_db = mic1Value - 12
mic1Value = gain_db + 12
```

With the confirmed `-12..+12 dB` device range, the corresponding accepted MIC1 range is `0..24`. This is distinct from Huawei speaker volume `0..21`. Presentation for TE40 and TE50 is dB, not percent. Examples:

```text
mic1Value=0  -> -12 dB
mic1Value=12 ->   0 dB
mic1Value=18 ->  +6 dB
mic1Value=21 ->  +9 dB
mic1Value=24 -> +12 dB
```

TE40/TE50 `−/+` request exactly one one-dB/native wire step, bounded by the corrected MIC range, through the existing typed MIC1 mutation/reconciliation contract. Independent microphone mute remains unchanged. RCA scale clarification does not introduce a new RCA mutation path.

### 10.3 RPG310 remediation boundary

The current capability oracle is unchanged:

```text
speaker_adjust = SUPPORTED
speaker_mute   = SUPPORTED
range          = 0..100
step           = 2
```

Remediation must trace the existing Polycom serialized HTTPS/SSH interaction and exact-row mutation/reconciliation lifecycle. A terminal success, typed failure, timeout, cancellation, or cleanup completion must leave the current row usable according to the existing lock matrix; a failed operation may not leave Audio controls permanently disabled. The hardware observation alone does not authorize a new command grammar, alternate blind replay, or capability downgrade. Any protocol change requires non-secret readback/command evidence and, if it contradicts the current approved protocol contract, another reviewed architecture amendment before implementation.

### 10.4 Bar310 LIVE remediation boundary

Bar microphone LIVE remains supported exactly through the approved modern-session contract and `GET /v1/mediacontrol/mic/current-volume` parser/normalization until real protocol evidence proves otherwise. The UI-level `Нет данных` observation does not itself authorize changing endpoint, token routing, list selection, aggregation, or normalization.

Implementation must first determine whether the failure is admission/lifecycle, session/token reuse, request failure category, parser rejection, or unavailable-sample publication. The investigation may record only non-secret method/path, typed category, payload shape metadata needed for review, and normalized outcome. If the real successful payload or session behavior contradicts the current approved contract, implementation SHALL stop and return to OpenSpec/design review before changing parser/session authority.

Bar detailed journal usage statistics remain governed by the common call-log/statistics contract. Remediation must restore the shared normalized duration/statistics path rather than add Bar-specific percentage calculations in Qt presentation.

### 10.5 Box310 call-log remediation boundary

Box remains exact-model call-log-capable and LIVE-unsupported. Automatic preview after the whole-room terminal/current-expanded/usable boundary and explicit fresh `Развернуть` acquisition remain mandatory. Fixing the Box journal SHALL preserve exact Box identity, shared CloudLink handler/session boundaries, serialized lane ownership, fresh explicit acquisition, typed failure cleanup, and zero Box microphone-LIVE start/resume/request.

### 10.6 TE20 call-log remediation boundary

TE20 explicit journal must use the common normalized call-log contract. Accepted completed records with valid duration evidence must expose/render `Продолжительность`, and usage statistics must use the existing machine-readable duration/period rules. Remediation SHALL not parse formatted GUI duration text back into arithmetic and SHALL not manufacture duration or percentages when source evidence is unavailable. Existing explicit partial/incomplete warning semantics remain authoritative.

### 10.7 Final hardware revalidation scope

The current `6f90bf80...` run is discovery evidence, not final acceptance. After a reviewed remediation implementation creates a new production SHA, exact-SHA hardware validation must rerun:

1. every scenario that failed in this discovery round on the model that exposed it;
2. Huawei audio-scale scenarios affected by the corrected contract: TE40/TE50 configured MIC dB range and Huawei TE20/TE40/TE50 speaker `0..21` where the final diff touches the shared path; no TE50 configured-MIC percent presentation is expected;
3. any cross-model smoke necessary for a shared production path touched by remediation, including shared call-log or common codec Audio/lifecycle code;
4. bounded cleanup/UI-unlocked behavior for remediated mutations and auxiliary reads.

Unrelated deep hardware scenarios whose authoritative code/protocol path is untouched by the final remediation diff do not need a complete six-model rerun solely because the commit SHA changes. This does not permit carrying a failed scenario forward: every remediated/changed scenario must have evidence tied to the final published SHA. Independent validation must review the actual production diff to decide which shared-path smoke is required.

Deployment-local regeneration/inspection of ignored `equipment_inventory.local.json` is a deployment follow-up and not an archive gate for this source change. The importer implementation/tests and exact-model runtime contract remain required source acceptance evidence.

## Updated acceptance inventory for the hardware-remediation amendment

| Area | Required result |
| --- | --- |
| Huawei audio-scale separation | TE20/TE40/TE50 MIC and RCA `-12..+12 dB`, nominal `0 dB`; speaker `0..21`; domains remain distinct |
| TE40 configured MIC1 | accepted `0..24` -> `-12..+12 dB`; native step 1; mute independent |
| TE50 configured MIC1 | same dB contract as TE40; no percentage exception; accepted `0..24` -> `-12..+12 dB`; native step 1; mute independent |
| TE20 numeric MIC control | remains unsupported; confirmed input-gain scale does not create a new capability |
| Huawei speaker | TE20/TE40/TE50 speaker volume uses separate `0..21`, step 1 |
| RPG310 speaker adjust/mute | real device changes reconcile; every terminal path releases the UI/interaction lock |
| Bar310 microphone LIVE | supported meter receives/publishes accepted samples under the approved Bar contract, or contradictory real protocol evidence triggers a new architecture review before parser/session changes |
| Bar310 call-log statistics | common normalized detailed-journal usage statistics render when authoritative; degraded/partial states remain explicit |
| Box310 call log | one automatic preview at the approved boundary plus fresh explicit journal; zero Box LIVE lifecycle |
| TE20 call log | `Продолжительность` is present when authoritative duration exists; common usage statistics render under existing completeness rules |
| Unsupported/no-data states | TE20/RPG numeric mic gain unsupported; Bar/Box mic mutations unsupported; Box/RPG mic LIVE unsupported; missing status/uptime/camera may remain `Нет данных` when no current evidence exists |
| Hardware rerun | final-SHA rerun of all failed/changed scenarios plus shared-path smoke determined from the remediation diff |

The amendment is architecture-only. Production code remains frozen until strict OpenSpec validation, disposable archive-applicability, Git checks, and independent architecture review of the exact published amendment SHA permit implementation.