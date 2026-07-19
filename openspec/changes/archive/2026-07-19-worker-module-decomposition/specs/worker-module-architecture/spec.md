## ADDED Requirements

### Requirement: Focused worker implementation modules
Worker implementation ownership SHALL be decomposed from `core/worker.py` into
focused `core/workers/` modules by domain and responsibility boundary rather
than by line count alone. The approved target structure SHALL be:

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

Canonical ownership SHALL be:

- `core/workers/common.py`: `WorkerSignals` and shared worker
  redaction/error helpers;
- `core/workers/codec_polling.py`: `HuaweiTE40Worker`,
  `HuaweiBar310Worker`, and `PolycomRPG310Worker`;
- `core/workers/codec_actions.py`: `CodecSipFixWorker`;
- `core/workers/codec_call_logs.py`: `PolycomCallLogWorker`;
- `core/workers/audio_dsp.py`: `BiampTesiraForteCIWorker`;
- `core/workers/dmp.py`: `ExtronDMP64PlusMeterWorker`;
- `core/workers/matrix.py`: `ExtronIN1804Worker`;
- `core/workers/pdu.py`: `PDUOperationWorker` and `AtenPDUWorker`;
- `core/te20_worker.py`: `HuaweiTE20Worker`.

Implementation SHALL NOT arbitrarily change these boundaries. If implementation
discovers a real architectural obstacle, the engineer SHALL stop and return the
change for architectural review instead of choosing different boundaries
independently.

#### Scenario: Codec polling worker has focused ownership
- **WHEN** a developer needs to change TE40, Bar 310, or Polycom diagnostic polling behavior
- **THEN** the canonical implementation is in `core/workers/codec_polling.py`
- **AND** unrelated PDU, Matrix, DMP, audio-DSP, and call-log worker implementation code is not required reading

#### Scenario: Codec action worker has focused ownership
- **WHEN** a developer needs to change SIP server fix worker behavior
- **THEN** the canonical implementation is in `core/workers/codec_actions.py`
- **AND** the move does not change the public SIP fix result or error payload contract

#### Scenario: Call-log worker has focused ownership
- **WHEN** a developer needs to change Polycom call-log loading
- **THEN** the canonical implementation is in `core/workers/codec_call_logs.py`
- **AND** the operation remains separate from generic codec polling workers

#### Scenario: DMP worker has focused ownership
- **WHEN** a developer needs to change Extron DMP 64 Plus meter polling behavior
- **THEN** the canonical implementation is in `core/workers/dmp.py`
- **AND** it is not placed in `core/workers/audio_dsp.py`
- **AND** its long-lived polling lifecycle, cancellation, timeout/session poisoning, recovery, credential-success gate, stale-context, error classification, redaction, and background execution contracts remain explicit

#### Scenario: PDU worker has focused ownership
- **WHEN** a developer needs to change PDU refresh or PDU command worker behavior
- **THEN** the canonical implementation is in `core/workers/pdu.py`
- **AND** device-specific PDU protocol semantics remain outside a universal hardware worker layer

#### Scenario: TE20 remains explicitly separate
- **WHEN** the worker facade exports `HuaweiTE20Worker`
- **THEN** it imports the worker from `core.te20_worker`
- **AND** this change does not move TE20 into `core/workers/codec_polling.py`

### Requirement: Worker compatibility facade
`core/worker.py` SHALL remain as a small compatibility facade after the worker
implementation moves. It SHALL re-export the existing public worker symbols
without containing worker run-loop implementation, handler protocol logic,
parser logic, credential orchestration, retry/recovery policy, internal
monkeypatch compatibility indirection, GUI callback logic, or device
orchestration.

The public compatibility symbols SHALL include:

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

#### Scenario: Existing public import remains valid
- **WHEN** production code or tests import a worker with `from core.worker import HuaweiTE40Worker`
- **THEN** the import succeeds
- **AND** the imported class is the canonical `core.workers.codec_polling.HuaweiTE40Worker`

#### Scenario: Existing DMP public import remains valid
- **WHEN** production code or tests import `ExtronDMP64PlusMeterWorker` with `from core.worker import ExtronDMP64PlusMeterWorker`
- **THEN** the import succeeds
- **AND** `core.worker.ExtronDMP64PlusMeterWorker is core.workers.dmp.ExtronDMP64PlusMeterWorker`

#### Scenario: Worker facade remains small
- **WHEN** `core/worker.py` is inspected after decomposition
- **THEN** it contains only imports, documented facade exports, `__all__`, and minimal facade documentation
- **AND** it contains no worker `run()` implementation
- **AND** it contains no runtime compatibility indirection for internal test monkeypatch paths

#### Scenario: Core package lazy exports remain valid
- **WHEN** code imports `WorkerSignals`, `HuaweiTE20Worker`, or `AtenPDUWorker` through `core.__getattr__`
- **THEN** the lazy export continues to resolve through the compatibility worker layer

### Requirement: Internal test monkeypatch path migration
Public production compatibility SHALL cover worker class imports from
`core.worker`. Internal monkeypatch paths for worker implementation
dependencies SHALL NOT be treated as public production API.

Existing internal test patch targets, including
`core.worker.HuaweiTE40Handler`, `core.worker.CloudLinkBar310Handler`,
`core.worker.HuaweiTE40DataParser.parse_raw_data`,
`core.worker.HuaweiBar310DataParser.parse_raw_data`,
`core.worker.time.monotonic`, and `core.worker.wait_cancelable`, SHALL migrate
to the canonical dependency location in the focused worker module during
implementation. The implementation SHALL NOT add complex runtime compatibility
indirection in `core.worker` solely to preserve these internal monkeypatch paths.
The semantics of migrated tests SHALL remain the same.

#### Scenario: Codec patch path is migrated
- **WHEN** a test patches a TE40 or Bar 310 handler/parser dependency after decomposition
- **THEN** it patches the canonical dependency in `core.workers.codec_polling`
- **AND** the test verifies the same worker behavior as before

#### Scenario: DMP patch path is migrated
- **WHEN** a test patches DMP timing or cancellation helper behavior after decomposition
- **THEN** it patches the canonical dependency in `core.workers.dmp`
- **AND** the test verifies the same DMP lifecycle behavior as before

#### Scenario: Facade import compatibility is tested separately
- **WHEN** internal patch paths are migrated to focused modules
- **THEN** separate regression tests still prove every public worker class imports from `core.worker`
- **AND** each facade class has identity with its canonical implementation class

### Requirement: Shared worker infrastructure
Shared worker signal and error/redaction helpers SHALL live in
`core/workers/common.py` when they are moved out of `core/worker.py`.
`WorkerSignals` SHALL preserve the existing public signal names and signal
payload types: `finished`, `error`, `result`, `progress`, `status`,
`terminal_log`, `connected`, and `disconnected`.

Shared redaction helpers SHALL preserve existing error tuple shapes and SHALL
redact known worker secrets before emitting public errors, terminal logs,
stdout diagnostics, or result payloads.

#### Scenario: Signal contract is unchanged
- **WHEN** a moved worker creates its `signals` object
- **THEN** consumers can connect to the same signal names as before
- **AND** emitted payload shapes remain compatible with existing GUI and test consumers

#### Scenario: Error helper contract is unchanged
- **WHEN** a moved worker catches an exception containing an assigned credential value
- **THEN** the emitted error tuple keeps the previous category/message/details shape
- **AND** the credential value is redacted

#### Scenario: Common module has no worker imports
- **WHEN** `core/workers/common.py` is imported
- **THEN** it does not import focused worker modules, handlers, GUI modules, or application composition modules

### Requirement: Worker dependency direction
Focused worker modules SHALL depend downward on shared worker infrastructure,
handlers, parsers, domain modules, exception types, connection-profile helpers,
and redaction helpers. Focused worker modules SHALL NOT import `core.worker`,
and handlers SHALL NOT import worker modules to emit GUI-facing signals.

`core/workers/__init__.py` SHALL exist as the package boundary for focused
worker modules. It SHALL contain no worker implementation, orchestration,
lifecycle logic, credential logic, retry/recovery logic, handler construction
logic, parser logic, compatibility indirection, or mixed-domain aggregation.
It MAY contain minimal package documentation and simple convenience re-exports
only when required by existing consumers. Public backwards-compatible worker
imports SHALL continue through `core.worker`; `core.workers` SHALL NOT become a
second compatibility facade.

#### Scenario: Focused worker avoids facade import
- **WHEN** `core/workers/codec_polling.py`, `codec_actions.py`, `codec_call_logs.py`, `audio_dsp.py`, `dmp.py`, `matrix.py`, or `pdu.py` is imported
- **THEN** it does not import `core.worker`

#### Scenario: Workers package root remains minimal
- **WHEN** `core/workers/__init__.py` is inspected after decomposition
- **THEN** it contains no worker implementation or mixed-domain orchestration
- **AND** it does not duplicate `core.worker` as a public compatibility facade

#### Scenario: No new universal orchestration layer
- **WHEN** worker modules are decomposed
- **THEN** PDU, codec, DMP, Matrix, and audio-DSP lifecycles remain owned by their existing domain/application boundaries
- **AND** no new module hides their different retry, recovery, and mutation-safety contracts behind one universal worker orchestration API

#### Scenario: Handler layer stays GUI-signal free
- **WHEN** a protocol handler performs device I/O
- **THEN** it does not import worker modules or depend on Qt worker signals

### Requirement: Structural refactor behavioral equivalence
Worker module decomposition SHALL be behavior-preserving. It SHALL NOT change
credential ownership, credential fallback, successful credential memory,
transport profile ordering, retry semantics, state-changing operation safety,
DMP lifecycle, cancellation contract, timeout/session poisoning, recovery
budget, stale-context boundary, GUI-threading boundaries, signal lifecycle,
callback payload shapes, error classification, or secret redaction.

#### Scenario: Credential ownership remains in application layer
- **WHEN** any moved worker is constructed for one credential attempt
- **THEN** the worker uses only the assigned credential candidate
- **AND** it does not select, advance, wrap, or persist credential candidates

#### Scenario: Transport fallback is unchanged
- **WHEN** a moved codec worker tries supported connection profiles
- **THEN** it uses the same profile ordering and retry semantics that existed before decomposition
- **AND** transport fallback remains separate from credential fallback

#### Scenario: Mutation safety is unchanged
- **WHEN** a moved worker performs or reports a state-changing operation
- **THEN** the refactor adds no replay, no new recovery policy, no changed ambiguity handling, and no credential fallback after a potentially delivered mutation

#### Scenario: DMP lifecycle is unchanged
- **WHEN** `ExtronDMP64PlusMeterWorker` moves to `core/workers/dmp.py`
- **THEN** persistent polling lifecycle, cancellation, stale-context suppression, transaction timeout poisoning, recovery budget, and credential persistence semantics remain unchanged

#### Scenario: DMP credential-success gate is unchanged
- **WHEN** a moved DMP worker emits continuous meter snapshots or terminal failures
- **THEN** the credential-success gate and successful credential memory semantics remain unchanged

#### Scenario: DMP error classification is unchanged
- **WHEN** a moved DMP worker reports authentication, unsupported-device, transaction-timeout, connection, cancellation, stale, or generic failures
- **THEN** the machine-readable categories remain compatible with existing application and test consumers

#### Scenario: GUI threading is unchanged
- **WHEN** a moved worker performs network I/O
- **THEN** the work remains outside the Qt GUI thread under the existing background execution boundary

#### Scenario: Secrets remain redacted
- **WHEN** moved worker code emits logs, stdout diagnostics, GUI errors, public worker error payloads, or results
- **THEN** credentials, Session IDs, cookies, CSRF tokens, SSH secret material, and other secrets remain redacted

### Requirement: Worker decomposition validation
Implementation of the decomposition SHALL include focused regression tests for
compatibility imports from `core.worker`, canonical class identity through the
facade, `WorkerSignals` behavior when moved, migrated internal patch/mock
paths, unchanged worker error payload contracts, unchanged credential
ownership, unchanged transport fallback, unchanged state-changing operation
safety, unchanged DMP cancellation/lifecycle/stale/error/credential-success
contracts, absence of GUI-thread network I/O, and unchanged secret redaction.

#### Scenario: Compatibility imports are regression-tested
- **WHEN** focused worker import tests run
- **THEN** every public worker symbol imports from `core.worker`
- **AND** each facade class is identical to its canonical implementation class

#### Scenario: DMP compatibility import is regression-tested
- **WHEN** focused worker import tests run
- **THEN** `ExtronDMP64PlusMeterWorker` imports from `core.worker`
- **AND** `core.worker.ExtronDMP64PlusMeterWorker is core.workers.dmp.ExtronDMP64PlusMeterWorker`

#### Scenario: Patchability migration is regression-tested
- **WHEN** focused patch/mock tests run
- **THEN** each migrated handler/parser/timing helper patch path is verified at its canonical focused module location
- **AND** the tests fail if the canonical patch path stops controlling the worker dependency

#### Scenario: Error payload equivalence is regression-tested
- **WHEN** focused worker outcome tests run before and after decomposition
- **THEN** public error tuple categories, messages, details, result payloads, and completion behavior remain compatible

#### Scenario: Strict validation passes
- **WHEN** the decomposition implementation is complete
- **THEN** the focused regression tests pass
- **AND** `python -m unittest discover -s tests -p "test_*.py"` passes
- **AND** `.\openspec.cmd validate worker-module-decomposition --strict` passes
- **AND** `.\openspec.cmd validate --all --strict` passes
