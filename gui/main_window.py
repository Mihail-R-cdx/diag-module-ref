from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox, QStackedWidget, QMessageBox, QInputDialog, QDialog, QDialogButtonBox, QFormLayout, QPlainTextEdit, QSizePolicy

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThreadPool, QDateTime, QEvent, QObject, QRunnable
from PyQt5.QtGui import QColor
from dataclasses import dataclass
import datetime
import os
import random
import platform
import subprocess
import traceback
from types import MappingProxyType

from .screens import CodecScreen, MatrixScreen, PDUScreen, AudioDSPScreen
from .components import EmptyState, StatusIndicator
from .dmp_polling_controller import DMP_DEVICE_NAME, DMPPollingController
from .diagnostic_dispatch import (
    ActionBinding,
    DiagnosticActionPurpose,
    dispatch_entries,
    dispatch_entry_for_model,
    dispatch_model_names,
    resolve_exact_model_for_ip,
    validate_dispatch_registry,
)
from .device_model_fallback_dialog import DeviceModelFallbackDialog
from .matrix_controller import MATRIX_DEVICE_NAME, MatrixController
from .pdu_controller import PDUController
from .pdu_room_codec_enrichment import PDURoomCodecEnrichmentController
from .equipment_pages import (
    EQUIPMENT_PAGE_REGISTRY,
    PDU_DEVICE_NAMES,
    attach_shared_room_block,
    registrations_by_screen,
    screen_key_for_model,
)
from .theme import SPACING, apply_theme, legacy_colors
from .ui_states import UIState, coerce_ui_state, state_spec
from core.equipment_inventory import (
    EquipmentInventoryLoadError,
    load_equipment_inventory,
    normalize_ip_address,
)
from core.room_context import RoomContextResolver, RoomResolutionStatus
from core.switch_connection_context import SwitchConnectionResolver
from core.worker import (
    HuaweiTE40Worker,
    HuaweiBar310Worker,
    HuaweiTE20Worker,
    PolycomRPG310Worker,
    CodecSipFixWorker,
    BiampTesiraForteCIWorker,
)
from core.pdu import (
    BULK_COMMAND_OFF,
    BULK_COMMAND_ON,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_REBOOT,
    REFRESH,
    PDUOperationDescriptor,
    build_pdu_bulk_outlet_sequence,
    ensure_pdu_operation_supported,
    normalize_pdu_credential_candidates,
)
from core.exceptions import (
    AuthenticationError,
    CodecFailureCategory,
    ConnectionError,
)
from core.credentials import (
    CredentialAttemptPlan,
    JsonCredentialProvider,
    resolve_request_credential_candidates,
    resolve_request_credentials,
)
from core.exceptions import CredentialConfigurationError
from core.exceptions import (
    CredentialFileMissingError,
    CredentialProfileNotFoundError,
)
from core.redaction import redact_exception, redact_text
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter


class ReachabilitySignals(QObject):
    finished = pyqtSignal(dict)


class ReachabilityCheckWorker(QRunnable):
    def __init__(self, *, operation_id, ip_address, ping_callable):
        super().__init__()
        self.operation_id = operation_id
        self.ip_address = ip_address
        self.ping_callable = ping_callable
        self.signals = ReachabilitySignals()

    def run(self):
        reachable = False
        try:
            reachable = bool(self.ping_callable(self.ip_address))
        except Exception:
            reachable = False
        self.signals.finished.emit(
            {
                "operation_id": self.operation_id,
                "ip_address": self.ip_address,
                "reachable": reachable,
            }
        )


@dataclass(frozen=True)
class DiagnosticCredentialSnapshot:
    diagnostic_model: str
    ip_address: str
    candidates: tuple
    starting_successful_index: int
    diagnostic_generation: int
    reachability_operation_id: int
    inventory_context_identity: str

    @property
    def identity(self):
        return (
            self.diagnostic_model,
            self.ip_address,
            self.diagnostic_generation,
            self.reachability_operation_id,
            self.inventory_context_identity,
        )


class RightAlignHeaderDelegate(QStyledItemDelegate):
    """Делегат для выравнивания заголовков по правому краю"""
    def __init__(self, parent=None, header_list=None):
        super().__init__(parent)
        self.header_list = header_list or []
    
    def paint(self, painter, option, index):
        text = index.data()
        
        # Проверяем, является ли элемент заголовком
        if text in self.header_list:
            # Для заголовков рисуем с выравниванием по правому краю
            painter.save()
            
            # Рисуем фон
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            
            # Рисуем текст с выравниванием по правому краю
            text_rect = QRect(option.rect)
            text_rect.setRight(option.rect.right() - 10)  # Отступ справа 10px
            painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, text)
            
            painter.restore()
        else:
            # Для обычных элементов используем стандартное рисование
            # Вызываем родительский метод
            QStyledItemDelegate.paint(self, painter, option, index)


class MatrixTerminalDialog(QDialog):
    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.setWindowTitle("Терминал Extron IN1804")
        self.resize(760, 420)

        layout = QVBoxLayout(self)
        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setProperty("uiRole", "terminal")
        layout.addWidget(self.output)

    def reset_session(self, title: str):
        self.setWindowTitle(title)
        self.output.clear()

    def append_line(self, text: str):
        self.output.appendPlainText(text)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())


class RequestCredentialStore(dict):
    """Compatibility bridge for explicit UI/test credentials and the provider."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def get(self, device_name, default=None):
        if device_name in self:
            return super().get(device_name)
        return self.owner.resolve_device_credential_candidates(device_name)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def setdefault(self, key, default=None):
        return super().setdefault(key, default)

class VCSDiagnosticApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Цветовая схема
        self.colors = legacy_colors()
        
        # Имитация данных
        self.codec_data = {
            "Codec1": self.generate_fake_data("Codec1"),
            "Codec2": self.generate_fake_data("Codec2"),
            "Codec3": self.generate_fake_data("Codec3"),
            "Codec4": self.generate_fake_data("Codec4")
        }
        
        # Application-owned exact diagnostic dispatch registry.
        self.dispatch_registry = dispatch_entries()
        self.device_to_screen = {
            entry.diagnostic_model: entry.screen_key for entry in self.dispatch_registry
        }
        
        self.matrix_params = {
            'num_inputs': 8,
            'num_outputs': 6,
            'input_names': [
                "Ноутбук 1", "Ноутбук 2", "Apple TV", "ВКС система",
                "Документ-камера", "Системный ПК", "Резерв 1", "Резерв 2"
            ],
            'output_names': ["ТВ зал 1", "ТВ зал 2", "ВКС кам", "ВКС през", "Выход 5", "Выход 6"]
        }
        
        self.huawei_settings = {
            'port': 443,
            'use_ssl': True,
            'verify_ssl': False
        }        
        
        # Список credentials для разных устройств
        self.credential_provider = JsonCredentialProvider()
        self.device_credentials = RequestCredentialStore(self)
        
        # Текущий индекс credentials для каждого устройства
        self.current_credential_index = {}
        for device in self.device_credentials:
            self.current_credential_index[device] = 0
        self.device_connection_profiles = {}
        self.equipment_inventory = None
        self.equipment_inventory_load_error = None
        try:
            self.replace_equipment_inventory_state(
                inventory=load_equipment_inventory(),
                load_error=None,
                reason="initial_inventory_load",
                supersede=False,
            )
        except EquipmentInventoryLoadError as error:
            self.replace_equipment_inventory_state(
                inventory=None,
                load_error=error,
                reason="initial_inventory_failure",
                supersede=False,
            )
        self.equipment_page_registry = EQUIPMENT_PAGE_REGISTRY
        self.room_context_resolver = RoomContextResolver()
        self.room_information_blocks = {}
        self._equipment_room_context_generation = 0
        self._equipment_room_context_binding = None
        self._equipment_room_credential_context_revision = 0
        self.switch_connection_resolver = SwitchConnectionResolver()
        self._equipment_switch_context_generation = 0
        self._equipment_switch_context_binding = None
        self.progress_dialog = None
        self.ui_state = UIState.IDLE
        self._request_serial = 0
        self._active_request = None
        self._diagnostic_action_generation = 0
        self._credential_action_generation = 0
        self._fallback_dialog_generation = 0
        self._credential_dialog_generation = 0
        self._active_diagnostic_model_context = None
        self._active_credential_configuration_context = None
        self._reachability_operation_serial = 0
        self._current_reachability_context = None
        self._current_reachability_worker = None
        self._reachability_presentation_operation_id = None
        self._diagnostic_credential_snapshots = {}
        self._current_action_dialog_bindings = {}
        self._credential_attempt_plans = {}
        self._matrix_credential_context_revision = 0
        self._pdu_room_codec_enrichment_enabled = True
        self.matrix_controller = MatrixController(
            context_provider=self._matrix_public_context,
            credential_candidates_provider=self._matrix_credential_candidates,
            credential_index_provider=self._matrix_credential_index,
            credential_advance_provider=self._matrix_advance_credential_attempt,
            credential_revision_provider=self._matrix_credential_revision,
            parent=self,
        )
        self.pdu_controller = PDUController(
            shell=self,
            screen_provider=lambda: getattr(self, "screens", {}).get("pdu"),
            accepted_refresh_callback=self._on_pdu_refresh_accepted_for_enrichment,
            superseded_callback=self._on_pdu_context_superseded_for_enrichment,
        )
        self.pdu_room_codec_enrichment_controller = PDURoomCodecEnrichmentController(
            inventory_provider=lambda: self.equipment_inventory,
            inventory_failure_provider=lambda: self.equipment_inventory_load_error,
            credential_candidates_provider=self._related_codec_credential_candidates,
            credential_index_provider=self._related_codec_credential_index,
            credential_revision_provider=self._related_codec_credential_revision,
            connection_profile_provider=self.get_device_connection_profile,
            success_persistence=self._persist_related_codec_success,
            presentation_callback=self._render_pdu_room_codec_enrichment,
            parent=self,
        )
        self.dmp_polling_controller = DMPPollingController(
            shell=self,
            screen_provider=lambda: getattr(self, "screens", {}).get("audio_dsp"),
        )
        
        # Инициализация экранов
        self.screens = {}
        self.current_screen = None
        
        # Таймер для обновления времени
        self.update_timer = QTimer(self)
        self.last_update_time = None
        self._last_logged_button_event = None
        self.button_log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "logs"))
        self.button_log_path = os.path.join(self.button_log_dir, "button_clicks.log")
        
        self.init_ui()
        self.update_timer.setInterval(30000)
        self.update_timer.timeout.connect(self.update_time_display)
        self.update_timer.start()

    def resolve_device_credentials(self, device_name, profile_name=None, explicit_credentials=None):
        """Resolve credentials once in the GUI composition layer."""
        credential = resolve_request_credentials(
            self.credential_provider,
            device_model=device_name,
            profile_name=profile_name,
            explicit_credentials=explicit_credentials,
        )
        return credential.as_handler_kwargs()

    def resolve_device_credential_candidates(
        self, device_name, profile_name=None, explicit_credentials=None
    ):
        """Resolve all candidates once before any worker or handler is created."""
        credentials = resolve_request_credential_candidates(
            self.credential_provider,
            device_model=device_name,
            profile_name=profile_name,
            explicit_credentials=explicit_credentials,
        )
        return [credential.as_handler_kwargs() for credential in credentials]

    @staticmethod
    def _is_pcs4i_credentialless_fallback(device_name, error):
        return device_name == "Extron IPL T PCS4i" and isinstance(
            error,
            (CredentialFileMissingError, CredentialProfileNotFoundError),
        )

    def _resolve_pdu_attempt_credentials(self, device_name, ip_address):
        try:
            candidates = normalize_pdu_credential_candidates(
                device_name,
                self.device_credentials.get(device_name),
            )
            if device_name == "Extron IPL T PCS4i" and not candidates:
                return [{}]
            return candidates
        except CredentialConfigurationError as error:
            if self._is_pcs4i_credentialless_fallback(device_name, error):
                return [{}]
            raise
    
    def init_ui(self, params=None):
        """Инициализация интерфейса"""
        self.setWindowTitle("Диагностический модуль ММК")
        self.setMinimumSize(800, 700)
        self.setGeometry(100, 0, 950, 1000)
        
        # Установка темной темы
        self.set_dark_theme()
        
        # Создаем центральный виджет
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        # Основной вертикальный layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(SPACING["md"])
        main_layout.setContentsMargins(
            SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["md"]
        )
        
        # 1. Панель выбора устройства и подключения
        top_panel = self.create_top_panel()
        main_layout.addWidget(top_panel)
        
        # 2. Создаем контейнер для экранов
        self.screen_container = QStackedWidget()
        self.screen_container.setObjectName("screenContainer")
        self.screen_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Создаем экраны
        self.init_screens()
        validate_dispatch_registry(
            registered_screens=set(self.screens),
            page_models_by_screen={
                registration.screen_key: registration.device_models
                for registration in self.equipment_page_registry
            },
        )
        
        # Добавляем экраны в контейнер
        for screen_name, screen in self.screens.items():
            self.screen_container.addWidget(screen)
        
        # 3. Создаем страницу-заглушку с надписью "Обновите данные"
        self.placeholder_widget = self.create_placeholder_widget()
        self.screen_container.addWidget(self.placeholder_widget)
        
        # Показываем заглушку
        self.screen_container.setCurrentWidget(self.placeholder_widget)
        
        main_layout.addWidget(self.screen_container, 1)
        
        # 4. Панель времени обновления
        update_time_panel = self.create_update_time_panel()
        main_layout.addWidget(update_time_panel)
        
        # Сохраняем текущий выбранный тип экрана
        self.current_screen_type = None

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
    
    def create_placeholder_widget(self):
        """Создание виджета-заглушки с надписью Обновите данные"""
        return EmptyState(
            "Обновите данные",
            "Нажмите кнопку «Обновить данные» для получения информации об оборудовании",
        )

    def create_top_panel(self):
        """Создание верхней панели с IP-адресом и действиями."""
        group_box = QGroupBox()
        group_box.setObjectName("connectionPanel")
        group_box.setProperty("uiRole", "toolbar")
        
        layout = QGridLayout()
        layout.setHorizontalSpacing(SPACING["sm"])
        layout.setVerticalSpacing(SPACING["xs"])
        layout.setContentsMargins(
            SPACING["md"], SPACING["md"], SPACING["md"], SPACING["lg"]
        )
        
        # Метка и поле для IP-адреса
        ip_label = QLabel("IP-адрес")
        ip_label.setProperty("uiRole", "fieldLabel")
        
        self.ip_entry = QLineEdit()
        self.ip_entry.setObjectName("ipEntry")
        self.ip_entry.setMinimumWidth(160)
        self.ip_entry.setPlaceholderText("link.ru")
        self.ip_entry.setText("192.168.1.1")
        self.ip_entry.textChanged.connect(
            lambda _text: self._invalidate_pdu_context()
        )
        self.ip_entry.textChanged.connect(
            lambda _text: self._invalidate_dmp_context()
        )
        self.ip_entry.textChanged.connect(
            lambda _text: self._publish_current_equipment_room_context("ip_changed")
        )
        self.ip_entry.textChanged.connect(
            lambda _text: self._supersede_model_actions("ip_changed")
        )
        self.ip_entry.returnPressed.connect(self.trigger_refresh_from_input)
        self.ip_entry.installEventFilter(self)
        
        # Кнопка для ввода пароля
        self.password_btn = QPushButton("Пароль")
        self.password_btn.setObjectName("passwordButton")
        self.password_btn.setProperty("uiRole", "secondary")
        self.password_btn.clicked.connect(self.show_password_dialog)
        
        # Кнопка обновления данных
        self.refresh_btn = QPushButton("Обновить данные")
        self.refresh_btn.setObjectName("refreshButton")
        self.refresh_btn.setProperty("uiRole", "primary")
        self.refresh_btn.clicked.connect(self.refresh_data)

        self.debug_btn = QPushButton("Отладка")
        self.debug_btn.setObjectName("debugButton")
        self.debug_btn.setProperty("uiRole", "secondary")
        self.debug_btn.clicked.connect(self.show_debug_window)

        self.setTabOrder(self.ip_entry, self.password_btn)
        self.setTabOrder(self.password_btn, self.refresh_btn)
        self.setTabOrder(self.refresh_btn, self.debug_btn)
        
        layout.addWidget(ip_label, 0, 0)
        layout.addWidget(self.ip_entry, 1, 0)
        layout.addWidget(self.password_btn, 1, 1)
        layout.addWidget(self.refresh_btn, 1, 2)
        layout.addWidget(self.debug_btn, 1, 3)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 0)
        layout.setColumnStretch(3, 0)
        
        group_box.setLayout(layout)
        self.connection_panel = group_box
        return group_box

    def _supersede_model_actions(self, reason="context_changed"):
        self._invalidate_equipment_switch_context(reason)
        self._diagnostic_action_generation += 1
        self._credential_action_generation += 1
        self._invalidate_reachability_context(reason)
        self._active_credential_configuration_context = None
        self._active_diagnostic_model_context = None
        self.__dict__.setdefault("_current_action_dialog_bindings", {}).clear()

    def _restore_refresh_button(self):
        if hasattr(self, "refresh_btn"):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")

    def _release_reachability_presentation_owner(self, operation_id):
        if (
            operation_id is not None
            and self.__dict__.get("_reachability_presentation_operation_id") == operation_id
        ):
            self._reachability_presentation_operation_id = None
            return True
        return False

    def _complete_reachability_loading_state(self, operation_id):
        if not self._release_reachability_presentation_owner(operation_id):
            return False
        if self.__dict__.get("ui_state") == UIState.LOADING:
            self.set_ui_state(UIState.IDLE, "Готово к обновлению")
        return True

    def _discard_diagnostic_credential_snapshot(self, operation_id):
        if operation_id is None:
            return None
        return self.__dict__.setdefault(
            "_diagnostic_credential_snapshots",
            {},
        ).pop(operation_id, None)

    def _store_diagnostic_credential_snapshot(self, snapshot):
        self.__dict__.setdefault("_diagnostic_credential_snapshots", {})[
            snapshot.reachability_operation_id
        ] = snapshot

    def _peek_diagnostic_credential_snapshot(self, operation_id):
        return self.__dict__.setdefault(
            "_diagnostic_credential_snapshots",
            {},
        ).get(operation_id)

    def _take_diagnostic_credential_snapshot(self, context):
        operation_id = (context or {}).get("operation_id")
        snapshot = self._discard_diagnostic_credential_snapshot(operation_id)
        if snapshot is None or context is None:
            return None
        if (
            snapshot.diagnostic_model != context.get("model")
            or snapshot.ip_address != context.get("ip")
            or snapshot.diagnostic_generation != context.get("generation")
            or snapshot.reachability_operation_id != context.get("operation_id")
            or snapshot.inventory_context_identity != context.get("inventory_context")
        ):
            return None
        return snapshot

    def _freeze_credential_candidates(self, candidates):
        return tuple(MappingProxyType(dict(candidate)) for candidate in tuple(candidates or ()))

    def _ensure_diagnostic_credential_candidates(self, device_name, candidates):
        if candidates or device_name == "Extron IPL T PCS4i":
            return
        raise CredentialConfigurationError(
            f"Credentials are required before refreshing {device_name}."
        )

    def _snapshot_credential_candidates(self, snapshot, device_name, ip_address):
        if (
            snapshot is None
            or snapshot.diagnostic_model != device_name
            or snapshot.ip_address != ip_address
        ):
            return None
        return snapshot.candidates

    def _snapshot_credential_index(self, snapshot, device_name, creds_list, ip_address):
        if (
            snapshot is not None
            and snapshot.diagnostic_model == device_name
            and snapshot.ip_address == ip_address
            and tuple(creds_list or ()) == snapshot.candidates
        ):
            return snapshot.starting_successful_index
        return self._credential_attempt_index(device_name, creds_list, ip_address)

    def _cleanup_reachability_operation(self, context, *, restore=True):
        if context is None:
            return False
        current = self.__dict__.get("_current_reachability_context")
        if current is not context:
            return False
        self._discard_diagnostic_credential_snapshot(context.get("operation_id"))
        self._current_reachability_context = None
        self._current_reachability_worker = None
        if restore:
            self._restore_refresh_button()
            self._complete_reachability_loading_state(context.get("operation_id"))
        else:
            self._release_reachability_presentation_owner(context.get("operation_id"))
        return True

    def _invalidate_reachability_context(self, reason="context_changed"):
        context = self.__dict__.get("_current_reachability_context")
        if context is None:
            return False
        return self._cleanup_reachability_operation(
            context,
            restore=reason != "shutdown",
        )

    def _supersede_pending_diagnostic_reachability(self, reason="diagnostic_superseded"):
        self._invalidate_reachability_context(reason)

    @staticmethod
    def _fallback_dialog_stage(purpose):
        if purpose is DiagnosticActionPurpose.DIAGNOSTIC_START:
            return "diagnostic_fallback"
        return "credential_fallback"

    @staticmethod
    def _dialog_binding_key(purpose, stage):
        return (purpose.value if hasattr(purpose, "value") else purpose, stage)

    def _publish_current_dialog_binding(self, stage, binding):
        self.__dict__.setdefault("_current_action_dialog_bindings", {})[
            self._dialog_binding_key(binding.purpose, stage)
        ] = binding

    def _clear_current_dialog_binding(self, stage, binding):
        bindings = self.__dict__.setdefault("_current_action_dialog_bindings", {})
        key = self._dialog_binding_key(binding.purpose, stage)
        if bindings.get(key) == binding:
            bindings.pop(key, None)

    def _current_dialog_binding(self, purpose, stage):
        return self.__dict__.setdefault("_current_action_dialog_bindings", {}).get(
            self._dialog_binding_key(purpose, stage)
        )
    def set_dark_theme(self):
        """Apply the centralized theme for direct window construction."""
        apply_theme(self)



    def init_screens(self):
        """Инициализация всех экранов"""
        self.screens = {
            "codec": CodecScreen(self),
            "matrix": MatrixScreen(self),
            "pdu": PDUScreen(self),
            "audio_dsp": AudioDSPScreen(self)
        }
        self._attach_registered_room_blocks()
        matrix_screen = self.screens["matrix"]
        matrix_screen.routeRequested.connect(self.matrix_controller.request_route)
        matrix_screen.refreshRequested.connect(
            self.matrix_controller.request_status_refresh
        )
        pdu_screen = self.screens["pdu"]
        pdu_screen.refreshRequested.connect(self._pdu_controller().request_refresh)
        pdu_screen.outletMutationRequested.connect(
            self._pdu_controller().request_individual_mutation
        )
        pdu_screen.bulkMutationRequested.connect(
            self._pdu_controller().request_bulk_mutation
        )
        self.matrix_controller.resultAccepted.connect(self._on_matrix_result)
        self.matrix_controller.errorAccepted.connect(self._on_matrix_error)
        self.matrix_controller.progressAccepted.connect(self._on_matrix_progress)
        self.matrix_controller.statusAccepted.connect(self._on_matrix_status)
        self.matrix_controller.terminalAccepted.connect(self._on_matrix_terminal)
        self.matrix_controller.finishedAccepted.connect(self._on_matrix_finished)
        self.matrix_controller.routeAccepted.connect(self._on_matrix_route_accepted)
        self.matrix_controller.routeError.connect(self._on_matrix_route_error)
    
    def create_update_time_panel(self):
        """Создание панели времени обновления"""
        panel = QWidget()
        panel.setObjectName("connectionStatusBar")
        panel.setProperty("uiRole", "statusBar")
        
        layout = QHBoxLayout(panel)
        layout.setSpacing(SPACING["sm"])
        layout.setContentsMargins(
            SPACING["sm"], SPACING["sm"], SPACING["sm"], 0
        )

        self.connection_indicator = StatusIndicator("inactive", show_text=False)
        self.connection_indicator.setObjectName("connectionIndicator")
        self.connection_indicator.setAccessibleName("Состояние соединения")

        self.connection_status = QLabel("Соединение: не установлено")
        self.connection_status.setObjectName("connectionStatus")
        self.connection_status.setProperty("uiRole", "secondary")
        
        time_label = QLabel("Последнее обновление:")
        time_label.setProperty("uiRole", "secondary")
        
        self.time_display = QLabel("Никогда")
        self.time_display.setProperty("uiRole", "secondary")
        self.time_display.setMinimumWidth(10)
        self.time_display.setAlignment(Qt.AlignLeft)
        
        layout.addWidget(self.connection_indicator)
        layout.addWidget(self.connection_status)
        layout.addStretch(1)
        layout.addWidget(time_label)
        layout.addWidget(self.time_display)
        
        return panel

    def set_connection_status(self, status: str, text: str):
        """Update the persistent connection summary without changing device logic."""
        if not hasattr(self, "connection_indicator"):
            return
        self.connection_indicator.set_status(status)
        self.connection_status.setText(text)
        for widget in (self.connection_indicator, self.connection_status):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def set_ui_state(self, state, text=None, screen=None):
        """Set the persistent state summary and, when requested, a screen state."""
        self.ui_state = coerce_ui_state(state)
        spec = state_spec(self.ui_state)
        self.setProperty("uiState", self.ui_state.value)
        self.set_connection_status(
            spec.indicator,
            text or f"Состояние: {spec.default_text}",
        )
        if screen is not None and hasattr(screen, "set_ui_state"):
            screen.set_ui_state(self.ui_state, text or spec.default_text)

    def _pdu_controller(self):
        controller = self.__dict__.get("pdu_controller")
        if controller is None:
            enrichment_enabled = self.__dict__.get("_pdu_room_codec_enrichment_enabled", False)
            controller = PDUController(
                shell=self,
                screen_provider=lambda: getattr(self, "screens", {}).get("pdu"),
                thread_pool=QThreadPool.globalInstance(),
                accepted_refresh_callback=(
                    self._on_pdu_refresh_accepted_for_enrichment
                    if enrichment_enabled
                    else None
                ),
                superseded_callback=(
                    self._on_pdu_context_superseded_for_enrichment
                    if enrichment_enabled
                    else None
                ),
            )
            self.__dict__["pdu_controller"] = controller
        return controller

    def _invalidate_pdu_context(self):
        self._pdu_controller().invalidate_context()

    def _pdu_room_codec_controller(self):
        controller = self.__dict__.get("pdu_room_codec_enrichment_controller")
        if controller is None:
            controller = PDURoomCodecEnrichmentController(
                inventory_provider=lambda: self.equipment_inventory,
                inventory_failure_provider=lambda: self.equipment_inventory_load_error,
                credential_candidates_provider=self._related_codec_credential_candidates,
                credential_index_provider=self._related_codec_credential_index,
                credential_revision_provider=self._related_codec_credential_revision,
                connection_profile_provider=self.get_device_connection_profile,
                success_persistence=self._persist_related_codec_success,
                presentation_callback=self._render_pdu_room_codec_enrichment,
                parent=self,
            )
            self.__dict__["pdu_room_codec_enrichment_controller"] = controller
        return controller

    def _on_pdu_refresh_accepted_for_enrichment(self, context):
        if not self.__dict__.get("_pdu_room_codec_enrichment_enabled", False):
            return
        self._pdu_room_codec_controller().accept_pdu_refresh(context)

    def _on_pdu_context_superseded_for_enrichment(self, event):
        if not self.__dict__.get("_pdu_room_codec_enrichment_enabled", False):
            return
        self._pdu_room_codec_controller().supersede_pdu_context(event)

    def current_device_name(self):
        request = self.__dict__.get("_active_request") or {}
        if request.get("device"):
            return request["device"]
        context = self.__dict__.get("_active_diagnostic_model_context") or {}
        return context.get("model")

    def _normalized_current_ip_or_warn(self):
        raw_ip = self.ip_entry.text().strip() if hasattr(self, "ip_entry") else ""
        normalized_ip = normalize_ip_address(raw_ip)
        if normalized_ip is None:
            self.set_ui_state(UIState.REQUEST_ERROR, "Неверный формат IP-адреса")
            QMessageBox.warning(self, "Внимание", "Неверный формат IP-адреса")
            return None
        return normalized_ip

    def _next_action_generation(self, purpose):
        if purpose is DiagnosticActionPurpose.DIAGNOSTIC_START:
            self._diagnostic_action_generation += 1
            return self._diagnostic_action_generation
        self._credential_action_generation += 1
        return self._credential_action_generation

    def _action_generation(self, purpose):
        if purpose is DiagnosticActionPurpose.DIAGNOSTIC_START:
            return self.__dict__.get("_diagnostic_action_generation", 0)
        return self.__dict__.get("_credential_action_generation", 0)

    def _inventory_context_id(self):
        return self._equipment_inventory_snapshot_context()

    def _binding_id(
        self,
        *,
        purpose,
        generation,
        normalized_ip,
        resolution_status=None,
        selection_source=None,
        accepted_model=None,
        screen_key=None,
        lifecycle_route=None,
        fallback_dialog_id=None,
        credential_dialog_id=None,
    ):
        return ActionBinding(
            purpose=purpose,
            generation=generation,
            normalized_ip=normalized_ip,
            inventory_context_identity=self._inventory_context_id(),
            resolution_status=resolution_status,
            selection_source=selection_source,
            accepted_model=accepted_model,
            screen_key=screen_key,
            lifecycle_route=lifecycle_route,
            fallback_dialog_id=fallback_dialog_id,
            credential_dialog_id=credential_dialog_id,
        )

    def _accepted_action_binding(
        self,
        *,
        purpose,
        generation,
        normalized_ip,
        resolution_status,
        source,
        entry,
        fallback_dialog_id=None,
        credential_dialog_id=None,
    ):
        return self._binding_id(
            purpose=purpose,
            generation=generation,
            normalized_ip=normalized_ip,
            resolution_status=getattr(resolution_status, "value", resolution_status),
            selection_source=source,
            accepted_model=entry.diagnostic_model,
            screen_key=entry.screen_key,
            lifecycle_route=entry.lifecycle_route,
            fallback_dialog_id=fallback_dialog_id,
            credential_dialog_id=credential_dialog_id,
        )

    def _next_fallback_dialog_id(self):
        self._fallback_dialog_generation += 1
        return self._fallback_dialog_generation

    def _next_credential_dialog_id(self):
        self._credential_dialog_generation += 1
        return self._credential_dialog_generation

    def _resolve_model_for_action(self, purpose, normalized_ip):
        return resolve_exact_model_for_ip(
            purpose=purpose,
            normalized_ip=normalized_ip,
            inventory=self.equipment_inventory,
        )

    def _open_model_fallback(self, *, purpose, generation, normalized_ip, resolution):
        fallback_dialog_id = self._next_fallback_dialog_id()
        fallback_stage = self._fallback_dialog_stage(purpose)
        binding_id = self._binding_id(
            purpose=purpose,
            generation=generation,
            normalized_ip=normalized_ip,
            resolution_status=resolution.status.value,
            fallback_dialog_id=fallback_dialog_id,
        )
        self._publish_current_dialog_binding(fallback_stage, binding_id)
        dialog = DeviceModelFallbackDialog(
            purpose=purpose,
            generation=generation,
            binding_id=binding_id,
            safe_reason=resolution.safe_reason or "Модель устройства не определена.",
            model_choices=dispatch_model_names(),
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            self._clear_current_dialog_binding(fallback_stage, binding_id)
            return None
        selection = dialog.selection()
        if selection is None:
            self._clear_current_dialog_binding(fallback_stage, binding_id)
            return None
        if not self._is_action_binding_current(
            purpose=purpose,
            generation=selection.generation,
            normalized_ip=normalized_ip,
            binding_id=selection.binding_id,
        ):
            return None
        entry = dispatch_entry_for_model(selection.diagnostic_model)
        if entry is None:
            return None
        accepted_binding = self._accepted_action_binding(
            purpose=purpose,
            generation=generation,
            normalized_ip=normalized_ip,
            resolution_status=resolution.status.value,
            source="MANUAL_FALLBACK",
            entry=entry,
            fallback_dialog_id=fallback_dialog_id,
        )
        self._publish_current_dialog_binding(fallback_stage, accepted_binding)
        if not self._is_action_binding_current(
            purpose=purpose,
            generation=generation,
            normalized_ip=normalized_ip,
            binding_id=accepted_binding,
        ):
            return None
        return entry, accepted_binding

    def _is_action_binding_current(self, *, purpose, generation, normalized_ip, binding_id):
        if not isinstance(binding_id, ActionBinding):
            return False
        if binding_id.purpose is not purpose:
            return False
        if generation != self._action_generation(purpose):
            return False
        if binding_id.generation != generation:
            return False
        if binding_id.normalized_ip != normalized_ip:
            return False
        if normalize_ip_address(self.ip_entry.text().strip()) != normalized_ip:
            return False
        if binding_id.inventory_context_identity != self._inventory_context_id():
            return False
        if binding_id.credential_dialog_id is not None:
            return (
                self._current_dialog_binding(purpose, "credential_dialog")
                == binding_id
            )
        if binding_id.fallback_dialog_id is not None:
            return (
                self._current_dialog_binding(
                    purpose,
                    self._fallback_dialog_stage(purpose),
                )
                == binding_id
            )
        return binding_id == self._binding_id(
            purpose=purpose,
            generation=generation,
            normalized_ip=normalized_ip,
            resolution_status=binding_id.resolution_status,
            selection_source=binding_id.selection_source,
            accepted_model=binding_id.accepted_model,
            screen_key=binding_id.screen_key,
            lifecycle_route=binding_id.lifecycle_route,
            fallback_dialog_id=binding_id.fallback_dialog_id,
            credential_dialog_id=binding_id.credential_dialog_id,
        )

    def _accept_diagnostic_model_context(self, *, normalized_ip, entry, source, generation, binding):
        context = {
            "purpose": DiagnosticActionPurpose.DIAGNOSTIC_START.value,
            "generation": generation,
            "binding": binding,
            "ip": normalized_ip,
            "model": entry.diagnostic_model,
            "screen_key": entry.screen_key,
            "lifecycle_route": entry.lifecycle_route,
            "source": source,
            "resolution_status": binding.resolution_status,
            "inventory_context": binding.inventory_context_identity,
        }
        self._active_diagnostic_model_context = context
        self.current_screen_type = entry.screen_key
        self.setWindowTitle(f"Диагностический модуль ММК - {entry.diagnostic_model}")
        if entry.diagnostic_model != MATRIX_DEVICE_NAME:
            self.matrix_controller.invalidate_context()
        if not self._is_pdu_device(entry.diagnostic_model):
            self._invalidate_pdu_context()
        if not self._is_dmp_device(entry.diagnostic_model):
            self._invalidate_dmp_context()
        self._publish_current_equipment_room_context("model_context_accepted", force=True)
        self._publish_current_equipment_switch_context("model_context_accepted", force=True)
        return context

    def _accept_test_diagnostic_model(self, diagnostic_model):
        """Test helper for legacy lifecycle tests after removing the UI selector."""
        entry = dispatch_entry_for_model(diagnostic_model)
        if entry is None:
            raise ValueError(f"Unsupported diagnostic model: {diagnostic_model}")
        normalized_ip = normalize_ip_address(self.ip_entry.text().strip()) or ""
        generation = self._next_action_generation(DiagnosticActionPurpose.DIAGNOSTIC_START)
        binding = self._accepted_action_binding(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation=generation,
            normalized_ip=normalized_ip,
            resolution_status="TEST_CONTEXT",
            source="TEST_CONTEXT",
            entry=entry,
        )
        context = self._accept_diagnostic_model_context(
            normalized_ip=normalized_ip,
            entry=entry,
            source="TEST_CONTEXT",
            generation=generation,
            binding=binding,
        )
        request = self.__dict__.get("_active_request")
        if request is not None:
            request["device"] = entry.diagnostic_model
            request["ip"] = normalized_ip
            request["screen"] = self.screens.get(entry.screen_key)
            request["credential_context"] = (
                self._pdu_context_token() if self._is_pdu_device(entry.diagnostic_model) else None
            )
        return context

    def _related_codec_credential_candidates(self, device_name, ip_address):
        return tuple(self.device_credentials.get(device_name) or ())

    def _related_codec_credential_index(self, device_name, ip_address, candidates):
        return self.get_valid_current_credential_index(
            device_name,
            tuple(candidates or ()),
            ip_address,
        )

    def _related_codec_credential_revision(self):
        return self.__dict__.get("_related_codec_credential_context_revision", 0)

    def _persist_related_codec_success(self, device_name, ip_address, credential_index, profile):
        self.set_current_credential_index(device_name, credential_index, ip_address)
        if profile:
            self.set_device_connection_profile(device_name, dict(profile), ip_address)

    def _render_pdu_room_codec_enrichment(self, payload):
        screen = getattr(self, "screens", {}).get("pdu")
        if screen is not None and hasattr(screen, "set_related_room_codec"):
            screen.set_related_room_codec(payload)

    def _attach_registered_room_blocks(self):
        self.room_information_blocks = {}
        registrations = registrations_by_screen()
        for screen_key, screen in self.screens.items():
            registration = registrations.get(screen_key)
            if registration is None or not registration.shared_room_block:
                continue
            block = attach_shared_room_block(screen, registration)
            if block is not None:
                self.room_information_blocks[screen_key] = block

    def _ensure_shared_room_block(self, screen_key):
        registration = registrations_by_screen().get(screen_key)
        if registration is None or not registration.shared_room_block:
            return None
        screen = getattr(self, "screens", {}).get(screen_key)
        if screen is None:
            return None
        block = getattr(screen, "shared_room_information_block", None)
        try:
            live = block is not None and block.parent() is not None and not block.isHidden()
        except RuntimeError:
            # The underlying C++ object was already deleted.
            live = False
        if not live:
            if block is not None:
                try:
                    block.deleteLater()
                except RuntimeError:
                    pass
                setattr(screen, "shared_room_information_block", None)
            block = attach_shared_room_block(screen, registration)
            if block is not None:
                self.room_information_blocks[screen_key] = block
        return block

    def replace_equipment_inventory_state(
        self,
        *,
        inventory=None,
        load_error=None,
        reason="inventory_replaced",
        supersede=True,
    ):
        previous_identity = self._equipment_inventory_snapshot_context()
        self.equipment_inventory = inventory
        self.equipment_inventory_load_error = load_error
        current_identity = self._equipment_inventory_snapshot_context()
        if supersede and current_identity != previous_identity:
            self._supersede_model_actions(reason)
            controller = self.__dict__.get("pdu_room_codec_enrichment_controller")
            if controller is not None:
                controller.invalidate_context(reason)
            if hasattr(self, "matrix_controller"):
                self.matrix_controller.invalidate_context()
            if "dmp_polling_controller" in self.__dict__:
                self._dmp_controller().invalidate_context()
            self._equipment_switch_context_generation += 1
            self._equipment_switch_context_binding = None
            self._publish_current_equipment_switch_context(reason, force=True)

    def set_equipment_inventory(self, inventory, *, reason="inventory_replaced"):
        self.replace_equipment_inventory_state(
            inventory=inventory,
            load_error=None,
            reason=reason,
        )

    def set_equipment_inventory_failure(self, load_error, *, reason="inventory_failure"):
        self.replace_equipment_inventory_state(
            inventory=None,
            load_error=load_error,
            reason=reason,
        )

    def _equipment_inventory_snapshot_context(self):
        inventory = getattr(self, "equipment_inventory", None)
        if inventory is not None:
            return inventory.metadata.snapshot_id
        error = getattr(self, "equipment_inventory_load_error", None)
        category = getattr(getattr(error, "category", None), "value", "UNAVAILABLE")
        return f"unavailable:{category}"

    def _current_equipment_room_binding(self):
        if not hasattr(self, "ip_entry"):
            return None
        device_name = self.current_device_name()
        if not device_name:
            return None
        if device_name in PDU_DEVICE_NAMES:
            return None
        screen_key = screen_key_for_model(device_name) or self.device_to_screen.get(device_name)
        if screen_key is None:
            return None
        if registrations_by_screen().get(screen_key) is None:
            return None
        normalized_ip = normalize_ip_address(self.ip_entry.text().strip())
        return (
            device_name,
            normalized_ip,
            self._equipment_inventory_snapshot_context(),
            screen_key,
            self.__dict__.get("_equipment_room_credential_context_revision", 0),
        )

    def _publish_current_equipment_room_context(self, reason="context_changed", force=False):
        binding = self._current_equipment_room_binding()
        if binding is None:
            return
        screen_key = binding[3]
        block = self._ensure_shared_room_block(screen_key)
        if block is None:
            return
        if (
            not force
            and binding == self.__dict__.get("_equipment_room_context_binding")
            and block.property("roomContextBinding") == repr(binding)
        ):
            return

        self._equipment_room_context_generation += 1
        generation = self._equipment_room_context_generation
        self._equipment_room_context_binding = binding
        device_name, normalized_ip, _snapshot_id, _page_context, _credential_revision = binding
        if normalized_ip is None:
            result = self.room_context_resolver.resolve_equipment_room_context(None, "")
            result = type(result)(
                RoomResolutionStatus.ROOM_UNRESOLVED,
                safe_message="Room context is unavailable until a valid IP address is entered.",
                room_vip_status=result.room_vip_status,
            )
        else:
            result = self.room_context_resolver.resolve_equipment_room_context(
                self.equipment_inventory,
                normalized_ip,
            )
            if self.equipment_inventory is None:
                failure = self.equipment_inventory_load_error
                category = getattr(getattr(failure, "category", None), "value", "UNAVAILABLE")
                result = type(result)(
                    RoomResolutionStatus.INVENTORY_UNAVAILABLE,
                    safe_message=f"Equipment inventory unavailable: {category}.",
                    room_vip_status=result.room_vip_status,
                )
        self._accept_equipment_room_context_publication(
            generation,
            binding,
            result,
            reason=reason,
            device_name=device_name,
        )

    def _accept_equipment_room_context_publication(
        self,
        generation,
        binding,
        result,
        *,
        reason,
        device_name,
    ):
        if generation != self.__dict__.get("_equipment_room_context_generation"):
            return False
        if binding != self.__dict__.get("_equipment_room_context_binding"):
            return False
        block = self._ensure_shared_room_block(binding[3])
        if block is None:
            return False
        room_name = result.room_name
        safe_message = None
        if result.status != RoomResolutionStatus.RESOLVED:
            safe_message = result.safe_message or self._safe_room_context_message(result.status)
        block.set_room_presentation(
            room_name=room_name,
            room_vip_status=result.room_vip_status,
            safe_message=safe_message,
        )
        block.setProperty("roomContextBinding", repr(binding))
        block.setProperty("roomContextGeneration", generation)
        block.setProperty("roomContextReason", reason)
        block.setProperty("roomContextDevice", device_name)
        return True

    @staticmethod
    def _safe_room_context_message(status):
        return {
            RoomResolutionStatus.INVENTORY_UNAVAILABLE: "База оборудования недоступна.",
            RoomResolutionStatus.PDU_NOT_FOUND: "Оборудование не найдено в базе оборудования.",
            RoomResolutionStatus.AMBIGUOUS_PDU_IP: "В базе найдено несколько устройств с этим IP-адресом.",
            RoomResolutionStatus.ROOM_UNRESOLVED: "Для устройства не указано помещение.",
        }.get(status, "Контекст комнаты недоступен.")

    def _current_equipment_switch_binding(self):
        if not hasattr(self, "ip_entry"):
            return None
        device_name = self.current_device_name()
        if not device_name:
            return None
        screen_key = screen_key_for_model(device_name) or self.device_to_screen.get(device_name)
        if screen_key is None:
            return None
        if registrations_by_screen().get(screen_key) is None:
            return None
        normalized_ip = normalize_ip_address(self.ip_entry.text().strip())
        return (
            device_name,
            normalized_ip,
            self._equipment_inventory_snapshot_context(),
            screen_key,
        )

    def _invalidate_equipment_switch_context(self, reason="context_changed"):
        previous_binding = self.__dict__.get("_equipment_switch_context_binding")
        self._equipment_switch_context_generation += 1
        self._equipment_switch_context_binding = None
        if previous_binding is None:
            return
        screen = getattr(self, "screens", {}).get(previous_binding[3])
        if screen is None or not hasattr(screen, "set_switch_connection"):
            return
        screen.set_switch_connection(
            switch_ip_address=None,
            switch_port=None,
        )

    def _publish_current_equipment_switch_context(self, reason="context_changed", force=False):
        binding = self._current_equipment_switch_binding()
        if binding is None:
            return
        screen_key = binding[3]
        screen = getattr(self, "screens", {}).get(screen_key)
        if screen is None or not hasattr(screen, "set_switch_connection"):
            return
        if (
            not force
            and binding == self.__dict__.get("_equipment_switch_context_binding")
        ):
            return
        stored = self.__dict__.get("_equipment_switch_context_binding")
        if stored is not None and stored[3] != binding[3]:
            prev_screen = getattr(self, "screens", {}).get(stored[3])
            if (
                prev_screen is not None
                and prev_screen is not screen
                and hasattr(prev_screen, "set_switch_connection")
            ):
                prev_screen.set_switch_connection(
                    switch_ip_address=None,
                    switch_port=None,
                )
        self._equipment_switch_context_generation += 1
        generation = self._equipment_switch_context_generation
        self._equipment_switch_context_binding = binding
        device_name, normalized_ip, _snapshot_id, _page_context = binding
        result = self.switch_connection_resolver.resolve_switch_connection(
            self.equipment_inventory,
            normalized_ip,
        )
        self._accept_equipment_switch_publication(
            generation,
            binding,
            result,
            reason=reason,
            device_name=device_name,
        )

    def _accept_equipment_switch_publication(
        self,
        generation,
        binding,
        result,
        *,
        reason,
        device_name,
    ):
        if generation != self.__dict__.get("_equipment_switch_context_generation"):
            return False
        if binding != self.__dict__.get("_equipment_switch_context_binding"):
            return False
        if binding != self._current_equipment_switch_binding():
            return False
        screen = getattr(self, "screens", {}).get(binding[3])
        if screen is None or not hasattr(screen, "set_switch_connection"):
            return False
        screen.set_switch_connection(
            switch_ip_address=result.switch_ip_address,
            switch_port=result.switch_port,
        )
        return True

    def _dmp_controller(self):
        controller = self.__dict__.get("dmp_polling_controller")
        if controller is None:
            controller = DMPPollingController(
                shell=self,
                screen_provider=lambda: getattr(self, "screens", {}).get("audio_dsp"),
                thread_pool=QThreadPool.globalInstance(),
            )
            self.__dict__["dmp_polling_controller"] = controller
        return controller

    def _invalidate_dmp_context(self):
        self._dmp_controller().invalidate_context()

    def _matrix_public_context(self):
        return (
            MATRIX_DEVICE_NAME,
            self.ip_entry.text().strip() if hasattr(self, "ip_entry") else "",
        )

    def _matrix_credential_candidates(self, device_name, ip_address):
        active_request = self.__dict__.get("_active_request") or {}
        candidates = None
        if active_request.get("device") == device_name:
            candidates = getattr(self, "_active_request_credentials", None)
        if candidates is None:
            candidates = self.__dict__.get("device_credentials", {}).get(
                device_name, []
            )
        return tuple(candidates or ())

    def _matrix_credential_index(self, device_name, ip_address, candidates):
        return self.get_valid_current_credential_index(
            device_name, tuple(candidates or ()), ip_address
        )

    def _matrix_credential_revision(self):
        return self.__dict__.get("_matrix_credential_context_revision", 0)

    def _matrix_advance_credential_attempt(
        self,
        device_name,
        ip_address,
        candidates,
        current_index,
        operation_id,
    ):
        return self._advance_request_credential_attempt(
            device_name,
            tuple(candidates or ()),
            ip_address,
            current_index,
            operation_id=operation_id,
        )

    def _active_request_matches_model_ip(self, device_name, normalized_ip):
        request = self.__dict__.get("_active_request") or {}
        return request.get("device") == device_name and request.get("ip") == normalized_ip

    def _related_codec_context_matches_model_ip(self, device_name, normalized_ip):
        controller = self.__dict__.get("pdu_room_codec_enrichment_controller")
        presentation = getattr(controller, "_last_presentation", None)
        if presentation is None or normalized_ip is None:
            return False
        return (
            presentation.codec_diagnostic_model == device_name
            and presentation.codec_ip_address == normalized_ip
        )

    def _current_room_context_matches_model_ip(self, device_name, normalized_ip):
        binding = self.__dict__.get("_equipment_room_context_binding")
        if binding is None or normalized_ip is None:
            return False
        return binding[0] == device_name and binding[1] == normalized_ip

    def _on_credential_configuration_changed(self, device_name=None, normalized_ip=None):
        exact_context = device_name is not None and normalized_ip is not None
        if not exact_context:
            return

        reachability = self.__dict__.get("_current_reachability_context")
        if (
            reachability is not None
            and reachability.get("model") == device_name
            and reachability.get("ip") == normalized_ip
        ):
            self._supersede_pending_diagnostic_reachability(
                "credential_context_changed"
            )

        related_changed = self._related_codec_context_matches_model_ip(
            device_name, normalized_ip
        )
        if related_changed:
            self.__dict__["_related_codec_credential_context_revision"] = (
                self.__dict__.get("_related_codec_credential_context_revision", 0) + 1
            )
            controller = self.__dict__.get("pdu_room_codec_enrichment_controller")
            if controller is not None:
                controller.invalidate_context("credential_context_changed")

        room_changed = self._current_room_context_matches_model_ip(
            device_name, normalized_ip
        )
        if room_changed:
            self.__dict__["_equipment_room_credential_context_revision"] = (
                self.__dict__.get("_equipment_room_credential_context_revision", 0) + 1
            )
            self._publish_current_equipment_room_context(
                "credential_context_changed",
                force=True,
            )

        if (
            device_name == MATRIX_DEVICE_NAME
            and self._active_request_matches_model_ip(device_name, normalized_ip)
        ):
            self._matrix_credential_context_revision = (
                self.__dict__.get("_matrix_credential_context_revision", 0) + 1
            )
            if hasattr(self, "matrix_controller"):
                self.matrix_controller.invalidate_context()

        if (
            device_name == DMP_DEVICE_NAME
            and self._active_request_matches_model_ip(device_name, normalized_ip)
        ):
            self._dmp_controller().invalidate_credential_context()

        if self._is_pdu_device(device_name):
            self._discard_obsolete_pdu_credential_attempt_plans(device_name, normalized_ip)
            if self._active_request_matches_model_ip(device_name, normalized_ip):
                self._invalidate_pdu_context()
                self.__dict__.pop("_active_request_credentials", None)

    def configure_credential_candidate(self, device_name, normalized_ip, credential):
        if not device_name or not normalized_ip:
            raise ValueError("Credential configuration requires exact model and IP.")
        if device_name in self.device_credentials:
            creds_list = dict.__getitem__(self.device_credentials, device_name)
        else:
            creds_list = []
            dict.__setitem__(self.device_credentials, device_name, creds_list)
        old_order = list(creds_list)

        existing_index = None
        password_only = self._is_pcs4i_device(device_name)
        for index, current in enumerate(creds_list):
            same_password = current.get("password") == credential.get("password")
            same_identity = password_only or current.get("username") == credential.get("username")
            if same_password and same_identity:
                existing_index = index
                break

        inserted = existing_index is None
        if inserted:
            creds_list.insert(0, dict(credential))
        else:
            creds_list.insert(0, creds_list.pop(existing_index))
        self._remap_successful_credential_indexes_after_reorder(
            device_name,
            old_order,
            list(creds_list),
        )
        self._on_credential_configuration_changed(device_name, normalized_ip)
        return inserted

    @staticmethod
    def _credential_identity_for_index_remap(device_name, credential):
        if not isinstance(credential, dict):
            return None
        if VCSDiagnosticApp._is_pcs4i_device(device_name):
            return ("password", credential.get("password"))
        return ("username_password", credential.get("username"), credential.get("password"))

    @staticmethod
    def _credential_identity_positions(device_name, credentials, identity):
        return [
            index
            for index, candidate in enumerate(credentials)
            if VCSDiagnosticApp._credential_identity_for_index_remap(
                device_name,
                candidate,
            ) == identity
        ]

    def _successful_credential_index_keys_for_model(self, device_name):
        ip_prefix = f"{device_name}|"
        return [
            key
            for key in list(self.current_credential_index)
            if key == device_name or key.startswith(ip_prefix)
        ]

    def _remap_successful_credential_indexes_after_reorder(
        self, device_name, old_order, new_order
    ):
        for key in self._successful_credential_index_keys_for_model(device_name):
            saved_index = self.current_credential_index.get(key)
            if (
                not isinstance(saved_index, int)
                or saved_index < 0
                or saved_index >= len(old_order)
            ):
                self.current_credential_index.pop(key, None)
                continue
            identity = self._credential_identity_for_index_remap(
                device_name,
                old_order[saved_index],
            )
            if identity is None:
                self.current_credential_index.pop(key, None)
                continue
            if len(self._credential_identity_positions(device_name, old_order, identity)) != 1:
                self.current_credential_index.pop(key, None)
                continue
            new_positions = self._credential_identity_positions(
                device_name,
                new_order,
                identity,
            )
            if len(new_positions) == 1:
                self.current_credential_index[key] = new_positions[0]
            else:
                self.current_credential_index.pop(key, None)

    @staticmethod
    def _is_pdu_device(device_name):
        return device_name in {"Aten PE8208AV", "Extron IPL T PCS4i"}

    def _discard_obsolete_pdu_credential_attempt_plans(self, device_name=None, normalized_ip=None):
        plans = self.__dict__.get("_credential_attempt_plans")
        if not plans:
            return
        if device_name is None:
            plans.clear()
            return
        if normalized_ip is not None:
            exact_key = f"{device_name}|{normalized_ip}"
            operation_prefix = f"{exact_key}|"
            for key in list(plans):
                if key == exact_key or key.startswith(operation_prefix):
                    plans.pop(key, None)
            return
        prefix = f"{device_name}|"
        for key in list(plans):
            if key == device_name or key.startswith(prefix):
                plans.pop(key, None)

    def _pdu_context_token(self):
        return self._pdu_controller().context_token()

    @staticmethod
    def _is_dmp_device(device_name):
        return device_name == DMP_DEVICE_NAME

    def _set_active_pdu_credential_context(
        self,
        device_name,
        ip_address,
        credential_index,
    ):
        request = self.__dict__.get("_active_request")
        if not request:
            return
        if request.get("device") != device_name or request.get("ip") != ip_address:
            return
        request["credential_index"] = credential_index

    def _begin_request(self, device_name, ip_address, screen):
        self._request_serial += 1
        self._active_request = {
            "id": self._request_serial,
            "device": device_name,
            "ip": ip_address,
            "screen": screen,
            "credential_context": self._pdu_context_token()
            if VCSDiagnosticApp._is_pdu_device(device_name)
            else None,
            "credential_index": None,
        }
        if VCSDiagnosticApp._is_pdu_device(device_name):
            self._pdu_controller()._current_outlet_context = None
            if screen is not None and hasattr(screen, "set_bulk_records_current"):
                screen.set_bulk_records_current(False)
        self.set_ui_state(
            UIState.LOADING,
            f"Подключение к {device_name} ({ip_address})…",
            screen,
        )
        return self._active_request

    def _next_pdu_operation_id(self):
        return self._pdu_controller().next_operation_id()

    def _request_is_current(self, request_id, worker=None):
        request = self._active_request
        if request is None or request_id != request["id"]:
            return False
        return worker is None or worker is getattr(self, "current_worker", None)

    def _bind_worker(self, worker):
        """Bind worker signals to the request that created it."""
        if self._active_request is None:
            device_name = getattr(worker, "device_name", None) or self.current_device_name()
            entry = dispatch_entry_for_model(device_name)
            if entry is None or entry.screen_key not in self.screens:
                self._fail_request_start(f"Неподдерживаемая модель: {device_name}")
                return
            self._begin_request(
                device_name,
                getattr(worker, "ip_address", self.ip_entry.text().strip()),
                self.screens.get(entry.screen_key),
            )
        request_id = self._active_request["id"]
        worker.signals.result.connect(
            lambda data, w=worker, rid=request_id:
            self.on_device_data_received(data, w, rid)
        )
        worker.signals.error.connect(
            lambda error, w=worker, rid=request_id:
            self.on_device_error(error, w, rid)
        )
        worker.signals.progress.connect(
            lambda progress, w=worker, rid=request_id:
            self.on_progress_update(progress, w, rid)
        )
        worker.signals.status.connect(
            lambda status, w=worker, rid=request_id:
            self.on_status_update(status, w, rid)
        )
        worker.signals.finished.connect(
            lambda w=worker, rid=request_id:
            self.on_worker_finished(w, rid)
        )

    def _matrix_request_id(self):
        request = self.__dict__.get("_active_request") or {}
        return request.get("id")

    def _on_matrix_result(self, data, worker):
        self.current_worker = worker
        self.on_device_data_received(data, worker, self._matrix_request_id())

    def _on_matrix_error(self, error, worker):
        self.current_worker = worker
        self.on_device_error(error, worker, self._matrix_request_id())

    def _on_matrix_progress(self, progress, worker):
        self.current_worker = worker
        self.on_progress_update(progress, worker, self._matrix_request_id())

    def _on_matrix_status(self, status, worker):
        self.current_worker = worker
        self.on_status_update(status, worker, self._matrix_request_id())

    def _on_matrix_terminal(self, message, worker):
        self.current_worker = worker
        self.on_terminal_log(message)

    def _on_matrix_finished(self, worker):
        self.current_worker = worker
        self.on_worker_finished(worker, self._matrix_request_id())

    def _on_matrix_route_accepted(self, input_num):
        matrix_screen = self.screens.get("matrix")
        if matrix_screen is not None:
            matrix_screen.current_connection = input_num
            matrix_screen.update_connection_display()

    def _on_matrix_route_error(self, message):
        QMessageBox.warning(
            self,
            "Ошибка",
            f"Не удалось переключить матрицу: {message}",
        )

    def _fail_request_start(self, error):
        """Leave loading deterministically when worker construction fails."""
        self.hide_progress_dialog()
        self.set_ui_state(
            UIState.REQUEST_ERROR,
            f"Не удалось запустить запрос: {error}",
            (self._active_request or {}).get("screen"),
        )
        if hasattr(self, "refresh_btn"):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
    
    def generate_fake_data(self, codec_name):
        """Генерация тестовых данных для кодеков"""
        data = {
            "Версия прошивки": f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "Модель кодеков": codec_name,
            "Серийный номер": f"SN{random.randint(100000, 999999)}",
            "MAC адрес": ":".join([f"{random.randint(0x00, 0xff):02x}" for _ in range(6)]),
            "SIP регистрация": random.choice(["Зарегистрирован", "Не зарегистрирован"]),
            "Время работы": f"{random.randint(1, 100)} дней",
            "Температура": f"{random.randint(30, 60)}°C",
            "Скорость сети": f"{random.randint(10, 1000)} Мбит/с",
            "Статус звонка": random.choice(["Подключено", "Не подключено"]),
            "Статус презентации": random.choice(["Подключено", "Не подключено"]),
            "Громкость микрофона": f"{random.randint(0, 100)}%",
            "Громкость динамиков": f"{random.randint(0, 100)}%",
            "Статус камеры": random.choice(["Подключена", "Отключена"]),
            "Статус микрофона": random.choice(["Подключен", "Отключен"])
        }
        
        return data
    
    def on_device_change(self, device_name):
        """Обработка изменения выбранного устройства"""
        entry = dispatch_entry_for_model(device_name)
        if entry is None:
            self.set_ui_state(UIState.IDLE, "Модель устройства не поддерживается")
            return False
        self._supersede_model_actions("model_changed")
        self._invalidate_dmp_context()
        codec_screen = self.screens.get("codec") if hasattr(self, 'screens') else None
        if codec_screen and hasattr(codec_screen, 'reset_volume_session'):
            codec_screen.reset_volume_session()
        if codec_screen and hasattr(codec_screen, 'stop_te20_monitor_audio_polling'):
            codec_screen.stop_te20_monitor_audio_polling()
        if device_name != MATRIX_DEVICE_NAME:
            self.matrix_controller.invalidate_context()

        screen_type = entry.screen_key
        if screen_type == "codec" and codec_screen and hasattr(codec_screen, 'update_parameters_display'):
            codec_screen.update_parameters_display()
        self._ensure_shared_room_block(screen_type)
        
        # Сохраняем тип экрана, который должен отображаться после обновления
        self.current_screen_type = screen_type
        
        # Показываем заглушку вместо экрана
        self.screen_container.setCurrentWidget(self.placeholder_widget)
        self._active_request = None
        self.hide_progress_dialog()
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Обновить данные")
        self.set_ui_state(UIState.IDLE, "Данные ещё не запрашивались")
        self._publish_current_equipment_room_context("model_changed")
        self._publish_current_equipment_switch_context("model_changed", force=True)
        return True
        
    def eventFilter(self, obj, event):
        """Запускать обновление по Enter на списке устройств."""
        if isinstance(obj, QPushButton) and self._is_user_button_activation(obj, event):
            self.log_button_click(obj)

        # Выделение всего текста в IP-поле при клике
        if obj is getattr(self, 'ip_entry', None) and event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                QTimer.singleShot(0, self.ip_entry.selectAll)

        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        self._top_alignment_attempts = 0
        QTimer.singleShot(0, self._align_frame_to_screen_top)

    def _align_frame_to_screen_top(self):
        window_handle = self.windowHandle()
        screen = window_handle.screen() if window_handle is not None else QApplication.primaryScreen()
        if screen is None:
            return
        top = screen.availableGeometry().top()
        delta = top - self.frameGeometry().top()
        if delta:
            self.move(self.x(), self.y() + delta)
        self._top_alignment_attempts = getattr(self, "_top_alignment_attempts", 0) + 1
        if self._top_alignment_attempts < 3:
            QTimer.singleShot(0, self._align_frame_to_screen_top)

    def _is_user_button_activation(self, button, event):
        if not button.isEnabled():
            return False

        event_type = event.type()
        if event_type == QEvent.MouseButtonRelease:
            if event.button() != Qt.LeftButton or not button.rect().contains(event.pos()):
                return False
        elif event_type == QEvent.KeyRelease:
            if event.key() not in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                return False
        else:
            return False

        event_key = (id(button), event_type, int(datetime.datetime.now().timestamp() * 1000))
        if event_key == self._last_logged_button_event:
            return False
        self._last_logged_button_event = event_key
        return True

    def _get_button_log_label(self, button):
        text = button.text().strip()
        tooltip = button.toolTip().strip()
        object_name = button.objectName().strip()

        if text and tooltip:
            return f"{text} ({tooltip})"
        if text:
            return text
        if tooltip:
            return tooltip
        if object_name:
            return object_name
        return button.__class__.__name__

    def log_button_click(self, button):
        try:
            os.makedirs(self.button_log_dir, exist_ok=True)

            device_model = self.current_device_name() or ""
            device_ip = self.ip_entry.text().strip() if hasattr(self, 'ip_entry') else ""
            clean_value = lambda value: str(value).replace("\r", " ").replace("\n", " ")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = (
                f"[{timestamp}] "
                f"Модель: {clean_value(device_model)} | "
                f"IP: {clean_value(device_ip)} | "
                f"Кнопка: {clean_value(self._get_button_log_label(button))}\n"
            )

            with open(self.button_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(log_line)
        except Exception as e:
            print(f"Button click log write failed: {e}")

    def trigger_refresh_from_input(self):
        """Унифицированный запуск обновления из полей ввода."""
        if hasattr(self, 'refresh_btn') and self.refresh_btn.isEnabled():
            self.refresh_btn.click()

    def get_current_matrix_credentials(self):
        device_name = "Extron IN1804"
        creds_list = self.device_credentials.get(device_name, [])
        if not creds_list:
            return None

        current_idx = self.get_valid_current_credential_index(
            device_name, creds_list, self.ip_entry.text().strip()
        )
        return creds_list[current_idx]

    def get_credential_key(self, device_name: str, ip_address: str = None):
        if ip_address:
            return f"{device_name}|{ip_address}"
        return device_name

    def get_current_credential_index(self, device_name: str, ip_address: str = None):
        if ip_address:
            return self.current_credential_index.get(
                self.get_credential_key(device_name, ip_address),
                0,
            )
        return self.current_credential_index.get(device_name, 0)

    def set_current_credential_index(self, device_name: str, index: int, ip_address: str = None):
        if ip_address:
            self.current_credential_index[self.get_credential_key(device_name, ip_address)] = index
        else:
            self.current_credential_index[device_name] = index

    def get_valid_current_credential_index(self, device_name, creds_list, ip_address=None):
        index = self.get_current_credential_index(device_name, ip_address)
        if index < 0 or index >= len(creds_list):
            return 0
        return index

    def _credential_attempt_plan_key(self, device_name, ip_address=None, operation_id=None):
        key = self.get_credential_key(device_name, ip_address)
        if operation_id is not None:
            return f"{key}|operation:{operation_id}"
        return key

    def _credential_attempt_plan(
        self, device_name, creds_list, ip_address=None, operation_id=None
    ):
        """Return one finite request cursor without mutating successful-index memory."""
        plans = self.__dict__.get("_credential_attempt_plans")
        if plans is None:
            plans = self._credential_attempt_plans = {}
        key = VCSDiagnosticApp._credential_attempt_plan_key(
            self, device_name, ip_address, operation_id
        )
        plan = plans.get(key)
        candidates = tuple(creds_list or ())
        if plan is None or plan.candidates != candidates:
            plan = CredentialAttemptPlan(
                candidates,
                VCSDiagnosticApp.get_valid_current_credential_index(
                    self,
                    device_name, candidates, ip_address
                ),
            )
            plans[key] = plan
        return plan

    def _credential_attempt_index(
        self, device_name, creds_list, ip_address=None, operation_id=None
    ):
        return self._credential_attempt_plan(
            device_name, creds_list, ip_address, operation_id
        ).current_index

    def _discard_credential_attempt_plan(
        self, device_name, ip_address=None, operation_id=None
    ):
        self.__dict__.get("_credential_attempt_plans", {}).pop(
            VCSDiagnosticApp._credential_attempt_plan_key(
                self, device_name, ip_address, operation_id
            ),
            None,
        )

    def _advance_codec_credential_attempt(
        self, device_name, creds_list, ip_address, current_index
    ):
        return (
            self._advance_request_credential_attempt(
                device_name, creds_list, ip_address, current_index
            )
            is not None
        )

    def _advance_request_credential_attempt(
        self, device_name, creds_list, ip_address, current_index, operation_id=None
    ):
        plans = self.__dict__.get("_credential_attempt_plans")
        if plans is None:
            plans = self._credential_attempt_plans = {}
        key = VCSDiagnosticApp._credential_attempt_plan_key(
            self, device_name, ip_address, operation_id
        )
        plan = plans.get(key)
        candidates = tuple(creds_list or ())
        if (
            plan is None
            or plan.candidates != candidates
            or plan.current_index != current_index
        ):
            plan = CredentialAttemptPlan(candidates, current_index)
            plans[key] = plan
        if not plan.advance_after_authentication_failure():
            return None
        return plan.current_index

    @staticmethod
    def _is_pcs4i_device(device_name):
        return device_name == "Extron IPL T PCS4i"

    def _uses_request_scoped_credential_retry(self, device_name):
        return (
            self.is_vcs_codec_device(device_name)
            or VCSDiagnosticApp._is_pcs4i_device(device_name)
            or device_name == MATRIX_DEVICE_NAME
            or device_name == "Biamp Tesira Forte CI"
        )

    def _is_structured_retry_authentication_error(self, device_name, error_type, error_message):
        if VCSDiagnosticApp._uses_request_scoped_credential_retry(self, device_name):
            return error_type == CodecFailureCategory.AUTHENTICATION.value
        return False

    @staticmethod
    def _credential_secrets(creds_list):
        return tuple(
            value
            for credentials in creds_list
            if isinstance(credentials, dict)
            for value in credentials.values()
            if value is not None and str(value)
        )

    def get_device_connection_profile(self, device_name: str, ip_address: str = None):
        if ip_address:
            return self.device_connection_profiles.get((device_name, ip_address))
        return self.device_connection_profiles.get(device_name)

    def set_device_connection_profile(self, device_name: str, profile: dict, ip_address: str = None):
        self.device_connection_profiles[device_name] = profile
        if ip_address:
            self.device_connection_profiles[(device_name, ip_address)] = profile

    def switch_screen(self, screen_type):
        """Переключение между экранами"""
        if screen_type in self.screens:
            screen_index = list(self.screens.keys()).index(screen_type)
            self.screen_container.setCurrentIndex(screen_index)
            self.current_screen = self.screens[screen_type]
    
    def update_ip_for_device(self, device_name):
        """Обновление IP адреса для выбранного устройства"""
        ip_mapping = {
            "Huawei TE20": "link.ru",
            "Huawei TE40": "link.ru",
            "CloudLink Bar 310": "link.ru",  # Добавлено новое устройство
            "CloudLink Box 310": "link.ru",
            "CloudLink Box 300": "link.ru",
            "Polycom RPG 310": "link.ru",
            "Extron IN1804": "link.ru"
        }
        
        self.ip_entry.setText(ip_mapping.get(device_name, "link.ru"))
    
    def validate_ip_address(self, ip: str) -> bool:
        """Валидация IP адреса"""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        parts = ip.split('.')
        for part in parts:
            if not 0 <= int(part) <= 255:
                return False
        
        return True

    def ping_device(self, ip_address: str) -> bool:
        return self._ping_device_address(ip_address)

    @staticmethod
    def _ping_device_address(ip_address: str) -> bool:
        if platform.system().lower() == "windows":
            command = ["ping", "-n", "1", "-w", "1000", ip_address]
        else:
            command = ["ping", "-c", "1", "-W", "1", ip_address]

        try:
            startupinfo = None
            if platform.system().lower() == "windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                timeout=2,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Ping check failed for {ip_address}: {e}")
            return False

    def ensure_ping_success(self, ip_address: str) -> bool:
        if self.ping_device(ip_address):
            return True

        self.set_ui_state(UIState.DISCONNECTED, f"Нет соединения с {ip_address}")
        QMessageBox.warning(self, "Внимание", "Ping неуспешен")
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
        return False

    def _next_reachability_operation_id(self):
        self._reachability_operation_serial = (
            self.__dict__.get("_reachability_operation_serial", 0) + 1
        )
        return self._reachability_operation_serial

    def _reachability_thread_pool(self):
        return QThreadPool.globalInstance()

    def _submit_reachability_check(self, context):
        operation_context = dict(context)
        self._current_reachability_context = operation_context
        self._reachability_presentation_operation_id = operation_context["operation_id"]
        if hasattr(self, "refresh_btn"):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Проверка...")
        self.set_ui_state(
            UIState.LOADING,
            f"Проверка доступности IP {operation_context['ip']}…",
        )
        worker = ReachabilityCheckWorker(
            operation_id=operation_context["operation_id"],
            ip_address=operation_context["ip"],
            ping_callable=self.__dict__.get(
                "_reachability_ping_callable",
                self._ping_device_address,
            ),
        )
        worker.signals.finished.connect(self._on_reachability_finished)
        self._current_reachability_worker = worker
        try:
            self._reachability_thread_pool().start(worker)
        except Exception:
            self._cleanup_reachability_operation(operation_context, restore=True)
            self.hide_progress_dialog()
            self.set_ui_state(
                UIState.REQUEST_ERROR,
                "Не удалось запустить проверку доступности IP",
            )
            return None
        return worker

    def _is_reachability_context_current(self, context):
        if context is None or self.__dict__.get("_current_reachability_context") is not context:
            return False
        return self._is_action_binding_current(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation=context["generation"],
            normalized_ip=context["ip"],
            binding_id=context["binding"],
        )

    @pyqtSlot(dict)
    def _on_reachability_finished(self, result):
        context = self.__dict__.get("_current_reachability_context")
        if context is None or result.get("operation_id") != context.get("operation_id"):
            return
        if result.get("ip_address") != context.get("ip"):
            self._cleanup_reachability_operation(context, restore=True)
            return
        if not self._is_reachability_context_current(context):
            self._cleanup_reachability_operation(context, restore=True)
            return
        if not result.get("reachable"):
            self._cleanup_reachability_operation(context, restore=False)
            self.hide_progress_dialog()
            self.set_ui_state(
                UIState.DISCONNECTED,
                f"Нет соединения с IP {context['ip']}",
            )
            QMessageBox.warning(self, "Внимание", "Ping неуспешен")
            self._restore_refresh_button()
            return
        snapshot = self._take_diagnostic_credential_snapshot(context)
        self._current_reachability_context = None
        self._current_reachability_worker = None
        self._release_reachability_presentation_owner(context.get("operation_id"))
        if snapshot is None:
            self.hide_progress_dialog()
            self.set_ui_state(
                UIState.REQUEST_ERROR,
                "Не удалось запустить запрос: контекст credentials устарел",
            )
            self._restore_refresh_button()
            return
        self._continue_diagnostic_after_reachability(context, snapshot)

    def _prepare_diagnostic_credentials_before_reachability(
        self,
        *,
        device_name,
        ip_address,
        generation=None,
        operation_id=None,
        inventory_context=None,
    ):
        if generation is None:
            generation = self.__dict__.get("_diagnostic_action_generation", 0)
        if operation_id is None:
            operation_id = self._next_reachability_operation_id()
        if inventory_context is None:
            inventory_context = self._inventory_context_id()
        try:
            if self._is_pdu_device(device_name):
                candidates = self._resolve_pdu_attempt_credentials(
                    device_name,
                    ip_address,
                )
            else:
                candidates = self.device_credentials.get(device_name)
            frozen_candidates = self._freeze_credential_candidates(candidates)
            self._ensure_diagnostic_credential_candidates(
                device_name,
                frozen_candidates,
            )
            starting_successful_index = self.get_valid_current_credential_index(
                device_name,
                frozen_candidates,
                ip_address,
            )
            snapshot = DiagnosticCredentialSnapshot(
                diagnostic_model=device_name,
                ip_address=ip_address,
                candidates=frozen_candidates,
                starting_successful_index=starting_successful_index,
                diagnostic_generation=generation,
                reachability_operation_id=operation_id,
                inventory_context_identity=inventory_context,
            )
        except CredentialConfigurationError as error:
            message = str(error)
            self.set_ui_state(UIState.REQUEST_ERROR, message)
            self._restore_refresh_button()
            QMessageBox.warning(
                self,
                "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 credentials",
                message,
            )
            return None
        self._store_diagnostic_credential_snapshot(snapshot)
        return snapshot

    def _target_screen_for_diagnostic_context(self, context):
        device_type = context["screen_key"]
        if device_type == "codec":
            return self.screens["codec"]
        if device_type == "matrix":
            return self.screens["matrix"]
        if device_type == "audio_dsp":
            return self.screens["audio_dsp"]
        if device_type == "pdu":
            return self.screens["pdu"]
        return None

    def _continue_diagnostic_after_reachability(self, context, credential_snapshot):
        if not self._is_action_binding_current(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation=context["generation"],
            normalized_ip=context["ip"],
            binding_id=context["binding"],
        ):
            self._discard_diagnostic_credential_snapshot(context.get("operation_id"))
            return
        accepted_context = self._accept_diagnostic_model_context(
            normalized_ip=context["ip"],
            entry=context["entry"],
            source=context["source"],
            generation=context["generation"],
            binding=context["binding"],
        )
        if not self._is_action_binding_current(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation=context["generation"],
            normalized_ip=context["ip"],
            binding_id=context["binding"],
        ):
            return
        device_name = accepted_context["model"]
        ip_address = accepted_context["ip"]
        if self._is_pdu_device(device_name):
            self._pdu_controller().refresh_pdu(
                ip_address,
                device_name,
                credential_snapshot=credential_snapshot,
            )
            return

        device_type = accepted_context["screen_key"]
        target_screen = self._target_screen_for_diagnostic_context(accepted_context)
        if target_screen is None:
            self.set_ui_state(UIState.REQUEST_ERROR, "Неподдерживаемый экран диагностики")
            self._restore_refresh_button()
            return

        self._begin_request(device_name, ip_address, target_screen)
        self.screen_container.setCurrentWidget(target_screen)
        if device_type == "codec" and hasattr(target_screen, 'update_parameters_display'):
            target_screen.update_parameters_display()
        if hasattr(target_screen, 'clear_data'):
            target_screen.clear_data()
        elif hasattr(target_screen, 'update_data'):
            target_screen.update_data({"status": "loading", "message": "Загрузка данных…"})
        if hasattr(target_screen, "set_ui_state"):
            target_screen.set_ui_state(UIState.LOADING, "Загрузка данных…")
        self._publish_current_equipment_room_context("request_started")
        self._publish_current_equipment_switch_context("request_started", force=True)

        if device_name == "Huawei TE40":
            self.refresh_huawei_te40(ip_address, credential_snapshot=credential_snapshot)
        elif device_name in {"CloudLink Bar 310", "CloudLink Box 310"}:
            self.refresh_huawei_bar310(ip_address, credential_snapshot=credential_snapshot)
        elif device_name == "Huawei TE20":
            self.refresh_huawei_te20(ip_address, credential_snapshot=credential_snapshot)
        elif device_name == "Polycom RPG 310":
            self.refresh_polycom_rpg310(ip_address, credential_snapshot=credential_snapshot)
        elif device_name == "Extron IN1804":
            self.refresh_extron_in1804(ip_address, credential_snapshot=credential_snapshot)
        elif device_name == "Biamp Tesira Forte CI":
            self.refresh_biamp_tesira_forte_ci(ip_address, credential_snapshot=credential_snapshot)
        elif device_name == "Extron DMP 64 Plus":
            self.refresh_extron_dmp64_plus(ip_address, credential_snapshot=credential_snapshot)
        elif device_type == "matrix":
            self.refresh_matrix_data(ip_address, credential_snapshot=credential_snapshot)
        else:
            QMessageBox.information(
                self,
                "Информация",
                f"Support for {device_name} will be added later"
            )

    def is_vcs_codec_device(self, device_name: str) -> bool:
        return self.device_to_screen.get(device_name) == "codec"

    def is_authentication_error(self, error_type: str, error_message: str) -> bool:
        message = str(error_message).lower()
        return (
            error_type == "authentication_error"
            or "authentication" in message
            or "аутентификац" in message
            or "авторизац" in message
            or "auth" in message
            or "401" in message
            or "403" in message
            or "16781315" in message
            or "100666780" in message
        )

    def refresh_data(self):
        """Resolve current IP to one exact model and submit reachability off the GUI thread."""
        ip_address = self._normalized_current_ip_or_warn()
        if ip_address is None:
            return

        self._supersede_pending_diagnostic_reachability("new_diagnostic_start")
        generation = self._next_action_generation(DiagnosticActionPurpose.DIAGNOSTIC_START)
        test_context = self.__dict__.get("_active_diagnostic_model_context") or {}
        if test_context.get("source") == "TEST_CONTEXT":
            entry = dispatch_entry_for_model(test_context.get("model"))
            source = "TEST_CONTEXT"
            binding = self._accepted_action_binding(
                purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                generation=generation,
                normalized_ip=ip_address,
                resolution_status="TEST_CONTEXT",
                source=source,
                entry=entry,
            ) if entry is not None else None
        else:
            resolution = self._resolve_model_for_action(
                DiagnosticActionPurpose.DIAGNOSTIC_START,
                ip_address,
            )
            if resolution.resolved:
                entry = resolution.entry
                source = "AUTO_INVENTORY"
                binding = self._accepted_action_binding(
                    purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                    generation=generation,
                    normalized_ip=ip_address,
                    resolution_status=resolution.status.value,
                    source=source,
                    entry=entry,
                )
            else:
                fallback_result = self._open_model_fallback(
                    purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                    generation=generation,
                    normalized_ip=ip_address,
                    resolution=resolution,
                )
                source = "MANUAL_FALLBACK"
                if fallback_result is None:
                    entry = None
                    binding = None
                else:
                    entry, binding = fallback_result
        if entry is None or binding is None:
            self.set_ui_state(UIState.IDLE, "Модель устройства не выбрана")
            return

        if not self._is_action_binding_current(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation=generation,
            normalized_ip=ip_address,
            binding_id=binding,
        ):
            return
        if entry.screen_key not in {"codec", "matrix", "pdu", "audio_dsp"}:
            self.set_ui_state(UIState.REQUEST_ERROR, "Неподдерживаемый экран диагностики")
            return
        if entry.screen_key not in self.screens:
            self.set_ui_state(UIState.REQUEST_ERROR, "Экран диагностики недоступен")
            return

        device_name = entry.diagnostic_model
        operation_id = self._next_reachability_operation_id()
        snapshot = self._prepare_diagnostic_credentials_before_reachability(
            device_name=device_name,
            ip_address=ip_address,
            generation=generation,
            operation_id=operation_id,
            inventory_context=binding.inventory_context_identity,
        )
        if snapshot is None:
            return
        if not self._is_action_binding_current(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation=generation,
            normalized_ip=ip_address,
            binding_id=binding,
        ):
            self._discard_diagnostic_credential_snapshot(operation_id)
            return

        self._submit_reachability_check(
            {
                "purpose": DiagnosticActionPurpose.DIAGNOSTIC_START.value,
                "generation": generation,
                "operation_id": operation_id,
                "binding": binding,
                "ip": ip_address,
                "entry": entry,
                "model": device_name,
                "screen_key": entry.screen_key,
                "lifecycle_route": entry.lifecycle_route,
                "source": source,
                "resolution_status": binding.resolution_status,
                "inventory_context": binding.inventory_context_identity,
            }
        )


    def refresh_biamp_tesira_forte_ci(
        self,
        ip_address: str,
        *,
        credential_snapshot=None,
        creds_list=None,
        current_idx=None,
    ):
        """Refresh Biamp Tesira Forte CI read-only audio-DSP status."""
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Invalid IP", "Enter a valid IP address.")
            return

        device_name = self.current_device_name()
        creds_list = (
            tuple(creds_list or ())
            or self._snapshot_credential_candidates(
                credential_snapshot,
                device_name,
                ip_address,
            )
            or self.device_credentials.get(device_name)
        )
        current_idx = (
            current_idx
            if current_idx is not None
            else self._snapshot_credential_index(
                credential_snapshot,
                device_name,
                creds_list,
                ip_address,
            )
        )
        creds = creds_list[current_idx]
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Connecting...")

        self.show_progress_dialog(f"Connecting to {device_name} (attempt {current_idx + 1}/{len(creds_list)})...")
        self.show_codec_poll_terminal(device_name, ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))

        try:
            self.current_worker = BiampTesiraForteCIWorker(
                ip_address=ip_address,
                **creds,
            )
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            self.current_worker.credential_snapshot_identity = (
                credential_snapshot.identity if credential_snapshot is not None else None
            )
            self.current_worker.credential_snapshot_operation_id = (
                credential_snapshot.reachability_operation_id
                if credential_snapshot is not None
                else None
            )

            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)

            QThreadPool.globalInstance().start(self.current_worker)
        except Exception as e:
            self._fail_request_start(e)
            QMessageBox.critical(self, "Error", f"Could not create worker: {str(e)}")
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_extron_dmp64_plus(self, ip_address: str, *, credential_snapshot=None):
        """Compatibility delegate for Extron DMP 64 Plus polling."""
        return self._dmp_controller().refresh(
            ip_address,
            credential_snapshot=credential_snapshot,
        )


    def refresh_huawei_bar310(
        self,
        ip_address: str,
        *,
        credential_snapshot=None,
        creds_list=None,
        current_idx=None,
    ):
        """Start one Bar 310 attempt with the GUI-selected credential."""
        print(f"=== Начинаю обновление Huawei CloudLink Bar 310 для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для Bar 310
        device_name = self.current_device_name()
        creds_list = (
            tuple(creds_list or ())
            or self._snapshot_credential_candidates(
                credential_snapshot,
                device_name,
                ip_address,
            )
            or self.device_credentials.get(device_name)
        )
        
        # Создаем worker с текущими credentials
        current_idx = (
            current_idx
            if current_idx is not None
            else self._snapshot_credential_index(
                credential_snapshot,
                device_name,
                creds_list,
                ip_address,
            )
        )
        creds = creds_list[current_idx]
        # Отключаем кнопку
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")
        
        # Показываем прогресс
        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        self.show_codec_poll_terminal(device_name, ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))
        
        try:
            from core.worker import HuaweiBar310Worker
            
            # The full list is request context for redaction; the worker uses only **creds.
            self.current_worker = HuaweiBar310Worker(
                ip_address=ip_address,
                port=self.huawei_settings.get('port', 443),
                **creds,
                creds_list=creds_list,
                assigned_model=device_name,
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            self.current_worker.credential_snapshot_identity = (
                credential_snapshot.identity if credential_snapshot is not None else None
            )
            self.current_worker.credential_snapshot_operation_id = (
                credential_snapshot.reachability_operation_id
                if credential_snapshot is not None
                else None
            )
            
            # Подключаем сигналы
            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker для Huawei CloudLink Bar 310 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_huawei_te20(
        self,
        ip_address: str,
        *,
        credential_snapshot=None,
        creds_list=None,
        current_idx=None,
    ):
        """Start one TE20 attempt with the GUI-selected credential."""
        print(f"=== Начинаю обновление TE-20 для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для TE-20
        device_name = self.current_device_name()
        creds_list = (
            tuple(creds_list or ())
            or self._snapshot_credential_candidates(
                credential_snapshot,
                device_name,
                ip_address,
            )
            or self.device_credentials.get(device_name)
        )

        # Создаем worker с текущими credentials
        current_idx = (
            current_idx
            if current_idx is not None
            else self._snapshot_credential_index(
                credential_snapshot,
                device_name,
                creds_list,
                ip_address,
            )
        )
        creds = creds_list[current_idx]
        
        
        # Отключаем кнопку
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")
        
        # Показываем прогресс
        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        self.show_te20_terminal(ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))
        
        try:
            from core.te20_worker import HuaweiTE20Worker
            
            self.current_worker = HuaweiTE20Worker(
                ip_address=ip_address,
                port=80,  # TE-20 использует HTTP порт 80
                preferred_profile=self.get_device_connection_profile(
                    device_name, ip_address
                ),
                **creds,
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            self.current_worker.credential_snapshot_identity = (
                credential_snapshot.identity if credential_snapshot is not None else None
            )
            self.current_worker.credential_snapshot_operation_id = (
                credential_snapshot.reachability_operation_id
                if credential_snapshot is not None
                else None
            )
            
            # Подключаем сигналы
            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_te20_terminal_log)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker TE-20 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_huawei_te40(
        self,
        ip_address: str,
        *,
        credential_snapshot=None,
        creds_list=None,
        current_idx=None,
    ):
        """Обновление данных Huawei TE40 с перебором credentials"""
        print(f"=== Начинаю обновление для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для TE-40
        device_name = self.current_device_name()
        creds_list = (
            tuple(creds_list or ())
            or self._snapshot_credential_candidates(
                credential_snapshot,
                device_name,
                ip_address,
            )
            or self.device_credentials.get(device_name)
        )
        
        # Создаем worker с текущими credentials
        current_idx = (
            current_idx
            if current_idx is not None
            else self._snapshot_credential_index(
                credential_snapshot,
                device_name,
                creds_list,
                ip_address,
            )
        )
        creds = creds_list[current_idx]
        
        
        # Отключаем кнопку
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")
        
        # Показываем прогресс
        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        self.show_codec_poll_terminal(device_name, ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))
        
        try:
            from core.worker import HuaweiTE40Worker
            
            self.current_worker = HuaweiTE40Worker(
                ip_address=ip_address,
                port=self.huawei_settings.get('port', 443),
                preferred_profile=self.get_device_connection_profile(
                    device_name, ip_address
                ),
                **creds,
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            self.current_worker.credential_snapshot_identity = (
                credential_snapshot.identity if credential_snapshot is not None else None
            )
            self.current_worker.credential_snapshot_operation_id = (
                credential_snapshot.reachability_operation_id
                if credential_snapshot is not None
                else None
            )
            
            # Подключаем сигналы
            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_polycom_rpg310(
        self,
        ip_address: str,
        *,
        credential_snapshot=None,
        creds_list=None,
        current_idx=None,
    ):
        """Обновление данных Polycom RPG 310 с перебором credentials"""
        print(f"=== Начинаю обновление Polycom RPG 310 для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для Polycom
        device_name = self.current_device_name()
        creds_list = (
            tuple(creds_list or ())
            or self._snapshot_credential_candidates(
                credential_snapshot,
                device_name,
                ip_address,
            )
            or self.device_credentials.get(device_name)
        )
        
        # Создаем worker с текущими credentials
        current_idx = (
            current_idx
            if current_idx is not None
            else self._snapshot_credential_index(
                credential_snapshot,
                device_name,
                creds_list,
                ip_address,
            )
        )
        creds = creds_list[current_idx]
        
        
        # Отключаем кнопку
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")
        
        # Показываем прогресс
        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        self.show_codec_poll_terminal(device_name, ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))
        
        try:
            from core.worker import PolycomRPG310Worker
            
            self.current_worker = PolycomRPG310Worker(
                ip_address=ip_address,
                port=443,
                **creds,
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            self.current_worker.credential_snapshot_identity = (
                credential_snapshot.identity if credential_snapshot is not None else None
            )
            self.current_worker.credential_snapshot_operation_id = (
                credential_snapshot.reachability_operation_id
                if credential_snapshot is not None
                else None
            )
            
            # Подключаем сигналы
            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker для Polycom RPG 310 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_extron_in1804(
        self,
        ip_address: str,
        *,
        credential_snapshot=None,
        creds_list=None,
        current_idx=None,
    ):
        """Обновление данных Extron IN1804 с перебором credentials"""
        print(f"=== Начинаю обновление Extron IN1804 для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        device_name = self.current_device_name()
        creds_list = (
            tuple(creds_list or ())
            or self._snapshot_credential_candidates(
                credential_snapshot,
                device_name,
                ip_address,
            )
            or self.device_credentials.get(device_name)
        )

        current_idx = (
            current_idx
            if current_idx is not None
            else self._snapshot_credential_index(
                credential_snapshot,
                device_name,
                creds_list,
                ip_address,
            )
        )

        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")

        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        self.show_matrix_terminal(ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))

        try:
            self.matrix_controller.request_full_refresh(
                ip_address,
                creds_list,
                current_idx,
            )
            print("MatrixController full refresh submitted")
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_aten_pdu(self, ip_address: str):
        """Start one Aten PDU attempt with the GUI-selected credential."""
        self.refresh_pdu(ip_address, "Aten PE8208AV")

    def refresh_pdu(self, ip_address: str, device_name: str = None):
        """Start one model-aware PDU refresh attempt in a background worker."""
        return self._pdu_controller().refresh_pdu(ip_address, device_name)
    
    def _bind_pdu_refresh_worker(self, worker, descriptor):
        self._pdu_controller()._bind_refresh_worker(worker, descriptor)

    def on_pdu_refresh_result(self, data, worker, descriptor):
        self._pdu_controller().on_refresh_result(data, worker, descriptor)

    def on_pdu_refresh_error(self, error_info, worker, descriptor):
        self._pdu_controller().on_refresh_error(error_info, worker, descriptor)

    def on_pdu_refresh_progress(self, progress, worker, descriptor):
        self._pdu_controller().on_refresh_progress(progress, worker, descriptor)

    def on_pdu_refresh_status(self, status, worker, descriptor):
        self._pdu_controller().on_refresh_status(status, worker, descriptor)

    def on_pdu_refresh_finished(self, worker, descriptor):
        self._pdu_controller().on_refresh_finished(worker, descriptor)

    def control_pdu_outlet(self, outlet_num: int, command: str):
        """Submit a PDU outlet command without blocking the GUI thread."""
        return self._pdu_controller().request_individual_mutation(outlet_num, command)

    def _start_pdu_command_retry_worker(
        self,
        *,
        descriptor,
        creds_list,
        current_idx,
    ):
        self._pdu_controller().start_command_retry_worker(
            descriptor=descriptor,
            creds_list=creds_list,
            current_idx=current_idx,
        )

    def _pdu_context_is_current(self, descriptor: PDUOperationDescriptor) -> bool:
        return self._pdu_controller().is_descriptor_common_current(descriptor)

    def _remember_pdu_outlet_context(self, data, descriptor: PDUOperationDescriptor) -> None:
        self._pdu_controller().remember_outlet_context(data, descriptor)

    def _current_pdu_outlet_records(self, device_name: str, ip_address: str):
        return self._pdu_controller().current_outlet_records(device_name, ip_address)

    def _is_current_pdu_mutation_active(self) -> bool:
        return self._pdu_controller().is_mutation_active()

    def _set_pdu_mutation_busy(
        self,
        descriptor: PDUOperationDescriptor,
        kind: str,
        busy: bool,
    ) -> None:
        screen = getattr(self, "screens", {}).get("pdu")
        self._pdu_controller().set_mutation_busy(descriptor, kind, busy)

    def _is_current_pdu_bulk_active(self) -> bool:
        return self._pdu_controller().is_mutation_active()

    def _set_pdu_command_busy(self, descriptor: PDUOperationDescriptor, busy: bool) -> None:
        self._pdu_controller().set_command_busy(descriptor, busy)

    def _set_pdu_bulk_busy(self, descriptor: PDUOperationDescriptor, busy: bool) -> None:
        self._set_pdu_mutation_busy(descriptor, "bulk", busy)

    def control_pdu_outlets_bulk(self, command: str):
        return self._pdu_controller().request_bulk_mutation(command)

    def _start_pdu_bulk_retry_worker(
        self,
        *,
        descriptor,
        creds_list,
        current_idx,
    ):
        self._pdu_controller().start_bulk_retry_worker(
            descriptor=descriptor,
            creds_list=creds_list,
            current_idx=current_idx,
        )

    def on_pdu_bulk_result(self, data, worker, descriptor):
        self._pdu_controller().on_bulk_result(data, worker, descriptor)

    def on_pdu_bulk_error(self, error_info, worker, descriptor):
        self._pdu_controller().on_bulk_error(error_info, worker, descriptor)

    def on_pdu_bulk_finished(self, worker, descriptor):
        self._pdu_controller().on_bulk_finished(worker, descriptor)

    def on_pdu_command_result(self, data, worker, descriptor):
        self._pdu_controller().on_command_result(data, worker, descriptor)

    def on_pdu_command_error(self, error_info, worker, descriptor):
        self._pdu_controller().on_command_error(error_info, worker, descriptor)

    def on_pdu_command_finished(self, worker, descriptor):
        self._pdu_controller().on_command_finished(worker, descriptor)


    def update_time_display(self):
        """Обновление отображения времени"""
        
        from PyQt5.QtCore import QDateTime
        
        if self.last_update_time and isinstance(self.last_update_time, QDateTime):
            current_time = QDateTime.currentDateTime()
            seconds = self.last_update_time.secsTo(current_time)
            
            if seconds < 60:
                time_text = "Только что"
            elif seconds < 3600:
                minutes = seconds // 60
                if minutes == 1:
                    time_text = "1 минуту назад"
                elif minutes < 5:
                    time_text = f"{minutes} минуты назад"
                else:
                    time_text = f"{minutes} минут назад"
            elif seconds < 86400:
                hours = seconds // 3600
                if hours == 1:
                    time_text = "1 час назад"
                elif hours < 5:
                    time_text = f"{hours} часа назад"
                else:
                    time_text = f"{hours} часов назад"
            else:
                days = seconds // 86400
                if days == 1:
                    time_text = "1 день назад"
                else:
                    time_text = f"{days} дней назад"
            
            self.time_display.setText(time_text)
        else:
            self.time_display.setText("Никогда")


    def on_device_data_received(self, data, worker=None, request_id=None):
        """Обработка полученных данных от устройства"""
        if request_id is not None and not self._request_is_current(request_id, worker):
            return
        worker = worker or getattr(self, "current_worker", None)
        data = dict(data)
        structured_outcome = data.pop('_outcome', None)
        credential_used = data.pop('_credential_used', None)
        credential_policy_handled = bool(data.pop('_credential_policy_handled', False))
        data.pop('_matrix_credential_success_candidate', None)
        continuous_update = bool(data.pop('_continuous_update', False))
        if structured_outcome == 'error':
            self.on_device_error(
                (
                    data.pop('error_type', 'connection_error'),
                    data.pop('error', data.pop('message', 'Worker request failed')),
                    data.pop('traceback', ''),
                ),
                worker,
                request_id,
            )
            return
        partial_update = bool(data.pop('_partial_update', False))
        if not partial_update:
            self.hide_progress_dialog()
        if not partial_update and self.current_device_name() == "Extron IN1804":
            self.finish_matrix_terminal("Опрос завершён успешно")
        elif not partial_update and self.current_device_name() == "Huawei TE20":
            self.finish_te20_terminal("Опрос завершён успешно")

        meaningful_keys = [
            key for key, value in data.items()
            if key != 'ip_address' and value not in (None, '', {}, [], 'N/A', 'Не доступно')
        ]
        if not meaningful_keys:
            screen = (self._active_request or {}).get("screen")
            self.set_ui_state(
                UIState.UNAVAILABLE,
                "Устройство ответило, но доступных значений нет",
                screen,
            )
            QMessageBox.warning(
                self,
                "Нет данных",
                "Устройство ответило, но полезные данные для отображения не получены.\n"
                "Проверьте API/протокол подключения для выбранной модели."
            )
            return
        
        # Сбрасываем индекс на успешный credentials для этого устройства
        if (
            worker
            and not partial_update
            and credential_used is not False
            and not credential_policy_handled
            and not VCSDiagnosticApp._is_pdu_device(getattr(worker, 'device_name', None))
            and not VCSDiagnosticApp._is_dmp_device(getattr(worker, 'device_name', None))
        ):
            device_name = getattr(worker, 'device_name', None)
            current_idx = getattr(worker, 'current_idx', 0)
            if device_name:
                self.set_current_credential_index(device_name, current_idx, data.get('ip_address', self.ip_entry.text()))
                VCSDiagnosticApp._discard_credential_attempt_plan(
                    self,
                    device_name,
                    data.get('ip_address', self.ip_entry.text()),
                )
                connection_profile = data.get('connection_profile')
                if isinstance(connection_profile, dict) and connection_profile:
                    self.set_device_connection_profile(
                        device_name,
                        connection_profile,
                        data.get('ip_address', self.ip_entry.text())
                    )
                print(f"Запомнен успешный credentials #{current_idx + 1} для {device_name}")
        
        # Обновляем данные на текущем экране
        current_screen = (self._active_request or {}).get("screen")
        if current_screen is None and hasattr(self, 'current_screen_type'):
            current_screen = self.screens.get(self.current_screen_type)
        if current_screen:
            current_screen.update_data(data)
        
        from PyQt5.QtCore import QDateTime
        self.last_update_time = QDateTime.currentDateTime()
        self.update_time_display()
        if partial_update:
            self.set_ui_state(
                UIState.LOADING,
                "Получены частичные данные; запрос продолжается…",
            )
            if (
                worker
                and getattr(worker, 'device_name', None) == "Polycom RPG 310"
            ):
                if self.progress_dialog is None:
                    self.show_progress_dialog("Подключение по SSH для дополнительных параметров...")
                if self.progress_dialog is not None:
                    self.progress_dialog.setRange(0, 100)
                    self.progress_dialog.setValue(60)
                    self.progress_dialog.setLabelText("Подключение по SSH для дополнительных параметров...")
                    self.progress_dialog.show()
                    self.progress_dialog.raise_()
                    self.progress_dialog.activateWindow()
            return

        self.set_ui_state(
            UIState.CONNECTED,
            "Соединение установлено; данные обновлены",
        )

        if continuous_update:
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")
            return

        if getattr(self, 'suppress_success_message_once', False):
            self.suppress_success_message_once = False
            return

        device_name = self.current_device_name()
        message_text = (
            f"Данные для {device_name} успешно получены\n"
            f"IP: {data.get('ip_address', self.ip_entry.text())}"
        )
        protocol = data.get('connection_protocol')
        if protocol:
            message_text += f"\nПротокол: {protocol}"

        QMessageBox.information(
            self,
            "Данные получены",
            message_text
        )

   
    def on_device_error(self, error_info, worker=None, request_id=None):
        """Обработка ошибок от устройства с автоматическим перебором credentials"""
        if request_id is not None and not self._request_is_current(request_id, worker):
            return
        worker = worker or getattr(self, "current_worker", None)
        active_request_id = request_id
        if active_request_id is None:
            active_request_id = (self._active_request or {}).get("id")
        unhandled = object()
        if worker and getattr(
            worker, "_device_error_handled_request", unhandled
        ) == active_request_id:
            return
        if worker:
            worker._device_error_handled_request = active_request_id
        error_type = error_info[0]
        error = error_info[1]
        traceback_text = error_info[2] if len(error_info) > 2 else ""
        if worker and VCSDiagnosticApp._is_pdu_device(getattr(worker, 'device_name', None)):
            self.hide_progress_dialog()
            self.set_ui_state(UIState.REQUEST_ERROR, f"Ошибка PDU: {error}")
            return
        creds_list = getattr(worker, 'creds_list', []) if worker else []
        if (
            worker
            and getattr(worker, 'device_name', None) == MATRIX_DEVICE_NAME
            and not creds_list
        ):
            creds_list = self._matrix_credential_candidates(
                MATRIX_DEVICE_NAME,
                getattr(worker, 'ip_address', None),
            )
        error = redact_exception(
            error,
            VCSDiagnosticApp._credential_secrets(creds_list),
        )
        if worker and getattr(worker, 'device_name', None) == "Extron IN1804":
            self.finish_matrix_terminal(f"Опрос завершён с ошибкой: {error}")
        elif worker and getattr(worker, 'device_name', None) == "Huawei TE20":
            self.finish_te20_terminal(f"Опрос завершён с ошибкой: {error}")
        elif worker and getattr(worker, 'device_name', None) == DMP_DEVICE_NAME:
            self.finish_codec_terminal(f"Опрос завершён с ошибкой: {error}")
        
        # Проверяем, есть ли текущий worker и нужно ли пробовать другие credentials
        if worker:
            device_name = getattr(worker, 'device_name', None)
            current_idx = getattr(worker, 'current_idx', 0)
            if VCSDiagnosticApp._is_dmp_device(device_name):
                uses_request_plan = False
                is_auth_error = False
            else:
                error_message = str(error)
                uses_request_plan = VCSDiagnosticApp._uses_request_scoped_credential_retry(
                    self, device_name
                )
                is_auth_error = VCSDiagnosticApp._is_structured_retry_authentication_error(
                    self, device_name, error_type, error_message
                )
            
            # Если это ошибка аутентификации и есть еще credentials для проверки
            if (
                not VCSDiagnosticApp._is_dmp_device(device_name)
                and is_auth_error
                and creds_list
                and current_idx < len(creds_list) - 1
            ):
                
                # Переходим к следующему credentials
                next_idx = current_idx + 1
                if uses_request_plan:
                    next_idx = VCSDiagnosticApp._advance_request_credential_attempt(
                        self,
                        device_name,
                        creds_list,
                        getattr(worker, 'ip_address', None),
                        current_idx,
                    )
                else:
                    self.set_current_credential_index(
                        device_name, next_idx, getattr(worker, 'ip_address', None)
                    )

                if next_idx is None:
                    VCSDiagnosticApp._discard_credential_attempt_plan(
                        self,
                        device_name,
                        getattr(worker, 'ip_address', None),
                    )
                else:
                    print(f"Ошибка аутентификации. Пробуем следующие credentials ({next_idx + 1}/{len(creds_list)})...")
                
                    # Скрываем текущий прогресс диалог
                    self.hide_progress_dialog()
                    self.set_ui_state(
                        UIState.LOADING,
                        f"Ошибка авторизации; попытка {next_idx + 1} из {len(creds_list)}…",
                    )
                
                    # Повторяем попытку с новыми credentials
                    if device_name == "Huawei TE40":
                        self.refresh_huawei_te40(
                            worker.ip_address,
                            creds_list=creds_list,
                            current_idx=next_idx,
                        )
                    elif device_name in {"CloudLink Bar 310", "CloudLink Box 310"}:
                        self.refresh_huawei_bar310(
                            worker.ip_address,
                            creds_list=creds_list,
                            current_idx=next_idx,
                        )
                    elif device_name == "Huawei TE20":
                        self.refresh_huawei_te20(
                            worker.ip_address,
                            creds_list=creds_list,
                            current_idx=next_idx,
                        )
                    elif device_name == "Polycom RPG 310":
                        self.refresh_polycom_rpg310(
                            worker.ip_address,
                            creds_list=creds_list,
                            current_idx=next_idx,
                        )
                    elif device_name == "Extron IN1804":
                        self.refresh_extron_in1804(
                            worker.ip_address,
                            creds_list=creds_list,
                            current_idx=next_idx,
                        )
                    elif device_name == "Aten PE8208AV":
                        self.refresh_aten_pdu(worker.ip_address)
                    elif device_name == "Extron IPL T PCS4i":
                        self.refresh_pdu(worker.ip_address, device_name)
                    elif device_name == "Biamp Tesira Forte CI":
                        self.refresh_biamp_tesira_forte_ci(
                            worker.ip_address,
                            creds_list=creds_list,
                            current_idx=next_idx,
                        )
                    return
                      
        
        # Если нет других credentials или ошибка не связана с аутентификацией
        self.hide_progress_dialog()
        
        error_message = str(error)
        device_name = getattr(worker, 'device_name', None) or self.current_device_name()
        if VCSDiagnosticApp._is_dmp_device(device_name):
            is_auth_error = error_type == CodecFailureCategory.AUTHENTICATION.value
        else:
            is_auth_error = VCSDiagnosticApp._is_structured_retry_authentication_error(
                self, device_name, error_type, error_message
            )
        VCSDiagnosticApp._discard_credential_attempt_plan(
            self,
            device_name,
            getattr(worker, 'ip_address', None) if worker else None,
        )

        if is_auth_error and self.is_vcs_codec_device(device_name):
            user_message = "Авторизация неуспешна"
        elif "Connection refused" in error_message or "timed out" in error_message:
            user_message = "Не удалось подключиться к устройству.\nПроверьте:\n1. IP адрес\n2. Сетевое подключение\n3. Порт устройства"
        elif is_auth_error:
            user_message = "Авторизация неуспешна"
        elif "SSL" in error_message:
            user_message = "Ошибка SSL соединения.\nПопробуйте отключить проверку SSL сертификата."
        else:
            user_message = f"Ошибка: {error_message}"
        
        if is_auth_error:
            self.set_ui_state(
                UIState.AUTH_ERROR,
                "Ошибка авторизации: проверьте учётные данные",
                (self._active_request or {}).get("screen"),
            )
            QMessageBox.warning(
                self,
                "Авторизация",
                user_message
            )
        else:
            self.set_ui_state(
                UIState.REQUEST_ERROR,
                f"Ошибка запроса: {error_message}",
                (self._active_request or {}).get("screen"),
            )
            QMessageBox.critical(
                self,
                "Ошибка подключения",
                user_message
            )
        
        # Включаем кнопку обратно
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
    
    def on_progress_update(self, progress, worker=None, request_id=None):
        """Обработка обновления прогресса"""
        if request_id is not None and not self._request_is_current(request_id, worker):
            return
        if self.progress_dialog is not None:
            try:
                if self.progress_dialog.maximum() == 0:
                    self.progress_dialog.setRange(0, 100)
                self.progress_dialog.setValue(progress)
                try:
                    if progress < 100:
                        self.progress_dialog.setLabelText(f"Прогресс: {progress}%")
                except AttributeError:
                    # setLabelText уже не работает, но setValue сработал
                    pass
                if (
                    progress >= 68
                    and worker
                    and getattr(worker, 'device_name', None) == "Polycom RPG 310"
                ):
                    self.progress_dialog.show()
                    self.progress_dialog.raise_()
                    self.progress_dialog.activateWindow()
            except AttributeError:
                # Диалог уже закрыт
                self.progress_dialog = None                 
    
    def on_status_update(self, status, worker=None, request_id=None):
        """Обработка обновления статуса"""
        if request_id is not None and not self._request_is_current(request_id, worker):
            return
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setLabelText(status)
        if self.ui_state in {UIState.LOADING, UIState.COMMAND}:
            self.set_connection_status("loading", status)
        print(f"Status: {status}")
    
    def on_worker_finished(self, worker=None, request_id=None):
        """Обработка завершения работы Worker"""
        if request_id is not None and not self._request_is_current(request_id, worker):
            return
        self.hide_progress_dialog()
        
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
    

    def on_progress_canceled(self):
        """Обработка отмены прогресса"""
        print("Operation cancelled by user")
        self.hide_progress_dialog()
    
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
    

    
    def show_success_message(self, message: str):
        """Показать сообщение об успехе"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Данные обновлены")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec_()

    def generate_matrix_data(self):
        """Генерация тестовых данных для матрицы"""
        return {
            "Температура": f"{random.randint(35, 55)}°C",
            "Версия прошивки": f"{random.randint(1, 5)}.{random.randint(0, 9)}",
            "Время работы": f"{random.randint(1, 365)} дней"
        }

    def show_password_dialog(self):
        """Показать диалог ввода логина и пароля."""
        normalized_ip = self._normalized_current_ip_or_warn()
        if normalized_ip is None:
            return
        generation = self._next_action_generation(
            DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION
        )
        resolution = self._resolve_model_for_action(
            DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            normalized_ip,
        )
        if resolution.resolved:
            entry = resolution.entry
            source = "AUTO_INVENTORY"
            binding = self._accepted_action_binding(
                purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
                generation=generation,
                normalized_ip=normalized_ip,
                resolution_status=resolution.status.value,
                source=source,
                entry=entry,
            )
        else:
            fallback_result = self._open_model_fallback(
                purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
                generation=generation,
                normalized_ip=normalized_ip,
                resolution=resolution,
            )
            source = "MANUAL_FALLBACK"
            if fallback_result is None:
                entry = None
                binding = None
            else:
                entry, binding = fallback_result
        if entry is None or binding is None:
            return
        if not self._is_action_binding_current(
            purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation=generation,
            normalized_ip=normalized_ip,
            binding_id=binding,
        ):
            return
        credential_dialog_id = self._next_credential_dialog_id()
        dialog_binding = self._accepted_action_binding(
            purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation=generation,
            normalized_ip=normalized_ip,
            resolution_status=binding.resolution_status,
            source=source,
            entry=entry,
            fallback_dialog_id=binding.fallback_dialog_id,
            credential_dialog_id=credential_dialog_id,
        )
        self._publish_current_dialog_binding("credential_dialog", dialog_binding)
        if not self._is_action_binding_current(
            purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation=generation,
            normalized_ip=normalized_ip,
            binding_id=dialog_binding,
        ):
            return

        device_name = entry.diagnostic_model
        self._active_credential_configuration_context = {
            "purpose": DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION.value,
            "generation": generation,
            "binding": dialog_binding,
            "binding_id": dialog_binding,
            "ip": normalized_ip,
            "model": device_name,
            "screen_key": entry.screen_key,
            "lifecycle_route": entry.lifecycle_route,
            "source": source,
            "resolution_status": dialog_binding.resolution_status,
            "fallback_dialog_id": dialog_binding.fallback_dialog_id,
            "credential_dialog_id": dialog_binding.credential_dialog_id,
            "inventory_context": dialog_binding.inventory_context_identity,
        }
        password_only = self._is_pcs4i_device(device_name)
        default_username = self.get_default_username_for_device(device_name)

        dialog = QDialog(self)
        dialog.setWindowTitle("Ввод нестандартных credentials")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        prompt_text = (
            f"Введите пароль для {device_name}:\nIP: {self.ip_entry.text()}"
            if password_only
            else f"Введите логин и пароль для {device_name}:\nIP: {self.ip_entry.text()}"
        )
        info_label = QLabel(prompt_text)
        info_label.setWordWrap(True)

        form_layout = QFormLayout()
        username_entry = QLineEdit()
        username_entry.setText(default_username)
        password_entry = QLineEdit()
        password_entry.setEchoMode(QLineEdit.Password)

        if not password_only:
            form_layout.addRow("Логин:", username_entry)
        form_layout.addRow("Пароль:", password_entry)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout.addWidget(info_label)
        layout.addLayout(form_layout)
        layout.addWidget(buttons)

        dialog.resize(420, 220)
        if dialog.exec_() != QDialog.Accepted:
            self._clear_current_dialog_binding("credential_dialog", dialog_binding)
            return
        if not self._is_action_binding_current(
            purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation=generation,
            normalized_ip=normalized_ip,
            binding_id=dialog_binding,
        ):
            self._clear_current_dialog_binding("credential_dialog", dialog_binding)
            return

        username = username_entry.text().strip()
        password = password_entry.text()

        if not password or (not password_only and not username):
            message = (
                "Заполните пароль."
                if password_only
                else "Заполните и логин, и пароль."
            )
            QMessageBox.warning(self, "Внимание", message)
            self._clear_current_dialog_binding("credential_dialog", dialog_binding)
            return

        new_credential = (
            {'password': password}
            if password_only
            else {'username': username, 'password': password}
        )
        inserted = self.configure_credential_candidate(
            device_name,
            normalized_ip,
            new_credential,
        )

        if inserted:
            message_title = "Успех"
            message_text = (
                f"Credentials для {device_name} успешно сохранены\n"
                f"Логин и пароль будут использованы при следующем подключении"
            )
        else:
            message_title = "Информация"
            message_text = (
                f"Такие credentials для {device_name} уже есть в списке\n"
                f"Логин и пароль будут использованы при следующем подключении"
            )

        if password_only:
            message_text = (
                f"Credentials для {device_name} успешно сохранены\n"
                "Пароль будет использован при следующем подключении"
            )
        QMessageBox.information(self, message_title, message_text)
        if password_only:
            print(f"Настроены password-only credentials для {device_name}")
        else:
            print(f"Настроены credentials для {device_name}")
        self._clear_current_dialog_binding("credential_dialog", dialog_binding)

    def get_default_username_for_device(self, device_name):
        """Вернуть логин по умолчанию для устройства."""
        default_username = 'admin'
        if device_name == "Aten PE8208AV":
            default_username = 'admin'
        elif device_name == "Polycom RPG 310":
            default_username = 'admin'
        elif device_name == "Extron IN1804":
            default_username = 'admin'
        return default_username

    def lighten_color(self, hex_color, percent):
        """Осветлить HEX цвет на указанный процент"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = min(255, int(r + (255 - r) * percent / 100))
        g = min(255, int(g + (255 - g) * percent / 100))
        b = min(255, int(b + (255 - b) * percent / 100))
        
        return f'#{r:02x}{g:02x}{b:02x}'


    def fix_sip_huawei_te40(self, ip_address: str):
        """Исправление SIP регистрации для Huawei TE40"""
        print(f"Исправление SIP регистрации для TE-40 на {ip_address}")
        
        # Жёстко заданный SIP сервер
        sip_server = "link.ru"
        
        # Показываем диалог прогресса
        self.show_progress_dialog(f"Установка SIP сервера {sip_server}...")
        
        try:
            # Получаем текущие credentials
            device_name = "Huawei TE40"
            creds_list = self.device_credentials.get(device_name, [])
            if not creds_list:
                raise CredentialConfigurationError("Credentials are required before setting a SIP server.")
            current_idx = self.get_valid_current_credential_index(
                device_name, creds_list, ip_address
            )
            creds = creds_list[current_idx]
            
            # Создаем worker для установки SIP
            from core.worker import HuaweiTE40Worker
            
            self.fix_worker = HuaweiTE40Worker(
                ip_address=ip_address,
                port=self.huawei_settings.get('port', 443),
                username=creds['username'],
                password=creds['password']
            )
            
            # Подключаем сигналы
            self.fix_worker.signals.result.connect(self.on_sip_fix_result)
            self.fix_worker.signals.error.connect(self.on_sip_fix_error)
            self.fix_worker.signals.status.connect(self.on_status_update)
            self.fix_worker.signals.finished.connect(self.on_worker_finished)
            
            # Запускаем установку SIP сервера
            QThreadPool.globalInstance().start(self.fix_worker)
            self.fix_worker.set_sip_server(sip_server)
            
        except Exception as e:
            self.hide_progress_dialog()
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить SIP сервер: {str(e)}")

  
    @pyqtSlot(dict)
    def on_sip_fix_result(self, result):
        """Обработка результата установки SIP сервера"""
        self.hide_progress_dialog()
        
        if result.get('action') == 'set_sip_server':
            if result.get('success'):
                QMessageBox.information(
                    self,
                    "Успех",
                    result.get('message', 'SIP сервер успешно установлен')
                )
                # Обновляем данные после успешной установки
                self.refresh_data()
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    result.get('message', 'Не удалось установить SIP сервер')
                )
    
    @pyqtSlot(tuple)
    def on_sip_fix_error(self, error_info):
        """Обработка ошибки установки SIP сервера"""
        self.hide_progress_dialog()
        error_type, error, traceback_text = error_info
        
        QMessageBox.critical(
            self,
            "Ошибка",
            f"Не удалось установить SIP сервер:\n{str(error)}"
        )



    def on_fix_sip_registration(self, ip_address: str, device_name: str):
        """Обработчик нажатия кнопки 'Исправить' для SIP регистрации"""
        print(f"=== Нажата кнопка Исправить для {device_name} ({ip_address}) ===")
        
        # Жёстко заданный SIP сервер
        sip_server = "link.ru"
        
        # Показываем диалог с вопросом
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы действительно хотите установить SIP сервер\n"
            f"{sip_server}\n\n"
            f"на устройстве {device_name}?\nIP: {ip_address}\n\n"
            f"Это действие может занять несколько секунд.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # В зависимости от типа устройства вызываем соответствующий метод
            if device_name == "Huawei TE40":
                self.fix_sip_huawei_te40(ip_address)
            elif device_name == "CloudLink Bar 310":
                # TODO: реализовать для Bar 310
                QMessageBox.information(self, "Информация", "Поддержка Bar 310 будет добавлена позже")
            elif device_name == "Huawei TE20":
                # TODO: реализовать для TE-20
                QMessageBox.information(self, "Информация", "Поддержка TE-20 будет добавлена позже")
            elif device_name == "Polycom RPG 310":
                # TODO: реализовать для Polycom
                QMessageBox.information(self, "Информация", "Поддержка Polycom будет добавлена позже")
            else:
                QMessageBox.information(
                    self,
                    "Информация",
                    f"Исправление SIP регистрации для {device_name} будет добавлено позже"
                )


    def fix_sip_huawei_te40(self, ip_address: str):
        """Исправление SIP регистрации для Huawei TE40"""
        print(f"\n=== fix_sip_huawei_te40 called ===")
        print(f"IP Address: {ip_address}")
        
        sip_server = "link.ru"
        print(f"SIP Server to set: {sip_server}")
        
        self.show_progress_dialog(f"Установка SIP сервера {sip_server}...")
        
        try:
            # Получаем текущие credentials
            device_name = "Huawei TE40"
            creds_list = self.device_credentials.get(device_name, [])
            if not creds_list:
                raise CredentialConfigurationError("Credentials are required before setting a SIP server.")
            current_idx = self.get_valid_current_credential_index(
                device_name, creds_list, ip_address
            )
            creds = creds_list[current_idx]
            
            # Создаем worker для установки SIP
            from core.worker import HuaweiTE40Worker
            
            self.fix_worker = HuaweiTE40Worker(
                ip_address=ip_address,
                port=self.huawei_settings.get('port', 443),
                username=creds['username'],
                password=creds['password']
            )
            
            print(f"Worker created for {ip_address}:{self.huawei_settings.get('port', 443)}")
            
            # Подключаем сигналы
            self.fix_worker.signals.result.connect(self.on_sip_fix_result)
            self.fix_worker.signals.error.connect(self.on_sip_fix_error)
            self.fix_worker.signals.status.connect(self.on_status_update)
            self.fix_worker.signals.finished.connect(self.on_worker_finished)
            
            print("Starting worker...")
            # Запускаем установку SIP сервера
            QThreadPool.globalInstance().start(self.fix_worker)
            self.fix_worker.set_sip_server(sip_server)
            print("Worker started")
            
        except Exception as e:
            print(f"Error in fix_sip_huawei_te40: {e}")
            import traceback
            traceback.print_exc()
            self.hide_progress_dialog()
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить SIP сервер: {str(e)}")
    
    
    
        def fix_sip_huawei_bar310(self, ip_address: str):
            """Исправление SIP регистрации для CloudLink Bar 310"""
            print(f"Исправление SIP регистрации для Bar 310 на {ip_address}")
            self.show_progress_dialog("Исправление SIP регистрации...")
            
            # TODO: Реализовать для Bar 310
            import time
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.on_fix_complete(True, "SIP регистрация успешно исправлена"))
    
    def fix_sip_huawei_te20(self, ip_address: str):
        """Исправление SIP регистрации для Huawei TE20"""
        print(f"Исправление SIP регистрации для TE-20 на {ip_address}")
        self.show_progress_dialog("Исправление SIP регистрации...")
        
        # TODO: Реализовать для TE-20
        import time
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.on_fix_complete(True, "SIP регистрация успешно исправлена"))
    
    def fix_sip_polycom_rpg310(self, ip_address: str):
        """Исправление SIP регистрации для Polycom RPG 310"""
        print(f"Исправление SIP регистрации для Polycom RPG 310 на {ip_address}")
        self.show_progress_dialog("Исправление SIP регистрации...")
        
        # TODO: Реализовать для Polycom
        import time
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.on_fix_complete(True, "SIP регистрация успешно исправлена"))
    
    def on_fix_complete(self, success: bool, message: str):
        """Обработчик завершения исправления SIP"""
        self.hide_progress_dialog()
        
        if success:
            QMessageBox.information(self, "Успех", message)
            # После успешного исправления обновляем данные
            self.refresh_data()
        else:
            QMessageBox.critical(self, "Ошибка", message)    
            
            
    @pyqtSlot(dict)
    def on_sip_fix_result(self, result):
        """Обработка результата установки SIP сервера."""
        self.hide_progress_dialog()
        self._set_sip_fix_busy(False)

        if result.get('action') == 'set_sip_server':
            if result.get('success'):
                self.set_ui_state(UIState.CONNECTED, "Команда SIP выполнена")
                QMessageBox.information(
                    self,
                    "Успех",
                    result.get('message', 'SIP сервер успешно установлен')
                )
                self.refresh_data()
            else:
                self.set_ui_state(
                    UIState.REQUEST_ERROR,
                    result.get('message', 'Не удалось установить SIP сервер'),
                )
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    result.get('message', 'Не удалось установить SIP сервер')
                )

    @pyqtSlot(tuple)
    def on_sip_fix_error(self, error_info):
        """Обработка ошибки установки SIP сервера."""
        self.hide_progress_dialog()
        self._set_sip_fix_busy(False)
        error_type, error, traceback_text = error_info
        self.set_ui_state(UIState.REQUEST_ERROR, f"Ошибка команды SIP: {error}")

        QMessageBox.critical(
            self,
            "Ошибка",
            f"Не удалось установить SIP сервер:\n{str(error)}"
        )

    def on_fix_sip_registration(self, ip_address: str, device_name: str):
        """Обработчик нажатия кнопки 'Исправить' для SIP регистрации."""
        print(f"=== Нажата кнопка Исправить для {device_name} ({ip_address}) ===")

        sip_server = "link.ru"
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы действительно хотите установить SIP сервер\n"
            f"{sip_server}\n\n"
            f"на устройстве {device_name}?\nIP: {ip_address}\n\n"
            f"Это действие может занять несколько секунд.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        if device_name == "Huawei TE40":
            self.fix_sip_huawei_te40(ip_address)
        elif device_name in {"CloudLink Bar 310", "CloudLink Box 310"}:
            self.fix_sip_huawei_bar310(ip_address, device_name)
        elif device_name == "Huawei TE20":
            QMessageBox.information(self, "Информация", "Поддержка TE-20 будет добавлена позже")
        elif device_name == "Polycom RPG 310":
            self.fix_sip_polycom_rpg310(ip_address)
        else:
            QMessageBox.information(
                self,
                "Информация",
                f"Исправление SIP регистрации для {device_name} будет добавлено позже"
            )

    def _get_sip_fix_connection_params(self, device_name: str, ip_address: str):
        """Подготовить параметры подключения для SIP fix."""
        if device_name == "Huawei TE40":
            port = self.huawei_settings.get('port', 443)
        elif device_name in {"CloudLink Bar 310", "CloudLink Box 310"}:
            port = self.huawei_settings.get('port', 443)
        elif device_name == "Polycom RPG 310":
            port = 22
        else:
            raise ValueError(f"SIP fix не поддерживается для {device_name}")

        creds_list = self.device_credentials.get(device_name, [])
        if not creds_list:
            raise CredentialConfigurationError(
                "Credentials are required before setting a SIP server."
            )
        current_idx = self.get_valid_current_credential_index(
            device_name, creds_list, ip_address
        )
        creds = creds_list[current_idx]

        return port, current_idx, creds

    def _start_sip_fix(self, device_name: str, ip_address: str):
        """Запустить установку SIP сервера в фоновом потоке."""
        sip_server = "link.ru"
        port, current_idx, creds = self._get_sip_fix_connection_params(device_name, ip_address)

        self.set_ui_state(UIState.COMMAND, "Установка SIP-сервера…")
        self._set_sip_fix_busy(True)
        self.show_progress_dialog(f"Установка SIP сервера {sip_server}...")
        self.show_codec_poll_terminal(device_name, ip_address, current_idx + 1, 1, reset=True)

        self.fix_worker = CodecSipFixWorker(
            device_name=device_name,
            ip_address=ip_address,
            port=port,
            username=creds['username'],
            password=creds['password'],
            sip_server=sip_server,
        )
        self.fix_worker.signals.result.connect(self.on_sip_fix_result)
        self.fix_worker.signals.error.connect(self.on_sip_fix_error)
        self.fix_worker.signals.status.connect(self.on_status_update)
        self.fix_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
        self.fix_worker.signals.finished.connect(self.on_worker_finished)
        QThreadPool.globalInstance().start(self.fix_worker)

    def _set_sip_fix_busy(self, busy: bool):
        codec_screen = self.screens.get("codec") if hasattr(self, "screens") else None
        for entry in getattr(codec_screen, "sip_fix_buttons", []):
            button = entry[1] if isinstance(entry, tuple) else entry
            if hasattr(button, "set_loading"):
                button.set_loading(busy, "Выполнение…")
            else:
                button.setEnabled(not busy)

    def fix_sip_huawei_te40(self, ip_address: str):
        """Исправление SIP регистрации для Huawei TE40."""
        creds = {}
        try:
            _port, _current_idx, creds = self._get_sip_fix_connection_params(
                "Huawei TE40", ip_address
            )
            self._start_sip_fix("Huawei TE40", ip_address)
        except Exception as error:
            secrets = (creds.get("username"), creds.get("password"))
            safe_error = redact_exception(error, secrets)
            safe_traceback = redact_text(traceback.format_exc(), secrets)
            print(f"SIP fix failed: {safe_error}")
            print(safe_traceback)
            self.hide_progress_dialog()
            self._set_sip_fix_busy(False)
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не удалось установить SIP сервер. Проверьте настройки подключения.",
            )

    def fix_sip_huawei_bar310(
        self, ip_address: str, device_name: str = "CloudLink Bar 310"
    ):
        """Исправление SIP регистрации для CloudLink Bar 310."""
        self._start_sip_fix(device_name, ip_address)

    def fix_sip_polycom_rpg310(self, ip_address: str):
        """Исправление SIP регистрации для Polycom RPG 310."""
        self._start_sip_fix("Polycom RPG 310", ip_address)

    def show_progress_dialog(self, message: str):
        """Показать диалог прогресса"""
        from PyQt5.QtWidgets import QProgressDialog

        if getattr(self, 'suppress_progress_dialog_once', False):
            self.suppress_progress_dialog_once = False
            return
        
        self.progress_dialog = QProgressDialog(message, "Отмена", 0, 100, self)
        self.progress_dialog.setWindowTitle("Выполнение операции")
        self.progress_dialog.setWindowModality(Qt.NonModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.setValue(0)
        self.progress_dialog.setCancelButton(None)  # Отключаем кнопку отмены пока
        self.progress_dialog.show()
        self.progress_dialog.raise_()
        self.progress_dialog.activateWindow()
    
    def hide_progress_dialog(self):
        """Скрыть диалог прогресса"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None         

    def show_matrix_terminal(self, ip_address: str, attempt_no: int, total_attempts: int, reset: bool = True):
        if not hasattr(self, 'matrix_terminal_dialog') or self.matrix_terminal_dialog is None:
            self.matrix_terminal_dialog = MatrixTerminalDialog(self.colors, self)

        title = f"Терминал Extron IN1804 - {ip_address}"
        if reset:
            self.matrix_terminal_dialog.reset_session(title)
            self.matrix_terminal_dialog.append_line(f"[session] start {ip_address}")
        else:
            self.matrix_terminal_dialog.setWindowTitle(title)
        self.matrix_terminal_dialog.append_line(f"[session] attempt {attempt_no}/{total_attempts}")

    @pyqtSlot(str)
    def on_terminal_log(self, message: str):
        if hasattr(self, 'matrix_terminal_dialog') and self.matrix_terminal_dialog:
            self.matrix_terminal_dialog.append_line(message)

    def finish_matrix_terminal(self, message: str):
        if hasattr(self, 'matrix_terminal_dialog') and self.matrix_terminal_dialog:
            self.matrix_terminal_dialog.append_line(f"[session] {message}")

    def show_te20_terminal(self, ip_address: str, attempt_no: int, total_attempts: int, reset: bool = True):
        if not hasattr(self, 'te20_terminal_dialog') or self.te20_terminal_dialog is None:
            self.te20_terminal_dialog = MatrixTerminalDialog(self.colors, self)

        title = f"Терминал Huawei TE20 - {ip_address}"
        if reset:
            self.te20_terminal_dialog.reset_session(title)
            self.te20_terminal_dialog.append_line(f"[session] start {ip_address}")
        else:
            self.te20_terminal_dialog.setWindowTitle(title)
        self.te20_terminal_dialog.append_line(f"[session] attempt {attempt_no}/{total_attempts}")

    @pyqtSlot(str)
    def on_te20_terminal_log(self, message: str):
        if hasattr(self, 'te20_terminal_dialog') and self.te20_terminal_dialog:
            self.te20_terminal_dialog.append_line(message)

    def finish_te20_terminal(self, message: str):
        if hasattr(self, 'te20_terminal_dialog') and self.te20_terminal_dialog:
            self.te20_terminal_dialog.append_line(f"[session] {message}")

    def show_codec_poll_terminal(self, device_name: str, ip_address: str, attempt_no: int, total_attempts: int, reset: bool = True):
        if not hasattr(self, 'codec_terminal_dialog') or self.codec_terminal_dialog is None:
            self.codec_terminal_dialog = MatrixTerminalDialog(self.colors, self)

        title = f"Терминал {device_name} - {ip_address}"
        if reset:
            self.codec_terminal_dialog.reset_session(title)
            self.codec_terminal_dialog.append_line(f"[session] start {ip_address}")
        else:
            self.codec_terminal_dialog.setWindowTitle(title)
        self.codec_terminal_dialog.append_line(f"[session] attempt {attempt_no}/{total_attempts}")

    @pyqtSlot(str)
    def on_codec_poll_terminal_log(self, message: str):
        if hasattr(self, 'codec_terminal_dialog') and self.codec_terminal_dialog:
            self.codec_terminal_dialog.append_line(message)

    def show_codec_terminal(self, device_name: str, ip_address: str, action: str, reset: bool = True):
        if not hasattr(self, 'codec_terminal_dialog') or self.codec_terminal_dialog is None:
            self.codec_terminal_dialog = MatrixTerminalDialog(self.colors, self)

        title = f"Терминал управления презентацией - {device_name} - {ip_address}"
        if reset:
            self.codec_terminal_dialog.reset_session(title)
            self.codec_terminal_dialog.append_line(f"[session] start {ip_address}")
            self.codec_terminal_dialog.append_line(f"[session] action presentation {action}")
        else:
            self.codec_terminal_dialog.setWindowTitle(title)

    def append_codec_terminal_line(self, message: str):
        if hasattr(self, 'codec_terminal_dialog') and self.codec_terminal_dialog:
            self.codec_terminal_dialog.append_line(message)

    def finish_codec_terminal(self, message: str):
        if hasattr(self, 'codec_terminal_dialog') and self.codec_terminal_dialog:
            self.codec_terminal_dialog.append_line(f"[session] {message}")

    def show_debug_window(self):
        device_name = self.current_device_name()
        ip_address = self.ip_entry.text().strip()

        if device_name == "Huawei TE20":
            if not hasattr(self, 'te20_terminal_dialog') or self.te20_terminal_dialog is None:
                self.te20_terminal_dialog = MatrixTerminalDialog(self.colors, self)
                self.te20_terminal_dialog.setWindowTitle(f"Терминал Huawei TE20 - {ip_address}")
            dialog = self.te20_terminal_dialog
        elif device_name == "Extron IN1804":
            if not hasattr(self, 'matrix_terminal_dialog') or self.matrix_terminal_dialog is None:
                self.matrix_terminal_dialog = MatrixTerminalDialog(self.colors, self)
                self.matrix_terminal_dialog.setWindowTitle(f"Терминал Extron IN1804 - {ip_address}")
            dialog = self.matrix_terminal_dialog
        else:
            if not hasattr(self, 'codec_terminal_dialog') or self.codec_terminal_dialog is None:
                self.codec_terminal_dialog = MatrixTerminalDialog(self.colors, self)
                self.codec_terminal_dialog.setWindowTitle(
                    f"Терминал управления устройством - {device_name} - {ip_address}"
                )
            dialog = self.codec_terminal_dialog

        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def closeEvent(self, event):
        self._supersede_model_actions("shutdown")
        controller = self.__dict__.get("pdu_room_codec_enrichment_controller")
        if controller is not None:
            controller.shutdown()
        self._dmp_controller().shutdown()
        codec_screen = self.screens.get("codec") if hasattr(self, "screens") else None
        if codec_screen and hasattr(codec_screen, "shutdown_interactive_controller"):
            codec_screen.shutdown_interactive_controller()
        elif codec_screen and hasattr(codec_screen, "reset_volume_session"):
            codec_screen.reset_volume_session()
        self.matrix_controller.shutdown()
        self._pdu_controller().shutdown()
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        super().closeEvent(event)
            
