## 1. Architecture and implementation preparation

- [ ] 1.1 Read `RULES.md` before implementation, confirm the implementation checkout is based on the current published `agent/pdu-room-codec-enrichment` branch, and preserve unrelated work.
- [ ] 1.2 Read this change's `proposal.md`, `design.md`, every delta spec, and archived/root specifications for `equipment-inventory-snapshot`, PDU lifecycle, codec interactive recovery, credentials, request lifecycle, and device diagnostics.
- [ ] 1.3 Run `.\openspec.cmd validate pdu-room-codec-enrichment --strict` before implementation and stop for architecture correction if the approved artifacts are invalid or contradictory.
- [ ] 1.4 Do not change canonical inventory schema v1, add a primary-codec field, or introduce real organization inventory data.
- [ ] 1.5 Keep production changes within approved PDU-room-codec enrichment scope; do not refactor unrelated generic device lifecycles.

## 2. Pure room and codec resolution model

- [ ] 2.1 Add immutable non-secret resolution/result types in a focused core/application-domain module.
- [ ] 2.2 Implement a pure `RoomContextResolver` or equivalent that consumes only `EquipmentInventory` and canonical PDU IP.
- [ ] 2.3 Resolve PDU IP with exact zero/one/many semantics from `find_by_ip`; do not filter duplicate-IP ambiguity into an apparent single PDU match.
- [ ] 2.4 Return `PDU_NOT_FOUND` for zero IP records and `AMBIGUOUS_PDU_IP` for more than one.
- [ ] 2.5 Require the one IP record to have canonical `device_kind == "pdu"`; otherwise return `PDU_KIND_MISMATCH`.
- [ ] 2.6 Require authoritative non-null `room_id`; otherwise return `ROOM_UNRESOLVED` without falling back to `room_name`.
- [ ] 2.7 Resolve codecs with `find_by_room_and_kind(room_id, "video_codec")`; return `CODEC_NOT_FOUND` for zero and `AMBIGUOUS_CODEC` for more than one.
- [ ] 2.8 For one codec, return `CODEC_IP_MISSING` when canonical IP is absent and `CODEC_UNSUPPORTED` when `diagnostic_model` is absent or unsupported.
- [ ] 2.9 Return `RESOLVED` only for one canonical PDU record, authoritative room ID, and one supported codec model/IP.
- [ ] 2.10 Derive room display name from every record under the authoritative room ID; do not select a conflicting name. Emit safe `ROOM_NAME_CONFLICT` while continuing by room ID.
- [ ] 2.11 Include inventory `snapshot_id`, selected PDU/codec record IDs, room ID, safe display fields, codec model, and codec IP in immutable resolved context.
- [ ] 2.12 Keep resolver free of Qt, credentials, provider reads, handler/worker construction, complete-record logging, and network I/O.

## 3. Focused enrichment controller and context lifecycle

- [ ] 3.1 Add `PDURoomCodecEnrichmentController` or an equivalently focused application/composition controller.
- [ ] 3.2 Give it independent enrichment generation and operation identity; do not use generic `_active_request`, global `current_worker`, PDU refresh/mutation lane identity, or user codec interactive generation as enrichment authority.
- [ ] 3.3 Capture immutable non-secret PDU generation, accepted refresh operation ID, PDU model/IP, PDU credential revision, inventory snapshot ID, resolved room/codec identity, and codec credential revision.
- [ ] 3.4 Start a new enrichment generation for every accepted user PDU refresh, including repeat Refresh for the same PDU and same resolved codec.
- [ ] 3.5 Invalidate current enrichment immediately on PDU model/IP/context change, PDU credential-context change, start of new/repeat PDU Refresh, explicit PDU context invalidation/deactivation, relevant codec credential change, inventory replacement if later supported, and shutdown.
- [ ] 3.6 Clear or reset related-room presentation at PDU-context supersession time, before replacement PDU success is known.
- [ ] 3.7 Keep old presentation cleared when replacement PDU refresh fails and produces no accepted-success trigger.
- [ ] 3.8 Treat inventory load failure as `INVENTORY_UNAVAILABLE` with existing safe load category/message; do not block startup or PDU diagnostics.
- [ ] 3.9 Publish only accepted current structured results; stale resolution/session outcomes must not render or persist state.

## 4. PDU lifecycle integration

- [ ] 4.1 Add a focused non-secret accepted-user-refresh callback/signal from `PDUController` to application composition.
- [ ] 4.2 Publish accepted refresh only after `PDUController` accepts current successful user refresh.
- [ ] 4.3 Include only PDU generation/revision, refresh operation ID, model, IP, and non-secret credential revision or equivalent identity.
- [ ] 4.4 Do not include credentials, candidate lists, outlet data, complete PDU result, worker/handler/session objects, cookies, tokens, or transports.
- [ ] 4.5 Do not publish accepted enrichment trigger for reconciliation whose `originating_mutation_operation_id` is non-null.
- [ ] 4.6 Ensure stale PDU callbacks and PDU errors cannot start enrichment.
- [ ] 4.7 Add a separate focused non-secret PDU-context supersession callback or equivalent application method owned by `PDUController`.
- [ ] 4.8 Publish/invoke supersession no later than PDU model change, IP change, PDU credential-context change, new/repeat user Refresh start, explicit context invalidation/deactivation, and shutdown.
- [ ] 4.9 Ensure the shell only forwards PDU-owned supersession facts and does not maintain a second PDU generation or read widgets as background freshness authority.
- [ ] 4.10 Keep inventory lookup, room resolution, codec selection, codec credentials, and codec network I/O outside `PDUController`.

## 5. Independent related-codec read-only session lane

- [ ] 5.1 Compose a separate `InteractiveSessionController` instance or equivalent isolated serialized read-only component owned by enrichment controller.
- [ ] 5.2 Do not reuse `CodecScreen.interactive_controller` and do not call generic codec `refresh_*` methods.
- [ ] 5.3 Do not switch `device_combo`, `ip_entry`, current screen, generic codec progress dialogs, or terminal windows.
- [ ] 5.4 Submit one quiet `READ_ONLY` status operation and keep all handler/network work off the Qt GUI thread.
- [ ] 5.5 Before every new enrichment session activation, call `invalidate_context()` on the dedicated session or use a reviewed equivalent force-rollover mechanism.
- [ ] 5.6 Perform force rollover even when codec model/IP, credential identities, start index, and saved profile are unchanged; plain equal-identity `activate_context()` reuse is forbidden.
- [ ] 5.7 Recheck both enrichment and session currentness before handler acquisition and before first network I/O when phases are separate.
- [ ] 5.8 Drop queued stale work with zero handler factory/acquisition, transport open, or device request.
- [ ] 5.9 Ignore in-flight stale result, error, progress, finished, credential-index, and profile callbacks.
- [ ] 5.10 Close/invalidate bounded related-codec resources on success, terminal error, PDU/enrichment supersession, credential change, inventory replacement, and shutdown.
- [ ] 5.11 Ensure cleanup runs on the owning execution lane and does not block Qt GUI thread on network cleanup.

## 6. Codec status normalization

- [ ] 6.1 Add a focused related-codec status adapter or equivalent model dispatch for supported VCS codec models.
- [ ] 6.2 Reuse existing handlers and parser classes where available; do not duplicate login, transport fallback, or protocol implementation.
- [ ] 6.3 Normalize at least `call_status` and `presentation_status` for Huawei TE20, Huawei TE40, CloudLink Bar 310, and Polycom RPG 310 where authoritatively supported.
- [ ] 6.4 Keep complete raw codec status internal; send only narrow normalized presentation to `PDUScreen`.
- [ ] 6.5 Represent unavailable authoritative fields as unavailable/unknown rather than inventing values.
- [ ] 6.6 Classify unsupported adapter/method behavior as `UNAVAILABLE` or `PROTOCOL_FAILED`; do not report fabricated success.

## 7. Credential and transport policy

- [ ] 7.1 Resolve complete related-codec credential chain in application composition before handler/session construction.
- [ ] 7.2 Start from valid saved credential index for exact codec model/IP and try supported saved profile first.
- [ ] 7.3 Keep one assigned credential across every supported transport attempt.
- [ ] 7.4 Advance monotonically only after structured confirmed new-login `AuthenticationError`; do not use `is_authentication_error()`, message substrings, HTTP-code text, empty data, or malformed responses.
- [ ] 7.5 Do not let handler, adapter, or worker inspect or advance candidate chain.
- [ ] 7.6 Apply at most one reconnect cycle and one read-only replay; recovery must not recurse.
- [ ] 7.7 Commit successful credential index/profile only after accepted current final status success.
- [ ] 7.8 Persist nothing for stale, partial, resolution-only, unsupported, or failed outcomes.
- [ ] 7.9 Expose at most attempt position/total publicly; never expose profile names or credential values.

## 8. PDU screen presentation

- [ ] 8.1 Add a related-room/codec section to existing `PDUScreen`; do not create a separate screen.
- [ ] 8.2 Render neutral/pending state, room ID, unambiguous room name, codec model/IP, call status, and presentation/broadcast status.
- [ ] 8.3 Render safe structured states for inventory unavailable, PDU not found, ambiguous IP, kind mismatch, unresolved room, codec not found, ambiguous codec, missing codec IP, unsupported codec, authentication, transport, protocol, and unavailable outcomes.
- [ ] 8.4 Keep enrichment errors inline and non-modal.
- [ ] 8.5 Preserve accepted PDU connection state, device information, outlets, lanes, and controls when enrichment fails.
- [ ] 8.6 Keep `PDUScreen` rendering-only for enrichment.
- [ ] 8.7 Reset related-room presentation immediately on PDU-context supersession and ensure stale values cannot reappear.

## 9. Safe observability and data isolation

- [ ] 9.1 Keep credentials, candidate dictionaries, profile names, cookies, Session IDs, CSRF/access tokens, handlers, workers, sessions, and transports out of public contexts, signals, logs, errors, dialogs, and screen models.
- [ ] 9.2 Do not emit complete raw codec responses, complete inventory records/snapshots, or source workbook rows when narrow result is sufficient.
- [ ] 9.3 Use only synthetic equipment, room, IP, codec, and credential fixtures in tests.
- [ ] 9.4 Confirm no real organization workbook or `equipment_inventory.local.json` content is added to Git.

## 10. Focused regression coverage

- [ ] 10.1 Test inventory unavailable does not block or invalidate successful PDU diagnostics.
- [ ] 10.2 Test PDU IP zero/one/many, including one PDU plus one non-PDU sharing IP, with no filtering shortcut.
- [ ] 10.3 Test one non-PDU IP record returns `PDU_KIND_MISMATCH`.
- [ ] 10.4 Test missing room ID does not fall back to room name.
- [ ] 10.5 Test codec zero/one/many and prove `codecs[0]` is never selected.
- [ ] 10.6 Test missing codec IP and unsupported/null/non-codec `diagnostic_model`.
- [ ] 10.7 Test conflicting room names preserve room-ID resolution but select no authoritative name.
- [ ] 10.8 Test only accepted current user PDU refresh starts enrichment.
- [ ] 10.9 Test mutation reconciliation does not start enrichment.
- [ ] 10.10 Test repeat Refresh supersedes prior enrichment even for same PDU model/IP.
- [ ] 10.11 Test queued old related-codec status, repeat same PDU, same codec, same credential chain/index/profile: old work is dropped before handler factory and performs zero network I/O.
- [ ] 10.12 Test PDU model/IP/credential change and new Refresh start invalidate enrichment before replacement success.
- [ ] 10.13 Test replacement PDU refresh failure leaves old room/codec presentation cleared and old work stale.
- [ ] 10.14 Test user interactive codec A remains active while automatic enrichment reads codec B.
- [ ] 10.15 Test related-codec work does not replace `_active_request`, global `current_worker`, selected device/IP, screen, or generic dialogs.
- [ ] 10.16 Test general queued stale work is dropped before handler acquisition/network I/O.
- [ ] 10.17 Test in-flight stale callbacks cannot update presentation, PDU state, or credential/profile memory.
- [ ] 10.18 Test transport fallback retains one credential and saved supported profile is first.
- [ ] 10.19 Test only structured confirmed authentication rejection advances candidates; auth-looking strings and session invalidation do not directly advance.
- [ ] 10.20 Test candidate advancement is monotonic without wrap-around and handler/adapter cannot iterate.
- [ ] 10.21 Test accepted final success persists exact model/IP index/profile; stale/error/partial outcomes do not.
- [ ] 10.22 Test one bounded read-only recovery/replay and no recursive reconnect.
- [ ] 10.23 Test normalized call/presentation status for every supported related-codec model using fakes/parser fixtures.
- [ ] 10.24 Test inline failures preserve PDU data and controls and open no modal dialog.
- [ ] 10.25 Test shutdown invalidates enrichment and closes resources safely.
- [ ] 10.26 Test all public payloads remain secret/session-free and omit complete inventory/raw status dumps.

## 11. Validation and handoff

- [ ] 11.1 Run focused resolver, controller, lifecycle, credential, status-adapter, PDU-integration, and screen tests.
- [ ] 11.2 Run `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] 11.3 Run `.\openspec.cmd validate pdu-room-codec-enrichment --strict`.
- [ ] 11.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 11.5 Run `git diff --check`.
- [ ] 11.6 Confirm implementation changes no inventory schema-v1 fields/query semantics and commits no real inventory data.
- [ ] 11.7 Confirm implementation does not reuse user codec interactive-controller instance, generic codec refresh authority, or string authentication heuristics.
- [ ] 11.8 Update implementation evidence, commit, and push complete implementation before requesting independent validation. The implementation session must not issue its own final `APPROVE`.
