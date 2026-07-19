import ast
import importlib
from pathlib import Path
import unittest


PUBLIC_WORKER_SYMBOLS = (
    "WorkerSignals",
    "HuaweiTE20Worker",
    "HuaweiTE40Worker",
    "HuaweiBar310Worker",
    "PolycomRPG310Worker",
    "CodecSipFixWorker",
    "PolycomCallLogWorker",
    "BiampTesiraForteCIWorker",
    "ExtronDMP64PlusMeterWorker",
    "ExtronIN1804Worker",
    "PDUOperationWorker",
    "AtenPDUWorker",
)


CANONICAL_CLASSES = {
    "HuaweiTE20Worker": "core.te20_worker",
    "HuaweiTE40Worker": "core.workers.codec_polling",
    "HuaweiBar310Worker": "core.workers.codec_polling",
    "PolycomRPG310Worker": "core.workers.codec_polling",
    "CodecSipFixWorker": "core.workers.codec_actions",
    "PolycomCallLogWorker": "core.workers.codec_call_logs",
    "BiampTesiraForteCIWorker": "core.workers.audio_dsp",
    "ExtronDMP64PlusMeterWorker": "core.workers.dmp",
    "ExtronIN1804Worker": "core.workers.matrix",
    "PDUOperationWorker": "core.workers.pdu",
    "AtenPDUWorker": "core.workers.pdu",
}


class WorkerFacadeCompatibilityTests(unittest.TestCase):
    def test_public_worker_symbols_import_from_facade(self):
        facade = importlib.import_module("core.worker")

        self.assertEqual(list(PUBLIC_WORKER_SYMBOLS), facade.__all__)
        for symbol in PUBLIC_WORKER_SYMBOLS:
            self.assertTrue(hasattr(facade, symbol), symbol)

    def test_facade_classes_are_canonical_classes(self):
        facade = importlib.import_module("core.worker")
        common = importlib.import_module("core.workers.common")

        self.assertIs(facade.WorkerSignals, common.WorkerSignals)
        for symbol, module_name in CANONICAL_CLASSES.items():
            canonical = importlib.import_module(module_name)
            self.assertIs(getattr(facade, symbol), getattr(canonical, symbol), symbol)

    def test_dmp_facade_identity_is_canonical_dmp_worker(self):
        facade = importlib.import_module("core.worker")
        dmp = importlib.import_module("core.workers.dmp")

        self.assertIs(facade.ExtronDMP64PlusMeterWorker, dmp.ExtronDMP64PlusMeterWorker)

    def test_worker_signals_contract_is_unchanged(self):
        common = importlib.import_module("core.workers.common")
        signals = common.WorkerSignals()

        expected_signatures = {
            "finished": "2finished()",
            "error": "2error(PyQt_PyObject)",
            "result": "2result(PyQt_PyObject)",
            "progress": "2progress(int)",
            "status": "2status(QString)",
            "terminal_log": "2terminal_log(QString)",
            "connected": "2connected()",
            "disconnected": "2disconnected()",
        }
        for name, signature in expected_signatures.items():
            self.assertTrue(hasattr(signals, name), name)
            self.assertEqual(signature, getattr(signals, name).signal, name)

    def test_workers_package_root_is_minimal(self):
        package = importlib.import_module("core.workers")

        self.assertEqual("Focused worker implementation package.", package.__doc__)
        self.assertNotIn("__all__", vars(package))


class WorkerDependencyDirectionTests(unittest.TestCase):
    def parse_module(self, relative_path):
        path = Path(__file__).resolve().parents[1] / relative_path
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def imported_modules(self, tree):
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        return modules

    def test_focused_workers_do_not_import_facade(self):
        focused_modules = (
            "core/workers/audio_dsp.py",
            "core/workers/codec_actions.py",
            "core/workers/codec_call_logs.py",
            "core/workers/codec_polling.py",
            "core/workers/dmp.py",
            "core/workers/matrix.py",
            "core/workers/pdu.py",
        )

        for relative_path in focused_modules:
            imports = self.imported_modules(self.parse_module(relative_path))
            self.assertNotIn("core.worker", imports, relative_path)

    def test_common_module_has_no_focused_worker_handler_or_gui_imports(self):
        imports = self.imported_modules(self.parse_module("core/workers/common.py"))

        self.assertFalse(
            any(
                module.startswith("core.workers.")
                or module.startswith("handlers")
                or module.startswith("gui")
                for module in imports
            ),
            imports,
        )

    def test_facade_contains_no_worker_run_implementation(self):
        tree = self.parse_module("core/worker.py")

        class_defs = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        run_defs = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        self.assertEqual([], class_defs)
        self.assertEqual([], run_defs)


if __name__ == "__main__":
    unittest.main()
