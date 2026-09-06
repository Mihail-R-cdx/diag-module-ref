# Tasks: codec-interaction-parity-restoration

## 1. Forensic baseline

- [x] 1.1 Compare current `master` with pre-codec-redesign `c442152077dd8aa6251f1d8be9fc98b765406dbd`.
- [x] 1.2 Confirm that the principal regression boundary is room interaction/composition rather than wholesale handler replacement.
- [x] 1.3 Document retained legacy `CodecScreen` behavior as a behavioral oracle, not as new room authority.

## 2. OpenSpec / architecture

- [x] 2.1 Create proposal, design, delta specs, and task plan.
- [ ] 2.2 Review exact current root specs and implementation against this design for contradictions or missing model-specific behavior.
- [ ] 2.3 Perform independent architecture review with CRITICAL/HIGH/MEDIUM/LOW findings.
- [ ] 2.4 Resolve all blocking architecture findings.
- [ ] 2.5 Obtain final architecture `APPROVE` before implementation.

## 3. Exact-model capability parity

- [ ] 3.1 Build one explicit codec capability matrix from current registry + proven pre-redesign behavior for TE20, TE40, Bar 310, Box 310, and Polycom RPG 310.
- [ ] 3.2 Make visible actionable controls agree with the exact-model capability descriptor.
- [ ] 3.3 Keep intentionally unsupported operations fail-closed before room interaction admission/device I/O.
- [ ] 3.4 Preserve CloudLink microphone-gain prohibition unless separately proven and approved.

## 4. Live telemetry parity

- [ ] 4.1 Prevent automatic call-log preview from retiring/starving active codec LIVE.
- [ ] 4.2 Restore CloudLink Bar/Box live microphone meter using the existing proven meter/session path.
- [ ] 4.3 Restore TE20/TE40 room-owned `get_live_audio_status` telemetry with bounded cadence/currentness/cleanup.
- [ ] 4.4 Do not fabricate unsupported Polycom live telemetry.
- [ ] 4.5 Add integration regressions proving LIVE survives automatic preview behavior and resumes after explicit auxiliary actions.

## 5. Call-log parity

- [ ] 5.1 Preserve fresh explicit call-log acquisition through proven model-specific retrieval methods.
- [ ] 5.2 Decouple explicit journal correctness from automatic preview state.
- [ ] 5.3 Ensure ordinary call-log failure cannot strand the room lane or permanently disable the row.
- [ ] 5.4 Add composition-level call-log regressions using transport-edge fakes rather than prebuilt snapshots alone.

## 6. Codec audio controls and refresh

- [ ] 6.1 Restore speaker-volume +/- behavior through one serialized model-specific operation plus targeted authoritative readback.
- [ ] 6.2 Restore supported speaker/microphone mute semantics from exact current evidence.
- [ ] 6.3 Preserve current blocked/unconfirmed safety when mutation readback cannot confirm final state; no blind replay.
- [ ] 6.4 Ensure Local Refresh and codec actions terminate/cleanup without indefinite UI lock on all typed outcomes.
- [ ] 6.5 Add regressions for success, auth rejection, ordinary failure, transport loss, cancellation, cleanup timeout, and stale late callbacks.

## 7. Presentation parity

- [ ] 7.1 Show canonical microphone/speaker values when the exact model parser publishes them.
- [ ] 7.2 Render CloudLink live microphone level continuously while LIVE owns the row.
- [ ] 7.3 Render TE20/TE40 live-audio evidence according to the proven model-specific semantics.
- [ ] 7.4 Unsupported controls are disabled/hidden or clearly local-only and never appear as normal actionable network controls.

## 8. Hardware-backed acceptance

- [ ] 8.1 Validate CloudLink Box 310 affected scenarios on real hardware and record non-secret operation/result evidence.
- [ ] 8.2 Validate CloudLink Bar 310 affected scenarios on real hardware when available.
- [ ] 8.3 Validate Huawei TE20 affected scenarios on real hardware when available.
- [ ] 8.4 Validate Huawei TE40 affected scenarios on real hardware when available.
- [ ] 8.5 Validate Polycom RPG 310 affected scenarios on real hardware when available.
- [ ] 8.6 Do not mark an unavailable model's hardware-specific defect as proven fixed solely from mocked/offline tests.

## 9. Implementation validation

- [ ] 9.1 Run focused codec interaction/call-log/live tests.
- [ ] 9.2 Run full offline test suite.
- [ ] 9.3 Run `./openspec.cmd validate codec-interaction-parity-restoration --strict` using the repository-local wrapper.
- [ ] 9.4 Run `./openspec.cmd validate --all --strict`.
- [ ] 9.5 Run `git diff --check` and `git diff --cached --check`.
- [ ] 9.6 Synchronize implementation evidence without replacing hardware acceptance with synthetic evidence.
- [ ] 9.7 Create and push focused implementation commit(s).

## 10. Independent validation

- [ ] 10.1 Validate the exact published remote feature SHA from a clean detached worktree.
- [ ] 10.2 Re-run required focused/full tests and strict OpenSpec validation independently.
- [ ] 10.3 Review implementation against the approved architecture and the `c442152...` behavioral oracle.
- [ ] 10.4 Confirm hardware acceptance evidence is not substituted by snapshot/mock-only tests.
- [ ] 10.5 Issue one permitted verdict: `APPROVE`, `APPROVE WITH NON-BLOCKING NOTES`, or `CHANGES REQUIRED`.

## 11. Archive + completion

- [ ] 11.1 Archive only after a permitting independent verdict.
- [ ] 11.2 Review resulting root-spec/archive diff and ensure no duplicate/contradictory codec contracts.
- [ ] 11.3 Run strict all-artifact validation, full offline tests, and Git checks after archive.
- [ ] 11.4 Create and push a dedicated archive commit.
- [ ] 11.5 Merge only with explicit user authorization.
