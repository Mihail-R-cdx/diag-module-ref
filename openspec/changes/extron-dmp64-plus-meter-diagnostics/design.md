## Context

The current Audio DSP category routes `Biamp Tesira Forte CI` to
`AudioDSPScreen`, where Biamp `signal_sources` are shown as read-only tables.
DMP belongs to the same product category but needs a different presentation:
physical live meters for six inputs and four outputs.

The project already has relevant architectural patterns: background workers,
request-context isolation, application-owned credential fallback, PCS4i Extron
protocol parsing/redaction lessons, and explicit stale-generation protection.
DMP should extend those patterns as a read-only Audio DSP diagnostic path.

## Goals

- Add Extron DMP 64 Plus as an Audio DSP diagnostic model.
- Preserve current Biamp behavior.
- Use one persistent SIS-over-SSH polling session per active DMP context.
- Deliver complete normalized snapshots approximately once per second.
- Separate SSH/PTY stream cleanup from DMP meter parsing.
- Keep recovery bounded and conditional.
- Keep credential ownership in the application/composition layer.
- Make implementation offline-testable without live DMP hardware.

## Non-Goals

- Do not implement production code in this architecture change.
- Do not add write controls except bounded conditional meter recovery.
- Do not use Meter Groups, SLM, push subscription, pipelining, or Telnet 23.
- Do not dispatch by the exact live-device string `DMP 64 Plus C AT` unless
  future protocol evidence requires it.

## Decisions

### Register DMP under Audio DSP

The selectable model is `Extron DMP 64 Plus`. It appears under `Audio DSP` and
routes to the existing `audio_dsp` screen key. Runtime `device_info` may report
a more specific discovered model, but dispatch must not depend on one IP,
serial number, DSP configuration, Meter Group, or exact firmware.

### Reuse AudioDSPScreen with a DMP presentation mode

`AudioDSPScreen` remains the shared Audio DSP surface. Existing Biamp
`signal_sources` table rendering stays unchanged. DMP result metadata selects a
meter presentation with two sections:

- `Inputs`: six physical channels.
- `Outputs`: four physical channels.

Each channel is primarily a horizontal green meter bar. All ten bars update
from one complete normalized snapshot, not from independent GUI polling loops.

### Use SIS-over-SSH on port 22023

The DMP production baseline is SIS-over-SSH on TCP `22023`. The supported
current mechanism is:

```text
SSH connect -> open_session -> get_pty(term='vt100') -> invoke_shell()
```

This is a supported implementation mechanism, not a universal claim about all
DMP firmware. Non-PTY attempts on the tested firmware did not produce working
SIS interaction.

### Separate stream handling from meter parsing

The transport stream may contain SSH/channel data, PTY command echo, SIS
payload, CR/LF framing, partial chunks, and multiple logical frames in one
read. The boundary is:

```text
SSH transport -> stream buffering/framing -> PTY echo filtering
  -> clean SIS payload -> DMP meter parser
```

The meter parser consumes clean payloads only. It must not know about PTY,
skip the first line as echo, assume the second line is payload, or assume one
`recv()` per response.

### Query physical meter OIDs

Current physical OIDs:

| Channel | OID |
| --- | --- |
| Input 1 | `40000` |
| Input 2 | `40001` |
| Input 3 | `40002` |
| Input 4 | `40003` |
| Input 5 | `40004` |
| Input 6 | `40005` |
| Output 1 | `60000` |
| Output 2 | `60001` |
| Output 3 | `60002` |
| Output 4 | `60003` |

Do not use `40100-40105` in the current DMP path; live queries returned `E13`.

Read command:

```text
ESC V<OID>AU CR
```

Valid payloads `1*NNN` and `2*NNN` convert with:

```text
dBFS = -(raw_meter / 10)
```

`0*0` means unavailable/not initialized/no useful sample, not `0 dBFS`.

### Bound meter recovery

After direct read returns `0*0`, the implementation may send one recovery
command for that OID:

```text
ESC V<OID>*2AU CR
```

Expected acknowledgement:

```text
DsV<OID>*2
```

Then direct read is retried once. If still unavailable or errored, that OID is
unavailable for the snapshot. The recovery budget is one attempt per OID in
the current polling session/recovery episode. A new DMP session receives a
fresh bounded budget. Do not send `*2` unconditionally or in an infinite loop.

### Poll complete snapshots sequentially

The baseline is one persistent SSH session and one sequential polling flow over
all ten OIDs. Do not start ten SSH connections, ten parallel requests, ten
per-channel GUI polling loops, or the next polling cycle before the previous
snapshot finishes.

The accepted cadence is approximately one complete ten-channel snapshot per
second. Observed 1.07 second sequential snapshot time is accepted. No
pipelining or sub-second optimization is required in this change.

Partial channel failure does not destroy the whole snapshot if the session is
usable. Transport-wide failure, authentication failure, and session loss are
session-level outcomes.

### Manage lifecycle and stale context

DMP polling captures explicit non-GUI context: model, IP address,
worker/session identity, credential candidate/index context, generation token,
and cancellation/stop state.

Polling stops or becomes stale when model changes, IP changes, the operator
leaves the DMP screen, a new DMP context starts, or the application closes.
Queued stale work is dropped before handler acquisition/network I/O where
possible. In-flight stale callbacks cannot update UI, recovery state, polling
state, or credential memory. Workers must not inspect Qt widgets for
freshness.

### Keep credentials application-owned

The application resolves candidate chains before DMP session acquisition. One
worker/session attempt receives one credential. The handler and worker do not
iterate candidates. Credential fallback is allowed only after a structured
confirmed authentication failure during session acquisition. SIS errors,
`E13`, `0*0`, malformed payloads, timeout, PTY echo, and per-OID failures are
not retry authority.

Credential memory is saved only after a real successful connection is
established and used for a successful DMP operation, such as an accepted final
snapshot. Stale/cancelled/failed sessions do not save credentials.

### Map meter values

Visual scale:

```text
normalized = clamp((db_value + 60) / 72, 0, 1)
```

Examples: `-60 -> 0%`, `-48 -> 16.7%`, `-36 -> 33.3%`, `-24 -> 50%`,
`-12 -> 66.7%`, `0 -> 83.3%`, `+12 -> 100%`.

DMP samples are already dBFS after raw conversion. Do not apply another
logarithmic transform. Values below `-60 dBFS` render as 0%. Unavailable
samples render empty/unavailable and never as maximum.

## Risks / Trade-offs

- Reusing `AudioDSPScreen` adds a presentation split, but preserves category
  consistency and avoids a DMP-only top-level screen.
- A long-lived polling worker adds lifecycle complexity, but avoids overlapping
  network workers and stale UI writes.
- PTY echo handling is fragile if implemented by line number; the spec requires
  command-aware framing instead.
- `*2` recovery changes device-side meter state, so it is bounded and
  conditional.

## Migration Plan

1. Add DMP selector registration and Audio DSP routing.
2. Extend `AudioDSPScreen` with a DMP meter mode while preserving Biamp tables.
3. Add DMP SSH/PTTY transport, stream framing, echo filtering, OID map, parser,
   dBFS conversion, normalization, and recovery state.
4. Add one long-lived background polling worker/controller with explicit
   context, cancellation, stale suppression, and cleanup.
5. Wire application-owned credential plans and structured fallback.
6. Add focused offline tests and run full validation.

## Open Questions

- Do any DMP 64 Plus family variants with the same user-facing model use a
  different physical meter OID contract? Current scope is the six-input,
  four-output family contract above.
