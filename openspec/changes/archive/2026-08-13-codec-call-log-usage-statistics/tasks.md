# Tasks: codec-call-log-usage-statistics

## 0. Architecture publication and approval gate

- [x] Create this change from exact `master` base `41d3ca3a0c1d9c13835b6d7da6c2cdbdc016614d` on branch `agent/codec-call-log-usage-statistics`.
- [x] Keep architecture publication limited to active OpenSpec artifacts; do not change production code, tests, root specs, archived changes, validation evidence, equipment inventory, credentials, captured device traffic, or Graphify artifacts.
- [x] Read current `RULES.md`, the current `device-diagnostics-and-control` root contract, current call-log dialog/screen/worker paths, and current TE20/TE40/CloudLink/Polycom call-log handlers before writing architecture.
- [x] Resolve the first architecture review by adding interval-safe normal coverage proof, structured `source_history_limited`/no-progress semantics, and the repository-required Archive + completion phase.
- [x] Resolve the second architecture review by restoring the approved hard-cap product convention: exactly 100 accepted records degrade from `oldest_of_100.start_at` without requiring an additional interval-safe proof, while normal full-period coverage remains strict and `source_history_limited` remains separate.
- [ ] On the exact newly published remote architecture HEAD, create/use a clean validation checkout and run repository-local architecture checks:

```powershell
git diff --check
.\openspec.cmd validate codec-call-log-usage-statistics --strict
.\openspec.cmd validate --all --strict
```

- [ ] Record exact remote feature HEAD, current `master`, PR state/Draft/base/head/mergeability, clean validation checkout state, exact commands, exit codes, and strict-validation results for that exact remote HEAD.
- [ ] Perform independent architecture review against current `RULES.md`, current root specs, current source/tests, and the exact validated published architecture HEAD. Do not begin implementation until the architecture verdict is `APPROVE`.

## 1. Reconfirm implementation baseline and perform read-only protocol research

- [ ] Before implementation, read `RULES.md`, fetch `origin`, and record exact `origin/master`, `origin/agent/codec-call-log-usage-statistics`, PR state, Draft state, base/head, merge state, mergeability, and remote feature HEAD.
- [ ] If the remote feature HEAD changed after architecture approval, review every new commit and re-evaluate the approved architecture before editing code.
- [ ] Read the approved `proposal.md`, `design.md`, capability delta, current call-log/session root requirements, and relevant current source/tests.
- [ ] Inspect current TE20, TE40, CloudLink Bar 310 / Box 310, and Polycom RPG310 call-log implementations before selecting pagination or time-query mechanics.
- [ ] Use available real devices only for read-only observational research where source/fixtures are insufficient; do not place calls, delete history, alter device time/configuration, change credentials, or otherwise manufacture journal state.
- [ ] For each protocol family/model as applicable, establish and report sanitized facts for call-log endpoint/command, actual ordering key, batch/page limit, pagination/cursor/offset semantics, clean end-of-journal indication, repeated-page/no-progress behavior, source record identity if available, timestamp/duration encoding, active-call representation if present, and reliable codec-local current-time acquisition.
- [ ] Explicitly determine whether each source has an interval-safe invariant that permits early **normal full-period** coverage proof. Do not treat `oldest_retrieved.start_at < boundary` as proof by itself.
- [ ] If an early normal-coverage invariant is claimed, document the exact source/query guarantee and add focused synthetic coverage for that assumption.
- [ ] Establish a bounded `source_history_limited`/no-progress detection rule distinct from clean EoJ, the product cap at exactly 100 accepted records, and typed operational failure.
- [ ] Confirm that no interval-safe proof is required merely to apply the approved hard-cap 100 product convention after exactly 100 accepted records are reached.
- [ ] Confirm that a small/recent live journal is acceptable evidence for observable wire behavior; do not block implementation because a device lacks 100 calls or 90 days of history.
- [ ] Do not commit production IPs, credentials, cookies, tokens, raw captures, HAR files, or sensitive response bodies. Synthetic fixtures remain deterministic authority for unavailable edge cases.

## 2. Introduce normalized call-history and usage-calculation boundaries

- [x] Add a focused machine-readable normalized call-history snapshot/model shared by the five supported presentation paths; do not parse GUI-formatted date/duration strings for arithmetic.
- [x] Preserve room/call number, start time, duration, speed, active state, and optional stable source identity needed for display/retrieval semantics.
- [x] Represent acquisition termination explicitly as normal coverage proven, clean source end, product limit reached, source history limited, or operational failure.
- [x] Keep normalized call timestamps and `reference_now` on one coherent codec-local calendar basis; when reliable codec time is unavailable, use computer-local time with a structured fallback warning.
- [x] Preserve literal call-log records: no result/outcome/direction filtering and no interval union across legitimate overlapping calls.
- [x] Suppress only transport/page duplicates proven to be the same source record; do not semantic-deduplicate distinct calls.
- [x] Count active and malformed-duration visible records toward the 100-record ceiling while excluding active calls and unparseable durations from usage totals.
- [x] Implement pure helpers for normal 30/90 calendar windows, exact interval overlap, capped available-history intervals, touched-weekday `* 8h` denominator, one-decimal hours, whole percentages, and values above 100% without clamping.
- [x] Make the current weekday and a partial first weekday in a capped interval contribute a full eight denominator hours; ignore holidays/shifted workdays.
- [x] Guard a zero-weekday denominator without dividing by zero.

## 3. Implement bounded Huawei call-history retrieval without changing lifecycle authority

- [x] Preserve Huawei TE20, TE40, CloudLink Bar 310, and CloudLink Box 310 call-history work on the existing shared interactive-session/controller path.
- [x] Validate each model-specific fixed response shape; treat only a validated empty journal as clean EoJ, raise typed protocol failures for malformed/unrecognized payloads, and do not invent undocumented pagination parameters.
- [x] Normalize every returned batch newest-first by machine `start_at` before preview/latest-20/product-cap selection; do not claim that this proves source ordering or normal-period coverage.
- [x] Never accept a 101st call-log record solely to improve statistics.
- [x] Keep existing bounded invalid-session recovery with no handler-owned credential fallback and no unbounded retry loop.
- [x] Use codec-local current time only through a reliable researched mechanism; otherwise publish the structured system-time fallback warning without treating a supplied datetime as device authority.
- [x] Preserve exact `CloudLink Box 310` identity while reusing shared CloudLink handler semantics where already approved.
- [x] Keep all history/device-time I/O and cleanup outside the Qt GUI thread.

## 4. Implement bounded Polycom call-history retrieval while preserving its dedicated worker

- [x] Keep Polycom RPG310 call-log acquisition owned by the existing short-lived Polycom call-log worker/session path; do not route it through the Huawei/shared interactive controller.
- [x] Read-only live observation confirmed that the current Polycom fixed response returns all 16 records present on that device for `limit` 10, 20, and 25; the parser preserves every returned record and a non-empty result remains `source_history_limited` without protocol EoJ.
- [ ] Establish a documented or live-observed Polycom continuation mechanism capable of retrieving 20+ records when a device has more than 16; the observed `start`/`page` variants made no progress, so no undocumented parameter is used.
- [x] Normalize the returned batch newest-first and apply the same exact 100-accepted-record ceiling as the Huawei paths without claiming source-global recency.
- [x] Preserve typed HTTPS authentication/session/transport errors and existing application-owned credential policy.
- [x] Obtain/normalize Polycom codec-local current time when reliable; otherwise use the same explicit computer-time fallback warning.
- [x] Keep Polycom connection, history reads, device-time reads, and logout/cleanup off the Qt GUI thread.

## 5. Implement explicit completeness and degradation semantics

- [x] Treat clean EoJ as complete history for this feature: older parts of normal 30/90 windows contribute zero and do not trigger retention warnings.
- [x] Treat successful empty history with clean EoJ as valid complete data and produce normal 30-day and 90-day zero-usage rows.
- [x] For normal full 30/90 claims before clean EoJ, require interval-safe coverage proof; never infer completeness solely from an old `start_at`.
- [x] At exactly 100 accepted records without a higher-priority explicit terminal result, stop immediately and define capped available history as `[oldest_of_100.start_at, reference_now]` without requiring an additional interval-safe proof for that capped lower bound; clean EoJ in the same acquisition result remains complete.
- [x] Calculate hard-cap values from the accepted records only and display a clear warning that history was limited to 100 records.
- [x] If the hard-cap available interval reaches at least 30 but fewer than 90 calendar dates, show `30 days` plus the actual capped-day row (e.g. `47 days`).
- [x] If the hard-cap available interval reaches fewer than 30 calendar dates, show exactly one capped actual-day row (e.g. `18 days`).
- [x] If the hard-cap available interval reaches at least 90 days, show `30 days` and `90 days` rows from the capped dataset with the 100-record warning.
- [x] Recalculate numerator and touched-weekday `* 8h` denominator for every capped actual interval; a partial first weekday contributes full eight hours.
- [x] Do not silently apply the hard-cap convention to `source_history_limited` before 100 records. Preserve already proven normal targets; mark unproven targets incomplete/unavailable with a warning.
- [x] Keep malformed-duration records visible, exclude them from totals, and attach a partial-calculation warning.
- [ ] If typed deep retrieval fails, preserve already accepted recent records and every normal target whose coverage had already been proven; mark only unproven targets incomplete/unavailable.

## 6. Redesign the call-log dialog without changing visible record fields

- [x] Replace the current ten-row-only presentation with two always-visible newest call rows using `Номер комнаты`, `Дата и время начала`, `Продолжительность`, `Скорость`.
- [x] Add usage summary row(s) below the preview using existing GUI visual language; period/day count, hours, percentage, and warnings must remain clear.
- [x] Add an initially collapsed section labelled exactly `Журнал звонков` showing up to the latest 20 acquired records total, including the same two preview records; if fewer than 20 records are available, show all without padding, including the live-confirmed 16-record Polycom batch.
- [x] If fewer than 20 records exist, show every available record with no artificial empty rows.
- [x] Keep active calls in chronological preview/list position and visibly mark them `Активный`.
- [x] Show `Загрузка журнала звонков...` during initial acquisition; show `Расчёт статистики использования...` only while real deeper work continues, never as an artificial fixed-batch stage.
- [x] Show non-modal warnings for system-time fallback, hard cap 100, malformed durations, source-history limitation, and incomplete deeper retrieval.
- [x] Use already loaded records when expanding/collapsing; do not perform a device query on disclosure toggles.
- [x] Preserve fresh acquisition for every later explicit dialog open; do not introduce a cross-open history cache.
- [x] Keep all five supported models visually identical and keep GUI code free of vendor protocol parsing, credential selection, or blocking network I/O; source-limited Polycom batches use the same presentation without false completeness.

## 7. Add deterministic regression coverage

- [x] Cover normal 30/90 windows, inclusion of today, exact boundary overlap, night/weekend numerator inclusion, Monday-Friday denominator, current/partial-first weekday rules, whole percentages, and values above 100%.
- [x] Cover literal successful/unanswered/failed and incoming/outgoing records without outcome filtering.
- [x] Cover legitimate overlapping records summing independently.
- [x] Cover active records remaining visible/counting toward 100 but contributing zero usage.
- [x] Cover malformed duration remaining visible, excluded from totals, and warned.
- [x] Cover clean early EoJ and successful empty journal as complete full-period data.
- [x] Cover a normal full-coverage counterexample where `09:00/20 min` is followed by an unseen older `08:00/3 h` record crossing the 10:00 boundary; `start_at < boundary` alone must not stop normal retrieval.
- [x] Cover exact hard stop after the 100th accepted record with no 101st accepted record.
- [x] Cover hard-cap `47 days -> 30 + 47` without requiring interval-safe proof for the 47-day capped lower bound.
- [x] Cover hard-cap `18 days -> exactly one 18-day row` without requiring interval-safe proof for the 18-day capped lower bound.
- [x] Cover oldest hard-cap record Monday 15:00: numerator starts exactly 15:00 and Monday contributes full eight hours denominator.
- [x] Cover `source_history_limited`/repeated page/no-progress before 100 remaining distinct from hard-cap product degradation.
- [x] Cover typed deep failure after proven 30-day normal coverage preserving that row while an unproven longer target becomes incomplete/unavailable.
- [x] Cover codec-time authority and computer-time fallback warning without mixing calendar bases.
- [x] Cover page-boundary duplicate suppression while preserving distinct similar/overlapping records.
- [x] Cover latest-two preview, collapsed latest-20 total, fewer-than-20, active label, loading transitions, warnings, no disclosure refetch, and fresh later open, including a 16-record Polycom-like source-limited batch.
- [x] Cover Huawei shared-session ownership/recovery and Polycom dedicated-worker ownership.
- [x] Use synthetic histories/fake handlers for 100+/old/active/malformed/no-progress/error cases; automated regression tests must not require physical devices or network access.

## 8. Validate implementation and publish for independent validation

- [x] Run focused handler/history/calculation/worker/GUI regression modules with the repository-supported Python interpreter and record exact commands/counts.
- [x] Run the canonical full offline suite:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [x] Run repository-local strict OpenSpec validation only:

```powershell
.\openspec.cmd validate codec-call-log-usage-statistics --strict
.\openspec.cmd validate --all --strict
```

- [x] Run repository protection checks:

```powershell
git diff --check
git diff --cached --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [x] Review that no root spec, archive, validation-report-only artifact, real-device capture/secret, inventory, generated log, temporary environment, or Graphify output changed during implementation.
- [x] After architecture `APPROVE`, create focused implementation commit(s), push `agent/codec-call-log-usage-statistics`, and verify local HEAD equals remote branch HEAD without amend, rebase, force-push, or published-history rewrite.
- [x] Keep the PR Draft and do not issue the independent final `APPROVE` from the implementation session.

## 9. Independent validation, live confirmation, and archive applicability

- [ ] Create a separate clean detached worktree from current `origin/agent/codec-call-log-usage-statistics`, record remote SHA, and prove detached HEAD equals that exact remote SHA before validation.
- [ ] Independently repeat focused tests, the full offline suite, both strict OpenSpec validations, `git diff --check`, scope/security review, and all material period/cap/source-limit/lifecycle/presentation contracts without fixing findings in the validation session.
- [ ] Independently verify current `master`, PR state/Draft/base/head/remote HEAD/mergeability before verdict and review every newer published commit first.
- [ ] Where physical devices are available, perform read-only live confirmation of observable request/record/order/pagination/end/no-progress/time behavior and any claimed normal interval-safe coverage invariant; do not require 100 calls or 90-day history and do not manufacture device state.
- [ ] Treat synthetic offline regression coverage, not accidental live journal contents, as proof for hard-cap 47/18, hidden boundary-crossing, no-progress, old-history, active/malformed, and failure edge cases.
- [ ] Because this change adds a new root capability, perform the required disposable archive-applicability check from the exact validated remote HEAD using only repository-local `openspec.cmd`; inspect the prospective archive/root-spec diff against then-current root specs and discard disposable output/worktree without publishing it.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, any mandatory test/strict validation/Git check fails, the validated remote HEAD changed, validation worktree was dirty, implementation differs from approved architecture, live-observable protocol assumptions contradict implementation, or archive applicability is unproven.

## 10. Archive + completion

- [ ] Begin only after independent validation of the current published feature HEAD returns a permitting verdict and no newer remote feature commit has appeared.
- [ ] Re-read current `RULES.md`, fetch `origin`, and record current `origin/master`, current remote feature HEAD, PR state/Draft/base/head/mergeability, and the exact independently validated SHA before archive.
- [ ] If remote feature HEAD or `master` changed, review the new commits/diff first and stop/reorient if the permitting validation no longer applies.
- [ ] Archive only with the repository-local wrapper:

```powershell
.\openspec.cmd archive codec-call-log-usage-statistics --yes
```

- [ ] Review the complete archive/root-spec diff, including the new root `codec-call-log-usage-statistics` capability, and confirm no unrelated root-spec changes.
- [ ] Run mandatory post-archive strict validation:

```powershell
.\openspec.cmd validate --all --strict
```

- [ ] Run the canonical full offline suite after archive:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] Run post-archive Git protection checks:

```powershell
git diff --check
git diff --cached --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [ ] Confirm no unexpected production/test/inventory/credential/capture/Graphify/generated artifacts were introduced by archive.
- [ ] Create one dedicated archive commit containing only the expected archived change and root-spec delta, then push `agent/codec-call-log-usage-statistics` without amend, rebase, force-push, or published-history rewrite.
- [ ] Re-fetch GitHub and prove local archive HEAD equals remote feature HEAD. Reconfirm current `master`, PR state/Draft/base/head/mergeability, and review any new remote commit before readiness.
- [ ] Issue `READY FOR MERGE` only when archive/root-spec review, strict-all validation, full offline tests, Git checks, dedicated archive commit/push, and remote-head equality all pass with no unresolved Critical/High/Medium findings.
- [ ] Do not merge, undraft, close the PR, delete the branch, or otherwise change publication state without explicit user authorization.
