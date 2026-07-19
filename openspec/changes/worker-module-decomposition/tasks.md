## 1. Preparation and inventory

- [ ] 1.1 Reconfirm `origin/master` and preserve unrelated working-tree changes.
- [ ] 1.2 Inventory all public imports from `core.worker` in production code and tests.
- [ ] 1.3 Inventory direct canonical worker imports such as `core.te20_worker`.
- [ ] 1.4 Inventory tests that patch or mock `core.worker` handler/parser symbols.
- [ ] 1.5 Record the compatibility public symbol list before moving code.

## 2. Shared infrastructure

- [ ] 2.1 Add `core/workers/common.py` with `WorkerSignals`, `_worker_secrets`, `_safe_error`, and `_emit_error`.
- [ ] 2.2 Keep common infrastructure free of focused worker, handler, GUI, and application-composition imports.
- [ ] 2.3 Add focused tests for `WorkerSignals` signal names/types and redacted error emission if signal infrastructure moves.

## 3. Focused worker modules

- [ ] 3.1 Move `PolycomCallLogWorker` to `core/workers/codec_call_logs.py`.
- [ ] 3.2 Move `BiampTesiraForteCIWorker` to `core/workers/audio_dsp.py`.
- [ ] 3.3 Move `HuaweiTE40Worker`, `HuaweiBar310Worker`, and `PolycomRPG310Worker` to `core/workers/codec_polling.py`.
- [ ] 3.4 Move `CodecSipFixWorker` to `core/workers/codec_actions.py`.
- [ ] 3.5 Move `ExtronIN1804Worker` to `core/workers/matrix.py`.
- [ ] 3.6 Move `PDUOperationWorker` and `AtenPDUWorker` to `core/workers/pdu.py`.
- [ ] 3.7 Keep `HuaweiTE20Worker` canonical in `core.te20_worker` unless a separate reviewed decision moves it.

## 4. Compatibility facade

- [ ] 4.1 Convert `core/worker.py` to a facade with no worker run-loop implementation.
- [ ] 4.2 Re-export all compatibility public worker symbols from `core.worker`.
- [ ] 4.3 Ensure `core.worker` worker class objects are identical to their canonical module class objects.
- [ ] 4.4 Choose and document the strategy for existing `core.worker` handler/parser patch points.
- [ ] 4.5 Add compatibility import tests for every public worker symbol.
- [ ] 4.6 Add focused tests for patch/mock paths that are preserved or intentionally migrated.

## 5. Behavioral regression coverage

- [ ] 5.1 Run focused credential ownership tests for TE20, TE40, Bar 310, Polycom, Biamp, and Aten workers.
- [ ] 5.2 Run focused transport fallback tests for TE20 and TE40.
- [ ] 5.3 Run focused state-changing operation tests for codec SIP actions and PDU operations.
- [ ] 5.4 Run focused DMP lifecycle tests when any import adjacency affects DMP polling or background codec operations.
- [ ] 5.5 Run focused GUI worker signal consumer tests for `gui/main_window.py` and `gui/screens/codec_screen.py`.
- [ ] 5.6 Run focused redaction tests for stdout, terminal logs, GUI errors, and public worker error payloads.

## 6. Validation

- [ ] 6.1 Run the focused regression modules affected by worker imports and patch paths.
- [ ] 6.2 Run `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] 6.3 Run `.\openspec.cmd validate worker-module-decomposition --strict`.
- [ ] 6.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 6.5 Run `git diff --check`.
- [ ] 6.6 Confirm no production behavior, signal payload, credential fallback, transport fallback, mutation safety, DMP lifecycle, GUI-threading, or redaction contract changed.
