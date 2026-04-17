import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMessageBox

from gui.main_window import VCSDiagnosticApp


LOG_PATH = Path(__file__).with_name("app_crash.log")


def _write_crash_log(title: str, exc_type, exc_value, exc_traceback) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trace = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    message = f"[{timestamp}] {title}\n{trace}\n"
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(message)
    return trace


def _show_crash_message(trace: str) -> None:
    app = QApplication.instance()
    if app is None:
        return

    last_line = trace.splitlines()[-1] if trace.splitlines() else "Unknown error"
    QMessageBox.critical(
        None,
        "Ошибка запуска",
        "Приложение столкнулось с неожиданной ошибкой.\n\n"
        f"Подробности сохранены в:\n{LOG_PATH}\n\n"
        f"Последняя ошибка:\n{last_line}",
    )


def _handle_unhandled_exception(exc_type, exc_value, exc_traceback) -> None:
    trace = _write_crash_log(
        "Unhandled exception in main thread",
        exc_type,
        exc_value,
        exc_traceback,
    )
    _show_crash_message(trace)


def _handle_thread_exception(args) -> None:
    _write_crash_log(
        f"Unhandled exception in thread {args.thread.name}",
        args.exc_type,
        args.exc_value,
        args.exc_traceback,
    )


def main():
    sys.excepthook = _handle_unhandled_exception
    threading.excepthook = _handle_thread_exception

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = VCSDiagnosticApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
