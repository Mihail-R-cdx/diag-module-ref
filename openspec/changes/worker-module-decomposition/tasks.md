## 1. Preparation and inventory

- [x] 1.1 Reconfirm `origin/master` and preserve unrelated working-tree changes.
- [x] 1.2 Inventory all public imports from `core.worker` in production code and tests.
- [x] 1.3 Inventory direct canonical worker imports such as `core.te20_worker`.
- [x] 1.4 Inventory tests that patch or mock `core.worker` handler/parser symbols.
- [x] 1.5 Inventory tests that patch DMP timing/cancellation helpers through `core.worker`.
- [x] 1.6 Record the compatibility public symbol list before moving code, including `ExtronDMP64PlusMeterWorker`.

## 2. Shared infrastructure

- [x] 2.1 Add `core/workers/common.py` with `WorkerSignals`, `_worker_secrets`, `_safe_error`, and `_emit_error`.
- [x] 2.2 Keep common infrastructure free of focused worker, handler, GUI, and application-composition imports.
- [x] 2.3 Add focused tests for `WorkerSignals` signal names/types and redacted error emission if signal infrastructure moves.
- [x] 2.4 Add `core/workers/__init__.py` as a minimal package boundary without worker implementation, orchestration, lifecycle logic, credential logic, retry/recovery logic, handler construction logic, parser logic, compatibility indirection, or mixed-domain aggregation.

## 3. Focused worker modules

- [x] 3.1 Move `PolycomCallLogWorker` to `core/workers/codec_call_logs.py`.
- [x] 3.2 Move `BiampTesiraForteCIWorker` to `core/workers/audio_dsp.py`.
- [x] 3.3 Move `HuaweiTE40Worker`, `HuaweiBar310Worker`, and `PolycomRPG310Worker` to `core/workers/codec_polling.py`.
- [x] 3.4 Move `CodecSipFixWorker` to `core/workers/codec_actions.py`.
- [x] 3.5 Move `ExtronDMP64PlusMeterWorker` to `core/workers/dmp.py`.
- [x] 3.6 Move `ExtronIN1804Worker` to `core/workers/matrix.py`.
- [x] 3.7 Move `PDUOperationWorker` and `AtenPDUWorker` to `core/workers/pdu.py`.
- [x] 3.8 Keep `HuaweiTE20Worker` canonical in `core.te20_worker` unless a separate reviewed decision moves it.

## 4. Compatibility facade

- [x] 4.1 Convert `core/worker.py` to a facade with no worker run-loop implementation.
- [x] 4.2 Re-export all compatibility public worker symbols from `core.worker`.
- [x] 4.3 Ensure `core.worker` worker class objects are identical to their canonical module class objects.
- [x] 4.4 Migrate internal `core.worker` handler/parser/timing helper patch paths to canonical focused module patch paths.
- [x] 4.5 Do not add runtime compatibility indirection in `core.worker` for internal test monkeypatch paths.
- [x] 4.6 Add compatibility import tests for every public worker symbol, including `ExtronDMP64PlusMeterWorker`.
- [x] 4.7 Add class identity tests proving facade worker classes are identical to canonical implementation classes, including `core.worker.ExtronDMP64PlusMeterWorker is core.workers.dmp.ExtronDMP64PlusMeterWorker`.
- [x] 4.8 Add focused tests for migrated canonical patch/mock paths.

## 5. Behavioral regression coverage

- [x] 5.1 Run focused credential ownership tests for TE20, TE40, Bar 310, Polycom, Biamp, DMP, and Aten workers.
- [x] 5.2 Run focused transport fallback tests for TE20 and TE40.
- [x] 5.3 Run focused state-changing operation tests for codec SIP actions and PDU operations.
- [x] 5.4 Run focused DMP worker tests for cancellation, long-lived polling lifecycle, error classification, credential-success gate, stale-context boundary, secret redaction, and absence of GUI-thread network I/O.
- [x] 5.5 Run focused GUI worker signal consumer tests for `gui/main_window.py` and `gui/screens/codec_screen.py`.
- [x] 5.6 Run focused redaction tests for stdout, terminal logs, GUI errors, and public worker error payloads.

## 6. Validation

- [x] 6.1 Run the focused regression modules affected by worker imports and patch paths.
- [x] 6.2 Run `python -m unittest discover -s tests -p "test_*.py"`.
- [x] 6.3 Run `.\openspec.cmd validate worker-module-decomposition --strict`.
- [x] 6.4 Run `.\openspec.cmd validate --all --strict`.
- [x] 6.5 Run `git diff --check`.
- [x] 6.6 Confirm no production behavior, signal payload, credential fallback, transport fallback, mutation safety, DMP lifecycle, GUI-threading, or redaction contract changed.
