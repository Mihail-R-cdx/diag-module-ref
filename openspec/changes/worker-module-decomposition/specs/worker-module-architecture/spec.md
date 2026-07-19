## ADDED Requirements

### Requirement: Focused worker implementation modules
Worker implementation ownership SHALL be decomposed from `core/worker.py` into
focused `core/workers/` modules by domain and responsibility boundary rather
than by line count alone. The decomposition SHALL use the following canonical
ownership unless implementation review identifies a stronger local boundary:

- `core/workers/common.py`: `WorkerSignals` and shared redacted error helpers;
- `core/workers/codec_polling.py`: `HuaweiTE40Worker`,
  `HuaweiBar310Worker`, and `PolycomRPG310Worker`;
- `core/workers/codec_actions.py`: `CodecSipFixWorker`;
- `core/workers/codec_call_logs.py`: `PolycomCallLogWorker`;
- `core/workers/audio_dsp.py`: `BiampTesiraForteCIWorker`;
- `core/workers/matrix.py`: `ExtronIN1804Worker`;
- `core/workers/pdu.py`: `PDUOperationWorker` and `AtenPDUWorker`.

`HuaweiTE20Worker` SHALL remain canonical in the existing `core.te20_worker`
module during this change unless a separate reviewed architecture decision
moves it.

#### Scenario: Codec polling worker has focused ownership
- **WHEN** a developer needs to change TE40, Bar 310, or Polycom diagnostic polling behavior
- **THEN** the canonical implementation is in `core/workers/codec_polling.py`
- **AND** unrelated PDU, Matrix, audio-DSP, and call-log worker implementation code is not required reading

#### Scenario: Codec action worker has focused ownership
- **WHEN** a developer needs to change SIP server fix worker behavior
- **THEN** the canonical implementation is in `core/workers/codec_actions.py`
- **AND** the move does not change the public SIP fix result or error payload contract

#### Scenario: Call-log worker has focused ownership
- **WHEN** a developer needs to change Polycom call-log loading
- **THEN** the canonical implementation is in `core/workers/codec_call_logs.py`
- **AND** the operation remains separate from generic codec polling workers

#### Scenario: PDU worker has focused ownership
- **WHEN** a developer needs to change PDU refresh or PDU command worker behavior
- **THEN** the canonical implementation is in `core/workers/pdu.py`
- **AND** device-specific PDU protocol semantics remain outside a universal hardware worker layer

#### Scenario: TE20 remains explicitly separate
- **WHEN** the worker facade exports `HuaweiTE20Worker`
- **THEN** it imports the worker from `core.te20_worker`
- **AND** this change does not automatically move TE20 into `core/workers/codec_polling.py`

### Requirement: Worker compatibility facade
`core/worker.py` SHALL remain as a small compatibility facade after the worker
implementation moves. It SHALL re-export the existing public worker symbols
without containing worker run-loop implementation, handler protocol logic,
parser logic, credential iteration, retry policy, GUI callback logic, or device
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
- `ExtronIN1804Worker`;
- `PDUOperationWorker`;
- `AtenPDUWorker`.

#### Scenario: Existing public import remains valid
- **WHEN** production code or tests import a worker with `from core.worker import HuaweiTE40Worker`
- **THEN** the import succeeds
- **AND** the imported class is the canonical `core.workers.codec_polling.HuaweiTE40Worker`

#### Scenario: Worker facade remains small
- **WHEN** `core/worker.py` is inspected after decomposition
- **THEN** it contains only imports, `__all__`, narrow compatibility aliases, and facade documentation
- **AND** it contains no worker `run()` implementation

#### Scenario: Core package lazy exports remain valid
- **WHEN** code imports `WorkerSignals`, `HuaweiTE20Worker`, or `AtenPDUWorker` through `core.__getattr__`
- **THEN** the lazy export continues to resolve through the compatibility worker layer

### Requirement: Compatibility-sensitive patch paths
The implementation SHALL explicitly handle tests and consumers that patch
worker implementation dependencies through `core.worker`. Existing known patch
targets include `core.worker.HuaweiTE40Handler`,
`core.worker.CloudLinkBar310Handler`,
`core.worker.HuaweiTE40DataParser.parse_raw_data`, and
`core.worker.HuaweiBar310DataParser.parse_raw_data`.

The implementation SHALL either preserve each listed patch path through a
narrow compatibility mechanism that still affects the moved worker
implementation, or migrate the affected tests to the canonical focused module
patch path in the same refactor. The chosen strategy SHALL be covered by
focused regression tests and documented in implementation evidence. Public
worker class imports from `core.worker` SHALL remain compatible in either case.

#### Scenario: Preserved patch path remains effective
- **GIVEN** the implementation chooses to preserve a `core.worker` handler or parser patch path
- **WHEN** a test patches that path
- **THEN** the moved worker implementation observes the patched dependency

#### Scenario: Migrated patch path is deliberate
- **GIVEN** the implementation chooses to migrate an old `core.worker` handler or parser patch path
- **WHEN** the affected test is updated to the canonical focused module path
- **THEN** the test continues to verify the same worker behavior
- **AND** a compatibility import test proves the worker class still imports from `core.worker`

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

`core/workers/__init__.py`, if added, SHALL be an optional export convenience
only and SHALL NOT contain worker implementation code or mixed-domain
orchestration.

#### Scenario: Focused worker avoids facade import
- **WHEN** `core/workers/codec_polling.py`, `codec_actions.py`,
  `codec_call_logs.py`, `audio_dsp.py`, `matrix.py`, or `pdu.py` is imported
- **THEN** it does not import `core.worker`

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
DMP lifecycle, GUI-threading boundaries, signal lifecycle, callback payload
shapes, or secret redaction.

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
- **WHEN** DMP polling or adjacent background codec operation code interacts with moved workers
- **THEN** persistent polling lifecycle, cancellation, stale-context suppression, transaction timeout poisoning, recovery budget, and credential persistence semantics remain unchanged

#### Scenario: GUI threading is unchanged
- **WHEN** a moved worker performs network I/O
- **THEN** the work remains outside the Qt GUI thread under the existing background execution boundary

#### Scenario: Secrets remain redacted
- **WHEN** moved worker code emits logs, stdout diagnostics, GUI errors, public worker error payloads, or results
- **THEN** credentials, Session IDs, cookies, CSRF tokens, and other secrets remain redacted

### Requirement: Worker decomposition validation
Implementation of the decomposition SHALL include focused regression tests for
compatibility imports from `core.worker`, canonical class identity through the
facade, `WorkerSignals` behavior when moved, compatibility-sensitive patch/mock
paths, unchanged worker error payload contracts, unchanged credential
ownership, unchanged transport fallback, unchanged state-changing operation
safety, and unchanged secret redaction.

#### Scenario: Compatibility imports are regression-tested
- **WHEN** focused worker import tests run
- **THEN** every public worker symbol imports from `core.worker`
- **AND** each facade class is identical to its canonical implementation class

#### Scenario: Patchability is regression-tested
- **WHEN** focused patch/mock tests run
- **THEN** each preserved or intentionally migrated handler/parser patch path is verified
- **AND** the tests fail if the selected patch strategy silently stops controlling the worker dependency

#### Scenario: Error payload equivalence is regression-tested
- **WHEN** focused worker outcome tests run before and after decomposition
- **THEN** public error tuple categories, messages, details, result payloads, and completion behavior remain compatible

#### Scenario: Strict validation passes
- **WHEN** the decomposition implementation is complete
- **THEN** the focused regression tests pass
- **AND** `python -m unittest discover -s tests -p "test_*.py"` passes
- **AND** `.\openspec.cmd validate worker-module-decomposition --strict` passes
- **AND** `.\openspec.cmd validate --all --strict` passes
