> **CURRENT HARDWARE EVIDENCE / BOUNDED GUARDED-BATCH ARCHITECTURE**
> The third exact-IN1808 hardware probe completed the 31-command guarded batch
> in **1.328 s** with `success=True`, `raw_length=490`, and 31 observed
> chunks: one aggregate command echo plus exactly 30 useful Video payloads.
> The sacrificial in-batch `1I` payload was omitted; `Q` through `1%`
> were all present in expected order; the post-batch standalone `1I` again
> returned `IN1808 IPCP SA`. Together with the two earlier probes, this closes
> the guard-shape hardware question.
>
> Architecture now uses a bounded correlation contract rather than claiming an
> unprovable universal isolation guarantee for untagged SIS payloads. Production
> is constrained to one serialized Matrix owner operation, the exact aggregate
> echo + 30 useful payload shape, command-specific parsers, and matching
> standalone pre/post exact identity gates. Detectable ambiguity fails closed.
> The residual possibility of an indistinguishable same-grammar
> delayed/unsolicited/duplicated/stale substitution is explicitly accepted only
> for this read-only diagnostic snapshot and grants no mutation authority.
> Production implementation remains blocked until the resulting published
> architecture HEAD receives fresh repository-local strict validation and
> architecture `APPROVE`.
>
> **SUPERSEDED ARCHITECTURE REVIEW REMEDIATION — BATCH FRAMING GATE**
> Architecture review found that payload count plus positional parsing cannot
> prove command-to-payload ownership for untagged batch responses: a missing
> required payload plus a compensating unrelated/delayed/duplicated frame can
> preserve the expected count. It also found that the exact in-batch-`1I` guard
> shape had been made normative before task 7.36e tested it. Current OpenSpec
> therefore demotes that guard shape to an evidence candidate and blocks
> production batching until two gates pass: (A) exact guard-shape hardware
> behavior, and (B) transaction-isolation/correlation authority excluding
> unrelated/unsolicited/delayed/duplicated/stale frames from being accepted as
> required payloads. The exact production wire/framing rule must be written back
> into OpenSpec and freshly validated before implementation. The separate
> no-duplicate-`matrix_room_live`/Video->Audio refresh contract remains
> normative and unchanged.
>
> **SUPERSEDED HISTORICAL DRAFT — DO NOT USE AS CURRENT BATCH AUTHORITY**
> The current OpenSpec now fixes both requested behaviors without changing
> production code yet. First, a legitimate exact-IN1808 full Video refresh uses
> one standalone authoritative `1I`, then a guarded batch whose first command
> is sacrificial read-only `1I` followed by the 30 required Video status reads.
> The parser accepts only 30 status payloads when the guard payload is omitted,
> or 31 payloads when the first one independently matches the same exact IN1808
> identity; all other framing fails closed. Second, an already accepted
> `matrix_one_shot` Video snapshot is reused by `matrix_room_live` and by
> Video -> Audio entry: neither path may schedule another full Video refresh.
> A fresh lazy LIVE transport may perform only standalone `1I` before Audio
> I/O. Task 7.36e remains the final hardware confirmation of the selected guard
> shape before architecture validation/implementation; it is no longer an
> unresolved architecture choice.
>
> **SECOND REAL VIDEO-BATCH PROBE RESULT / FIRST-QUERY LOSS CONFIRMED**
> On the same exact `IN1808 IPCP SA`, standalone `Q` correctly returned
> firmware `1.09`. The following 29-query batch completed in **0.906 s** with
> `success=True` and `raw_length=459`, but again produced one aggregate echo
> block plus only **28** payloads: this time the leading `w20STAT` temperature
> payload was absent, while `wE1HDCP` through `1%` remained in the expected
> order. A post-batch standalone `1I` again returned `IN1808 IPCP SA`.
> Combined with the first probe (where leading `Q` alone was missing), the
> hardware evidence now shows a first-in-batch payload loss independent of query
> family. The next probe therefore prepends a sacrificial read-only `1I`
> framing guard and places all 30 required Video status queries after it.
>
> **FIRST REAL VIDEO-BATCH PROBE RESULT**
> Real exact-IN1808 hardware (`IN1808 IPCP SA`) completed the original
> 30-query mixed Video batch in **0.907 s** with `success=True` and
> `raw_length=469`. The response contained one aggregate echo block followed
> by **29** payload chunks, not 30: the standalone baseline firmware value from
> `Q` was absent, while payloads from `w20STAT` through `1%` remained in
> expected order (temperature 52, HDCP fields, eight input names, output name,
> signal bitmap, route 1). A following standalone `1I` returned
> `IN1808 IPCP SA`, proving the session remained usable. Therefore `Q` is
> not eligible for the mixed batch on this device. The probe has been revised
> to test `1I` -> standalone `Q` -> 29-query batch -> `1I`; production
> batching remains unapproved until that exact revised sequence is captured.
>
> **GUI LAUNCHER FOR VIDEO-BATCH PROBE ADDED**
> `tools/probe_in1808_video_batch_gui.py` wraps the read-only batch probe in a
> small PyQt GUI. The operator supplies only IP/port; the tool resolves the
> ordered `Extron IN1808` credential candidates through the existing
> `JsonCredentialProvider` / root-level ignored `credentials.local.json`.
> Credential values are never displayed. Candidate fallback is allowed only
> after a typed, confirmed, safe Matrix authentication rejection. Network I/O
> runs on a worker thread rather than the Qt GUI thread. This remains hardware
> evidence tooling, not production polling implementation.
>
> **READ-ONLY VIDEO-BATCH HARDWARE PROBE ADDED**
> `tools/probe_in1808_video_batch.py` is hardware-evidence tooling for task
> 7.36, not production polling implementation. It performs a standalone `1I`
> exact-identity gate, sends the intended 30-command read-only Video status set
> as one CR-separated write, prints the complete raw response bytes/framing and
> elapsed time, then sends a second standalone `1I` to check post-batch session
> usability. It contains no route mutation or Audio state-changing command.
> Real hardware output has **NOT** yet been captured, so batching remains
> unapproved for production use.
>
> **CORRECTED CURRENT HARDWARE-QA BATCHING/LIVE-BOOTSTRAP AMENDMENT**
> Hardware QA on implementation HEAD `570902cb532d7028f3bb4402dc7f11930f0447c3`
> confirmed the visible no-`dBFS` wording and clarified the remaining behavior.
> The initial room Video poll had already completed before the Audio click. The
> repeated Video commands observed at the click were a **new duplicate full
> refresh** started by exact-IN1808 `matrix_room_live` bootstrap, which currently
> creates a new `MatrixController` and unconditionally calls
> `request_full_refresh()`. Audio then waits behind that unnecessary second
> poll. The previous amendment's description of this as merely an already-running
> initial Video refresh was therefore inaccurate and is superseded by this
> corrected architecture.
>
> The current architecture requires two fixes in PR #42: hardware-proven batching
> for legitimate exact-IN1808 full Video snapshots, and elimination of the
> duplicate full Video refresh when LIVE starts after an accepted room one-shot.
> A fresh LIVE transport may perform only the minimum exact identity/variant gate
> needed before Audio commands; it must not re-poll the complete Video status set.
>
> Production code/tests for these fixes have **NOT** been implemented yet. Real
> mixed-Video-batch protocol evidence is still required before implementation.


> **CURRENT VISIBLE METER-WORDING IMPLEMENTATION EVIDENCE**
> This section supersedes the historical implementation evidence below for the
> current implementation-review handoff. Earlier evidence remains unchanged.

# IN1808 Visible Audio Meter Wording Follow-up

This presentation-only follow-up started from approved architecture HEAD
`ed2bccba634d4da5ed97f27991d2a108d2a8b25c` and the previously implemented and
hardware-tested behavior at `a67857727dd2c08bf74b24641398e07fe59e7a29`.
The final implementation revision is the single focused commit containing this
section. Its exact SHA is recorded after the ordinary push in the implementation
handoff and verified by the post-push local/remote SHA comparison.

## Implemented Wording

- Available visible IN1808 Audio meter text now renders the numeric value alone,
  for example `-20.0` instead of `-20.0 dBFS`.
- Unavailable IN1808 Audio meter text, including unavailable Program L/R,
  renders exactly `—` instead of `— dBFS`.
- Internal `dbfs`, `display_dbfs`, raw meter evidence, normalization,
  conversion, segment fill, scale, orientation, and geometry are unchanged.
- Generic DMP presentation remains unchanged and continues to render visible
  values such as `-12.5 dBFS` and `— dBFS`.
- Matrix controller/handler/protocol ownership, Audio lifecycle/currentness,
  credentials, polling, mode switching, and route projection are unchanged.
- Video batching, Video full-refresh cancellation/preemption, and transport
  redesign were not implemented.

## Changed Files

- `gui/room_diagnostic_tree.py`: removed only the literal visible unit suffix
  from the exact IN1808 logical-meter label.
- `tests/test_in1808_audio_routing_meters.py`: exact available, unavailable,
  Program-unknown, and card-scoped no-visible-`dBFS` regressions.
- `openspec/changes/in1808-audio-routing-meters/tasks.md`: recorded completion
  of the approved architecture gate; combined implementation/hardware task
  7.34 remains open.
- `openspec/changes/in1808-audio-routing-meters/implementation-report.md`: this
  current evidence section; historical evidence below is preserved.

No normative proposal, design, or delta-spec file changed. No theme,
application/controller, handler, protocol, credential, Graphify, generated
artifact, or log-capture file changed.

## Fresh Automated Evidence

Focused IN1808 command:

```powershell
py -3.12 -m unittest tests.test_in1808_audio_routing_meters -v
```

- 61 tests run; 61 passed; 0 failed; 0 errors; 0 skipped.

Related Matrix/room/lifecycle command:

```powershell
py -3.12 -m unittest tests.test_in1808_audio_routing_meters tests.test_extron_matrix_profiles tests.test_matrix_controller tests.test_matrix_handler_security tests.test_matrix_modern_ui tests.test_audio_dsp_modern_ui tests.test_extron_dmp64_plus_meter_diagnostics tests.test_inventory_diagnostic_dispatch tests.test_room_equipment_diagnostic_tree tests.test_room_interaction tests.test_gui_theme tests.test_room_live_production_lifecycle -v
```

- 377 tests run; 377 passed; 0 failed; 0 errors; 0 skipped.

Full offline suite:

```powershell
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- 1071 tests run; 1071 passed; 0 failed; 0 errors; 0 skipped.

Repository-local OpenSpec validation on Node v20.19.0 / npm 10.8.2:

- `.\openspec.cmd validate in1808-audio-routing-meters --strict`: PASS.
- `.\openspec.cmd validate --all --strict`: PASS, 18/18 items.

Git validation:

- `git diff --check`: PASS.
- `git diff --cached --check`: required before publication.
- Post-push local/remote implementation SHA equality: required and recorded in
  the final handoff.

## Hardware Status

Hardware QA on the new final implementation HEAD: **NOT PERFORMED**.

Implementation handoff status: **READY FOR REVIEW**.

> **SUPERSEDED FOR IN1808 VISIBLE METER-UNIT WORDING**
> The current implementation evidence below applies to implementation HEAD
> `a67857727dd2c08bf74b24641398e07fe59e7a29`, which still renders the literal `dBFS` suffix in visible
> IN1808 Audio meter values. A newer approved-direction architecture amendment
> removes that visible suffix while preserving numeric/internal dBFS evidence.
> Production/tests have not yet implemented or validated that amendment, so the
> READY FOR REVIEW handoff below is historical for the superseded wording.

> **CURRENT HARDWARE-QA FOLLOW-UP IMPLEMENTATION EVIDENCE**
> This section supersedes the historical implementation evidence below for the
> current implementation-review handoff. Earlier evidence remains unchanged.

# IN1808 Audio Mode Hardware-QA Follow-up

This implementation started from approved architecture HEAD
`841ce680ee696d6615e96e1c61b19cfc03c9ffdd`. Previous real-hardware QA was
performed on implementation HEAD `8798b2e59f7043bd94652dab52045628430bb557`.
That session found that the first real Audio-button click could be discarded,
the short `Аудио` / `Видео` target-action wording was ambiguous, and the route
markers were too small. This section records implementation evidence, not an
independent-validation verdict or a hardware PASS.

The final implementation revision is the single focused commit containing this
section. Its exact SHA is recorded after the ordinary push in the implementation
handoff and is verified by the post-push local/remote SHA comparison.

## Implemented Follow-up

- The exact-IN1808 Video -> Audio control now admits the local presentation
  action when the same current row owns a non-retiring `RoomInteractionKind.LIVE`,
  even though that LIVE owner correctly keeps `row.network_actions_enabled`
  false. Admission still requires CONNECTED, non-stale, quiescent Audio state,
  and no pending acknowledgement. Retiring LIVE and unrelated exclusive
  operations remain blocked.
- The existing application-owned acknowledgement remains unchanged: the real
  control is disabled first, row mode and the neutral Audio grid are committed
  synchronously, the replacement control is re-enabled, and only then is Audio
  acquisition started or queued on the existing serialized Matrix owner.
- Video mode now reads exactly `Переключить на аудио`; Audio mode reads exactly
  `Переключить на видео`. The dedicated header column was widened so the action
  wording has presentation space; button text is not lifecycle authority.
- `QLabel#roomIN1808RouteCell` alone now uses a 15 pt font. Routing row height
  remains 30 px, alignment is unchanged, and no other Matrix, DMP, header,
  meter, or generic label typography is enlarged.
- Audio -> Video still performs the existing immediate presentation switch and
  Audio retirement/quiescence path. It issues no `request_full_refresh`,
  `request_status_refresh`, `get_full_status`, `1%`, or other automatic Video
  read.
- Video polling batching, full-refresh cancellation/preemption, transport
  redesign, a second Matrix session, overlapping Audio/Video I/O, and new
  lifecycle kinds were not implemented.

## Changed Files

- `gui/room_diagnostic_tree.py`: same-row non-retiring LIVE admission for the
  local mode action, exact action labels, and label-column presentation width.
- `gui/theme.py`: dedicated 15 pt IN1808 route-cell marker selector.
- `tests/test_in1808_audio_routing_meters.py`: real-button integrated LIVE
  regression, retiring/exclusive negative cases, exact labels, actual themed Qt
  marker geometry, and explicit Audio -> Video no-refresh assertions.
- `openspec/changes/in1808-audio-routing-meters/tasks.md`: factual architecture
  review and follow-up implementation tracking while hardware task 7.25 stays
  open.
- `openspec/changes/in1808-audio-routing-meters/implementation-report.md`: this
  current evidence section; historical evidence below is preserved.

No normative proposal, design, or delta-spec file changed. No Matrix controller,
handler, protocol, credential, Graphify, generated artifact, or log-capture file
changed.

## Fresh Automated Evidence

Focused IN1808 command:

```powershell
py -3.12 -m unittest tests.test_in1808_audio_routing_meters -v
```

- 61 tests run; 61 passed; 0 failed; 0 errors; 0 skipped.

Related Matrix/room/lifecycle command:

```powershell
py -3.12 -m unittest tests.test_in1808_audio_routing_meters tests.test_extron_matrix_profiles tests.test_matrix_controller tests.test_matrix_handler_security tests.test_matrix_modern_ui tests.test_audio_dsp_modern_ui tests.test_extron_dmp64_plus_meter_diagnostics tests.test_inventory_diagnostic_dispatch tests.test_room_equipment_diagnostic_tree tests.test_room_interaction tests.test_gui_theme tests.test_room_live_production_lifecycle -v
```

- 377 tests run; 377 passed; 0 failed; 0 errors; 0 skipped.

Full offline suite:

```powershell
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- 1071 tests run; 1071 passed; 0 failed; 0 errors; 0 skipped.

Repository-local OpenSpec validation on Node v20.19.0 / npm 10.8.2:

- `.\openspec.cmd validate in1808-audio-routing-meters --strict`: PASS.
- `.\openspec.cmd validate --all --strict`: PASS, 18/18 items.

Git validation:

- `git diff --check`: PASS.
- `git diff --cached --check`: PASS.
- Post-push local/remote implementation SHA equality: required and recorded in
  the final handoff.

## Hardware Status

Hardware QA on the new final implementation HEAD: **NOT PERFORMED**.

Implementation handoff status: **READY FOR REVIEW**.

> **SUPERSEDED BY CURRENT HARDWARE-QA WORDING AMENDMENT**
> The remediation evidence below applies to implementation HEAD `8798b2e59f7043bd94652dab52045628430bb557`.
> Hardware QA subsequently changed the exact row-header mode-control text to
> `Переключить на аудио` / `Переключить на видео`. Production/tests have not
> yet implemented or validated that amended wording, so the older READY FOR REVIEW
> handoff below is historical evidence only.

> **CURRENT REMEDIATION EVIDENCE**
> This section supersedes the implementation evidence below for the current
> implementation-review handoff. Historical evidence remains unchanged.

# IN1808 Meter Layout and Mode Acknowledgement Remediation

This remediation was implemented from approved amendment HEAD
`ecaf2c4268ae44294ed56e184395ebb0d2b2ca79`. The publication revision is the
single focused remediation commit containing this report and is verified by
the post-push local/remote SHA comparison. This is implementation evidence,
not an independent validation verdict.

## Remediated Behavior

- The IN1808 logical-meter track now has an IN1808-specific object/style
  contract. Horizontal tracks are 99 x 8 pixels and vertical tracks are
  12 x 99 pixels, which fits all twenty fixed segments plus nineteen one-pixel
  gaps. The unchanged legacy DMP `roomAudioDspMeterTrack` vertical QSS can no
  longer constrain or clip the IN1808 horizontal scale.
- An actual-layout regression applies the application theme, shows the widget,
  processes Qt events, and verifies orientation-specific track/parent bounds,
  non-zero visible segment geometry, all twenty segments within each track,
  compact horizontal height, and the absence of the legacy 22-pixel width.
- An accepted `Аудио` request now creates an application-owned acknowledgement
  token, immediately disables the current exact-row control, changes local
  Audio state, and renders the complete neutral Audio grid synchronously.
  Structural layout properties, rather than button text, prove that the same
  session/row/operation-token/Audio-generation layout was committed before the
  current control is re-enabled as `Видео`.
- The acknowledgement has a single-shot 10-second hard maximum. Its callback
  is guarded by exact session object/identity, record and row identity, row
  operation token, Audio generation, interaction context/retirement state, and
  credential-context revision. Collapse, replacement, invalidation, shutdown,
  and newer requests discard stale acknowledgement authority.
- Normal acknowledgement completion does not wait for a Matrix controller,
  controller-busy retry, metadata, routing, meters, device I/O, or any network
  result. A fail-safe expiry only re-enables the same-current control; it does
  not render a layout, create Audio evidence, change protocol state, or start
  I/O.
- Audio -> Video remains an immediate presentation switch followed by the
  existing Audio cleanup/quiescence gate. It adds no `request_full_refresh`,
  video query, or new Video polling.

## Current Changed Files

- `gui/main_window.py`: application-owned acknowledgement token/timer,
  same-current commit verification, bounded expiry, and lifecycle revocation.
- `gui/room_diagnostic_tree.py`: current-item mode-control lookup, pending-state
  rendering, structural Audio-layout commit markers, and orientation-specific
  IN1808 meter-track geometry.
- `gui/theme.py`: distinct horizontal/vertical IN1808 track selectors while
  preserving generic DMP meter styling unchanged.
- `tests/test_in1808_audio_routing_meters.py`: actual Qt geometry, synchronous
  disabled/commit/re-enable, controller-absent/busy, deterministic fail-safe,
  replacement/collapse staleness, and Audio -> Video no-refresh regressions.
- `openspec/changes/in1808-audio-routing-meters/tasks.md`: factual completion
  state through remediation validation/publication; real hardware QA remains
  open.

## Fresh Automated Evidence

Focused IN1808 regression command:

```powershell
py -3.12 -m unittest tests.test_in1808_audio_routing_meters -v
```

- 58 tests run; 58 passed; 0 failed; 0 errors; 0 skipped.

Related Matrix/room/lifecycle regression command:

```powershell
py -3.12 -m unittest tests.test_in1808_audio_routing_meters tests.test_extron_matrix_profiles tests.test_matrix_controller tests.test_matrix_handler_security tests.test_matrix_modern_ui tests.test_audio_dsp_modern_ui tests.test_extron_dmp64_plus_meter_diagnostics tests.test_inventory_diagnostic_dispatch tests.test_room_equipment_diagnostic_tree tests.test_room_interaction tests.test_gui_theme tests.test_room_live_production_lifecycle -v
```

- 374 tests run; 374 passed; 0 failed; 0 errors; 0 skipped.

Full offline suite:

```powershell
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- 1068 tests run; 1068 passed; 0 failed; 0 errors; 0 skipped.

Repository-local OpenSpec validation on Node v20.19.0 / npm 10.8.2:

- `./openspec.cmd validate in1808-audio-routing-meters --strict`: PASS.
- `./openspec.cmd validate --all --strict`: PASS, 18/18 items.

Git validation:

- `git diff --check`: PASS.
- `git diff --cached --check`: PASS.
- The final local/remote remediation SHA is checked after the ordinary push.

## Hardware Status

Hardware QA: **NOT PERFORMED** in this remediation session.

Real IN1808 hardware QA remains required on the remediation HEAD.

Implementation handoff status: **READY FOR REVIEW**. This does not claim
independent revalidation, archive readiness, merge readiness, or hardware-QA
completion.

> **SUPERSEDED BY CURRENT HARDWARE-QA FOLLOW-UP**
> This implementation evidence applies to feature HEAD `6810359dbdd9c033a4745357b47e843f30bc723b`.
> Subsequent hardware QA found that the horizontal logical input-meter scale can
> be clipped by the legacy vertical meter-track QSS, and the approved change was
> amended to require a bounded disabled-state acknowledgement on the `Аудио`
> mode control. Do not treat the `READY FOR REVIEW` status below as evidence for
> the amended architecture. New implementation/test evidence is required after
> those follow-up items are implemented.

# GUI Refinement Implementation Evidence

This section records the hardware-QA GUI refinement implemented from approved
architecture HEAD `30aa120e9cd3dfd2931f8ec6635f651d4c3427e0`. The publication
revision is the feature-branch commit containing this report and is verified by
the post-push local/remote SHA comparison. This is implementation evidence, not
an independent validation verdict.

## Current Baseline

- Repository: `Mihail-R-cdx/diag-module-ref`.
- Branch: `agent/in1808-audio-routing-meters`.
- PR: `#42` (OPEN, Draft).
- `origin/master`: `5d2d44298334fc77741dab50652ca7e8472a7d76`.
- Implementation start / approved architecture HEAD:
  `30aa120e9cd3dfd2931f8ec6635f651d4c3427e0`.
- Runtime: Python 3.12; Node v20.19.0; npm 10.8.2.
- Hardware access: none in this session.

## Refined Behavior

- The first `Аудио` click now synchronously commits Audio mode, changes the
  control to `Видео`, and renders the complete neutral Audio grid before a
  Matrix controller or device result is available. A temporarily busy
  serialized controller retains the Audio presentation and uses the existing
  bounded background retry.
- One shared `QGridLayout` owns output meters, output headers, input meters,
  input headers, and route cells. Horizontal input-meter and routing-row
  centerlines therefore share a row; vertical output-meter and routing-column
  centerlines share a column. The top-left rail area is an explicit empty
  spacer, and routing rows are compact 30-pixel rows.
- The visible grid has exactly six stable logical input rows and seven base
  output columns. Exact SA/MA70 variants add one stereo/mono Amplifier column;
  base IN1808 has no empty amplifier slot.
- Raw channel-accurate routing evidence remains unchanged. Presentation-only
  grouping applies topology-aware FULL/INACTIVE/MIXED/UNKNOWN semantics for
  stereo-to-stereo, stereo-to-mono, mono-to-stereo, and mono-to-mono routes.
  Cells show only `●`, `○`, `◐`, or `—`; complete component state evidence is
  retained in tooltip/accessibility metadata.
- `Program L/R` uses only the physical 300xx meter group selected by mandatory
  `1$`. UNKNOWN source or unavailable selected-source evidence renders
  `— dBFS`; video `1%` is never used as a fallback.
- Input meters are horizontal, output meters are vertical, and every logical
  meter retains the modern 20-segment language. Structural labels appear only
  in row/column headers; meter labels and visible VALID/INVALID outcome text
  were removed.
- Stable semantic labels own grid geometry. Accepted ANAM values are exposed
  only as deterministic tooltip/accessibility metadata, including different
  stereo component names and selected Program-source metadata.
- Existing Matrix session ownership, LIVE serialization, Audio cleanup gates,
  stale callback rejection, video mutation authority, meter `*1/*0/*2`
  policy, and read-only Audio routing contract remain unchanged.

## Current Changed Files

- `gui/main_window.py`: immediate local Audio presentation before controller
  availability while preserving existing background serialization/cleanup.
- `gui/room_diagnostic_tree.py`: shared aligned logical grid, meter
  orientations, Program projection, topology-aware route grouping, stable
  labels, ANAM metadata, variant filtering, and marker-only route cells.
- `tests/test_in1808_audio_routing_meters.py`: immediate-switch, busy retry,
  shared-geometry, topology, raw-evidence, naming, Program-source, meter, text
  cleanup, and variant regressions.
- `openspec/changes/in1808-audio-routing-meters/tasks.md`: factual completion
  state for the GUI-refinement implementation and validation tasks.
- `openspec/changes/in1808-audio-routing-meters/implementation-report.md`:
  current evidence separated from the superseded implementation below.

## Fresh Automated Evidence

Focused regression command:

```powershell
py -3.12 -m unittest tests.test_in1808_audio_routing_meters tests.test_extron_matrix_profiles tests.test_matrix_controller tests.test_matrix_handler_security tests.test_matrix_modern_ui tests.test_audio_dsp_modern_ui tests.test_extron_dmp64_plus_meter_diagnostics tests.test_inventory_diagnostic_dispatch tests.test_room_equipment_diagnostic_tree tests.test_room_interaction tests.test_gui_theme tests.test_room_live_production_lifecycle -v
```

- 370 tests run; 370 passed; 0 failed; 0 errors; 0 skipped.

Full offline suite:

```powershell
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- 1064 tests run; 1064 passed; 0 failed; 0 errors; 0 skipped.

Repository-local OpenSpec validation:

```text
node --version                                                    -> v20.19.0
npm --version                                                     -> 10.8.2
.\openspec.cmd validate in1808-audio-routing-meters --strict      -> valid
.\openspec.cmd validate --all --strict                            -> 18 passed, 0 failed
```

Git validation is completed immediately before commit and repeated after the
documentation update. The implementation worktree contains only the five files
listed above relative to the approved architecture HEAD.

## GUI and Hardware Evidence

- A local offscreen Qt component smoke test rendered the Audio card without
  hardware and verified the shared-grid ownership, six/eight logical topology,
  compact 30-pixel route rows, complete 20-segment meters, and absence of
  duplicate meter/status labels.
- Real IN1808 hardware QA was **NOT PERFORMED** in this session.
- Real IN1808 hardware QA remains required before independent validation.

## Current Implementation Status

`READY FOR REVIEW`

---

## Historical Superseded Implementation Evidence

> **SUPERSEDED FOR CURRENT HEAD**
> This report records implementation evidence for feature HEAD
> `012ba60c225dee4411126b71859b5b19cda7250d`. Hardware GUI QA subsequently
> changed the OpenSpec architecture beginning with commit
> `8f53042b06a11ba9ae3e5bd0807e96e0e67cc712` and later architecture-review
> corrections. Therefore the `READY FOR INDEPENDENT REVALIDATION` status at
> the end of this report applies only to the older implementation and is not the
> status of the current feature HEAD. Do not rewrite or reuse the test counts
> below as evidence for the refined GUI. New implementation evidence must be
> produced after the GUI refinement is implemented and revalidated.

# Implementation Evidence

This is implementation evidence, not an independent validation verdict. It
does not approve, archive, merge, close, or delete the change.

## Baseline

- Repository: `Mihail-R-cdx/diag-module-ref`.
- Branch: `agent/in1808-audio-routing-meters`.
- PR: `#42` (Draft).
- Change base / `origin/master`: `5d2d44298334fc77741dab50652ca7e8472a7d76`.
- Approved architecture SHA: `0e2340498d967b2baeef4f089bda0c383c4f68f3`.
- Implementation date: 2026-09-26.
- Runtime: Python 3.12; Node v20.19.0; npm 10.8.2.
- Hardware access: none; validation used deterministic offline fakes.

## Delivered Behavior

- Added one exact IN1808 Audio protocol/domain profile with closed wire-variant
  capability, ANAM names, mandatory `1$` Program source, approved meter OIDs,
  raw/dBFS component evidence, stereo aggregation, and read-only 200xx routing.
- Added IN1808 meter-state handling with initial read, bounded `*1` activation,
  no DMP `*2`, no production cleanup `*0`, and no blind replay after an
  ambiguous possible send.
- Batched each production Audio read family through the existing Matrix
  transport/session. A normal meter snapshot now uses one transport call; an
  entry snapshot uses five bounded calls, and inactive-meter activation uses
  bounded initial/enable/follow-up batches rather than one delayed call per OID.
- Preserved `1$` as a literal ordinary SIS command while applying the leading
  `W` only to the approved extended `V...AU` and `M...AU` commands; `ANAM`
  commands retain their already-complete wire form.
- Added one bounded retry timer when the serialized Matrix controller is
  temporarily busy. Entry and meter work therefore resumes after keepalive or
  another short operation without overlapping requests or accumulating a
  backlog. Meter scheduling accounts for operation duration to retain an
  approximately one-second cadence.
- Preserved canonical `Extron IN1808` application identity while retaining the
  exact accepted `1I` wire identity for amplifier filtering.
- Reused the existing MatrixController, persistent Matrix session, credential
  lane, serialization, LIVE authority, retirement boundary, and stale-result
  suppression. No GUI-thread network I/O or parallel session was added.
- Added the exact-IN1808 Audio/Video header control. Audio mode preserves the
  General information card and replaces only the right tile with 20-segment
  meters, current Program source, read-only ACTIVE/INACTIVE/UNKNOWN routing,
  mapping-basis disclosure, and output meters.
- Kept video `1%` / `<I>*1%` behavior and standalone Matrix, Audio DSP, and DMP
  ownership unchanged. Audio failures remain isolated unless the shared Matrix
  session itself has a fatal lifecycle failure.

## Changed Files

- `handlers/extron/in1808_audio.py`: exact protocol/domain profile.
- `handlers/extron/matrix.py`: exact wire identity and shared-session Audio API.
- `core/parser.py`: normalized wire-identity evidence.
- `core/room_diagnostic_tree.py`: capability and Audio subcontext row state.
- `gui/diagnostic_dispatch.py`: exact application-owned IN1808 capability.
- `gui/matrix_controller.py`: serialized Audio entry/meter operations.
- `gui/main_window.py`: LIVE scheduling, currentness, quiescence, and failure isolation.
- `gui/room_diagnostic_tree.py`: Audio/Video control and Variant B presentation.
- `tests/test_in1808_audio_routing_meters.py`: protocol, controller, lifecycle,
  GUI, capability, transport, and isolation regressions.
- `openspec/changes/in1808-audio-routing-meters/tasks.md`: factual task state.
- `openspec/changes/in1808-audio-routing-meters/implementation-report.md`: this evidence.

## Automated Evidence

Focused offline regression command:

```powershell
py -3.12 -m unittest tests.test_in1808_audio_routing_meters tests.test_extron_matrix_profiles tests.test_matrix_controller tests.test_matrix_handler_security tests.test_matrix_modern_ui tests.test_audio_dsp_modern_ui tests.test_extron_dmp64_plus_meter_diagnostics tests.test_inventory_diagnostic_dispatch tests.test_room_equipment_diagnostic_tree tests.test_room_interaction tests.test_gui_theme tests.test_room_live_production_lifecycle -v
```

- Result after review corrections: 363 tests run; 363 passed; 0 failed;
  0 errors; 0 skipped.

Full offline suite:

```powershell
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- Result after review corrections: 1057 tests run; 1057 passed; 0 failed;
  0 errors; 0 skipped.

Dependency and OpenSpec validation:

```text
node --version                                                    -> v20.19.0
npm --version                                                     -> 10.8.2
npm ci                                                            -> 79 packages, 0 vulnerabilities
.\openspec.cmd validate in1808-audio-routing-meters --strict      -> valid
.\openspec.cmd validate --all --strict                            -> 18 passed, 0 failed
```

Git whitespace validation:

```text
git diff --check                                                  -> passed
git diff --cached --check                                         -> passed
```

## Pending Independent Work

- Independent clean-worktree validation and archive applicability were not
  performed in this implementation session.
- The review corrections require a new independent validation against their
  exact published HEAD; this report is implementation evidence only.
- The change was not archived or merged, and PR #42 remains Draft.

## Implementation Status

`READY FOR INDEPENDENT REVALIDATION`
