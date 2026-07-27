# Graph Report - diag-module-ref@7e83d303dd99  (2026-07-27)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3106 nodes · 8563 edges · 121 communities (92 shown, 29 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1099 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Bootstrap Frozen Baseline Policy
- Built from source commit: `7e83d303dd997f59987d5007fff9ea56b7d10efc`
- Indexed source ref: `origin/master`
- Target branch: `master`
- Stage: bootstrap, pre-archive, non-final.
- This frozen project baseline verifies the initial Graphify integration, wrapper, corpus filters, security scans, smoke queries, and reproducibility.
- This graph is not the navigation baseline for the next change.
- Do not rebuild or incrementally update the graph during active implementation, review, testing, or validation.
- Read `RULES.md`, `docs/project-graph-runbook.md`, and `graphify-out/baseline.json`.
- Compare `indexed_source_commit` with the current branch and analyze the branch diff separately.
- Build the final baseline only after independent review, archive, and post-archive validation.

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 111
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118

## God Nodes (most connected - your core abstractions)
1. `VCSDiagnosticApp` - 230 edges
2. `AuthenticationError` - 158 edges
3. `DeviceClass` - 145 edges
4. `ConnectionError` - 118 edges
5. `CodecScreen` - 112 edges
6. `PolycomRPG310Handler` - 98 edges
7. `HuaweiTE40Handler` - 97 edges
8. `InteractiveOperation` - 86 edges
9. `HuaweiTE20Handler` - 86 edges
10. `PDUOperationDescriptor` - 79 edges

## Surprising Connections (you probably didn't know these)
- `AtenPDUHandler` --uses--> `ProtocolHandler`  [INFERRED]
  handlers/aten/pdu.py → core/base_handler.py
- `CloudLinkBar310Handler` --uses--> `BaseHuaweiCodecHandler`  [INFERRED]
  handlers/huawei/bar310.py → core/base_handler.py
- `CloudLinkBox300Handler` --uses--> `BaseHuaweiCodecHandler`  [INFERRED]
  handlers/huawei/box300.py → core/base_handler.py
- `HuaweiTE20Handler` --uses--> `BaseHuaweiCodecHandler`  [INFERRED]
  handlers/huawei/te20.py → core/base_handler.py
- `HuaweiTE40Handler` --uses--> `BaseHuaweiCodecHandler`  [INFERRED]
  handlers/huawei/te40.py → core/base_handler.py

## Import Cycles
- None detected.

## Communities (121 total, 29 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (60): EquipmentInventory, EquipmentInventoryLoadError, EquipmentInventoryMetadata, Exception, Structured inventory load failure safe for application consumers., CodecFailureCategory, Stable retry/recovery authority for codec refresh and interactive paths., OperationSemantic (+52 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (36): Проверить, установлено ли соединение, An established codec session is no longer accepted by the device., SessionInvalidError, _Context, _credential_identity(), _default_handler_factory(), _disconnect(), _emit_signal() (+28 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (60): application_root(), _canonical_nullable_string(), _canonical_required_string(), compute_snapshot_id(), default_snapshot_path(), EquipmentRecord, _freeze_index(), _invalid_snapshot() (+52 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (24): HuaweiTE40Handler, Any, Exception, Проверка текущего адреса SIP сервера                  Returns:             str:, Return one authoritative sleep/audio sample for interactive polling., Разбудить устройство из режима сна., Получить текущий статус презентации., Return authoritative TE40 microphone mute state for reconciliation. (+16 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (28): Reusable, device-agnostic widgets for the diagnostic GUI., configure_button(), EmptyState, ExclusiveActionGroup, ParameterRow, QLabel, QWidget, Small reusable widgets styled by :mod:`gui.theme`.  The components intentionally (+20 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (39): classify_codec_failure(), Classify a caught typed failure without inspecting human-readable text., Remove sensitive fields recursively without mutating application data., Wrap a public logging/debug callback without retaining a raw secret., redact_data(), redacted_callback(), Compatibility facade for public worker imports.  Worker implementations live in, BiampTesiraForteCIWorker (+31 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (7): PolycomRPG310Handler, Any, Handler for Polycom RealPresence Group 310 over HTTPS REST., HardwareLogRedactionTests, main(), parse_args(), Exercise Polycom GUI controls through SSH when Web UI sessions are full.  The sc

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (26): BaseHuaweiCodecHandler, Базовый класс для всех кодеков Huawei, Настройка HTTP сессии, Получить системную информацию, AuthenticationError, classify_matrix_failure(), ConnectionError, DeviceError (+18 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (10): Унифицированный запуск обновления из полей ввода., Переключение между экранами, Submit a PDU outlet command without blocking the GUI thread., Показать сообщение об успехе, Генерация тестовых данных для матрицы, Осветлить HEX цвет на указанный процент, Инициализация всех экранов, Запускать обновление по Enter на списке устройств. (+2 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (4): PDUScreen, Aten outlet status and control screen., Disable only the controls for the outlet being changed., PDUIntegrationScreenTests

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (9): HuaweiTE20Handler, Response, Decode TE20 responses as UTF-8 because the device often omits charset metadata., Parse JSON from raw response bytes to avoid requests charset guesswork., Return one authoritative sleep/audio sample for interactive polling., Разбудить устройство из режима сна., Получить текущий статус локальной презентации., Return authoritative TE20 microphone mute state for reconciliation. (+1 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (7): CommandRejectedError, The device authoritatively rejected the requested command., PDUOperationWorker, QRunnable, Background refresh/control worker for model-aware PDU operations., PDUOperationContractTests, ScriptedPDUHandler

### Community 16 - "Community 16"
Cohesion: 0.10
Nodes (20): HTTPAdapter, decode_response(), export_with_pycurl(), main(), post_action(), pycurl_request(), main(), parse_args() (+12 more)

### Community 18 - "Community 18"
Cohesion: 0.07
Nodes (14): Start one Aten PDU attempt with the GUI-selected credential., Start one model-aware PDU refresh attempt in a background worker., Обновление отображения времени, Обработка полученных данных от устройства, Обработка ошибок от устройства с автоматическим перебором credentials, Обработка обновления прогресса, Обработка обновления статуса, Обработка завершения работы Worker (+6 more)

### Community 19 - "Community 19"
Cohesion: 0.09
Nodes (16): AtenPDUHandler, Any, Response, Универсальная функция для запросов к API Aten PDU, Попытка аутентификации с перебором паролей, Обработчик для PDU Aten (серия PE), Получение информации об устройстве, Получение статуса всех розеток (+8 more)

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (25): The requested operation is not supported by the selected device., UnsupportedOperationError, build_pdu_bulk_outlet_sequence(), build_pdu_handler(), bulk_target_operation(), disconnect_quietly(), ensure_pdu_operation_supported(), _execute_absolute_outlet_policy() (+17 more)

### Community 22 - "Community 22"
Cohesion: 0.09
Nodes (18): _is_sensitive_key(), Any, BaseException, Reusable redaction helpers for public diagnostic boundaries., Prepare exception text and tracebacks for public error boundaries., Redact structured diagnostic text as well as Python containers., _redact_authorization_scheme(), redact_diagnostic() (+10 more)

### Community 23 - "Community 23"
Cohesion: 0.17
Nodes (3): MatrixController, MatrixOperationContext, Owns Matrix refresh, route, persistent session, and stale suppression.

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (9): ProtocolError, CloudLinkBar310Handler, Парсинг ответа от сервера с обработкой двойной сериализации, Обработчик для Huawei CloudLink Bar 310, Download and parse the latest CloudLink Bar 310 call records., Получить статус презентации, Разбудить устройство из режима сна., Установить SIP-сервер через тот же API, что и в референсном драйвере. (+1 more)

### Community 25 - "Community 25"
Cohesion: 0.08
Nodes (6): FakeCodecHandler, FakeDataApp, FakeMatrixHandler, main(), Launch the GUI with representative local data and no device I/O., VCSDiagnosticApp

### Community 26 - "Community 26"
Cohesion: 0.13
Nodes (11): BaseExtronMatrixHandler, Базовый класс для обработчиков матриц Extron, Установка TCP соединения с матрицей и аутентификация, Вход в Extron: ждем `login as:`, отправляем логин, ждем `Password:`, отправляем, Отправка команды и получение ответа, Чтение ответа от сокета, Читаем ответ, пока не появится одно из ожидаемых подстрок., MatrixAuthenticationError (+3 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (7): DMPAttemptState, DMPPollingContext, DMPPollingController, PendingDMPRetry, QThreadPool, DMP-specific application polling lifecycle controller., Owns DMP polling context, callback authority, and credential handoff.

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (11): ExtronIN1804Handler, Обработчик для видеоматрицы Extron IN1804, Получение статуса сигналов на входах, Получение HDCP информации для входов, Получение текущих коммутаций, Получение полного статуса матрицы, Установка коммутации (выход всегда 1 для этой модели), Получить полный статус устройства (+3 more)

### Community 29 - "Community 29"
Cohesion: 0.10
Nodes (3): HandlerSessionFailureTests, RaisingOpener, RequestsResponse

### Community 30 - "Community 30"
Cohesion: 0.12
Nodes (9): is_supported_dmp64_plus_variant(), require_assigned_credentials(), ExtronDMP64PlusHandler, _looks_like_paramiko_authentication(), _ParamikoDMPSession, Any, BaseException, Extron DMP 64 Plus SIS-over-SSH meter handler. (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.12
Nodes (14): CommandError, CommandOutcomeUnknownError, CredentialRequired, ParseError, The device requested a credential, but none was assigned for this attempt., Ошибка выполнения команды на устройстве, Ошибка парсинга данных, A state-changing command may have reached the device without a reply. (+6 more)

### Community 35 - "Community 35"
Cohesion: 0.13
Nodes (17): Credential, normalize_credential(), Any, Resolve an explicitly requested or device-mapped profile., Resolve ordered candidates while keeping single-provider compatibility., Validate direct caller/test injection with the same profile rules., Apply source priority: direct input, explicit profile, model mapping., Apply source priority and return all request-scoped candidates. (+9 more)

### Community 36 - "Community 36"
Cohesion: 0.15
Nodes (19): build_identity_command(), build_read_command(), build_recovery_command(), _channel_result(), dbfs_from_raw_meter(), DMPMeterChannel, DMPSessionPoisoned, DMPUnsupportedModel (+11 more)

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (3): ExtronIPLTPCS4iHandler, Any, Handler for PCS4i authoritative Telnet control and optional HTTP names.

### Community 38 - "Community 38"
Cohesion: 0.14
Nodes (13): BaseScreen, QWidget, Обновление данных экрана, Apply a shared state without replacing device-specific layouts., coerce_ui_state(), Enum, str, Shared semantic states for device screens and application operations. (+5 more)

### Community 39 - "Community 39"
Cohesion: 0.15
Nodes (12): Обновление данных в зависимости от устройства, Refresh Biamp Tesira Forte CI read-only audio-DSP status., Start one Bar 310 attempt with the GUI-selected credential., Start one TE20 attempt with the GUI-selected credential., Обновление данных Huawei TE40 с перебором credentials, Обновление данных Polycom RPG 310 с перебором credentials, Обновление данных Extron IN1804 с перебором credentials, Исправление SIP регистрации для Huawei TE20 (+4 more)

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (8): CallLogWindow, QDialog, Window for displaying the last codec call records., Fill the table with up to ten latest call records., Placeholder for device-specific call history commands., PasswordDialog, ReleaseUIOffscreenTest, SavedPasswordDisclosureRegressionTest

### Community 41 - "Community 41"
Cohesion: 0.11
Nodes (6): CodecScreen, Обработчик нажатия кнопки "Исправить" для SIP регистрации, Обновление отображения статуса презентации в GUI., Осветлить HEX цвет на указанный процент, Обновление данных экрана, Совместимый helper: разделение теперь задаёт общая тема строк.

### Community 43 - "Community 43"
Cohesion: 0.14
Nodes (16): order_codec_profiles(), _profile_key(), Any, Pure model/runtime codec transport ordering shared by all codec paths., Return the currently supported default profiles for one codec model., Put a supported saved profile first and deduplicate by port/SSL mode., supported_codec_profiles(), HuaweiTE20Worker (+8 more)

### Community 44 - "Community 44"
Cohesion: 0.15
Nodes (21): application_root(), CredentialProvider, default_credentials_path(), ABC, Path, Local credential profile resolution at the application/core boundary.  Only the, Replaceable source of resolved request-scoped credentials., Resolve the project root from this stable module path, never ``cwd``. (+13 more)

### Community 45 - "Community 45"
Cohesion: 0.18
Nodes (5): build_meter_snapshot(), DMPTransportSession, Serialized SIS transaction layer for one DMP SSH channel/session., DMPProtocolTests, FakeChannel

### Community 46 - "Community 46"
Cohesion: 0.10
Nodes (11): ProtocolFactory, Фабрика для создания обработчиков протоколов., Зарегистрировать новый обработчик, Создает обработчик протокола указанного типа, Получить список поддерживаемых устройств, Core package exports with lazy imports., AtenPDUDataParser, Парсер данных для PDU Aten (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.14
Nodes (10): BiampTesiraForteCIDataParser, Parser for Biamp Tesira Forte CI read-only audio-DSP status., BiampTesiraForteCIHandler, Collect read-only Input/Meter subscription values from Tesira TTP., Handler package exports with lazy imports., BiampGUIBoundaryTest, BiampHandlerParserTest, BiampMainWindowRoutingTest (+2 more)

### Community 48 - "Community 48"
Cohesion: 0.11
Nodes (13): ClickableImageWidget, load_database_excel(), load_database_json(), MainSchemeWindow, QWidget, Фильтрует список помещений в ComboBox на основе текста в поиске., Обновляет элементы в ComboBox, сохраняя текущий выбор, если возможно., Вызывается при выборе помещения в списке (клик или Enter). (+5 more)

### Community 49 - "Community 49"
Cohesion: 0.15
Nodes (17): _attributes_for_alias(), BiampSession, _is_candidate_source(), _is_error_response(), _is_output_alias(), _issue(), _parse_aliases(), _parse_scalar() (+9 more)

### Community 50 - "Community 50"
Cohesion: 0.16
Nodes (12): Queue, build_output_dir(), InteractivePlinkSession, main(), parse_args(), PlinkHelpCollector, prompt_value(), Namespace (+4 more)

### Community 51 - "Community 51"
Cohesion: 0.15
Nodes (12): CloudLinkBox300Handler, Any, Получить статус аудио, Получить статус видео, Вспомогательный метод для HTTP запросов, Установка соединения с CloudLink Box 300, Отправить команду устройству, Обработчик для Huawei CloudLink Box 300 (+4 more)

### Community 53 - "Community 53"
Cohesion: 0.19
Nodes (4): active_chain(), PolycomWorkerOutcomeTests, public_output(), TE40WorkerOutcomeTests

### Community 54 - "Community 54"
Cohesion: 0.11
Nodes (14): ExtronIN1804DataParser, Парсер данных для Extron IN1804, Преобразование сырых данных в формат для GUI, MatrixBackgroundOperation, _MatrixCleanupOperation, MatrixOperationFailure, MatrixOperationHandle, MatrixOperationSignals (+6 more)

### Community 55 - "Community 55"
Cohesion: 0.18
Nodes (3): Обновление отображения громкости в GUI, Обновление данных на экране, Преобразует строку вида '12' или '12%' в число.

### Community 56 - "Community 56"
Cohesion: 0.11
Nodes (8): QDialog, Compatibility delegate for Extron DMP 64 Plus polling., Показать диалог ввода пароля с кастомными стилями, Показать диалог ввода логина и пароля., Вернуть логин по умолчанию для устройства., Создание верхней панели с выпадающим списком и IP-адресом, Обработка изменения выбранного устройства, QLineEdit

### Community 60 - "Community 60"
Cohesion: 0.21
Nodes (5): active_chain(), Bar310CredentialRetryOwnershipTests, collect_outcomes(), RemainingProductionWorkerRetryOwnershipTests, TE20CredentialRetryOwnershipTests

### Community 61 - "Community 61"
Cohesion: 0.20
Nodes (9): build_output_dir(), main(), parse_args(), prompt_value(), Namespace, Path, SSHHelpCollector, strip_ansi() (+1 more)

### Community 62 - "Community 62"
Cohesion: 0.11
Nodes (3): Return one finite request cursor without mutating successful-index memory., Обновление IP адреса для выбранного устройства, Resolve all candidates once before any worker or handler is created.

### Community 64 - "Community 64"
Cohesion: 0.14
Nodes (9): DMPCancellationToken, DMPCancelled, The application-owned polling context was cancelled or superseded., Small thread-safe cancellation handle owned by the composition layer., wait_cancelable(), ExtronDMP64PlusMeterWorker, QRunnable, Long-lived DMP 64 Plus physical meter polling worker. (+1 more)

### Community 65 - "Community 65"
Cohesion: 0.13
Nodes (6): Исправление SIP регистрации для Huawei TE40, Обработчик нажатия кнопки 'Исправить' для SIP регистрации, Исправление SIP регистрации для Polycom RPG 310, Подготовить параметры подключения для SIP fix., Запустить установку SIP сервера в фоновом потоке., Исправление SIP регистрации для CloudLink Bar 310.

### Community 66 - "Community 66"
Cohesion: 0.17
Nodes (4): MatrixScreen, Reset displayed values without losing the selected route., Extron routing screen with the original switching contract., Publish a non-secret route intent.

### Community 68 - "Community 68"
Cohesion: 0.13
Nodes (9): Any, Получить информацию об устройстве, Получить системную информацию, Получить статус вызова, Получить статус аудио, Получить статус видео, Return TE20 HTTPS transport diagnostics before any network activity starts., Очистка строки версии от служебных символов (+1 more)

### Community 70 - "Community 70"
Cohesion: 0.16
Nodes (6): HuaweiTE40DataParser, Парсер данных для Huawei TE40, Парсинг сырых данных от Huawei кодеков, Очистка версии ПО - ИСПРАВЛЕНО, Преобразование статуса презентации, RequestLifecycleRegressionTests

### Community 71 - "Community 71"
Cohesion: 0.12
Nodes (5): EthernetClientInterface, EthernetClass, SerialClass, SerialOverEthernetClass, SerialInterface

### Community 72 - "Community 72"
Cohesion: 0.17
Nodes (3): AudioDSPScreen, Read-only Biamp signal status screen., BiampAudioDSPScreenTest

### Community 73 - "Community 73"
Cohesion: 0.14
Nodes (4): Submit desired presentation state without blocking the GUI thread., Возвращает актуальные credentials с учётом IP-специфичного индекса., Read speaker volume on the serialized background lane., Read microphone mute/gain on the serialized background lane.

### Community 75 - "Community 75"
Cohesion: 0.29
Nodes (3): JsonCredentialProvider, Version-one plain-text JSON provider using only the standard ``json`` module., JsonCredentialProviderTests

### Community 76 - "Community 76"
Cohesion: 0.19
Nodes (7): HuaweiBar310DataParser, Парсер данных для Huawei CloudLink Bar 310, Парсинг сырых данных от Huawei CloudLink Bar 310, Преобразование типа вызова, Преобразование состояния конференции, Преобразование режима сна, Преобразование статуса микрофона (для Bar 310: On - выключен, Off - включен)

### Community 77 - "Community 77"
Cohesion: 0.18
Nodes (6): ExtronIN1804Worker, QRunnable, Worker для опроса матрицы Extron IN1804, collect(), ExtronIN1804WorkerRuntimeTests, ProductionWorkerOutcomeContractTests

### Community 78 - "Community 78"
Cohesion: 0.18
Nodes (7): PolycomDataParser, Преобразование статуса SIP, Парсер данных для Polycom устройств, Парсинг сырых данных от Polycom устройств, Преобразование статуса Selfview, Преобразование настроек LAN, Преобразование статуса двух мониторов

### Community 79 - "Community 79"
Cohesion: 0.19
Nodes (3): Изменение громкости на 1 единицу, Submit an absolute target, preserving relative-button intent metadata., Возвращает текущее значение громкости из кеша или из отображаемой строки.

### Community 80 - "Community 80"
Cohesion: 0.17
Nodes (8): Any, Получить текст ошибки, Получение полного статуса устройства, Получить информацию об устройстве, Получить системную информацию, Получить статус вызова, Получить статус аудио, Получить статус видео

### Community 81 - "Community 81"
Cohesion: 0.22
Nodes (11): apply_theme(), build_stylesheet(), create_palette(), Central design tokens and the application-wide PyQt5 theme.  Widgets should sele, Apply the shared palette and QSS to a QApplication or QWidget., _handle_thread_exception(), _handle_unhandled_exception(), main() (+3 more)

### Community 83 - "Community 83"
Cohesion: 0.28
Nodes (14): build_action_path(), http_post(), load_credentials(), load_ip_list(), main(), parse_args(), parse_json(), ping_probe() (+6 more)

### Community 84 - "Community 84"
Cohesion: 0.08
Nodes (13): ProtocolHandler, ABC, Any, Получить статус вызова, Получить статус аудио, Получить статус видео, Абстрактный базовый класс для всех обработчиков протоколов, Установить соединение с устройством (+5 more)

### Community 85 - "Community 85"
Cohesion: 0.14
Nodes (4): Обработчик нажатия кнопки изменения громкости, Перестраивает карточки, сохраняя публичные ссылки на controls., Создаёт строки через общие компоненты этапа 4., Match firmware value edges to the two detail value columns.

### Community 86 - "Community 86"
Cohesion: 0.15
Nodes (3): _literal_assignment(), ThemeOffscreenSmokeTest, ThemeSourceContractTest

### Community 87 - "Community 87"
Cohesion: 0.17
Nodes (7): dict, Compatibility bridge for explicit UI/test credentials and the provider., Делегат для выравнивания заголовков по правому краю, Генерация тестовых данных для кодеков, RequestCredentialStore, RightAlignHeaderDelegate, QStyledItemDelegate

### Community 90 - "Community 90"
Cohesion: 0.18
Nodes (3): Cookies, Response, TE20CallLogExportTests

### Community 92 - "Community 92"
Cohesion: 0.23
Nodes (5): CandidateT, CredentialAttemptPlan, Finite monotonic request cursor; persistence remains a caller decision., Advance exactly once to an unattempted higher candidate, never wrap., Return the index a caller may commit after final confirmed success.

### Community 94 - "Community 94"
Cohesion: 0.18
Nodes (6): BiampSessionManager, _DefaultBiampSessionManager, BaseException, Connect through SSH first, then Telnet fallback., _safe_message(), Protocol

### Community 95 - "Community 95"
Cohesion: 0.24
Nodes (5): _clean_command_echo(), _clean_frame(), DMPStreamFramer, _echo_comparison_text(), Frame CR/LF-delimited PTY stream data and filter command echo.

### Community 98 - "Community 98"
Cohesion: 0.50
Nodes (3): DMPTransactionTimeout, A SIS transaction timed out; the current session must be abandoned., DeviceTimeoutError

### Community 99 - "Community 99"
Cohesion: 0.31
Nodes (4): HuaweiTE20DataParser, Парсер данных для Huawei TE20, Парсинг сырых данных от Huawei TE20 в формат, ожидаемый маппингом, Преобразование состояния mute микрофона TE-20 для отображения.

### Community 100 - "Community 100"
Cohesion: 0.22
Nodes (8): @fission-ai/openspec, description, devDependencies, @fission-ai/openspec, engines, node, name, private

### Community 102 - "Community 102"
Cohesion: 0.25
Nodes (4): Инициализация интерфейса, Создание виджета-заглушки с надписью Обновите данные, Apply the centralized theme for direct window construction., Создание панели времени обновления

### Community 103 - "Community 103"
Cohesion: 0.33
Nodes (5): ParserFactory, Any, Фабрика для получения парсера по типу устройства, Получить парсер для указанного типа устройства, Удобный метод для парсинга данных

### Community 104 - "Community 104"
Cohesion: 0.33
Nodes (3): QLabel, Compact round SIP registration state without an external icon pack., SIPRegistrationIndicator

### Community 108 - "Community 108"
Cohesion: 0.47
Nodes (5): build_legacy_context(), main(), parse_args(), Namespace, SSLContext

### Community 109 - "Community 109"
Cohesion: 0.60
Nodes (4): inspect_media_nodes(), main(), Inspect the Huawei endpoint UI without changing the diagnostic application.  Usa, visible_summary()

### Community 113 - "Community 113"
Cohesion: 0.50
Nodes (4): main(), parse_args(), Namespace, Run one sanitized, read-only GUI refresh against approved hardware.  The script

### Community 114 - "Community 114"
Cohesion: 0.67
Nodes (3): main(), Read Huawei endpoint SSH CLI help without changing configuration., receive()

## Knowledge Gaps
- **5 isolated node(s):** `name`, `private`, `description`, `@fission-ai/openspec`, `node`
  These have ≤1 connection - possible missing edges or undocumented components.
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VCSDiagnosticApp` connect `Community 9` to `Community 0`, `Community 6`, `Community 8`, `Community 13`, `Community 17`, `Community 18`, `Community 22`, `Community 23`, `Community 25`, `Community 27`, `Community 32`, `Community 35`, `Community 36`, `Community 38`, `Community 39`, `Community 40`, `Community 43`, `Community 44`, `Community 45`, `Community 46`, `Community 48`, `Community 56`, `Community 62`, `Community 63`, `Community 64`, `Community 65`, `Community 70`, `Community 74`, `Community 75`, `Community 81`, `Community 86`, `Community 87`, `Community 88`, `Community 92`, `Community 101`, `Community 102`, `Community 105`, `Community 110`, `Community 113`?**
  _High betweenness centrality (0.212) - this node is a cross-community bridge._
- **Why does `AuthenticationError` connect `Community 8` to `Community 0`, `Community 1`, `Community 3`, `Community 5`, `Community 6`, `Community 9`, `Community 12`, `Community 13`, `Community 14`, `Community 15`, `Community 19`, `Community 20`, `Community 24`, `Community 26`, `Community 28`, `Community 29`, `Community 30`, `Community 31`, `Community 36`, `Community 37`, `Community 43`, `Community 44`, `Community 45`, `Community 46`, `Community 47`, `Community 49`, `Community 53`, `Community 60`, `Community 64`, `Community 67`, `Community 77`, `Community 84`, `Community 87`, `Community 88`, `Community 94`, `Community 95`, `Community 97`, `Community 98`, `Community 106`?**
  _High betweenness centrality (0.167) - this node is a cross-community bridge._
- **Why does `ConnectionError` connect `Community 8` to `Community 0`, `Community 1`, `Community 3`, `Community 5`, `Community 6`, `Community 9`, `Community 14`, `Community 15`, `Community 19`, `Community 24`, `Community 26`, `Community 28`, `Community 30`, `Community 31`, `Community 36`, `Community 37`, `Community 42`, `Community 43`, `Community 44`, `Community 45`, `Community 47`, `Community 49`, `Community 63`, `Community 64`, `Community 84`, `Community 87`, `Community 88`, `Community 94`, `Community 95`, `Community 98`, `Community 106`, `Community 115`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `VCSDiagnosticApp` (e.g. with `CredentialAttemptPlan` and `JsonCredentialProvider`) actually correct?**
  _`VCSDiagnosticApp` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 87 inferred relationships involving `AuthenticationError` (e.g. with `BaseExtronMatrixHandler` and `BaseHuaweiCodecHandler`) actually correct?**
  _`AuthenticationError` has 87 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `ConnectionError` (e.g. with `BaseExtronMatrixHandler` and `BaseHuaweiCodecHandler`) actually correct?**
  _`ConnectionError` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `CodecScreen` (e.g. with `InteractiveOperation` and `InteractiveSessionController`) actually correct?**
  _`CodecScreen` has 6 INFERRED edges - model-reasoned connections that need verification._