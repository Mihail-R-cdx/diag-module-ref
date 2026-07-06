"""Exercise Polycom GUI controls through SSH when Web UI sessions are full.

The script uses the real CodecScreen buttons.  It obtains one credential
object already configured by the application, never prints it, verifies
``not in a call`` before every state-changing click, and restores state in
``finally`` blocks.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import time
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui.main_window import VCSDiagnosticApp
from handlers.polycom.rpg310 import PolycomRPG310Handler


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "operation",
        choices=("microphone-mute-cycle", "presentation-cycle"),
    )
    parser.add_argument("--credential-index", type=int, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication.instance() or QApplication([])
    sink = io.StringIO()
    result = {
        "operation": args.operation,
        "address": "10.10.0.x",
        "ssh_connected": False,
        "call_preflights": [],
        "original": None,
        "target_verified": False,
        "restored": None,
        "restored_verified": False,
        "emergency_restore_used": False,
        "qt_heartbeat_max_gap_ms": None,
        "secret_detected": False,
        "failure_type": None,
        "failure_reason": None,
    }
    window = None
    handler = None
    timer = None
    credential = None
    ticks = []
    original_messages = {
        name: getattr(QMessageBox, name)
        for name in ("information", "warning", "critical", "question")
    }
    try:
        for name in original_messages:
            setattr(
                QMessageBox,
                name,
                lambda *_args, **_kwargs: QMessageBox.Yes,
            )
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(
            sink
        ):
            window = VCSDiagnosticApp()
            credentials = window.device_credentials["Polycom RPG 310"]
            if not 0 <= args.credential_index < len(credentials):
                raise RuntimeError("Credential index is out of range")
            credential = credentials[args.credential_index]
            window.device_credentials["Polycom RPG 310"] = [credential]
            window.device_combo.setCurrentText("Polycom RPG 310")
            window.ip_entry.setText("link.ru")

            handler = PolycomRPG310Handler(
                "link.ru",
                username=credential["username"],
                password=credential["password"],
            )
            handler._connect_ssh()
            result["ssh_connected"] = True

            screen = window.screens["codec"]
            screen.schedule_volume_refresh = lambda *_args: None
            screen.schedule_presentation_refresh = lambda *_args: None
            screen.volume_session_handler = handler
            screen.volume_session_key = (
                "Polycom RPG 310",
                "link.ru",
                credential["username"],
                credential["password"],
                ((443, None),),
            )

            timer = QTimer()
            timer.setInterval(25)
            timer.timeout.connect(lambda: ticks.append(time.monotonic()))
            timer.start()
            app.processEvents()
            time.sleep(0.04)
            app.processEvents()

            def no_active_call():
                response = handler.send_command(
                    "callinfo all",
                    wait_time=1.0,
                )
                safe = "not in a call" in response.lower()
                result["call_preflights"].append(safe)
                if not safe:
                    raise RuntimeError(
                        "State-changing command aborted: call state is active "
                        "or unknown"
                    )

            if args.operation == "microphone-mute-cycle":
                original = handler.get_microphone_mute()
                if original not in {"Muted", "Unmuted"}:
                    raise RuntimeError("Microphone state is unavailable")
                result["original"] = original
                screen.update_data(
                    {
                        "Статус звонка": "Нет звонка",
                        "Статус микрофона": "Подключён",
                        "Mute микрофона": original,
                        "mic_mute": (
                            "on" if original == "Muted" else "off"
                        ),
                    }
                )
                button = screen.mute_buttons[
                    screen._microphone_param_name()
                ]
                try:
                    no_active_call()
                    button.click()
                    toggled = handler.get_microphone_mute()
                    result["target_verified"] = toggled != original
                finally:
                    current = handler.get_microphone_mute()
                    if current != original:
                        no_active_call()
                        button.click()
                    restored = handler.get_microphone_mute()
                    if restored != original:
                        result["emergency_restore_used"] = True
                        handler.set_microphone_mute(original == "Muted")
                        restored = handler.get_microphone_mute()
                    result["restored"] = restored
                    result["restored_verified"] = restored == original

            elif args.operation == "presentation-cycle":
                original = handler.get_presentation_status()
                if original not in {"Start", "Stop"}:
                    raise RuntimeError("Presentation state is unavailable")
                result["original"] = original
                screen.update_data(
                    {
                        "Статус звонка": "Нет звонка",
                        "Режим презентации": original,
                    }
                )
                buttons = screen.presentation_buttons[
                    "Статус презентации"
                ]
                try:
                    no_active_call()
                    screen.set_presentation_buttons_enabled(
                        "Статус презентации",
                        True,
                    )
                    buttons["on"].click()
                    started = handler.get_presentation_status()
                    result["target_verified"] = started == "Start"
                finally:
                    no_active_call()
                    screen.set_presentation_buttons_enabled(
                        "Статус презентации",
                        True,
                    )
                    buttons["off"].click()
                    restored = handler.get_presentation_status()
                    if restored != "Stop":
                        result["emergency_restore_used"] = True
                        handler.set_presentation("Stop")
                        restored = handler.get_presentation_status()
                    result["restored"] = restored
                    result["restored_verified"] = restored == "Stop"

            app.processEvents()
            gaps = [
                (current - previous) * 1000
                for previous, current in zip(ticks, ticks[1:])
            ]
            if gaps:
                result["qt_heartbeat_max_gap_ms"] = round(max(gaps), 1)
    except Exception as error:
        reason = str(error)
        if credential:
            for key in ("username", "password"):
                secret = credential.get(key)
                if secret:
                    reason = reason.replace(str(secret), "<redacted>")
        result["failure_type"] = type(error).__name__
        result["failure_reason"] = reason
    finally:
        if timer is not None:
            timer.stop()
        if handler is not None:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(
                sink
            ):
                handler._disconnect_ssh()
        if window is not None:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(
                sink
            ):
                window.close()
                app.processEvents()
        for name, method in original_messages.items():
            setattr(QMessageBox, name, method)
        console = sink.getvalue()
        if credential:
            result["secret_detected"] = any(
                value
                and len(str(value)) >= 4
                and str(value) in console
                for value in (
                    credential.get("username"),
                    credential.get("password"),
                )
            )

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if (
        result["ssh_connected"]
        and all(result["call_preflights"])
        and result["target_verified"]
        and result["restored_verified"]
        and not result["secret_detected"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
