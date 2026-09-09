# Design: Codec interaction parity restoration

## Context and status

The change is back in the OpenSpec / Design phase. Published implementation `467f2cbb502f698476f047d277052bf5ccb55147` passed offline validation but real-device testing exposed architecture defects. Amendment `969e4a55e44a4f6879daa5c664de812141fa1704` received independent `CHANGES REQUIRED`; remediation `918a046a4f525a3f2fede8dc142e6c1e8fbcf295` resolved root-spec replacement and lifecycle ambiguity; `df5447abe556d53ce3d7fd2a2a56e1c042918272` then closed the TE40 setter/range/step gap.

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
| Huawei TE40 | SUPPORTED from `WEB_GetCurrentAudioParam`: `max(valid MicValueIndex + valid mic<N>ValueIndex + valid micArray<N>_<NN>ValIdx)`, normalized `0..220 -> 0..100%` |
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

## 2. TE40/TE50 static microphone authorities

TE40, and exact-model TE50 by the declared reuse contract, keep two independent authorities:

```text
static configured microphone gain -> mic1Value -> canonical microphone_volume
microphone mute state              -> MicSwitch / approved equivalent -> canonical microphone_muted
```

Configured numeric zero means `-12 dB`, not mute.

The display/wire mapping is:

```text
native configured gain: -12 dB .. +9 dB
native adjustment step: 1 dB
wire mic1Value range:   0 .. 21
wire step:              1
gain_db = mic1Value - 12
mic1Value = gain_db + 12
```

Observed device points include `21 -> +9 dB` and `18 -> +6 dB`.

## 3. TE40 MIC1 mutation uses fresh full-state compare-and-preserve

The approved setter boundary is:

```text
POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams
```

The native save payload is full-state: it carries `micall`, microphone enable fields `mic1..mic18`, microphone value fields `mic1Value..mic18Value`, and required session/CSRF material. Therefore a previously accepted room snapshot is **not** safe payload authority.

The exact lifecycle is:

```text
operator confirms TE40 MIC1 +/-
-> exact MUTATION owns the serialized room lane
-> retire prior LIVE and finish bounded cleanup
-> fresh TE40 full audio-control read
-> validate complete required non-secret save-state fields
-> construct payload only from that fresh pre-write state
-> change only target mic1Value by exactly +/-1 wire unit (= 1 dB)
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
Громкость динамиков    [−] <accepted value/percentage or Нет данных> [+] [mute]
```

Huawei TE20 uses raw `MicValueIndex` for its normalized microphone LIVE meter from `get_live_audio_status`. TE40, and exact-model TE50 by the declared reuse contract, use one shared `WEB_GetCurrentAudioParam` extractor for initial seed and true LIVE: decode the JSON-string envelope, then take `max(valid MicValueIndex + valid mic<N>ValueIndex + valid micArray<N>_<NN>ValIdx)`, followed by the existing `0..220 -> 0..100%` normalization. Configured `mic1Value` is rendered in dB separately from live microphone evidence and mute.

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
| TE40/TE50 static mic | numeric `mic1Value` -> canonical `microphone_volume` -> `-12..+9 dB`; mute independent |
| TE40/TE50 mic mutation | fresh full pre-read after lane ownership; change only `mic1Value`; one save; full target + collateral post-read reconciliation |
| TE40 pre-read failure | no POST; no command-ambiguity block solely from pre-submit failure |
| TE40 collateral mismatch | mutation unconfirmed/blocked; no silent success/replay |
| TE40 LIVE | `WEB_GetCurrentAudioParam` microphone meter from normalized `max(valid MicValueIndex + valid mic<N>ValueIndex + valid micArray<N>_<NN>ValIdx)`; no speaker LIVE meter or duplicate textual live rows |
| TE40 camera | one valid camera entry is sufficient |
| TE50 inventory | `te` + `50` component evidence -> exact canonical `Huawei TE50`; expected kind `video_codec` is non-authoritative consistency evidence |
| Bar LIVE | supported under Bar-specific approved parser |
| Box LIVE | microphone LIVE explicitly unsupported/deferred; no live binding/I/O; room presentation has no speaker LIVE capability |
| Box non-LIVE | diagnostics, speaker, preview/journal, Local Refresh remain in scope |
| Auto call preview | session-bound current expanded usable row accepted without bind/render I/O; whole-cycle terminal, once per row/generation, before first eligible LIVE |
| Explicit journal | always fresh and separate |
| Speaker controls | preserve ranges/steps/readback and no-restore safety |
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
