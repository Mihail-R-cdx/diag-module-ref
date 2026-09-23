# Design: Extron matrix model expansion

## Context

Current Matrix behavior is centered on `ExtronIN1804Handler`, one logical routing output, and a scalar current route. The new scope adds IN1806 plus other single-output presentation switchers and true multi-output matrix frames while preserving hardware-confirmed IN1804 behavior.

The design must make command syntax, topology, identity and HDCP decoding explicit per approved family/model profile.

## Design Principles

### 1. Routing topology is not physical connector count

The application SHALL model independently routable endpoints rather than counting physical output connectors. Multiple physical connectors driven by one logical route SHALL NOT create duplicate GUI route columns.

### 2. Runtime authority comes from read-only evidence

Topology discovery SHALL use only read-only identity/configuration evidence. State-changing route commands SHALL NOT be used to probe whether an input/output exists.

### 3. Exact SIS syntax belongs to a profile

No global Extron command table SHALL assume that all models use the same routing, naming, HDCP or topology syntax. Common transport owns authentication/session/framing only. Family/model profiles own command generation and response interpretation.

### 4. Unproven is different from unsupported

If research has not established an authoritative command for an optional field, the capability SHALL be `UNPROVEN`/unavailable and the application SHALL NOT send a speculative SIS read.

The six `Общая информация` fields are acceptance-critical for every Matrix model supported by this change and are not optional diagnostics. If authoritative acquisition for `Модель`, `MAC-адрес`, `Серийный номер`, `Версия прошивки`, `Температура`, or `Время работы` is unproven for an in-scope model, that is a blocking capability gap for that profile. The implementation SHALL establish authoritative read/source evidence before claiming a complete successful full refresh or hardware PASS; it SHALL NOT fill the gap with a guessed command, placeholder, unrelated field, stale snapshot, or synthetic value.

### 5. Profile selection precedes profile-specific decoding

Matrix dimensions and installed-board symbols are not sufficient by themselves to distinguish first-generation XTP from XTP II. The application SHALL establish authoritative frame identity first, then select the matching XTP or XTP II decoder/profile, then interpret dimension/board evidence under that selected profile.

Authoritative frame identity SHALL come from a documented frame identity/part-number response accepted by an exact-frame registry. The `*N` response may contribute the frame part number plus slot-by-slot board evidence when the official profile defines that response. If the returned part number/identity cannot be resolved exactly, the device remains unsupported rather than inheriting the nearest XTP family profile.

## Proposed Domain Model

Conceptually:

```python
MatrixCapabilities(
    family,
    exact_model,
    logical_input_ids,
    logical_output_ids,
    available_input_ids,
    available_output_ids,
    physical_outputs,
    supports_signal_presence,
    supports_input_hdcp,
    supports_output_hdcp,
    supports_hdcp_authorization,
    supports_input_names,
    supports_output_names,
    supports_temperature,
    supports_firmware,
    supports_uptime,
    supports_device_mac_fallback,
    supports_device_serial_fallback,
    route_profile,
    input_hdcp_profile,
    output_hdcp_profile,
)
```

Normalized runtime state:

```python
MatrixState(
    general_info={
        "model": authoritative_model,
        "mac_address": authoritative_mac,
        "serial_number": authoritative_serial,
        "firmware": authoritative_firmware,
        "temperature": authoritative_temperature,
        "uptime": authoritative_uptime,
    },
    routes={output_id: input_id_or_none},
    signal_presence={input_id: bool_or_none},
    input_hdcp={input_id: normalized_hdcp_state},
    output_hdcp={output_id: normalized_output_hdcp_state},
    input_names={input_id: name_or_none},
    output_names={output_id: name_or_none},
)
```

The existing scalar `current_connection` MAY remain only as a compatibility projection for a proven single-output topology; it SHALL NOT remain authoritative for the generalized Matrix domain.

## Approved Scope and Profiles

### IN1804 compatibility profile

Preserve the existing hardware-confirmed behavior:

```text
identity             1I
temperature          W20STAT
input name N         WI<N>VNAM
output name 1        WO1VNAM
signal presence      W0LS
HDCP authorization   WE<N>HDCP
input HDCP           WI<N>HDCP
output HDCP          WO1HDCP
read route           !
set route            <I>*1!
```

The command terminator remains transport-owned. This profile SHALL NOT be rewritten merely to match an alternate canonical form shown in a manual when that would regress the deployed hardware-confirmed behavior.

### IN1806 profile

IN1806 is a distinct exact supported application/profile identity with six logical
inputs and one logical main routing output. It SHALL NOT be represented as IN1808
merely because both devices share a documented SIS family.

Hardware and official evidence establish the exact identity pair:

```text
model identity        IN1806
part number           60-1663-01
logical inputs        1..6
logical main output   1
```

Its approved SIS profile follows the documented IN1806/IN1808 command family:

```text
identity             1I
part number          N
temperature          W20STAT
input name N         WI<N>VNAM
output name N        WO<N>VNAM
signal presence      W0LS
HDCP authorization   WE<N>HDCP
input HDCP           WI<N>HDCP
output HDCP          WO<N>HDCP
read video route     1%
set video route      <I>*1%
```

Inputs 7 and 8 are unavailable for IN1806 and SHALL NOT be fabricated from the
IN1808 profile. Canonical `routes[1]` is the video route only; audio breakaway is
outside the Matrix table, and neither polling nor route intent SHALL change or
reconcile the audio tie. The separate HDMI loop output is not a second main routing
column; loop-out exposure remains outside generalized main-route authority unless
separately approved.

### IN1808 profile

```text
identity             1I
temperature          W20STAT
input name N         WI<N>VNAM
output name N        WO<N>VNAM
signal presence      W0LS
HDCP authorization   WE<N>HDCP
input HDCP           WI<N>HDCP
output HDCP          WO<N>HDCP
read video route     1%
set video route      <I>*1%
```

Main scaled routing remains one logical route even when multiple physical output connectors share that route. Canonical `routes[1]` is the video route only: read with `1%` and mutate with `<I>*1%`. Audio breakaway is outside the Matrix table and SHALL NOT be changed by route intent or used for reconciliation. Loop-out routing is deferred unless separately proven and accepted as an auxiliary endpoint in this change; it SHALL NOT be silently counted as a second main matrix output.

### IN1608 xi profile

```text
identity             1I
temperature          W20STAT
input name N         W<N>NI
signal presence      W0LS
HDCP authorization   WE<N>HDCP
input HDCP           WI<N>HDCP
output HDCP          WO<N>HDCP
read video route     &
set video route      <I>&
```

Canonical `routes[1]` is video-only. The combined `!` selection and separate
audio route are outside the Matrix table, so polling and room route intent SHALL
not change or reconcile the audio tie. Output-name read remains `UNPROVEN`
unless separately established.

### Presentation-switcher route-state semantics

For IN1806, IN1808, and IN1608 xi, the room Matrix table represents video routing
only. Read, mutation, and reconciliation SHALL therefore target the video route
and SHALL remain valid when the device is in audio breakaway mode. Combined AV
selection commands (`!`) SHALL NOT be used by these new profiles for polling or
route mutation. Audio routing is not displayed and SHALL NOT be changed by a
Matrix-table route intent.

IN1804 is an explicit compatibility exception: its existing deployed
hardware-confirmed `!` / `<I>*1!` route profile remains unchanged until separate
evidence and approval justify a migration.

### DTP CrossPoint approved scope

This change supports only:

```text
DTP CrossPoint 84
DTP CrossPoint 82 4K
DTP CrossPoint 84 4K
DTP CrossPoint 86 4K
DTP CrossPoint 108 4K
```

It explicitly excludes DTP2 CrossPoint, DTP3 CrossPoint and any unnamed DTP generation.

For the approved DTP profiles, canonical `routes[output_id]` authority is the video tie only. The documented `<O>%` query is distinct from AV tie syntax; `<O>!` SHALL NOT be used as a DTP read-only route query. A DTP route intent SHALL mutate only video with `<I>*<O>%`, and video untie SHALL use `0*<O>%`. Audio ties are outside this Matrix table and SHALL NOT be read, displayed, changed, or used for reconciliation by the DTP route operation. Hardware QA observed `E13` after the old `1!` polling attempt on a DTP CrossPoint 86 4K path, after other diagnostic reads had already succeeded.

```text
identity/profile     exact documented model identity -> fixed topology registry
signal presence      0LS
input name N         W<N>NI
output name N        W<N>NO
input HDCP           WI<N>HDCP
output HDCP          WO<N>HDCP
read video route O   <O>%
set video route I->O <I>*<O>%
untie video O        0*<O>%
```

Fixed topology SHALL be resolved from exact-model identity/profile data. Physical connector numbering MAY differ from logical routing-output numbering; GUI routing follows logical routing outputs. DTP temperature is now a mandatory unresolved General-information capability gap: authoritative evidence must be established before a DTP profile can satisfy complete full-refresh or hardware-PASS acceptance.

### First-generation XTP CrossPoint profile

The approved profile uses authoritative exact-frame identity plus documented XTP matrix/board evidence:

```text
frame identity       documented exact frame/part-number evidence
matrix dimensions    I
installed boards     *N
signal presence      0LS
input HDCP           WI<N>HDCP
output HDCP          W0<N>HDCP
all output HDCP      W0*HDCP
read AV route O      <O>!
set AV route I->O    <I>*<O>!
untie O              0*<O>!
```

`WO<N>HDCP` SHALL NOT be used as the first-generation XTP frame output-HDCP command merely because DTP uses that form.

Input/output names may remain `UNPROVEN` where the routing table has an approved deterministic fallback. Temperature does not: for XTP it is a mandatory General-information capability gap and authoritative acquisition must be established before complete full-refresh or hardware-PASS acceptance.

### XTP II CrossPoint profile

XTP II remains a separate profile. It uses authoritative exact-frame identity before interpreting dimension/board evidence:

```text
frame identity       documented exact XTP II frame/part-number evidence
matrix dimensions    I
installed boards     *N
signal presence      0LS
input HDCP           WI<N>HDCP
HDCP authorization   WE<N>HDCP
read AV route O      <O>!
set AV route I->O    <I>*<O>!
untie O              0*<O>!
```

XTP II **output-HDCP command and decoder remain UNPROVEN in this change until verified from official XTP II evidence**. The application SHALL NOT reuse either DTP `WO<N>HDCP` or first-generation XTP `W0<N>HDCP` by assumption.

Input/output names may remain `UNPROVEN` where presentation has an approved deterministic fallback. Temperature does not: for XTP II it is a mandatory General-information capability gap and authoritative acquisition must be established before complete full-refresh or hardware-PASS acceptance.

## HDCP Normalization

Raw input values SHALL be decoded through the selected device profile.

### IN1804 / IN1806 / IN1808 input HDCP

```text
0 -> source absent
1 -> source present, HDCP absent
2 -> source present, HDCP present
```

### IN1608 xi / approved DTP CrossPoint / XTP CrossPoint / XTP II CrossPoint input HDCP

```text
0 -> source absent
1 -> source present, HDCP compliant/present
2 -> source present, HDCP non-compliant/absent
```

Normalized input states SHALL distinguish at least `ABSENT`, `PRESENT_HDCP`, `PRESENT_NO_HDCP`, and `UNKNOWN`.

Room presentation continues to derive its HDCP display from normalized input HDCP status, not HDCP authorization/configuration or output HDCP state.

Output HDCP SHALL use a separate per-family command/decoder profile. DTP and first-generation XTP are explicitly different; XTP II remains unavailable until proven.

## Topology Discovery

### Fixed presentation switchers

IN1804 / IN1806 / IN1808 / IN1608 xi topology may be resolved from exact model identity and an authoritative fixed profile.

### Fixed DTP CrossPoint models

Only the exact DTP models named above may resolve to fixed logical topology. Unknown DTP2/DTP3/other DTP identities SHALL NOT match the DTP profile.

### XTP / XTP II

The application SHALL:

1. establish authoritative exact frame generation/identity;
2. select XTP or XTP II profile from that identity;
3. read matrix dimensions with the documented information query;
4. read installed I/O board configuration with the selected profile;
5. derive `available_input_ids` and `available_output_ids` without renumbering gaps caused by empty board slots;
6. use only those available IDs for polling, route reconciliation and GUI columns.

A missing board slot SHALL NOT cause later IDs to be compressed into lower numbers.

## Required General-information acquisition

Every exact Matrix model supported by this change SHALL be able to produce a
complete authoritative General-information tuple after a successful full refresh:

```text
Модель
MAC-адрес
Серийный номер
Версия прошивки
Температура
Время работы
```

Authority is fixed as follows:

- `Модель` comes from the accepted exact Matrix identity/canonical profile for the current operation.
- `MAC-адрес` first uses current canonical room/inventory evidence when present; if that evidence is absent, the selected exact device profile SHALL provide an authoritative read-only device fallback.
- `Серийный номер` first uses current canonical room/inventory evidence when present; if that evidence is absent, the selected exact device profile SHALL provide an authoritative read-only device fallback.
- `Версия прошивки`, `Температура`, and `Время работы` SHALL come from authoritative current device reads for the selected exact profile.

A full refresh SHALL NOT be classified as complete successful room-Matrix refresh
while any one of these six values is missing, malformed, stale, synthetic, or
unproven. Partial/incomplete/failed acquisition may present truthful `Нет данных`
for the missing row, but that state is not the successful-full-refresh acceptance
state required by this change.

### General-information acquisition matrix

This matrix is the pre-implementation acquisition authority. Status meanings are:

- `PROVEN` — the exact source/command and accepted grammar are already established
  by current approved architecture plus the cited official product programming
  documentation/hardware evidence.
- `PROVEN-INVENTORY-FIRST` — current canonical room/inventory evidence is the
  first authority and the listed exact device command is the approved fallback.
- `REQUIRED-PROVE (blocking)` — the product contract requires the value, but this
  change does not yet have an approved exact machine-readable command/source and
  response grammar for that profile. Production implementation for this change
  SHALL NOT start while any such cell remains.

```text
Profile group
  Field        Source / exact read                         Accepted response grammar                         Status / evidence
----------------------------------------------------------------------------------------------------------------------------------------------------------------
IN1804
  model        device 1I                                   closed IN1804 exact alias grammar                  PROVEN
  MAC          inventory first; fallback ECH}              00-05-A6-xx-xx-xx; verbose Iph•<MAC>             PROVEN-INVENTORY-FIRST
  serial       inventory first; device fallback TBD        no approved device grammar                        REQUIRED-PROVE (blocking)
  firmware     device Q                                    dotted firmware token / exact tagged form          PROVEN
  temperature  device E20STAT} (W20STAT equivalent)        two-digit Celsius; verbose 20Stat•<temp>          PROVEN
  uptime       device source TBD                           no approved machine-readable grammar               REQUIRED-PROVE (blocking)

IN1806 / IN1808
  model        device 1I                                   exact model token; verbose Inf01*<model>           PROVEN
  MAC          inventory first; fallback ECH}              00-05-A6-xx-xx-xx; verbose Iph•<MAC>             PROVEN-INVENTORY-FIRST
  serial       inventory first; device fallback TBD        no approved device grammar                        REQUIRED-PROVE (blocking)
  firmware     device Q                                    n.nn; verbose Ver01*n.nn                          PROVEN
  temperature  device E20STAT} (W20STAT equivalent)        two-digit Celsius; verbose 20Stat•<temp>          PROVEN
  uptime       internal Web UI visibly exposes Uptime,
               but exact machine read/grammar TBD          no approved machine-readable grammar               REQUIRED-PROVE (blocking)

IN1608 xi
  model        device 1I                                   closed exact IN1608 xi alias grammar               PROVEN
  MAC          inventory first; fallback ECH}              00-05-A6-xx-xx-xx; verbose Iph•<MAC>             PROVEN-INVENTORY-FIRST
  serial       inventory first; device fallback TBD        no approved device grammar                        REQUIRED-PROVE (blocking)
  firmware     device Q                                    dotted firmware token / exact tagged form          PROVEN
  temperature  device E20STAT} (W20STAT equivalent)        Celsius token / exact tagged form                  PROVEN
  uptime       device source TBD                           no approved machine-readable grammar               REQUIRED-PROVE (blocking)

DTP CrossPoint 84
  model        device I                                    exact DTPCP84 identity                             PROVEN
  MAC          inventory first; device fallback TBD        no approved exact fallback grammar in this change REQUIRED-PROVE (blocking)
  serial       inventory first; device fallback TBD        no approved device grammar                        REQUIRED-PROVE (blocking)
  firmware     device Q                                    x.xx                                               PROVEN
  temperature  device S                                    [Sts00*]voltage•tempC•fan1•fan2; temp is field 2  PROVEN
  uptime       device source TBD                           no approved machine-readable grammar               REQUIRED-PROVE (blocking)

DTP CrossPoint 82/84/86/108 4K
  model        device N                                    exact part-number / Pno<part-number> grammar       PROVEN
  MAC          inventory first; device fallback TBD        no approved exact fallback grammar in this change REQUIRED-PROVE (blocking)
  serial       inventory first; device fallback TBD        no approved device grammar                        REQUIRED-PROVE (blocking)
  firmware     device Q                                    x.xx                                               PROVEN
  temperature  device S                                    [Sts00*]voltage•tempC•future•future; field 2      PROVEN
  uptime       device source TBD                           no approved machine-readable grammar               REQUIRED-PROVE (blocking)

XTP CrossPoint 1600 / 3200
  model        device N + I + *N                            exact frame part-number plus approved topology     PROVEN
  MAC          inventory first; fallback ECH}              exact MAC token; verbose Iph tagged form           PROVEN-INVENTORY-FIRST
  serial       inventory first; device fallback TBD        no approved device grammar                        REQUIRED-PROVE (blocking)
  firmware     device Q                                    x.xx / profile-approved firmware token             PROVEN
  temperature  device S                                    profile positional status; internal temp in °F     PROVEN
  uptime       device source TBD                           no approved machine-readable grammar               REQUIRED-PROVE (blocking)

XTP II CrossPoint 1600 / 3200 / 6400
  model        device N + I + *N                            exact XTP II frame identity plus topology          PROVEN
  MAC          inventory first; fallback ECH}              exact MAC token; verbose Iph tagged form           PROVEN-INVENTORY-FIRST
  serial       inventory first; device fallback TBD        no approved device grammar                        REQUIRED-PROVE (blocking)
  firmware     device Q                                    x.xx / profile-approved firmware token             PROVEN
  temperature  device S                                    profile positional status; internal temp in °F     PROVEN
  uptime       device source TBD                           no approved machine-readable grammar               REQUIRED-PROVE (blocking)
```

Evidence references for the PROVEN rows are the exact product programming/user
guides already used by this change: IN1804 Series User Guide 68-3274-01_C;
IN1806 and IN1808 Series User Guide 68-3131-01_B; IN1608 xi Series User Guide
68-2290-02; DTP CrossPoint 84 Programming Guide 68-2349-01_D; DTP CrossPoint
4K Series User Guide 68-2368-02_R; and the exact first-generation XTP CrossPoint
and XTP II CrossPoint programming guides used for the approved frame/topology
profiles. Hardware evidence may confirm an already-approved grammar but SHALL NOT
silently create a new cross-family command contract.

The currently unresolved serial fallbacks and uptime machine reads are therefore
explicit architecture blockers across the supported scope; DTP MAC fallback is
also unresolved in this change. The product decision is to preserve the six-field
requirement and current model scope rather than weaken either one silently. Those
blocking cells SHALL be resolved by architecture/protocol research and reviewed
OpenSpec amendment before any production implementation session. A visible value
on a human web page is not sufficient unless a stable authenticated machine-readable
source and exact response/DOM/API grammar are separately approved.

The existing no-stale/no-secret/currentness rules apply to this tuple. A prior
successful value SHALL clear when the current full refresh cannot establish it;
old evidence SHALL NOT be retained merely to keep the card visually complete.

## GUI Design

The production room Matrix dashboard SHALL NOT expose hardware-QA/debug leftovers. `Отладка` is absent; the information card has no `IP-адрес` row, no embedded `!`/warning/action button, and no footer/action strip below the approved information fields. Existing room/global refresh authority remains outside that information card and does not create a Matrix-specific polling lane.

The Matrix table is dynamic:

```text
№ | Signal | HDCP | Input | <Output 1> | <Output 2> | ...
```

Output columns SHALL be generated from authoritative `available_output_ids`.

If an authoritative output name is available, it SHOULD be used as the heading; otherwise use deterministic `Output <id>` fallback. A single input MAY be active on multiple outputs simultaneously. An untied output has no active input cell.

Stale, failed, unsupported, unproven or otherwise unauthorized state remains non-actionable under existing Matrix mutation lifecycle rules.

## Migration / Compatibility

- Preserve existing IN1804 transport/session behavior and hardware-confirmed commands.
- Generalize parser/view-model to `routes` while retaining only a temporary single-output compatibility projection where needed.
- Do not silently promote `UNPROVEN` fields because another Extron family uses a similarly named SIS command.
- Do not regress existing Matrix route ambiguity/reconciliation protections.
- Do not start production implementation until the pre-implementation OpenSpec gate in `tasks.md` is fully PASS and independently approved.

## Inventory canonicalization

The offline inventory converter SHALL normalize model and name evidence into
components, evaluate the complete canonical match set for each field, and
reconcile their distinct union before selecting `diagnostic_model`. It SHALL
not use manufacturer text, substring matching, or registry order as model
authority.

Inventory rules may require components and forbid discriminating components.
The latter distinguishes DTP CrossPoint 84 from DTP CrossPoint 84 4K and
first-generation XTP CrossPoint from XTP II without priority. A bare IN1608
remains unresolved because `xi` is required. IN1806 remains a separate canonical
runtime model from IN1808 and resolves only from its own exact inventory evidence. Canonical inventory output uses
the exact runtime dispatch names, while original source-model text remains
source evidence.

## IN1804 wire identity compatibility

The inventory/application model `Extron IN1804` and protocol profile `IN1804`
remain canonical. The documented `1I` wire identities `IN1804`, `IN1804 DI`,
`IN1804 DO`, and `IN1804 DI/DO` resolve through one closed alias map to that
profile. The map is not a family substring rule: any other spelling or suffix
remains unsupported. Expected-model validation compares the resolved canonical
profile, so an IN1804 alias is accepted for expected IN1804 while a proved
IN1808 identity remains rejected.

The existing transport removes only an exact leading command echo before
identity resolution; subsequent payload validation stays exact.

## SIS identity framing

Identity evidence is processed in four distinct layers: transport removes only
an exact leading command echo; the protocol accepts only the documented grammar
for that command; the domain resolves the extracted value through a closed
canonical map; expected-model validation compares canonical profiles. `1I`
accepts only a bare model or `Inf01*<model>`; `N` accepts only a bare exact
part number or `Pno<part-number>`. These are not generic prefix stripping:
`Pno` is not model evidence and `Inf01*` is not part-number evidence. Multiple
records, trailing garbage, and unknown values remain fail-closed. The closed
IN1608 xi wire-alias map now additionally accepts the hardware-proven exact
`IN1608 xi IPCP SA` identity and no substring/prefix family inference. The DTP
CrossPoint 108 4K exact part-number map additionally accepts the hardware-proven
`60-1381-12`; adjacent suffixes remain unsupported unless separately approved.
IN1806 resolves as its own canonical profile from exact `IN1806` model identity
(and exact `60-1663-01` part-number evidence where that command is used).

## Deferred / Evidence-Dependent Items

- IN1808 Loop Out exposure remains deferred unless evidence and product intent explicitly include it.
- XTP/XTP II input/output names may remain unavailable where the approved deterministic presentation fallback applies.
- XTP II output-HDCP remains unavailable unless its exact command/decoder is proven before implementation.

The six General-information fields are explicitly excluded from this optional/deferred rule. Firmware, temperature, uptime, and any required device fallback for missing inventory MAC/serial must be proven for every in-scope model before complete implementation/hardware acceptance. Other unresolved optional diagnostics SHALL remain unavailable rather than encouraging speculative commands.

## Follow-up hardware compatibility

Closed documented IN1808 `1I` aliases resolve to canonical `IN1808`; unknown
suffixes fail closed. Legacy IN1804 list-shaped input HDCP/auth and scalar
output HDCP are normalized by the Matrix parser into canonical per-ID state
before either Matrix GUI surface consumes it.

## Hardware-QA GUI remediation

Room one-shot context remains the authority for the exact canonical Matrix
model: `diagnostic_model -> ExtronIN1804Worker.expected_model ->
ExtronIN1804Handler(expected_model=...)`. This avoids the old fallback-IN path;
the DTP CrossPoint 86 4K path must select DTP and issue `N`, never interpret the
wrong-path `1I -> DTPCP86` observation as an alias.

GUI consumes canonical `input_hdcp` only. `PRESENT_HDCP` is positive;
`PRESENT_NO_HDCP` and `ABSENT` are confirmed negative; and missing/`UNKNOWN`
is unavailable. HDCP authorization and output HDCP do not determine the input
presentation. Temperature is displayed only from the current accepted snapshot,
with unavailable data clearing the established empty field.

Read-only hardware evidence remains a separate gate: IN1804 recorded
`w20STAT=59`, input HDCP `0,1,0,1`, signal `0*1*0*1`, and route-read PASS;
IN1808 recorded `w20STAT=47`, input HDCP `0,1,1,1,0,0,0,0`, signal
`0*1*1*1*0*0*0*0`, and route-read PASS. Both acquired HDCP successfully, but
neither observed a positive active-HDCP (`2`) case. DTP CrossPoint 86 4K
transport/auth passed on the old wrong fallback path; post-fix hardware retest
is still required and its first identity assertion is `N` after authentication.

## 2026-09-23 Read-only hardware QA findings

The following observations are architecture evidence for this remediation and
must be reproduced by post-implementation hardware QA; they are not themselves
implementation completion:

- IN1608 xi hardware authenticated successfully and returned exact `1I` identity
  `IN1608 xi IPCP SA`; the previous closed resolver rejected that valid exact
  variant.
- DTP CrossPoint 108 4K hardware returned exact `N` part number `60-1381-12`;
  the previous exact allowlist did not contain it.
- A DTP CrossPoint 86 4K read-only poll successfully returned names and `0LS`
  signal evidence, then the old route poll sent `1!` and received `E13`.
  DTP canonical route authority is video-only: read `<O>%`, mutation
  `<I>*<O>%`, and video untie `0*<O>%`. Audio ties remain outside the current
  Matrix table and are not changed by this route intent.
- IN1806 hardware banner identified `IN1806`, firmware `V1.04`, part number
  `60-1663-01`. This change now includes IN1806 as a distinct six-input,
  one-main-route supported profile.
- Production room Matrix UI showed `Отладка`, an information-card IP row, an
  embedded `!` action, and trailing card action/footer space. Those elements
  are explicitly removed from the approved production presentation.

These observations invalidate the earlier archive readiness. Implementation,
independent revalidation, and read-only hardware QA must all be repeated on the
new published remediation HEAD before archive.
