# Tasks: codec-interaction-parity-restoration

## 1. Historical baseline and first implementation cycle

- [x] 1.1 Compare current `master` with pre-codec-redesign `c442152077dd8aa6251f1d8be9fc98b765406dbd` and treat legacy `CodecScreen` as behavioral evidence, not room authority.
- [x] 1.2 Establish the original exact-model matrix, parser normalization, LIVE/call-log lifecycle and hardware gate.
- [x] 1.3 Obtain the original architecture `APPROVE` and implement through published SHA `467f2cbb502f698476f047d277052bf5ccb55147`.
- [x] 1.4 Independently validate `467f2cbb...` offline; result was `PASS FOR HARDWARE ACCEPTANCE`.
- [x] 1.5 Begin hardware acceptance and record that real-device findings invalidate parts of the original architecture; `467f2cbb...` is discovery baseline only.

## 2. Hardware-discovered architecture amendment

- [x] 2.1 Publish first amendment `969e4a55e44a4f6879daa5c664de812141fa1704` covering TE40 numeric microphone evidence, live presentation, camera, initial three-call product requirement and Box live response shape.
- [x] 2.2 Independently review `969e4a55...`; verdict `CHANGES REQUIRED` with 4 HIGH and 1 MEDIUM findings.
- [x] 2.3 Resolve HIGH root capability conflict by replacing `Current codec room-control support matrix is a fixed acceptance oracle` through archive-compatible `MODIFIED Requirements` rather than a competing ADDED matrix.
- [x] 2.4 Resolve HIGH adapter conflict by replacing `Codec room-control adapters reuse approved typed operations and explicitly reject unsupported operations`; TE20/RPG remain mute-only and TE40 numeric gain/mute semantics are independent.
- [x] 2.5 Resolve HIGH root presentation conflict by replacing `Codec audio card distinguishes supported live-meter evidence from unsupported capability` with the two-live-meter Audio-card contract and preserved root requirement identity.
- [x] 2.6 Resolve HIGH visual-checkpoint conflict by replacing `Codec visual acceptance is measurable from repository-local checkpoints` and defining the exact new Audio-card order.
- [x] 2.7 Resolve HIGH initial-preview lifecycle ambiguity: whole automatic room cycle terminal + exact codec current/expanded/usable -> one fresh automatic preview -> bounded cleanup -> first LIVE.
- [x] 2.8 Keep collapsed/non-current codec rows free of automatic call-log network I/O; this amendment does not create background preview for every room codec.
- [x] 2.9 Remove the unproven Box `max(all curVolume)` contract and make response-envelope/device-role semantics a pre-APPROVE discovery gate.
- [x] 2.10 Publish remediation `918a046a4f525a3f2fede8dc142e6c1e8fbcf295` with root-compatible capability/presentation/lifecycle corrections and fail-closed TE40/Box discovery gates.

## 3. Mandatory protocol discovery before architecture APPROVE

These tasks belong to the **OpenSpec / Design phase**. Production implementation SHALL NOT begin while the remaining Box gate is open.

- [x] 3.1 TE40 gain: on authorized hardware, identify the exact state-changing boundary `POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams` used by the native web UI for primary `MIC1` configured gain.
- [x] 3.2 TE40 gain: record payload/target semantics and scale: preserve current `micall`, `mic1..mic18`, `mic1Value..mic18Value` state; change target `mic1Value`; native range `-12..+9 dB`, step `1 dB`; wire range `0..21`, step `1`; `gain_db = mic1Value - 12`.
- [x] 3.3 TE40 gain: record ACK/reconciliation semantics: `{"success":1,"data":""}` is acknowledgement only; authoritative numeric readback uses existing TE40 `get_audio_status` / `WEB_InitAudioCtrlParamsAPI` field `micValue`; mute remains independent and numeric zero is not mute authority.
- [x] 3.4 Amend `design.md`, `device-diagnostics-and-control/spec.md`, `diagnostic-ui-presentation/spec.md`, `proposal.md` and tasks with the proven TE40 contract; change exact `Huawei TE40 microphone_adjust` to `SUPPORTED` only through that contract.
- [ ] 3.5 Box 310 LIVE: capture a redacted complete Box response envelope/container from authorized hardware. Do not substitute current Bar 310 `mic*ValueIndex` evidence.
- [ ] 3.6 Box 310 LIVE: establish whether the relevant earlier `{deviceId, curVolume}` collection is microphone-only; otherwise document authoritative device-role/filter semantics.
- [ ] 3.7 Amend Box parser contract with exact envelope path, microphone record selection, numeric validity, aggregation rule, unavailable behavior and normalization. Do not assume Bar schema or `max(all)` without proof.

## 4. Architecture validation and approval after discovery

- [ ] 4.1 Re-read all four current root specs affected by this change and confirm no competing capability/presentation/lifecycle contract remains after the final Box discovery amendment.
- [ ] 4.2 Run `.\openspec.cmd validate codec-interaction-parity-restoration --strict` through the tracked repository-local wrapper.
- [ ] 4.3 Run `.\openspec.cmd validate --all --strict`.
- [ ] 4.4 Run disposable archive-applicability check for all `MODIFIED Requirements`; verify every replaced root requirement/scenario remains archive-compatible.
- [ ] 4.5 Run Git hygiene checks applicable to architecture artifacts (`git diff --check`, `git diff --cached --check`).
- [ ] 4.6 Perform independent architecture review against the exact published amendment SHA after tasks 3.5-3.7 are complete.
- [ ] 4.7 Resolve every Critical/High/Medium architecture finding without production implementation.
- [ ] 4.8 Obtain and record the new final architecture `APPROVE` SHA. No post-amendment production implementation before this gate.

## 5. Post-approval exact-model capability and parser implementation

- [ ] 5.1 Make `diagnostic_dispatch`/unified exact-model registration conform to the final approved matrix; preserve RPG310 speaker step `2` and set exact TE40 `microphone_adjust` supported only through the MIC1 binding.
- [ ] 5.2 TE40: normalize numeric static `micValue` to canonical `microphone_volume` and independent mute evidence to `microphone_muted`.
- [ ] 5.3 TE40: implement primary MIC1 gain mutation exactly: one `-`/`+` = `1 dB`, display `-12..+9 dB`, wire `0..21`, save via `WEB_SaveAudioMicCtrlParams`, preserve unrelated current audio-input payload state, reconcile through `WEB_InitAudioCtrlParamsAPI.micValue`, and apply blocked/unconfirmed safety on ambiguous/mismatched readback.
- [ ] 5.4 TE40: preserve microphone mute as a separate supported desired-state/readback operation; gain must not reuse mute commands.
- [ ] 5.5 TE40 camera: process `itemList` as zero-to-many; cover exactly-one-camera hardware shape.
- [ ] 5.6 Box 310 LIVE: implement only the final approved envelope/device-role/parser contract from tasks 3.5-3.7; exact Box identity remains independent from Bar.
- [ ] 5.7 Keep CloudLink microphone gain and all-five reboot unsupported/local-only with zero network I/O.
- [ ] 5.8 Preserve TE20/RPG310 microphone-mute semantics and no fabricated numeric gain.

## 6. Post-approval presentation and LIVE implementation

- [ ] 6.1 Render Audio card in exact order: `Микрофон (уровень)`, `Динамик (уровень)`, `Громкость микрофона`, `Громкость динамиков`.
- [ ] 6.2 TE20/TE40: map accepted `MicValueIndex` to the microphone meter and `SpeakerValueIndex` to the speaker meter.
- [ ] 6.3 Remove redundant textual `Live микрофон` / `Live динамик` rows for Huawei TE live evidence.
- [ ] 6.4 TE40: display configured `micValue` using exact dB transform (`21 -> +9 dB`, `18 -> +6 dB`, `12 -> 0 dB`, `0 -> -12 dB`) independently from live `MicValueIndex` and mute; `-`/`+` requests exactly one dB through typed application intent.
- [ ] 6.5 Bar/Box: keep approved microphone LIVE meter behavior; speaker live meter remains unsupported. Current Bar fixed-field capture must not be reused as Box parser evidence.
- [ ] 6.6 RPG310: no fabricated live meters.
- [ ] 6.7 Update repository-local visual acceptance tests/checkpoints for the two-meter Audio-card contract and TE40 dB configured-value presentation.

## 7. Initial three-call preview and explicit journal

- [ ] 7.1 After the **entire** automatic room cycle is terminal, admit automatic call preview only for the exact current expanded connected/usable call-log-capable codec row.
- [ ] 7.2 For that exact row/generation, perform one fresh serialized call-history acquisition before first LIVE; normalize newest-first and retain at most three preview rows.
- [ ] 7.3 If no codec row is expanded at whole-room terminal time, perform zero hidden preview I/O until an eligible row is later expanded.
- [ ] 7.4 After a row/generation automatic attempt is terminal, collapse/re-expand, repaint, resize, theme switch and duplicate Qt events cause zero additional automatic call-log I/O.
- [ ] 7.5 Row switch may admit the newly current codec's own first generation-bound preview after prior lifecycle cleanup; stale old callbacks remain powerless.
- [ ] 7.6 Ordinary preview failure/no-data reaches bounded cleanup and does not permanently degrade a connected row; first LIVE may start afterward if still eligible.
- [ ] 7.7 Every explicit `Развернуть` remains a separate fresh call-log acquisition; active LIVE retires/resumes through bounded cleanup.
- [ ] 7.8 Add end-to-end call-log regressions for TE20, TE40, Bar310, Box310 and RPG310 proving up-to-three automatic rows and fresh explicit detail.

## 8. Existing speaker/control safety regression

- [ ] 8.1 Preserve speaker ranges/steps: TE20/TE40 `0..21/1`, Bar/Box `0..15/1`, RPG310 `0..100/2`.
- [ ] 8.2 Preserve speaker zero/restore mute using only proven exact-row/generation positive restore evidence.
- [ ] 8.3 Preserve no-restore unmute at `0` as local unavailable with zero mutation/handler/device I/O.
- [ ] 8.4 Preserve mutation blocked/unconfirmed safety after possible send + failed/ambiguous readback; no blind replay. Apply the same root safety to TE40 MIC1 gain.
- [ ] 8.5 Preserve Local Refresh, cancellation, cleanup timeout, stale-callback and no-indefinite-lock behavior after amended lifecycles.

## 9. Post-amendment implementation validation

- [ ] 9.1 Run focused parser/codec-control/live/call-log/camera/lifecycle tests.
- [ ] 9.2 Run the full offline unittest suite.
- [ ] 9.3 Run `.\openspec.cmd validate codec-interaction-parity-restoration --strict`.
- [ ] 9.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 9.5 Run `git diff --check` and `git diff --cached --check`.
- [ ] 9.6 Synchronize implementation evidence/tasks without treating synthetic tests as hardware acceptance.
- [ ] 9.7 Create and push focused implementation commit(s). Implementation session MUST NOT issue the independent final verdict.

## 10. Exact-SHA hardware acceptance

Current five-model scope remains TE20, TE40, Bar310, Box310 and RPG310. Physical availability at any one moment does not count as acceptance evidence.

- [ ] 10.1 Run every applicable in-scope hardware scenario against the exact published post-amendment implementation SHA.
- [ ] 10.2 TE40: verify static numeric mic value/dB display, MIC1 gain `-`/`+` exact `1 dB` step and numeric readback, independent mute, two live meters, exactly-one-camera behavior, automatic three-call preview, explicit fresh journal, speaker controls and Local Refresh.
- [ ] 10.3 Box310: verify final approved live parser against real response roles/envelope plus automatic three-call preview and explicit fresh journal.
- [ ] 10.4 TE20/Bar310/RPG310: rerun all applicable original hardware gates plus new automatic three-call lifecycle and new Audio-card negative/positive meter expectations.
- [ ] 10.5 Record exact SHA, model, action, non-secret method/path, raw outcome category, normalized result, GUI result and UI-unlocked status for every scenario.
- [ ] 10.6 Missing/failed required hardware evidence is blocking `CHANGES REQUIRED` regardless of offline test count.

## 11. Independent validation

- [ ] 11.1 Validate the exact published remote implementation SHA from a clean detached worktree.
- [ ] 11.2 Re-run focused/full tests, strict OpenSpec validation, Git checks and required disposable archive-applicability check.
- [ ] 11.3 Review implementation against the **new approved architecture SHA**, root MODIFIED contracts, exact-row call-preview boundary, TE40 MIC1 gain contract, final Box live parser contract, root mutation safety and behavioral oracle.
- [ ] 11.4 Confirm all five models passed every applicable hardware gate on the exact validated implementation SHA.
- [ ] 11.5 Issue only `APPROVE`, `APPROVE WITH NON-BLOCKING NOTES`, or `CHANGES REQUIRED` according to repository rules.

## 12. Archive + completion

- [ ] 12.1 Archive only after a permitting independent verdict that includes mandatory hardware acceptance.
- [ ] 12.2 Review root-spec/archive diff for duplicate or contradictory capability, Audio-card, call-preview, TE40 gain, Box parser, restore-authority or currentness contracts.
- [ ] 12.3 Run strict all-artifact validation, full offline tests and Git checks after archive.
- [ ] 12.4 Create/push dedicated archive commit.
- [ ] 12.5 Merge only with explicit user authorization.
