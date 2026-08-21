# Equipment Inventory Runbook

## Purpose and authority

This document is the operational map for equipment-inventory work in
`Mihail-R-cdx/diag-module-ref`. It is intended for developers, reviewers,
ChatGPT sessions, and local Codex sessions.

The normative contracts remain the current root OpenSpec specifications:

- `openspec/specs/equipment-inventory-snapshot/spec.md`
- `openspec/specs/pdu-room-codec-enrichment/spec.md`, when that capability is
  present on the current branch
- the related root specifications for application composition, request
  lifecycle, credentials, and device diagnostics

When the second root specification is not yet present on a branch, read the
current active or archived `pdu-room-codec-enrichment` change instead. If this
runbook conflicts with an approved OpenSpec specification, the OpenSpec
specification wins.

Any change to source-column mapping, canonical schema, identity authority,
ambiguity handling, PDU-to-room resolution, codec selection, or enrichment
lifecycle requires a semantic OpenSpec change before production implementation.

## Data flow

The approved boundary is:

```text
organization Excel workbook
    + optional approved network-connection workbook
    -> offline importer
    -> canonical versioned JSON snapshot
    -> runtime loader
    -> immutable indexed EquipmentInventory
    -> application-owned resolution/orchestration
```

Excel is an offline source format only. Normal diagnostic runtime code must not
parse `.xlsx` files and must not require a spreadsheet library.

The importer has two intentional conversion modes:

```text
primary equipment workbook only
    -> schema_version = 4
    -> switch_ip_address = null
    -> switch_port = null

primary equipment workbook
    + explicitly configured valid network workbook
    -> schema_version = 4
    -> switch fields may be populated only through approved MAC-only reconciliation
```

If a network source is explicitly configured and then cannot be read or does
not satisfy the approved worksheet/header contract, the importer fails the run
and preserves the previous output. It does not silently fall back to a
primary-only schema-v4 candidate.

The deployment-local runtime snapshot is:

```text
equipment_inventory.local.json
```

The real workbook and the generated production snapshot are operational data.
They must not be committed to Git. Tests use synthetic inventory only.

## Key implementation files

```text
core/equipment_inventory.py
tools/import_equipment_inventory.py
core/room_context.py
core/related_codec_status.py
gui/equipment_pages.py
gui/diagnostic_dispatch.py
gui/device_model_fallback_dialog.py
gui/main_window.py
gui/pdu_room_codec_enrichment.py
gui/pdu_controller.py
gui/screens/pdu_screen.py
tests/test_equipment_inventory.py
tests/test_inventory_diagnostic_dispatch.py
tests/test_inventory_credential_configuration.py
tests/test_pdu_room_codec_enrichment.py
tests/test_equipment_room_context_gui.py
```

## Authoritative primary workbook source mapping

The inspected organization workbook uses this authoritative current source mapping:

```text
SmartRoomID       -> record_id
ID комнаты        -> room_id
Название комнаты  -> room_name
Адрес комнаты     -> room_address
Наименование      -> source_model
IP                -> ip_address
MAC               -> mac_address
Серийный номер    -> serial_number
Тип модели        -> device_kind
```

The current schema-v4 source contract also requires:

```text
VIP оборудование -> room_vip
```

`Адрес комнаты -> room_address` is part of the current source mapping. Canonical
records include `room_address` only in schema v4; historic schema-v1 records
remain defined as documented below and do not contain that field.

`Адрес комнаты` is an exact required header for primary-source preflight and
conversion. Individual address cells are nullable: NFC-normalize and trim the
text, preserve case and internal text, and convert blank values to `null`. No
aliases, transliteration, substring matching, or inferred address column is
allowed. Missing or ambiguous discovery is fatal and leaves a previous output
unchanged.

The VIP mapping is closed:

```text
Excel boolean true  -> true
Excel boolean false -> false
ИСТИНА/истина       -> true
ЛОЖЬ/ложь           -> false
blank               -> null
anything else       -> null plus INVALID_ROOM_VIP
```

Text matching applies Unicode NFC normalization, trim, and casefold before the
exact comparison. Do not support the old `VIP` header, numeric `1`/`0`,
`да`/`нет`, `true`/`false`, `yes`/`no`, substrings, or fuzzy aliases.

The optional network-connection workbook contract is closed:

```text
worksheet: Устройства

MAC-адрес        -> MAC-only join evidence
IP коммутатора   -> switch_ip_address candidate
Порт             -> switch_port candidate
```

The worksheet `Изменения` is ignored completely. The column
`Корректная запись` is ignored completely: it is not required, does not filter
rows, does not create or suppress issues, does not break ambiguity, and does
not affect canonical fields or snapshot identity. Device IP, room text,
manufacturer, model, source/confidence/prefix fields, row order, and other
network workbook columns are not reconciliation authority.

The public two-source configuration names are exact:

```text
module configuration: NETWORK_XLSX_PATH
environment:          DIAG_INVENTORY_NETWORK_XLSX
CLI:                  --network-source
direct API keyword:   network_source_path
```

The direct API signature is:

```python
import_equipment_inventory(
    source_path,
    *,
    network_source_path=None,
    output_path=None,
    generated_at=None,
)
```

Network source priority is explicit API/CLI value, then
`DIAG_INVENTORY_NETWORK_XLSX`, then explicitly configured
`NETWORK_XLSX_PATH`, then intentional absence of a network source. All
configured paths are resolved to absolute `Path` values before workbook I/O.

Importer-only evidence may include:

```text
Производитель
Модель
Наименование
SmartRoomID контроллера
```

These evidence columns do not become separate canonical schema-v1 fields.
`diagnostic_model` is populated only through an explicit reviewed mapping to an
application-supported model name. Approximate matching, fuzzy matching, and
model guessing are forbidden.

## Diagnostic model recognition

The offline importer recognizes `diagnostic_model` from two independent
importer-only evidence fields:

```text
Модель
Наименование
```

`Наименование` remains the authoritative source for canonical `source_model`.
Using that same normalized value as recognition evidence does not rewrite
`source_model` and does not make free-form `source_model` runtime dispatch
authority. Runtime code remains exact-only and uses canonical
`diagnostic_model`, not `source_model`.

The source `Производитель` column is optional consistency evidence only: it is
not required for recognition, cannot add, remove, veto, or select a model
match, and cannot choose between multiple matching model rules.

Recognition evidence is built by applying the canonical text conversion,
Unicode NFC normalization, trim, and Unicode-aware `casefold()`. The importer
then splits evidence at non-alphanumeric separators and exposes exact
alphabetic and decimal runs at letter-to-digit and digit-to-letter transitions.
Space, hyphen, underscore, dot, slash, and other non-alphanumeric separators
are equivalent boundaries. Component evidence is set-like: order and repetition
do not affect rule satisfaction.

Compact forms are supported only through exact component boundaries:

```text
TE40, TE 40, TE-40, Huawei_TE.40 -> te + 40
DMP64, DMP 64, Extron/DMP-64-Plus -> dmp + 64
IPL T PCS4i, IPL-T-PCS-4i -> ipl + pcs + 4i
```

The mixed component `4i` is specifically supported for the reviewed
`PCS4i` evidence. Do not extend this into fuzzy matching, arbitrary substring
matching, typo correction, transliteration, edit distance, token similarity,
manufacturer guessing, or machine-learning classification.

The closed diagnostic model registry is exactly:

```text
Huawei TE20
  required: te + 20

Huawei TE40
  required: te + 40

CloudLink Bar 310
  required: cloudlink + bar + 310

CloudLink Box 310
  required: cloudlink + box + 310

Polycom RPG 310
  alternative 1: rpg + 310
  alternative 2: realpresence + group + 310

Extron IN1804
  required: in + 1804

Aten PE8208AV
  required: pe + 8208

Extron IPL T PCS4i
  required: ipl + pcs + 4i

Biamp Tesira Forte CI
  alternative 1: tesira + forte
  alternative 2: tesira + forté

Extron DMP 64 Plus
  required: dmp + 64
```

`AV`, `CI`, and `Plus` are intentionally optional source components. Do not
add new aliases, manufacturer requirements, or registry-order tie breakers
without a new approved OpenSpec change.

All rules are evaluated before the importer selects an outcome:

```text
M = complete distinct canonical match set from Модель
N = complete distinct canonical match set from Наименование
C = M union N

zero distinct matches in C
    -> diagnostic_model = null
    -> UNMAPPED_DIAGNOSTIC_MODEL

one distinct match in C
    -> diagnostic_model = exact canonical model
    -> no model-recognition issue

many distinct matches in C
    -> diagnostic_model = null
    -> AMBIGUOUS_DIAGNOSTIC_MODEL
```

Neither evidence field has priority over the other. Agreement on the same one
canonical model is still one distinct match. If one field is internally
ambiguous, the ambiguity is preserved even when the other field agrees with one
candidate.

`UNMAPPED_DIAGNOSTIC_MODEL` and `AMBIGUOUS_DIAGNOSTIC_MODEL` are non-fatal
data-quality issues when the row is otherwise representable. They are mutually
exclusive for one row. Missing or blank `Модель` or `Наименование` contributes
an empty match set rather than a fatal source-structure error.

Normal diagnostics may include a safe row number and canonical `record_id`, but
must not dump complete source rows, workbook content, production inventory, or
unnecessary free-form evidence. Runtime code remains exact-only: application
dispatch may use canonical `diagnostic_model`, but must not reproduce the
component recognizer or infer support from `source_model`, `Производитель`,
`Модель`, or other evidence fields.

After importer recognition changes are deployed, regenerate the
deployment-local `equipment_inventory.local.json` offline from the configured
workbook path. The workbook and generated deployment snapshot remain outside
Git.

After schema-v4 inventory metadata is deployed, regenerate the deployment-local
snapshot offline from the primary workbook and, when authorized operationally,
the configured network workbook. The primary workbook, network workbook, and
generated deployment snapshot remain outside Git.

## Identity rules

### Equipment identity

`SmartRoomID` is the only authoritative source for canonical `record_id`.

Missing, blank-after-normalization, or duplicate `SmartRoomID` is a fatal
source-contract error. It blocks publication of the candidate snapshot.

Do not manufacture fallback identity from:

- workbook row number or order;
- IP or MAC address;
- serial number;
- room ID or room name;
- model text;
- UUID, timestamp, suffix, or counter.

### Room identity

`ID комнаты` is authoritative for `room_id`.

`Название комнаты` maps to `room_name` and is display evidence only. Never use
`room_name` as fallback identity, never merge rooms by display name, and never
select one conflicting name as authoritative.

## Canonical snapshot schema v1

The JSON root contains required fields:

```text
schema_version
snapshot_id
records
```

Optional generation metadata:

```text
generated_at
source_row_count
```

Every canonical record contains exactly:

```text
record_id
source_model
diagnostic_model
ip_address
mac_address
serial_number
room_id
room_name
device_kind
```

Required non-null record fields:

```text
record_id
device_kind
```

Nullable fields:

```text
source_model
diagnostic_model
ip_address
mac_address
serial_number
room_id
room_name
```

Allowed `device_kind` values:

```text
pdu
video_codec
other
```

Exact source-type mapping:

```text
Video Conference -> video_codec
БРП              -> pdu
all other values -> other
```

Recognized model evidence must not override the exact `Тип модели` mapping.
For the reviewed organization rows, correct Aten PE8208AV and Extron IPL T
PCS4i source type maps to `device_kind = other`. The importer consistency
expectation follows that contract; runtime PDU dispatch is authorized by exact
canonical `diagnostic_model`, not by `device_kind`.

## Canonical snapshot schema v4

Every newly generated snapshot uses `schema_version = 4`, whether conversion
uses the primary workbook only or a configured network workbook. Each record
contains exactly:

```text
record_id
source_model
diagnostic_model
ip_address
mac_address
serial_number
room_id
room_name
room_address
device_kind
room_vip
switch_ip_address
switch_port
```

All keys are present even when nullable. In primary-only mode both switch fields
are `null`; a valid configured network source may populate them only through
the existing MAC-only reconciliation. `room_id` remains the sole room identity;
`room_name`, `room_address`, and `room_vip` remain per-record display metadata.
The importer does not reconcile different same-room display values or emit
room-display conflicts solely because they differ.

The schema-v4 deterministic identity contains only:

```text
schema_version
records
```

Records are sorted by `record_id`. `room_address`, `room_vip`, and both switch
fields participate in schema-v4 identity. `generated_at`, report fields, and all network-run counters
remain outside identity. `source_row_count` remains the primary equipment
workbook row count only; network row count is report metadata only.

The runtime loader validates exact per-version record shapes:

```text
schema v1 -> room_vip = null, room_address = null, switch_ip_address = null, switch_port = null
schema v2 -> room_vip is read, room_address = null, switch_ip_address = null, switch_port = null
schema v3 -> room_vip and switch fields are read, room_address = null
schema v4 -> room_vip, room_address, and switch fields are read
```

Hybrid records are invalid: each declared v1–v4 version must have its own exact
field set. Future schema versions
remain unsupported until explicitly reviewed.

## Switch connection reconciliation

Reconciliation is by canonical MAC only:

```text
primary canonical mac_address
    <-> network MAC-адрес after the same canonical MAC normalization
```

Do not join or break ties by device IP, room, manufacturer, model, row order,
ignored metadata, `Изменения`, or `Корректная запись`.

A network row creates a usable connection candidate only when at least one
normalized switch field is non-null. A valid MAC with blank switch IP and blank
port creates no candidate and reports `EMPTY_SWITCH_CONNECTION`. Invalid
non-blank switch IP reports `INVALID_SWITCH_IP`; if the port is valid, the row
is a usable partial candidate with `switch_ip_address = null`.

Unique partial candidates are preserved:

```text
valid switch IP + null port      -> MISSING_SWITCH_PORT
blank switch IP + valid port     -> MISSING_SWITCH_IP
invalid switch IP + valid port   -> INVALID_SWITCH_IP
```

The importer enriches only when exactly one primary record and exactly one
distinct usable normalized network candidate share the same canonical MAC.
Repeated identical candidates collapse to one candidate and report
`DUPLICATE_SWITCH_CONNECTION_SOURCE`. Multiple distinct candidates report
`AMBIGUOUS_SWITCH_CONNECTION` and leave both switch fields null. Multiple
primary records sharing one MAC report `AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH`
and none are enriched. A network MAC absent from primary inventory reports
`NETWORK_MAC_NOT_IN_INVENTORY`.

Network row-level issues are non-fatal when the primary candidate remains
representable. Fatal network failures are limited to configured path/read
failure, missing or ambiguous `Устройства`, missing or ambiguous required
headers, complete candidate validation failure, and output publication failure.
Publication remains atomic: the candidate is built and validated through the
runtime loader before replacing the output, and fatal failure leaves the
previous output intact.

## Normalization

Canonical text uses Unicode NFC normalization and trims leading and trailing
whitespace. Empty nullable text becomes `null`.

When present, IP must be canonical dotted-decimal IPv4. Invalid source IP is
represented as `null` plus a structured non-fatal import issue when the record
is otherwise representable.

When present, MAC must use lowercase colon-separated text:

```text
aa:bb:cc:dd:ee:ff
```

Invalid source MAC is represented as `null` plus a structured non-fatal import
issue when the record is otherwise representable.

## Snapshot identity and publication

Schema v1 uses deterministic content identity:

```text
snapshot_id = "sha256:" + sha256(canonical identity payload)
```

The identity payload contains only:

```text
schema_version
records
```

Records are sorted by normalized `record_id`. `generated_at` and
`source_row_count` do not affect identity. The runtime loader recomputes the
digest and rejects a mismatch as `INVALID_SNAPSHOT`.

Publication is atomic. A fatal import failure must leave the previous valid
production snapshot intact and must not expose a partial candidate at the
production path.

## Runtime inventory boundary

A successful load creates one immutable `EquipmentInventory` revision and
prebuilds multi-value indexes equivalent to:

```text
ip_address -> tuple[EquipmentRecord, ...]
room_id -> tuple[EquipmentRecord, ...]
(room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

Public query methods are:

```python
inventory.find_by_ip(ip_address)
inventory.find_room_equipment(room_id)
inventory.find_by_room_and_kind(room_id, device_kind)
```

Schema v4 exposes `switch_ip_address` and `switch_port` as passive record
attributes only. The runtime inventory keeps the same indexes and public
queries. Do not add runtime indexes or public queries by switch IP or switch
port in this change. Diagnostic dispatch, credential configuration, room
context, PDU-to-room-to-codec enrichment, handlers, controllers, workers,
transports, and device I/O ignore the switch fields.

Every normal query returns a tuple containing zero, one, or many records.
The inventory layer preserves multiplicity and does not classify it as
`NOT_FOUND`, `RESOLVED`, or `AMBIGUOUS`.

Do not use implicit first-match selection such as `records[0]` or `codecs[0]`.
Interpretation of zero/one/many belongs to application/composition code.

## Standalone inventory converter GUI

The standalone operator converter is launched separately from the diagnostic
application:

```powershell
<repository-supported-python> .\tools\inventory_converter_gui.py
```

It owns its own `QApplication` and converter window. The normal diagnostic
entry point `main.py` and `gui/main_window.py` do not import, launch, navigate
to, or depend on converter GUI paths, reports, workers, or state. Importer and
runtime inventory modules remain UI-independent and must not import PyQt5.

The converter exposes exactly three path controls:

```text
primary equipment workbook (.xlsx)
network connection workbook (.xlsx)
output JSON file (.json)
```

Operation path requirements are:

```text
Primary Test -> primary workbook
Network Test -> network workbook
Check all    -> primary workbook + network workbook
Convert      -> primary workbook + network workbook + output JSON
```

`Primary Test` and `Network Test` are read-only source preflights. They reuse
the importer reader, layout/header discovery, normalization, model recognition,
network-source normalization, and issue classification. They do not create or
replace JSON and they do not become authority for later conversion.

`Check all` rereads the current primary and network workbook bytes, performs
approved MAC-only reconciliation, builds a schema-v4 candidate in memory,
validates it through the runtime loader, and publishes nothing. It intentionally
does not require an output path.

`Convert` is the explicit two-source schema-v4 GUI workflow. It always rereads
the current source bytes and repeats full validation; it does not trust cached
test results. CLI and direct API callers may still use the supported one-source
mode, which also publishes schema v4 with null switch fields.

Per-source GUI states are presentation-only:

```text
NOT_TESTED
RUNNING
PASSED
PASSED_WITH_WARNINGS
FAILED
STALE
```

Only completed operation reports have terminal statuses:

```text
SUCCEEDED
SUCCEEDED_WITH_WARNINGS
FAILED
```

The GUI maps terminal report statuses to completed source states as
`PASSED`, `PASSED_WITH_WARNINGS`, and `FAILED`. Editing a source path resets
that source to `NOT_TESTED`. After a source test, the GUI stores a safe
fingerprint containing resolved path, file size, and last-modified time. Before
showing an old result as current, before `Check all`, and before `Convert`, a
fingerprint mismatch changes the state to `STALE`. There is no background file
watcher and no full-workbook hash.

All workbook I/O, validation, reconciliation, candidate validation,
serialization, publication-precondition checking, and publication run outside
the GUI thread through a serialized worker lifecycle. Only one operation runs
at a time. During an operation, path edits, browse buttons, tests, `Check all`,
`Convert`, and conflicting report actions are disabled. Progress is
indeterminate because there is no measured percentage contract. Closing the
window while work is running is blocked; the GUI must not terminate a worker or
interrupt atomic publication.

Before GUI conversion starts, the GUI captures the normalized output path and
confirmed output state. Existing output requires explicit replacement
confirmation. Absent output is confirmed as absent. The GUI then delegates
publication to the importer and must not delete, truncate, pre-create, rename,
or write JSON itself. Immediately before atomic replacement, the importer
rejects publication with fatal `OUTPUT_CHANGED_SINCE_CONFIRMATION` when the
output appeared, disappeared, changed size, changed mtime, changed available
file identity, or no longer matches the confirmed normalized path. Rejection
sets `published = false`, uses stage `PUBLICATION`, source role `OUTPUT`, and
leaves current output bytes untouched.

All converter operations serialize the same closed report shape. Existing
conversion report keys remain present, and the additive root keys are:

```text
operation
status
stage_reached
schema_version
source_files
output_path
published
data_quality_issue_count
consistency_issue_count
```

Issue objects contain:

```text
class
code
sheet
row
record_id
description
stage
source_file_role
source_column
related_row
details
```

`details` is a flat JSON object with scalar values or arrays of scalars. It
must not contain full source rows, workbook fragments, canonical record dumps,
credentials, secrets, or unnecessary evidence. The GUI summary shows operation,
terminal status, publication state, output path, stage, schema version, source
row counts, record count, snapshot ID, network counters, and issue counts. The
issue table shows fatal issues first, supports presentation-only filtering by
issue class, and displays exact `details` for the selected issue. `Save report`
exports the complete unfiltered UTF-8 JSON report with exactly one trailing
newline after both success and failure.

The network workbook contract remains exact: only worksheet `Устройства` is
current evidence. Worksheet `Изменения` and column `Корректная запись` are
ignored completely; they do not filter rows, create or suppress issues, join
records, affect ambiguity, enter canonical JSON, or affect snapshot identity.

Production workbooks, the generated deployment snapshot
`equipment_inventory.local.json`, exported converter reports, local path
preferences, and temporary outputs are operational data and must not be
committed to Git.

## Inventory-driven diagnostic dispatch

The permanent top-panel model selector is not part of runtime authority.
Operators enter only the target IP, then use Refresh/Enter to start diagnostics
or `Пароль` to configure credentials. The application owns exact model
resolution, accepted contexts, page routing, and lifecycle selection.

The closed runtime dispatch registry is exactly the same nine canonical model
names recognized by the importer:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
Extron IN1804
Aten PE8208AV
Extron IPL T PCS4i
Biamp Tesira Forte CI
Extron DMP 64 Plus
```

Each registry entry declares the target screen and existing lifecycle route.
The registry must not contain credentials, indexes, handlers, workers,
sessions, cookies, tokens, or mutable operation state.

For every diagnostic start and every `Пароль` activation, application
composition:

```text
1. validates and normalizes the current IP;
2. creates a fresh action generation for the specific purpose;
3. captures the immutable inventory context;
4. calls inventory.find_by_ip(normalized_ip);
5. classifies unavailable, zero, one, or many total IP matches before model inspection;
6. for exactly one record, resolves only exact non-null diagnostic_model through the closed registry.
```

Resolution outcomes are:

```text
INVENTORY_UNAVAILABLE
IP_NOT_FOUND
AMBIGUOUS_IP
MODEL_UNMAPPED
MODEL_UNSUPPORTED
RESOLVED
```

Runtime dispatch must not inspect or normalize `source_model`, manufacturer
evidence, free-form model text, `device_kind`, current page, previous fallback,
previous diagnostic request, hidden widget state, handler availability, or
registry order as model authority.

For Refresh/Enter, a resolved inventory model becomes one current
`AUTO_INVENTORY` diagnostic context. Unresolved outcomes open the
purpose-bound fallback dialog; only explicit selection plus diagnostic
confirmation may create a `MANUAL_FALLBACK` context. Cancel or close performs
no page switch, credential access, ping, handler/controller/worker creation,
automatic diagnostic start, or device I/O. A supported automatic resolution
does not expose an ordinary manual override.

For `Пароль`, model resolution is a separate `CREDENTIAL_CONFIGURATION` action.
It never reuses an accepted diagnostic model as credential authority. Resolved
inventory or explicit credential-purpose fallback may open only the exact
accepted model/IP credential dialog. Credential configuration does not ping,
transition pages, create diagnostic requests, acquire handlers/sessions, submit
controllers or workers, start PDU enrichment, or perform device I/O.
Credential-dialog cancel mutates nothing; confirmation may only add or promote
the exact bound model/IP candidate under existing credential-store semantics
and must not mark it as a confirmed successful credential or persist a
connection profile.

All model actions are bound to purpose, generation, normalized IP, immutable
inventory context, selection source, exact accepted model, and dialog identity
where applicable. IP changes, inventory replacement/failure changes, shutdown,
or newer same-purpose actions supersede old work before credential mutation,
page/controller activation, handler acquisition, worker submission, or network
I/O.

Room VIP evidence is evaluated only across all records sharing one non-null
authoritative `room_id`:

```text
no room records                         -> unresolved room
all room_vip values null                -> NO_DATA
one or more true, all others null/true  -> VIP_TRUE
one or more false, all others null/false-> VIP_FALSE
at least one true and at least one false-> CONFLICT
```

The importer preserves differing per-record VIP values and does not report
`ROOM_VIP_CONFLICT` solely from same-room disagreement. The legacy runtime
room-context aggregation may still present its existing `CONFLICT` result.

## Structured runtime load failures

Runtime inventory loading classifies failures as exactly one of:

```text
NOT_FOUND
UNREADABLE
INVALID_FORMAT
UNSUPPORTED_SCHEMA
INVALID_SNAPSHOT
```

No failed load may publish partial records, indexes, or an
`EquipmentInventory` instance.

## PDU to room to codec resolution

Resolution starts only after a current successful user-initiated PDU refresh
has been accepted by `PDUController`.

A mutation reconciliation refresh, stale callback, PDU error, progress event,
or completion without accepted success must not start enrichment.

The exact resolution sequence is:

```text
1. Receive the accepted current PDU IP and exact accepted PDU model.
2. Call inventory.find_by_ip(pdu_ip).
3. Require exactly one total IP match.
4. Require the accepted PDU model to be Aten PE8208AV or Extron IPL T PCS4i.
5. Require the one inventory record diagnostic_model to be in that closed PDU set.
6. Require the inventory diagnostic_model to exactly equal the accepted PDU model.
7. Require non-null authoritative room_id.
8. Call inventory.find_room_equipment(room_id) for display consistency evidence.
9. Call inventory.find_by_room_and_kind(room_id, "video_codec").
10. Require exactly one codec record.
11. Require non-null canonical codec ip_address.
12. Require an exact supported codec diagnostic_model.
13. Bind the result to the inventory snapshot and accepted PDU context.
14. Run an independent read-only codec-status operation.
15. Render only accepted current non-secret presentation on PDUScreen.
```

Duplicate IP ambiguity is evaluated before model inspection. If two records
share the accepted PDU IP, the result remains `AMBIGUOUS_PDU_IP`.

Room name never replaces room ID. When one `room_id` has multiple distinct room
names, no name is selected; a safe `ROOM_NAME_CONFLICT` warning is exposed and
resolution continues by `room_id`.

## Resolution statuses

```text
INVENTORY_UNAVAILABLE
PDU_NOT_FOUND
AMBIGUOUS_PDU_IP
PDU_MODEL_UNSUPPORTED
PDU_MODEL_MISMATCH
ROOM_UNRESOLVED
CODEC_NOT_FOUND
AMBIGUOUS_CODEC
CODEC_IP_MISSING
CODEC_UNSUPPORTED
RESOLVED
```

These statuses are application resolution outcomes. They are not emitted by the
inventory query layer itself.

## Supported related-codec models

Automatic related-codec diagnostics use exact canonical `diagnostic_model`
values only:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

Do not choose a handler from `source_model`, manufacturer substrings, similar
text, source row order, or a first matching record.

## Related-codec operation boundary

Automatic related-codec diagnostics are read-only and obtain only narrow
normalized status such as:

```text
call_status
presentation_status
```

They must not issue Wake, volume, mute, SIP update, call placement, call
termination, presentation control, or any other state-changing command.

The operation uses an independent serialized `InteractiveSessionController` or
equivalent lane. It must not reuse:

```text
CodecScreen.interactive_controller
generic _active_request
global current_worker
```

A user-selected codec context and an automatically resolved related codec must
remain independent.

## Generation and stale-work safety

Every accepted PDU refresh creates a distinct enrichment generation, including
a repeat refresh for the same PDU and the same resolved codec.

Required order:

```text
new enrichment generation
    -> dedicated session invalidate_context()
    -> resolve inventory and codec context
    -> activate dedicated codec context
    -> submit one read-only status operation
```

A stale queued operation must be dropped before handler acquisition and before
network I/O. A stale in-flight result must not:

- update the GUI;
- restore old room or codec values;
- persist a credential index;
- persist a connection profile;
- change PDU lifecycle state.

Starting a new or repeat PDU refresh, changing PDU model/IP/credential context,
explicit invalidation, or shutdown must supersede old enrichment immediately,
without waiting for replacement success.

## Credential and transport rules

Application/composition code resolves the complete credential chain before
handler or session construction.

One assigned credential is used across all supported transport attempts.
Transport fallback and credential fallback are separate mechanisms.

Credential advancement is allowed only after a structured confirmed
`AuthenticationError` from new-session login. Transport errors, timeouts, SSL
errors, protocol/parser failures, empty or malformed responses, and text such as
`auth`, `401`, or `403` do not authorize credential advancement.

A supported saved connection profile is tried first. Credential index and
profile are persisted only after an accepted current complete success. Stale,
partial, resolution-only, unsupported, and failed outcomes persist nothing.

## PDU result independence

Inventory and related-codec enrichment are optional contextual diagnostics.
Their failure must not convert an accepted PDU success into a PDU failure.

Enrichment failure must not:

- clear accepted PDU device or outlet data;
- disable valid PDU controls;
- change PDU refresh or mutation authority;
- trigger PDU retry or reconciliation;
- open an automatic modal connection error.

Related-room failures are rendered safely and inline.

## Non-PDU room context

Every registered non-PDU equipment page is routed through the centralized
equipment-page registry in `gui/equipment_pages.py` and receives the same
shared room-information block at the bottom of the page. PDU pages are excluded
only by explicit registry classification because they keep the dedicated PDU
room/related-codec block.

Non-PDU room context is application-owned and independent from device
diagnostic success. A new room-context generation is created when model,
normalized IP, page context, credential context, or accepted inventory snapshot
context changes. The resolver uses only the loaded `EquipmentInventory` and the
canonical equipment IP; it does not wait for device refresh, ping, worker
callbacks, or handler construction.

Device start/progress/result/error/finished callbacks must not rerun, clear, or
restore the room block. Inventory failure is displayed as safe inline room
context and must not open automatic modal connection errors or change device
diagnostic authority.

## Data and secret protection

Do not commit or expose:

- the real organization workbook;
- `equipment_inventory.local.json`;
- real organization inventory in tests;
- complete source rows or complete inventory dumps;
- credential dictionaries or values;
- cookies, Session IDs, CSRF/access tokens;
- handler, worker, transport, or session objects;
- complete raw codec status when a narrow result is sufficient.

Importer and runtime diagnostics should expose only the minimum safe evidence:
issue class, issue code, row reference, safe `record_id` when appropriate, and a
short safe description.

## Checklist for future agent sessions

Before any inventory-related task:

1. Read `RULES.md`.
2. Read this runbook.
3. Read the current root OpenSpec inventory specification.
4. Read the current PDU-room-codec specification or active/archived change when relevant.
5. Verify the current GitHub branch, PR, and `master`; do not rely on old session memory.
6. Preserve zero/one/many semantics and authoritative identity rules.
7. Use only synthetic fixtures.
8. Create a semantic OpenSpec change before changing a normative contract.
9. Use only the repository-local `./openspec.cmd` or `.\openspec.cmd` wrapper.
10. Run focused tests, the full offline suite, strict OpenSpec validation, and Git checks required by `RULES.md`.
