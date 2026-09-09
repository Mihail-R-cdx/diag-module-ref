# Change: Restore codec interaction parity after room UI redesign

## Why

The room codec redesign preserved most protocol handlers but replaced the working codec-screen interaction composition with the modern room lifecycle/dashboard. The first implementation of this change reached published SHA `467f2cbb502f698476f047d277052bf5ccb55147` and passed independent offline validation, but real-device testing then proved several architecture assumptions incomplete or wrong.

A first hardware-discovered amendment was published as `969e4a55e44a4f6879daa5c664de812141fa1704`. Independent architecture review returned `CHANGES REQUIRED`. Remediation `918a046a4f525a3f2fede8dc142e6c1e8fbcf295` resolved the root replacement/lifecycle findings, and `df5447abe556d53ce3d7fd2a2a56e1c042918272` closed the TE40 protocol-discovery gap with an explicit MIC1 gain contract.

Independent review of `df5447...` found two HIGH issues: Box 310 LIVE was still architecturally incomplete, and the TE40 full-state save contract could build a POST from stale non-target microphone state. Amendment `01faf3cc522f89f936cb4daefa70161279093f40` resolved those by deferring Box LIVE and requiring fresh full-state TE40 pre/post reads.

Validation of `01faf3...` then produced:

```text
OpenSpec change strict: PASS
OpenSpec all strict: PASS
Archive applicability: FAIL
git diff --check: PASS
git diff --cached --check: PASS
```

The archive failure exposed one remaining root conflict: `cloudlink-live-microphone-metering` still declared Box LIVE and `WEB_GetCurrentAudioParam` polling as supported. The same review also found a Box call-log regression that still referenced a nonexistent first Box LIVE. This amendment resolves both without changing production code.

Hardware acceptance of implementation `01226c6620932db01424a06211ba7292c6efc164` then found that TE40 dynamic microphone audio is acquired by browser request `WEB_GetCurrentAudioParam`, while the implementation's seed and LIVE paths use `WEB_GetMonitorAudioParam`. The decoded current-audio payload contains individual `mic<N>ValueIndex` and `micArray<N>_<NN>ValIdx` microphone evidence. This OpenSpec-only amendment corrects that approved source/evidence contract before further production implementation. The corrected TE40 implementation was subsequently hardware-accepted for current-audio LIVE at exact SHA `43fa6ca247898ff661e6e2fbcc4850c561512a2f`; that is historical TE40 evidence, not a whole-change hardware completion.

The explicit TE50 runtime contract cannot be reached from organization workbook evidence while the offline importer's closed diagnostic-model registry omits `Huawei TE50`. This amendment therefore adds only the reviewed inventory-recognition and importer-side expected-kind contract required to produce the same canonical exact model, without making free-form source text runtime authority or expanding Huawei protocol semantics.

## Hardware-discovered product requirements

The target product behavior is now:

- Huawei TE40 static audio exposes independent primary `mic1Value` gain and independent microphone mute evidence. Exact-model Huawei TE50 reuses that approved contract by declared product protocol equivalence.
- TE40 primary `MIC1` microphone gain is supported. Native configured range is `-12..+9 dB`, step `1 dB`; wire `mic1Value` range is `0..21`, step `1`, with `gain_db = mic1Value - 12`. Exact-model TE50 reuses this contract pending its own hardware acceptance.
- TE40 gain setter is `POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams`; its full-state payload MUST be constructed only from a fresh serialized pre-write audio-control read after mutation ownership is acquired and prior LIVE is retired.
- The fresh pre-write state must contain every non-secret `micall`, `mic1..mic18`, and `mic1Value..mic18Value` field required by the save contract. The mutation changes only target `mic1Value`. If fresh full state is incomplete, no POST is sent.
- Successful save ACK is not final authority. Post-write reconciliation re-reads full audio-control state, confirms target MIC1, and confirms preserved non-target fields against the fresh pre-write baseline.
- TE40 microphone gain and microphone mute remain separate operations; numeric zero means `-12 dB`, not muted.
- TE20 live raw `MicValueIndex` is unchanged and normalized from `0..220` to the `Микрофон (уровень)` meter. TE40 and exact-model TE50 use `WEB_GetCurrentAudioParam` for both initial seed and true LIVE, take the maximum valid numeric evidence from compatibility `MicValueIndex`, hardware-observed `mic<N>ValueIndex`, and `micArray<N>_<NN>ValIdx`, then use the same scale; no user-visible speaker LIVE meter is advertised.
- TE40 camera parsing accepts zero, one or many returned `itemList` records.
- Every call-log-capable codec, including Box 310, shows up to the three newest calls automatically for the exact current expanded usable codec row after the entire automatic room cycle is terminal.
- For a model that advertises LIVE, that LIVE waits for preview terminal cleanup. For a model that advertises no LIVE, preview cleanup releases the lane without creating or implying LIVE.
- Explicit `Развернуть` remains a separate fresh detailed-journal acquisition.
- CloudLink Bar 310 microphone LIVE remains supported under its approved Bar-specific contract.
- **CloudLink Box 310 microphone LIVE is explicitly deferred from this change and from the archived root contract.** Exact Box registration advertises no LIVE binding, no Box meter polling context exists, no LIVE `WEB_GetCurrentAudioParam` request is sent, and current Box live-level presentation is unsupported.

## Scope decision for Box 310 LIVE

Box 310 hardware is not currently available and existing evidence does not establish a complete response envelope, microphone record selection, aggregation, or normalization. Keeping Box LIVE marked supported would force implementation to make an architectural decision.

This change therefore chooses a fail-closed scope reduction:

```text
CloudLink Box 310 diagnostics / speaker controls / call log / automatic preview / explicit journal / Local Refresh
    -> remain in scope

CloudLink Box 310 microphone LIVE
    -> UNSUPPORTED / DEFERRED
    -> no unified-registration live binding
    -> no polling context
    -> no LIVE request to WEB_GetCurrentAudioParam
    -> legacy codec-page meter row hidden
    -> modern room Audio slot shows Не поддерживается
    -> restoration deferred to a separate reviewed change with fresh hardware evidence
```

The historical `WEB_GetCurrentAudioParam` legacy compatibility classification may remain as dormant protocol knowledge but SHALL NOT advertise Box LIVE or authorize polling.

The current Bar 310 capture SHALL NOT be used as Box evidence. Earlier Box `{deviceId, curVolume}` observations SHALL NOT be turned into `max(all)` or any other parser rule in this change.

## What this amendment changes now

- Add archive-compatible `MODIFIED Requirements` for root `cloudlink-live-microphone-metering`, making Bar 310 the only supported CloudLink live microphone model in this change.
- Remove archived-root Box LIVE polling authority while preserving Bar endpoint/session/parser/polling behavior.
- Preserve the root Box scenario names for archive compatibility but redefine them as explicit no-capability/no-polling/deferred behavior.
- Keep root-compatible codec capability and Audio-card contracts aligned with Box LIVE deferred semantics.
- Correct Box call-log regression so automatic preview is followed by lane release, not by a fabricated first Box LIVE.
- Keep exact `Huawei TE40 microphone_adjust = SUPPORTED` under the proven MIC1 contract and fresh full-state mutation safety.
- Preserve Huawei microphone LIVE presentation, TE40 dB configured gain, zero-to-many TE40 camera parsing, automatic three-call lifecycle, explicit fresh journal, Polycom speaker step `2`, speaker restore-authority safety, exact-row/currentness rules, one serialized network owner, typed failures, bounded cleanup, no blind mutation replay, and no Qt-thread network I/O.
- Preserve a generation-current session `expanded_record_id` at coordinator binding without render-triggered I/O so the mandatory terminal-cycle preview does not depend on a synthetic Qt expansion event.
- Use one TE40 current-audio extractor for initial seed and true LIVE: `WEB_GetCurrentAudioParam`, JSON-string envelope decoding, maximum valid `MicValueIndex`/`mic<N>ValueIndex`/`micArray<N>_<NN>ValIdx` evidence, and the existing Huawei `0..220 -> 0..100%` normalization.
- Add `Huawei TE50 | te + 50` to the closed offline diagnostic-model registry, retain existing component extraction and cardinality rules, and add importer-only `Huawei TE50 -> video_codec` expected-kind consistency evidence without overriding source `Тип модели` authority.
- Require deployment-local regeneration of `equipment_inventory.local.json` from the configured organization workbook after the reviewed registry change; workbooks and generated inventory remain outside Git and runtime remains JSON-only.

## Scope

Affected exact models are Huawei TE20, Huawei TE40, Huawei TE50, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310. TE50 is an explicit exact-model registration that reuses the approved TE40 contract for all functions covered by this change: connection/session/authentication, static diagnostics, microphone/camera/status/uptime, `WEB_GetCurrentAudioParam` microphone LIVE decoding and normalization, MIC1 gain/mutation/mute, speaker, presentation, call-log/journal, Local Refresh, and preview/currentness/cleanup lifecycle. It does not authorize loose `TE*` or Huawei-family inference. The linked offline importer may recognize only the canonical TE50 component rule so runtime receives `diagnostic_model = Huawei TE50`; it does not use `source_model` for dispatch or add a protocol contract.

Box 310 remains in scope for all approved non-LIVE behavior listed above. Only Box 310 microphone LIVE restoration is deferred.

TE30 and TE60 expansion remain later changes and SHALL NOT be inferred from this remediation. TE50 is admitted only through its named exact model registration.

## Architecture gates

Hardware-backed TE40 endpoint evidence changes the approved LIVE source contract: it records `WEB_GetCurrentAudioParam`, its JSON-string envelope, and the observed TE40 microphone field families as an application aggregation contract. A new independent architecture review is required before implementation may begin. The remaining gates are:

1. `.\openspec.cmd validate codec-interaction-parity-restoration --strict`;
2. `.\openspec.cmd validate --all --strict`;
3. disposable archive-applicability check for all `MODIFIED Requirements`;
4. Git hygiene checks;
5. independent architecture review of the exact published amendment SHA with a permitting verdict.

The PASS/FAIL evidence from `01faf3...` is historical validation evidence only; all required checks must be rerun against the new exact amendment SHA.

## Hardware gate

Hardware observations from `467f2cbb...` and subsequent TE40 captures are architecture-discovery evidence only, except that TE40 current-audio LIVE has a recorded PASS at exact SHA `43fa6ca247898ff661e6e2fbcc4850c561512a2f`. TE50 is admitted by declared protocol equivalence and remains pending exact-SHA TE50 hardware acceptance. Any later production implementation, including TE50 registration, requires a new exact-SHA TE40 quick rerun as well as applicable TE50 testing before whole-change hardware completion.

For Box 310 in this change, hardware acceptance does **not** require working microphone LIVE. It requires the deferred contract: no Box live binding/request/polling context, legacy meter row hidden where applicable, modern `Микрофон (уровень) = Не поддерживается`, while all other applicable Box behaviors remain testable. A future dedicated Box LIVE change must carry its own hardware evidence and acceptance.

## Behavioral oracle

Pre-redesign behavioral reference:

`c442152077dd8aa6251f1d8be9fc98b765406dbd`

Change-creation baseline:

`754099722ec14d4b9aa0516e0e085387fd0e727b`

Hardware-discovery implementation baseline:

`467f2cbb502f698476f047d277052bf5ccb55147`

Historical behavior is evidence, not authority over current root OpenSpec or contradictory real-device evidence.

## Affected Specs

- `device-diagnostics-and-control`
- `diagnostic-ui-presentation`
- `room-device-interaction-lifecycle`
- `codec-call-log-usage-statistics`
- `cloudlink-live-microphone-metering`
- `equipment-inventory-snapshot`
