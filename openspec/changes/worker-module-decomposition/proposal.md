## Why

`core/worker.py` has become a multi-domain worker module. It currently mixes
shared Qt signal infrastructure, credential/error redaction helpers, codec
polling workers, codec state-changing actions, Polycom call-log loading,
audio-DSP polling, matrix polling, and PDU refresh/control workers in one file.
As a result, a developer or coding agent changing one device family must load
unrelated workers, handlers, parser imports, and safety contracts.

The current file also carries public import compatibility. Production GUI code
and tests import workers from `core.worker`; several tests patch handler and
parser symbols through `core.worker`. A structural refactor therefore needs an
explicit compatibility facade and focused regression coverage, not a mass
consumer migration.

## What Changes

- Decompose implementation ownership out of `core/worker.py` into focused
  modules under `core/workers/` by domain/responsibility boundary.
- Keep `core/worker.py` as a small compatibility facade that re-exports the
  existing public worker symbols and required temporary compatibility patch
  points.
- Keep `HuaweiTE20Worker` in its existing `core.te20_worker` module during this
  change and continue importing it through the worker layer; do not move it
  without a separate architectural reason.
- Move shared `WorkerSignals` and redacted worker error helpers to
  `core/workers/common.py`.
- Preserve runtime behavior: signal shapes, credential ownership, credential
  fallback, transport fallback, mutation safety, DMP lifecycle, background
  execution boundaries, and secret redaction are unchanged.
- Avoid introducing a new universal orchestration layer that combines codec,
  DMP, Matrix, audio-DSP, and PDU lifecycles.

## Proposed Module Map

```text
core/
    worker.py                  # compatibility facade only
    te20_worker.py             # existing Huawei TE20 worker remains in place
    workers/
        __init__.py            # optional package export convenience
        common.py              # WorkerSignals and shared redacted error helpers
        codec_polling.py       # HuaweiTE40Worker, HuaweiBar310Worker, PolycomRPG310Worker
        codec_actions.py       # CodecSipFixWorker
        codec_call_logs.py     # PolycomCallLogWorker
        audio_dsp.py           # BiampTesiraForteCIWorker
        matrix.py              # ExtronIN1804Worker
        pdu.py                 # PDUOperationWorker, AtenPDUWorker
```

This is the target for implementation review. File names may change only if the
implementation finds a stronger repository-local boundary.

## Capabilities

### New Capabilities

- `worker-module-architecture`: define the worker implementation decomposition,
  compatibility facade, dependency direction, patchability migration, and
  behavioral equivalence contract.

### Modified Capabilities

- `request-lifecycle-and-recovery`: clarify that worker module moves must keep
  background execution and signal lifecycle behavior unchanged.
- `credential-source-isolation`: clarify that decomposed worker modules do not
  take ownership of credential iteration or successful credential memory.
- `secure-observability-and-validation`: clarify that moved shared redaction
  helpers must not weaken secret handling or public error payloads.

## Impact

Future implementation is expected to touch `core/worker.py`, add focused
modules under `core/workers/`, and add focused compatibility/regression tests.
It should not change production behavior, GUI workflows, handler protocols,
credential resolution, transport retry order, PDU safety policy, DMP polling
lifecycle, or existing worker signal payload shapes.
