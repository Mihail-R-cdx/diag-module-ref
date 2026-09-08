# Change: Restore codec interaction parity after room UI redesign

## Why

The room codec redesign preserved most protocol handlers but replaced the working codec-screen interaction composition with the modern room lifecycle/dashboard. The first implementation of this change reached published SHA `467f2cbb502f698476f047d277052bf5ccb55147` and passed independent offline validation, but real-device testing then proved several architecture assumptions incomplete or wrong.

A first hardware-discovered amendment was published as `969e4a55e44a4f6879daa5c664de812141fa1704`. Independent architecture review returned `CHANGES REQUIRED`. Remediation `918a046a4f525a3f2fede8dc142e6c1e8fbcf295` resolved the root replacement/lifecycle findings, and `df5447abe556d53ce3d7fd2a2a56e1c042918272` closed the TE40 protocol-discovery gap with an explicit MIC1 gain contract.

Independent review of `df5447...` found two remaining HIGH issues: Box 310 LIVE was still architecturally incomplete, and the TE40 full-state save contract could build a POST from stale non-target microphone state. This amendment resolves both without changing production code.

## Hardware-discovered product requirements

The target product behavior is now:

- Huawei TE40 static audio exposes independent numeric `micValue` and independent microphone mute evidence; the common room snapshot/presentation must preserve both rather than collapse numeric value into mute/unmute semantics.
- TE40 primary `MIC1` microphone gain is supported. Native configured range is `-12..+9 dB`, step `1 dB`; wire `mic1Value` range is `0..21`, step `1`, with `gain_db = mic1Value - 12`.
- TE40 gain setter is `POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams`; its full-state payload MUST be constructed only from a fresh serialized pre-write audio-control read taken after mutation ownership is acquired and prior LIVE is retired. Previously accepted room cache is insufficient payload authority.
- The fresh pre-write state must contain every non-secret `micall`, `mic1..mic18`, and `mic1Value..mic18Value` field required by the save contract. The mutation changes only target `mic1Value`. If the fresh full state is incomplete, no POST is sent.
- Successful save ACK is not final authority. Post-write reconciliation re-reads the same authoritative full audio-control state, confirms target MIC1, and confirms all preserved non-target fields against the fresh pre-write baseline. Missing/malformed/mismatched target or collateral state enters the root blocked/unconfirmed mutation contract; no blind replay is allowed.
- TE40 microphone gain and microphone mute remain separate operations; numeric zero means `-12 dB`, not muted.
- TE20/TE40 live `MicValueIndex` and `SpeakerValueIndex` are presented as `Микрофон (уровень)` and `Динамик (уровень)` meters; redundant textual `Live микрофон` / `Live динамик` rows are removed.
- TE40 camera parsing accepts zero, one or many returned `itemList` records.
- Every call-log-capable codec, including Box 310, shows up to the three newest calls automatically for the exact current expanded usable codec row after the entire automatic room cycle is terminal and before that row's first eligible LIVE starts.
- Explicit `Развернуть` remains a separate fresh detailed-journal acquisition.
- CloudLink Bar 310 microphone LIVE remains supported under its approved Bar-specific contract.
- **CloudLink Box 310 microphone LIVE is explicitly deferred from this change.** The exact Box registration SHALL advertise no post-cycle LIVE binding, the microphone LIVE slot SHALL render `Не поддерживается`, and current implementation work SHALL perform zero Box LIVE polling. Earlier `{deviceId, curVolume}` observations are retained only as evidence for a future dedicated Box LIVE restoration change.

## Scope decision for Box 310 LIVE

Box 310 hardware is not currently available and the existing evidence does not establish a complete response envelope, microphone record selection, aggregation, or normalization. Keeping Box LIVE marked supported would force the implementation agent to make an architectural decision.

This change therefore chooses a fail-closed scope reduction:

```text
CloudLink Box 310 diagnostics / speaker controls / call log / automatic preview / explicit journal / Local Refresh
    -> remain in scope

CloudLink Box 310 post-cycle microphone LIVE
    -> UNSUPPORTED in this change
    -> no unified-registration live binding
    -> no room LIVE request to WEB_GetCurrentAudioParam
    -> Audio meter shows Не поддерживается
    -> restoration deferred to a separate reviewed change with fresh hardware evidence
```

The current Bar 310 `mic1ValueIndex` / `micArray...` capture SHALL NOT be used as Box evidence. Earlier Box `{deviceId, curVolume}` observations SHALL NOT be turned into `max(all)` or any other parser rule in this change.

## What this amendment changes now

- Keep archive-compatible `MODIFIED Requirements` for the current codec capability and Audio-card contracts.
- Keep exact `Huawei TE40 microphone_adjust = SUPPORTED` under the proven MIC1 range/step/setter contract.
- Strengthen TE40 mutation safety with a mandatory fresh full-state pre-read after lane ownership/LIVE retirement, payload construction exclusively from that fresh state, and full post-write collateral reconciliation.
- Make pre-read failure before POST a definite no-send outcome: no command ambiguity is created solely by inability to obtain fresh full state.
- Replace root-compatible CloudLink interactive-session semantics so Box LIVE is dormant/deferred rather than an advertised capability; its legacy transport classification is retained only for a future approved restoration.
- Change the root-compatible Audio-card support matrix so Box microphone LIVE is `UNSUPPORTED` for this change.
- Preserve Huawei two-meter presentation, TE40 dB configured gain, zero-to-many TE40 camera parsing, automatic three-call lifecycle, explicit fresh journal, Polycom speaker step `2`, speaker restore-authority safety, exact-row/currentness rules, one serialized network owner, typed failures, bounded cleanup, no blind mutation replay, and no Qt-thread network I/O.

## Scope

Affected exact models remain Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310.

Box 310 remains in scope for all approved non-LIVE behavior listed above. Only Box 310 **post-cycle microphone LIVE restoration** is deferred.

TE30/TE50/TE60 expansion is a later change and SHALL NOT be inferred from this TE40 remediation.

## Architecture gates

There is no longer an unresolved device-protocol discovery gate inside this change. Before implementation may begin, the remaining gates are repository/process gates:

1. `.\openspec.cmd validate codec-interaction-parity-restoration --strict`;
2. `.\openspec.cmd validate --all --strict`;
3. disposable archive-applicability check for all `MODIFIED Requirements`;
4. Git hygiene checks;
5. independent architecture review of the exact published amendment SHA with a permitting verdict.

## Hardware gate

Hardware observations from `467f2cbb...` and subsequent TE40 captures are architecture-discovery evidence only. Final hardware acceptance must be repeated on the exact post-amendment implementation SHA after new architecture `APPROVE`, implementation, and independent offline validation.

For Box 310 in this change, hardware acceptance does **not** require working microphone LIVE. It requires the deferred contract: no Box live binding/request, `Микрофон (уровень) = Не поддерживается`, while all other applicable Box behaviors remain testable. A future dedicated Box LIVE change must carry its own hardware evidence and acceptance.

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
