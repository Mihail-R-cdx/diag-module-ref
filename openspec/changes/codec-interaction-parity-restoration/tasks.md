# Tasks: codec-interaction-parity-restoration

## 1. Forensic baseline

- [x] 1.1 Compare current `master` with pre-codec-redesign `c442152077dd8aa6251f1d8be9fc98b765406dbd`.
- [x] 1.2 Confirm that the principal regression boundary is room interaction/composition rather than wholesale handler replacement.
- [x] 1.3 Document retained legacy `CodecScreen` behavior as a behavioral oracle, not as new room authority.
- [x] 1.4 Confirm the pre-redesign Polycom speaker step is `2`, while current registry uses `1`.
- [x] 1.5 Confirm static microphone evidence differs by exact model and requires explicit normalization before common presentation.

## 2. OpenSpec / architecture

### Original approved architecture cycle

- [x] 2.1 Create proposal, design, delta specs, and task plan.
- [x] 2.2 Review exact current root specs and implementation against this design for contradictions or missing model-specific behavior.
- [x] 2.3 Perform independent architecture review; result: `CHANGES REQUIRED` with 2 HIGH and 2 MEDIUM findings.
- [x] 2.4 Resolve the first architecture findings by adding the normative exact-model capability matrix, microphone normalization contract, hardware gate rules, and explicit defect/action inventory.
- [x] 2.5 Resolve all hardware-availability rows to `AVAILABLE` based on the user's commitment to provide TE20, TE40, Bar 310, Box 310, and RPG 310 after implementation; hardware execution remains a post-implementation exact-SHA gate.
- [x] 2.6 Resolve follow-up architecture findings: remove invented first-unmute fallback; replace the conflicting automatic-preview lifecycle contract with LIVE-priority `MODIFIED` semantics; modify parallel call-log contracts and preserve all replaced root scenario names for archive applicability.
- [x] 2.7 Run a disposable repository-local archive-applicability check for the original approved architecture SHA.
- [x] 2.8 Obtain original architecture `APPROVE` before the first implementation cycle.

### Hardware-discovered architecture amendment after `467f2cbb...`

- [x] 2.9 Amend proposal/design/delta specs from hardware findings: TE40 independent numeric microphone gain, TE40 one-or-more camera parsing, TE live meter presentation, mandatory initial three-call preview before LIVE, and Box 310 `{deviceId, curVolume}` live parsing.
- [ ] 2.10 Run `.\openspec.cmd validate codec-interaction-parity-restoration --strict` and `.\openspec.cmd validate --all --strict` using the repository-local wrapper against the amended architecture HEAD.
- [ ] 2.11 Re-run the disposable archive-applicability check because the `MODIFIED` call-log/lifecycle requirements changed again; preserve required root requirement/scenario replacement compatibility.
- [ ] 2.12 Perform independent architecture review of the amended artifacts and resolve every Critical/High/Medium finding.
- [ ] 2.13 Obtain a new final architecture `APPROVE` and record the exact approved architecture SHA before any post-amendment production implementation.

## 3. Exact-model capability parity

- [x] 3.1 Original architecture fixed a normative matrix for TE20, TE40, Bar 310, Box 310, and RPG310.
- [ ] 3.2 Make `diagnostic_dispatch` conform to the **amended** matrix, including TE40 independent microphone gain and existing RPG310 speaker step `2`.
- [ ] 3.3 Make visible actionable controls agree with the amended exact-model capability descriptor, including separate TE40 gain and mute controls.
- [x] 3.4 Keep intentionally unsupported operations fail-closed before room interaction admission/device I/O where the amended matrix still says `NO`.
- [x] 3.5 Preserve CloudLink microphone-gain prohibition and do not invent reboot capability.
- [ ] 3.6 Update startup/registry tests so implementation descriptors fail if they contradict the amended matrix.
- [ ] 3.7 Do not add TE30/TE50/TE60 in this amendment; broader TE-family model expansion remains a follow-up scope.

## 4. Static codec audio and device normalization

- [x] 4.1 Preserve actual parser/handler evidence and normalize it into canonical room fields before presentation.
- [x] 4.2 TE20: map authoritative `mic_mute` evidence to canonical `microphone_muted`; do not fabricate numeric `microphone_volume`.
- [ ] 4.3 TE40: map authoritative numeric `micValue` to canonical `microphone_volume` and independently map `MicSwitch`/mute evidence to `microphone_muted`; do not derive one from the other.
- [x] 4.4 CloudLink Bar 310: map authoritative diagnostic `mic_volume` to canonical numeric `microphone_volume`; publish mute only from authoritative mute evidence.
- [x] 4.5 CloudLink Box 310 static diagnostic normalization remains independent from live-meter parsing; publish mute only from authoritative mute evidence.
- [x] 4.6 Polycom RPG 310: map authoritative microphone mute evidence to canonical `microphone_muted`; do not fabricate numeric gain.
- [ ] 4.7 Add/update transport-edge parser/normalizer/session/dashboard regressions for TE40 numeric gain + mute; prebuilding canonical fields is insufficient.
- [ ] 4.8 TE40 camera: change `WEB_GetLocalCameraList.itemList` parsing from `len >= 2` to zero-to-many independent entries and cover exactly-one-camera hardware shape.

## 5. Live telemetry parity

- [ ] 5.1 Replace the superseded LIVE-priority automatic-preview skip with one mandatory fresh initial call-history acquisition per current row/generation before first LIVE start.
- [x] 5.2 Preserve CloudLink Bar live microphone meter using the approved Bar meter/session path.
- [ ] 5.3 CloudLink Box 310: replace fixed `mic1ValueIndex` / `micArray...` parsing with Box-specific extraction of hardware-observed `{deviceId, curVolume}` records and max valid numeric `curVolume` aggregation.
- [x] 5.4 Preserve TE20/TE40 room-owned `get_live_audio_status` acquisition with 2-second cadence, currentness, and bounded cleanup.
- [ ] 5.5 Present TE20/TE40 `MicValueIndex` through the existing `Микрофон (уровень)` meter and `SpeakerValueIndex` through a dedicated `Динамик (уровень)` meter; remove redundant textual `Live микрофон` / `Live динамик` rows.
- [x] 5.6 Do not fabricate unsupported Polycom live telemetry.
- [ ] 5.7 Add integration regressions proving initial preview finishes before first LIVE, expansion/re-render causes no extra automatic preview I/O, and explicit journal retires/resumes LIVE correctly.

## 6. Call-log parity

- [x] 6.1 Preserve fresh explicit call-log acquisition through proven model-specific retrieval methods.
- [x] 6.2 Keep explicit journal correctness independent from automatic preview state.
- [ ] 6.3 Implement one fresh automatic initial call-history acquisition for every call-log-capable exact model after initial diagnostic acceptance and before first LIVE start.
- [ ] 6.4 Normalize automatic results newest-first and publish at most the three newest records inline; fewer than three displays all available records.
- [ ] 6.5 Ensure collapse/re-expand, repaint, resize, theme switch and duplicate expansion notifications create zero additional automatic call-history I/O in the same room generation.
- [ ] 6.6 Ensure ordinary initial-preview failure/no-data reaches bounded cleanup, does not permanently degrade a connected row, and still permits LIVE afterward; typed connection/session failures retain existing semantics.
- [ ] 6.7 Update Box 310 end-to-end call-history regression oracle: initial fresh preview before LIVE + up-to-three inline records + later fresh explicit detailed acquisition.
- [ ] 6.8 Preserve Polycom's working call-log path while adding the same initial three-call preview lifecycle.

## 7. Codec audio controls and Local Refresh

- [x] 7.1 Speaker `-/+` uses one serialized model-specific operation plus targeted `get_speaker_volume` readback.
- [x] 7.2 Preserve exact speaker range/step: TE20/TE40 `0..21/1`, Bar/Box `0..15/1`, RPG310 `0..100/2`.
- [x] 7.3 Preserve supported speaker zero/restore mute semantics only from authoritative current volume plus proven exact-row/generation restore evidence.
- [x] 7.4 Preserve root no-restore safety: `speaker_volume=0` without proven positive restore -> local unavailable, zero mutation/handler/device I/O, no stuck lane.
- [ ] 7.5 Recover and verify the actual TE40 microphone-gain setter protocol: non-secret method/ActionID, payload, accepted numeric range/step, and authoritative numeric `micValue` readback. Do not guess.
- [ ] 7.6 Implement TE40 microphone gain as an independent numeric mutation/readback path; `+/-` must never map to mute/unmute.
- [ ] 7.7 Preserve TE40 microphone mute as a separate desired-state operation/readback based on authoritative mute evidence; gain value must not determine mute state.
- [x] 7.8 Preserve TE20/RPG310 microphone mute semantics; do not infer numeric gain for them.
- [x] 7.9 Bar/Box microphone `-/+` remains disabled/hidden/local-only; zero gain network I/O.
- [x] 7.10 Reboot remains disabled/hidden/local-only for all five; zero reboot network I/O.
- [x] 7.11 Preserve blocked/unconfirmed safety when a mutation may have been sent but authoritative readback cannot confirm final state; no blind replay.
- [ ] 7.12 Add TE40 gain mutation regressions for success, ambiguous send, readback mismatch/unavailable, cancellation, timeout, stale callback, and LIVE retire/resume.
- [ ] 7.13 Re-run Local Refresh/no-indefinite-lock regressions after the amended interaction changes.

## 8. Defect/action acceptance inventory

For every row marked `In scope = YES` in amended `design.md`, produce explicit acceptance evidence; passing a different model/action does not satisfy the row.

- [ ] 8.1 `Обновить статус`: reproduce/verify per exact model in scope.
- [ ] 8.2 Automatic initial call preview: verify one fresh acquisition and up to three newest rows for every supported exact model without pressing `Развернуть`.
- [ ] 8.3 Explicit `Журнал звонков` / `Развернуть`: verify fresh acquisition per exact model independently from preview.
- [ ] 8.4 CloudLink Bar/Box live microphone bar: verify continuous operation; Box must parse actual `{deviceId, curVolume}` response.
- [ ] 8.5 TE20/TE40 live audio: verify microphone and speaker **meter** presentation and absence of redundant textual live rows.
- [ ] 8.6 TE40 numeric microphone gain: verify current value, `-`/`+` exact step, authoritative numeric readback, and no unintended mute-state change.
- [ ] 8.7 TE40 microphone mute: verify independent mute/readback while numeric gain remains separately represented.
- [ ] 8.8 TE40 camera: verify exactly-one-camera response renders known camera evidence rather than `Нет данных`.
- [ ] 8.9 Speaker `-/+`: verify exact range/step/readback per model; Polycom must move by `2`.
- [ ] 8.10 Speaker mute: verify positive -> mute -> unmute zero/restore semantics and authoritative readback per model when restore evidence exists.
- [ ] 8.11 No-restore speaker unmute: start with authoritative `speaker_volume=0` and no proven positive restore value, press Unmute, verify local unavailable, zero handler/session/device I/O, and no stuck UI/lane.
- [ ] 8.12 TE20/RPG310 microphone mute regression remains correct.
- [ ] 8.13 Bar/Box microphone gain affordance remains non-actionable with zero gain I/O.
- [ ] 8.14 Reboot affordance remains non-actionable with zero reboot I/O for all five.
- [ ] 8.15 Verify no in-scope action leaves row/top controls or room lane permanently locked after success/failure/cancel/timeout/local-unavailable result.

## 9. Hardware-backed acceptance

### Availability resolution

- [x] 9.1 CloudLink Bar 310: `AVAILABLE`.
- [x] 9.2 CloudLink Box 310: `AVAILABLE`.
- [x] 9.3 Huawei TE20: `AVAILABLE`.
- [x] 9.4 Huawei TE40: `AVAILABLE`.
- [x] 9.5 Polycom RPG 310: `AVAILABLE`.

### Discovery evidence from superseded pre-hardware baseline

- [x] 9.6 Hardware testing of `467f2cbb502f698476f047d277052bf5ccb55147` identified architecture-discovery findings: TE40 gain/meter/camera/initial-preview mismatches and Box live parser mismatch. This is discovery evidence only, not final acceptance.

### Hardware gate on post-amendment published implementation SHA

- [ ] 9.7 Run every applicable in-scope hardware scenario for all five models against the exact published post-amendment feature SHA and record non-secret request/result/GUI/unlock evidence.
- [ ] 9.8 Hardware evidence MUST include the exact published implementation SHA; evidence from `467f2cbb...` or another commit/branch does not satisfy the final gate.
- [ ] 9.9 TE40 microphone-gain evidence MUST include verified non-secret setter method/ActionID and prove expected numeric readback/step independently from mute state.
- [ ] 9.10 A missing or failed required scenario for any model is a blocking validation failure (`CHANGES REQUIRED`) regardless of offline test count.

## 10. Post-amendment implementation validation

The checks previously completed for `467f2cbb...` are historical evidence only and must be rerun after amended implementation.

- [ ] 10.1 Run focused codec interaction/call-log/live/parser/TE40-gain/camera tests.
- [ ] 10.2 Run full offline test suite.
- [ ] 10.3 Run `.\openspec.cmd validate codec-interaction-parity-restoration --strict` using the repository-local wrapper.
- [ ] 10.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 10.5 Run `git diff --check` and `git diff --cached --check`.
- [ ] 10.6 Synchronize implementation evidence without replacing hardware acceptance with synthetic evidence.
- [ ] 10.7 Create and push focused post-amendment implementation commit(s).

## 11. Independent validation

- [ ] 11.1 Validate the exact published remote post-amendment feature SHA from a clean detached worktree.
- [ ] 11.2 Re-run required focused/full tests and strict OpenSpec validation independently.
- [ ] 11.3 Review implementation against the **new approved architecture SHA**, amended exact-model matrix, initial-preview-before-LIVE lifecycle, TE40 gain/mute separation, camera contract, Box live parser, root restore-authority rule, and behavioral oracle.
- [ ] 11.4 Confirm parser/normalizer regressions start at the transport edge and are not satisfied only by prebuilt canonical snapshots.
- [ ] 11.5 Confirm all five models passed every applicable mandatory hardware gate on the exact validated published SHA.
- [ ] 11.6 If any required hardware scenario is missing/failed, issue `CHANGES REQUIRED`; offline PASS cannot override it.
- [ ] 11.7 Issue one permitted verdict: `APPROVE`, `APPROVE WITH NON-BLOCKING NOTES`, or `CHANGES REQUIRED`.

## 12. Archive + completion

- [ ] 12.1 Archive only after a permitting independent verdict that also satisfies the mandatory hardware gate.
- [ ] 12.2 Review resulting root-spec/archive diff and ensure no duplicate/contradictory codec capability, restore-authority, preview lifecycle, TE40 gain/mute, Box live parser, or normalization contracts.
- [ ] 12.3 Run strict all-artifact validation, full offline tests, and Git checks after archive.
- [ ] 12.4 Preserve exact-SHA hardware evidence for all five available models in completion reporting.
- [ ] 12.5 Create and push a dedicated archive commit.
- [ ] 12.6 Merge only with explicit user authorization.
