# Design: Equipment page inventory context

## Context

The equipment inventory already owns canonical device identity, diagnostic routing evidence, room identity, room display, and room VIP context. Schema v3 additionally stores two nullable network-connection fields:

```text
switch_ip_address
switch_port
```

They are produced offline by the approved MAC-only reconciliation, validated by the runtime loader, and exposed on immutable `EquipmentRecord` values. Existing indexes remain keyed only by device IP and room identity.

The current root requirement is named `Schema-v3 switch fields are passive runtime data in this change`. That name no longer describes the intended future contract because this change permits one controlled runtime consumer: application-owned, display-only GUI presentation. The requirement therefore must be renamed to `Schema-v3 switch fields are non-authoritative runtime inventory metadata`; the full updated contract is supplied under the new name in `MODIFIED Requirements`.

The GUI has four registered equipment-page kinds:

```text
codec
matrix
pdu
audio_dsp
```

Each screen already owns an information card:

```text
codec      -> Основная информация
matrix     -> Информация об устройстве
pdu        -> Информация об устройстве
audio_dsp  -> Информация об устройстве
```

The switch connection belongs in those existing cards. It is inventory context, not device-observed status.

The approved non-PDU room contract is application-owned. `VCSDiagnosticApp` attaches one shared `RoomInformationBlock` to registered non-PDU pages and publishes address/VIP state independently of device network success.

### Confirmed codec lifecycle defect

The normal codec diagnostic path already attempts to restore room presentation after rebuilding:

```text
CodecScreen.update_parameters_display()
-> target_screen.clear_data()
-> _publish_current_equipment_room_context("request_started")
```

The failure occurs earlier at the widget ownership boundary:

```text
CodecScreen.update_parameters_display()
-> removes every item from param_layout
-> hide()
-> deleteLater()
```

This schedules the shell-owned room block for `QEvent.DeferredDelete`. The subsequent publication calls `_ensure_shared_room_block()`, but the pending-deletion block still has a parent until Qt processes deferred deletion. The current parent-based liveness check therefore accepts the stale object as current and republishes into it. On the next event-loop turn Qt deletes that object, leaving the codec page without a room block.

The defect is not an absent publication call. It is deletion of a shell-owned widget plus a false liveness decision during the interval between `deleteLater()` and `DeferredDelete` processing.

## Goals

1. Show canonical switch IP and switch port in the existing information card of every registered equipment page.
2. Keep switch presentation independent of device request success, credentials, transports, handlers, workers, controllers, and controls.
3. Preserve exact zero/one/many inventory lookup semantics and fail closed on ambiguity.
4. Preserve useful unique partial connection data without inventing missing values.
5. Keep equipment screens rendering-only and free of inventory lookup authority.
6. Preserve exactly one live shell-owned codec room block through every codec rebuild.
7. Prevent any widget scheduled for deferred deletion from being accepted as current presentation state.
8. Bind inventory presentation to current model, normalized IP, inventory snapshot, page context, and application generation so stale publications cannot restore old values.
9. Exercise the real codec diagnostic-start lifecycle and flush deferred-deletion events before final assertions.

## Non-goals

- Do not change either workbook contract.
- Do not change MAC-only reconciliation, ambiguity rules, schema shapes, loader validation, snapshot identity, or inventory indexes.
- Do not add a switch-IP or switch-port inventory index or public query.
- Do not connect to a switch, validate reachability, obtain switch credentials, inspect link state, or perform switch management.
- Do not infer switch connection from runtime MAC, device response, room, model, row order, or another source.
- Do not put inventory lookup, multiplicity interpretation, stale-result authority, or lifecycle generation inside screens.
- Do not add switch fields to handler, worker, controller, parser, or transport result payloads.
- Do not change diagnostic dispatch, credentials, fallback, retries, related-codec selection, room aggregation, PDU control, Matrix routing, or audio polling.
- Do not redesign the shared room presentation or PDU dedicated room-and-codec section.
- Do not modify operational workbooks, `equipment_inventory.local.json`, root specs before archive, archived changes, or Graphify artifacts.

## Authority and ownership

```text
offline importer
  owns source parsing and MAC-only reconciliation
  publishes canonical nullable switch fields

EquipmentInventory
  owns immutable records and existing lookup semantics

application/composition layer
  owns current model/IP/snapshot/page generations
  resolves one record through existing device-IP lookup
  converts canonical fields into safe scalar presentation
  rejects stale publication

registered equipment screen
  owns placement and rendering of two rows only
  does not query inventory or decide multiplicity

VCSDiagnosticApp / equipment-page composition
  owns the shared RoomInformationBlock

CodecScreen
  owns codec information/control cards only
  must not delete shell-owned layout children
```

The switch connection is not a device-observation result. The application must not wait for a worker/controller result before publishing it and must not clear valid current values merely because a device request fails.

## Inventory switch resolution

For a valid normalized current device IP, the application shall call existing `EquipmentInventory.find_by_ip()`.

```text
inventory unavailable       -> — / —
invalid or absent IP        -> — / —
zero matching records       -> — / —
multiple matching records   -> — / —
one matching record         -> display each field independently
null field                  -> —
```

The application shall not narrow multiple records by selected model, `device_kind`, MAC, room, completeness, row order, or presentation state.

Schema-v1 and schema-v2 records are already adapted to null switch fields. Screens require no source-version branching.

`switch_port` remains opaque text. The GUI must not parse vendor grammar, split chassis/slot/interface components, normalize it again, or infer link state.

## Presentation model

Implementation should use one focused immutable/value-like result, or an equivalent scalar boundary, containing at least:

```text
switch_ip_address: str | None
switch_port: str | None
```

A safe internal resolution status may be carried for tests and lifecycle diagnostics, but it must not expose workbook rows or become a device failure category.

Screens receive only safe scalar values. They do not receive the inventory, `EquipmentRecord`, source evidence, import issues, or mutable canonical state.

Missing values are non-blocking and render as `—`. No modal warning is introduced.

## Registry-wide placement

Every `EquipmentPageRegistration`, including PDU, must expose exactly one row labelled `IP коммутатора` and exactly one row labelled `Порт коммутатора`.

Both rows must belong to the existing information card:

```text
CodecScreen    -> Основная информация
MatrixScreen   -> Информация об устройстве
PDUScreen      -> Информация об устройстве
AudioDSPScreen -> Информация об устройстве
```

They must not be placed in the shared room block, PDU related-room section, controls, routing/outlet tables, or a new standalone card. The rows remain adjacent. Registry enumeration is the completeness authority for tests.

## Application-owned publication lifecycle

The switch presentation shall use a binding equivalent to:

```text
(
  exact current diagnostic model,
  normalized current device IP,
  inventory snapshot identity,
  registered page context,
  inventory-presentation generation,
)
```

The shell invalidates prior presentation when model, IP, page, snapshot identity/availability, shutdown, or relevant screen destruction changes.

Device refresh, reachability progress, credentials, handler acquisition, worker/controller result, request error/completion, interactive actions, and device controls are not publication authorities.

A screen rebuild may require re-rendering the already current values into replacement row widgets. That is view reconstruction, not a new inventory lookup authority.

## Codec room-block ownership contract

The implementation shall use one explicit ownership model:

> `CodecScreen.update_parameters_display()` removes and recreates only codec-owned widgets. It SHALL preserve the shell-owned `RoomInformationBlock` and SHALL NOT call `hide()` or `deleteLater()` on it.

A generic "remove everything and reattach later" implementation is not approved because the existing failure demonstrates that a widget between `deleteLater()` and `DeferredDelete` can still have a parent and be mistaken for live state.

The codec rebuild boundary must therefore distinguish codec-owned cards/stretch items from shell-owned layout children before removal. After every rebuild used by model selection or diagnostic refresh:

- exactly one live `RoomInformationBlock` is attached;
- it is the last widget in the codec content layout, after codec-owned cards;
- the screen's `shared_room_information_block` reference points to that exact live object;
- its address, VIP state, and safe status match the current application-owned room binding;
- no hidden, detached, pending-deletion, or deleted duplicate remains accepted as current;
- repeated rebuilds do not multiply blocks;
- subsequent publications target only the current live block;
- room presentation remains independent of codec worker success or failure.

`_ensure_shared_room_block()` may still recover from a genuinely missing or already deleted block, but it must not be the normal repair mechanism for codec rebuilds and must not accept a stale/pending-deletion object as current.

The same post-rebuild integration point may re-render switch values into recreated codec information rows. Room and switch values may share a lifecycle trigger while remaining separate presentation contracts.

## Device data clearing

Existing `clear_data()` methods may clear device-observed fields while a request loads. Inventory-backed rows must either be excluded from generic device-data clearing or immediately re-rendered from the current binding during the same synchronous rebuild/clear lifecycle.

The final event-loop-visible page must show current inventory values without waiting for network success. Inventory-owned labels should have an explicit ownership marker or focused render path so generic `data_field` clearing cannot permanently erase them.

## Deferred-delete regression contract

Every regression test that exercises codec reconstruction shall process Qt deferred deletion before final assertions:

```python
QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
QApplication.processEvents()
```

This flush occurs after each rebuild under test, including repeated rebuilds.

After the flush, tests shall verify:

1. the pre-rebuild shell-owned block was not scheduled for deletion and remains live, or—only for a genuine missing/deleted recovery case—the stale block is deleted and no longer referenced;
2. exactly one live `RoomInformationBlock` exists under the codec content widget;
3. that live block is the last widget in the layout;
4. `shared_room_information_block` points to that exact object;
5. its address and VIP values match the current binding;
6. later publication updates only that live object;
7. a stale/deleted object cannot receive or display a subsequent publication;
8. exactly one switch-row pair remains after reconstruction.

A test that asserts only before processing `DeferredDelete` is insufficient evidence.

## Security and privacy

Switch IP and port are operational inventory metadata, not credentials, and may appear on the intended local equipment page. Data minimization still applies:

- do not log/display complete inventory records;
- do not expose workbook paths, source rows, reconciliation evidence, or unrelated records;
- do not add switch values to public errors without an existing focused debug contract;
- do not include credentials, sessions, tokens, cookies, or handler objects in presentation values;
- do not infer or expose switch management capability.

Credential redaction and secret-isolation contracts remain unchanged.

## Compatibility

Valid schema-v1/v2 snapshots remain supported and display `—` through existing null adaptation. Schema-v3 identity, validation, ordering, and indexes remain unchanged.

Diagnostics remain usable when inventory is unavailable or unresolved. Missing switch presentation does not trigger model fallback, disable controls, or change device request state.

The PDU related-room/codec section remains unchanged while the PDU information card independently displays the PDU record's switch metadata.

## Expected implementation scope

Expected production files:

```text
gui/main_window.py
gui/equipment_pages.py
gui/screens/codec_screen.py
gui/screens/matrix_screen.py
gui/screens/pdu_screen.py
gui/screens/audio_dsp_screen.py
```

One focused pure resolver/presentation module may be added under `core/` or `gui/` when justified. A module under `core/` must remain UI-independent and must not become a new authority.

Expected focused tests include `tests/test_equipment_room_context_gui.py` and one directly related switch-presentation GUI module.

Out of scope:

```text
tools/import_equipment_inventory.py
operational workbooks
equipment_inventory.local.json
handlers/**
transport/**
credentials.local.json
openspec/specs/** before archive
openspec/changes/archive/**
graphify-out/**
.graphify-local/**
```

## Test strategy

### Registry and placement

Enumerate every current registration and prove both rows exist exactly once in the existing information card, including PDU, with no standalone card.

### Value resolution

Using synthetic immutable inventories, prove full values, IP-only, port-only, both-null, schema-v1/v2 adaptation, unavailable inventory, invalid IP, zero match, and multiple matches. Prove ambiguity is not narrowed.

### Lifecycle and stale protection

Prove publication without network I/O, immediate replacement on model/IP/page/snapshot change, rejection of stale publications, persistence through device request errors, protection from device payload overwrite, and no duplicate rows.

### Codec regression

Exercise the real diagnostic-start path that calls `update_parameters_display()`. After every rebuild, flush `DeferredDelete` and verify the complete ownership/liveness assertions above. Repeat rebuilds and include codec request failure.

### Regression protection

Run focused room/switch GUI tests, affected codec/Matrix/PDU/audio-DSP tests, the full offline suite, `git diff --check`, strict change validation, and strict all validation.

## Validation and rollout

1. Publish this corrected architecture and keep the PR Draft.
2. On the exact new remote architecture HEAD, run `git diff --check`, `.\openspec.cmd validate equipment-page-inventory-context --strict`, and `.\openspec.cmd validate --all --strict`, recording versions and exit codes.
3. Repeat independent architecture review; implementation starts only after `APPROVE`.
4. Implement only the approved ownership and presentation contracts with regression coverage.
5. Independently validate the exact remote implementation HEAD in a clean detached worktree.
6. Because the change uses `RENAMED Requirements` and `MODIFIED Requirements`, perform a disposable archive-applicability check outside the feature branch before `READY FOR ARCHIVE`.
7. Archive only after independent approval, inspect the archive/root-spec diff, repeat post-archive checks, and publish a dedicated archive commit.
8. Merge only after direct user authorization and a fresh check of current remote archive HEAD, PR state, and current `master`.
