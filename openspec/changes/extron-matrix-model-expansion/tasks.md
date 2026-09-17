# Tasks: Extron matrix model expansion

## 1. Architecture and evidence

- [ ] 1.1 Reconfirm current IN1804 production behavior and preserve the hardware-confirmed command baseline without semantic regression.
- [ ] 1.2 Record official SIS evidence for IN1808 and IN1608 xi commands used by this change only: identity, temperature, names, signal presence, HDCP, route read/set.
- [ ] 1.3 Record official SIS evidence for DTP CrossPoint, XTP CrossPoint and XTP II CrossPoint commands used by this change only.
- [ ] 1.4 Keep unsupported/unproven diagnostics explicitly unavailable; do not add speculative SIS reads.
- [ ] 1.5 Resolve the initial implementation scope for IN1808 Loop Out from evidence and product intent without treating physical connectors as independent routes by default.

## 2. Capability and topology model

- [ ] 2.1 Introduce a normalized Matrix capability/topology representation that distinguishes logical routing IDs, available IDs and physical connectors/endpoints.
- [ ] 2.2 Replace authoritative single-route state with normalized `routes: output_id -> input_id | None` state.
- [ ] 2.3 Preserve a compatibility projection for existing single-output consumers only where needed during migration.
- [ ] 2.4 Add exact fixed topology profiles for IN1804, IN1808 and IN1608 xi.
- [ ] 2.5 Add exact fixed topology profiles for supported DTP CrossPoint models.
- [ ] 2.6 Add read-only XTP topology discovery from matrix dimensions plus installed-board evidence.
- [ ] 2.7 Add read-only XTP II topology discovery from matrix dimensions plus installed-board evidence.
- [ ] 2.8 Ensure empty board slots do not renumber later available input/output IDs.
- [ ] 2.9 Add tests proving topology discovery never uses route mutation/probing.

## 3. SIS command profiles

- [ ] 3.1 Extract common Extron Matrix transport/session concerns from model-specific command semantics without changing credential/failure ownership.
- [ ] 3.2 Preserve the existing IN1804 working command profile.
- [ ] 3.3 Add IN1808 route/name/status profile.
- [ ] 3.4 Add IN1608 xi route/name/status profile.
- [ ] 3.5 Add common multi-output CrossPoint AV routing profile for DTP/XTP/XTP II where the documented SIS syntax is shared.
- [ ] 3.6 Add DTP CrossPoint fixed-model identity/topology capability resolution.
- [ ] 3.7 Add XTP board-aware capability resolution.
- [ ] 3.8 Add XTP II board-aware capability resolution as a distinct profile from first-generation XTP.
- [ ] 3.9 Implement per-profile command generation tests using exact handler strings before transport terminators are appended.

## 4. Signal, HDCP and optional diagnostics

- [ ] 4.1 Normalize signal presence by authoritative available input IDs.
- [ ] 4.2 Implement IN1804/IN1808 input-HDCP raw mapping separately from IN1608/DTP/XTP/XTP II mapping.
- [ ] 4.3 Keep output-HDCP normalization separate from input-HDCP normalization.
- [ ] 4.4 Preserve HDCP authorization/configuration separately from actual input HDCP state.
- [ ] 4.5 Preserve working IN1804 input/output names and temperature behavior.
- [ ] 4.6 Add only documented IN1808 and IN1608 name/temperature reads.
- [ ] 4.7 Add DTP CrossPoint names where documented.
- [ ] 4.8 Leave XTP/XTP II naming and DTP/XTP/XTP II temperature unavailable if authoritative evidence is still absent at implementation time.

## 5. Parser and normalized state

- [ ] 5.1 Generalize Matrix parser output to a multi-output route map.
- [ ] 5.2 Normalize signal, HDCP, names and topology into deterministic per-ID dictionaries/lists.
- [ ] 5.3 Reject malformed/out-of-range route/status evidence rather than guessing from arbitrary digits.
- [ ] 5.4 Represent untied outputs explicitly as `None`/untied state.
- [ ] 5.5 Preserve current single-output IN1804 room presentation through the normalized model.

## 6. GUI

- [ ] 6.1 Render one route column for every `available_output_id`.
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

- [ ] 8.1 Register IN1808 and IN1608 xi as supported Matrix models through capability profiles rather than raw substring-only behavior.
- [ ] 8.2 Register supported DTP CrossPoint exact models/family resolution.
- [ ] 8.3 Register XTP CrossPoint family/frame resolution.
- [ ] 8.4 Register XTP II CrossPoint family/frame resolution separately from XTP.
- [ ] 8.5 Ensure an unsupported or unknown Extron model does not silently inherit a nearest-looking profile.

## 9. Regression tests

- [ ] 9.1 IN1804 existing full-status command sequence remains hardware-compatible.
- [ ] 9.2 IN1804 current route read `!` remains accepted and route mutation remains `<I>*1!`.
- [ ] 9.3 IN1808 route read/set use `1!` and `<I>*1!`.
- [ ] 9.4 IN1608 xi route read/set use `!` and `<I>!`.
- [ ] 9.5 CrossPoint route read/set use `<O>!` and `<I>*<O>!` across multiple outputs.
- [ ] 9.6 CrossPoint untie `0*<O>!` normalizes to an untied output.
- [ ] 9.7 HDCP raw value `1/2` is decoded differently for the required profile groups.
- [ ] 9.8 XTP/XTP II board gaps preserve original logical IDs in GUI and route validation.
- [ ] 9.9 Unsupported/unproven name/temperature capability sends no speculative SIS command.
- [ ] 9.10 Dynamic GUI creates exactly one route column per available logical output.
- [ ] 9.11 Existing room Matrix IN1804 behavior remains unchanged for a 4-input/1-output record.

## 10. Validation

- [ ] 10.1 Run focused Matrix/unit tests for capability discovery, parser normalization, GUI projection and mutation lifecycle.
- [ ] 10.2 Run the full offline suite.
- [ ] 10.3 Run `openspec validate extron-matrix-model-expansion --strict`.
- [ ] 10.4 Run `openspec validate --all --strict`.
- [ ] 10.5 Run `git diff --check` and scope review.
- [ ] 10.6 Perform independent architecture/production diff review with CRITICAL/HIGH/MEDIUM/LOW findings.
- [ ] 10.7 Hardware-check at least one representative newly supported family/profile where devices are available; any unavailable hardware validation SHALL be explicitly recorded rather than fabricated.

## 11. Archive and merge

- [ ] 11.1 Reconcile task state against implementation evidence and explicitly deferred follow-up work.
- [ ] 11.2 Prove disposable archive applicability before real archive.
- [ ] 11.3 Archive only after strict validation passes.
- [ ] 11.4 Re-run strict validation after archive.
- [ ] 11.5 Merge only after final post-archive review and tests pass.