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
- [x] 2.5 Resolve root presentation conflict with the then-current two-live-meter Audio-card contract (subsequently superseded by the single microphone LIVE meter contract in 9.10).
- [x] 2.6 Replace root visual-checkpoint requirement with exact new Audio-card order.
- [x] 2.7 Resolve automatic-preview lifecycle ambiguity: whole automatic room cycle terminal + exact codec current/expanded/usable -> one fresh preview -> cleanup -> first eligible LIVE.
- [x] 2.8 Keep collapsed/non-current codec rows free of automatic call-log network I/O.
- [x] 2.9 Remove unproven Box `max(all curVolume)` contract.
- [x] 2.10 Publish remediation `918a046a4f525a3f2fede8dc142e6c1e8fbcf295`.
- [x] 2.11 Publish `df5447abe556d53ce3d7fd2a2a56e1c042918272` with proven TE40 MIC1 setter/range/step/readback.
- [x] 2.12 Review `df5447...`; verdict `CHANGES REQUIRED` with 2 HIGH findings: unresolved Box LIVE architecture and stale full-state TE40 save risk.
- [x] 2.13 Publish `01faf3cc522f89f936cb4daefa70161279093f40` deferring Box LIVE and hardening TE40 fresh full-state mutation safety.
- [x] 2.14 Validate/review `01faf3...`: change strict PASS, all strict PASS, Git checks PASS, worktree clean, archive applicability FAIL; independent verdict `CHANGES REQUIRED` with one HIGH root CloudLink meter conflict and one MEDIUM Box call-log/LIVE contradiction.

## 3. Final architecture corrections before re-validation

- [x] 3.1 TE40 gain setter boundary: `POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams`.
- [x] 3.2 TE40 gain scale: native `-12..+9 dB`, step `1 dB`; wire `0..21`, step `1`; `gain_db = mic1Value - 12`.
- [x] 3.3 TE40 ACK/readback: ACK is non-authoritative; numeric target evidence uses approved TE40 audio-control readback; mute independent.
- [x] 3.4 Strengthen TE40 full-state mutation: after MUTATION owns lane and LIVE retires, require a fresh full `WEB_InitAudioCtrlParamsAPI` audio-control read before POST; old accepted cache is not payload authority.
- [x] 3.5 Require fresh pre-write state to contain `micall`, `mic1..mic18`, `mic1Value..mic18Value`; if incomplete, send nothing and do not create command ambiguity solely from that pre-submit failure.
- [x] 3.6 Require post-write full-state reconciliation of MIC1 target plus every preserved non-target microphone field against the fresh pre-write baseline; collateral mismatch is blocked/unconfirmed and never silently accepted/replayed.
- [x] 3.7 Resolve Box LIVE architecture by explicit scope reduction: Box microphone LIVE is UNSUPPORTED/DEFERRED, exact Box registration has no LIVE binding, and room LIVE performs zero Box `WEB_GetCurrentAudioParam` polling.
- [x] 3.8 Preserve Box non-LIVE scope: diagnostics, speaker controls, call-log automatic preview/detail, Local Refresh, exact identity/currentness/cleanup remain in scope.
- [x] 3.9 Preserve earlier `{deviceId, curVolume}` observations only as future Box LIVE discovery evidence; Bar evidence is Bar-only; no current Box parser implementation task remains.
- [x] 3.10 Add archive-compatible `MODIFIED Requirements` for root `cloudlink-live-microphone-metering`: Bar 310 remains the only supported CloudLink live microphone model; Box LIVE/polling is removed from root authority while historical Box endpoint knowledge remains dormant.
- [x] 3.11 Preserve every existing root CloudLink meter requirement/scenario identity needed for archive applicability while redefining Box-specific scenarios as explicit no-capability/no-polling/deferred behavior.
- [x] 3.12 Correct Box call-log regression: Box preview still runs once per eligible row/generation, but terminal cleanup releases the lane with zero Box LIVE start/resume/request; generic preview ordering references first LIVE only when exact registration actually advertises LIVE.

## 4. Architecture validation and approval

Historical validation at `01faf3cc522f89f936cb4daefa70161279093f40`:

- [x] 4.1 `.\openspec.cmd validate codec-interaction-parity-restoration --strict`: PASS.
- [x] 4.2 `.\openspec.cmd validate --all --strict`: PASS.
- [x] 4.3 `git diff --check` and `git diff --cached --check`: PASS.
- [x] 4.4 Disposable archive-applicability check: FAIL because root `cloudlink-live-microphone-metering` still mandated Box LIVE.
- [x] 4.5 Independent architecture review of `01faf3...`: `CHANGES REQUIRED` (1 HIGH, 1 MEDIUM).
- [x] 4.6 Resolve the HIGH/MEDIUM findings in OpenSpec only; no production implementation.

Required re-validation on the new exact published SHA:

- [x] 4.7 Re-read all current root specs affected by this change and confirm no competing capability/presentation/lifecycle contract remains, including the state-card uptime replacement, root CloudLink meter Box deferral, Box call-log no-LIVE semantics, and TE40 fresh full-state mutation safety.
- [x] 4.8 Run `.\openspec.cmd validate codec-interaction-parity-restoration --strict` for the current OpenSpec-only architecture remediation.
- [x] 4.9 Run `.\openspec.cmd validate --all --strict` for the current OpenSpec-only architecture remediation.
- [x] 4.10 Run a disposable archive-applicability check for all `MODIFIED Requirements`; verify every replaced root requirement/scenario is archive-compatible without publishing archive output.
- [x] 4.11 Run Git hygiene checks (`git diff --check`, `git diff --cached --check`) and confirm only in-scope OpenSpec artifacts are modified before the resulting commit.
- [x] 4.12 Independent reviewer completed the historical architecture review of exact SHA `11af77b14010c34ae2d33de816678a6724971caa`: `APPROVE` (`CRITICAL 0 / HIGH 0 / MEDIUM 0`). The post-approval hardware amendment requires the new review in 9.13.
- [x] 4.13 Resolve the current Critical/High/Medium findings without production implementation: add the archive-compatible state-card uptime replacement and classify TE40 static status as an ADDED requirement.
- [x] 4.14 Record historical final independent architecture `APPROVE` for exact content SHA `11af77b14010c34ae2d33de816678a6724971caa` (`CRITICAL 0 / HIGH 0 / MEDIUM 0`). This bookkeeping descendant does not change that historical architecture-approved SHA; the post-approval hardware amendment requires the new review in 9.13.

## 5. Post-approval exact-model capability and parser implementation

- [x] 5.1 Make `diagnostic_dispatch`/unified exact-model registration conform to final approved matrix; preserve RPG310 speaker step `2`; TE40 `microphone_adjust` supported only through MIC1 binding.
- [x] 5.2 TE40: normalize present numeric static `mic1Value` primary gain to canonical `microphone_volume`; use historical `micValue` only as a compatibility fallback when MIC1 is absent; preserve independent mute evidence as `microphone_muted`.
- [x] 5.3 TE40: implement MIC1 gain mutation with mandatory fresh full-state pre-read after lane ownership/LIVE retirement; build save payload only from that fresh state; change only target `mic1Value`; send once via `WEB_SaveAudioMicCtrlParams`.
- [x] 5.4 TE40: post-write full-state reconciliation must confirm target plus preserved non-target `micall`/`micN`/`micNValue`; insufficient/collateral mismatch -> blocked/unconfirmed, no replay.
- [x] 5.5 TE40: preserve microphone mute as a separate supported desired-state/readback operation.
- [x] 5.6 TE40 camera: process `itemList` as zero-to-many; cover exactly-one-camera shape.
- [x] 5.7 Box 310: remove/disable all live-microphone capability surfaces for this change: no unified-registration LIVE binding, no Box meter polling context, no LIVE `WEB_GetCurrentAudioParam`, no legacy codec-page meter row, and the modern room microphone LIVE slot is unsupported. Do not implement a replacement Box parser.
- [x] 5.8 Bar 310: preserve approved current-volume LIVE endpoint/session/parser/polling behavior and do not let Box deferral regress Bar.
- [x] 5.9 Keep CloudLink microphone gain and all-five reboot unsupported/local-only with zero network I/O.
- [x] 5.10 Preserve TE20/RPG310 microphone-mute semantics and no fabricated numeric gain.

## 6. Post-approval presentation and LIVE implementation

- [x] 6.1 Render Audio card in exact order: `Микрофон (уровень)`, `Громкость микрофона`, `Громкость динамиков`; no user-visible speaker LIVE meter.
- [x] 6.2 Implement the then-approved TE20/TE40 `MicValueIndex` normalization and seed precedence for `Микрофон (уровень)`; `SpeakerValueIndex` remains compatibility/internal evidence and creates no user-visible speaker LIVE meter. The TE40 MicValueIndex-only authority is superseded by post-approval hardware evidence tracked in 9.13-9.18.
- [x] 6.3 Remove redundant textual Huawei live-audio rows; the Audio card has no user-visible speaker LIVE row.
- [x] 6.4 TE40: display configured MIC1 gain from canonical `microphone_volume`, originating from authoritative `mic1Value`, via `gain_db = mic1Value - 12`; make `-`/`+` request exactly one dB through typed application intent.
- [x] 6.5 Bar310: preserve approved microphone LIVE meter; room presentation has no user-visible speaker LIVE capability.
- [x] 6.6 Box310: `Микрофон (уровень)` is unsupported/deferred; there is no Box LIVE binding, polling, or room LIVE `WEB_GetCurrentAudioParam`, and room presentation has no user-visible speaker LIVE capability. Legacy codec-page live microphone row is hidden; no historical/stale Box meter data is rendered as current.
- [x] 6.7 RPG310: microphone LIVE is unsupported; the room Audio card retains its single microphone LIVE slot plus configured control rows.
- [x] 6.8 Update repository-local visual acceptance tests/checkpoints for the Huawei single microphone LIVE meter contract, TE40 configured MIC1 dB value, Bar LIVE preservation, Box deferred microphone LIVE state, and absence of a user-visible speaker LIVE meter.

## 7. Initial three-call preview and explicit journal

- [x] 7.1 After the **entire** automatic room cycle is terminal, admit automatic call preview only for the exact current expanded connected/usable call-log-capable codec row.
- [x] 7.2 For that exact row/generation, perform one fresh serialized call-history acquisition; if the exact registration advertises LIVE, first LIVE waits for preview terminal cleanup. If it advertises no LIVE, cleanup releases the lane with no LIVE start.
- [x] 7.3 If no codec row is expanded at whole-room terminal time, perform zero hidden preview I/O until an eligible row is later expanded.
- [x] 7.4 After a row/generation automatic attempt is terminal, collapse/re-expand, repaint, resize, theme switch and duplicate Qt events cause zero additional automatic call-log I/O.
- [x] 7.5 Row switch may admit the newly current codec's own first generation-bound preview after prior lifecycle cleanup; stale old callbacks remain powerless.
- [x] 7.6 Ordinary preview failure/no-data reaches bounded cleanup and does not permanently degrade a connected row; first LIVE may start afterward only when exact registration advertises LIVE.
- [x] 7.7 Every explicit `Развернуть` remains a separate fresh call-log acquisition; active LIVE retires/resumes only where that exact model actually has LIVE. Box has zero LIVE retirement/resume in this change.
- [x] 7.8 Add end-to-end call-log regressions for TE20, TE40, Bar310, Box310 and RPG310 proving up-to-three automatic rows and fresh explicit detail.
- [x] 7.9 Box regression specifically proves: one preview, no Box LIVE context/request before or after cleanup, and later explicit detail remains fresh.

## 8. Existing speaker/control safety regression

- [x] 8.1 Preserve speaker ranges/steps: TE20/TE40 `0..21/1`, Bar/Box `0..15/1`, RPG310 `0..100/2`.
- [x] 8.2 Preserve speaker zero/restore mute using only proven exact-row/generation positive restore evidence.
- [x] 8.3 Preserve no-restore unmute at `0` as local unavailable with zero mutation/handler/device I/O.
- [x] 8.4 Preserve root blocked/unconfirmed safety after possible send + failed/ambiguous readback; apply to TE40 MIC1 target or collateral mismatch.
- [x] 8.5 Preserve definite pre-submit semantics: TE40 fresh pre-read failure before save does not create `unconfirmed_after_command` solely from no-send.
- [x] 8.6 Preserve Local Refresh, cancellation, cleanup timeout, stale-callback and no-indefinite-lock behavior after amended lifecycles.

## 9. Post-amendment implementation validation

- [x] 9.1 Run focused parser/codec-control/live/call-log/camera/lifecycle tests.
- [x] 9.2 Run the full offline unittest suite.
- [x] 9.3 Run `.\openspec.cmd validate codec-interaction-parity-restoration --strict`.
- [x] 9.4 Run `.\openspec.cmd validate --all --strict`.
- [x] 9.5 Run `git diff --check` and `git diff --cached --check`.
- [x] 9.6 Synchronize implementation evidence/tasks without treating synthetic tests as hardware acceptance.
- [x] 9.7 Create and push focused implementation commit(s). Implementation session MUST NOT issue the independent final verdict.
- [x] 9.8 Remediate automatic-preview terminal typed connection/session/authentication failure so exact-row degradation occurs before bounded preview cleanup and blocks first LIVE; retain non-degrading ordinary-preview failure semantics.
- [x] 9.9 Remediate TE40 mutation completion classification so the possible-send boundary controls unconfirmed state for pre-submit typed and ordinary failures, while post-send cancellation, timeout, and failed readback remain fail-closed; add composition regressions.
- [x] 9.10 Amend room codec presentation/lifecycle contracts: remove speaker LIVE, normalize Huawei monitor audio from `0..220`, seed microphone meter from initial evidence, preserve TE40 canonical state/uptime, and release preview ownership after already-completed physical cleanup.
- [x] 9.11 Add remediation regressions for TE40 canonical MIC1 gain/status/uptime, microphone meter normalization and seed precedence, absent speaker LIVE meter, and preview cleanup handoff.
- [x] 9.12 Remediate review findings: persist successful preview credential/profile before first LIVE, establish MIC1-primary wording, and remove stale speaker-LIVE contract text.

## 9A. Post-approval hardware-discovered remediation

- [x] 9.13 Obtain independent architecture review of the OpenSpec amendment for session-bound initial expansion preview admission and TE40 monitor-audio `micArray<N>_<NN>ValIdx` aggregation. Exact SHA `5b21dbe081e04c6e12f5c9448c34db9e4263d197`: APPROVE WITH NON-BLOCKING NOTES (`CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 1`).
- [x] 9.14 Implement coordinator adoption of a generation-current session `expanded_record_id` at bind without bind/render I/O; preserve the one terminal-cycle automatic preview and preview-before-LIVE ordering.
- [x] 9.15 Implement one TE40 monitor-audio extractor for one-shot seed and true LIVE: maximum valid `MicValueIndex`/`micArray<N>_<NN>ValIdx` candidates, unavailable-versus-zero semantics, and existing `0..220 -> 0..100%` normalization.
- [x] 9.16 Add regression coverage for initial-expanded preview admission without synthetic Qt events and the TE40 primary/array aggregation, malformed/absent/zero/speaker-isolation, and seed-versus-true-LIVE boundaries.
- [x] 9.17 Re-run focused/full offline validation and strict OpenSpec checks after implementation; do not treat them as hardware evidence.
- [x] 9.18 Attempt exact-SHA Huawei TE40 hardware acceptance for automatic preview after ordinary `Обновить данные` and microphone LIVE array telemetry after implementation. At `01226c6620932db01424a06211ba7292c6efc164`, TE40 microphone LIVE **FAILED**: browser-proven dynamic audio uses `WEB_GetCurrentAudioParam` with decoded `mic<N>ValueIndex` and `micArray<N>_<NN>ValIdx` evidence, while the implementation uses `WEB_GetMonitorAudioParam`; remediation and a new exact-SHA hardware rerun are required. This is failure evidence, not hardware acceptance PASS.

## 9B. Hardware-corrected TE40 current-audio architecture (pending independent review)

- [x] 9.19 Obtain independent architecture review of the OpenSpec amendment that makes `WEB_GetCurrentAudioParam` the sole TE40 initial-seed/true-LIVE microphone authority and adds exact `mic<N>ValueIndex` aggregation. Exact SHA `23347fa1febb70cd1395041f0b02928b95d1eb56`: APPROVE WITH NON-BLOCKING NOTES (`CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 1`).
- [x] 9.20 Implement the reviewed TE40 current-audio endpoint/extractor correction with one seed/LIVE path, then add focused regressions and rerun required validation.
- [x] 9.21 Repeat exact-SHA TE40 microphone LIVE hardware acceptance after the reviewed implementation. At exact SHA `43fa6ca247898ff661e6e2fbcc4850c561512a2f`, current-audio LIVE PASSed on real TE40 hardware. This is TE40 current-audio evidence only, not whole-change hardware completion; later production changes require a new exact-SHA TE40 quick rerun.

## 9C. TE50 declared protocol-equivalence expansion (pending independent architecture review)

- [ ] 9.22 Amend OpenSpec for exact-model TE50 reuse and obtain independent architecture review of the published amendment SHA.
- [ ] 9.23 After permitting review, register exact `Huawei TE50` identity and reviewed TE40 handler reuse without family inference.
- [ ] 9.24 Add focused TE50 reuse regressions while preserving TE30/TE60 exclusion and all existing safety/lifecycle regressions.
- [ ] 9.25 After TE50 implementation, repeat a quick exact-SHA TE40 hardware check for current-audio LIVE and affected shared behavior.
- [ ] 9.26 Run exact-SHA TE50 hardware acceptance when TE50 hardware is available; do not mark PASS before real-device evidence.

## 10. Exact-SHA hardware acceptance

Current six-model scope is TE20, TE40, TE50, Bar310, Box310 and RPG310. TE50 remains pending exact-SHA hardware acceptance; physical availability at any one moment does not count as acceptance evidence.

- [ ] 10.1 Run every applicable six-model in-scope hardware scenario, including TE50's applicable exact-SHA hardware acceptance, against the exact published post-amendment implementation SHA.
- [ ] 10.2 TE40: verify static numeric MIC1 gain/dB display, MIC1 gain exact `1 dB` step, fresh pre-write state acquisition, independent mute, microphone LIVE meter, exactly-one-camera behavior, automatic three-call preview, explicit fresh journal, speaker controls and Local Refresh.
- [ ] 10.3 TE40 mutation safety: where feasible, verify non-target microphone state is preserved; target/collateral reconciliation failure must not yield confirmed success or blind replay.
- [ ] 10.4 Box310: verify deferred LIVE contract — no live binding/polling/request and microphone LIVE meter unsupported; separately verify automatic three-call preview, explicit fresh journal, speaker controls and Local Refresh.
- [ ] 10.5 TE20/Bar310/RPG310: rerun all applicable original hardware gates plus new automatic three-call lifecycle and Audio-card expectations.
- [ ] 10.6 Record exact SHA, model, action, non-secret method/path, raw outcome category, normalized result, GUI result and UI-unlocked status for every scenario.
- [ ] 10.7 Missing/failed required hardware evidence is blocking `CHANGES REQUIRED` regardless of offline test count.

## 11. Independent validation

- [ ] 11.1 Validate the exact published remote implementation SHA from a clean detached worktree.
- [ ] 11.2 Re-run focused/full tests, strict OpenSpec validation, Git checks and required disposable archive-applicability check.
- [ ] 11.3 Review implementation against the **new approved architecture SHA**, root MODIFIED contracts including `cloudlink-live-microphone-metering`, exact-row call-preview boundary, TE40 fresh full-state MIC1 contract, Box deferred LIVE contract, root mutation safety and behavioral oracle.
- [ ] 11.4 Confirm all six models passed every applicable hardware gate on the exact validated implementation SHA, including TE50's mandatory applicable exact-SHA hardware acceptance. Independent validation and archive are prohibited if that TE50 acceptance is missing or failed.
- [ ] 11.5 Issue only `APPROVE`, `APPROVE WITH NON-BLOCKING NOTES`, or `CHANGES REQUIRED` according to repository rules.

## 12. Archive + completion

- [ ] 12.1 Archive only after a permitting independent verdict that includes mandatory hardware acceptance.
- [ ] 12.2 Review root-spec/archive diff for duplicate or contradictory capability, Audio-card, CloudLink meter, call-preview, TE40 gain/full-state safety, Box deferred LIVE, restore-authority or currentness contracts.
- [ ] 12.3 Run strict all-artifact validation, full offline tests and Git checks after archive.
- [ ] 12.4 Create/push dedicated archive commit.
- [ ] 12.5 Merge only with explicit user authorization.

## Deferred follow-up (not a completion gate for this change)

A separate reviewed change is required to restore `CloudLink Box 310` microphone LIVE when hardware is available. It must prove the complete Box response envelope, microphone device-role selection, numeric validity, aggregation, normalization and unavailable/error semantics before re-advertising a Box LIVE binding.
