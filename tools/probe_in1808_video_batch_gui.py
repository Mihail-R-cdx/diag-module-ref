"""Small GUI for the read-only exact-IN1808 Video batch hardware probe.

Credentials are resolved through the repository's existing JsonCredentialProvider
from the ignored root-level credentials.local.json.  This tool never parses the
credential file directly and never renders credential values.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PyQt5.QtCore import QThread, pyqtSignal  # noqa: E402
from PyQt5.QtWidgets import (  # noqa: E402
    QApplication,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.credentials import (  # noqa: E402
    Credential,
    JsonCredentialProvider,
    resolve_request_credential_candidates,
)
from core.exceptions import is_confirmed_matrix_credential_rejection  # noqa: E402
from handlers.extron.in1804 import ExtronIN1804Handler  # noqa: E402
from handlers.extron.matrix import (  # noqa: E402
    normalize_identity_response,
    resolve_matrix_capabilities,
)
from tools.probe_in1808_video_batch import (  # noqa: E402
    BATCH_GUARD_COMMAND,
    VIDEO_STATUS_COMMANDS,
)


DEVICE_MODEL = "Extron IN1808"


def _safe_error_text(error: BaseException, candidates: Sequence[Credential]) -> str:
    text = f"{type(error).__name__}: {error}"
    for credential in candidates:
        for value in (credential.username, credential.password):
            if value:
                text = text.replace(value, "<redacted>")
    return text


def _format_raw_section(label: str, result: dict, elapsed: float | None = None) -> str:
    raw = result.get("raw_response", b"") if isinstance(result, dict) else b""
    if not isinstance(raw, bytes):
        raw = str(raw).encode("utf-8", errors="replace")

    lines = [f"=== {label} ==="]
    if elapsed is not None:
        lines.append(f"elapsed_seconds={elapsed:.3f}")
    lines.extend(
        (
            f"success={bool(result.get('success')) if isinstance(result, dict) else False}",
            f"raw_length={len(raw)}",
            f"raw_repr={raw!r}",
            f"decoded_repr={raw.decode('utf-8', errors='replace')!r}",
        )
    )
    chunks = [chunk for chunk in raw.split(b"\r\r\n") if chunk]
    lines.append(f"observed_double_crlf_chunks={len(chunks)}")
    for index, chunk in enumerate(chunks, 1):
        lines.append(f"chunk[{index:02d}]={chunk!r}")
    return "\n".join(lines)


class ProbeThread(QThread):
    output = pyqtSignal(str)
    succeeded = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(
        self,
        ip_address: str,
        port: int,
        candidates: Sequence[Credential],
        parent=None,
    ):
        super().__init__(parent)
        self.ip_address = ip_address
        self.port = port
        self.candidates = tuple(candidates)

    def run(self) -> None:
        try:
            self._run_probe()
        except Exception as error:
            self.failed.emit(_safe_error_text(error, self.candidates))

    def _run_probe(self) -> None:
        if not self.candidates:
            raise RuntimeError("Для Extron IN1808 не настроены credentials.")

        for index, credential in enumerate(self.candidates):
            handler = ExtronIN1804Handler(
                self.ip_address,
                port=self.port,
                expected_model=DEVICE_MODEL,
                **credential.as_handler_kwargs(),
            )
            try:
                self.output.emit(
                    f"Подключение к {self.ip_address}:{self.port}; "
                    f"credential candidate {index + 1}/{len(self.candidates)}"
                )
                try:
                    handler.connect()
                except Exception as error:
                    if (
                        is_confirmed_matrix_credential_rejection(error)
                        and index + 1 < len(self.candidates)
                    ):
                        self.output.emit(
                            "Credential отклонён устройством; пробую следующий "
                            "настроенный профиль.\n"
                        )
                        continue
                    raise

                identity_result = handler.send_command("1I")
                self.output.emit(
                    _format_raw_section("IDENTITY BEFORE BATCH", identity_result)
                )

                identity = normalize_identity_response(
                    "1I",
                    identity_result.get("response", "") if identity_result else "",
                )
                profile = resolve_matrix_capabilities(identity)
                self.output.emit(
                    f"normalized_identity={identity!r}\n"
                    f"resolved_model={getattr(profile, 'exact_model', None)!r}"
                )
                if profile is None or profile.exact_model != "IN1808":
                    raise RuntimeError(
                        "Exact IN1808 identity gate failed; batch was NOT sent."
                    )

                probe_commands = (BATCH_GUARD_COMMAND,) + VIDEO_STATUS_COMMANDS
                self.output.emit("\n=== BATCH COMMAND LIST ===")
                for command_index, command in enumerate(probe_commands, 1):
                    suffix = "  [framing guard]" if command_index == 1 else ""
                    self.output.emit(f"{command_index:02d}: {command}{suffix}")
                batch = "\r".join(probe_commands)
                self.output.emit(
                    f"batch_command_count={len(probe_commands)}\n"
                    f"expected_status_payload_count={len(VIDEO_STATUS_COMMANDS)}\n"
                    f"batch_wire_repr={(batch + chr(13))!r}"
                )

                started = time.monotonic()
                batch_result = handler.send_command(batch)
                elapsed = time.monotonic() - started
                self.output.emit(
                    _format_raw_section(
                        "VIDEO BATCH RAW RESPONSE",
                        batch_result,
                        elapsed,
                    )
                )

                followup = handler.send_command("1I")
                self.output.emit(
                    _format_raw_section("IDENTITY AFTER BATCH", followup)
                )
                followup_identity = normalize_identity_response(
                    "1I",
                    followup.get("response", "") if followup else "",
                )
                self.output.emit(
                    f"post_batch_normalized_identity={followup_identity!r}"
                )
                if followup_identity is None:
                    raise RuntimeError(
                        "Post-batch identity check failed; session framing may be stale."
                    )

                self.output.emit(
                    "\nГотово. Нажмите «Копировать вывод» и пришлите результат в чат."
                )
                self.succeeded.emit()
                return
            finally:
                try:
                    handler.disconnect()
                except Exception:
                    pass

        raise RuntimeError("Все настроенные credentials были отклонены устройством.")


class ProbeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IN1808 Video Batch Probe")
        self.resize(960, 720)
        self._thread: ProbeThread | None = None

        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        intro = QLabel(
            "Read-only probe: 1I → guard 1I + 30 Video queries одним batch → 1I.\n"
            "Credentials берутся из credentials.local.json для Extron IN1808."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("Например: 192.168.1.100")
        form.addRow("IP IN1808:", self.ip_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22023)
        form.addRow("Порт:", self.port_spin)
        layout.addLayout(form)

        self.credentials_label = QLabel()
        self.credentials_label.setWordWrap(True)
        layout.addWidget(self.credentials_label)

        buttons = QHBoxLayout()
        self.run_button = QPushButton("Запустить batch")
        self.copy_button = QPushButton("Копировать вывод")
        self.copy_button.setEnabled(False)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.copy_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.output_edit = QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        layout.addWidget(self.output_edit, 1)

        self.status_label = QLabel("Готово к запуску.")
        layout.addWidget(self.status_label)

        self.run_button.clicked.connect(self._start_probe)
        self.copy_button.clicked.connect(self._copy_output)

        self._refresh_credentials_status()

    def _resolve_candidates(self) -> tuple[Credential, ...]:
        provider = JsonCredentialProvider()
        return tuple(
            resolve_request_credential_candidates(
                provider,
                device_model=DEVICE_MODEL,
            )
        )

    def _refresh_credentials_status(self) -> None:
        try:
            candidates = self._resolve_candidates()
            self.credentials_label.setText(
                "credentials.local.json: найдено настроенных кандидатов "
                f"для {DEVICE_MODEL}: {len(candidates)}. Значения скрыты."
            )
        except Exception as error:
            self.credentials_label.setText(
                "credentials.local.json: ошибка конфигурации — "
                f"{type(error).__name__}: {error}"
            )

    def _start_probe(self) -> None:
        ip_address = self.ip_edit.text().strip()
        if not ip_address:
            QMessageBox.warning(self, "IN1808 Batch Probe", "Введите IP устройства.")
            return

        try:
            candidates = self._resolve_candidates()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Credentials",
                f"Не удалось загрузить credentials.local.json:\n"
                f"{type(error).__name__}: {error}",
            )
            return

        self.output_edit.clear()
        self.copy_button.setEnabled(False)
        self.run_button.setEnabled(False)
        self.ip_edit.setEnabled(False)
        self.port_spin.setEnabled(False)
        self.status_label.setText("Выполняется read-only batch probe...")

        thread = ProbeThread(
            ip_address,
            self.port_spin.value(),
            candidates,
            self,
        )
        self._thread = thread
        thread.output.connect(self._append_output)
        thread.succeeded.connect(self._probe_succeeded)
        thread.failed.connect(self._probe_failed)
        thread.finished.connect(self._probe_finished)
        thread.start()

    def _append_output(self, text: str) -> None:
        self.output_edit.appendPlainText(text)

    def _probe_succeeded(self) -> None:
        self.status_label.setText("Probe завершён успешно.")
        self.copy_button.setEnabled(True)

    def _probe_failed(self, message: str) -> None:
        self._append_output(f"\nERROR: {message}")
        self.status_label.setText("Probe завершился ошибкой.")
        self.copy_button.setEnabled(True)

    def _probe_finished(self) -> None:
        self.run_button.setEnabled(True)
        self.ip_edit.setEnabled(True)
        self.port_spin.setEnabled(True)
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

    def _copy_output(self) -> None:
        QApplication.clipboard().setText(self.output_edit.toPlainText())
        self.status_label.setText("Вывод скопирован в буфер обмена.")


def main() -> int:
    app = QApplication(sys.argv)
    window = ProbeWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
