# Tasks: Extron matrix model expansion

## 1. Architecture, evidence, and PRE-IMPLEMENTATION GATE

- [ ] 1.1 Reconfirm current IN1804 production behavior and preserve the hardware-confirmed command baseline without semantic regression.
- [ ] 1.2 Record official SIS evidence for IN1808 and IN1608 xi commands used by this change only: identity, temperature, names, signal presence, HDCP, route read/set.
- [ ] 1.3 Record official SIS evidence for the exact supported DTP CrossPoint set, first-generation XTP CrossPoint, and XTP II CrossPoint commands used by this change only.
- [ ] 1.4 Confirm DTP scope is limited to DTP CrossPoint 84 plus DTP CrossPoint 82/84/86/108 4K. Explicitly exclude DTP2/DTP3 and legacy analog CrossPoint generations.
- [ ] 1.5 Confirm first-generation XTP output-HDCP uses `W0<N>HDCP` / `W0*HDCP`, while DTP uses `WO<N>HDCP`; keep XTP II output-HDCP UNPROVEN unless separately evidenced.
- [ ] 1.6 Define authoritative XTP-vs-XTP-II frame/profile selection from exact frame identity/part-number evidence before dimension/board decoding.
- [ ] 1.7 Keep unsupported/unproven diagnostics explicitly unavailable; do not add speculative SIS reads.
- [ ] 1.8 Resolve the initial implementation scope for IN1808 Loop Out without treating physical connectors as independent routes by default.
- [ ] 1.9 Reconcile every `MODIFIED Requirements` block against exact current root requirement identity and preserve all existing scenario identities in replacement blocks; genuinely new independent contracts must be `ADDED Requirements`.
- [ ] 1.10 Run `openspec validate extron-matrix-model-expansion --strict` and record PASS.
- [ ] 1.11 Run `openspec validate --all --strict` and record PASS.
- [ ] 1.12 Perform disposable archive-applicability validation and confirm the modified requirements replace current root identities without contradiction or scenario loss.
- [ ] 1.13 Run Git scope/hygiene checks (`git diff --check`, OpenSpec-only changed-file review, exact branch/SHA verification).
- [ ] 1.14 Obtain independent architecture review with CRITICAL=0, HIGH=0 and explicit `IMPLEMENTATION MAY PROCEED: YES`.

**IMPLEMENTATION GATE:** Sections 2 through 9 SHALL NOT begin until tasks 1.10-1.14 are complete and PASS. A validation or review failure returns the change to OpenSpec/design correction; it does not authorize production-code work.

## 2. Capability and topology model

- [ ] 2.1 Introduce a normalized Matrix capability/topology representation that distinguishes logical routing IDs, available IDs and physical connectors/endpoints.
- [ ] 2.2 Replace authoritative single-route state with normalized `routes: output_id -> input_id | None` state.
- [ ] 2.3 Preserve a compatibility projection for existing single-output consumers only where needed during migration.
- [ ] 2.4 Add exact fixed topology profiles for IN1804, IN1808 and IN1608 xi.
- [ ] 2.5 Add exact fixed topology profiles only for approved DTP CrossPoint models.
- [ ] 2.6 Add first-generation XTP frame-identity selection followed by read-only topology discovery from matrix dimensions plus installed-board evidence.
- [ ] 2.7 Add XTP II frame-identity selection followed by read-only topology discovery from matrix dimensions plus installed-board evidence.
- [ ] 2.8 Ensure empty board slots do not renumber later available input/output IDs.
- [ ] 2.9 Add tests proving topology discovery never uses route mutation/probing.

## 3. SIS command profiles

- [ ] 3.1 Extract common Extron Matrix transport/session concerns from model-specific command semantics without changing credential/failure ownership.
- [ ] 3.2 Preserve the existing IN1804 working command profile.
- [ ] 3.3 Add IN1808 route/name/status profile.
- [ ] 3.4 Add IN1608 xi route/name/status profile.
- [ ] 3.5 Add common multi-output CrossPoint AV-routing syntax only where DTP/XTP/XTP II documentation proves it shared.
- [ ] 3.6 Add exact DTP CrossPoint model identity/topology capability resolution and reject DTP2/DTP3/unknown DTP generations.
- [ ] 3.7 Add first-generation XTP board-aware capability resolution with output-HDCP read `W0<N>HDCP` / all-output `W0*HDCP`.
- [ ] 3.8 Add XTP II board-aware capability resolution as a distinct profile; do not implement output-HDCP until exact official command/decoder evidence is approved.
- [ ] 3.9 Implement per-profile command-generation tests using exact handler strings before transport terminators are appended.

## 4. Signal, HDCP and optional diagnostics

- [ ] 4.1 Normalize signal presence by authoritative available input IDs.
- [ ] 4.2 Implement IN1804/IN1808 input-HDCP raw mapping separately from IN1608/approved-DTP/XTP/XTP-II input mapping.
- [ ] 4.3 Keep output-HDCP command generation and normalization separate by family: DTP != XTP != unproven XTP II.
- [ ] 4.4 Preserve HDCP authorization/configuration separately from actual input HDCP state.
- [ ] 4.5 Preserve working IN1804 input/output names and temperature behavior.
- [ ] 4.6 Add only documented IN1808 and IN1608 name/temperature reads.
- [ ] 4.7 Add DTP CrossPoint names only where documented for the approved exact family/model set.
- [ ] 4.8 Leave XTP/XTP II naming and DTP/XTP/XTP II temperature unavailable if authoritative evidence is absent at implementation time.
- [ ] 4.9 Leave XTP II output-HDCP unavailable if its exact command/decoder is still unproven.

## 5. Parser and normalized state

- [ ] 5.1 Generalize Matrix parser output to a multi-output route map.
- [ ] 5.2 Normalize signal, HDCP, names and topology into deterministic per-ID dictionaries/lists.
- [ ] 5.3 Reject malformed/out-of-range route/status evidence rather than guessing from arbitrary digits.
- [ ] 5.4 Represent untied outputs explicitly as `None`/untied state.
- [ ] 5.5 Preserve current single-output IN1804 room presentation through the normalized model.

## 6. GUI

- [ ] 6.1 Render one route column for every authoritative `available_output_id`.
- [ ] 6.2 Use authoritative output names as headers where supported and deterministic `Output <id>` fallback otherwise.
- [ ] 6.3 Show one input active on multiple outputs when the route map requires it.
- [ ] 6.4 Show an untied output with no selected input.
- [ ] 6.5 Preserve current non-actionable behavior for stale, failed, blocked, unsupported and unproven rows/cells.
- [ ] 6.6 Route cell actions through the existing Matrix controller/application-shell intent boundary, generalized to include both input ID and output ID.
- [ ] 6.7 Do not create GUI route columns from duplicate physical connectors that share one logical route.

## 7. Routing mutation lifecycle

- [ ] 7.1 Generalize route intent/mutation from fixed output 1 to explicit `(input_id, output_id)` context.
- [ ] 7.2 Preserve no-blind-replay semantics for state-changing Matrix route commands after a possible-send boundary.
- [ ] 7.3 Reconcile a successful mutation with an authoritative read of the targeted output route.
- [ ] 7.4 Reject mutation for unavailable input/output IDs before send.
- [ ] 7.5 Support authoritative CrossPoint untie state without inventing a source input.

## 8. Factory / discovery / model registration

- [ ] 8.1 Register IN1808 and IN1608 xi as supported Matrix models through exact capability profiles rather than raw substring-only behavior.
- [ ] 8.2 Register only approved DTP CrossPoint exact models.
- [ ] 8.3 Register first-generation XTP CrossPoint frame identities to the XTP profile.
- [ ] 8.4 Register XTP II frame identities separately to the XTP II profile.
- [ ] 8.5 Ensure an unsupported or unknown Extron model/generation does not silently inherit a nearest-looking profile.

## 9. Regression tests

- [ ] 9.1 IN1804 existing full-status command sequence remains hardware-compatible.
- [ ] 9.2 IN1804 current route read `!` remains accepted and route mutation remains `<I>*1!`.
- [ ] 9.3 IN1808 route read/set use `1!` and `<I>*1!`.
- [ ] 9.4 IN1608 xi route read/set use `!` and `<I>!`.
- [ ] 9.5 CrossPoint route read/set use `<O>!` and `<I>*<O>!` across multiple outputs.
- [ ] 9.6 CrossPoint untie `0*<O>!` normalizes to an untied output.
- [ ] 9.7 HDCP raw value `1/2` is decoded differently for required profile groups.
- [ ] 9.8 DTP output-HDCP generates `WO<N>HDCP`; first-generation XTP generates `W0<N>HDCP`; XTP II sends no speculative output-HDCP query while unproven.
- [ ] 9.9 XTP/XTP II board gaps preserve original logical IDs in GUI and route validation.
- [ ] 9.10 Unsupported/unproven name/temperature/output-HDCP capability sends no speculative SIS command.
- [ ] 9.11 Dynamic GUI creates exactly one route column per available logical output.
- [ ] 9.12 Existing room Matrix IN1804 behavior remains unchanged for a 4-input/1-output record.

## 10. Post-implementation validation

- [ ] 10.1 Run focused Matrix/unit tests for capability discovery, parser normalization, GUI projection and mutation lifecycle.
- [ ] 10.2 Run the full offline suite.
- [ ] 10.3 Re-run `openspec validate extron-matrix-model-expansion --strict`.
- [ ] 10.4 Re-run `openspec validate --all --strict`.
- [ ] 10.5 Re-run `git diff --check` and scope review.
- [ ] 10.6 Perform independent production diff review with CRITICAL/HIGH/MEDIUM/LOW findings.
- [ ] 10.7 Hardware-check at least one representative newly supported family/profile where devices are available; unavailable hardware validation must be explicitly recorded, never fabricated.

## 11. Archive and merge

- [ ] 11.1 Reconcile task state against implementation evidence and explicitly deferred follow-up work.
- [ ] 11.2 Prove disposable archive applicability again before real archive.
- [ ] 11.3 Archive only after strict validation passes.
- [ ] 11.4 Re-run strict validation after archive.
- [ ] 11.5 Merge only after final post-archive review and tests pass.