"""Shared semantic states for device screens and application operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union


class UIState(str, Enum):
    IDLE = "idle"
    LOADING = "loading"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    AUTH_ERROR = "authentication_error"
    REQUEST_ERROR = "request_error"
    UNAVAILABLE = "unavailable"
    SLEEPING = "sleeping"
    COMMAND = "command_in_progress"
    DISABLED = "disabled"


@dataclass(frozen=True)
class UIStateSpec:
    indicator: str
    value_state: str
    default_text: str


STATE_SPECS = {
    UIState.IDLE: UIStateSpec("inactive", "inactive", "Данные ещё не запрашивались"),
    UIState.LOADING: UIStateSpec("loading", "loading", "Загрузка данных…"),
    UIState.CONNECTED: UIStateSpec("success", "success", "Соединение установлено"),
    UIState.DISCONNECTED: UIStateSpec("danger", "error", "Нет соединения"),
    UIState.AUTH_ERROR: UIStateSpec("danger", "error", "Ошибка авторизации"),
    UIState.REQUEST_ERROR: UIStateSpec("danger", "error", "Ошибка запроса"),
    UIState.UNAVAILABLE: UIStateSpec("warning", "inactive", "Значение недоступно"),
    UIState.SLEEPING: UIStateSpec("warning", "inactive", "Устройство в спящем режиме"),
    UIState.COMMAND: UIStateSpec("loading", "loading", "Выполнение команды…"),
    UIState.DISABLED: UIStateSpec("inactive", "disabled", "Элемент недоступен"),
}


def coerce_ui_state(state: Union[UIState, str]) -> UIState:
    if isinstance(state, UIState):
        return state
    return UIState(str(state))


def state_spec(state: Union[UIState, str]) -> UIStateSpec:
    return STATE_SPECS[coerce_ui_state(state)]
