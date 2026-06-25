"""Core package exports with lazy imports."""

__all__ = [
    "ProtocolHandler",
    "BaseHuaweiCodecHandler",
    "ProtocolFactory",
    "HuaweiTE40DataParser",
    "AtenPDUDataParser",
    "WorkerSignals",
    "HuaweiTE20Worker",
    "AtenPDUWorker",
]


def __getattr__(name):
    if name in {"ProtocolHandler", "BaseHuaweiCodecHandler"}:
        from core.base_handler import BaseHuaweiCodecHandler, ProtocolHandler

        return {
            "ProtocolHandler": ProtocolHandler,
            "BaseHuaweiCodecHandler": BaseHuaweiCodecHandler,
        }[name]
    if name in {"HuaweiTE40DataParser", "AtenPDUDataParser"}:
        from core.parser import AtenPDUDataParser, HuaweiTE40DataParser

        return {
            "HuaweiTE40DataParser": HuaweiTE40DataParser,
            "AtenPDUDataParser": AtenPDUDataParser,
        }[name]
    if name in {"WorkerSignals", "HuaweiTE20Worker", "AtenPDUWorker"}:
        from core.worker import AtenPDUWorker, HuaweiTE20Worker, WorkerSignals

        return {
            "WorkerSignals": WorkerSignals,
            "HuaweiTE20Worker": HuaweiTE20Worker,
            "AtenPDUWorker": AtenPDUWorker,
        }[name]
    if name == "ProtocolFactory":
        from core.factory import ProtocolFactory

        return ProtocolFactory
    raise AttributeError(name)
