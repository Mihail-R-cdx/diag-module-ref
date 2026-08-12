# Tasks: codec-call-log-usage-statistics

## 0. Architecture publication and approval gate

- [x] Create this change from exact `master` base `41d3ca3a0c1d9c13835b6d7da6c2cdbdc016614d` on branch `agent/codec-call-log-usage-statistics`.
- [x] Keep architecture publication limited to active OpenSpec artifacts; do not change production code, tests, root specs, archived changes, validation evidence, equipment inventory, credentials, captured device traffic, or Graphify artifacts.
- [x] Read current `RULES.md`, the current `device-diagnostics-and-control` root contract, current call-log dialog/screen/worker paths, and current TE20/TE40/CloudLink/Polycom call-log handlers before writing architecture.
- [x] Resolve architecture review findings by defining interval-safe coverage proof, structured source-history limitation/no-progress semantics, and the required Archive + completion phase without changing production code/tests/root specs.
- [ ] On the exact newly published remote architecture HEAD, create/use a clean validation checkout and run repository-local architecture checks:

```powershell
git diff --check
.\openspec.cmd validate codec-call-log-usage-statistics --strict
.\openspec.cmd validate --all --strict
```

- [ ] Record exact remote feature HEAD, current `master`, PR state/Draft/base/head/mergeability, clean validation checkout state, commands, exit codes, and strict-validation results for that exact remote HEAD.
- [ ] Perform independent architecture review against current `RULES.md`, current root specs, current source/tests, and the exact validated published architecture HEAD. Do not begin implementation until the architecture verdict is `APPROVE`.

## 1. Reconfirm implementation baseline and perform read-only protocol research

- [ ] Before implementation, read `RULES.md`, fetch `origin`, and record exact `origin/master`, `origin/agent/codec-call-log-usage-statistics`, PR state, Draft state, base/head, merge state, mergeability, and remote feature HEAD.
- [ ] If the remote feature HEAD changed after architecture approval, review every new commit and re-evaluate the approved architecture before editing code.
- [ ] Read the approved `proposal.md`, `design.md`, capability delta, current `device-diagnostics-and-control` call-log/session requirements, and relevant current source/tests.
- [ ] Inspect current TE20, TE40, CloudLink Bar 310 / Box 310, and Polycom RPG310 call-log implementations before selecting pagination or time-query mechanics.
- [ ] Use available real devices only for read-only observational research where source/fixtures are insufficient; do not place calls, delete history, alter device time/configuration, change credentials, or otherwise manufacture journal state.
- [ ] For each protocol family/model as applicable, establish and report sanitized facts for call-log endpoint/command, actual ordering key, batch/page limit, pagination/cursor/offset semantics, clean end-of-journal indication, source record identity if available, timestamp/duration encoding, active-call representation if present, and reliable codec-local current-time acquisition.
- [ ] For each protocol family/model as applicable, explicitly determine whether there is an interval-safe coverage invariant that proves no unseen older record can overlap a requested lower bound. Do not treat `oldest_retrieved.start_at < boundary` as proof by itself.
- [ ] If an early coverage invariant is claimed, document the exact source/query guarantee that makes it safe, such as end-time ordering, server-side interval-intersection semantics, or another proven ordering/duration/continuation invariant, and add focused synthetic tests for that exact assumption.
- [ ] Determine how the source behaves when deeper pagination is unavailable, ignored, repeated, or makes no progress; establish a bounded `source_history_limited`/no-progress detection rule distinct from clean EoJ and typed operational failure.
- [ ] Confirm that a small/recent live journal is acceptable evidence for observable wire behavior; do not block implementation because a device lacks 100 calls or 90 days of history.
- [ ] Do not commit production IPs, credentials, cookies, tokens, raw captures, HAR files, or sensitive response bodies. Synthetic fixtures remain the deterministic evidence for unavailable edge cases.

## 2. Introduce a normalized call-history and usage-calculation boundary

- [ ] Add a focused machine-readable normalized call-history snapshot/model shared by the five supported presentation paths; do not parse GUI-formatted date/duration strings for arithmetic.
- [ ] Preserve room/call number, start time, duration, speed, active state, and optional stable source identity needed for display/retrieval semantics.
- [ ] Represent acquisition termination/completeness structurally, distinguishing at least `coverage_proven`, `source_ended`, `product_limit_reached`, `source_history_limited`, and `operational_failure`.
- [ ] Represent a coverage lower bound only when interval-safe semantics actually prove that no unseen older record can overlap that timestamp; do not infer completeness from record count or oldest `start_at` alone.
- [ ] Keep normalized call timestamps and `reference_now` on one coherent codec-local calendar basis; when reliable codec time is unavailable, use computer-local time with a structured fallback warning.
- [ ] Preserve literal call-log records: no result/outcome/direction filtering and no interval union across legitimate overlapping calls.
- [ ] Suppress only transport/page duplicates proven to be the same source record; do not semantic-deduplicate distinct calls.
- [ ] Count active and malformed-duration visible records toward the 100-record acquisition ceiling while excluding active calls and unparseable durations from usage totals.
- [ ] Implement pure calculation helpers for 30-day and 90-day calendar windows, exact interval overlap, weekday-count `* 8h` denominator, one-decimal-hour display value, whole percentage, and percentages above 100% without clamping.
- [ ] Make the current weekday and a partial first weekday in a proven degraded interval contribute a full eight denominator hours; ignore holidays/shifted workdays.
- [ ] Guard a zero-weekday denominator without dividing by zero.

## 3. Implement bounded Huawei call-history retrieval without changing lifecycle authority

- [ ] Preserve Huawei TE20, TE40, CloudLink Bar 310, and CloudLink Box 310 call-history work on the existing shared interactive-session/controller path.
- [ ] Extend each model-specific handler/protocol boundary only as required by the researched read-only history mechanism; do not invent undocumented pagination or coverage parameters.
- [ ] Retrieve newest-first and stop only after interval-safe 90-day coverage is proven, clean end-of-journal is reported, exactly 100 accepted records are obtained, `source_history_limited`/no-progress is reached, or a typed operational failure prevents continuation.
- [ ] Never stop merely because one retrieved `start_at` is older than the target boundary unless the researched protocol invariant separately proves interval coverage.
- [ ] Never accept a 101st call-log record solely to improve statistics.
- [ ] Detect repeated-page/no-progress behavior without an unbounded loop and report it as `source_history_limited` rather than clean EoJ or a fabricated complete result.
- [ ] Keep existing bounded invalid-session recovery: one approved reconnect/replay path for Huawei call-log work, with no handler-owned credential fallback and no unbounded retry loop.
- [ ] Obtain codec-local current time through the researched read-only mechanism when reliable; otherwise publish the structured system-time fallback warning rather than silently mixing time bases.
- [ ] Preserve exact `CloudLink Box 310` identity while reusing shared CloudLink handler semantics where already approved.
- [ ] Keep all history/device-time I/O and cleanup outside the Qt GUI thread.

## 4. Implement bounded Polycom call-history retrieval while preserving its dedicated worker

- [ ] Keep Polycom RPG310 call-log acquisition owned by the existing short-lived Polycom call-log worker/session path; do not route it through the Huawei/shared interactive controller.
- [ ] Replace the current fixed presentation-depth request behavior only as required by the researched Polycom history pagination/limit contract.
- [ ] Apply the same interval-safe coverage rules, explicit `source_history_limited`/no-progress outcome, and exact 100-accepted-record ceiling as the Huawei paths.
- [ ] Do not interpret the current `/rest/calllog/entries?...limit=10` behavior, a maximum returned batch, or a repeated batch as clean EoJ unless the researched protocol contract actually proves it.
- [ ] Preserve typed HTTPS authentication/session/transport errors and existing application-owned credential policy.
- [ ] Obtain/normalize Polycom codec-local current time when reliable; otherwise use the same explicit computer-time fallback warning.
- [ ] Keep Polycom connection, history reads, device-time reads, and logout/cleanup off the Qt GUI thread.

## 5. Implement explicit completeness/degradation semantics

- [ ] Treat clean end-of-journal as complete history for this feature: older parts of 30/90-day windows contribute zero usage and do not trigger a retention warning.
- [ ] Treat successful empty history with clean EoJ as valid complete data and produce full 30-day and 90-day zero-usage rows.
- [ ] Keep a 30-day or 90-day statistic authoritative only when that target lower bound has interval-safe coverage proof or clean EoJ establishes the missing older history as zero.
- [ ] When the 100-record ceiling is reached, stop acquisition immediately but do not assume the oldest accepted `start_at` is a complete lower bound.
- [ ] Apply the agreed product-limit degraded interval from the exact oldest accepted record timestamp through `reference_now` only when interval-safe semantics prove that no unseen older record can overlap that exact timestamp.
- [ ] For a proven product-limit degraded interval, derive its displayed day count from calendar dates touched inclusively and recalculate both numerator and weekday `* 8h` denominator for the exact timestamp interval.
- [ ] If the complete 30-day interval is proven and a longer shortened interval is also proven but the complete 90-day interval is not, keep the normal 30-day row and show the proven actual-period longer row with warning.
- [ ] If a proven shortened interval is fewer than 30 days and the complete 30-day interval is not proven, show exactly one degraded actual-period row rather than duplicate 30/90 rows.
- [ ] If the product limit is reached but no target or shortened lower bound is interval-safe/proven, preserve recent records and mark affected statistics incomplete/unavailable instead of manufacturing a percentage.
- [ ] Treat `source_history_limited` distinctly from clean EoJ and typed failure. Preserve every already proven target statistic; show a shorter numeric statistic only if its lower bound is independently proven, otherwise mark the affected statistic incomplete/unavailable with a source-limit warning.
- [ ] Keep malformed-duration records visible, exclude them from totals, and attach a partial-calculation warning.
- [ ] If deep retrieval fails operationally, preserve already accepted recent records and every target statistic whose coverage had already been proven; mark only unproven statistics incomplete/unavailable with a non-secret warning.

## 6. Redesign the call-log dialog without changing visible record fields

- [ ] Replace the current ten-row-only presentation with two always-visible newest call rows using the existing four fields: `Номер комнаты`, `Дата и время начала`, `Продолжительность`, `Скорость`.
- [ ] Add usage summary row(s) below the preview using existing GUI visual language; exact typography may adapt to current components but hours, percent, period/day count, incomplete state, and warnings must remain clear.
- [ ] Add an initially collapsed disclosure section labelled exactly `Журнал звонков` showing up to the latest 20 records total, including the two preview records.
- [ ] If fewer than 20 records exist, show every available record with no artificial empty rows.
- [ ] Keep active calls in chronological preview/list position and visibly mark them `Активный`; do not remove them merely because they are excluded from statistics.
- [ ] Show `Загрузка журнала звонков...` during initial acquisition and `Расчёт статистики использования...` while deeper history/calculation continues.
- [ ] Show non-modal warnings for system-time fallback, product-limit degradation, source-history limitation/no-progress, malformed durations, and incomplete deeper retrieval.
- [ ] Use already loaded records when expanding/collapsing `Журнал звонков`; do not perform an extra device query on disclosure toggles.
- [ ] Preserve fresh acquisition for every later explicit dialog open; do not introduce a cross-opening call-history cache.
- [ ] Keep all five supported models visually identical and keep GUI code free of vendor protocol parsing, credential selection, or blocking network I/O.

## 7. Add deterministic regression coverage

- [ ] Add pure calculation tests for normal 30/90-day windows, inclusion of today, calendar boundaries, boundary-crossing call overlap, night/weekend numerator inclusion, Monday-Friday denominator, full eight hours for current/proven-partial-first weekdays, whole percentages, and values above 100%.
- [ ] Cover literal successful/unanswered/failed and incoming/outgoing records without outcome filtering.
- [ ] Cover legitimate overlapping records summing independently rather than interval-union behavior.
- [ ] Add the explicit coverage regression where boundary is 10:00, one retrieved record starts 09:00 for 20 minutes, and an older-start 08:00 record lasts three hours; prove that start-time ordering alone does not permit early stop after the 09:00 record.
- [ ] Cover an interval-safe protocol invariant that does permit early 90-day coverage stop and prove no further request is issued once that invariant is satisfied.
- [ ] Cover active records remaining visible/counting toward 100 but contributing zero usage.
- [ ] Cover malformed duration remaining visible, excluded from totals, and producing a warning.
- [ ] Cover clean early source end and successful empty journal as complete full-period data.
- [ ] Cover exact hard stop at 100 accepted records with no 101st accepted record.
- [ ] Cover 100-record proven degradation shorter than 30 days (one row) and between 30 and 90 days (full 30-day row plus proven degraded longer row), including exact oldest-record interval start and full eight-hour partial-first-weekday denominator.
- [ ] Cover 100-record stop without interval-safe proof preserving journal and marking affected statistics incomplete/unavailable.
- [ ] Cover `source_history_limited` when pagination is unsupported/ignored and when a continuation repeats the same page/no unique progress; prove bounded termination, no clean-EoJ fabrication, and no unbounded retry.
- [ ] Cover source-history limitation after 30-day coverage preserving the valid 30-day statistic while the unproven longer statistic becomes incomplete/unavailable.
- [ ] Cover deep operational retrieval failure after 30-day coverage preserving valid 30-day statistics while the longer period becomes incomplete/unavailable.
- [ ] Cover codec-time authority and computer-time fallback warning without mixing calendar bases.
- [ ] Cover page-boundary duplicate suppression while preserving distinct semantically similar/overlapping records.
- [ ] Cover latest-two preview, collapsed latest-20 total, fewer-than-20 behavior, active label, loading-stage transitions, warning rendering, no disclosure refetch, and fresh later explicit open.
- [ ] Cover Huawei shared-session ownership/recovery and Polycom dedicated-worker ownership so the common statistics layer does not collapse approved lifecycle boundaries.
- [ ] Use synthetic histories/fake handlers for 100+/old/active/malformed/error/no-progress cases; automated regression tests must not require physical devices or network access.

## 8. Validate implementation and publish for independent validation

- [ ] Run focused handler/history/calculation/worker/GUI regression modules with the repository-supported Python interpreter and record exact commands/counts.
- [ ] Run the canonical full offline test suite:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] Run repository-local strict OpenSpec validation only:

```powershell
.\openspec.cmd validate codec-call-log-usage-statistics --strict
.\openspec.cmd validate --all --strict
```

- [ ] Run repository protection checks:

```powershell
git diff --check
git diff --cached --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [ ] Review that no root spec, archive, validation-report-only artifact, real-device capture/secret, inventory, generated log, temporary environment, or Graphify output changed during implementation.
- [ ] After architecture `APPROVE`, create focused implementation commit(s), push `agent/codec-call-log-usage-statistics`, and verify local HEAD equals remote branch HEAD without amend, rebase, force-push, or published-history rewrite.
- [ ] Keep the PR Draft and do not issue the independent final `APPROVE` from the implementation session.

## 9. Independent validation, live confirmation, and archive applicability

- [ ] Create a separate clean detached worktree from current `origin/agent/codec-call-log-usage-statistics`, record remote SHA, and prove detached HEAD equals that exact remote SHA before validation.
- [ ] Independently repeat focused tests, the full offline suite, both strict OpenSpec validations, `git diff --check`, scope/security review, and all material period/coverage/limit/source-limitation/degradation/lifecycle/presentation contracts without fixing findings in the validation session.
- [ ] Independently verify current `master`, PR state/Draft/base/head/remote HEAD/mergeability before verdict and review every newer published commit first.
- [ ] Where physical devices are available, perform read-only live confirmation of the implemented protocol assumptions that can actually be observed: request success, record shape/order, next-page/end/no-progress behavior, time acquisition/encoding, and any claimed interval-safe coverage invariant. Do not require 100 calls or 90-day history and do not manufacture device state.
- [ ] Treat synthetic offline regression coverage, not accidental live journal contents, as the proof for 100-record, hidden boundary-crossing, no-progress, old-history, active/malformed, and failure edge cases.
- [ ] Because this change adds a new root capability, perform the required disposable archive-applicability check from the exact validated remote HEAD using only repository-local `openspec.cmd`; inspect the prospective archive/root-spec diff against then-current root specs and discard the disposable archive output/worktree without publishing it.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, any mandatory test/strict validation/Git check fails, the validated remote HEAD changed, validation worktree was dirty, implementation differs from approved architecture, live-observable protocol assumptions contradict implementation, or archive applicability is unproven.

## 10. Archive + completion

- [ ] Begin this phase only after independent validation of the current published feature HEAD returns a permitting verdict (`APPROVE` or repository-equivalent permitting status) and no newer remote feature commit has appeared.
- [ ] Re-read current `RULES.md`, fetch `origin`, and record current `origin/master`, current remote feature HEAD, PR state/Draft/base/head/mergeability, and the exact independently validated SHA before archive.
- [ ] If the remote feature HEAD or `master` changed, review the new commits/diff first and stop/reorient if the permitting validation no longer applies.
- [ ] Archive only with the repository-local wrapper:

```powershell
.\openspec.cmd archive codec-call-log-usage-statistics --yes
```

- [ ] Review the complete archive/root-spec diff produced by archive, including creation/update of the root `codec-call-log-usage-statistics` capability, and confirm it applies cleanly to then-current root specs without unrelated changes.
- [ ] Run mandatory post-archive strict validation:

```powershell
.\openspec.cmd validate --all --strict
```

- [ ] Run the canonical full offline test suite after archive:

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

- [ ] Confirm no unexpected production/test/inventory/credential/capture/Graphify/generated artifacts were introduced by the archive phase.
- [ ] Create one dedicated archive commit containing only the expected archived change and root-spec delta, then push `agent/codec-call-log-usage-statistics` without amend, rebase, force-push, or published-history rewrite.
- [ ] Re-fetch GitHub and prove local archive HEAD equals remote feature HEAD. Reconfirm current `master`, PR state/Draft/base/head/mergeability, and review any new remote commit before a readiness decision.
- [ ] Issue `READY FOR MERGE` only when archive/root-spec review, strict-all validation, full offline tests, Git checks, dedicated archive commit/push, and remote-head equality all pass with no unresolved Critical/High/Medium findings.
- [ ] Do not merge, undraft, close the PR, delete the branch, or otherwise change publication state without explicit user authorization.
