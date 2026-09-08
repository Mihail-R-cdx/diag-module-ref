# Change: Restore codec interaction parity after room UI redesign

## Why

The room codec redesign preserved most protocol handlers but replaced the working codec-screen interaction composition with the modern room lifecycle/dashboard. The first implementation of this change reached published SHA `467f2cbb502f698476f047d277052bf5ccb55147` and passed independent offline validation, but real-device testing then proved several architecture assumptions incomplete or wrong.

A first hardware-discovered amendment was published as `969e4a55e44a4f6879daa5c664de812141fa1704`. Independent architecture review of that amendment returned `CHANGES REQUIRED`: it overlaid root capability/presentation contracts with `ADDED` requirements, declared TE40 microphone-gain mutation before the actual setter contract was known, left the initial three-call lifecycle ambiguous relative to the exact expanded row and full automatic-room-cycle boundary, and assumed every Box 310 `{deviceId, curVolume}` record was microphone evidence without proving the response envelope/device roles.

Remediation `918a046a4f525a3f2fede8dc142e6c1e8fbcf295` resolved the root replacement/lifecycle findings and converted TE40 gain plus Box LIVE parsing into explicit pre-APPROVE discovery gates. Authorized TE40 hardware work has now closed the TE40 gate. Box 310 remains unresolved because the complete Box response envelope/device-role semantics are not currently available.

The change therefore remains in the **OpenSpec / Design** phase. `467f2cbb...`, `969e4a55...` and `918a046a...` are not final implementation/acceptance candidates.

## Hardware-discovered product requirements

The target product behavior is now:

- Huawei TE40 static audio exposes independent numeric `micValue` and independent microphone mute evidence; the common room snapshot/presentation must preserve both rather than collapse numeric value into mute/unmute semantics.
- TE40 primary `MIC1` microphone gain is a supported state-changing capability. Native configured range is `-12..+9 dB`, step `1 dB`; device/wire `mic1Value` range is `0..21`, step `1`, with `gain_db = mic1Value - 12`.
- TE40 gain setter is `POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams`; the request preserves unrelated current audio-input fields and changes only target `mic1Value`. Successful ACK is not final authority; mandatory exact-row numeric reconciliation uses the existing TE40 `get_audio_status` / `WEB_InitAudioCtrlParamsAPI` `micValue` readback.
- TE40 microphone gain and microphone mute remain separate operations; numeric zero means `-12 dB`, not muted.
- TE20/TE40 live `MicValueIndex` and `SpeakerValueIndex` must be presented as `Микрофон (уровень)` and `Динамик (уровень)` meters; redundant textual `Live микрофон` / `Live динамик` rows are not the target presentation.
- TE40 camera parsing must accept zero, one or many returned `itemList` records; one valid camera must not become `Нет данных` merely because a second entry is absent.
- Every supported codec must show up to the three newest calls automatically for the **current expanded usable codec row after the entire automatic room cycle is terminal and before that row's first LIVE starts**. The operator must not need to press `Развернуть` to obtain those three rows.
- Explicit `Развернуть` remains a separate fresh detailed-journal acquisition and may retire/resume active LIVE through the existing bounded serialized lifecycle.
- The current fixed `mic1ValueIndex` / `micArray...` capture belongs to **CloudLink Bar 310**, not Box 310. Earlier Box 310 hardware evidence remains the `{deviceId, curVolume}` pair shape only. Box live parsing must wait for a complete Box envelope and authoritative microphone-device semantics before implementation.

## Remaining pre-APPROVE discovery gate

The TE40 protocol gate is closed and encoded normatively in this amendment.

One device-protocol fact remains missing and is an explicit **architecture gate**, not an implementation task:

1. **CloudLink Box 310 live response role contract.** Before final architecture `APPROVE`, capture a redacted complete Box response envelope/container and establish either that the relevant `{deviceId, curVolume}` collection is microphone-only or define the authoritative microphone filter/device-role rule. Until then, neither Bar's `mic*ValueIndex` schema nor a normative `max(all curVolume)` Box rule is approved.

The implementation phase SHALL NOT begin while this Box gate is open.

## What this amendment changes now

- Keep the archive-compatible `MODIFIED Requirements` for current root codec capability, but promote exact `Huawei TE40 microphone_adjust` from pending/unsupported to `SUPPORTED` under the proven MIC1 contract.
- Fix the TE40 target semantics before implementation: `-12..+9 dB`, step `1 dB`, wire `0..21`, `WEB_SaveAudioMicCtrlParams`, preserve unrelated payload state, ACK not authority, numeric `WEB_InitAudioCtrlParamsAPI.micValue` reconciliation mandatory.
- Keep microphone mute independent from numeric gain.
- Update the root-compatible Audio-card presentation so TE40 configured gain displays in dB and `-`/`+` requests exactly one dB through application-owned mutation authority.
- Preserve the two Huawei live-meter slots and removal of redundant textual live rows.
- Preserve the automatic three-call boundary: **entire automatic room cycle terminal + exact codec row current/expanded/usable -> mandatory fresh preview -> bounded cleanup -> first LIVE**.
- Keep automatic preview bound to the current expanded exact row; this change does not authorize background call-log I/O for collapsed/hidden codec rows.
- Preserve fresh explicit detail acquisition as a separate auxiliary intent.
- Preserve TE40 zero-to-many camera normalization.
- Explicitly classify the current `mic*ValueIndex` capture as Bar 310 evidence only; retain Box `{deviceId, curVolume}` observation without inventing envelope/roles/range.
- Keep CloudLink microphone gain and codec reboot fail-closed as before.
- Preserve Polycom speaker step `2`, speaker restore-authority safety, exact-row/currentness rules, one serialized network owner, typed failures, bounded cleanup, no blind mutation replay, and no Qt-thread network I/O.

## Scope

Affected exact models remain Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310. TE30/TE50/TE60 expansion is a later change and SHALL NOT be inferred from this TE40 remediation.

## Hardware gate

Hardware observations from `467f2cbb...` and subsequent authorized TE40 protocol captures are architecture-discovery evidence only. Final hardware acceptance must be repeated on the exact post-amendment implementation SHA after a new architecture `APPROVE`, implementation, and independent offline validation.

Box 310 is not currently available for the remaining parser-discovery gate. The change SHALL remain pre-implementation until that gate is either closed with hardware evidence or explicitly removed/deferred by a separately approved scope decision.

## Behavioral oracle

Pre-redesign behavioral reference:

`c442152077dd8aa6251f1d8be9fc98b765406dbd`

Change-creation baseline:

`754099722ec14d4b9aa0516e0e085387fd0e727b`

Hardware-discovery implementation baseline:

`467f2cbb502f698476f047d277052bf5ccb55147`

Historical behavior is evidence, not authority over current root OpenSpec or contradictory real-device evidence. Newly discovered state-changing protocol details must be proven before they are promoted to capability; TE40 now meets that bar, Box LIVE does not yet.

## Affected Specs

- `device-diagnostics-and-control`
- `diagnostic-ui-presentation`
- `room-device-interaction-lifecycle`
- `codec-call-log-usage-statistics`
