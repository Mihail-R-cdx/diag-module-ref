# Tasks: codec-interaction-parity-restoration

## 1. Historical baseline and first implementation cycle

- [x] 1.1 Compare current `master` with pre-codec-redesign `c442152077dd8aa6251f1d8be9fc98b765406dbd` and treat legacy `CodecScreen` as behavioral evidence, not room authority.
- [x] 1.2 Establish the original exact-model matrix, parser normalization, LIVE/call-log lifecycle and hardware gate.
- [x] 1.3 Obtain the original architecture `APPROVE` and implement through published SHA `467f2cbb502f698476f047d277052bf5ccb55147`.
- [x] 1.4 Independently validate `467f2cbb...` offline; result was `PASS FOR HARDWARE ACCEPTANCE`.
- [x] 1.5 Begin hardware acceptance and record that real-device findings invalidate parts of the original architecture; `467f2cbb...` is discovery baseline only.

## 2. Hardware-discovered architecture amendment

- [x] 2.1 Publish first amendment `969e4a55e44a4f6879daa5c664de812141fa1704`.
- [x] 2.2 Independently review `969e4a55...`; verdict `CHANGES REQUIRED` with 4 HIGH and 1 MEDIUM findings.
- [x] 2.3 Resolve root capability conflict through archive-compatible `MODIFIED Requirements`.
- [x] 2.4 Resolve adapter conflict; TE20/RPG remain mute-only, TE40 gain/mute independent.
- [x] 2.5 Resolve root presentation conflict with the two-live-meter Audio-card contract.
- [x] 2.6 Replace root visual-checkpoint requirement with exact new Audio-card order.
- [x] 2.7 Resolve automatic-preview lifecycle ambiguity: whole automatic room cycle terminal + exact codec current/expanded/usable -> one fresh preview -> cleanup -> first eligible LIVE.
- [x] 2.8 Keep collapsed/non-current codec rows free of automatic call-log network I/O.
- [x] 2.9 Remove unproven Box `max(all curVolume)` contract.
- [x] 2.10 Publish remediation `918a046a4f525a3f2fede8dc142e6c1e8fbcf295`.
- [x] 2.11 Publish `df5447abe556d53ce3d7fd2a2a56e1c042918272` with proven TE40 MIC1 setter/range/step/readback.
- [x] 2.12 Review `df5447...`; verdict `CHANGES REQUIRED` with 2 HIGH findings: unresolved Box LIVE architecture and stale full-state TE40 save risk.

## 3. Final architecture corrections before validation

- [x] 3.1 TE40 gain setter boundary: `POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams`.
- [x] 3.2 TE40 gain scale: native `-12..+9 dB`, step `1 dB`; wire `0..21`, step `1`; `gain_db = mic1Value - 12`.
- [x] 3.3 TE40 ACK/readback: ACK is non-authoritative; numeric target evidence uses approved TE40 audio-control readback; mute independent.
- [x] 3.4 Strengthen TE40 full-state mutation: after MUTATION owns lane and LIVE retires, require a fresh full `WEB_InitAudioCtrlParamsAPI` audio-control read before POST; old accepted cache is not payload authority.
- [x] 3.5 Require fresh pre-write state to contain `micall`, `mic1..mic18`, `mic1Value..mic18Value`; if incomplete, send nothing and do not create command ambiguity solely from that pre-submit failure.
- [x] 3.6 Require post-write full-state reconciliation of MIC1 target plus every preserved non-target microphone field against the fresh pre-write baseline; collateral mismatch is blocked/unconfirmed and never silently accepted/replayed.
- [x] 3.7 Resolve Box LIVE architecture by explicit scope reduction: Box post-cycle microphone LIVE is UNSUPPORTED/DEFERRED in this change, exact Box registration has no LIVE binding, and room LIVE performs zero Box `WEB_GetCurrentAudioParam` polling.
- [x] 3.8 Preserve Box non-LIVE scope: diagnostics, speaker controls, call-log automatic preview/detail, Local Refresh, exact identity/currentness/cleanup remain in scope.
- [x] 3.9 Preserve earlier `{deviceId, curVolume}` observations only as future Box LIVE discovery evidence; Bar `mic*ValueIndex` evidence is Bar-only; no current Box parser implementation task remains.

## 4. Architecture validation and approval

- [ ] 4.1 Re-read all current root specs affected by this change and confirm no competing capability/presentation/lifecycle contract remains, including Box LIVE deferred semantics and TE40 fresh full-state mutation safety.
- [ ] 4.2 Run `.\openspec.cmd validate codec-interaction-parity-restoration --strict` through the tracked repository-local wrapper.
- [ ] 4.3 Run `.\openspec.cmd validate --all --strict`.
- [ ] 4.4 Run disposable archive-applicability check for all `MODIFIED Requirements`; verify every replaced root requirement/scenario remains archive-compatible.
- [ ] 4.5 Run Git hygiene checks applicable to architecture artifacts (`git diff --check`, `git diff --cached --check`).
- [ ] 4.6 Perform independent architecture review against the exact published amendment SHA after 3.1-3.9 are complete.
- [ ] 4.7 Resolve every Critical/High/Medium architecture finding without production implementation.
- [ ] 4.8 Obtain and record the new final architecture `APPROVE` SHA. No post-amendment production implementation before this gate.

## 5. Post-approval exact-model capability and parser implementation

- [ ] 5.1 Make `diagnostic_dispatch`/unified exact-model registration conform to final approved matrix; preserve RPG310 speaker step `2`; TE40 `microphone_adjust` supported only through MIC1 binding.
- [ ] 5.2 TE40: normalize numeric static `micValue` to canonical `microphone_volume` and independent mute evidence to `microphone_muted`.
- [ ] 5.3 TE40: implement MIC1 gain mutation with mandatory fresh full-state pre-read after lane ownership/LIVE retirement; build save payload only from that fresh state; change only target `mic1Value`; send once via `WEB_SaveAudioMicCtrlParams`.
- [ ] 5.4 TE40: post-write full-state reconciliation must confirm target plus preserved non-target `micall`/`micN`/`micNValue`; insufficient/collateral mismatch -> blocked/unconfirmed, no replay.
- [ ] 5.5 TE40: preserve microphone mute as a separate supported desired-state/readback operation.
- [ ] 5.6 TE40 camera: process `itemList` as zero-to-many; cover exactly-one-camera shape.
- [ ] 5.7 Box 310: remove/disable post-cycle LIVE binding in unified registration for this change; do not implement a new Box LIVE parser and admit zero Box LIVE `WEB_GetCurrentAudioParam` requests.
- [ ] 5.8 Keep CloudLink microphone gain and all-five reboot unsupported/local-only with zero network I/O.
- [ ] 5.9 Preserve TE20/RPG310 microphone-mute semantics and no fabricated numeric gain.

## 6. Post-approval presentation and LIVE implementation

- [ ] 6.1 Render Audio card in exact order: `Микрофон (уровень)`, `Динамик (уровень)`, `Громкость микрофона`, `Громкость динамиков`.
- [ ] 6.2 TE20/TE40: map accepted `MicValueIndex` to microphone meter and `SpeakerValueIndex` to speaker meter.
- [ ] 6.3 Remove redundant textual `Live микрофон` / `Live динамик` rows for Huawei.
- [ ] 6.4 TE40: display configured `micValue` via exact dB transform and make `-`/`+` request exactly one dB through typed application intent.
- [ ] 6.5 Bar310: preserve approved microphone LIVE meter; speaker live meter unsupported.
- [ ] 6.6 Box310: both live-level slots render `Не поддерживается`; no historical/stale Box meter data is rendered as current and no Box LIVE lifecycle is implied.
- [ ] 6.7 RPG310: both live-level slots unsupported.
- [ ] 6.8 Update repository-local visual acceptance tests/checkpoints for Huawei two-meter contract, TE40 dB value, and Box deferred LIVE state.

## 7. Initial three-call preview and explicit journal

- [ ] 7.1 After the **entire** automatic room cycle is terminal, admit automatic call preview only for the exact current expanded connected/usable call-log-capable codec row.
- [ ] 7.2 For that exact row/generation, perform one fresh serialized call-history acquisition before first eligible LIVE; normalize newest-first and retain at most three preview rows.
- [ ] 7.3 If no codec row is expanded at whole-room terminal time, perform zero hidden preview I/O until an eligible row is later expanded.
- [ ] 7.4 After a row/generation automatic attempt is terminal, collapse/re-expand, repaint, resize, theme switch and duplicate Qt events cause zero additional automatic call-log I/O.
- [ ] 7.5 Row switch may admit the newly current codec's own first generation-bound preview after prior lifecycle cleanup; stale old callbacks remain powerless.
- [ ] 7.6 Ordinary preview failure/no-data reaches bounded cleanup and does not permanently degrade a connected row; first eligible LIVE may start afterward.
- [ ] 7.7 Every explicit `Развернуть` remains a separate fresh call-log acquisition; active LIVE retires/resumes where that exact model actually has LIVE. Box has no LIVE retirement/resume in this change.
- [ ] 7.8 Add end-to-end call-log regressions for TE20, TE40, Bar310, Box310 and RPG310 proving up-to-three automatic rows and fresh explicit detail.

## 8. Existing speaker/control safety regression

- [ ] 8.1 Preserve speaker ranges/steps: TE20/TE40 `0..21/1`, Bar/Box `0..15/1`, RPG310 `0..100/2`.
- [ ] 8.2 Preserve speaker zero/restore mute using only proven exact-row/generation positive restore evidence.
- [ ] 8.3 Preserve no-restore unmute at `0` as local unavailable with zero mutation/handler/device I/O.
- [ ] 8.4 Preserve root blocked/unconfirmed safety after possible send + failed/ambiguous readback; apply to TE40 MIC1 target or collateral mismatch.
- [ ] 8.5 Preserve definite pre-submit semantics: TE40 fresh pre-read failure before save does not create `unconfirmed_after_command` solely from no-send.
- [ ] 8.6 Preserve Local Refresh, cancellation, cleanup timeout, stale-callback and no-indefinite-lock behavior after amended lifecycles.

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
- [ ] 10.2 TE40: verify static numeric mic value/dB display, MIC1 gain exact `1 dB` step, fresh pre-write state acquisition, independent mute, two live meters, exactly-one-camera behavior, automatic three-call preview, explicit fresh journal, speaker controls and Local Refresh.
- [ ] 10.3 TE40 mutation safety: where feasible, verify non-target microphone state is preserved; target/collateral reconciliation failure must not yield confirmed success or blind replay.
- [ ] 10.4 Box310: verify **deferred LIVE contract** — no Box post-cycle LIVE request/binding and both live-level slots show `Не поддерживается`; separately verify automatic three-call preview, explicit fresh journal, speaker controls and Local Refresh.
- [ ] 10.5 TE20/Bar310/RPG310: rerun all applicable original hardware gates plus new automatic three-call lifecycle and Audio-card expectations.
- [ ] 10.6 Record exact SHA, model, action, non-secret method/path, raw outcome category, normalized result, GUI result and UI-unlocked status for every scenario.
- [ ] 10.7 Missing/failed required hardware evidence is blocking `CHANGES REQUIRED` regardless of offline test count.

## 11. Independent validation

- [ ] 11.1 Validate the exact published remote implementation SHA from a clean detached worktree.
- [ ] 11.2 Re-run focused/full tests, strict OpenSpec validation, Git checks and required disposable archive-applicability check.
- [ ] 11.3 Review implementation against the **new approved architecture SHA**, root MODIFIED contracts, exact-row call-preview boundary, TE40 fresh full-state MIC1 contract, Box deferred LIVE contract, root mutation safety and behavioral oracle.
- [ ] 11.4 Confirm all five models passed every applicable hardware gate on the exact validated implementation SHA.
- [ ] 11.5 Issue only `APPROVE`, `APPROVE WITH NON-BLOCKING NOTES`, or `CHANGES REQUIRED` according to repository rules.

## 12. Archive + completion

- [ ] 12.1 Archive only after a permitting independent verdict that includes mandatory hardware acceptance.
- [ ] 12.2 Review root-spec/archive diff for duplicate or contradictory capability, Audio-card, call-preview, TE40 gain/full-state safety, Box deferred LIVE, restore-authority or currentness contracts.
- [ ] 12.3 Run strict all-artifact validation, full offline tests and Git checks after archive.
- [ ] 12.4 Create/push dedicated archive commit.
- [ ] 12.5 Merge only with explicit user authorization.

## Deferred follow-up (not a completion gate for this change)

A separate reviewed change is required to restore `CloudLink Box 310` microphone LIVE when hardware is available. It must prove the complete Box response envelope, microphone device-role selection, numeric validity, aggregation, normalization and unavailable/error semantics before re-advertising a Box LIVE binding.
