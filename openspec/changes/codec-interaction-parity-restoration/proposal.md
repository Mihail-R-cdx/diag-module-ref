# Change: Restore codec interaction parity after room UI redesign

## Why

The room codec redesign preserved most protocol handlers but replaced the working codec-screen interaction composition with the modern room lifecycle/dashboard. The first implementation of this change reached published SHA `467f2cbb502f698476f047d277052bf5ccb55147` and passed independent offline validation, but real-device testing then proved several architecture assumptions incomplete or wrong.

A first hardware-discovered amendment was published as `969e4a55e44a4f6879daa5c664de812141fa1704`. Independent architecture review of that amendment returned `CHANGES REQUIRED`: it overlaid root capability/presentation contracts with `ADDED` requirements, declared TE40 microphone-gain mutation before the actual setter contract was known, left the initial three-call lifecycle ambiguous relative to the exact expanded row and full automatic-room-cycle boundary, and assumed every Box 310 `{deviceId, curVolume}` record was microphone evidence without proving the response envelope/device roles.

This remediation keeps the change in the **OpenSpec / Design** phase. Neither `467f2cbb...` nor `969e4a55...` is a final architecture or acceptance candidate.

## Hardware-discovered product requirements

The target product behavior remains:

- Huawei TE40 static audio exposes independent numeric `micValue` and independent microphone mute evidence; the common room snapshot/presentation must preserve both rather than collapse numeric value into mute/unmute semantics.
- TE40 microphone gain is intended to be a real numeric control, but state-changing support SHALL NOT be promoted until the real setter contract is proven and written into OpenSpec.
- TE20/TE40 live `MicValueIndex` and `SpeakerValueIndex` must be presented as `Микрофон (уровень)` and `Динамик (уровень)` meters; redundant textual `Live микрофон` / `Live динамик` rows are not the target presentation.
- TE40 camera parsing must accept zero, one or many returned `itemList` records; one valid camera must not become `Нет данных` merely because a second entry is absent.
- Every supported codec must show up to the three newest calls automatically for the **current expanded usable codec row after the entire automatic room cycle is terminal and before that row's first LIVE starts**. The operator must not need to press `Развернуть` to obtain those three rows.
- Explicit `Развернуть` remains a separate fresh detailed-journal acquisition and may retire/resume active LIVE through the existing bounded serialized lifecycle.
- CloudLink Box 310 hardware disproves the old fixed `mic1ValueIndex` / `micArray...` response assumption. Box live parsing must be based on the actual `{deviceId, curVolume}` response envelope and authoritative microphone-device semantics once those semantics are captured.

## Pre-APPROVE discovery gates

Two protocol facts are still missing and are now explicit **architecture gates**, not implementation tasks:

1. **Huawei TE40 microphone-gain mutation contract.** Before final architecture `APPROVE`, record and review the exact non-secret state-changing method/ActionID, payload semantics, numeric range, step, and authoritative numeric post-write readback. Until that amendment is approved, the root/runtime `microphone_adjust` capability for TE40 remains `UNSUPPORTED`; accepted numeric `micValue` remains valid read-only presentation evidence.
2. **CloudLink Box 310 live response role contract.** Before final architecture `APPROVE`, capture a redacted complete `WEB_GetCurrentAudioParam` response envelope and establish either that the relevant `{deviceId, curVolume}` collection is microphone-only or define the authoritative microphone filter/device-role rule. Until then, no normative `max(all curVolume)` rule is approved.

The implementation phase SHALL NOT begin while either gate is open.

## What this remediation changes now

- Replace the conflicting root codec capability requirements with archive-compatible `MODIFIED Requirements`; TE40 numeric read evidence is separated from mutation capability, and TE40 mutation remains fail-closed pending protocol proof.
- Replace the conflicting root codec Audio-card visual requirements with archive-compatible `MODIFIED Requirements`, preserving existing scenario names while establishing two live-meter slots and the exact new Audio-card order.
- Make the automatic three-call boundary unambiguous and compatible with current root authority: **entire automatic room cycle terminal + exact codec row current/expanded/usable -> mandatory fresh preview -> bounded cleanup -> first LIVE**.
- Keep automatic preview bound to the current expanded exact row; this change does not authorize background call-log I/O for collapsed/hidden codec rows.
- Preserve fresh explicit detail acquisition as a separate auxiliary intent.
- Preserve TE40 one-or-more camera normalization and TE40 static numeric `micValue` presentation.
- Remove the unproven Box `max(all curVolume)` assertion and make response-envelope/device-role discovery a pre-APPROVE gate.
- Keep CloudLink microphone gain and codec reboot fail-closed as before.
- Preserve Polycom speaker step `2`, speaker restore-authority safety, exact-row/currentness rules, one serialized network owner, typed failures, bounded cleanup, no blind mutation replay, and no Qt-thread network I/O.

## Scope

Affected exact models remain Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310. TE30/TE50/TE60 expansion is a later change and SHALL NOT be inferred from this TE40 remediation.

## Hardware gate

All five current models remain `AVAILABLE`. Hardware observations from `467f2cbb...` are architecture-discovery evidence only. Final hardware acceptance must be repeated on the exact post-amendment implementation SHA after a new architecture `APPROVE`, implementation, and independent offline validation.

## Behavioral oracle

Pre-redesign behavioral reference:

`c442152077dd8aa6251f1d8be9fc98b765406dbd`

Change-creation baseline:

`754099722ec14d4b9aa0516e0e085387fd0e727b`

Hardware-discovery implementation baseline:

`467f2cbb502f698476f047d277052bf5ccb55147`

Historical behavior is evidence, not authority over current root OpenSpec or contradictory real-device evidence. Newly discovered state-changing protocol details must be proven before they are promoted to capability.

## Affected Specs

- `device-diagnostics-and-control`
- `diagnostic-ui-presentation`
- `room-device-interaction-lifecycle`
- `codec-call-log-usage-statistics`
