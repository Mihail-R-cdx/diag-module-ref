"""Run one sanitized, read-only GUI refresh against approved hardware.

The script deliberately obtains credentials from ``VCSDiagnosticApp`` so they
are never duplicated in this file or printed to stdout. Device response values
and terminal text are suppressed; only aggregate QA facts are emitted.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import time
from pathlib import Path

from PyQt5.QtCore import QThreadPool, QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui.main_window import VCSDiagnosticApp


APPROVED_TARGETS = {
    "CloudLink Bar 310": "link.ru",
    "Huawei TE20": "link.ru",
    "Huawei TE40": "link.ru",
    "Extron IN1804": "link.ru",
    "Polycom RPG 310": "link.ru",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("device", choices=APPROVED_TARGETS)
    parser.add_argument("--timeout", type=float, default=55.0)
    parser.add_argument("--call-log", action="store_true")
    parser.add_argument("--te20-poll", action="store_true")
    parser.add_argument("--extron-keepalive", action="store_true")
    parser.add_argument("--switch-during-request", action="store_true")
    parser.add_argument("--speaker-volume-cycle", action="store_true")
    parser.add_argument("--wake-if-sleeping", action="store_true")
    parser.add_argument("--speaker-mute-cycle", action="store_true")
    parser.add_argument("--presentation-cycle", action="store_true")
    parser.add_argument("--routing-cycle", action="store_true")
    parser.add_argument("--microphone-mute-cycle", action="store_true")
    parser.add_argument("--credential-index", type=int)
    parser.add_argument("--duplicate-refresh", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication.instance() or QApplication([])
    sink = io.StringIO()
    result: dict[str, object] = {
        "device": args.device,
        "address": APPROVED_TARGETS[args.device].rsplit(".", 1)[0] + ".x",
        "completed": False,
        "connected": False,
        "timed_out": False,
        "credential_attempts": 0,
        "result_payloads": 0,
        "meaningful_fields": 0,
        "errors": 0,
        "auth_errors": 0,
        "error_types": [],
        "qt_heartbeat_ticks": 0,
        "qt_heartbeat_max_gap_ms": None,
        "terminal_secret_detected": False,
        "terminal_username_detected": False,
        "terminal_password_detected": False,
        "console_secret_detected": False,
        "console_username_detected": False,
        "console_password_detected": False,
        "field_names": [],
        "state_summary": {},
        "call_log_ok": None,
        "call_log_records": None,
        "call_log_elapsed_s": None,
        "te20_poll_ok": None,
        "te20_poll_max_elapsed_s": None,
        "extron_persistent_connected": None,
        "extron_keepalive_ok": None,
        "extron_keepalive_max_elapsed_s": None,
        "extron_cleanup_ok": None,
        "switched_during_request": False,
        "late_update_applied": None,
        "refresh_enabled_after_stale": None,
        "volume_preflight_safe": None,
        "volume_original": None,
        "volume_target": None,
        "volume_changed_verified": None,
        "volume_restored_verified": None,
        "volume_change_elapsed_s": None,
        "volume_restore_elapsed_s": None,
        "sleep_before": None,
        "wake_command_sent": False,
        "sleep_after": None,
        "wake_verified": None,
        "mute_original": None,
        "mute_applied_verified": None,
        "mute_restored_verified": None,
        "microphone_control_available": None,
        "microphone_original": None,
        "microphone_toggled_verified": None,
        "microphone_restored_verified": None,
        "duplicate_refresh_blocked": None,
        "presentation_before": None,
        "presentation_initial_stop_verified": None,
        "presentation_started_verified": None,
        "presentation_after": None,
        "presentation_restored_verified": None,
        "route_before": None,
        "route_target_verified": None,
        "route_after": None,
        "route_restored_verified": None,
        "failure_type": None,
        "failure_reason": None,
        "dialogs": [],
        "final_ui_state": None,
        "refresh_enabled_final": None,
    }

    original_message_methods = {
        name: getattr(QMessageBox, name)
        for name in ("information", "warning", "critical", "question")
    }

    def message_stub(kind: str):
        def show(*_args, **_kwargs):
            result["dialogs"].append(kind)
            return (
                QMessageBox.Yes
                if kind == "question"
                else QMessageBox.Ok
            )

        return show

    for method_name in original_message_methods:
        setattr(QMessageBox, method_name, message_stub(method_name))

    window = None
    timer = None
    credential_values = {"username": set(), "password": set()}
    heartbeat_times: list[float] = []
    started = time.monotonic()
    try:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            window = VCSDiagnosticApp()
            credentials = window.device_credentials[args.device]
            if not isinstance(credentials, list):
                credentials = [credentials]
            credential_values = {
                key: {
                    str(credential.get(key))
                    for credential in credentials
                    if credential.get(key)
                    and len(str(credential.get(key))) >= 4
                }
                for key in ("username", "password")
            }

            original_result = window.on_device_data_received
            original_error = window.on_device_error

            def on_result(data, worker=None, request_id=None):
                result["result_payloads"] += 1
                state_keys = {
                    "SIP регистрация",
                    "Статус звонка",
                    "Состояние конференции",
                    "Режим презентации",
                    "Режим сна",
                    "Mute микрофона",
                    "Статус микрофона",
                    "Статус динамика",
                    "call_status",
                    "presentation",
                    "mic_mute",
                    "current_connection",
                }
                result["state_summary"] = {
                    str(key): value
                    for key, value in dict(data).items()
                    if key in state_keys
                    and isinstance(value, (str, int, float, bool, type(None)))
                }
                current_connection = dict(data).get("current_connection")
                if isinstance(current_connection, dict):
                    result["state_summary"]["current_connection"] = {
                        str(key): value
                        for key, value in current_connection.items()
                        if isinstance(
                            value, (str, int, float, bool, type(None))
                        )
                    }
                result["field_names"] = sorted(
                    str(key)
                    for key in dict(data)
                    if key not in {"ip_address", "connection_profile"}
                )
                result["meaningful_fields"] = max(
                    int(result["meaningful_fields"]),
                    sum(
                        key != "ip_address"
                        and value not in (None, "", {}, [], "N/A", "Не доступно")
                        for key, value in dict(data).items()
                    ),
                )
                return original_result(data, worker, request_id)

            def on_error(error_info, worker=None, request_id=None):
                result["errors"] += 1
                error_type, error, _traceback_text = error_info
                result["error_types"].append(str(error_type))
                if window.is_authentication_error(error_type, str(error)):
                    result["auth_errors"] += 1
                return original_error(error_info, worker, request_id)

            window.on_device_data_received = on_result
            window.on_device_error = on_error

            def terminal_wrapper(original):
                def accept(message):
                    text = str(message)
                    username_found = any(
                        value in text
                        for value in credential_values["username"]
                    )
                    password_found = any(
                        value in text
                        for value in credential_values["password"]
                    )
                    if username_found or password_found:
                        result["terminal_secret_detected"] = True
                    if username_found:
                        result["terminal_username_detected"] = True
                    if password_found:
                        result["terminal_password_detected"] = True
                    return original(message)

                return accept

            for slot_name in (
                "on_terminal_log",
                "on_te20_terminal_log",
                "on_codec_poll_terminal_log",
            ):
                setattr(
                    window,
                    slot_name,
                    terminal_wrapper(getattr(window, slot_name)),
                )

            timer = QTimer()
            timer.setInterval(25)
            timer.timeout.connect(lambda: heartbeat_times.append(time.monotonic()))
            timer.start()

            def process_events_for(seconds):
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(0.01)

            window.device_combo.setCurrentText(args.device)
            window.ip_entry.setText(APPROVED_TARGETS[args.device])
            if args.credential_index is not None:
                credentials = window.device_credentials[args.device]
                if not 0 <= args.credential_index < len(credentials):
                    raise RuntimeError("Credential index is out of range")
                selected_credential = credentials[args.credential_index]
                window.device_credentials[args.device] = [
                    selected_credential
                ]
                window.set_current_credential_index(
                    args.device,
                    0,
                    APPROVED_TARGETS[args.device],
                )
            update_time_before = window.last_update_time
            if args.switch_during_request:
                def switch_device():
                    window.device_combo.setCurrentText("Huawei TE40")
                    window.ip_entry.setText(
                        APPROVED_TARGETS["Huawei TE40"]
                    )
                    result["switched_during_request"] = True

                QTimer.singleShot(50, switch_device)
            window.refresh_data()
            if args.duplicate_refresh:
                payloads_before_duplicate = result["result_payloads"]
                window.refresh_btn.click()
                result["duplicate_refresh_blocked"] = (
                    not window.refresh_btn.isEnabled()
                    and result["result_payloads"] == payloads_before_duplicate
                )

            while time.monotonic() - started < args.timeout:
                app.processEvents()
                normal_completion = (
                    time.monotonic() - started > 0.2
                    and window.refresh_btn.isEnabled()
                    and QThreadPool.globalInstance().activeThreadCount() == 0
                    and (result["result_payloads"] or result["errors"])
                )
                stale_completion = (
                    args.switch_during_request
                    and result["switched_during_request"]
                    and QThreadPool.globalInstance().activeThreadCount() == 0
                    and (result["result_payloads"] or result["errors"])
                )
                if normal_completion or stale_completion:
                    result["completed"] = True
                    break
                time.sleep(0.01)
            else:
                result["timed_out"] = True

            app.processEvents()
            result["connected"] = (
                getattr(window.ui_state, "value", str(window.ui_state))
                == "connected"
            )
            result["final_ui_state"] = getattr(
                window.ui_state,
                "value",
                str(window.ui_state),
            )
            result["refresh_enabled_final"] = (
                window.refresh_btn.isEnabled()
            )
            if args.switch_during_request:
                result["late_update_applied"] = (
                    window.last_update_time is not update_time_before
                )
                result["refresh_enabled_after_stale"] = (
                    window.refresh_btn.isEnabled()
                )
            result["credential_attempts"] = (
                window.get_current_credential_index(
                    args.device, APPROVED_TARGETS[args.device]
                )
                + 1
            )
            result["qt_heartbeat_ticks"] = len(heartbeat_times)
            gaps = [
                (current - previous) * 1000
                for previous, current in zip(
                    heartbeat_times, heartbeat_times[1:]
                )
            ]
            if gaps:
                result["qt_heartbeat_max_gap_ms"] = round(max(gaps), 1)
            result["elapsed_s"] = round(time.monotonic() - started, 2)

            codec_screen = window.screens.get("codec")
            if args.call_log and codec_screen is not None:
                critical_before = result["dialogs"].count("critical")
                call_log_started = time.monotonic()
                codec_screen.open_call_log_window()
                call_log_deadline = time.monotonic() + 20
                while (
                    getattr(
                        codec_screen,
                        "_polycom_call_log_loading",
                        False,
                    )
                    and time.monotonic() < call_log_deadline
                ):
                    app.processEvents()
                    time.sleep(0.01)
                result["call_log_elapsed_s"] = round(
                    time.monotonic() - call_log_started, 2
                )
                app.processEvents()
                call_log_window = getattr(
                    codec_screen, "call_log_window", None
                )
                if call_log_window is not None:
                    result["call_log_records"] = (
                        call_log_window.table.rowCount()
                    )
                result["call_log_ok"] = (
                    result["dialogs"].count("critical") == critical_before
                )

            if (
                args.te20_poll
                and args.device == "Huawei TE20"
                and codec_screen is not None
            ):
                poll_times = []
                critical_before = result["dialogs"].count("critical")
                for _ in range(3):
                    poll_started = time.monotonic()
                    codec_screen.poll_te20_monitor_audio()
                    poll_times.append(time.monotonic() - poll_started)
                    app.processEvents()
                result["te20_poll_max_elapsed_s"] = round(
                    max(poll_times), 3
                )
                result["te20_poll_ok"] = (
                    result["dialogs"].count("critical") == critical_before
                )

            if args.extron_keepalive and args.device == "Extron IN1804":
                handler = window.matrix_persistent_handler
                result["extron_persistent_connected"] = bool(
                    handler is not None and handler.is_connected()
                )
                keepalive_times = []
                for _ in range(3):
                    keepalive_started = time.monotonic()
                    window.on_matrix_keepalive()
                    keepalive_times.append(
                        time.monotonic() - keepalive_started
                    )
                    app.processEvents()
                result["extron_keepalive_max_elapsed_s"] = round(
                    max(keepalive_times), 3
                )
                handler = window.matrix_persistent_handler
                result["extron_keepalive_ok"] = bool(
                    handler is not None and handler.is_connected()
                )

            if args.speaker_volume_cycle and codec_screen is not None:
                call_state_text = " ".join(
                    str(value).lower()
                    for key, value in result["state_summary"].items()
                    if key in {
                        "Статус звонка",
                        "Состояние конференции",
                        "call_status",
                    }
                )
                safe_markers = (
                    "нет звонка",
                    "не в звонке",
                    "ожидание",
                )
                result["volume_preflight_safe"] = bool(
                    call_state_text
                    and any(
                        marker in call_state_text
                        for marker in safe_markers
                    )
                )
                if not result["volume_preflight_safe"]:
                    raise RuntimeError(
                        "Volume test aborted: call state is active or unknown"
                    )

                original_volume = codec_screen.get_speaker_volume()
                result["volume_original"] = original_volume
                _minimum, maximum = codec_screen._get_volume_range(
                    "Громкость динамиков"
                )
                if (
                    not isinstance(original_volume, int)
                    or original_volume >= maximum
                ):
                    raise RuntimeError(
                        "Volume test aborted: original value is unavailable "
                        "or already at maximum"
                    )

                step = 2 if args.device == "Polycom RPG 310" else 1
                target_volume = original_volume + step
                result["volume_target"] = target_volume
                up_button = codec_screen.volume_buttons[
                    "Громкость динамиков"
                ]["up"]
                down_button = codec_screen.volume_buttons[
                    "Громкость динамиков"
                ]["down"]

                change_error = None
                try:
                    change_started = time.monotonic()
                    up_button.click()
                    result["volume_change_elapsed_s"] = round(
                        time.monotonic() - change_started, 3
                    )
                    app.processEvents()
                    changed_volume = codec_screen.get_speaker_volume()
                    result["volume_changed_verified"] = (
                        changed_volume == target_volume
                    )
                except Exception as error:
                    change_error = error
                finally:
                    restore_started = time.monotonic()
                    try:
                        current_volume = codec_screen.get_speaker_volume()
                    except Exception:
                        current_volume = None
                    if current_volume == target_volume:
                        down_button.click()
                    elif current_volume != original_volume:
                        codec_screen.set_speaker_volume(original_volume)
                    result["volume_restore_elapsed_s"] = round(
                        time.monotonic() - restore_started, 3
                    )
                    app.processEvents()
                    restored_volume = codec_screen.get_speaker_volume()
                    result["volume_restored_verified"] = (
                        restored_volume == original_volume
                    )
                    if not result["volume_restored_verified"]:
                        codec_screen.set_speaker_volume(original_volume)
                        app.processEvents()
                        restored_volume = codec_screen.get_speaker_volume()
                        result["volume_restored_verified"] = (
                            restored_volume == original_volume
                        )
                if not result["volume_restored_verified"]:
                    raise RuntimeError(
                        "CRITICAL: original speaker volume was not restored"
                    )
                if change_error is not None:
                    raise change_error

            if args.wake_if_sleeping:
                if (
                    args.device != "Huawei TE20"
                    or codec_screen is None
                ):
                    raise RuntimeError(
                        "The current GUI exposes a wake button only for TE-20"
                    )
                credentials, _index, _all_credentials = (
                    codec_screen._get_current_device_credentials(
                        args.device, APPROVED_TARGETS[args.device]
                    )
                )
                handler = codec_screen._get_or_create_volume_handler(
                    ip_address=APPROVED_TARGETS[args.device],
                    device_name=args.device,
                    username=credentials["username"],
                    password=credentials["password"],
                    command_logger=(
                        codec_screen
                        ._append_te20_monitor_audio_terminal_log
                    ),
                )
                sleep_before = handler.get_sleep_mode()
                result["sleep_before"] = sleep_before
                if sleep_before == "On":
                    codec_screen._set_te20_monitor_audio_sleep_state(True)
                    wake_button = codec_screen.wake_buttons[
                        "Звук в помещении (микрофон)"
                    ]
                    wake_button.click()
                    result["wake_command_sent"] = True

                    deadline = time.monotonic() + 15
                    sleep_after = sleep_before
                    while time.monotonic() < deadline:
                        app.processEvents()
                        sleep_after = handler.get_sleep_mode()
                        if sleep_after != "On":
                            break
                        time.sleep(1)
                    result["sleep_after"] = sleep_after
                    result["wake_verified"] = sleep_after != "On"
                else:
                    result["sleep_after"] = sleep_before
                    result["wake_verified"] = True

            if args.speaker_mute_cycle and codec_screen is not None:
                call_state_text = " ".join(
                    str(value).lower()
                    for key, value in result["state_summary"].items()
                    if key in {
                        "Статус звонка",
                        "Состояние конференции",
                        "call_status",
                    }
                )
                if not any(
                    marker in call_state_text
                    for marker in (
                        "нет звонка",
                        "не в звонке",
                        "ожидание",
                    )
                ):
                    raise RuntimeError(
                        "Mute test aborted: call state is active or unknown"
                    )

                original_volume = codec_screen.get_speaker_volume()
                if not isinstance(original_volume, int):
                    raise RuntimeError(
                        "Mute test aborted: speaker volume is unavailable"
                    )
                result["mute_original"] = original_volume
                mute_button = codec_screen.mute_buttons[
                    "Громкость динамиков"
                ]
                original_muted = original_volume == 0
                try:
                    mute_button.click()
                    app.processEvents()
                    toggled_volume = codec_screen.get_speaker_volume()
                    result["mute_applied_verified"] = (
                        toggled_volume != 0
                        if original_muted
                        else toggled_volume == 0
                    )
                finally:
                    try:
                        current_volume = codec_screen.get_speaker_volume()
                    except Exception:
                        current_volume = None
                    if current_volume == 0 and original_volume != 0:
                        mute_button.click()
                    elif original_muted and current_volume != 0:
                        mute_button.click()
                    elif current_volume != original_volume:
                        codec_screen.set_speaker_volume(original_volume)
                    app.processEvents()
                    restored_volume = codec_screen.get_speaker_volume()
                    result["mute_restored_verified"] = (
                        restored_volume == original_volume
                    )
                    if not result["mute_restored_verified"]:
                        codec_screen.set_speaker_volume(original_volume)
                        app.processEvents()
                        restored_volume = codec_screen.get_speaker_volume()
                        result["mute_restored_verified"] = (
                            restored_volume == original_volume
                        )
                if not result["mute_restored_verified"]:
                    raise RuntimeError(
                        "CRITICAL: original speaker state was not restored"
                    )

            if args.microphone_mute_cycle and codec_screen is not None:
                call_state_text = " ".join(
                    str(value).lower()
                    for key, value in result["state_summary"].items()
                    if key in {
                        "Статус звонка",
                        "Состояние конференции",
                        "call_status",
                    }
                )
                if not any(
                    marker in call_state_text
                    for marker in (
                        "нет звонка",
                        "не в звонке",
                        "ожидание",
                    )
                ):
                    raise RuntimeError(
                        "Microphone test aborted: call state is active or unknown"
                    )

                microphone_param = codec_screen._microphone_param_name()
                microphone_button = codec_screen.mute_buttons.get(
                    microphone_param
                )
                microphone_status = codec_screen.get_microphone_volume()
                normalized_original = str(microphone_status).strip().lower()
                control_available = bool(
                    microphone_button is not None
                    and not microphone_button.isHidden()
                    and microphone_button.isEnabled()
                    and normalized_original in {"muted", "unmuted"}
                )
                result["microphone_control_available"] = control_available
                result["microphone_original"] = microphone_status
                if control_available:
                    original_muted = normalized_original == "muted"
                    try:
                        microphone_button.click()
                        app.processEvents()
                        toggled = codec_screen.get_microphone_volume()
                        result["microphone_toggled_verified"] = (
                            str(toggled).strip().lower()
                            == ("unmuted" if original_muted else "muted")
                        )
                    finally:
                        current = codec_screen.get_microphone_volume()
                        if (
                            str(current).strip().lower()
                            != normalized_original
                        ):
                            microphone_button.click()
                            app.processEvents()
                        restored = codec_screen.get_microphone_volume()
                        result["microphone_restored_verified"] = (
                            str(restored).strip().lower()
                            == normalized_original
                        )
                    if not result["microphone_restored_verified"]:
                        raise RuntimeError(
                            "CRITICAL: original microphone state was not restored"
                        )

            if args.presentation_cycle and codec_screen is not None:
                credentials, _index, _all_credentials = (
                    codec_screen._get_current_device_credentials(
                        args.device, APPROVED_TARGETS[args.device]
                    )
                )
                handler = codec_screen._get_or_create_volume_handler(
                    ip_address=APPROVED_TARGETS[args.device],
                    device_name=args.device,
                    username=credentials["username"],
                    password=credentials["password"],
                    command_logger=(
                        codec_screen._append_presentation_terminal_log
                    ),
                )
                presentation_before = handler.get_presentation_status()
                result["presentation_before"] = presentation_before
                buttons = codec_screen.presentation_buttons[
                    "Статус презентации"
                ]
                if str(presentation_before).strip().lower() in {
                    "start",
                    "started",
                }:
                    buttons["off"].click()
                    process_events_for(1.6)
                    initial_stop = handler.get_presentation_status()
                    result["presentation_initial_stop_verified"] = (
                        str(initial_stop).strip().lower()
                        in {"stop", "stopped"}
                    )
                    if not result["presentation_initial_stop_verified"]:
                        raise RuntimeError(
                            "CRITICAL: initial presentation did not stop"
                        )
                elif str(presentation_before).strip().lower() not in {
                    "stop",
                    "stopped",
                }:
                    raise RuntimeError(
                        "Presentation test aborted: initial state is unknown"
                    )
                try:
                    buttons["on"].click()
                    app.processEvents()
                    started_state = handler.get_presentation_status()
                    result["presentation_started_verified"] = (
                        str(started_state).strip().lower()
                        in {"start", "started"}
                    )
                    process_events_for(1.6)
                finally:
                    try:
                        current_state = handler.get_presentation_status()
                    except Exception:
                        current_state = None
                    if str(current_state).strip().lower() in {
                        "start",
                        "started",
                    }:
                        buttons["off"].click()
                    elif str(current_state).strip().lower() not in {
                        "stop",
                        "stopped",
                    }:
                        codec_screen.set_presentation_state("off")
                    app.processEvents()
                    presentation_after = handler.get_presentation_status()
                    result["presentation_after"] = presentation_after
                    result["presentation_restored_verified"] = (
                        str(presentation_after).strip().lower()
                        in {"stop", "stopped"}
                    )
                    if not result["presentation_restored_verified"]:
                        codec_screen.set_presentation_state("off")
                        app.processEvents()
                        presentation_after = (
                            handler.get_presentation_status()
                        )
                        result["presentation_after"] = presentation_after
                        result["presentation_restored_verified"] = (
                            str(presentation_after).strip().lower()
                            in {"stop", "stopped"}
                        )
                if not result["presentation_restored_verified"]:
                    raise RuntimeError(
                        "CRITICAL: presentation was not stopped"
                    )

            if args.routing_cycle:
                if args.device != "Extron IN1804":
                    raise RuntimeError(
                        "Routing test is only valid for Extron IN1804"
                    )
                matrix_screen = window.screens["matrix"]
                handler = window.matrix_persistent_handler
                connections = handler.get_connections()
                original_route = connections[0] if connections else None
                result["route_before"] = original_route
                if original_route != 2:
                    raise RuntimeError(
                        "Routing test aborted: expected initial input 2"
                    )

                try:
                    matrix_screen.matrix_table.cellClicked.emit(0, 3)
                    process_events_for(0.8)
                    connections = handler.get_connections()
                    target_route = connections[0] if connections else None
                    result["route_target_verified"] = target_route == 1
                finally:
                    try:
                        connections = handler.get_connections()
                        current_route = (
                            connections[0] if connections else None
                        )
                    except Exception:
                        current_route = None
                    if current_route != original_route:
                        matrix_screen.matrix_table.cellClicked.emit(
                            original_route - 1, 3
                        )
                        process_events_for(0.8)
                    connections = handler.get_connections()
                    final_route = connections[0] if connections else None
                    if final_route != original_route:
                        handler.set_connection(1, original_route)
                        connections = handler.get_connections()
                        final_route = (
                            connections[0] if connections else None
                        )
                    result["route_after"] = final_route
                    result["route_restored_verified"] = (
                        final_route == original_route
                    )
                if not result["route_restored_verified"]:
                    raise RuntimeError(
                        "CRITICAL: original matrix route was not restored"
                    )

            result["qt_heartbeat_ticks"] = len(heartbeat_times)
            gaps = [
                (current - previous) * 1000
                for previous, current in zip(
                    heartbeat_times, heartbeat_times[1:]
                )
            ]
            if gaps:
                result["qt_heartbeat_max_gap_ms"] = round(max(gaps), 1)
            result["elapsed_s"] = round(time.monotonic() - started, 2)

            if timer is not None:
                timer.stop()
            QThreadPool.globalInstance().waitForDone(5000)
            window.close()
            app.processEvents()
            result["extron_cleanup_ok"] = (
                window.matrix_persistent_handler is None
                and not window.matrix_keepalive_timer.isActive()
            )

            console_text = sink.getvalue()
            console_username_found = any(
                value in console_text
                for value in credential_values["username"]
            )
            console_password_found = any(
                value in console_text
                for value in credential_values["password"]
            )
            result["console_username_detected"] = console_username_found
            result["console_password_detected"] = console_password_found
            result["console_secret_detected"] = (
                console_username_found or console_password_found
            )
    except Exception as error:
        reason = str(error)
        for values in credential_values.values():
            for value in values:
                reason = reason.replace(value, "<redacted>")
        result["failure_type"] = type(error).__name__
        result["failure_reason"] = reason
    finally:
        for method_name, method in original_message_methods.items():
            setattr(QMessageBox, method_name, method)
        if window is not None:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(
                sink
            ):
                if timer is not None:
                    timer.stop()
                QThreadPool.globalInstance().waitForDone(5000)
                window.close()
                app.processEvents()
            window.deleteLater()
        app.processEvents()

    sys.__stdout__.write(
        json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n"
    )
    sys.__stdout__.flush()
    if args.switch_during_request:
        return 0 if (
            result["completed"]
            and not result["late_update_applied"]
            and result["refresh_enabled_after_stale"]
        ) else 1
    if args.speaker_volume_cycle:
        return 0 if (
            result["completed"]
            and result["connected"]
            and result["volume_changed_verified"]
            and result["volume_restored_verified"]
        ) else 1
    if args.wake_if_sleeping:
        return 0 if (
            result["completed"]
            and result["connected"]
            and result["wake_verified"]
        ) else 1
    if args.speaker_mute_cycle:
        return 0 if (
            result["completed"]
            and result["connected"]
            and result["mute_applied_verified"]
            and result["mute_restored_verified"]
        ) else 1
    if args.presentation_cycle:
        return 0 if (
            result["completed"]
            and result["connected"]
            and result["presentation_started_verified"]
            and result["presentation_restored_verified"]
        ) else 1
    if args.routing_cycle:
        return 0 if (
            result["completed"]
            and result["connected"]
            and result["route_target_verified"]
            and result["route_restored_verified"]
        ) else 1
    if args.microphone_mute_cycle:
        return 0 if (
            result["completed"]
            and result["connected"]
            and (
                not result["microphone_control_available"]
                or (
                    result["microphone_toggled_verified"]
                    and result["microphone_restored_verified"]
                )
            )
        ) else 1
    return 0 if result["completed"] and result["connected"] else 1


if __name__ == "__main__":
    sys.exit(main())
