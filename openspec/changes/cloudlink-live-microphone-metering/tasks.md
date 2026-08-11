# Tasks: cloudlink-live-microphone-metering

## 0. Architecture publication and approval gate

- [x] Create this change from exact `master` base `3197b3326be2cdf7387cf45d0360a18ec5b12ce3` on branch `agent/cloudlink-live-microphone-metering`.
- [x] Keep architecture publication limited to active OpenSpec artifacts; do not change production code, tests, root specs, archived changes, validation evidence, operational inventory, HAR captures, credentials, or Graphify artifacts.
- [x] Read current `RULES.md`, `docs/equipment-inventory-runbook.md`, current `pdu-room-codec-enrichment` root spec, current CloudLink handler/worker/screen paths, DMP meter lifecycle/presentation reference, and current PDU enrichment implementation before writing architecture.
- [x] Record the approved Bar 310 protocol assumption that the normal established CloudLink session obtains HTTP `200` with valid `curMicVouumeList` from `GET /v1/mediacontrol/mic/current-volume` without `X-Access-Token`; this change introduces no meter-specific token/login authority.
- [ ] Run repository-local architecture checks on the exact published remote architecture HEAD:

```powershell
git diff --check
.\openspec.cmd validate cloudlink-live-microphone-metering --strict
.\openspec.cmd validate --all --strict
```

- [ ] Record exact remote branch HEAD, current `master`, PR state/Draft/base/head/mergeability, clean validation checkout state, Node/npm versions, commands, exit codes, and strict-validation results.
- [ ] Perform independent architecture review against current `RULES.md`, root specs, current source/tests, and this change. Do not begin implementation until the architecture verdict is `APPROVE`.

## 1. Reconfirm implementation baseline before code changes

- [ ] Before beginning implementation, read `RULES.md` and, because PDU related-codec enrichment is in scope, `docs/equipment-inventory-runbook.md`.
- [ ] Fetch `origin` and record exact current `origin/master`, `origin/agent/cloudlink-live-microphone-metering`, PR state, Draft state, base/head, merge state, mergeability, and remote branch HEAD.
- [ ] If remote feature HEAD changed after architecture approval, review every newer commit and re-evaluate approved architecture before editing code.
- [ ] Read approved `proposal.md`, `design.md`, both delta specs, current root `pdu-room-codec-enrichment` spec, and relevant application/request-lifecycle root requirements.
- [ ] Read current `handlers/huawei/bar310.py`, `core/cloudlink_310.py`, `core/interactive_session.py`, CloudLink worker/parser code, `gui/screens/codec_screen.py`, `gui/pdu_room_codec_enrichment.py`, `gui/screens/pdu_screen.py`, application composition wiring, DMP polling/meter presentation reference, and relevant tests.
- [ ] Confirm implementation scope contains no equipment-inventory schema/model-recognition changes, PDU outlet-operation changes, DMP protocol changes, Matrix changes, state-changing audio commands, Graphify work, or captured HAR/secret artifacts.

## 2. Implement pure model-specific microphone sample extraction

- [ ] Add a focused CloudLink microphone sample normalization boundary shared by codec-page and PDU consumers; do not duplicate raw protocol parsing in both GUI paths.
- [ ] For Bar 310, send exact `GET /v1/mediacontrol/mic/current-volume` only after the normal CloudLink handler session is established and reuse that same HTTP-Basic-backed `requests.Session` / current CloudLink session context.
- [ ] Do not add, acquire, persist, refresh, infer, or transmit `X-Access-Token` or another meter-specific token/login flow; existing `acCSRFToken` handling remains action.cgi session material and is not a new meter credential.
- [ ] Preserve typed authentication/session failure and existing bounded recovery if the Bar meter endpoint rejects the established session; do not react by token discovery, alternate login, or handler-owned credential fallback.
- [ ] Require decoded `curMicVouumeList` to be a list and calculate the maximum non-negative numeric `curVolume` across every valid Mapping entry regardless of `deviceId`.
- [ ] Prove `deviceId == 18` is included and no fixed `0..17` range, preferred device, or list-position authority exists.
- [ ] Treat empty/malformed/no-valid-Bar observations as unavailable rather than zero.
- [ ] For Box 310, send exact `WEB_GetCurrentAudioParam` through the established authenticated CloudLink session/CSRF request boundary.
- [ ] Calculate the maximum only from the exact approved `mic1ValueIndex`..`mic4ValueIndex` and nine `micArray*_0*ValIdx` fields.
- [ ] Explicitly exclude TRS, RCA, HDMI, Bluetooth, UAC, `m220w_porwer_hint`, arbitrary substring-matched keys, and unreviewed audio fields.
- [ ] Treat missing/malformed/no-valid-Box microphone observations as unavailable rather than zero.
- [ ] If real-device implementation requires an additional non-mutating Box meter setup handshake, keep it inside the model-specific session, prove its necessity/safety with focused coverage, and do not use its response as meter-value authority or authentication authority.
- [ ] Do not add live sampling to ordinary CloudLink `get_status()`.

## 3. Implement canonical level and presentation normalization

- [ ] Represent available raw levels independently from unavailable state.
- [ ] Preserve observed raw `0` as valid silence.
- [ ] Normalize display fraction using fixed ceiling `20`, with `0 -> 0%`, `20 -> 100%`, and values above `20` display-clamped to 100% while preserving the raw observation.
- [ ] Do not manufacture dB/dBFS/percentage text or a physical-unit calibration.
- [ ] Keep the normalization pure and reusable by both presentation consumers.

## 4. Implement codec-page live meter lifecycle

- [ ] Add a focused CloudLink-specific application/composition lifecycle boundary for the current codec meter; do not create a generic multi-device polling manager.
- [ ] Capture immutable exact model/IP, meter generation/operation identity, and relevant credential-context identity before background work.
- [ ] Start metering only for exact accepted current `CloudLink Bar 310` or `CloudLink Box 310` context after normal diagnostic context acceptance.
- [ ] Poll at one-second cadence with at most one sample request in flight and no overlap when a sample is slow.
- [ ] Keep handler/session acquisition, sample I/O, bounded recovery, and cleanup outside the Qt GUI thread.
- [ ] Invalidate immediately on model/IP change, page/diagnostic-context replacement, repeat refresh, relevant credential-context change, explicit reset/deactivation, and shutdown.
- [ ] Reject queued stale work before handler acquisition and first network I/O where separable and reject stale result/error/completion callbacks before UI or memory publication.
- [ ] Ensure meter success is not successful credential-index/profile evidence.

## 5. Isolate optional sample failures while preserving typed terminal failures

- [ ] Map endpoint-local unsuccessful/malformed sample outcomes to meter-unavailable for that cycle and permit the next scheduled read on an otherwise usable current session.
- [ ] Preserve structured authentication, established-session invalidation, and transport/session failures for existing bounded read-only recovery.
- [ ] Do not create an unbounded one-second login/reconnect loop after terminal session failure.
- [ ] After bounded recovery is exhausted, keep the meter unavailable until a new authoritative diagnostic context starts.
- [ ] Ensure any meter failure leaves accepted ordinary codec status unchanged and opens no automatic modal error solely for optional telemetry.
- [ ] Ensure no string heuristic such as `auth`, `401`, or `403` advances credentials and no meter outcome persists credential/profile memory.
- [ ] Redact credentials, CSRF/session material, cookies, tokens, IP captures, and sensitive response data from public meter logs/errors.

## 6. Render the codec-page microphone meter

- [ ] Add exactly one `Уровень микрофонов` row to `Параметры и управление` for supported CloudLink models.
- [ ] Place it exactly after `Статус микрофона` and before `Журнал звонков`.
- [ ] Render a horizontal meter with no numeric overlay and the same available/unavailable visual semantics as the existing DMP meter.
- [ ] Hide the row for unsupported codec models.
- [ ] Make codec-owned widget rebuilds preserve exactly one current meter row, remove stale widget references safely, and prevent prior-context callbacks from updating rebuilt current widgets.

## 7. Extend PDU enrichment with a long-lived CloudLink meter child lifecycle

- [ ] Preserve `PDURoomCodecEnrichmentController` as owner of exact PDU/enrichment/room/related-codec identity and the dedicated related-codec serialized session lane.
- [ ] For exact resolved Bar 310 or Box 310, perform the existing initial normalized call/presentation status read first and publish existing codec diagnostic `SUCCESS` normally.
- [ ] After initial status success, retain the same current dedicated related-codec session context for serialized one-second microphone samples rather than opening a second simultaneous PDU-related CloudLink session solely for metering.
- [ ] Keep live-meter availability independent from `codec_diagnostic_status`, call status, presentation status, accepted PDU data, and PDU controls.
- [ ] For unsupported related-codec models, preserve existing one-shot status success and terminal session cleanup with no meter loop.
- [ ] Bind every PDU sample to exact enrichment generation, accepted PDU refresh identity, inventory-derived resolution, codec model/IP, and codec credential-context revision.
- [ ] On repeat refresh, PDU/model/IP/credential/inventory supersession, explicit invalidation, or shutdown, invalidate the old meter immediately and clean its session on the owning background lane.
- [ ] Ensure stale meter callbacks cannot restore old PDU presentation or mutate credential/profile memory.

## 8. Render the PDU meter above VIP

- [ ] Add exactly one `Уровень микрофонов` meter row to `Комната и связанный кодек` only when the current resolved related codec is exact Bar 310 or Box 310.
- [ ] Make it the top overall row of the block.
- [ ] Keep `VIP` immediately below it as the first room-context row and preserve existing VIP value semantics and prominent `VIP: ДА` treatment.
- [ ] Hide the meter before supported related-codec resolution and for unsupported related codecs without changing existing row semantics/order below it.
- [ ] Clear/hide the old meter at the same PDU enrichment supersession boundary that resets existing related-codec presentation.
- [ ] Keep the PDU screen rendering-only; it must not query inventory, choose codec models, select credentials, or perform network I/O.

## 9. Add focused synthetic regression coverage

- [ ] Add focused tests proving Bar sampling reuses the established session without `X-Access-Token` or another meter-specific token/login path.
- [ ] Add a Bar rejection test proving structured authentication/session failure remains typed and does not trigger token discovery or alternate login.
- [ ] Add focused tests for Bar maximum calculation across all entries, including a case where `deviceId == 18` owns the maximum.
- [ ] Cover Bar empty list, malformed list, invalid `curVolume`, mixed valid/invalid entries, and observed zero.
- [ ] Add focused tests for every Box approved microphone field and prove larger TRS/RCA/HDMI/Bluetooth/UAC values are excluded.
- [ ] Cover Box missing fields, mixed valid/invalid fields, no valid microphone field, and observed zero.
- [ ] Cover normalization at raw `0`, an intermediate value, `20`, and above `20`, plus unavailable state.
- [ ] Cover one-second scheduling and prove no overlapping sample requests when one read runs long.
- [ ] Cover stale cancellation before handler acquisition/I/O and stale callback suppression after context replacement.
- [ ] Cover endpoint-local sample failure followed by a later sample and bounded terminal session failure without unbounded reconnect or credential-memory mutation.
- [ ] Cover codec-page row exact order, supported/unsupported visibility, progress rendering, unavailable rendering, and rebuild/no-duplicate behavior.
- [ ] Extend PDU enrichment tests for status-success-then-meter continuation on the same dedicated lane, unsupported-codec one-shot cleanup, meter sample isolation, supersession, credential/inventory invalidation, and shutdown cleanup.
- [ ] Cover PDU row exact order: meter first overall, VIP immediately second/first room-context row, followed by existing block content.
- [ ] Cover accepted PDU success and existing call/presentation values remaining unchanged when the meter is unavailable.
- [ ] Use synthetic IPs/payloads and fake handlers/sessions only; do not add the supplied HAR files, real endpoint hosts, credentials, tokens, cookies, or production inventory to tests.

## 10. Validate implementation and publish for independent validation

- [ ] Run focused meter/PDU/GUI tests using the repository-supported Python interpreter and record exact counts. At minimum include the new meter tests plus existing PDU room-codec enrichment and device-screen regression modules affected by the implementation.
- [ ] Run the canonical full offline test suite:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] Run repository-local strict OpenSpec validation only:

```powershell
.\openspec.cmd validate cloudlink-live-microphone-metering --strict
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

- [ ] Review that no root spec, archive, validation-report-only artifact, HAR capture, credential/local inventory, generated log, temporary environment, or Graphify output changed during implementation.
- [ ] Create focused implementation commit(s), push `agent/cloudlink-live-microphone-metering`, and verify local HEAD equals the remote branch HEAD without amend, rebase, force-push, or history rewrite.
- [ ] Keep the PR Draft and do not issue the independent final `APPROVE` from the implementation session.

## 11. Independent validation and disposable archive applicability

- [ ] Create a separate clean detached worktree from current `origin/agent/cloudlink-live-microphone-metering`, record remote SHA, and prove validation worktree HEAD equals that SHA before validation.
- [ ] Independently repeat focused tests, the full offline suite, both strict OpenSpec validations, `git diff --check`, scope/security review, and all material protocol/lifecycle/presentation contracts without fixing findings in the validation session.
- [ ] Independently verify current `master`, PR state/Draft/base/head/remote HEAD/mergeability before the verdict and review any newer published commits first.
- [ ] Because this change creates a root capability and modifies existing `pdu-room-codec-enrichment` requirements, perform the required disposable archive-applicability check in the clean detached validation worktree using only the repository-local `openspec.cmd`; inspect the resulting archive/root-spec diff against then-current root specs and discard the disposable output/worktree without publishing it.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, any mandatory test/strict validation/Git check fails, the validated remote HEAD changed, the validation worktree was dirty, implementation differs from approved architecture, or archive applicability is unproven.
