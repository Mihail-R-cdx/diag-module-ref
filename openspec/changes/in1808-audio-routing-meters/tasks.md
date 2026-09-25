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
- [x] 1.6 Separate hardware-proven facts from adopted Extron ProDSP
  family-convention mappings and require fail-closed runtime handling for
  contradictions.
- [ ] 1.7 Run repository-local
  `.\openspec.cmd validate in1808-audio-routing-meters --strict`,
  `.\openspec.cmd validate --all --strict`, and `git diff --check` on the
  exact published architecture HEAD.
- [ ] 1.8 Perform independent architecture review and obtain `APPROVE` before
  production implementation.

## 2. Protocol/domain implementation

- [ ] 2.1 Add an exact IN1808 audio profile without changing other Matrix
  profiles or DMP wire semantics.
- [ ] 2.2 Preserve exact accepted IN1808 `1I` wire identity as variant evidence
  while keeping canonical application model `Extron IN1808`.
- [ ] 2.3 Implement audio-name reads for the approved input/output IDs with
  deterministic fallback labels.
- [ ] 2.4 Implement the approved 300xx/400xx/600xx meter topology and retain raw
  component evidence.
- [ ] 2.5 Implement stereo meter aggregation as max available dBFS while
  preserving partial-component outcomes.
- [ ] 2.6 Implement IN1808 meter update lifecycle with `*1` enable,
  `*0` restore, no `*2`, initial-state capture, and no blind replay after
  ambiguous instrumentation send.
- [ ] 2.7 Implement read-only 200xx mix-point snapshot parsing with the approved
  address formula, variant output filtering, and 0/1/UNKNOWN semantics.
- [ ] 2.8 Do not add any audio-route, gain, mute, volume, or DSP mutation API.

## 3. Application/lifecycle implementation

- [ ] 3.1 Publish exact IN1808 audio capability through unified application
  registration/composition rather than a widget/model-substring allowlist.
- [ ] 3.2 Extend existing Matrix owner/session serialization with an IN1808
  audio subcontext; do not create a parallel persistent session.
- [ ] 3.3 Schedule audio metadata/routing acquisition once on Audio entry and
  meter polling approximately once per second without overlapping cycles.
- [ ] 3.4 Stop/restore the audio subcontext on Video toggle, collapse, another
  expanded row, room/search/context replacement, credential revision,
  invalidation, and shutdown.
- [ ] 3.5 Reject stale audio work before acquisition/I/O where possible and
  before accepted GUI update in all cases.
- [ ] 3.6 Keep application-owned credential selection/fallback authority and
  prohibit handler/worker credential iteration.

## 4. Room GUI implementation

- [ ] 4.1 Add the exact-IN1808 row-header `Аудио` control; in Audio mode the
  same control reads `Видео`.
- [ ] 4.2 Preserve the left `Общая информация` card field semantics and swap
  only the right tile.
- [ ] 4.3 Render the all-source meter band and output meters using the modern
  segmented DMP visual language.
- [ ] 4.4 Render the DSP routing grid read-only with channel-accurate L/R axes
  and ACTIVE/INACTIVE/UNKNOWN non-color semantics.
- [ ] 4.5 Keep stereo meters combined without collapsing L/R route evidence.
- [ ] 4.6 Isolate Audio no-data/error presentation from accepted Matrix row,
  General-information, and video-routing state.
- [ ] 4.7 Leave standalone `MatrixScreen`, `AudioDSPScreen`, and
  `DMPPollingController` ownership unchanged.

## 5. Regression coverage

- [ ] 5.1 Cover exact capability gating: IN1808 gets Audio mode; IN1804,
  IN1806, IN1608 xi and DTP models do not.
- [ ] 5.2 Cover accepted IN1808 wire variants and amplifier capability filtering.
- [ ] 5.3 Cover ANAM parsing/fallback and stable IDs.
- [ ] 5.4 Cover meter command generation, state transitions, raw parsing,
  derived dBFS, stereo aggregation and partial evidence.
- [ ] 5.5 Prove no IN1808 path sends the DMP `*2` meter enable command.
- [ ] 5.6 Cover 200xx boundaries/formula and prove no state-changing mix-point
  command is generated.
- [ ] 5.7 Cover one routing snapshot per Audio entry and non-overlapping live
  meter cycles.
- [ ] 5.8 Cover mode-toggle/collapse/context replacement cleanup and stale
  callback rejection.
- [ ] 5.9 Cover Audio-only failure isolation.
- [ ] 5.10 Re-run existing Matrix video route/read/mutation regressions and DMP
  meter regressions to prove protocol separation.

## 6. Implementation validation

- [ ] 6.1 Run focused IN1808 audio/domain/controller/room GUI tests.
- [ ] 6.2 Run the full required offline Python suite.
- [ ] 6.3 Run
  `.\openspec.cmd validate in1808-audio-routing-meters --strict`.
- [ ] 6.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 6.5 Run `git diff --check` and `git diff --cached --check`.
- [ ] 6.6 Create and push one focused implementation commit after architecture
  approval; the implementation session must not issue its own final
  independent `APPROVE`.

## 7. Independent validation and completion

- [ ] 7.1 Validate the exact current published feature HEAD in a separate clean
  detached worktree from `origin/<branch>`; verify local/remote SHA equality.
- [ ] 7.2 Re-run focused tests, full offline tests, strict change/all OpenSpec
  validation, Git checks, and implementation-vs-approved-architecture review.
- [ ] 7.3 Do not fix findings in the independent validation session.
- [ ] 7.4 If root-spec applicability is affected by concurrent changes, perform
  a disposable archive-applicability check before `READY FOR ARCHIVE`.
- [ ] 7.5 Archive only after a permitting independent verdict; then run
  post-archive strict-all, full offline tests, Git checks, archive/root-spec
  diff review, and a dedicated archive commit/push.
- [ ] 7.6 Merge only after current remote archive HEAD/master are rechecked and
  the user explicitly authorizes merge.
