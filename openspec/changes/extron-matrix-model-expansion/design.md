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

If research has not established an authoritative command for a field, the capability SHALL be `UNPROVEN`/unavailable and the application SHALL NOT send a speculative SIS read.

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
    route_profile,
    input_hdcp_profile,
    output_hdcp_profile,
)
```

Normalized runtime state:

```python
MatrixState(
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
read main route      1!
set main route       <I>*1!
```

Inputs 7 and 8 are unavailable for IN1806 and SHALL NOT be fabricated from the
IN1808 profile. The separate HDMI loop output is not a second main routing column;
loop-out exposure remains outside generalized main-route authority unless separately
approved.

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
read main route      1!
set main route       <I>*1!
```

Main scaled routing remains one logical route even when multiple physical output connectors share that route. Loop-out routing is deferred unless separately proven and accepted as an auxiliary endpoint in this change; it SHALL NOT be silently counted as a second main matrix output.

### IN1608 xi profile

```text
identity             1I
temperature          W20STAT
input name N         W<N>NI
signal presence      W0LS
HDCP authorization   WE<N>HDCP
input HDCP           WI<N>HDCP
output HDCP          WO<N>HDCP
read route           !
set route            <I>!
```

Output-name read remains `UNPROVEN` unless separately established.

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

Fixed topology SHALL be resolved from exact-model identity/profile data. Physical connector numbering MAY differ from logical routing-output numbering; GUI routing follows logical routing outputs. Temperature remains `UNPROVEN` until authoritative evidence is established.

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

Input/output names and temperature remain `UNPROVEN` unless authoritative commands are established.

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

Input/output names and temperature also remain `UNPROVEN` until separately proven.

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
- XTP/XTP II names and temperature remain unavailable unless proven before implementation.
- XTP II output-HDCP remains unavailable unless its exact command/decoder is proven before implementation.

Unresolved optional diagnostics SHALL remain unavailable rather than blocking core routing/topology support or encouraging speculative commands.

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
