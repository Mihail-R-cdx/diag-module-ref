# Tasks: IN1808 audio routing meters

## 1. Architecture

- [x] 1.1 Re-read current `RULES.md`, current `master`, current Matrix/DMP
  source boundaries, and archived approved Matrix/Audio DSP architecture.
- [x] 1.2 Record the available real-hardware IN1808 evidence for `ANAM`,
  `V<OID>AU`, meter state 0/1 behavior, representative 300xx/400xx/600xx
  domains, and the bounded 200xx mix-point address space.
- [x] 1.3 Select Variant B: one IN1808 Audio/Video mode control, unchanged
  General information, and replacement of only the right tile.
- [x] 1.4 Keep audio routing read-only and keep existing IN1808 video routing
  authority unchanged.
- [x] 1.5 Define one Matrix-owned audio live subcontext; no second controller,
  transport session, credential lane, or GUI-thread I/O.
- [x] 1.6 Separate hardware-proven facts from the adopted
  `IN1808_PRODSP_PROFILE_MAPPING`; do not claim runtime can detect a valid but
  semantically permuted 200xx map.
- [x] 1.7 Make documented read-only `1$` mandatory Audio metadata so physical
  DP/HDMI/TP/Aux input 1..9 is linked to `Program L/R`.
- [x] 1.8 Resolve unknown meter-update ownership scope by forbidding production
  cleanup `*0` until authoritative scope evidence exists.
- [x] 1.9 Bind Audio polling to existing `RoomInteractionKind.LIVE` and retain
  bounded cleanup gates before Local Refresh, video mutation, and reconciliation.
- [x] 1.10 Run repository-local
  `.\openspec.cmd validate in1808-audio-routing-meters --strict`,
  `.\openspec.cmd validate --all --strict`, and `git diff --check` on the
  exact published architecture HEAD.
- [x] 1.11 Perform independent architecture review and obtain `APPROVE` before
  production implementation.

## 2. Protocol/domain implementation

- [x] 2.1 Add an exact IN1808 audio profile without changing other Matrix
  profiles or DMP wire semantics.
- [x] 2.2 Preserve exact accepted IN1808 `1I` wire identity as variant evidence
  while keeping canonical application model `Extron IN1808`.
- [x] 2.3 Implement audio-name reads for the approved input/output IDs with
  deterministic fallback labels.
- [x] 2.4 Implement the approved 300xx/400xx/600xx meter topology and retain raw
  component evidence.
- [x] 2.5 Implement stereo meter aggregation as max available dBFS while
  preserving partial-component outcomes.
- [x] 2.6 Implement IN1808 meter update lifecycle with initial-state read,
  `*1` activation when needed, no `*2`, no production cleanup `*0`, and
  no blind replay after ambiguous instrumentation send.
- [x] 2.7 Implement mandatory read-only `1$` current Program-source metadata
  with 1..9/UNKNOWN normalization independent from video `1%`.
- [x] 2.8 Implement read-only 200xx mix-point snapshot parsing with the bounded
  address formula, adopted `IN1808_PRODSP_PROFILE_MAPPING`, variant output
  filtering, and 0/1/UNKNOWN protocol semantics.
- [x] 2.9 Do not add any audio-route, gain, mute, volume, or DSP mutation API.

## 3. Application/lifecycle implementation

- [x] 3.1 Publish exact IN1808 audio capability through unified application
  registration/composition rather than a widget/model-substring allowlist.
- [x] 3.2 Extend existing Matrix owner/session serialization with an IN1808
  audio subcontext; do not create a parallel persistent session.
- [x] 3.3 Schedule audio metadata/routing acquisition once on Audio entry and
  meter polling approximately once per second without overlapping cycles.
- [x] 3.4 Stop/quiesce the Audio subcontext on Video toggle, collapse, another
  expanded row, room/search/context replacement, credential revision,
  invalidation, and shutdown; cleanup sends no `*0` under current evidence.
- [x] 3.5 Bind Audio to existing LIVE authority and preserve bounded retirement
  gates before Local Refresh/video mutation plus reconciliation exclusivity.
- [x] 3.6 Reject stale audio work before acquisition/I/O where possible and
  before accepted GUI update in all cases.
- [x] 3.7 Keep application-owned credential selection/fallback authority and
  prohibit handler/worker credential iteration.

## 4. Room GUI implementation

- [x] 4.1 Add the exact-IN1808 row-header `Аудио` control; in Audio mode the
  same control reads `Видео`.
- [x] 4.2 Preserve the left `Общая информация` card field semantics and swap
  only the right tile.
- [x] 4.3 Render the all-source meter band and output meters using the modern
  segmented DMP visual language.
- [x] 4.4 Render current Program source from `1$`, including explicit UNKNOWN.
- [x] 4.5 Render the DSP routing grid read-only with channel-accurate L/R axes,
  ACTIVE/INACTIVE/UNKNOWN non-color semantics, and safe profile-mapping basis metadata.
- [x] 4.6 Keep stereo meters combined without collapsing L/R route evidence.
- [x] 4.7 Keep Video network actions locked until Audio subcontext cleanup
  reaches its permitted boundary.
- [x] 4.8 Isolate Audio no-data/error presentation from accepted Matrix row,
  General-information, and video-routing state.
- [x] 4.9 Leave standalone `MatrixScreen`, `AudioDSPScreen`, and
  `DMPPollingController` ownership unchanged.

## 5. Regression coverage

- [x] 5.1 Cover exact capability gating: IN1808 gets Audio mode; IN1804,
  IN1806, IN1608 xi and DTP models do not.
- [x] 5.2 Cover accepted IN1808 wire variants and amplifier capability filtering.
- [x] 5.3 Cover ANAM parsing/fallback and stable IDs.
- [x] 5.4 Cover meter command generation, state transitions, raw parsing,
  derived dBFS, stereo aggregation and partial evidence.
- [x] 5.5 Prove no IN1808 path sends DMP `*2` and no cleanup path sends
  `*0` under the unknown-scope contract.
- [x] 5.6 Cover mandatory `1$` Program-source mapping 1..9 and UNKNOWN
  independently from video `1%`.
- [x] 5.7 Cover 200xx boundaries/formula, adopted mapping-basis metadata, and
  prove no state-changing mix-point command is generated.
- [x] 5.8 Cover one routing snapshot per Audio entry and non-overlapping live
  meter cycles.
- [x] 5.9 Cover Audio -> Video cleanup lock, Local Refresh/mutation retirement
  gates, reconciliation exclusion, and cleanup-timeout fail-closed behavior.
- [x] 5.10 Cover mode-toggle/collapse/context replacement cleanup and stale
  callback rejection.
- [x] 5.11 Cover Audio-only failure isolation.
- [x] 5.12 Re-run existing Matrix video route/read/mutation regressions and DMP
  meter regressions to prove protocol separation.

## 6. Implementation validation

- [x] 6.1 Run focused IN1808 audio/domain/controller/room GUI tests.
- [x] 6.2 Run the full required offline Python suite.
- [x] 6.3 Run
  `.\openspec.cmd validate in1808-audio-routing-meters --strict`.
- [x] 6.4 Run `.\openspec.cmd validate --all --strict`.
- [x] 6.5 Run `git diff --check` and `git diff --cached --check`.
- [x] 6.6 Create and push one focused implementation commit after architecture
  approval; the implementation session must not issue its own final
  independent `APPROVE`.
- [x] 6.7 Correct independent-review findings: batch production Audio reads on
  the existing Matrix session, preserve literal `1$`, and retry a temporarily
  busy serialized Audio entry/meter request without overlap or backlog.
- [x] 6.8 Re-run focused and full offline tests, strict change/all OpenSpec
  validation, and Git whitespace validation after the review corrections.

## 7. Hardware-QA GUI refinement

- [x] 7.1 Record hardware QA finding that the first `Аудио` click can appear
  to do nothing while background acquisition/controller availability is pending.
- [x] 7.2 Replace the free-standing meter bands with one shared logical grid:
  horizontal input meters aligned to routing rows and vertical output meters
  aligned to routing columns, with an empty top-left spacer.
- [x] 7.3 Define presentation-only L/R grouping while retaining the raw
  channel-accurate 8 x 12 routing evidence; grouped routes use topology-aware
  stereo->stereo, stereo->mono, mono->stereo and mono->mono
  FULL/INACTIVE/MIXED/UNKNOWN semantics, with normal diagonal stereo routing
  classified as FULL.
- [x] 7.4 Define Program L/R meter binding to the physical DP/HDMI/TP/Aux source
  selected by mandatory `1$`.
- [x] 7.5 Remove duplicate meter labels plus visible
  `ACTIVE`/`INACTIVE`/`MIXED`/`VALID`/`INVALID` text; retain compact
  `●`/`○`/`◐`/`—` markers and numeric dBFS.
- [x] 7.6 Separate stable semantic row/column identity from accepted ANAM:
  structural labels stay fixed, while device names are deterministic secondary
  tooltip/accessibility metadata, including stereo and Program-source rules.
- [x] 7.7 Correct the proposal to state horizontal logical-input meters and
  vertical logical-output meters.
- [x] 7.8 Mark the previous implementation report as superseded by the
  hardware-QA GUI-refinement architecture without rewriting its old evidence.
- [x] 7.9 Run repository-local
  `.\openspec.cmd validate in1808-audio-routing-meters --strict`,
  `.\openspec.cmd validate --all --strict`, and `git diff --check` on the
  published GUI-refinement architecture HEAD.
- [x] 7.10 Perform architecture review of the GUI refinement and obtain
  `APPROVE` before changing production GUI/tests.
- [x] 7.11 Implement immediate first-click Audio layout rendering before I/O and
  keep it visible through temporary controller-busy retry.
- [x] 7.12 Implement the six logical input rows and exact variant-filtered
  seven/eight logical output columns using the approved fail-safe grouping
  semantics.
- [x] 7.13 Implement shared row/column geometry so meter centerlines and routing
  row/column centerlines are exactly aligned; compact row height and allow
  narrower meters as needed.
- [x] 7.14 Implement Program L/R meter projection from the `1$`-selected
  physical source while keeping all normalized raw meter evidence unchanged.
- [x] 7.15 Implement stable primary semantic labels plus deterministic ANAM
  tooltip/accessibility metadata without changing grid geometry.
- [x] 7.16 Add GUI/lifecycle regression coverage for immediate switching,
  topology-aware stereo->stereo/stereo->mono/mono->stereo/mono->mono
  FULL/INACTIVE/MIXED/UNKNOWN grouping (including normal diagonal stereo FULL,
  crossed/partial MIXED and UNKNOWN fail-safe), exact alignment/sizing ownership,
  naming authority, no duplicate labels/status words, Program-source meter
  projection, and variant Amplifier presence/absence.
- [x] 7.17 Re-run focused/full offline tests, strict change/all OpenSpec
  validation, `git diff --check`, and `git diff --cached --check`.
- [x] 7.18 Create and push one focused GUI-refinement implementation commit; the
  implementation session must not issue its own independent `APPROVE`.
- [x] 7.19 Record hardware-QA follow-up that the horizontal logical input meter
  reuses legacy vertical-track QSS and can render the 20-segment scale clipped
  while the dBFS number remains visible.
- [x] 7.20 Define bounded local acknowledgement for an accepted `Аудио` click:
  disable the same mode control until the complete Audio layout is committed,
  never wait for network/device completion, and enforce a currentness-safe
  10-second fail-safe maximum.
- [ ] 7.21 Re-run repository-local strict change/all validation and Git
  whitespace checks on the published acknowledgement amendment, then obtain
  architecture review `APPROVE` before production remediation.
- [ ] 7.22 Fix IN1808 orientation-specific meter-track sizing so horizontal
  input and vertical output 20-segment scales are visibly compatible with the
  shared-grid geometry; add geometry regression coverage that can catch legacy
  vertical-QSS clipping.
- [ ] 7.23 Implement the bounded Audio-toggle disabled state and stale-safe
  10-second fail-safe, with regression coverage proving re-enable on committed
  layout and no dependency on controller/device completion.
- [ ] 7.24 Re-run focused/full offline tests, strict change/all OpenSpec
  validation, Git checks, then create and push one focused remediation commit.
- [ ] 7.25 Repeat hardware QA on the final published remediation HEAD before
  independent validation; record any new blocking UX/protocol finding before
  proceeding.

## 8. Independent validation and completion

- [ ] 8.1 Validate the exact current published feature HEAD in a separate clean
  detached worktree from `origin/<branch>`; verify local/remote SHA equality.
- [ ] 8.2 Re-run focused tests, full offline tests, strict change/all OpenSpec
  validation, Git checks, and implementation-vs-approved-architecture review.
- [ ] 8.3 Do not fix findings in the independent validation session.
- [ ] 8.4 Perform the mandatory disposable archive-applicability check in the
  clean detached validation worktree before `READY FOR ARCHIVE` because this
  change adds requirements to existing root specs. Concurrent root-spec changes
  require the check to be repeated/reconciled against the then-current base.
- [ ] 8.5 Archive only after a permitting independent verdict; then run
  post-archive strict-all, full offline tests, Git checks, archive/root-spec
  diff review, and a dedicated archive commit/push.
- [ ] 8.6 Merge only after current remote archive HEAD/master are rechecked and
  the user explicitly authorizes merge.
