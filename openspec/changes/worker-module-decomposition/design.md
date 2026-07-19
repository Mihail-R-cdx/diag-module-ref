## Context

Current `core/worker.py` owns several unrelated worker families:

- shared Qt signal infrastructure: `WorkerSignals`;
- shared helpers: `_worker_secrets`, `_safe_error`, `_emit_error`;
- codec polling: `HuaweiTE40Worker`, `HuaweiBar310Worker`,
  `PolycomRPG310Worker`;
- codec actions: `CodecSipFixWorker` and the existing
  `HuaweiTE40Worker.set_sip_server()` compatibility method;
- call-log/background codec operation: `PolycomCallLogWorker`;
- audio DSP polling: `BiampTesiraForteCIWorker`;
- DMP long-lived meter polling: `ExtronDMP64PlusMeterWorker`;
- matrix polling: `ExtronIN1804Worker`;
- PDU workers: `PDUOperationWorker`, `AtenPDUWorker`.

`HuaweiTE20Worker` is already implemented in `core/te20_worker.py` and is
imported into `core.worker`. That worker has its own local `WorkerSignals`
definition today. This change should not automatically move TE20; doing so
would expand the scope from decomposing the current monolithic file into
normalizing an already separate worker.

Known `core.worker` import consumers include `gui/main_window.py`,
`gui/screens/codec_screen.py`, `core/__init__.py`, and tests including
credential propagation, retry ownership, hardware redaction, PDU operations,
Extron DMP 64 Plus meter diagnostics, and worker outcome tests.

Known compatibility-sensitive test patch points include:

- `core.worker.HuaweiTE40Handler`;
- `core.worker.CloudLinkBar310Handler`;
- `core.worker.HuaweiTE40DataParser.parse_raw_data`;
- `core.worker.HuaweiBar310DataParser.parse_raw_data`.
- `core.worker.time.monotonic`;
- `core.worker.wait_cancelable`.

## Goals / Non-Goals

**Goals:**

- Reduce context load by placing workers in focused modules by domain and
  responsibility.
- Keep `core/worker.py` small enough to read as a compatibility facade.
- Preserve existing public worker imports from `core.worker`.
- Include every top-level worker implementation currently in `core/worker.py`
  in the target architecture, including `ExtronDMP64PlusMeterWorker`.
- Preserve runtime behavior and public signal/error/result payload shapes.
- Preserve application-owned credential selection, fallback, and successful
  credential index memory.
- Preserve existing transport profile ordering and retry semantics.
- Preserve state-changing operation safety for codec and PDU operations.
- Preserve DMP persistent polling lifecycle and safety contracts when workers
  adjacent to DMP polling are moved or imported.
- Preserve redaction for credentials, Session IDs, cookies, CSRF tokens, and
  other secrets.
- Define focused tests for facade imports, class identity, signal behavior,
  patch/mock paths, and error payload equivalence.

**Non-Goals:**

- Do not implement the decomposition in this architecture-only change.
- Do not change GUI workflows, screens, signal payloads, or handler protocols.
- Do not move credential fallback from the application/composition layer into
  workers or handlers.
- Do not change transport fallback order or retry budgets.
- Do not add replay, new recovery policy, or ambiguity handling changes.
- Do not move network I/O into the Qt GUI thread.
- Do not create a broad orchestration layer shared by PDU, codecs, DMP, Matrix,
  and audio DSP.
- Do not archive or merge this change as part of preparation.

## Target Module Boundaries

The implementation target structure is fixed:

```text
core/
    worker.py
    te20_worker.py

    workers/
        __init__.py
        common.py
        codec_polling.py
        codec_actions.py
        codec_call_logs.py
        audio_dsp.py
        dmp.py
        matrix.py
        pdu.py
```

If implementation discovers a real architectural obstacle to these boundaries,
the engineer must stop and return the change for architectural review rather
than independently changing the approved map.

### `core/workers/common.py`

Owns Qt worker infrastructure that is genuinely shared:

- `WorkerSignals`;
- `_worker_secrets(worker)`;
- `_safe_error(error, secrets)`;
- `_emit_error(worker, category, error, trace=True)`;
- any small redaction/error-emission helper currently duplicated by worker
  classes.

This module may depend on PyQt signal primitives, `core.exceptions` for
classification, and `core.redaction`. It must not import worker modules,
device handlers, GUI modules, or application composition code.

### `core/workers/codec_polling.py`

Owns read/status workers for codec-like devices currently embedded in
`core/worker.py`:

- `HuaweiTE40Worker`;
- `HuaweiBar310Worker`;
- `PolycomRPG310Worker`.

These workers may depend on codec handlers, codec parsers,
`order_codec_profiles`, common worker helpers, and redaction. They must not
select credentials from provider storage or advance credential indexes.

`HuaweiTE40Worker.set_sip_server()` remains on `HuaweiTE40Worker` in the first
implementation step because it is a public method on that class today. Any
later extraction of that method into an action-only class requires a separate
behavior/compatibility decision.

### `core/workers/codec_actions.py`

Owns explicit codec action workers:

- `CodecSipFixWorker`.

This module may depend on codec handlers and common worker helpers. It must
preserve current SIP fix result and error payloads and must not change
state-changing command safety.

### `core/workers/codec_call_logs.py`

Owns short-lived call-log/background codec operations:

- `PolycomCallLogWorker`.

This module remains separate from generic codec polling because call-log reads
have different payload shape and handler lifecycle.

### `core/workers/audio_dsp.py`

Owns audio DSP workers:

- `BiampTesiraForteCIWorker`.

This module may depend on the Biamp handler and parser only through the current
worker boundary. It must preserve existing read-only behavior and cleanup.

### `core/workers/dmp.py`

Owns DMP long-lived meter polling workers:

- `ExtronDMP64PlusMeterWorker`.

This worker is not owned by `audio_dsp.py` even though its meter data is
displayed by the Audio DSP GUI. It has a distinct long-lived polling lifecycle,
cancellation contract, timeout/session poisoning behavior, recovery budget,
credential-success gate, stale-context boundary, error classification, and
secret-redaction contract. It may depend on DMP cancellation/token types,
DMP-specific domain constants and helpers, the Extron DMP handler, common
worker helpers, and redaction. It must not change DMP polling behavior as part
of this structural refactor.

### `core/workers/matrix.py`

Owns matrix workers:

- `ExtronIN1804Worker`.

This module may depend on `handlers.extron.in1804`,
`ExtronIN1804DataParser`, common worker helpers, and redaction. It must not be
coupled to PDU workers even though both use Extron devices.

### `core/workers/pdu.py`

Owns PDU worker classes:

- `PDUOperationWorker`;
- `AtenPDUWorker`.

This module may depend on `core.pdu` domain operations and common worker
helpers. It must keep Aten and PCS4i protocol semantics in device-specific
handlers/domain code and must not become a universal hardware worker layer.

### `core/te20_worker.py`

`HuaweiTE20Worker` remains canonical in this existing module for this change.
`core.worker` continues to re-export it. A later TE20 normalization may move
shared signals into `core/workers/common.py` only if identity, signal shape,
and error payload tests prove no runtime regression.

### `core/worker.py`

After implementation, `core/worker.py` should be a small facade that:

- imports canonical worker classes from their focused modules;
- imports `HuaweiTE20Worker` from `core.te20_worker`;
- re-exports the public worker symbols listed in the compatibility contract;
- contains no worker run-loop implementation, handler protocol logic, parser
  logic, credential iteration, retry policy, or GUI callback logic.

## Compatibility Strategy

The following public worker symbols continue to import from `core.worker`:

- `WorkerSignals`;
- `HuaweiTE20Worker`;
- `HuaweiTE40Worker`;
- `HuaweiBar310Worker`;
- `PolycomRPG310Worker`;
- `CodecSipFixWorker`;
- `PolycomCallLogWorker`;
- `BiampTesiraForteCIWorker`;
- `ExtronDMP64PlusMeterWorker`;
- `ExtronIN1804Worker`;
- `PDUOperationWorker`;
- `AtenPDUWorker`.

`core.worker` class re-exports must have the same class identity as their
canonical implementation modules. For example, `core.worker.HuaweiTE40Worker`
must be `core.workers.codec_polling.HuaweiTE40Worker`, not a behavior-changing
wrapper.

Internal test monkeypatch paths such as
`core.worker.HuaweiTE40Handler`, `core.worker.CloudLinkBar310Handler`,
`core.worker.HuaweiTE40DataParser.parse_raw_data`,
`core.worker.HuaweiBar310DataParser.parse_raw_data`,
`core.worker.time.monotonic`, and `core.worker.wait_cancelable` are not public
production API. During implementation, tests that patch these internal
dependencies must migrate to the canonical dependency location in the focused
worker module, such as `core.workers.codec_polling.HuaweiTE40Handler` or
`core.workers.dmp.wait_cancelable`.

`core.worker` must not grow runtime compatibility indirection solely to preserve
internal test monkeypatch paths. The semantics of the tests must remain the
same, and public facade worker imports must be regression-tested separately.

## Behavioral Equivalence Contract

The decomposition is structural. It must not change runtime behavior.

Credentials:

- credential resolution, candidate ordering, fallback, and successful index
  memory remain owned by the GUI/application composition layer;
- each worker receives only its assigned credential candidate;
- workers and handlers do not read `credentials.local.json` or choose another
  candidate.

Transport fallback:

- TE20, TE40, and other transport profile ordering remains unchanged;
- transport fallback and credential fallback remain separate mechanisms;
- a confirmed authentication failure does not hide behind later protocol
  fallback unless that is already the existing contract.

State-changing operations:

- codec SIP changes and PDU control operations keep existing safety contracts;
- the refactor does not add replay, change recovery policy, change ambiguity
  handling, or add credential fallback after a potentially delivered mutation.

DMP:

- DMP persistent polling lifecycle, cancellation, stale-context suppression,
  transaction timeout poisoning, recovery budget, and credential persistence
  semantics remain unchanged by worker module moves.
- `ExtronDMP64PlusMeterWorker` remains a background long-lived polling worker;
- cancellation checkpoints, timeout/session poisoning, error classification,
  credential-success gate, stale-context boundary, secret redaction, and absence
  of GUI-thread network I/O remain regression-covered.

GUI threading:

- workers remain background execution boundaries;
- no network I/O is moved into the Qt GUI thread.

Signals and callbacks:

- public `WorkerSignals` names and emitted payload shapes remain unchanged;
- `finished`, `error`, `result`, `progress`, `status`, `terminal_log`,
  `connected`, and `disconnected` retain current signal types;
- consumers in `gui/main_window.py`, `gui/screens/codec_screen.py`, and tests
  continue to receive compatible payloads.

Secrets:

- credential values, Session IDs, cookies, CSRF tokens, and other secrets
  remain redacted from stdout, logs, GUI errors, public worker error payloads,
  and tests;
- moving `_worker_secrets`, `_safe_error`, or `_emit_error` must not weaken
  redaction.

## Dependency Direction

Allowed dependency direction:

```text
core.worker facade
    -> core.te20_worker
    -> core.workers.<focused modules>

core.workers.<focused modules>
    -> core.workers.common
    -> handlers.<device>
    -> core.parser / core.pdu / core.codec_connection_profiles / core.exceptions
    -> core.redaction
```

Forbidden dependency direction:

- focused worker modules importing `core.worker`;
- `core/workers/common.py` importing any focused worker module;
- handlers importing worker modules to call GUI-facing signal code;
- GUI modules becoming required imports for worker module import time;
- a new universal orchestration module that owns mixed PDU, codec, DMP, Matrix,
  and audio-DSP lifecycles.

`core/workers/__init__.py`, if added, must be a convenience export layer only.
It must not become a second large aggregator with implementation code.

## Migration Sequence

1. Add `core/workers/common.py` with `WorkerSignals` and shared redacted error
   helpers; update moved workers to import from it.
2. Move one low-coupling worker family first, preferably `PolycomCallLogWorker`
   or `BiampTesiraForteCIWorker`, while keeping `core.worker` re-exports and
   focused tests passing.
3. Move codec polling workers into `codec_polling.py`; preserve behavior while
   migrating internal parser/handler patch paths to canonical focused module
   paths.
4. Move `CodecSipFixWorker` into `codec_actions.py` without changing SIP fix
   result/error payloads.
5. Move `ExtronDMP64PlusMeterWorker` into `dmp.py`, preserving cancellation,
   long-lived polling, timeout/session poisoning, recovery, credential-success
   gate, stale-context, error classification, redaction, and background
   execution contracts.
6. Move matrix and PDU workers into `matrix.py` and `pdu.py`, keeping
   device-specific protocol code outside the facade.
7. Convert `core/worker.py` into the compatibility facade and define
   `__all__` for the compatibility public symbols.
8. Verify all `core.worker` public imports, direct canonical worker imports,
   facade class identity, and migrated patch/mock paths.
9. Run focused regression tests and the full offline suite.
10. Run strict OpenSpec validation through `.\openspec.cmd`.

This order intentionally keeps `core.worker` usable throughout the migration
and avoids a large intermediate state where many consumers break at once.

## Risks / Trade-offs

- Internal `core.worker` patch points will no longer affect moved module-local
  imports. The implementation must migrate tests to canonical patch paths with
  focused evidence and must keep facade public worker imports separately tested.
- `WorkerSignals` currently exists both in `core/worker.py` and
  `core/te20_worker.py`. Normalizing them could change class identity even if
  signal names match, so TE20 signal unification should be deliberate and
  tested.
- `ExtronDMP64PlusMeterWorker` has stricter lifecycle semantics than short
  polling workers. Treating it as audio-DSP polling would obscure cancellation,
  session timeout poisoning, and stale-context rules; the canonical boundary is
  therefore `core/workers/dmp.py`.
- A facade can grow back into an aggregator if helper code remains there. The
  implementation should keep facade content to imports, `__all__`, and minimal
  documentation only.
- Moving imports may introduce cycles, especially if a focused worker imports
  `core.worker` for compatibility. The dependency direction forbids that.
- PDU and codec workers share some lifecycle words but not the same protocol
  semantics. A broad shared orchestration layer would obscure safety contracts
  and is outside this change.
