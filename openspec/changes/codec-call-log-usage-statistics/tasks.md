# Tasks: codec-call-log-usage-statistics

## 0. Architecture publication and approval gate

- [x] Create this change from exact `master` base `41d3ca3a0c1d9c13835b6d7da6c2cdbdc016614d` on branch `agent/codec-call-log-usage-statistics`.
- [x] Keep architecture publication limited to active OpenSpec artifacts; do not change production code, tests, root specs, archived changes, validation evidence, equipment inventory, credentials, captured device traffic, or Graphify artifacts.
- [x] Read current `RULES.md`, the current `device-diagnostics-and-control` root contract, current call-log dialog/screen/worker paths, and current TE20/TE40/CloudLink/Polycom call-log handlers before writing architecture.
- [ ] Run repository-local architecture checks on the exact published remote architecture HEAD:

```powershell
git diff --check
.\openspec.cmd validate codec-call-log-usage-statistics --strict
.\openspec.cmd validate --all --strict
```

- [ ] Record exact remote feature HEAD, current `master`, PR state/Draft/base/head/mergeability, clean validation checkout state, commands, exit codes, and strict-validation results.
- [ ] Perform independent architecture review against current `RULES.md`, current root specs, current source/tests, and this change. Do not begin implementation until the architecture verdict is `APPROVE`.

## 1. Reconfirm implementation baseline and perform read-only protocol research

- [ ] Before implementation, read `RULES.md`, fetch `origin`, and record exact `origin/master`, `origin/agent/codec-call-log-usage-statistics`, PR state, Draft state, base/head, merge state, mergeability, and remote feature HEAD.
- [ ] If the remote feature HEAD changed after architecture approval, review every new commit and re-evaluate the approved architecture before editing code.
- [ ] Read the approved `proposal.md`, `design.md`, capability delta, current `device-diagnostics-and-control` call-log/session requirements, and relevant current source/tests.
- [ ] Inspect current TE20, TE40, CloudLink Bar 310 / Box 310, and Polycom RPG310 call-log implementations before selecting pagination or time-query mechanics.
- [ ] Use available real devices only for read-only observational research where source/fixtures are insufficient; do not place calls, delete history, alter device time/configuration, change credentials, or otherwise manufacture journal state.
- [ ] For each protocol family/model as applicable, establish and report sanitized facts for call-log endpoint/command, ordering, batch/page limit, pagination/cursor/offset semantics, end-of-journal indication, source record identity if available, timestamp/duration encoding, active-call representation if present, and reliable codec-local current-time acquisition.
- [ ] Confirm that a small/recent live journal is acceptable evidence for wire behavior; do not block implementation because a device lacks 100 calls or 90 days of history.
- [ ] Do not commit production IPs, credentials, cookies, tokens, raw captures, HAR files, or sensitive response bodies. Synthetic fixtures remain the deterministic evidence for unavailable edge cases.

## 2. Introduce a normalized call-history and usage-calculation boundary

- [ ] Add a focused machine-readable normalized call-history snapshot/model shared by the five supported presentation paths; do not parse GUI-formatted date/duration strings for arithmetic.
- [ ] Preserve room/call number, start time, duration, speed, active state, and optional stable source identity needed for display/retrieval semantics.
- [ ] Keep normalized call timestamps and `reference_now` on one coherent codec-local calendar basis; when reliable codec time is unavailable, use computer-local time with a structured fallback warning.
- [ ] Preserve literal call-log records: no result/outcome/direction filtering and no interval union across legitimate overlapping calls.
- [ ] Suppress only transport/page duplicates proven to be the same source record; do not semantic-deduplicate distinct calls.
- [ ] Count active and malformed-duration visible records toward the 100-record acquisition ceiling while excluding active calls and unparseable durations from usage totals.
- [ ] Implement pure calculation helpers for 30-day and 90-day calendar windows, exact interval overlap, weekday-count `* 8h` denominator, one-decimal-hour display value, whole percentage, and percentages above 100% without clamping.
- [ ] Make the current weekday and a partial first weekday in a degraded interval contribute a full eight denominator hours; ignore holidays/shifted workdays.
- [ ] Guard a zero-weekday denominator without dividing by zero.

## 3. Implement bounded Huawei call-history retrieval without changing lifecycle authority

- [ ] Preserve Huawei TE20, TE40, CloudLink Bar 310, and CloudLink Box 310 call-history work on the existing shared interactive-session/controller path.
- [ ] Extend each model-specific handler/protocol boundary only as required by the researched read-only history mechanism; do not invent undocumented pagination parameters.
- [ ] Retrieve newest-first and stop after 90-day coverage is proven, clean end-of-journal is reported, exactly 100 accepted records are obtained, or a typed operational failure prevents continuation.
- [ ] Never accept a 101st call-log record solely to improve statistics.
- [ ] Keep existing bounded invalid-session recovery: one approved reconnect/replay path for Huawei call-log work, with no handler-owned credential fallback and no unbounded retry loop.
- [ ] Obtain codec-local current time through the researched read-only mechanism when reliable; otherwise publish the structured system-time fallback warning rather than silently mixing time bases.
- [ ] Preserve exact `CloudLink Box 310` identity while reusing shared CloudLink handler semantics where already approved.
- [ ] Keep all history/device-time I/O and cleanup outside the Qt GUI thread.

## 4. Implement bounded Polycom call-history retrieval while preserving its dedicated worker

- [ ] Keep Polycom RPG310 call-log acquisition owned by the existing short-lived Polycom call-log worker/session path; do not route it through the Huawei/shared interactive controller.
- [ ] Replace the current fixed presentation-depth request behavior only as required by the researched Polycom history pagination/limit contract.
- [ ] Apply the same newest-first stop conditions and exact 100-accepted-record ceiling as the Huawei paths.
- [ ] Preserve typed HTTPS authentication/session/transport errors and existing application-owned credential policy.
- [ ] Obtain/normalize Polycom codec-local current time when reliable; otherwise use the same explicit computer-time fallback warning.
- [ ] Keep Polycom connection, history reads, device-time reads, and logout/cleanup off the Qt GUI thread.

## 5. Implement explicit completeness/degradation semantics

- [ ] Treat clean end-of-journal as complete history for this feature: older parts of 30/90-day windows contribute zero usage and do not trigger a retention warning.
- [ ] Treat successful empty history as valid complete data and produce full 30-day and 90-day zero-usage rows.
- [ ] When the 100-record ceiling is reached before 90-day coverage, calculate the degraded interval from the exact oldest accepted record timestamp through `reference_now` and derive its displayed day count from calendar dates touched inclusively.
- [ ] If 100 records cover at least 30 but fewer than 90 days, keep a normal 30-day row and replace the 90-day row with the actual degraded-period row and warning.
- [ ] If 100 records cover fewer than 30 days, show exactly one degraded-period row rather than duplicate 30/90 rows and warn that the 100-record ceiling limited coverage.
- [ ] Recalculate both numerator and weekday `* 8h` denominator for every degraded interval; do not divide a shortened numerator by the original 30/90-day denominator.
- [ ] Keep malformed-duration records visible, exclude them from totals, and attach a partial-calculation warning.
- [ ] If deep retrieval fails, preserve already accepted recent records and every target statistic whose coverage had already been proven; mark only unproven longer statistics incomplete/unavailable with a non-secret warning.

## 6. Redesign the call-log dialog without changing visible record fields

- [ ] Replace the current ten-row-only presentation with two always-visible newest call rows using the existing four fields: `Номер комнаты`, `Дата и время начала`, `Продолжительность`, `Скорость`.
- [ ] Add usage summary row(s) below the preview using existing GUI visual language; exact typography may adapt to current components but hours, percent, period/day count, and warnings must remain clear.
- [ ] Add an initially collapsed disclosure section labelled exactly `Журнал звонков` showing up to the latest 20 records total, including the two preview records.
- [ ] If fewer than 20 records exist, show every available record with no artificial empty rows.
- [ ] Keep active calls in chronological preview/list position and visibly mark them `Активный`; do not remove them merely because they are excluded from statistics.
- [ ] Show `Загрузка журнала звонков...` during initial acquisition and `Расчёт статистики использования...` while deeper history/calculation continues.
- [ ] Show non-modal warnings for system-time fallback, 100-record degradation, malformed durations, and incomplete deeper retrieval.
- [ ] Use already loaded records when expanding/collapsing `Журнал звонков`; do not perform an extra device query on disclosure toggles.
- [ ] Preserve fresh acquisition for every later explicit dialog open; do not introduce a cross-opening call-history cache.
- [ ] Keep all five supported models visually identical and keep GUI code free of vendor protocol parsing, credential selection, or blocking network I/O.

## 7. Add deterministic regression coverage

- [ ] Add pure calculation tests for normal 30/90-day windows, inclusion of today, calendar boundaries, boundary-crossing call overlap, night/weekend numerator inclusion, Monday-Friday denominator, full eight hours for current/partial first weekdays, whole percentages, and values above 100%.
- [ ] Cover literal successful/unanswered/failed and incoming/outgoing records without outcome filtering.
- [ ] Cover legitimate overlapping records summing independently rather than interval-union behavior.
- [ ] Cover active records remaining visible/counting toward 100 but contributing zero usage.
- [ ] Cover malformed duration remaining visible, excluded from totals, and producing a warning.
- [ ] Cover clean early source end and successful empty journal as complete full-period data.
- [ ] Cover exact stop after 90-day coverage and exact hard stop at 100 accepted records with no 101st accepted record.
- [ ] Cover 100-record degradation shorter than 30 days (one row) and between 30 and 90 days (full 30-day row plus degraded longer row), including exact oldest-record interval start and full eight-hour partial-first-weekday denominator.
- [ ] Cover deep retrieval failure after 30-day coverage preserving valid 30-day statistics while the longer period becomes incomplete/unavailable.
- [ ] Cover codec-time authority and computer-time fallback warning without mixing calendar bases.
- [ ] Cover page-boundary duplicate suppression while preserving distinct semantically similar/overlapping records.
- [ ] Cover latest-two preview, collapsed latest-20 total, fewer-than-20 behavior, active label, loading-stage transitions, warning rendering, no disclosure refetch, and fresh later explicit open.
- [ ] Cover Huawei shared-session ownership/recovery and Polycom dedicated-worker ownership so the common statistics layer does not collapse approved lifecycle boundaries.
- [ ] Use synthetic histories/fake handlers for 100+/old/active/malformed/error cases; automated regression tests must not require physical devices or network access.

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
- [ ] Independently repeat focused tests, the full offline suite, both strict OpenSpec validations, `git diff --check`, scope/security review, and all material period/limit/degradation/lifecycle/presentation contracts without fixing findings in the validation session.
- [ ] Independently verify current `master`, PR state/Draft/base/head/remote HEAD/mergeability before verdict and review every newer published commit first.
- [ ] Where physical devices are available, perform read-only live confirmation of the implemented protocol assumptions that can actually be observed (request success, record shape/order, next-page/end behavior, time acquisition/encoding); do not require 100 calls or 90-day history and do not manufacture device state.
- [ ] Treat synthetic offline regression coverage, not accidental live journal contents, as the proof for 100-record, old-history, active/malformed, and failure edge cases.
- [ ] Because this change adds a new root capability, perform the required disposable archive-applicability check from the exact validated remote HEAD using only repository-local `openspec.cmd`; inspect the prospective archive/root-spec diff against then-current root specs and discard the disposable archive output/worktree without publishing it.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, any mandatory test/strict validation/Git check fails, the validated remote HEAD changed, validation worktree was dirty, implementation differs from approved architecture, live-observable protocol assumptions contradict implementation, or archive applicability is unproven.
