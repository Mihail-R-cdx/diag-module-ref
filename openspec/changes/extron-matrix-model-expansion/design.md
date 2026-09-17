# Design: Extron matrix model expansion

## Context

Current Matrix behavior is centered on `ExtronIN1804Handler`, one logical routing output, and a scalar current route. The new scope adds both other single-output presentation switchers and true multi-output matrix frames.

The design must preserve the hardware-confirmed IN1804 behavior while making command syntax, topology and HDCP decoding explicit per family.

## Design Principles

### 1. Routing topology is not physical connector count

The application SHALL model independently routable endpoints rather than counting physical output connectors.

A device may expose multiple physical connectors that share one logical route. Those connectors SHALL NOT create duplicate GUI route columns.

### 2. Runtime authority comes from read-only evidence

Topology discovery SHALL use only read-only identity/configuration evidence.

State-changing route commands SHALL NOT be used to probe whether an input/output exists.

### 3. Exact SIS syntax belongs to a profile

No global Extron command table SHALL assume that all models use the same routing, naming, HDCP or topology syntax.

The common transport owns authentication/session/framing only. Family/model profiles own command generation and response interpretation.

### 4. Unproven is different from unsupported

If research has not established an authoritative command for a field, the capability SHALL be `UNPROVEN`/unavailable and the application SHALL NOT send a speculative SIS read.

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
    hdcp_profile,
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

The existing scalar `current_connection` may remain as a compatibility projection for single-output consumers during migration, but it SHALL NOT remain the authoritative routing representation.

## Capability / Command Profiles

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

The command terminator remains transport-owned.

This profile is intentionally based on the deployed, working implementation and SHALL NOT be rewritten merely to match an alternate canonical form shown in a manual.

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

Main scaled routing remains one logical route even when multiple physical output connectors share that route.

Loop-out routing, if included later, SHALL be represented as a distinct auxiliary routing endpoint/capability rather than pretending it is a second main matrix output.

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

### DTP CrossPoint profile

Routing is true multi-output matrix routing:

```text
identity             I
signal presence      0LS
input name N         W<N>NI
output name N        W<N>NO
input HDCP           WI<N>HDCP
output HDCP          WO<N>HDCP
read AV route O      <O>!
set AV route I->O    <I>*<O>!
untie O              0*<O>!
```

Fixed topology SHALL be resolved from authoritative exact-model identity/profile data.

DTP CrossPoint physical connector numbering MAY differ from logical routing-output numbering. GUI routing SHALL follow logical routing outputs.

Temperature remains `UNPROVEN` until an authoritative family/model command is established.

### XTP CrossPoint profile

Common matrix routing:

```text
matrix dimensions    I
installed boards     *N
signal presence      0LS
input HDCP           WI<N>HDCP
output HDCP          WO<N>HDCP
read AV route O      <O>!
set AV route I->O    <I>*<O>!
untie O              0*<O>!
```

Runtime topology SHALL combine matrix dimension evidence with installed-board evidence.

Input/output names and temperature remain `UNPROVEN` unless authoritative commands are established.

### XTP II CrossPoint profile

The same high-level topology/routing mechanism applies, but XTP II remains a separate capability profile because installed board types and supported diagnostics differ from first-generation XTP.

```text
matrix dimensions    I
installed boards     *N
signal presence      0LS
input HDCP           WI<N>HDCP
HDCP authorization   WE<N>HDCP
read AV route O      <O>!
set AV route I->O    <I>*<O>!
untie O              0*<O>!
```

Input/output names and temperature remain `UNPROVEN` until separately proven.

## HDCP Normalization

Raw values SHALL be decoded through the selected device profile.

### IN1804 / IN1808 input HDCP

```text
0 -> source absent
1 -> source present, HDCP absent
2 -> source present, HDCP present
```

### IN1608 xi / DTP CrossPoint / XTP CrossPoint / XTP II CrossPoint input HDCP

```text
0 -> source absent
1 -> source present, HDCP compliant/present
2 -> source present, HDCP non-compliant/absent
```

Normalized input states SHALL distinguish at least:

- `ABSENT`
- `PRESENT_HDCP`
- `PRESENT_NO_HDCP`
- `UNKNOWN`

Room presentation SHALL continue to derive its HDCP display from normalized input HDCP status, not HDCP authorization/configuration.

Output HDCP SHALL have a separate decoder because some CrossPoint families expose more output states than the input tri-state.

## Topology Discovery

### Fixed presentation switchers

IN1804 / IN1808 / IN1608 topology may be resolved from exact model identity and an authoritative fixed profile.

### Fixed DTP CrossPoint models

Exact model identity SHALL resolve a known fixed logical matrix topology.

### XTP / XTP II

The application SHALL:

1. read matrix dimensions with the documented information query;
2. read installed I/O board configuration;
3. derive `available_input_ids` and `available_output_ids` without renumbering gaps caused by empty board slots;
4. use only those available IDs for polling, route reconciliation and GUI columns.

A missing board slot SHALL NOT cause later physical/logical IDs to be compressed into lower numbers.

## GUI Design

The Matrix table SHALL be dynamic:

```text
№ | Signal | HDCP | Input | <Output 1> | <Output 2> | ...
```

Output columns SHALL be generated from `available_output_ids`.

If an authoritative output name is available, it SHOULD be used as the column heading; otherwise a deterministic fallback such as `Output <id>` SHALL be used.

A single input MAY be active on multiple outputs simultaneously.

An untied output SHALL have no active input cell.

Stale, failed, unsupported, unproven or otherwise unauthorized state SHALL remain non-actionable in accordance with the existing Matrix mutation lifecycle.

## Migration / Compatibility

- Preserve existing IN1804 transport/session behavior and hardware-confirmed commands.
- Generalize the parser/view-model to `routes` while retaining a temporary single-output compatibility projection where needed.
- Do not silently promote `UNPROVEN` fields to supported because another Extron family uses a similarly named SIS command.
- Do not regress existing Matrix route ambiguity/reconciliation protections.

## Open Questions That Do Not Block Architecture

- Whether IN1808 Loop Out should be exposed in the first implementation as an auxiliary routing endpoint or deferred.
- Whether additional authoritative name/temperature commands can be established for XTP/XTP II/DTP variants before implementation.

These questions SHALL be resolved by evidence; unresolved optional diagnostics SHALL remain unavailable rather than blocking core routing/topology support.