# Tasks: codec-interaction-parity-restoration

## 1. Forensic baseline

- [x] 1.1 Compare current `master` with pre-codec-redesign `c442152077dd8aa6251f1d8be9fc98b765406dbd`.
- [x] 1.2 Confirm that the principal regression boundary is room interaction/composition rather than wholesale handler replacement.
- [x] 1.3 Document retained legacy `CodecScreen` behavior as a behavioral oracle, not as new room authority.
- [x] 1.4 Confirm the pre-redesign Polycom speaker step is `2`, while current registry uses `1`.
- [x] 1.5 Confirm static microphone evidence differs by exact model and requires explicit normalization before common presentation.

## 2. OpenSpec / architecture

- [x] 2.1 Create proposal, design, delta specs, and task plan.
- [x] 2.2 Review exact current root specs and implementation against this design for contradictions or missing model-specific behavior.
- [x] 2.3 Perform independent architecture review; result: `CHANGES REQUIRED` with 2 HIGH and 2 MEDIUM findings.
- [x] 2.4 Resolve the architecture findings by adding the normative exact-model capability matrix, microphone normalization contract, hardware gate rules, and explicit defect/action inventory.
- [ ] 2.5 Resolve every `UNCONFIRMED` hardware-availability row to `AVAILABLE` or `UNAVAILABLE`; implementation SHALL NOT start while any row remains `UNCONFIRMED`.
- [ ] 2.6 Obtain final architecture `APPROVE` before implementation.

## 3. Exact-model capability parity

- [x] 3.1 Architecture fixes the normative matrix for TE20, TE40, Bar 310, Box 310, and Polycom RPG 310; implementation is not allowed to invent/downgrade capability values.
- [ ] 3.2 Make `diagnostic_dispatch` conform to the approved matrix, including Polycom speaker step `2`.
- [ ] 3.3 Make visible actionable controls agree with the exact-model capability descriptor.
- [ ] 3.4 Keep intentionally unsupported operations fail-closed before room interaction admission/device I/O.
- [ ] 3.5 Preserve CloudLink microphone-gain prohibition and do not invent reboot capability.
- [ ] 3.6 Add startup/registry tests that fail if implementation descriptors contradict the normative matrix.

## 4. Static codec audio normalization

- [ ] 4.1 Preserve actual parser/handler evidence and normalize it into canonical room fields before presentation.
- [ ] 4.2 TE20: map authoritative `mic_mute` evidence to canonical `microphone_muted`; do not fabricate numeric `microphone_volume`.
- [ ] 4.3 TE40: map authoritative `mic_mute` evidence to canonical `microphone_muted`; do not fabricate numeric `microphone_volume`.
- [ ] 4.4 CloudLink Bar 310: map authoritative diagnostic `mic_volume` to canonical numeric `microphone_volume`; publish mute only from authoritative mute evidence.
- [ ] 4.5 CloudLink Box 310: map authoritative diagnostic `mic_volume` to canonical numeric `microphone_volume`; publish mute only from authoritative mute evidence.
- [ ] 4.6 Polycom RPG 310: map authoritative microphone mute evidence to canonical `microphone_muted`; do not fabricate numeric gain.
- [ ] 4.7 Add end-to-end parser/normalizer/session/dashboard regressions using transport-edge fakes; manually prebuilding `microphone_volume` in a snapshot is insufficient evidence.

## 5. Live telemetry parity

- [ ] 5.1 Prevent automatic call-log preview from retiring/starving active codec LIVE.
- [ ] 5.2 Restore CloudLink Bar/Box live microphone meter using the existing proven meter/session path.
- [ ] 5.3 Restore TE20/TE40 room-owned `get_live_audio_status` telemetry with 2-second cadence, currentness, and bounded cleanup.
- [ ] 5.4 Preserve both TE20/TE40 microphone and speaker monitor evidence in the live projection.
- [ ] 5.5 Do not fabricate unsupported Polycom live telemetry.
- [ ] 5.6 Add integration regressions proving LIVE survives automatic preview behavior and resumes after explicit auxiliary actions.

## 6. Call-log parity

- [ ] 6.1 Preserve fresh explicit call-log acquisition through proven model-specific retrieval methods.
- [ ] 6.2 Decouple explicit journal correctness from automatic preview state.
- [ ] 6.3 Ensure ordinary preview/journal failure cannot strand the room lane or permanently disable the row.
- [ ] 6.4 Add composition-level call-log regressions using transport-edge fakes rather than prebuilt snapshots alone.
- [ ] 6.5 Protect Polycom's previously working call-log path as a regression oracle while restoring Huawei/CloudLink parity.

## 7. Codec audio controls and Local Refresh

- [ ] 7.1 Restore speaker `-/+` through one serialized model-specific operation plus targeted `get_speaker_volume` readback.
- [ ] 7.2 Enforce exact step/range from the matrix: TE20/TE40 `0..21/1`, Bar/Box `0..15/1`, RPG310 `0..100/2`.
- [ ] 7.3 Restore supported speaker zero/restore mute semantics from authoritative speaker-volume evidence.
- [ ] 7.4 Restore TE20/TE40/RPG310 microphone mute semantics; do not reinterpret them as numeric microphone gain.
- [ ] 7.5 Bar/Box microphone `-/+` is disabled/hidden or unmistakably local-only; no gain network I/O is admitted.
- [ ] 7.6 Reboot is disabled/hidden or unmistakably local-only for all five models; no reboot network I/O is introduced by this change.
- [ ] 7.7 Preserve blocked/unconfirmed safety when mutation readback cannot confirm final state; no blind replay.
- [ ] 7.8 Ensure Local Refresh and every in-scope codec action terminate/cleanup without indefinite UI lock on all typed outcomes.
- [ ] 7.9 Add regressions for success, auth rejection, ordinary failure, transport loss, cancellation, cleanup timeout, and stale late callbacks.

## 8. Defect/action acceptance inventory

For every row marked `In scope = YES` in `design.md`, produce explicit acceptance evidence; passing a different model/action does not satisfy the row.

- [ ] 8.1 `Обновить статус`: reproduce/verify per exact model in scope.
- [ ] 8.2 Explicit `Журнал звонков` / `Развернуть`: reproduce/verify per exact model in scope.
- [ ] 8.3 CloudLink Bar/Box live microphone bar: verify continuous operation and no preview starvation.
- [ ] 8.4 TE20/TE40 live audio: verify microphone and speaker monitor presentation.
- [ ] 8.5 Speaker `-/+`: verify exact range/step/readback per model; Polycom must move by `2`.
- [ ] 8.6 Speaker mute: verify zero/restore semantics and authoritative readback per model.
- [ ] 8.7 TE20/TE40/RPG310 microphone mute: verify supported mute/readback path.
- [ ] 8.8 Bar/Box microphone gain affordance: verify no normal actionable network control and zero gain I/O.
- [ ] 8.9 Reboot affordance: verify no normal actionable network control and zero reboot I/O for all five models.
- [ ] 8.10 Verify no in-scope action leaves row/top controls or room lane permanently locked after success/failure/cancel/timeout.

## 9. Hardware-backed acceptance

### Availability resolution before implementation

- [x] 9.1 CloudLink Bar 310 availability: `AVAILABLE` based on prior real-device work.
- [ ] 9.2 CloudLink Box 310 availability: resolve `UNCONFIRMED` -> `AVAILABLE` or `UNAVAILABLE` before architecture APPROVE.
- [ ] 9.3 Huawei TE20 availability: resolve `UNCONFIRMED` -> `AVAILABLE` or `UNAVAILABLE` before architecture APPROVE.
- [ ] 9.4 Huawei TE40 availability: resolve `UNCONFIRMED` -> `AVAILABLE` or `UNAVAILABLE` before architecture APPROVE.
- [ ] 9.5 Polycom RPG 310 availability: resolve `UNCONFIRMED` -> `AVAILABLE` or `UNAVAILABLE` before architecture APPROVE.

### Hardware gate on published implementation SHA

- [ ] 9.6 For every `AVAILABLE` model, run every applicable in-scope hardware scenario against the exact published feature SHA and record non-secret request/result/GUI/unlock evidence.
- [ ] 9.7 Hardware evidence MUST include the exact published implementation SHA; evidence from another commit/branch does not satisfy the gate.
- [ ] 9.8 A missing or failed required scenario for an `AVAILABLE` model is a blocking validation failure (`CHANGES REQUIRED`) regardless of offline test count.
- [ ] 9.9 For every `UNAVAILABLE` model, mark model-specific hardware defects explicitly `hardware-unverified`; do not represent them as proven fixed from mocks/offline tests.

## 10. Implementation validation

- [ ] 10.1 Run focused codec interaction/call-log/live/parser tests.
- [ ] 10.2 Run full offline test suite.
- [ ] 10.3 Run `.\openspec.cmd validate codec-interaction-parity-restoration --strict` using the repository-local wrapper.
- [ ] 10.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 10.5 Run `git diff --check` and `git diff --cached --check`.
- [ ] 10.6 Synchronize implementation evidence without replacing hardware acceptance with synthetic evidence.
- [ ] 10.7 Create and push focused implementation commit(s).

## 11. Independent validation

- [ ] 11.1 Validate the exact published remote feature SHA from a clean detached worktree.
- [ ] 11.2 Re-run required focused/full tests and strict OpenSpec validation independently.
- [ ] 11.3 Review implementation against the approved exact-model matrix, normalization contract, defect/action inventory, and `c442152...` behavioral oracle.
- [ ] 11.4 Confirm parser/normalizer regressions start at the transport edge and are not satisfied only by prebuilt canonical snapshots.
- [ ] 11.5 Confirm every `AVAILABLE` model passed every applicable hardware gate on the exact validated published SHA.
- [ ] 11.6 If an AVAILABLE required hardware scenario is missing/failed, issue `CHANGES REQUIRED`; offline PASS cannot override it.
- [ ] 11.7 Confirm every UNAVAILABLE model remains explicitly hardware-unverified in the final scope/report and is not described as proven fixed.
- [ ] 11.8 Issue one permitted verdict: `APPROVE`, `APPROVE WITH NON-BLOCKING NOTES`, or `CHANGES REQUIRED`.

## 12. Archive + completion

- [ ] 12.1 Archive only after a permitting independent verdict that also satisfies the mandatory AVAILABLE-model hardware gate.
- [ ] 12.2 Review resulting root-spec/archive diff and ensure no duplicate/contradictory codec capability or normalization contracts.
- [ ] 12.3 Run strict all-artifact validation, full offline tests, and Git checks after archive.
- [ ] 12.4 Preserve explicit `hardware-unverified` status for any UNAVAILABLE model in completion reporting; do not silently convert it to fixed.
- [ ] 12.5 Create and push a dedicated archive commit.
- [ ] 12.6 Merge only with explicit user authorization.
