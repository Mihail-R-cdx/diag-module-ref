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

- Add Extron DMP 64 Plus as an Audio DSP diagnostic model for explicit
  supported protocol variants.
- Preserve current Biamp behavior.
- Use one persistent SIS-over-SSH polling session per active DMP context.
- Deliver complete normalized snapshots approximately once per second.
- Separate SSH/PTY stream cleanup from DMP meter parsing.
- Correlate each sequential SIS request with its expected response so
  unrelated frames cannot shift channel results.
- Keep recovery bounded and conditional.
- Stop long-lived polling deterministically with bounded waits and background
  resource cleanup.
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

Supported protocol variants for this change are:

- `DMP 64 Plus C`
- `DMP 64 Plus C AT`
- `DMP 64 Plus C V`
- `DMP 64 Plus C V AT`

The vendor product documentation describes the DMP 64 Plus line as four models
with 6 mic/line inputs and 4 line outputs, and those four variants are the
current supported family boundary. The target physical meter OID contract for
this change remains the confirmed current protocol contract:
`40000-40005` for the six physical inputs and `60000-60003` for the four
physical outputs.

The selector identity remains `Extron DMP 64 Plus`, but discovered model
validation must accept only the explicit supported variant set above or a
model-identification response that is otherwise explicitly mapped to that set.
An unknown future variant is not automatically supported merely because its
string contains `DMP 64 Plus`.

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

### Correlate serialized SIS transactions

DMP polling is sequential and must keep at most one outstanding SIS
transaction on the persistent session. The next request is not sent until the
previous request has reached an expected terminal response, structured timeout,
or transport/session failure.

Each transaction carries its expected response contract:

- meter read `ESC V<OID>AU CR` expects a valid meter payload
  `<state>*<raw_meter>` for the current request, a documented SIS error such
  as `E13`, timeout, or transport/session failure;
- recovery `ESC V<OID>*2AU CR` expects acknowledgement `DsV<OID>*2` for the
  same OID, timeout, or transport/session failure.

PTY echo is never a response. A clean frame unrelated to the current request,
including an unsolicited frame or a frame for another OID, must not complete
the current transaction and must not be converted into the current OID's meter
value. The implementation may ignore such frames, record them through a
redacted optional unsolicited sink, or expose a structured ignored-frame
diagnostic, but it cannot use them as request success.

If the expected response is not observed before the bounded transaction
timeout, the transaction ends with a structured timeout/transport outcome. A
leftover unrelated frame must not be carried forward as the next OID's meter
result. The transaction boundary is responsible for preventing silent channel
shifting across sequential OID reads.

Because ordinary DMP meter payloads such as `1*457` and `2*1060` are untagged
and contain no OID, any DMP SIS transaction timeout poisons the current SIS
session. After timeout, the worker must not send the next OID request, must not
try to drain/clean the stream and continue using the same session, and must not
publish the interrupted polling cycle as a successful complete snapshot. The
current polling cycle terminates with a structured session/transport failure,
then the SSH channel/client/session are closed through the normal background
cleanup path.

This rule applies to meter-read timeout and recovery-acknowledgement timeout.
`E13` remains different: if it is received as the terminal response for the
current transaction, the response boundary is known and the session is not
desynchronized merely because of that SIS protocol outcome. Likewise, `0*0` is
a received meter response and continues to use the bounded one-shot recovery
contract.

Further polling after a transaction timeout requires a fully new SSH/SIS
session with clean stream/transaction state. The timeout is not an
authentication failure, does not authorize credential fallback, and does not
change successful credential memory.

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

Transaction timeout is session-level. A cycle interrupted by timeout is not a
complete ten-OID cycle even if earlier OIDs in that cycle had valid samples or
per-channel unavailable outcomes. It does not pass the credential success gate
and must not be emitted as a new successful complete snapshot. The GUI may keep
the last previously accepted snapshot or show a session-level error according
to the existing error contract; this architecture does not add new UI scope for
timeout recovery.

### Manage cancellation, lifecycle, and stale context

DMP polling captures explicit non-GUI context: model, IP address,
worker/session identity, credential candidate/index context, generation token,
and a thread-safe cancellation handle owned by the application/composition
layer. The worker receives immutable context identity plus that cancellation
handle. It does not inspect Qt widgets for freshness or cancellation.

Cancellation/freshness checkpoints are required at least:

1. before handler/session acquisition;
2. before starting each new full polling cycle;
3. before sending each new OID read;
4. before sending conditional `*2` recovery;
5. before the recovery retry read;
6. before emitting a snapshot, result, error, or completion that could affect
   the active context.

After cancellation or invalidation, the worker must not start new network I/O
at any later checkpoint. If cancellation happens between OID requests, the
next OID command is not sent, no old-context snapshot is applied to the GUI,
and the worker moves to cleanup. An already sent request may finish or time
out, but after that bounded wait the worker checks cancellation and does not
continue polling the old context.

All SSH/SIS reads use bounded timeouts. The architecture does not require an
instant hard interrupt of an in-progress socket/channel receive, but it does
require the worker to return to a cancellation checkpoint within bounded time;
infinite blocking `recv()` is forbidden.

On every terminal path, including normal stop, context cancellation,
authentication failure, transport/session failure, application close, and
unexpected exception, the session owner closes the SSH channel, SSH
client/session, and related transport resources on the background execution
lane that owns them. Cleanup must be idempotent or guaranteed exactly once.
Terminal completion/error is emitted only after cleanup according to the
chosen worker contract.

An explicit Refresh for the currently active DMP model/IP context creates a
new polling generation/context and invalidates the previous one. The old
context receives cancellation, stops starting network I/O after the next
checkpoint, cleans up its resources, and has all callbacks ignored. The new
context is the only authoritative context and does not inherit credential
state from stale callbacks of the old context. Two authoritative polling
contexts for one Audio DSP UI are forbidden.

### Keep credentials application-owned

The application resolves candidate chains before DMP session acquisition. One
worker/session attempt receives one credential. The handler and worker do not
iterate candidates. Credential fallback is allowed only after a structured
confirmed authentication failure during session acquisition. SIS errors,
`E13`, `0*0`, malformed payloads, timeout, PTY echo, and per-OID failures are
not retry authority.

Credential memory uses a DMP-specific long-lived polling success gate. The
assigned credential index may be saved at most once for the current session
acquisition attempt, and only after the first accepted complete ten-OID
polling cycle.

For this gate, complete means all ten physical OIDs were attempted and either
produced a valid sample or a structured per-channel unavailable/protocol
outcome, the snapshot was formed, the session-level operation did not end in
authentication or transport failure, and the snapshot was accepted by the
active non-stale DMP context. It does not require all ten channels to have
numeric values. A successful SSH login alone is insufficient, one successful
OID is insufficient, stale complete snapshots never cache credentials, and
later snapshots from the same session do not repeatedly mutate credential
memory.

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
3. Add DMP SSH/PTY transport, stream framing, echo filtering, OID map, parser,
   dBFS conversion, normalization, and recovery state.
4. Add one long-lived background polling worker/controller with explicit
   context, cancellation, stale suppression, and cleanup.
5. Wire application-owned credential plans and structured fallback.
6. Add focused offline tests and run full validation.
