## 1. Architecture and implementation preparation

- [ ] 1.1 Read `RULES.md` before implementation, confirm the implementation checkout is based on the current published `agent/pdu-room-codec-enrichment` branch, and preserve unrelated work.
- [ ] 1.2 Read this change's `proposal.md`, `design.md`, all delta specs, and the archived/root specifications for `equipment-inventory-snapshot`, PDU lifecycle, codec interactive recovery, credentials, request lifecycle, and device diagnostics.
- [ ] 1.3 Run `\.\openspec.cmd validate pdu-room-codec-enrichment --strict` before implementation and stop for architecture correction if the approved artifacts are invalid or contradictory.
- [ ] 1.4 Do not change canonical inventory schema v1, add a primary-codec field, or introduce real organization inventory data.
- [ ] 1.5 Keep production changes within the approved PDU-room-codec enrichment scope; do not refactor unrelated generic device lifecycles.

## 2. Pure room and codec resolution model

- [ ] 2.1 Add immutable non-secret resolution/result types in a focused core/application-domain module.
- [ ] 2.2 Implement a pure `RoomContextResolver` or equivalent that consumes only `EquipmentInventory` and a canonical PDU IP.
- [ ] 2.3 Resolve PDU IP with exact zero/one/many semantics from `find_by_ip`; do not filter duplicate-IP ambiguity into an apparent single PDU match.
- [ ] 2.4 Return `PDU_NOT_FOUND` for zero IP records and `AMBIGUOUS_PDU_IP` for more than one IP record.
- [ ] 2.5 Require the one IP record to have canonical `device_kind == "pdu"`; otherwise return `PDU_KIND_MISMATCH`.
- [ ] 2.6 Require authoritative non-null `room_id`; otherwise return `ROOM_UNRESOLVED` without falling back to `room_name`.
- [ ] 2.7 Resolve room codecs with `find_by_room_and_kind(room_id, "video_codec")`; return `CODEC_NOT_FOUND` for zero and `AMBIGUOUS_CODEC` for more than one.
- [ ] 2.8 For exactly one codec, return `CODEC_IP_MISSING` when canonical IP is absent and `CODEC_UNSUPPORTED` when `diagnostic_model` is absent or is not an application-supported VCS codec model.
- [ ] 2.9 Return `RESOLVED` only for one canonical PDU record, authoritative room ID, and one supported codec model/IP.
- [ ] 2.10 Derive room display name from all records under the authoritative room ID; do not select one conflicting name. Emit a safe `ROOM_NAME_CONFLICT` warning while continuing by room ID.
- [ ] 2.11 Include the inventory `snapshot_id`, selected PDU/codec record IDs, room ID, safe display fields, codec model, and codec IP in the immutable resolved context.
- [ ] 2.12 Keep the resolver free of Qt, credentials, provider reads, handler/worker construction, logging of complete records, and network I/O.

## 3. Focused enrichment controller and context lifecycle

- [ ] 3.1 Add `PDURoomCodecEnrichmentController` or an equivalently focused application/composition controller.
- [ ] 3.2 Give it independent enrichment generation and operation identity; do not use generic `_active_request`, global `current_worker`, PDU refresh/mutation lane identity, or the user codec interactive generation as its authority.
- [ ] 3.3 Capture immutable non-secret PDU generation, accepted refresh operation ID, PDU model/IP, PDU credential-context revision, inventory snapshot ID, resolved room/codec identity, and related-codec credential-context revision.
- [ ] 3.4 Start a new generation for every accepted user PDU refresh, including repeat Refresh for the same model/IP.
- [ ] 3.5 Invalidate current enrichment on PDU model/IP/context change, relevant credential configuration change, inventory replacement if later supported, and application shutdown.
- [ ] 3.6 Clear or reset the related-room presentation when a new PDU context supersedes the old one.
- [ ] 3.7 Treat inventory load failure as `INVENTORY_UNAVAILABLE` with the existing safe load category/message; do not block application startup or PDU diagnostics.
- [ ] 3.8 Publish only accepted current structured results to the presentation callback; stale resolution/session outcomes must not render or persist state.

## 4. Accepted PDU refresh integration

- [ ] 4.1 Add a focused non-secret accepted-user-refresh callback/signal boundary from `PDUController` to application composition.
- [ ] 4.2 Publish only after `PDUController` accepts a current successful refresh result.
- [ ] 4.3 Include only PDU generation, refresh operation ID, model, IP, and non-secret credential-context revision or equivalent context identity.
- [ ] 4.4 Do not include credentials, candidate lists, outlet data, worker/handler/session objects, cookies, tokens, or transports in the callback.
- [ ] 4.5 Do not publish enrichment trigger for refresh-lane reconciliation whose `originating_mutation_operation_id` is non-null.
- [ ] 4.6 Ensure stale PDU callbacks and PDU errors cannot start enrichment.
- [ ] 4.7 Keep inventory lookup, room resolution, codec selection, codec credentials, and codec network I/O outside `PDUController`.

## 5. Independent related-codec read-only session lane

- [ ] 5.1 Compose a separate `InteractiveSessionController` instance or an equivalent isolated serialized read-only session component owned by the enrichment controller.
- [ ] 5.2 Do not reuse `CodecScreen.interactive_controller` and do not call generic codec `refresh_*` methods.
- [ ] 5.3 Do not switch `device_combo`, `ip_entry`, current screen, generic codec progress dialogs, or terminal windows for automatic related-codec work.
- [ ] 5.4 Submit one quiet `READ_ONLY` status operation for the resolved codec and keep all handler/network work off the Qt GUI thread.
- [ ] 5.5 Recheck session/enrichment currentness before handler acquisition and before first network I/O when those phases are separate.
- [ ] 5.6 Drop queued stale work with zero handler construction, transport open, or device request.
- [ ] 5.7 Ignore in-flight stale result, error, progress, finished, credential-index, and profile callbacks.
- [ ] 5.8 Close/invalidate the bounded related-codec handler/session on success, terminal error, supersession, credential-context change, and application shutdown.
- [ ] 5.9 Ensure cleanup runs on the execution lane that owns the handler/session and does not block the Qt GUI thread on network cleanup.

## 6. Codec status normalization

- [ ] 6.1 Add a focused related-codec status adapter or equivalent model dispatch for the supported VCS codec models.
- [ ] 6.2 Reuse existing handlers and parser classes where available; do not duplicate login, transport fallback, or protocol implementation.
- [ ] 6.3 Normalize at least `call_status` and `presentation_status` from the existing authoritative status response for Huawei TE20, Huawei TE40, CloudLink Bar 310, and Polycom RPG 310 where those fields are supported.
- [ ] 6.4 Keep complete raw codec status internal; send only the narrow normalized related-codec presentation model to `PDUScreen`.
- [ ] 6.5 Represent an unavailable authoritative field as unavailable/unknown rather than inventing a value or interpreting arbitrary text.
- [ ] 6.6 Classify unsupported adapter/method behavior as `UNAVAILABLE` or `PROTOCOL_FAILED` according to the structured contract; do not report success with fabricated values.

## 7. Credential and transport policy

- [ ] 7.1 Resolve the complete related-codec credential chain in application composition before handler/session construction.
- [ ] 7.2 Start from the valid saved credential index for the exact codec model/IP and use the supported saved connection profile first.
- [ ] 7.3 Keep one assigned credential across every supported transport attempt.
- [ ] 7.4 Advance monotonically to the next credential only after structured confirmed new-login `AuthenticationError`; do not use `is_authentication_error()`, message substrings, HTTP-code text, empty data, or malformed responses as retry authority.
- [ ] 7.5 Do not let the handler, status adapter, or worker inspect or advance the candidate chain.
- [ ] 7.6 Apply at most one reconnect cycle and one replay of the read-only status operation; recovery must not recurse.
- [ ] 7.7 Commit successful credential index and connection profile only after an accepted current final status success.
- [ ] 7.8 Do not persist credential/profile memory for stale, partial, resolution-only, unsupported, or failed outcomes.
- [ ] 7.9 Expose at most attempt position/total in public status; never expose profile names or credential values.

## 8. PDU screen presentation

- [ ] 8.1 Add a related-room/codec section to the existing `PDUScreen`; do not create a separate PDU or codec screen for this feature.
- [ ] 8.2 Render pending/loading, authoritative room ID, unambiguous room name, codec model/IP, call status, and presentation/broadcast status.
- [ ] 8.3 Render safe structured states for inventory unavailable, PDU not found, ambiguous PDU IP, kind mismatch, unresolved room, codec not found, ambiguous codec, missing codec IP, unsupported codec, authentication failure, transport failure, protocol failure, and unavailable status.
- [ ] 8.4 Keep enrichment errors inline and non-modal.
- [ ] 8.5 Preserve accepted PDU connection state, device information, outlet table, refresh/mutation lanes, and controls when enrichment is unavailable or fails.
- [ ] 8.6 Make `PDUScreen` rendering-only for enrichment: no inventory query, multiplicity classification, credential resolution, worker/session creation, network I/O, stale authority, or credential/profile persistence.
- [ ] 8.7 Ensure stale old-room values cannot reappear after a new PDU context is shown.

## 9. Safe observability and data isolation

- [ ] 9.1 Keep credentials, candidate dictionaries, profile names, cookies, Session IDs, CSRF/access tokens, handlers, workers, sessions, and transports out of public contexts, signals, logs, errors, dialogs, and screen models.
- [ ] 9.2 Do not emit complete raw codec responses, complete inventory records, complete snapshots, or source workbook rows when a narrow result is sufficient.
- [ ] 9.3 Use only synthetic equipment, room, IP, codec, and credential fixtures in tests.
- [ ] 9.4 Confirm no real organization workbook or `equipment_inventory.local.json` content is added to Git.

## 10. Focused regression coverage

- [ ] 10.1 Test inventory unavailable does not block or invalidate successful PDU diagnostics.
- [ ] 10.2 Test PDU IP zero, one, and many matches, including one PDU plus one non-PDU sharing the IP, with no first-match/filtering shortcut.
- [ ] 10.3 Test one IP record of non-PDU kind returns `PDU_KIND_MISMATCH`.
- [ ] 10.4 Test missing authoritative room ID does not fall back to room name.
- [ ] 10.5 Test room codec zero, one, and many matches and prove `codecs[0]` is never selected for ambiguity.
- [ ] 10.6 Test codec missing IP and unsupported/null/non-codec `diagnostic_model` outcomes.
- [ ] 10.7 Test conflicting room names preserve room-ID resolution but select no authoritative display name.
- [ ] 10.8 Test only accepted current user PDU refresh starts enrichment.
- [ ] 10.9 Test PDU mutation reconciliation refresh does not start enrichment.
- [ ] 10.10 Test repeated PDU Refresh supersedes prior enrichment even for the same model/IP.
- [ ] 10.11 Test a user interactive session for codec A remains active and untouched while automatic enrichment reads codec B.
- [ ] 10.12 Test related-codec work does not replace generic `_active_request`, global `current_worker`, selected device/IP, current screen, or generic codec dialogs.
- [ ] 10.13 Test queued stale related-codec work is dropped before handler acquisition and network I/O.
- [ ] 10.14 Test in-flight stale callbacks cannot update room/codec presentation, PDU state, or credential/profile memory.
- [ ] 10.15 Test transport fallback retains one credential and saved supported profile is attempted first.
- [ ] 10.16 Test only structured confirmed authentication rejection advances the candidate plan; authentication-looking strings and established-session invalidation do not directly advance it.
- [ ] 10.17 Test candidate advancement is monotonic without wrap-around and handler/adapter cannot iterate credentials.
- [ ] 10.18 Test accepted final success persists exact codec model/IP credential index and profile; stale/error/partial outcomes do not.
- [ ] 10.19 Test one bounded read-only recovery/replay and no recursive reconnect.
- [ ] 10.20 Test normalized call and presentation status for every supported related-codec model using fake handlers/raw parser fixtures.
- [ ] 10.21 Test inline failure rendering preserves PDU outlet data, connection state, and mutation controls and opens no modal dialog.
- [ ] 10.22 Test application shutdown invalidates enrichment and closes the dedicated related-codec session resources safely.
- [ ] 10.23 Test all public payloads and diagnostics remain secret/session-free and do not contain complete inventory or raw status dumps.

## 11. Validation and handoff

- [ ] 11.1 Run focused resolver, controller, credential, status-adapter, PDU-integration, and screen tests.
- [ ] 11.2 Run `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] 11.3 Run `\.\openspec.cmd validate pdu-room-codec-enrichment --strict`.
- [ ] 11.4 Run `\.\openspec.cmd validate --all --strict`.
- [ ] 11.5 Run `git diff --check`.
- [ ] 11.6 Confirm implementation changes no canonical inventory schema-v1 fields or query semantics and commits no real inventory data.
- [ ] 11.7 Confirm implementation does not reuse the user codec interactive-controller instance, generic codec refresh authority, or string authentication heuristics.
- [ ] 11.8 Update implementation evidence, commit, and push the complete implementation before requesting independent validation. The implementation session must not issue its own final `APPROVE`.
