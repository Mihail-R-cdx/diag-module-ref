## Why

`core/worker.py` has become a multi-domain worker module. It currently mixes
shared Qt signal infrastructure, credential/error redaction helpers, codec
polling workers, codec state-changing actions, Polycom call-log loading,
audio-DSP polling, DMP long-lived meter polling, matrix polling, and PDU
refresh/control workers in one file. As a result, a developer or coding agent
changing one device family must load unrelated workers, handlers, parser
imports, and safety contracts.

The current file also carries public import compatibility. Production GUI code
and tests import workers from `core.worker`; several tests patch internal
handler/parser/timing dependencies through `core.worker`. A structural refactor
therefore needs an explicit compatibility facade, fixed canonical module
ownership, and focused regression coverage.

## What Changes

- Decompose implementation ownership out of `core/worker.py` into focused
  modules under `core/workers/` by domain/responsibility boundary.
- Keep `core/worker.py` as a small compatibility facade that re-exports the
  existing public worker symbols.
- Keep `HuaweiTE20Worker` in its existing `core.te20_worker` module during this
  change and continue importing it through the worker layer.
- Move `ExtronDMP64PlusMeterWorker` to `core/workers/dmp.py`, not
  `audio_dsp.py`, because it owns a distinct long-lived polling lifecycle,
  cancellation contract, timeout/session poisoning, recovery, credential
  success gate, and stale-context semantics.
- Move shared `WorkerSignals` and redacted worker error helpers to
  `core/workers/common.py`.
- Migrate internal test monkeypatch paths from `core.worker.<dependency>` to
  the canonical focused worker module locations; do not add runtime facade
  indirection solely for internal test patch paths.
- Preserve runtime behavior: signal shapes, credential ownership, credential
  fallback, transport fallback, mutation safety, DMP lifecycle, cancellation,
  stale-context suppression, background execution boundaries, and secret
  redaction are unchanged.
- Avoid introducing a new universal orchestration layer that combines codec,
  DMP, Matrix, audio-DSP, and PDU lifecycles.

## Proposed Module Map

```text
core/
    worker.py                  # compatibility facade only
    te20_worker.py             # existing Huawei TE20 worker remains in place

    workers/
        __init__.py            # package boundary; minimal docs/re-exports only
        common.py              # WorkerSignals and shared redacted error helpers
        codec_polling.py       # HuaweiTE40Worker, HuaweiBar310Worker, PolycomRPG310Worker
        codec_actions.py       # CodecSipFixWorker
        codec_call_logs.py     # PolycomCallLogWorker
        audio_dsp.py           # BiampTesiraForteCIWorker
        dmp.py                 # ExtronDMP64PlusMeterWorker
        matrix.py              # ExtronIN1804Worker
        pdu.py                 # PDUOperationWorker, AtenPDUWorker
```

This is the approved target structure for implementation. If implementation
finds a real architectural obstacle to these boundaries, the engineer must stop
and return the change for architectural review rather than choosing different
boundaries independently.

## Capabilities

### New Capabilities

- `worker-module-architecture`: define the worker implementation decomposition,
  compatibility facade, dependency direction, patchability migration, and
  behavioral equivalence contract.

### Modified Capabilities

- `request-lifecycle-and-recovery`: clarify that worker module moves must keep
  background execution, request-context isolation, DMP polling lifecycle, and
  signal lifecycle behavior unchanged.
- `credential-source-isolation`: clarify that decomposed worker modules do not
  take ownership of credential iteration or successful credential memory.
- `secure-observability-and-validation`: clarify that moved shared redaction
  helpers must not weaken secret handling, public error payloads, or
  repository-local OpenSpec validation workflow evidence.

## Impact

Future implementation is expected to touch `core/worker.py`, add focused
modules under `core/workers/`, migrate internal test patch targets to canonical
focused module paths, and add focused compatibility/regression tests. It should
not change production behavior, GUI workflows, handler protocols, credential
resolution, transport retry order, PDU safety policy, DMP polling lifecycle,
cancellation, stale-context suppression, credential-success gate, error
classification, secret redaction, or existing worker signal payload shapes.
