# Design: Inventory-driven diagnostic dispatch

## Context

The approved inventory boundary is:

```text
organization Excel workbook
    -> offline importer
    -> canonical versioned JSON snapshot
    -> immutable indexed EquipmentInventory
    -> application/composition orchestration
```

The importer now publishes one exact supported `diagnostic_model` or null. Runtime inventory lookup preserves multiplicity through `find_by_ip(...)`, but the desktop shell still takes the model from the manual combo box and routes through several overlapping structures:

```text
device_to_screen
EQUIPMENT_PAGE_REGISTRY
model-specific refresh if/elif chain
controller-specific delegates
```

The current page registry already contains the same nine canonical models as the importer registry. It is therefore the correct reviewed source evidence for the closed supported UI surface, but page registration alone does not currently provide one authoritative model-to-lifecycle dispatch decision.

The importer consistency map also incorrectly declares `Aten PE8208AV -> pdu`. The authoritative source-type mapping is independent from diagnostic routing:

```text
Тип модели = Video Conference -> video_codec
Тип модели = БРП              -> pdu
all other values              -> other
```

The deployed Aten and PCS4i source rows legitimately map to `device_kind = other`. Their exact `diagnostic_model` values still route both models to the PDU page and PDU controller.

## Goals

1. Automatically select a supported diagnostic model from one exact canonical inventory record for the entered IP.
2. Preserve zero/one/many lookup semantics and refuse first-match behavior.
3. Route by exact `diagnostic_model`, never by `device_kind` or free-form evidence.
4. Establish one closed reviewable application-owned dispatch registry for page and existing lifecycle selection.
5. Preserve the existing manual diagnostic flow for all unresolved outcomes and explicit operator override.
6. Bind dispatch decisions to the current IP, immutable inventory context, and application generation so stale work cannot change a newer context or start I/O.
7. Keep credentials, transport retry, credential fallback, handler creation, worker lifecycle, controller lifecycle, and GUI rendering in their currently approved ownership boundaries.
8. Correct the false Aten known-model/type consistency expectation without changing canonical data authority.
9. Add synthetic regression coverage proving compatibility with room/VIP presentation and PDU-related-codec enrichment.

## Non-goals

- Do not change the canonical inventory schema or schema version.
- Do not modify the closed importer recognition component rules.
- Do not infer a diagnostic model from `source_model`, `Производитель`, `Модель`, manufacturer strings, substrings, aliases, handler availability, or similar models.
- Do not make `device_kind` a diagnostic-page identifier.
- Do not filter duplicate IP records by kind or supported model before deciding cardinality.
- Do not add an inventory mutation, editor, write-back path, learning mechanism, or JSON rewrite from the GUI.
- Do not remove the existing model selector.
- Do not replace Matrix, PDU, DMP, codec, or Biamp lifecycle implementations with one generic controller.
- Do not move inventory lookup into a screen, handler, worker, session, or transport.
- Do not change credential candidate selection, structured authentication failure rules, transport retry, successful-index persistence, or saved connection-profile policy.
- Do not load Excel or regenerate the deployment snapshot at runtime.
- Do not require or update Graphify output.

## Authority chain

The exact runtime authority is:

```text
current normalized user IP
    -> current immutable EquipmentInventory
    -> find_by_ip(IP) returns tuple[EquipmentRecord, ...]
    -> application classifies zero / one / many
    -> one record's exact diagnostic_model
    -> closed application dispatch registry
    -> assigned page and existing diagnostic lifecycle
```

The application must not add an intermediate inference step. In particular, this is forbidden:

```text
device_kind == pdu
source_model contains TE
manufacturer contains Huawei
handler exists for a nearby model
first supported record among duplicate IP matches
```

`EquipmentInventory` remains a data/query boundary. It returns canonical records and multiplicity; it does not return GUI pages, controller classes, handler factories, fallback models, or user-facing resolution outcomes.

## Closed dispatch registry

The application/composition layer owns one reviewable exact registry with these entries:

| Exact canonical model | Screen key | Existing lifecycle route |
| --- | --- | --- |
| `Huawei TE20` | `codec` | Huawei TE20 refresh route |
| `Huawei TE40` | `codec` | Huawei TE40 refresh route |
| `CloudLink Bar 310` | `codec` | CloudLink Bar 310 refresh route |
| `Polycom RPG 310` | `codec` | Polycom RPG 310 refresh route |
| `Extron IN1804` | `matrix` | `MatrixController` refresh route |
| `Aten PE8208AV` | `pdu` | `PDUController` with exact Aten model context |
| `Extron IPL T PCS4i` | `pdu` | `PDUController` with exact PCS4i model context |
| `Biamp Tesira Forte CI` | `audio_dsp` | existing Biamp polling route |
| `Extron DMP 64 Plus` | `audio_dsp` | `DMPPollingController` refresh route |

The implementation should consolidate or derive the current `device_to_screen`, combo-model population, `EQUIPMENT_PAGE_REGISTRY`, and model-specific refresh selection from one authoritative set where practical. It must at minimum ensure that a model cannot silently route to a page in one registry and a different or absent lifecycle in another.

The registry contains public routing identifiers or focused callables/factories owned by the composition layer. It must not contain credentials, credential lists, successful indexes, handler/session instances, transport objects, cookies/tokens, or mutable worker state.

Registry construction must reject or test against:

- duplicate canonical model entries;
- a selectable manual model with no dispatch entry;
- a dispatch model with no registered screen;
- inconsistent PDU/non-PDU page classification;
- implicit default-to-codec behavior for unknown models.

Unknown exact canonical models are unsupported. They do not fall through to `codec` or the nearest available handler.

## Dispatch trigger and ordering

Inventory-assisted dispatch occurs only as part of a user-initiated diagnostic start from Refresh or the equivalent Enter action. A valid canonical IPv4 address is required before lookup.

Required ordering:

```text
1. Capture a new application dispatch generation.
2. Capture normalized IP and current immutable inventory context.
3. Determine whether a current explicit manual override is active.
4. Otherwise call EquipmentInventory.find_by_ip(normalized_ip).
5. Classify zero / one / many before inspecting record model or kind.
6. For one record, read exact diagnostic_model.
7. Resolve that exact value in the closed dispatch registry.
8. Accept the result only if generation, IP, inventory context, and manual-selection context are still current.
9. Publish the assigned model/page/lifecycle context.
10. Resolve credentials and perform preliminary reachability checks under the assigned model.
11. Start only the existing model-specific controller/refresh lifecycle.
```

Inventory resolution must happen before model-specific credential resolution, ping, handler acquisition, worker creation, or device network I/O. A failed or unresolved inventory lookup is not a device connection failure and must not create an automatic modal network-error dialog.

The inventory is already loaded into memory. Normal lookup must not reread JSON, parse Excel, or perform network I/O on the Qt GUI thread. A bounded in-memory lookup may execute synchronously. If implementation introduces a queued or asynchronous lookup boundary, the same generation and binding checks remain mandatory before publishing its result.

## Resolution cardinality and outcomes

Application code classifies the complete IP tuple before any filtering:

```text
inventory unavailable
    -> INVENTORY_UNAVAILABLE
    -> retain manual selection path

zero IP records
    -> IP_NOT_FOUND
    -> retain manual selection path

more than one IP record
    -> AMBIGUOUS_IP
    -> do not inspect/select a preferred record
    -> retain manual selection path

exactly one IP record with diagnostic_model = null
    -> MODEL_UNMAPPED
    -> retain manual selection path

exactly one IP record with unknown canonical diagnostic_model
    -> MODEL_UNSUPPORTED
    -> retain manual selection path

exactly one IP record with a registered exact diagnostic_model
    -> RESOLVED
    -> assign that registry entry
```

Concrete private enum or class names are not architectural contracts, but the observable distinctions must remain testable. Safe UI presentation may be inline status or another non-secret controlled indication. It must distinguish duplicate IP from not found and unsupported from an invalid IP input.

The application must not treat `device_kind = other` as unresolved. `Aten PE8208AV` and `Extron IPL T PCS4i` resolve to PDU diagnostics solely from their exact registered `diagnostic_model`.

## Manual fallback and override

The current manual selector remains a supported diagnostic entry point.

For unresolved inventory outcomes, the operator's currently selected supported model remains available and existing direct manual diagnostics continue unchanged. Inventory failure must not disable manual diagnostics, alter credentials, or convert the selected model into a canonical database correction.

After an accepted automatic resolution for a normalized IP, an explicit user selection of another registered model creates a manual override bound only to the current request/input context. While that binding remains current, the next diagnostic start uses the explicitly selected model instead of silently replacing it from inventory.

The override contract is:

- the operator must perform an explicit model-selection action;
- the UI must make the inventory/manual discrepancy observable without exposing source rows or secrets;
- the override selects only an existing closed dispatch entry;
- it does not modify `EquipmentRecord`, `EquipmentInventory`, workbook data, or `equipment_inventory.local.json`;
- it does not persist as a new mapping or alias;
- it is invalidated when normalized IP changes, the immutable inventory context changes/reloads, application context is reset, or the application restarts;
- stale automatic lookup results cannot overwrite it;
- changing models supersedes any older device request/controller context under existing lifecycle rules.

Implementation may represent this as a focused selection-source/binding object rather than a public persistence mechanism. The selector text alone is not sufficient freshness authority; application state must know whether selection came from accepted inventory resolution or an explicit operator action.

## Freshness and supersession

Every inventory-assisted start receives a distinct dispatch generation, including repeated starts for the same IP and model.

A binding must include at least:

```text
dispatch generation
normalized IP
immutable inventory context/revision identity
selection source or manual-override binding
resolved canonical model, when any
```

The following immediately supersede older pending dispatch work:

- IP text changes;
- explicit model selection changes;
- a new or repeated Refresh/Enter start;
- inventory replacement/reload or availability change;
- application reset or shutdown.

A stale lookup/result must be rejected before credential resolution, handler acquisition, worker/controller submission, and network I/O. It must not:

- change the combo selection;
- change the visible page;
- clear or restore room/VIP presentation for a newer context;
- create or replace a controller/worker operation;
- select or advance credentials;
- persist a successful credential index or connection profile;
- start PDU room/codec enrichment;
- display an automatic modal connection error.

Once an existing device-specific lifecycle starts, its already approved controller/request freshness rules remain authoritative. Inventory dispatch must not create a second Matrix, PDU, DMP, codec, or audio-DSP operation-generation authority.

## Application, screen, controller, handler, and worker ownership

### Application/composition layer

Owns:

- normalized IP capture and validation;
- current inventory availability/context;
- `find_by_ip` call;
- zero/one/many interpretation;
- exact dispatch-registry lookup;
- manual fallback and override binding;
- accepted model/page/lifecycle assignment;
- dispatch generation and stale-result rejection;
- transition into existing credential and device lifecycle paths.

### EquipmentInventory

Owns only:

- immutable canonical records;
- deterministic tuple query results;
- preservation of multiplicity.

It does not know about GUI screens, controllers, handlers, model selectors, user overrides, or resolution status presentation.

### Screens

Render accepted page data and publish existing non-secret user intents. A screen does not query inventory, choose its own model, infer support, or start another screen/controller.

### Controllers and generic shell lifecycle

Receive an already assigned exact model/IP request context through existing application wiring. PDU and Matrix controllers retain their approved lane/generation authority. DMP retains its polling controller authority. Existing codec and Biamp paths remain model-specific until separately approved decomposition changes.

### Handlers, sessions, and workers

Receive one assigned supported model path and one assigned credential attempt according to existing contracts. They must not receive all inventory matches or a list of possible diagnostic models and must not:

- call `find_by_ip`;
- inspect `source_model`;
- parse manufacturer/model evidence;
- choose a GUI page;
- iterate diagnostic models;
- retry using a different model after protocol failure.

A protocol or authentication failure does not authorize model switching.

## Credential and transport compatibility

The final accepted model is established before model-specific credential resolution. Existing credential candidate chains remain application-owned.

Inventory dispatch does not change these rules:

- a saved supported profile is tried first where currently approved;
- transport retry and credential fallback remain separate;
- credential advancement occurs only after structured authentication failure;
- text such as `auth`, `401`, or `403` does not authorize fallback;
- successful credential index/profile is persisted only after accepted current complete success;
- stale or dispatch-only results persist nothing.

Manual override changes the assigned model for that request context, so credentials are resolved for the override model only. Credentials from the inventory model must not leak into the overridden path.

## Room, VIP, and PDU-related-codec compatibility

Automatic dispatch changes only the initial selected diagnostic model/page. Existing room-context publication remains bound to the final accepted model and normalized IP.

For a resolved Aten or PCS4i model:

```text
inventory dispatch
    -> PDU page/controller start
    -> accepted current PDU refresh
    -> existing independent PDU room/related-codec enrichment
```

Inventory dispatch must not start PDU enrichment before the PDU controller accepts a current successful user refresh. Enrichment failure remains independent from PDU success.

For non-PDU pages, the shared room block continues to use the selected exact model, screen registration, current IP, and immutable inventory context. Stale dispatch must not restore an old room block after a newer IP/model context.

## Aten consistency correction

`EXPECTED_KIND_BY_DIAGNOSTIC_MODEL` is importer-only consistency evidence. It is not canonical authority and not runtime dispatch authority.

This change corrects:

```text
Aten PE8208AV: expected kind pdu -> other
```

It preserves:

```text
Тип модели = Video Conference -> video_codec
Тип модели = БРП              -> pdu
all other values              -> other
```

Required outcomes:

```text
Aten PE8208AV + source type mapping to other
    -> diagnostic_model = Aten PE8208AV
    -> device_kind = other
    -> no KNOWN_MODEL_TYPE_MISMATCH

Extron IPL T PCS4i + source type mapping to other
    -> diagnostic_model = Extron IPL T PCS4i
    -> device_kind = other
    -> no KNOWN_MODEL_TYPE_MISMATCH

Aten PE8208AV + source type mapping to pdu or video_codec
    -> diagnostic_model remains Aten PE8208AV
    -> device_kind remains exact source-type result
    -> KNOWN_MODEL_TYPE_MISMATCH remains observable
```

The correction does not change model recognition, schema, snapshot identity algorithm, or runtime lookup APIs. A regenerated deployment snapshot is required only when operational data must incorporate other importer output changes; this expected-kind correction by itself changes issue reporting, not canonical record fields for correct Aten rows.

## Regression coverage

Focused synthetic tests must cover at least:

### Importer consistency

- Aten exact model with `device_kind = other` has no mismatch;
- PCS4i exact model with `device_kind = other` has no mismatch;
- genuinely conflicting Aten source type emits `KNOWN_MODEL_TYPE_MISMATCH` and preserves canonical kind;
- recognized model does not override `device_kind`.

### Dispatch registry

- all nine canonical models have exactly one dispatch entry and registered screen;
- no duplicate model entries;
- unknown model has no default page/lifecycle;
- selectable manual models and dispatch entries cannot drift.

### Inventory resolution

- unique Aten IP selects PDU page and Aten PDU lifecycle;
- unique PCS4i IP selects PDU page and PCS4i PDU lifecycle;
- unique Huawei TE40 IP selects codec page and TE40 refresh path;
- unique IN1804 IP selects matrix page and Matrix controller;
- representative Biamp and DMP records select the audio-DSP page and their distinct existing lifecycles;
- `device_kind = other` alone selects nothing;
- a record with supported-looking `source_model` but null/unknown `diagnostic_model` selects nothing automatically;
- duplicate IP never selects the first record or filters by kind/model;
- inventory unavailable and IP not found retain manual flow.

### Manual override and freshness

- explicit manual override uses only the selected registered model for the current context;
- override does not mutate or persist inventory;
- IP/inventory/reset changes invalidate override;
- stale lookup cannot alter a newer selection/page or start credential/network work;
- repeated refresh creates a new dispatch generation.

### Compatibility

- existing direct manual model diagnostics still start;
- PDU room/codec enrichment starts only after accepted PDU refresh;
- shared room/VIP presentation remains current;
- credential selection/fallback and successful-index persistence remain unchanged;
- no GUI-thread JSON/Excel/network work is introduced;
- no real organization data, credentials, or Graphify output appears in tests or diagnostics.

## Rollout and operational documentation

Implementation updates `docs/equipment-inventory-runbook.md` with:

- exact `diagnostic_model` dispatch authority;
- closed model-to-screen/lifecycle registry;
- zero/one/many outcomes;
- manual fallback/override boundary;
- stale-generation requirements;
- explicit statement that Aten and PCS4i may have `device_kind = other` while routing to PDU diagnostics;
- corrected importer consistency expectation.

No runtime Excel dependency or schema migration is introduced. Existing valid snapshots remain loadable. Production workbook and `equipment_inventory.local.json` remain deployment-local and outside Git.
