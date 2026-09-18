# Hardware validation: Extron matrix model expansion

## Evidence status

- **SOFTWARE VALIDATED:** offline implementation, regression, strict OpenSpec,
  and Git checks are tracked by the task-reconciliation gate for this change.
- **HARDWARE VALIDATED:** no model has current-change hardware evidence.
- **HARDWARE NOT RUN:** all models in the matrix below. Fixture, unit, and
  simulator results do not constitute hardware validation.

Only these hardware result values may be recorded: `PASS`, `PARTIAL`, `FAIL`,
`NOT RUN`, and `BLOCKED`. `PASS` requires every applicable read-only check and
safe controlled-mutation check. `PARTIAL` means only a documented subset was
observed. `FAIL` means observed hardware contradicts this change. `BLOCKED`
means a present device could not be exercised for an external reason.

## Model capability and evidence matrix

All status cells are deliberately `NOT RUN`. “Unavailable” means the approved
profile must not send a speculative read, not that a blank value should be
invented. `Yes` is an expected capability to exercise during hardware QA.

| Model | Inventory / identity | Topology | Signal / input HDCP | Output HDCP / auth | Input / output names / temp | Route read / mutation | Hardware status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Extron IN1804 | Canonical / `1I` | fixed 4x1 | Yes / legacy mapping | Yes / Yes | Yes / Yes / Yes | `!` / `<I>*1!` | FAIL | Reported physical baseline regression after strict identity resolution; closed documented wire-alias remediation awaits read-only retest. |
| Extron IN1808 | Canonical / `1I` | fixed 8x1 | Yes / legacy mapping | Yes / Yes | Yes / Yes / Yes | `1!` / `<I>*1!` | NOT RUN | Loop Out remains deferred; it is not a second logical route. |
| Extron IN1608 xi | Canonical / `1I` | fixed 8x1 | Yes / modern mapping | Yes / Yes | Yes / unavailable / Yes | `!` / `<I>!` | NOT RUN | Output-name read remains unavailable. |
| DTP CrossPoint 84 | Canonical / documented DTP identity | fixed 8x4 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / unavailable | `<O>!` / `<I>*<O>!` | NOT RUN | Capture actual `0LS` framing. |
| DTP CrossPoint 82 4K | Canonical / part number `N` | fixed 8x2 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / unavailable | `<O>!` / `<I>*<O>!` | NOT RUN | Capture actual `0LS` framing. |
| DTP CrossPoint 84 4K | Canonical / part number `N` | fixed 8x4 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / unavailable | `<O>!` / `<I>*<O>!` | NOT RUN | Must remain distinct from non-4K DTP 84. |
| DTP CrossPoint 86 4K | Canonical / part number `N` | fixed 8x6 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / unavailable | `<O>!` / `<I>*<O>!` | NOT RUN | Capture actual `0LS` framing. |
| DTP CrossPoint 108 4K | Canonical / part number `N` | fixed 10x8 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / unavailable | `<O>!` / `<I>*<O>!` | NOT RUN | Capture actual `0LS` framing. |
| XTP CrossPoint 1600 | Canonical / `N`, `I`, `*N` | dynamic board-aware | Yes / modern mapping | `W0<N>HDCP` / unavailable | unavailable / unavailable / unavailable | `<O>!` / `<I>*<O>!` | NOT RUN | First-generation symbol table only; preserve empty-slot IDs. |
| XTP CrossPoint 3200 | Canonical / `N`, `I`, `*N` | dynamic board-aware | Yes / modern mapping | `W0<N>HDCP` / unavailable | unavailable / unavailable / unavailable | `<O>!` / `<I>*<O>!` | NOT RUN | First-generation symbol table only; preserve empty-slot IDs. |
| XTP II CrossPoint 1600 | Canonical / `N`, `I`, `*N` | dynamic board-aware | Yes / modern mapping | unavailable / Yes | unavailable / unavailable / unavailable | `<O>!` / `<I>*<O>!` | NOT RUN | Output HDCP remains UNPROVEN/unavailable. |
| XTP II CrossPoint 3200 | Canonical / `N`, `I`, `*N` | dynamic board-aware | Yes / modern mapping | unavailable / Yes | unavailable / unavailable / unavailable | `<O>!` / `<I>*<O>!` | NOT RUN | Output HDCP remains UNPROVEN/unavailable. |
| XTP II CrossPoint 6400 | Canonical / `N`, `I`, `*N` | dynamic board-aware | Yes / modern mapping | unavailable / Yes | unavailable / unavailable / unavailable | `<O>!` / `<I>*<O>!` | NOT RUN | Output HDCP remains UNPROVEN/unavailable. |

## Phase A — read-only hardware procedure

This is the mandatory first pass. For every physically available model:

1. Verify inventory conversion resolves the expected canonical
   `diagnostic_model` without changing the source-model evidence.
2. Connect through the normal application/handler path and capture the exact
   identity response; verify it matches the inventory expectation.
3. Read only the profile-approved capabilities, topology, signal presence,
   input HDCP, output HDCP, HDCP authorization, names, temperature, and all
   applicable routes. Record unavailable/unproven fields as unavailable; do
   not issue a trial command.
4. Where practical, compare parsed state with the device Web UI or known
   current state. Record raw request/response pairs with firmware version and
   device serial/asset reference, omitting credentials.

For XTP and XTP II, retain raw responses for `N`, `I`, `*N`, and `0LS`, plus
all applicable HDCP and route reads. Verify that the `N` part number equals the
`*N` part number, the board-symbol sequence has the frame-specific slot count,
and every symbol belongs to the selected generation's symbol table. Empty slots
must retain later logical IDs. An undocumented symbol stops that profile's
validation and is recorded verbatim; it does not authorize parser expansion.

For DTP, capture the real `0LS` response exactly, including whether it is bare,
`Frq00*`-prefixed, space-separated, or contiguous. Verify DTP CrossPoint 84's
documented identity path and the 4K models' exact part-number path. A framing
variance is evidence for review, not permission to change parsing.

For IN1808, exercise only the approved read-only commands `1I`, `W20STAT`,
`WI<N>VNAM`, `WO<N>VNAM`, `W0LS`, `WE<N>HDCP`, `WI<N>HDCP`, `WO<N>HDCP`, and
`1!`; do not model Loop Out as a second main route. For IN1608 xi, use `1I`,
`W20STAT`, `W<N>NI`, `W0LS`, `WE<N>HDCP`, `WI<N>HDCP`, `WO<N>HDCP`, and `!`.
Do not probe an unproven IN1608 xi output-name read.

## Phase B — controlled mutation procedure

Run only where route switching is operationally safe and a reversion is
approved. Before mutation, record the accepted route state, the exact target
output, target input, and the restoration route. Send one route change only.
Transport success or ACK is not authoritative; read the exact target output
and accept success only when:

```text
routes[target_output] == requested_input
```

Restore the original route and verify the same targeted readback. If a failure
occurs after possible send, do not replay automatically. Preserve the raw
evidence and mark the result `PARTIAL`, `FAIL`, or `BLOCKED` as applicable.
