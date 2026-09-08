# Design: Codec interaction parity restoration

## Context and status

The change is back in the OpenSpec / Design phase. Published implementation `467f2cbb502f698476f047d277052bf5ccb55147` passed offline validation but real-device testing exposed architecture defects. Amendment `969e4a55e44a4f6879daa5c664de812141fa1704` then received independent architecture verdict `CHANGES REQUIRED` with four HIGH and one MEDIUM findings.

This remediation resolves the root-spec replacement and lifecycle ambiguity findings now, and turns the two still-unproven device-protocol facts into explicit pre-APPROVE gates. It does **not** authorize implementation yet.

Authority remains:

`RULES.md -> current root OpenSpec -> approved change -> source/tests -> Git diff -> runbooks -> agent reports`

The legacy `CodecScreen`/`c442152077dd8aa6251f1d8be9fc98b765406dbd` is behavioral evidence only. Current hardware evidence may invalidate a historical assumption. A state-changing capability is not approved until its target semantics and reconciliation boundary are explicit.

## Review findings and architectural resolution

### 1. TE40 microphone gain versus current root capability

Root OpenSpec currently declares `Huawei TE40 microphone_adjust = UNSUPPORTED`. The previous amendment incorrectly overlaid that with a second `ADDED` matrix saying `YES`.

This remediation uses archive-compatible `MODIFIED` replacements for the root capability requirements. Until protocol discovery is complete, the runtime/network mutation matrix remains:

| Exact model | speaker_adjust | speaker_mute | microphone_adjust | microphone_mute | reboot |
| --- | --- | --- | --- | --- | --- |
| Huawei TE20 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| Huawei TE40 | SUPPORTED | SUPPORTED | **UNSUPPORTED pending protocol proof** | SUPPORTED | UNSUPPORTED |
| CloudLink Bar 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| CloudLink Box 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| Polycom RPG 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |

This does **not** discard the hardware finding. TE40 has authoritative numeric microphone evidence distinct from mute:

```text
static configured microphone value -> micValue -> canonical microphone_volume
microphone mute state               -> MicSwitch / approved equivalent -> canonical microphone_muted
```

Read-only numeric presentation is therefore approved now. The mutation capability remains fail-closed until the exact setter contract is proven and this same change is amended again before architecture APPROVE.

TE20 and RPG310 remain true mute-only mutation models in the current scope. TE40 is no longer described as “mute-only”; it is described as “numeric read evidence exists, mutation contract not yet approved.”

### 2. TE40 gain protocol is a pre-APPROVE architecture gate

Before final architecture review, hardware/protocol discovery SHALL record:

```text
exact model / firmware context
state-changing method or ActionID
HTTP method / endpoint boundary
non-secret payload fields and target semantics
numeric allowed range
numeric step used by one +/- action
success/ack semantics
mandatory authoritative numeric readback method/field
```

The readback candidate already evidenced by source/device parsing is numeric `micValue`, but the final setter/range/step cannot be inferred from the visible legacy UI alone.

No implementation may:

- guess an ActionID;
- reinterpret `WEB_OpenMicAPI` / `WEB_CloseMicAPI` as gain control;
- treat numeric `0` as mute without independent mute evidence;
- select a range/step as an implementation decision.

After discovery, the OpenSpec matrix and mutation requirement must be amended to `SUPPORTED` with the exact contract, then revalidated/re-reviewed before implementation.

### 3. Audio-card presentation replaces the conflicting root contract

The previous root contract allowed one modern microphone meter, declared TE20/TE40 unsupported for it, and prohibited a second speaker-level indicator. Hardware shows TE20/TE40 have authoritative live microphone and speaker activity via `get_live_audio_status`.

The root visual requirements are therefore explicitly `MODIFIED` by this change. The fixed Audio-card order becomes:

```text
Микрофон (уровень)     <live horizontal meter or explicit unsupported/no-data state>
Динамик (уровень)      <live horizontal meter or explicit unsupported/no-data state>
Громкость микрофона    <numeric/static value or state> [model-appropriate controls]
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
Громкость микрофона = static configured numeric micValue
Микрофон (уровень)  = live MicValueIndex
```

These are different authorities. The dashboard must not show redundant textual `Live микрофон` / `Live динамик` rows when the two meter slots are present.

While TE40 `microphone_adjust` remains network-unsupported pending protocol proof, accepted numeric `micValue` may still be displayed. `-` / `+` gain affordances must not enter room interaction/device I/O until the capability becomes approved.

### 4. TE40 camera parsing

`WEB_GetLocalCameraList.itemList` is a zero-to-many collection. Parsing must not require `len(itemList) >= 2`.

For each present entry the handler/parser may process state independently and use the existing approved port/type lookup for active cameras. Exactly one valid camera record is sufficient to publish known camera state/model evidence when available.

### 5. Initial three-call preview lifecycle

The product requirement is not a background fetch for every collapsed codec. It is a mandatory preview for the **exact current expanded codec row**.

The lifecycle boundary is now explicit and compatible with current root room authority:

```text
entire automatic room cycle reaches terminal state
+ exact codec row is current / expanded / connected / usable / call-log-capable
+ no accepted initial-preview result exists for this exact row + room generation
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

### 7. Box 310 live parsing is not yet fully specified

Hardware has established that valid Box responses contain multiple records with:

```json
{"deviceId": <number>, "curVolume": <number>}
```

That evidence is sufficient to reject the old fixed-field parser contract, but not sufficient to prove that **every** such record is a microphone channel.

Therefore the previous amendment's normative `max(all curVolume)` rule is withdrawn.

Before architecture APPROVE, capture a redacted complete `WEB_GetCurrentAudioParam` response envelope and document one of:

1. the relevant collection is contractually/empirically microphone-only; then `max(valid microphone curVolume)` may use every record in that collection; or
2. the collection mixes roles; then define an authoritative microphone filter/device-role mapping before aggregation.

The eventual parser contract must also define the envelope/container path, numeric validity rules, empty/malformed behavior, exact Box identity, and normalization range. Until this discovery is complete, Box LIVE parser implementation must not be changed from one unproven assumption to another.

### 8. Existing room safety remains unchanged

All network work remains under one application-owned serialized room interaction lane. Exact current row/generation/model/IP/credential/currentness authority remains mandatory. State-changing operations still require live retirement, one send, authoritative reconciliation, and root blocked/unconfirmed behavior if final state cannot be confirmed. No blind replay is authorized.

Speaker zero/restore mute remains fail-closed: if current speaker volume is `0` and no proven exact-row/generation positive restore evidence exists, Unmute is local unavailable with zero mutation/session/device I/O.

Polycom speaker step remains `2`. CloudLink microphone gain and reboot for all five codecs remain unsupported.

## Acceptance inventory for the amended design

| Area | Required result |
| --- | --- |
| TE40 static mic | numeric `micValue` reaches canonical `microphone_volume`; mute remains independent |
| TE40 mic mutation | stays fail-closed until pre-APPROVE protocol discovery; after discovery exact range/step/set/readback must be normative |
| TE40 LIVE | `MicValueIndex` and `SpeakerValueIndex` feed two meter slots; no duplicate textual live rows |
| TE40 camera | exactly one valid camera entry is processed |
| Auto call preview | current expanded usable codec, after whole room cycle terminal, fresh once per row/generation, before first LIVE, up to 3 newest |
| Explicit journal | always fresh and separate from preview |
| Box LIVE | old fixed-field assumption rejected; final parser waits for full envelope + microphone-role evidence |
| Speaker controls | preserve exact ranges/steps/readback and no-restore safety |
| Bar/Box gain | unsupported, zero gain I/O |
| Reboot | unsupported, zero reboot I/O |
| Cleanup/currentness | no stale publication, no concurrent owner, no permanent UI/lane lock |

## Hardware and validation gates

All five models remain `AVAILABLE`: TE20, TE40, Bar 310, Box 310, RPG310.

Before **architecture APPROVE**:

1. TE40 gain protocol discovery complete and reflected in OpenSpec;
2. Box 310 full live-response envelope/device-role discovery complete and reflected in OpenSpec;
3. repository-local `.\openspec.cmd validate codec-interaction-parity-restoration --strict` passes;
4. repository-local `.\openspec.cmd validate --all --strict` passes;
5. disposable archive-applicability check passes for all MODIFIED requirements/scenarios;
6. independent architecture review returns a permitting verdict.

Only then may post-amendment production implementation start.

After implementation, all focused/full offline validation and exact-SHA hardware acceptance must be repeated. Evidence from `467f2cbb...` remains discovery evidence only.

## Rollback

Until the two discovery gates are closed, no production mutation capability is added. If protocol discovery disproves the intended TE40 gain or Box live behavior, update this architecture before implementation rather than forcing hardware to fit the assumption.
