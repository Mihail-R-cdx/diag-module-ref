## ADDED Requirements

### Requirement: Exact IN1808 audio diagnostics use a separate read-only DSP profile

The exact canonical application model `Extron IN1808` SHALL expose an
IN1808-specific audio diagnostic capability without changing the existing
video-only Matrix route authority. The existing video route remains `1%` for
read and `<I>*1%` for mutation.

The audio capability SHALL use only the approved IN1808 audio profile. It SHALL
NOT reuse DMP 64 Plus meter enable semantics, SHALL NOT infer support for another
Matrix model from family similarity, and SHALL NOT expose audio routing, gain,
mute, volume, or DSP configuration mutation.

The application SHALL preserve the exact accepted IN1808 `1I` wire identity
as variant evidence while retaining canonical application identity
`Extron IN1808`. Variant evidence MAY restrict amplifier meter/routing
capability; it SHALL NOT relabel the application model.

#### Scenario: IN1808 audio capability does not change video route authority

- **GIVEN** the exact current device is canonical `Extron IN1808`
- **WHEN** Audio diagnostics are available
- **THEN** video route read/mutation remains `1%` / `<I>*1%`
- **AND** the Audio diagnostic path uses its separate read-only DSP profile
- **AND** no Audio mix-point mutation is authorized

#### Scenario: Another Matrix model does not inherit IN1808 Audio capability

- **GIVEN** the current exact Matrix model is not `Extron IN1808`
- **WHEN** application capability is resolved
- **THEN** this IN1808 Audio diagnostic capability is unavailable
- **AND** runtime does not infer it from Matrix screen identity or a model substring

### Requirement: IN1808 Audio Name reads preserve stable channel identity

The IN1808 audio profile SHALL read supported audio names using
`WI<N>ANAM` for approved audio input IDs and `WO<N>ANAM` for approved audio
output IDs. Blank, malformed, or unavailable name evidence SHALL use a
deterministic semantic fallback label without changing channel IDs or topology.

The profile SHALL support input-name identities 1 through 15 and output-name
identities 1 through 7 only where mapped by the approved IN1808 audio topology.
Variant-derived amplifier labeling is not fabricated as an eighth ANAM output.

#### Scenario: Audio name is unavailable

- **GIVEN** one approved IN1808 audio-name query returns no authoritative name
- **WHEN** the normalized audio snapshot is built
- **THEN** the same channel ID remains present with its deterministic fallback label
- **AND** no neighboring name is shifted or reused

### Requirement: IN1808 live meters preserve raw evidence and use IN1808 state semantics

The IN1808 audio profile SHALL support approved meter OIDs in the 300xx, 400xx,
and 600xx domains. A meter read uses `V<OID>AU` and accepts only the
IN1808-observed state/value grammar.

Before changing meter-update instrumentation state, the application SHALL read
the current state. It SHALL send `V<OID>*1AU` only when the accepted current
state is 0 and SHALL remember that this exact audio subcontext changed that OID.
It SHALL never send the DMP `*2` enable value.

The hardware evidence does not establish whether meter-update state is
connection-local, session-local, or device-global. Therefore production cleanup
under this change SHALL NOT send `V<OID>*0AU`. Cleanup stops polling and
retires/quiesces through the existing Matrix LIVE boundary without claiming
ownership of the device meter-update state.

A possible-send failure on `V<OID>*1AU` SHALL NOT be blindly replayed. One
read MAY reconcile the state only while the same exact current session remains
safe; otherwise the affected Audio meter becomes unavailable.

Normalized meter evidence SHALL retain at least OID, raw meter value, meter
state, availability/outcome, derived dBFS and normalized fill when derivation is
valid. The accepted Extron DSP display conversion is `dbfs = -(raw / 10.0)`;
raw evidence remains preserved independently.

#### Scenario: Meter starts from state zero

- **GIVEN** an approved current meter read returns state 0
- **WHEN** the current IN1808 Audio subcontext activates that meter
- **THEN** it sends `V<OID>*1AU` once
- **AND** it never substitutes `*2`
- **AND** later accepted `V<OID>AU` reads may publish current meter values

#### Scenario: Existing active meter state is preserved

- **GIVEN** an approved current meter read already returns state 1
- **WHEN** Audio live polling starts
- **THEN** the application does not send a redundant enable command
- **AND** cleanup sends no `*0` because ownership/scope is unproven

#### Scenario: Meter state was zero and this Audio mode enabled it

- **GIVEN** the current Audio subcontext observed state 0 and successfully sent `*1`
- **WHEN** Audio mode later ends
- **THEN** the application stops polling without sending `*0`
- **AND** it does not reconnect solely to modify meter-update state

### Requirement: IN1808 current Program source is mandatory read-only metadata

On Audio-mode metadata acquisition, the IN1808 profile SHALL issue `1$` to
read the audio source for output 1. Accepted values `1..9` SHALL normalize to
DP 1, HDMI 2..6, TP 7..8, or Aux In respectively. Any error, missing response,
malformed value, or value outside `1..9` SHALL normalize to UNKNOWN.

This audio-source authority is separate from existing video `1%` authority.
It SHALL NOT alter, replace, or reconcile the video Matrix route.

#### Scenario: Audio breakaway source is known

- **WHEN** `1$` returns an accepted input ID from 1 through 9
- **THEN** the normalized Audio snapshot identifies that physical source as
  feeding `Program L/R`
- **AND** existing video route state remains unchanged

#### Scenario: Audio source read is unavailable

- **WHEN** `1$` fails or returns unsupported evidence
- **THEN** current Program physical source is UNKNOWN
- **AND** the DSP routing rows remain present without guessing from `1%`

### Requirement: IN1808 stereo meter groups combine display level without losing component evidence

Approved stereo source/output groups SHALL render one logical meter using the
maximum available dBFS across left/right components. The normalized snapshot
SHALL retain both component OIDs and outcomes.

A missing side SHALL NOT be replaced with a fabricated value. If one side is
valid and the other unavailable, the group MAY display the valid level only
with a structured partial outcome.

#### Scenario: Stereo sides have different levels

- **GIVEN** an approved stereo group has valid left and right dBFS values
- **WHEN** the logical display meter is derived
- **THEN** its displayed dBFS equals the greater of the two dBFS values
- **AND** both original component values remain available as evidence

### Requirement: IN1808 DSP routing snapshot is read-only and fail-closed

The accepted IN1808 DSP mix-point domain SHALL use the bounded address formula:

```text
oid = 20000 + input_row * 100 + output_column
input_row = 0..7
output_column = 0..11 before exact-variant filtering
```

A routing read uses `M<oid>AU`. Accepted `0` means an unmuted/open
crosspoint and accepted `1` means a muted/closed crosspoint. Any protocol
error, missing response, other value, or malformed response SHALL normalize to
UNKNOWN rather than an inferred route.

The row semantics Program L/R, Mic/Line 1/2, Line In 3/4 and File Player L/R,
and the output semantics HDMI L/R, TP/DTP L/R, DTP Analog L/R, Line Out 1..4
plus exact-variant amplifier channels are an explicitly adopted exact-profile
mapping named `IN1808_PRODSP_PROFILE_MAPPING`. The mapping is based on the
official IN1808 signal flow plus established Extron ProDSP OID ordering but was
not hardware-cross-checked cell-by-cell.

Runtime SHALL fail closed for OID bounds, exact-variant applicability, protocol
errors, missing/malformed responses, and values other than `0/1`. Runtime
SHALL NOT claim that a valid `0/1` response independently proves the semantic
row/column labels. Variant capability SHALL remove non-applicable amplifier
columns before command generation.

This change SHALL generate no state-changing `M<oid>*<value>AU` command.

#### Scenario: Mix-point read returns a supported value

- **WHEN** an applicable IN1808 mix-point read returns `0` or `1`
- **THEN** the normalized route cell is ACTIVE for `0` or INACTIVE for `1`
- **AND** no mutation command is sent

#### Scenario: Mix-point protocol evidence is unavailable

- **WHEN** a mix-point response is malformed, unsupported, missing, or outside
  the exact variant capability
- **THEN** the affected route state is UNKNOWN/unavailable
- **AND** the implementation does not shift indices, guess another topology, or
  mutate the device

#### Scenario: Valid mix-point response does not prove semantic mapping

- **WHEN** an in-range mix-point OID returns valid `0/1` evidence
- **THEN** ACTIVE/INACTIVE is authoritative for that queried OID
- **AND** its source/output labels come from `IN1808_PRODSP_PROFILE_MAPPING`
- **AND** runtime does not claim to have hardware-verified those labels from the response

### Requirement: Exact IN1808 Video batching uses a hardware-proven guard with bounded correlation

For exact canonical `Extron IN1808`, a legitimate fresh full Video status
operation SHALL replace the legacy long sequential fan-out with the exact
hardware-proven guarded read-only transaction below:

```text
standalone authoritative 1I

one serialized batch:
    1I
    Q
    w20STAT
    wE1HDCP
    wI1HDCP
    ...
    wE8HDCP
    wI8HDCP
    wO1HDCP
    wI1VNAM
    ...
    wI8VNAM
    wO1VNAM
    w0LS
    1%

standalone post-batch 1I
```

The first in-batch `1I` is a sacrificial read-only framing guard. Accepted
hardware evidence on exact `IN1808 IPCP SA` shows that the first query payload
is omitted in a CR-separated multi-query write while later payloads remain
ordered; with the guard present, all 30 required `Q` through `1%` payloads
were returned in order and the post-batch session remained usable.

The Matrix application owner SHALL execute this batch as one serialized
operation with no overlapping application Matrix I/O on the same session.
After removing only the exact aggregate submitted-command echo, the parser SHALL
require exactly 30 useful payload records corresponding positionally to `Q`
through `1%`. The accepted production shape expects the guard payload to be
omitted.

Every useful payload SHALL pass its existing command-specific parser. Any
detectable `E##`, malformed, missing, extra, guard-return, framing/order
mismatch, parser failure, or mismatched/unavailable post-batch exact identity
SHALL fail the complete Video batch closed. No later payload may be deliberately
shifted to repair a detected mismatch.

The response protocol is untagged and some adjacent fields share the same
grammar. This change therefore does not claim that hardware testing can prove
the universal absence of every possible delayed, unsolicited, duplicated, or
stale same-grammar payload. The architecture explicitly accepts the bounded
residual risk that such an undetectable payload could replace a missing
positional payload while all detectable checks still pass.

That residual risk is accepted only for this read-only diagnostic snapshot. A
batched Video result SHALL NOT authorize route mutation, state-changing replay,
credential fallback, or any conclusion that a state-changing command succeeded.
If future evidence demonstrates response contamination that defeats this
bounded contract, exact-IN1808 batching SHALL be disabled or replaced by a
stronger separately approved correlation mechanism.

Batch support SHALL NOT be generalized to another Matrix model without separate
protocol evidence.

#### Scenario: Guarded hardware-proven batch is accepted

- **GIVEN** standalone `1I` establishes the accepted exact IN1808 identity
- **AND** the serialized guarded batch returns exactly 30 useful payload records after its exact aggregate echo
- **AND** each record passes the parser for its corresponding `Q` through `1%` field
- **AND** the post-batch standalone `1I` returns the same accepted exact IN1808 identity
- **WHEN** the Video snapshot is normalized
- **THEN** the 30 payloads may be accepted positionally for this read-only snapshot
- **AND** no mutation authority is created

#### Scenario: Detectable batch ambiguity fails closed

- **WHEN** the guarded batch contains an `E##`, malformed, missing, extra,
  returned-guard, framing/order mismatch, or field-specific parser failure
- **OR** the post-batch exact identity check fails or mismatches
- **THEN** the complete Video batch is rejected
- **AND** no payload is shifted to a neighboring Video field
- **AND** no route mutation is generated

#### Scenario: Same-grammar substitution is an explicit residual limitation

- **GIVEN** the SIS response stream is untagged
- **AND** two distinct expected fields can share the same accepted wire grammar
- **WHEN** a hypothetical delayed, unsolicited, duplicated, or stale payload is
  indistinguishable from the missing positional payload by all available
  count/framing/field-parser checks
- **THEN** this change does not claim that the substitution is detectable
- **AND** the accepted risk is limited to read-only diagnostic evidence
- **AND** that evidence cannot authorize a state-changing operation

#### Scenario: Another Matrix model keeps its existing acquisition contract

- **GIVEN** the current exact Matrix model is not canonical `Extron IN1808`
- **WHEN** full Video status is acquired
- **THEN** this change does not infer IN1808 batch support from family similarity
