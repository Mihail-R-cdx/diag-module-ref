# Design: IN1808 audio routing meters

## Context and change base

Architecture base:

```text
repository  Mihail-R-cdx/diag-module-ref
master      5d2d44298334fc77741dab50652ca7e8472a7d76
change      in1808-audio-routing-meters
```

Current production IN1808 behavior is owned by the exact Matrix profile,
`MatrixController`, `matrix_one_shot`, `matrix_room_live`, and the room
projection `RoomReadOnlyPresentation._build_matrix()`.

The current IN1808 Matrix table is deliberately video-only. Its canonical route
read is `1%` and route mutation is `<I>*1%`; audio breakaway/DSP routing is
not part of that video route map. This change preserves that separation.

The modern Audio DSP room presentation already establishes the desired meter
visual language (vertical segmented dBFS indicators), but its DMP handler,
polling controller, wire semantics, and screen identity are not IN1808
authorities and must not be reused as such.

## Protocol evidence baseline

The following observations were made read-only on real IN1808 hardware except
for the meter-update instrumentation state commands explicitly shown below.
They are architecture evidence for this change, not a claim that every IN1808
variant has been exhaustively hardware-tested.

### Audio names

Observed:

```text
WI1ANAM| -> Audio Input 1
WO1ANAM| -> Audio Output 1
```

The Audio Name command family is therefore accepted for IN1808. Production
syntax uses the existing Extron convention where `W` is the web/SIS form of
the documented Escape command and the transport owns the terminator.

### Meter command family

Before enabling updates, representative OIDs in all three relevant domains
returned the meter-shaped response `0*0`:

```text
WV30002AU|
WV40000AU|
WV60000AU|
```

For OID 40000:

```text
WV40000*2AU| -> E13
WV40000*1AU| -> DsV40000*1
WV40000AU|   -> 1*972
```

Repeated reads while state `1` was active returned changing meter values.

After:

```text
WV40000*0AU|
```

repeated reads returned `0*988`, with the value frozen. This establishes for
the observed IN1808:

```text
V<OID>*1AU  start/update meter sampling
V<OID>*0AU  stop/freeze meter sampling
V<OID>*2AU  invalid (E13)
V<OID>AU    read state * current-or-last sample
```

Representative 300xx and 600xx OIDs also accepted `*1` and returned
`1*<changing four-digit value>`. The existing DMP 64 Plus `*2` recovery
semantics therefore SHALL NOT be reused for IN1808.

### DSP mix-point address space

Observed read-only probes:

```text
WM20000AU| -> 0
WM20001AU| -> 1
WM20100AU| -> 1
WM20011AU| -> 1
WM20012AU| -> E13
WM20700AU| -> 1
WM20800AU| -> E13
WG20000AU| -> 0
WM29999AU| -> E13
```

This proves an accepted rectangular `8 x 12` mix-point address domain with
the Extron ProDSP-style address formula:

```text
oid = 20000 + input_row * 100 + output_column

input_row     0..7
output_column 0..11
```

The exact semantic row/column ordering below is derived from the official
IN1808 DSP signal-flow ordering plus the established Extron ProDSP mix-point
convention. It was not visually cross-correlated against PCS before the fixture
became unavailable.

Current hardware evidence cannot detect a semantic permutation inside the valid
8 x 12 rectangle: a response such as `WM20200AU| -> 0` contains no signal
identity. Because further fixture testing is unavailable and the product
decision is to proceed from the available evidence, this change explicitly
adopts the row/column semantic map as an architecture assumption named
`IN1808_PRODSP_PROFILE_MAPPING`.

Runtime fail-closed behavior applies to exact-model/variant applicability, OID
bounds, protocol errors, missing responses, and malformed/unsupported values.
It SHALL NOT claim to prove the semantic row/column labels from a normal `0/1`
response. The adopted mapping is isolated in one exact IN1808 audio profile so
future authoritative evidence can correct that profile without changing the
generic Matrix/video contract.

The adopted read-only meaning of `M<oid>` is the documented ProDSP mix-point
mute convention:

```text
0 -> unmuted/open crosspoint
1 -> muted/closed crosspoint
```

No `M<oid>*<value>AU` mutation is authorized by this change.

## Exact IN1808 audio capability

Audio mode is available only for exact canonical `Extron IN1808`. Presentation
must not infer support from `screen_key == "matrix"`, an `IN` substring, the
presence of an `ANAM` field, or another Matrix model.

The unified application capability registry SHALL publish an explicit
IN1808-audio capability consumed by room composition.

The canonical application model remains `Extron IN1808`. The exact `1I`
wire identity SHALL additionally be preserved as variant evidence so
variant-dependent amplifier capability can be resolved without changing the
application model.

Accepted current closed identities remain the existing IN1808 identity set:

```text
IN1808
IN1808 IPCP SA
IN1808 IPCP MA 70
IN1808 IPCP Q SA
IN1808 IPCP Q MA 70
```

Unknown suffixes remain unsupported/fail-closed.

## Audio meter topology

### Source/input meter groups

The normalized presentation SHALL expose these logical meter groups in stable
order:

| Display group | Audio-name identity | Meter OID components |
| --- | --- | --- |
| DP 1 | input 1 | 30000 L, 30001 R |
| HDMI 2 | input 2 | 30002 L, 30003 R |
| HDMI 3 | input 3 | 30004 L, 30005 R |
| HDMI 4 | input 4 | 30006 L, 30007 R |
| HDMI 5 | input 5 | 30008 L, 30009 R |
| HDMI 6 | input 6 | 30010 L, 30011 R |
| TP 7 | input 7 | 30012 L, 30013 R |
| TP 8 | input 8 | 30014 L, 30015 R |
| Aux In | input 9 | 30016 L, 30017 R |
| Mic/Line 1 | input 10 | 40000 |
| Mic/Line 2 | input 11 | 40001 |
| Line In 3 | input 12 | 40002 |
| Line In 4 | input 13 | 40003 |
| File Player | inputs 14/15 | 40004 L, 40005 R |

For a stereo group, presentation uses one meter:

```text
display_dbfs = max(available_left_dbfs, available_right_dbfs)
```

The normalized payload SHALL retain both component OIDs/raw values/states so
one missing channel is not hidden. A group with one valid side and one
unavailable side MAY display the valid level but SHALL carry a partial
structured outcome.

### Output meter groups

Stable logical groups:

| Display group | Audio-name identity | Meter OID components |
| --- | --- | --- |
| HDMI 1A | output 1 | 60000 L, 60001 R |
| TP/DTP 1B | output 2 | 60002 L, 60003 R |
| DTP Analog | output 3 | 60004 L, 60005 R |
| Line Out 1 | output 4 | 60006 |
| Line Out 2 | output 5 | 60007 |
| Line Out 3 | output 6 | 60008 |
| Line Out 4 | output 7 | 60009 |
| Amplifier | fixed variant label | 60010 and, where applicable, 60011 |

The amplifier group is model-variant dependent:

- base `IN1808`: no amplifier group;
- `... SA` variants: stereo amplifier, use both 60010/60011 and one combined
  displayed meter;
- `... MA 70` variants: mono amplifier, use only the documented mono path;
- an unknown/unrecognized wire identity does not gain amplifier capability.

The implementation SHALL not send speculative amplifier meter/routing reads
outside the accepted exact variant capability.

## Meter units and normalized presentation

The meter response payload is preserved as raw evidence:

```text
state * raw_meter
```

The accepted presentation conversion follows the Extron DSP meter convention
already used by the project:

```text
dbfs = -(raw_meter / 10.0)
```

This scaling is family-convention evidence rather than an IN1808-specific
published meter table captured during the hardware session. For that reason the
normalized snapshot SHALL retain `raw_meter` as well as derived `dbfs`.
Malformed, negative, non-integral, or otherwise unsupported raw payloads fail
closed as unavailable rather than being coerced.

For the visual meter, reuse the existing modern Audio DSP presentation scale
and 20-segment quantization contract. Values below the visual floor remain
numerically visible while the fill clamps at the floor.

## Meter instrumentation state lifecycle

The hardware session proved that `*1` starts changing meter samples and `*0`
freezes them, but it did not establish whether that update state is scoped to
one SIS connection/session or is device-global. A normal state read contains no
ownership identity. Therefore this change SHALL NOT claim that it can restore
"our" prior meter state without affecting another client.

For every exact meter OID that the application intends to poll:

1. Read `V<OID>AU` first and record the observed state.
2. If state is `0`, send `V<OID>*1AU` at most once for the current Audio
   subcontext.
3. If state is already `1`, do not send an enable command.
4. Never send `*2`.
5. Poll only OIDs whose accepted current state is active.
6. On Audio-mode cleanup, stop scheduling meter reads and wait/cancel through
   the existing Matrix LIVE cleanup boundary. Under the current evidence,
   production SHALL NOT send `V<OID>*0AU` as cleanup.
7. A possible-send failure on `*1` is not blindly replayed. If the same
   generation/current session remains safe, one read MAY reconcile whether
   state became `1`; otherwise the affected Audio meter becomes unavailable.

If meter-update state is device-global, a `0 -> 1` transition may remain
enabled after this application stops polling. That limited instrumentation
side effect is explicitly accepted because disabling it cannot be ownership-safe
with current evidence. A later change may add `*0` restoration only after
authoritative evidence proves an ownership/scope rule that makes restoration
safe.

Meter update state is instrumentation only. It is not audio signal, gain, mute,
route, or device configuration authority and never authorizes audio-routing
mutation.

## DSP routing topology

### Row domain

The adopted routing rows are the eight DSP sources shown by the IN1808 signal
flow:

```text
row 0  Program L
row 1  Program R
row 2  Mic/Line 1
row 3  Mic/Line 2
row 4  Line In 3
row 5  Line In 4
row 6  File Player L
row 7  File Player R
```

The physical DP/HDMI/TP/Aux switcher inputs are not fabricated as independent
DSP mix-matrix rows. They remain visible in the source-meter group.

Audio-mode metadata acquisition SHALL issue the documented read-only `1$`
query for output 1. Accepted values `1..9` identify the current physical
audio source feeding `Program L/R`:

```text
1  DP 1
2  HDMI 2
3  HDMI 3
4  HDMI 4
5  HDMI 5
6  HDMI 6
7  TP 7
8  TP 8
9  Aux In
```

Any error, missing response, malformed value, or value outside `1..9`
normalizes to `UNKNOWN`. This audio-source read is independent from the
existing video route query `1%` and SHALL NOT replace or reconcile video
routing.

The Audio UI SHALL make the current physical audio source visible as the source
feeding both `Program L` and `Program R`; when it is UNKNOWN, those DSP rows
remain present but the physical-source link is explicitly UNKNOWN.

### Column domain

Internal output columns follow the published IN1808 output signal-flow order:

```text
0   HDMI L
1   HDMI R
2   TP/DTP L
3   TP/DTP R
4   DTP Analog L
5   DTP Analog R
6   Line Out 1
7   Line Out 2
8   Line Out 3
9   Line Out 4
10  Amplifier L / Mono
11  Amplifier R
```

Variant capability filters the visible/probed amplifier columns. Base IN1808
does not receive amplifier columns; mono variants do not fabricate a right
amplifier channel.

### Read-only route state

For every applicable cell:

```text
WM<oid>AU|
oid = 20000 + row * 100 + column
```

Accepted state:

```text
0 -> ACTIVE / unmuted crosspoint
1 -> INACTIVE / muted crosspoint
other / error / malformed -> UNKNOWN
```

`UNKNOWN` is visibly distinct and non-authoritative. No route cell is
clickable and no state-changing `M` command exists in this change.

These ACTIVE/INACTIVE values are protocol-authoritative only for the queried
OID. Their source/output labels come from the explicitly adopted
`IN1808_PRODSP_PROFILE_MAPPING`; runtime cannot independently verify that
semantic mapping from a normal `0/1` response. The normalized routing
snapshot SHALL retain a safe `mapping_basis` value identifying that profile so
presentation/tests do not misrepresent it as hardware-cross-checked mapping.

Routing acquisition is a diagnostic snapshot, not a 1 Hz stream. It is read on
Audio-mode entry after exact context/session authority is established. While
Audio mode remains open, live cadence is reserved for meters; routing is not
re-read every meter tick. Re-entering Audio or an accepted current refresh may
obtain a new routing snapshot.

This avoids an unnecessary continuous 96-cell command load while keeping the
view deterministic and read-only.

## Audio names

Read names through the accepted IN1808 Audio Name family:

```text
WI<N>ANAM|   audio inputs
WO<N>ANAM|   audio outputs
```

Input IDs 1..15 and output IDs 1..7 are consumed only according to the exact
audio topology above. Missing/blank/malformed name evidence uses deterministic
semantic fallback labels; it never removes the channel or shifts IDs.

For a combined stereo File Player group, differing L/R names remain preserved
as component evidence; presentation may use a deterministic combined label.
Amplifier labeling is variant-derived because it is not part of the seven
named output IDs.

## Application/session ownership

The new Audio capability SHALL extend the existing IN1808 Matrix application
owner; it SHALL NOT create a parallel screen, controller, credential planner,
or persistent transport.

```text
Room exact IN1808 row
  -> unified exact-model capability
  -> existing matrix_room_live / MatrixController owner
  -> one serialized Matrix SIS session
       -> existing video/status operations
       -> IN1808 audio metadata/routing snapshot
       -> IN1808 meter poll operations
```

All SIS I/O remains off the Qt GUI thread. The existing Matrix serialized owner
lock/session authority SHALL prevent overlapping command/response ownership.
A meter tick schedules background work only when the previous audio poll has
completed; ticks do not queue an unbounded backlog.

The target cadence is approximately one accepted meter snapshot per second
where transport throughput permits. A cycle never overlaps the next cycle; if
one full meter cycle takes longer than the target interval, the next cycle
starts only after completion/currentness checks.

Handler/transport code receives one application-selected credential. It does
not iterate candidates. Audio mode does not create an independent credential
fallback loop.

## Room lifecycle and currentness

Default expanded IN1808 mode is Video.

Selecting `Аудио`:

1. changes local row mode to Audio and the same control text to `Видео`;
2. composition revalidates current room identity + exact record + exact
   `Extron IN1808` capability;
3. starts the IN1808 audio subcontext on the existing Matrix owner;
4. acquires names/routing metadata and then live meter snapshots;
5. accepts callbacks only for the exact current room/record/audio generation.

Selecting `Видео` changes presentation immediately but requests orderly
Audio-subcontext quiescence. It does not refresh or mutate video routing merely
because the mode changed. Until the Audio subcontext has no in-flight meter
operation and has reached its cleanup boundary, network-backed Video actions
remain disabled/rejected.

Audio cleanup is also mandatory on:

- IN1808 row collapse;
- expanding another row;
- room/search/target replacement;
- record replacement/removal;
- credential-context revision;
- Matrix context invalidation;
- application shutdown.

Stale audio work is rejected before handler acquisition/I/O when possible and
again before accepted presentation update. A callback from an old Audio
generation cannot restore Audio mode, meter values, names, routing cells,
selection, or instrumentation authority in a replacement context.

### Serialized interaction-lane handoff

IN1808 Audio polling is a specialization of the existing
`RoomInteractionKind.LIVE` authority, not a sixth lifecycle kind. Existing
root ordering remains normative:

```text
LIVE
LOCAL_REFRESH
AUXILIARY_READ
MUTATION
RECONCILIATION
```

At most one of those network lifecycle kinds owns or awaits Matrix resources.

- A Video route mutation confirmed while Audio LIVE is active SHALL first
  invalidate/retire the existing Matrix LIVE through the approved bounded
  cleanup/release boundary. If that boundary is not reached, the route SHALL
  NOT be sent.
- Local Refresh while Audio LIVE is active SHALL likewise wait for/require the
  existing bounded LIVE cleanup before its handler/session acquisition; it
  SHALL not overlap a meter cycle.
- Once Matrix MUTATION begins, Audio polling SHALL remain stopped. Mandatory
  RECONCILIATION starts only after the existing mutation release boundary, and
  Audio/other LIVE work SHALL not resume until reconciliation is terminal and
  cleanup permits it.
- Switching Audio -> Video is allowed as an immediate local presentation
  change, but Video route/Local Refresh network actions remain locked until the
  Audio subcontext is quiescent. Their later admission still follows the
  ordinary LIVE-retirement contract above.

The existing coordinator/session retirement timeout policy is not weakened.
Audio mode cannot bypass a failed cleanup boundary to acquire route,
Local Refresh, or reconciliation transport authority.

## GUI: Variant B

The expanded IN1808 row retains the existing left `Общая информация` card
unchanged.

The row header gains one exact-IN1808 mode control aligned with model/status:

```text
Video mode:  [Аудио]
Audio mode:  [Видео]
```

Only the right tile changes.

### Video mode

The existing Matrix routing table remains unchanged and keeps its existing
video route authority/actions.

### Audio mode

The right tile contains:

1. a compact all-source meter band exposing every input/source meter group;
2. a current Program-source indicator from mandatory `1$` metadata, binding
   DP/HDMI/TP/Aux input 1..9 to the `Program L/R` DSP rows;
3. a read-only DSP routing matrix using the 8 x variant-filtered output-channel
   domain;
4. compact output meters associated with output header groups.

Routing axes stay channel-accurate. Stereo routing channels therefore remain
L/R subchannels; stereo meter presentation is combined to one meter per logical
stereo group. Presentation must not collapse four possible L/R crosspoints into
one boolean route cell.

The meter visual language reuses the modern room Audio DSP segmented dBFS
presentation, not the legacy standalone horizontal `AudioDSPScreen` bars.

Audio route cells are non-interactive. They visibly distinguish at least:

```text
ACTIVE
INACTIVE
UNKNOWN
```

Color alone is not sufficient; accessible/non-color state must remain present.
The Audio routing surface SHALL also expose safe non-interactive metadata
equivalent to `Карта каналов: профиль IN1808` (for example caption/tooltip or
accessibility description) so the adopted profile mapping is not presented as
hardware-cross-checked discovery.

## Failure isolation

An Audio-mode protocol/parse/timeout failure:

- clears current Audio live evidence that cannot be established;
- shows a safe Audio-specific no-data/error state;
- does not fabricate `0 dBFS`, a route, or a name;
- does not change accepted General information;
- does not change the last accepted video Matrix snapshot;
- does not mark the whole IN1808 row failed solely because optional Audio live
  diagnostics failed.

A failure that invalidates the shared physical Matrix session may retire that
session under existing Matrix lifecycle rules, but already accepted room
evidence remains governed by existing currentness/staleness contracts.

No secrets, raw credentials, command echoes, exception internals, or unsafe raw
transport text are rendered in the GUI.

## Standalone boundary

This change targets the room expanded exact-row surface only.

The standalone `MatrixScreen` remains a separate supported surface and is not
redesigned. The standalone `AudioDSPScreen` and `DMPPollingController` are
not promoted into IN1808 authority.

## Validation implications

Implementation requires focused coverage for:

- exact-model capability gating;
- preservation of exact wire identity/variant without relabeling canonical
  `Extron IN1808`;
- audio-name IDs and fallbacks;
- mandatory read-only `1$` Program-source binding with `1..9` / UNKNOWN normalization;
- 300xx/400xx/600xx meter topology and stereo aggregation;
- IN1808 meter-state lifecycle with `*1` activation, explicit non-use of
  DMP `*2`, and no production cleanup `*0` until state scope is proven;
- raw-meter preservation and dBFS conversion;
- 8 x 12 mix-point formula, explicit `IN1808_PRODSP_PROFILE_MAPPING`
  assumption, protocol-level fail-closed behavior, variant output filtering,
  0/1/UNKNOWN parsing, and zero audio-route mutation;
- one-shot routing acquisition versus meter live cadence;
- shared Matrix session serialization, RoomInteractionKind.LIVE handoff,
  Local Refresh/mutation/reconciliation exclusion, and no GUI-thread network I/O;
- mode toggle/collapse/context-replacement cleanup and stale callback rejection;
- Audio failure isolation from accepted Matrix/General-information state;
- unchanged existing video route read/mutation behavior.

This change adds root requirements. Independent validation still must review
archive/root-spec applicability against the then-current root specs if concurrent
changes touch the same requirements or capability boundaries.