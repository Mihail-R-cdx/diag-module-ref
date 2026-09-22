# Tasks: Extron matrix model expansion

## 1. Architecture, evidence, and PRE-IMPLEMENTATION GATE

- [x] 1.1 Reconfirm current IN1804 production behavior and preserve the hardware-confirmed command baseline without semantic regression.
- [x] 1.2 Record official SIS evidence for IN1808 and IN1608 xi commands used by this change only: identity, temperature, names, signal presence, HDCP, route read/set.
- [x] 1.3 Record official SIS evidence for the exact supported DTP CrossPoint set, first-generation XTP CrossPoint, and XTP II CrossPoint commands used by this change only.
- [x] 1.4 Confirm DTP scope is limited to DTP CrossPoint 84 plus DTP CrossPoint 82/84/86/108 4K. Explicitly exclude DTP2/DTP3 and legacy analog CrossPoint generations.
- [x] 1.5 Confirm first-generation XTP output-HDCP uses `W0<N>HDCP` / `W0*HDCP`, while DTP uses `WO<N>HDCP`; keep XTP II output-HDCP UNPROVEN unless separately evidenced.
- [x] 1.6 Define authoritative XTP-vs-XTP-II frame/profile selection from exact frame identity/part-number evidence before dimension/board decoding.
- [x] 1.7 Keep unsupported/unproven diagnostics explicitly unavailable; do not add speculative SIS reads.
- [x] 1.8 Resolve the initial implementation scope for IN1808 Loop Out without treating physical connectors as independent routes by default.
- [x] 1.9 Reconcile every `MODIFIED Requirements` block against exact current root requirement identity and preserve all existing scenario identities in replacement blocks; genuinely new independent contracts must be `ADDED Requirements`.
- [x] 1.10 Run `openspec validate extron-matrix-model-expansion --strict` and record PASS.
- [x] 1.11 Run `openspec validate --all --strict` and record PASS.
- [x] 1.12 Perform disposable archive-applicability validation and confirm the modified requirements replace current root identities without contradiction or scenario loss.
- [x] 1.13 Run Git scope/hygiene checks (`git diff --check`, OpenSpec-only changed-file review, exact branch/SHA verification).
- [x] 1.14 Obtain independent architecture review with CRITICAL=0, HIGH=0 and explicit `IMPLEMENTATION MAY PROCEED: YES`.

**IMPLEMENTATION GATE:** Sections 2 through 9 SHALL NOT begin until tasks 1.10-1.14 are complete and PASS. A validation or review failure returns the change to OpenSpec/design correction; it does not authorize production-code work.

## 2. Capability and topology model

- [x] 2.1 Introduce a normalized Matrix capability/topology representation that distinguishes logical routing IDs, available IDs and physical connectors/endpoints.
- [x] 2.2 Replace authoritative single-route state with normalized `routes: output_id -> input_id | None` state.
- [x] 2.3 Preserve a compatibility projection for existing single-output consumers only where needed during migration.
- [x] 2.4 Add exact fixed topology profiles for IN1804, IN1808 and IN1608 xi.
- [x] 2.5 Add exact fixed topology profiles only for approved DTP CrossPoint models.
- [x] 2.6 Add first-generation XTP frame-identity selection followed by read-only topology discovery from matrix dimensions plus installed-board evidence.
- [x] 2.7 Add XTP II frame-identity selection followed by read-only topology discovery from matrix dimensions plus installed-board evidence.
- [x] 2.8 Ensure empty board slots do not renumber later available input/output IDs.
- [x] 2.9 Add tests proving topology discovery never uses route mutation/probing.

## 3. SIS command profiles

- [x] 3.1 Extract common Extron Matrix transport/session concerns from model-specific command semantics without changing credential/failure ownership.
- [x] 3.2 Preserve the existing IN1804 working command profile.
- [x] 3.3 Add IN1808 route/name/status profile.
- [x] 3.4 Add IN1608 xi route/name/status profile.
- [x] 3.5 Add common multi-output CrossPoint AV-routing syntax only where DTP/XTP/XTP II documentation proves it shared.
- [x] 3.6 Add exact DTP CrossPoint model identity/topology capability resolution and reject DTP2/DTP3/unknown DTP generations.
- [x] 3.7 Add first-generation XTP board-aware capability resolution with output-HDCP read `W0<N>HDCP` / all-output `W0*HDCP`.
- [x] 3.8 Add XTP II board-aware capability resolution as a distinct profile; do not implement output-HDCP until exact official command/decoder evidence is approved.
- [x] 3.9 Implement per-profile command-generation tests using exact handler strings before transport terminators are appended.

## 4. Signal, HDCP and optional diagnostics

- [x] 4.1 Normalize signal presence by authoritative available input IDs.
- [x] 4.2 Implement IN1804/IN1808 input-HDCP raw mapping separately from IN1608/approved-DTP/XTP/XTP-II input mapping.
- [x] 4.3 Keep output-HDCP command generation and normalization separate by family: DTP != XTP != unproven XTP II.
- [x] 4.4 Preserve HDCP authorization/configuration separately from actual input HDCP state.
- [x] 4.5 Preserve working IN1804 input/output names and temperature behavior.
- [x] 4.6 Add only documented IN1808 and IN1608 name/temperature reads.
- [x] 4.7 Add DTP CrossPoint names only where documented for the approved exact family/model set.
- [x] 4.8 Leave XTP/XTP II naming and DTP/XTP/XTP II temperature unavailable if authoritative evidence is absent at implementation time.
- [x] 4.9 Leave XTP II output-HDCP unavailable if its exact command/decoder is still unproven.

## 5. Parser and normalized state

- [x] 5.1 Generalize Matrix parser output to a multi-output route map.
- [x] 5.2 Normalize signal, HDCP, names and topology into deterministic per-ID dictionaries/lists.
- [x] 5.3 Reject malformed/out-of-range route/status evidence rather than guessing from arbitrary digits.
- [x] 5.4 Represent untied outputs explicitly as `None`/untied state.
- [x] 5.5 Preserve current single-output IN1804 room presentation through the normalized model.

## 6. GUI

- [x] 6.1 Render one route column for every authoritative `available_output_id`.
- [x] 6.2 Use authoritative output names as headers where supported and deterministic `Output <id>` fallback otherwise.
- [x] 6.3 Show one input active on multiple outputs when the route map requires it.
- [x] 6.4 Show an untied output with no selected input.
- [x] 6.5 Preserve current non-actionable behavior for stale, failed, blocked, unsupported and unproven rows/cells.
- [x] 6.6 Route cell actions through the existing Matrix controller/application-shell intent boundary, generalized to include both input ID and output ID.
- [x] 6.7 Do not create GUI route columns from duplicate physical connectors that share one logical route.

## 7. Routing mutation lifecycle

- [x] 7.1 Generalize route intent/mutation from fixed output 1 to explicit `(input_id, output_id)` context.
- [x] 7.2 Preserve no-blind-replay semantics for state-changing Matrix route commands after a possible-send boundary.
- [x] 7.3 Reconcile a successful mutation with an authoritative read of the targeted output route.
- [x] 7.4 Reject mutation for unavailable input/output IDs before send.
- [x] 7.5 Support authoritative CrossPoint untie state without inventing a source input.

## 8. Factory / discovery / model registration

- [x] 8.1 Register IN1808 and IN1608 xi as supported Matrix models through exact capability profiles rather than raw substring-only behavior.
- [x] 8.2 Register only approved DTP CrossPoint exact models.
- [x] 8.3 Register first-generation XTP CrossPoint frame identities to the XTP profile.
- [x] 8.4 Register XTP II frame identities separately to the XTP II profile.
- [x] 8.5 Ensure an unsupported or unknown Extron model/generation does not silently inherit a nearest-looking profile.

## 9. Regression tests

- [x] 9.1 IN1804 existing full-status command sequence remains hardware-compatible.
- [x] 9.2 IN1804 current route read `!` remains accepted and route mutation remains `<I>*1!`.
- [x] 9.3 IN1808 route read/set use `1!` and `<I>*1!`.
- [x] 9.4 IN1608 xi route read/set use `!` and `<I>!`.
- [x] 9.5 CrossPoint route read/set use `<O>!` and `<I>*<O>!` across multiple outputs.
- [x] 9.6 CrossPoint untie `0*<O>!` normalizes to an untied output.
- [x] 9.7 HDCP raw value `1/2` is decoded differently for required profile groups.
- [x] 9.8 DTP output-HDCP generates `WO<N>HDCP`; first-generation XTP generates `W0<N>HDCP`; XTP II sends no speculative output-HDCP query while unproven.
- [x] 9.9 XTP/XTP II board gaps preserve original logical IDs in GUI and route validation.
- [x] 9.10 Unsupported/unproven name/temperature/output-HDCP capability sends no speculative SIS command.
- [x] 9.11 Dynamic GUI creates exactly one route column per available logical output.
- [x] 9.12 Existing room Matrix IN1804 behavior remains unchanged for a 4-input/1-output record.

## 10. Post-implementation validation

- [x] 10.1 Run focused Matrix/unit tests for capability discovery, parser normalization, GUI projection and mutation lifecycle.
- [x] 10.2 Run the full offline suite.
- [x] 10.3 Re-run `openspec validate extron-matrix-model-expansion --strict`.
- [x] 10.4 Re-run `openspec validate --all --strict`.
- [x] 10.5 Re-run `git diff --check` and scope review.
- [x] 10.6 Perform independent production diff review with CRITICAL/HIGH/MEDIUM/LOW findings.
- [ ] 10.7 Hardware-check at least one representative newly supported family/profile where devices are available; unavailable hardware validation must be explicitly recorded, never fabricated.

## 11. Archive and merge

- [ ] 11.1 Reconcile task state against implementation evidence and explicitly deferred follow-up work.
- [ ] 11.2 Prove disposable archive applicability again before real archive.
- [ ] 11.3 Archive only after strict validation passes.
- [ ] 11.4 Re-run strict validation after archive.
- [ ] 11.5 Merge only after final post-archive review and tests pass.

## 12. Inventory converter handoff remediation

- [x] 12.1 Extend the existing normalized component evidence rules with the approved Matrix canonical runtime models.
- [x] 12.2 Preserve complete-match-set and two-field ambiguity fail-closed semantics; add required/forbidden discriminators only where needed for DTP 84/84 4K and XTP/XTP II separation.
- [x] 12.3 Add real converter-path and exact-runtime-dispatch regression coverage for all approved Matrix inventory models.
- [x] 12.4 Run focused inventory, Matrix, full-suite, OpenSpec strict, and Git hygiene validation before independent review.

## 13. IN1804 hardware regression remediation

- [x] 13.1 Normalize only documented IN1804-series `1I` wire identities to the existing canonical IN1804 profile.
- [x] 13.2 Preserve canonical expected-model comparison, strict unknown-identity rejection, and DTP/XTP/XTP II identity rules.
- [x] 13.3 Add production-path full-refresh, framing, parser, and presentation regressions for the baseline IN1804 profile.
- [ ] 13.4 Re-run read-only hardware validation when the observed IN1804 is reachable; do not perform route mutation.

## 14. IN1808 identity and IN1804 HDCP remediation

- [x] 14.1 Add only documented IN1808 wire aliases and preserve expected-model fail-closed behavior.
- [x] 14.2 Normalize legacy IN1804 HDCP list/scalar evidence into canonical per-ID Matrix state.
- [ ] 14.3 Re-run read-only IN1804 and IN1808 hardware validation when devices are reachable; do not route-switch.

## 15. Identity hardening reconciliation

- [x] 15.1 Normalize only documented command-specific `1I` and `N` identity response grammars before closed resolution.
- [x] 15.2 Cover tagged framing, canonical mismatch, and DTP/XTP/XTP II fail-closed identity behavior.
- [ ] 15.3 Re-run read-only tagged-response and IN1608 xi hardware validation when devices are reachable.

## 16. Matrix hardware-QA GUI remediation

- [x] 16.1 Preserve room one-shot exact `diagnostic_model` propagation through Matrix worker and handler as completed in the preceding remediation.
- [x] 16.2 Add worker/handler production-path regression: DTP CrossPoint 86 4K begins identity with `N`; IN1608 xi with `1I`; XTP II CrossPoint 3200 with `N`.
- [x] 16.3 Make Matrix worker connection status model-aware, with a neutral backward-compatible label when no expected model is supplied.
- [x] 16.4 Preserve canonical input-HDCP true, confirmed false, and unknown semantics in standalone Matrix presentation.
- [x] 16.5 Preserve canonical input-HDCP true, confirmed false, and unknown semantics in room Matrix presentation, including Qt semantic data/tooltips.
- [x] 16.6 Prove current temperature reaches the existing standalone and room Matrix fields and unavailable current data clears the standalone field.
- [x] 16.7 Reconcile GUI requirements and preserve the separate hardware-acquisition/GUI-presentation QA gates.
- [ ] 16.8 Re-run read-only hardware QA for IN1804, IN1808, DTP CrossPoint 86 4K, and IN1608 xi when devices are reachable; begin DTP verification with `N` after authentication and do not mutate routes.

## 17. Matrix remediation follow-up

- [x] 17.1 Remove the room Matrix Quick Actions/reboot placeholders; place the lifecycle-gated Local Refresh intent in the exact-row IP field with stable accessible identity.
- [x] 17.2 Hide the Matrix card title, expand the routing surface, and use equal-width dynamic route columns derived only from `available_output_ids`.
- [x] 17.3 Render centered canonical HDCP indicators, retain distinct Qt semantics for positive/negative/absent/unknown, and keep Signal UNKNOWN non-positive.
- [x] 17.4 Project canonical row MAC/serial/IP into the Matrix information card without adding unproven device reads; clear unavailable device-polled fields.
- [x] 17.5 Prove an unresolved/unsupported exact Matrix identity fails closed and a terminal protocol failure with blocked physical retirement releases the next room row without credential fallback.
- [x] 17.6 Run focused Matrix/room regressions and strict OpenSpec validation.
- [ ] 17.7 Perform read-only hardware QA when fixtures are available; do not record PASS without a run and do not mutate routes.

## 18. Review-remediation follow-up

- [x] 18.1 Map only exact documented legacy identity `60-1381-23` to `DTP CrossPoint 108 4K`; retain mismatch and adjacent-token fail-closed behavior.
- [x] 18.2 Split the retired Matrix Quick Actions root contract into a REMOVED requirement and the compact dashboard contract into an ADDED requirement.
- [x] 18.3 Preserve immediate logical terminal handling for Matrix protocol failures while retiring detached handlers asynchronously without restoring authority.
- [x] 18.4 Distinguish active, known-other, explicitly untied, and UNKNOWN route evidence in room Matrix cells and intent gating.
- [x] 18.5 Restore approved Russian dynamic table headings and stable Matrix information-value object identities; prove snapshot clearing and hidden routing header.
- [x] 18.6 Add focused Matrix controller, Matrix UI, identity, and room-orchestration regression coverage; run full offline validation.
- [ ] 18.7 Perform read-only hardware QA when fixtures are available; do not record PASS without a run and do not mutate routes.

## 19. Retirement-serialization follow-up

- [x] 19.1 Preserve immediate Matrix logical terminal notification while recording a conflicting-device retirement barrier before detached physical cleanup.
- [x] 19.2 Gate new Matrix acquisition, credential fallback, route, and reconciliation transport authority on prior retirement completion; fail closed after the bounded barrier timeout.
- [x] 19.3 Keep legacy IN1804 missing route evidence semantically UNKNOWN and non-actionable.
- [x] 19.4 Reconcile historical `60-1381-23` wording with the documented exact alias and add focused retirement/legacy-route regressions.
- [ ] 19.5 Perform read-only hardware QA when fixtures are available; do not record PASS without a run and do not mutate routes.

## 20. Atomic Matrix retirement publication remediation

- [x] 20.1 Publish the per-endpoint retirement barrier while the serialized Matrix ownership boundary is still held, before scheduling detached physical cleanup.
- [x] 20.2 Reject a waiter that becomes stale while awaiting retirement before credential lookup, handler construction, connection, or SIS I/O, without emitting a replacement-context failure.
- [x] 20.3 Add deterministic regressions for the detach-to-background publication gap and stale-after-wait acquisition rejection.
- [x] 20.4 Run focused controller, Matrix UI, room-equipment and profile regressions; then run the full offline suite and strict OpenSpec validation.
- [ ] 20.5 Re-run read-only hardware validation when representative Matrix hardware is available; do not mutate routes.

## 21. Non-blocking Matrix invalidation remediation

- [x] 21.1 Make GUI-facing invalidation publish only short-lived retirement metadata and enqueue background retirement work.
- [x] 21.2 Keep retirement acquisition-gating and ensure no waiter holds the serialized owner lock while waiting for retirement completion.
- [x] 21.3 Add deterministic blocked-I/O invalidation and target/revision replacement regressions; preserve stale waiter and no-replay coverage.
- [x] 21.4 Run focused/full software and strict OpenSpec validation; hardware remains unchecked.

## 22. Stale connect and target-owner remediation

- [x] 22.1 Retire a handler that becomes stale while `connect()` is in progress without publishing persistent session or keepalive authority.
- [x] 22.2 Preserve the actual owner identity across public A→B replacement and same-IP credential-revision replacement.
- [x] 22.3 Add deterministic stale-connect, public target replacement, and revision replacement regressions.
- [x] 22.4 Run focused/full software and strict OpenSpec validation; hardware remains unchecked.
