# Design: Equipment page inventory context

## Context

The equipment inventory already has two distinct runtime responsibilities:

```text
canonical device identity and diagnostic routing evidence
room identity, room display, and room VIP context
```

Schema v3 additionally stores the passive network-connection fields:

```text
switch_ip_address
switch_port
```

They are produced offline by the approved network-workbook reconciliation, validated by the runtime loader, and exposed on immutable `EquipmentRecord` values. Existing indexes remain keyed only by device IP and room identity.

The GUI currently has four registered equipment-page kinds:

```text
codec
matrix
pdu
audio_dsp
```

Each screen already owns an existing information card:

```text
codec      -> Основная информация
matrix     -> Информация об устройстве
pdu        -> Информация об устройстве
audio_dsp  -> Информация об устройстве
```

The switch connection belongs in those existing cards. A separate switch card would make one item of device identity context appear structurally different from MAC, firmware, model, IP, protocol, and other device-information fields and would require page-specific placement rules outside the current screen composition.

The approved non-PDU room contract is already centralized. `VCSDiagnosticApp` attaches one shared `RoomInformationBlock` to every registered non-PDU screen and publishes room address/VIP state from immutable inventory independently of device network success.

The codec screen has a lifecycle conflict with that shell-owned widget. `CodecScreen.update_parameters_display()` removes all widgets from `param_layout`, then creates only its information and control cards. Because the shared room block is inserted into the same layout after initial screen construction, the next codec rebuild hides and schedules it for deletion. The normal diagnostic refresh calls the rebuild after selecting the codec screen and does not reattach the room block. The resulting presentation violates the existing registry-wide room contract even though focused tests prove only the initial attachment path.

## Goals

1. Show canonical switch IP and switch port in the existing information card of every registered equipment page.
2. Keep inventory presentation independent of device request success, credentials, transport, handlers, workers, and controllers.
3. Preserve exact zero/one/many inventory lookup semantics and fail closed on ambiguity.
4. Preserve useful unique partial connection data without inventing missing values.
5. Keep equipment screens rendering-only and free of inventory lookup authority.
6. Preserve or restore exactly one shared codec room block through every codec rebuild.
7. Bind both inventory presentations to current model, normalized IP, inventory snapshot, page context, and application generation so stale publications cannot restore old values.
8. Cover every registered page and the real codec refresh/rebuild path with regression tests.

## Non-goals

- Do not change either source workbook contract.
- Do not change MAC-only network reconciliation or ambiguity rules.
- Do not change canonical schema v1, v2, or v3 field shapes or snapshot identity.
- Do not add a switch-IP or switch-port inventory index or public query.
- Do not connect to a switch, validate switch reachability, obtain switch credentials, inspect link state, or perform switch management.
- Do not infer a device's switch connection from its current runtime MAC, device response, room, model, row order, or another source.
- Do not put inventory lookup, multiplicity interpretation, stale-result authority, or lifecycle generation inside equipment screens.
- Do not add switch fields to handler, worker, controller, parser, or transport result payloads.
- Do not change diagnostic dispatch, credentials, fallback, request retry, related-codec selection, room aggregation, PDU control, Matrix routing, or audio polling.
- Do not redesign the shared room presentation or PDU's dedicated room-and-codec section.
- Do not modify operational workbooks or `equipment_inventory.local.json` in the repository.
- Do not use or update Graphify artifacts.

## Authority and ownership

The ownership model shall be:

```text
offline importer
  owns source parsing and MAC-only reconciliation
  publishes canonical nullable switch fields

EquipmentInventory
  owns immutable canonical records and existing lookup semantics

application/composition layer
  owns current model/IP/snapshot/page generations
  resolves one current record through existing device-IP lookup
  converts canonical fields into non-secret display values
  rejects stale publication

registered equipment screen
  owns only the placement and rendering of two rows
  does not query inventory or decide multiplicity
```

The switch connection presentation is not a device-observation result. The shell must not wait for a device worker/controller to succeed before publishing it and must not clear a valid current presentation merely because a device request fails.

The shared codec room block remains shell-owned. The codec screen may rebuild codec-owned cards, but that rebuild must either preserve shell-owned layout children or invoke a focused shell/layout boundary that restores exactly one current shared block after rebuilding. The screen must not become the room resolver or room-publication authority.

## Inventory switch connection resolution

For a valid normalized current device IP, the application shall use the existing `EquipmentInventory.find_by_ip()` lookup.

The outcome is:

```text
inventory unavailable
    -> switch IP = —
    -> switch port = —

invalid or absent current IP
    -> switch IP = —
    -> switch port = —

zero matching records
    -> switch IP = —
    -> switch port = —

multiple matching records
    -> switch IP = —
    -> switch port = —

one matching record
    -> display switch_ip_address independently
    -> display switch_port independently
    -> null field becomes —
```

The application shall not narrow multiple records by current selected model, `device_kind`, MAC, room, or any presentation state. Existing diagnostic model resolution may have its own exact contract, but it does not authorize a different ambiguity rule for inventory display.

Schema-v1 and schema-v2 records are already adapted by the loader to null switch fields. Their display therefore naturally follows the same one-record/null-value rule and does not require source-version branching in screens.

`switch_port` remains opaque display text. The GUI must not parse, normalize again, abbreviate by vendor grammar, split chassis/slot/port components, or infer link state.

## Presentation model

Implementation should use one focused immutable or value-like presentation result, or an equivalent explicit scalar callback boundary, with at least:

```text
switch_ip_address: str | None
switch_port: str | None
```

It may also carry a safe internal resolution status needed for tests and lifecycle diagnostics, provided that status does not expose workbook rows or become a device failure category.

Screens shall receive only safe scalar presentation values. They shall render null as `—` and shall not receive the complete inventory, an `EquipmentRecord`, source workbook evidence, import issues, or mutable canonical state.

No modal warning is required for missing switch data. The existing room block may continue to show its own safe inventory/room message under its approved contract, but the new switch rows do not add a second modal or convert the screen to error state.

## Registry-wide placement contract

Every `EquipmentPageRegistration` shall be covered, including the dedicated PDU page. Each registered screen must expose exactly one row labelled:

```text
IP коммутатора
```

and exactly one row labelled:

```text
Порт коммутатора
```

Both rows must be children of that screen's existing information card, not the shared room block, PDU related-room card, controls card, routing table, outlet table, or a newly introduced standalone card.

The expected placement is:

```text
CodecScreen
  existing Основная информация card

MatrixScreen
  existing Информация об устройстве card

PDUScreen
  existing Информация об устройстве card

AudioDSPScreen
  existing Информация об устройстве card
```

The registry remains the completeness authority. Tests must enumerate registrations rather than maintain an independent hand-written list that could omit a future supported page.

The specific row order inside each existing card may respect that screen's current layout, but the two fields should remain adjacent and visually identifiable as one connection pair. Page-specific layout differences must not change their labels, source, null behavior, or lifecycle.

## Application-owned publication lifecycle

The switch presentation shall use an application-owned binding equivalent to:

```text
(
  exact current diagnostic model,
  normalized current device IP,
  inventory snapshot identity,
  registered page context,
  inventory-presentation generation,
)
```

A credential-context revision is not required as source authority because switch fields are not credential-derived. If implementation reuses a broader existing immutable equipment context containing a credential revision, that must not make credentials semantically authoritative for the switch values.

The shell shall invalidate prior switch presentation when any of these change:

- accepted diagnostic model;
- normalized IP input;
- registered page context;
- loaded inventory snapshot identity or inventory availability;
- application shutdown or screen destruction where relevant.

The new current presentation may be resolved synchronously from immutable inventory. If publication is queued or asynchronous, acceptance must confirm the complete current binding and generation before rendering.

Device refresh start, reachability progress, handler acquisition, worker/controller result, request error, request completion, interactive codec action, PDU mutation, Matrix route, and audio polling are not publication authorities. They must neither overwrite current inventory values with device payload data nor restore stale values.

A device screen rebuild may require the shell to re-render the already current presentation into newly created row widgets. That is a view replacement, not a new inventory authority. Re-rendering must use the current binding and must not accept an older record or stale callback.

## Codec room block rebuild contract

The codec rebuild defect must be corrected at the ownership boundary rather than hidden by a test-only attachment.

After every `CodecScreen.update_parameters_display()` execution that can occur during model change or diagnostic refresh:

- exactly one shared `RoomInformationBlock` must be attached to the codec page;
- it must remain at the bottom after codec-owned information and control cards;
- its address, VIP state, and safe status must match the current application-owned room binding;
- the rebuild must not leave a hidden or pending-deletion duplicate;
- repeated rebuilds must not multiply blocks;
- the block must remain independent from codec worker success or failure.

Two implementation patterns are acceptable:

1. make codec rebuild remove/recreate only codec-owned widgets while preserving shell-owned children; or
2. let codec rebuild replace its content, then call a focused shell/layout hook that safely reattaches one block and republishes current room presentation.

The implementation must choose one explicit ownership model and test it. It must not rely on the initial constructor attachment remaining alive accidentally.

The same post-rebuild integration point may republish the current switch connection values into the codec's recreated information rows. Room and switch presentation can share a lifecycle trigger while remaining distinct presentation models and contracts.

## Interaction with device data clearing

Existing `clear_data()` methods may reset device-observed fields while a request is loading. They must not interpret inventory rows as device-observed data.

The implementation shall ensure one of these equivalent outcomes:

- inventory-backed rows are excluded from generic device-data clearing; or
- the shell immediately re-renders current inventory values after a screen rebuild/clear under the same current binding.

A transient `—` during synchronous widget reconstruction is acceptable only if no event-loop-visible stale or incorrect context is published. The final current page after rebuild/clear must show current inventory values without requiring device network success.

The shared room block already marks its value labels as non-device data. The new switch rows should have an equally explicit ownership marker or focused render path so future generic `findChildren(... data_field ...)` clearing does not silently erase them.

## Security and privacy

Switch IP and switch port are operational inventory metadata but are not credentials. They may appear on the intended local equipment page.

The change must still preserve data minimization:

- do not log or display complete inventory records;
- do not expose workbook paths, source rows, reconciliation evidence, or unrelated device records;
- do not add switch values to public errors unless a focused debug contract already permits the exact displayed values;
- do not include credentials, sessions, cookies, tokens, or handler objects in the presentation model;
- do not infer or expose switch management capability.

Credential redaction and device secret-isolation contracts remain unchanged.

## Compatibility

Valid schema-v1 and schema-v2 snapshots remain supported. Their adapted null switch fields display as `—`.

Valid schema-v3 snapshots keep the same identity, validation, ordering, and existing indexes. This change reads fields already present on the selected record and does not alter publication or deterministic digest behavior.

Existing equipment diagnostics remain usable when inventory is unavailable or unresolved. Missing switch presentation is non-blocking and must not open fallback model selection, disable controls, or change successful device request state.

The PDU related-room/codec section remains unchanged. It may show room and related codec data while the PDU information card independently shows the PDU record's connected switch fields.

## Expected implementation boundaries

Expected production files:

```text
gui/main_window.py
gui/equipment_pages.py
gui/screens/codec_screen.py
gui/screens/matrix_screen.py
gui/screens/pdu_screen.py
gui/screens/audio_dsp_screen.py
```

One focused pure resolver or presentation-model module may be added under `core/` or `gui/` if it prevents lifecycle logic from being duplicated. Any such module must remain UI-independent if placed under `core/` and must not become a new inventory authority.

Expected focused tests:

```text
tests/test_equipment_room_context_gui.py
```

and either a new focused equipment-inventory presentation GUI test module or an existing directly related GUI test module selected during implementation.

Out of scope files and artifacts include:

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

Enumerate every current equipment-page registration and prove:

- each screen contains exactly one `IP коммутатора` row;
- each screen contains exactly one `Порт коммутатора` row;
- both rows belong to the existing device-information card;
- PDU remains included despite its dedicated room placement;
- no separate switch card is introduced.

### Value resolution

Use synthetic immutable inventories to prove:

- one schema-v3 record with both fields displays both exact values;
- one record with only switch IP displays that IP and `—` for port;
- one record with only port displays `—` for switch IP and exact opaque port text;
- one record with both null displays two `—` values;
- schema-v1/v2 adapted records display two `—` values;
- unavailable inventory, invalid IP, no record, and multiple records display two `—` values;
- multiple records are not narrowed by selected model or another field.

### Lifecycle and stale protection

Prove:

- accepted model/IP context publishes values without device network I/O;
- changing IP clears/replaces old values immediately;
- replacing the inventory snapshot republishes from the new snapshot;
- an old publication cannot restore values after model/IP/page/snapshot change;
- device request error does not clear current switch values;
- device result payload cannot overwrite the inventory values;
- repeated screen activation does not duplicate rows.

### Codec regression

Exercise the real codec path that calls `update_parameters_display()` during diagnostic startup and prove:

- exactly one room block exists afterward;
- it is the bottom shared block;
- current address and VIP remain visible;
- current switch rows exist and display current inventory values;
- repeated rebuilds keep exactly one block and one row pair;
- codec worker failure does not remove room or switch presentation.

The test must not rely only on initial window construction or `_accept_test_diagnostic_model()` without the rebuild step.

### Regression protection

Run existing inventory loader/importer, room-context GUI, PDU enrichment, diagnostic dispatch, Matrix, codec, PDU, and audio-DSP tests. No real workbook, device, credential file, or network access is required.

## Validation and rollout

1. Review and approve this architecture-only change.
2. Implement only the approved display and rebuild contracts with focused regression coverage.
3. Run focused GUI/inventory tests, the full offline Python suite, `git diff --check`, strict change validation, and strict all validation.
4. Publish focused implementation commits without rewriting history and keep the PR Draft.
5. Independently validate the exact remote implementation HEAD in a clean detached worktree.
6. Perform a disposable archive-applicability check because the change adds and modifies root-spec requirements.
7. Archive only after independent approval, inspect the archive/root-spec delta, repeat post-archive checks, and publish a dedicated archive commit.
8. Merge only after direct user authorization and a fresh check of current remote archive HEAD, PR state, and current `master`.
