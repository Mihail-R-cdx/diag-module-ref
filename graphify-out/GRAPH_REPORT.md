# Graph Report - frozen-project-graph-baseline-6108c852  (2026-07-26)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3122 nodes · 8590 edges · 120 communities (91 shown, 29 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1099 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e9cce86d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

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
- Community 21
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
- Community 34
- Community 35
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
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 67
- Community 69
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
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
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
- Community 106
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117

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

## Communities (120 total, 29 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (62): EquipmentInventory, EquipmentInventoryLoadError, EquipmentInventoryMetadata, EquipmentRecord, Exception, Structured inventory load failure safe for application consumers., CodecFailureCategory, Stable retry/recovery authority for codec refresh and interactive paths. (+54 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (38): classify_codec_failure(), CommandOutcomeUnknownError, Classify a caught typed failure without inspecting human-readable text., An established codec session is no longer accepted by the device., A state-changing command may have reached the device without a reply., SessionInvalidError, _Context, _credential_identity() (+30 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (33): CommandRejectedError, The requested operation is not supported by the selected device., The device authoritatively rejected the requested command., UnsupportedOperationError, build_pdu_bulk_outlet_sequence(), build_pdu_handler(), bulk_target_operation(), disconnect_quietly() (+25 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (19): CredentialRequired, DeviceError, DeviceNotFoundError, ParseError, Exception, Базовое исключение для ошибок устройств, The device requested a credential, but none was assigned for this attempt., Ошибка парсинга данных (+11 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (59): application_root(), _canonical_nullable_string(), _canonical_required_string(), compute_snapshot_id(), default_snapshot_path(), _freeze_index(), _invalid_snapshot(), inventory_from_document() (+51 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (36): CommandError, Ошибка выполнения команды на устройстве, BiampTesiraForteCIDataParser, Parser for Biamp Tesira Forte CI read-only audio-DSP status., _attributes_for_alias(), BiampSession, BiampSessionManager, BiampTesiraForteCIHandler (+28 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (7): PolycomRPG310Handler, Any, Handler for Polycom RealPresence Group 310 over HTTPS REST., HardwareLogRedactionTests, main(), parse_args(), Exercise Polycom GUI controls through SSH when Web UI sessions are full.  The

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (18): HuaweiTE20Handler, Any, Response, Получить информацию об устройстве, Получить системную информацию, Получить статус вызова, Decode TE20 responses as UTF-8 because the device often omits charset metadata., Получить статус аудио (+10 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (10): Унифицированный запуск обновления из полей ввода., Переключение между экранами, Submit a PDU outlet command without blocking the GUI thread., Показать сообщение об успехе, Генерация тестовых данных для матрицы, Осветлить HEX цвет на указанный процент, Инициализация всех экранов, Запускать обновление по Enter на списке устройств. (+2 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (23): ProtocolFactory, Фабрика для создания обработчиков протоколов., Зарегистрировать новый обработчик, Создает обработчик протокола указанного типа, Получить список поддерживаемых устройств, AtenPDUHandler, Any, Response (+15 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (21): Reusable, device-agnostic widgets for the diagnostic GUI., configure_button(), EmptyState, ExclusiveActionGroup, QLabel, QWidget, Small reusable widgets styled by :mod:`gui.theme`.  The components intentional, Colored status dot with optional adjacent text. (+13 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (4): PDUScreen, Aten outlet status and control screen., Disable only the controls for the outlet being changed., PDUIntegrationScreenTests

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (16): CloudLinkBar310Handler, Any, Парсинг ответа от сервера с обработкой двойной сериализации, Получить текст ошибки, Обработчик для Huawei CloudLink Bar 310, Download and parse the latest CloudLink Bar 310 call records., Получение полного статуса устройства, Получить информацию об устройстве (+8 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (25): is_pdu_bulk_operation(), _is_sensitive_key(), Any, BaseException, Reusable redaction helpers for public diagnostic boundaries., Remove sensitive fields recursively without mutating application data., Prepare exception text and tracebacks for public error boundaries., Redact structured diagnostic text as well as Python containers. (+17 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (29): Credential, CredentialProvider, normalize_credential(), ABC, Any, Local credential profile resolution at the application/core boundary.  Only th, Replaceable source of resolved request-scoped credentials., Resolve an explicitly requested or device-mapped profile. (+21 more)

### Community 20 - "Community 20"
Cohesion: 0.07
Nodes (14): Start one Aten PDU attempt with the GUI-selected credential., Start one model-aware PDU refresh attempt in a background worker., Обновление отображения времени, Обработка полученных данных от устройства, Обработка ошибок от устройства с автоматическим перебором credentials, Обработка обновления прогресса, Обработка обновления статуса, Обработка завершения работы Worker (+6 more)

### Community 21 - "Community 21"
Cohesion: 0.10
Nodes (12): ExtronIN1804Handler, Обработчик для видеоматрицы Extron IN1804, Получение статуса сигналов на входах, Получение HDCP информации для входов, Получение текущих коммутаций, Получение полного статуса матрицы, Установка коммутации (выход всегда 1 для этой модели), Получить полный статус устройства (+4 more)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (11): AuthenticationError, Ошибка аутентификации, ExtronIN1804Worker, QRunnable, Worker для опроса матрицы Extron IN1804, active_chain(), collect(), ExtronIN1804WorkerRuntimeTests (+3 more)

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (3): MatrixController, MatrixOperationContext, Owns Matrix refresh, route, persistent session, and stale suppression.

### Community 25 - "Community 25"
Cohesion: 0.10
Nodes (13): BaseHuaweiCodecHandler, Базовый класс для всех кодеков Huawei, Настройка HTTP сессии, Получить системную информацию, datetime, Обработчик для Huawei CloudLink Bar 310. Реализует протокол взаимодействия с ус, Handler package exports with lazy imports., HTTPAdapter (+5 more)

### Community 26 - "Community 26"
Cohesion: 0.08
Nodes (6): FakeCodecHandler, FakeDataApp, FakeMatrixHandler, main(), Launch the GUI with representative local data and no device I/O., VCSDiagnosticApp

### Community 27 - "Community 27"
Cohesion: 0.10
Nodes (13): HuaweiTE40DataParser, PolycomDataParser, Парсер данных для Huawei TE40, Парсинг сырых данных от Huawei кодеков, Очистка версии ПО - ИСПРАВЛЕНО, Преобразование статуса SIP, Преобразование статуса презентации, Парсер данных для Polycom устройств (+5 more)

### Community 28 - "Community 28"
Cohesion: 0.15
Nodes (7): DMPAttemptState, DMPPollingContext, DMPPollingController, PendingDMPRetry, QThreadPool, DMP-specific application polling lifecycle controller., Owns DMP polling context, callback authority, and credential handoff.

### Community 29 - "Community 29"
Cohesion: 0.10
Nodes (3): HandlerSessionFailureTests, RaisingOpener, RequestsResponse

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (11): BaseExtronMatrixHandler, Базовый класс для обработчиков матриц Extron, Установка TCP соединения с матрицей и аутентификация, Вход в Extron: ждем `login as:`, отправляем логин, ждем `Password:`, отправляем, Отправка команды и получение ответа, Чтение ответа от сокета, Читаем ответ, пока не появится одно из ожидаемых подстрок., MatrixAuthenticationError (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.12
Nodes (20): build_identity_command(), build_read_command(), build_recovery_command(), _channel_result(), _clean_command_echo(), _clean_frame(), dbfs_from_raw_meter(), DMPMeterChannel (+12 more)

### Community 32 - "Community 32"
Cohesion: 0.18
Nodes (6): ProtocolError, Return one authoritative sleep/audio sample for interactive polling., Разбудить устройство из режима сна., Получить текущий статус презентации., Return authoritative TE40 microphone mute state for reconciliation., Отправить команду устройству

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (23): Compatibility facade for public worker imports.  Worker implementations live i, BiampTesiraForteCIWorker, QRunnable, Read-only worker for Biamp Tesira Forte CI audio-DSP signal status., CodecSipFixWorker, QRunnable, Фоновый worker для установки SIP-сервера на поддерживаемых кодеках., PolycomCallLogWorker (+15 more)

### Community 37 - "Community 37"
Cohesion: 0.12
Nodes (17): order_codec_profiles(), _profile_key(), Any, Pure model/runtime codec transport ordering shared by all codec paths., Return the currently supported default profiles for one codec model., Put a supported saved profile first and deduplicate by port/SSL mode., supported_codec_profiles(), HuaweiTE20Worker (+9 more)

### Community 39 - "Community 39"
Cohesion: 0.15
Nodes (12): Обновление данных в зависимости от устройства, Refresh Biamp Tesira Forte CI read-only audio-DSP status., Start one Bar 310 attempt with the GUI-selected credential., Start one TE20 attempt with the GUI-selected credential., Обновление данных Huawei TE40 с перебором credentials, Обновление данных Polycom RPG 310 с перебором credentials, Обновление данных Extron IN1804 с перебором credentials, Исправление SIP регистрации для Huawei TE20 (+4 more)

### Community 40 - "Community 40"
Cohesion: 0.14
Nodes (10): DMPCancellationToken, DMPCancelled, The application-owned polling context was cancelled or superseded., Small thread-safe cancellation handle owned by the composition layer., wait_cancelable(), ExtronDMP64PlusMeterWorker, QRunnable, Long-lived Extron DMP meter polling workers. (+2 more)

### Community 41 - "Community 41"
Cohesion: 0.09
Nodes (8): CallLogWindow, QDialog, Window for displaying the last codec call records., Fill the table with up to ten latest call records., Placeholder for device-specific call history commands., PasswordDialog, ReleaseUIOffscreenTest, SavedPasswordDisclosureRegressionTest

### Community 42 - "Community 42"
Cohesion: 0.11
Nodes (6): CodecScreen, Обработчик нажатия кнопки "Исправить" для SIP регистрации, Обновление отображения статуса презентации в GUI., Осветлить HEX цвет на указанный процент, Обновление данных экрана, Совместимый helper: разделение теперь задаёт общая тема строк.

### Community 44 - "Community 44"
Cohesion: 0.18
Nodes (5): build_meter_snapshot(), DMPTransportSession, Serialized SIS transaction layer for one DMP SSH channel/session., DMPProtocolTests, FakeChannel

### Community 45 - "Community 45"
Cohesion: 0.11
Nodes (13): ClickableImageWidget, load_database_excel(), load_database_json(), MainSchemeWindow, QWidget, Фильтрует список помещений в ComboBox на основе текста в поиске., Обновляет элементы в ComboBox, сохраняя текущий выбор, если возможно., Вызывается при выборе помещения в списке (клик или Enter). (+5 more)

### Community 46 - "Community 46"
Cohesion: 0.12
Nodes (15): ExtronIN1804DataParser, Парсер данных для Extron IN1804, Преобразование сырых данных в формат для GUI, MatrixBackgroundOperation, _MatrixCleanupOperation, MatrixOperationFailure, MatrixOperationHandle, MatrixOperationSignals (+7 more)

### Community 47 - "Community 47"
Cohesion: 0.16
Nodes (12): Queue, build_output_dir(), InteractivePlinkSession, main(), parse_args(), PlinkHelpCollector, prompt_value(), Namespace (+4 more)

### Community 48 - "Community 48"
Cohesion: 0.12
Nodes (12): HuaweiBar310DataParser, ParserFactory, Any, Парсер данных для Huawei CloudLink Bar 310, Парсинг сырых данных от Huawei CloudLink Bar 310, Преобразование типа вызова, Преобразование состояния конференции, Преобразование режима сна (+4 more)

### Community 49 - "Community 49"
Cohesion: 0.15
Nodes (12): CloudLinkBox300Handler, Any, Получить статус аудио, Получить статус видео, Вспомогательный метод для HTTP запросов, Установка соединения с CloudLink Box 300, Отправить команду устройству, Обработчик для Huawei CloudLink Box 300 (+4 more)

### Community 51 - "Community 51"
Cohesion: 0.16
Nodes (7): ParameterRow, Label/value/action row whose content can be updated in place., BaseScreen, QWidget, Обновление данных экрана, Central design tokens and the application-wide PyQt5 theme.  Widgets should se, QFrame

### Community 52 - "Community 52"
Cohesion: 0.14
Nodes (6): Card with a title, optional icon, and public body layout., SectionCard, AudioDSPScreen, Read-only Biamp signal status screen., legacy_colors(), Return the legacy color contract backed by the central palette.

### Community 53 - "Community 53"
Cohesion: 0.15
Nodes (8): Exception, Проверка текущего адреса SIP сервера                  Returns:             st, Log a parsed, structurally redacted response without retaining raw text., Return request-scoped values that must never cross a diagnostic boundary., Emit redacted diagnostics for a public operation failure., Fallback login flow used by TE40 web UI on some firmware versions., Установка соединения с кодеком Huawei TE40, Установка адреса SIP сервера на кодеке Huawei TE40

### Community 54 - "Community 54"
Cohesion: 0.13
Nodes (10): DMPUnsupportedModel, is_supported_dmp64_plus_variant(), The connected SIS endpoint is not one of the supported DMP variants., require_assigned_credentials(), ExtronDMP64PlusHandler, _looks_like_paramiko_authentication(), _ParamikoDMPSession, BaseException (+2 more)

### Community 55 - "Community 55"
Cohesion: 0.16
Nodes (6): _redact_authorization_scheme(), _redact_key_value(), _redact_standalone_authorization_scheme(), redact_text(), Match, RedactionTests

### Community 56 - "Community 56"
Cohesion: 0.11
Nodes (8): QDialog, Compatibility delegate for Extron DMP 64 Plus polling., Показать диалог ввода пароля с кастомными стилями, Показать диалог ввода логина и пароля., Вернуть логин по умолчанию для устройства., Создание верхней панели с выпадающим списком и IP-адресом, Обработка изменения выбранного устройства, QLineEdit

### Community 58 - "Community 58"
Cohesion: 0.21
Nodes (5): active_chain(), Bar310CredentialRetryOwnershipTests, collect_outcomes(), RemainingProductionWorkerRetryOwnershipTests, TE20CredentialRetryOwnershipTests

### Community 60 - "Community 60"
Cohesion: 0.20
Nodes (9): build_output_dir(), main(), parse_args(), prompt_value(), Namespace, Path, SSHHelpCollector, strip_ansi() (+1 more)

### Community 61 - "Community 61"
Cohesion: 0.11
Nodes (3): Return one finite request cursor without mutating successful-index memory., Обновление IP адреса для выбранного устройства, Resolve all candidates once before any worker or handler is created.

### Community 62 - "Community 62"
Cohesion: 0.18
Nodes (3): Обновление отображения громкости в GUI, Обновление данных на экране, Преобразует строку вида '12' или '12%' в число.

### Community 63 - "Community 63"
Cohesion: 0.23
Nodes (7): main(), parse_args(), prompt_value(), Any, Namespace, Response, Te20HttpToggleClient

### Community 64 - "Community 64"
Cohesion: 0.18
Nodes (14): # TODO: реализовать для Bar 310, # TODO: реализовать для TE-20, # TODO: реализовать для Polycom, Делегат для выравнивания заголовков по правому краю, RightAlignHeaderDelegate, Apply a shared state without replacing device-specific layouts., coerce_ui_state(), Enum (+6 more)

### Community 65 - "Community 65"
Cohesion: 0.13
Nodes (6): Исправление SIP регистрации для Huawei TE40, Обработчик нажатия кнопки 'Исправить' для SIP регистрации, Исправление SIP регистрации для Polycom RPG 310, Подготовить параметры подключения для SIP fix., Запустить установку SIP сервера в фоновом потоке., Исправление SIP регистрации для CloudLink Bar 310.

### Community 67 - "Community 67"
Cohesion: 0.17
Nodes (4): MatrixScreen, Reset displayed values without losing the selected route., Extron routing screen with the original switching contract., Publish a non-secret route intent.

### Community 69 - "Community 69"
Cohesion: 0.12
Nodes (5): EthernetClientInterface, EthernetClass, SerialClass, SerialOverEthernetClass, SerialInterface

### Community 70 - "Community 70"
Cohesion: 0.14
Nodes (4): Submit desired presentation state without blocking the GUI thread., Возвращает актуальные credentials с учётом IP-специфичного индекса., Read speaker volume on the serialized background lane., Read microphone mute/gain on the serialized background lane.

### Community 71 - "Community 71"
Cohesion: 0.11
Nodes (11): HuaweiTE40Handler, Any, Обработчик для Huawei TE40 с рабочей реализацией подключения, Получить последние записи журнала звонков TE-40., Получение полного статуса устройства, Помощник для парсинга JSON данных, Получить информацию об устройстве, Получить системную информацию (+3 more)

### Community 73 - "Community 73"
Cohesion: 0.12
Nodes (9): ProtocolHandler, ABC, Абстрактный базовый класс для всех обработчиков протоколов, Установить соединение с устройством, Отправить команду устройству, Получить базовую информацию об устройстве, Проверить, установлено ли соединение, Получить время установки соединения (+1 more)

### Community 74 - "Community 74"
Cohesion: 0.29
Nodes (3): JsonCredentialProvider, Version-one plain-text JSON provider using only the standard ``json`` module., JsonCredentialProviderTests

### Community 75 - "Community 75"
Cohesion: 0.18
Nodes (6): CandidateT, CredentialAttemptPlan, Finite monotonic request cursor; persistence remains a caller decision., Advance exactly once to an unattempted higher candidate, never wrap., Return the index a caller may commit after final confirmed success., CredentialAttemptPlanTests

### Community 76 - "Community 76"
Cohesion: 0.14
Nodes (4): Обработчик нажатия кнопки изменения громкости, Перестраивает карточки, сохраняя публичные ссылки на controls., Создаёт строки через общие компоненты этапа 4., Match firmware value edges to the two detail value columns.

### Community 77 - "Community 77"
Cohesion: 0.23
Nodes (13): Assert-CleanGit(), Assert-Json(), Assert-SafeGeneratedOutput(), Count-Graph(), Fail(), Get-GraphVersion(), Get-JsonScalars(), Get-RepoRoot() (+5 more)

### Community 80 - "Community 80"
Cohesion: 0.28
Nodes (14): build_action_path(), http_post(), load_credentials(), load_ip_list(), main(), parse_args(), parse_json(), ping_probe() (+6 more)

### Community 81 - "Community 81"
Cohesion: 0.19
Nodes (3): Изменение громкости на 1 единицу, Submit an absolute target, preserving relative-button intent metadata., Возвращает текущее значение громкости из кеша или из отображаемой строки.

### Community 82 - "Community 82"
Cohesion: 0.15
Nodes (3): _literal_assignment(), ThemeOffscreenSmokeTest, ThemeSourceContractTest

### Community 83 - "Community 83"
Cohesion: 0.22
Nodes (8): DMPSessionPoisoned, DMPTransactionTimeout, A SIS transaction timed out; the current session must be abandoned., The SIS stream can no longer safely map untagged meter payloads., ConnectionError, Ошибка подключения к устройству, DeviceTimeoutError, Any

### Community 84 - "Community 84"
Cohesion: 0.22
Nodes (6): HuaweiTE20DataParser, Парсер данных для Huawei TE20, Парсинг сырых данных от Huawei TE20 в формат, ожидаемый маппингом, Преобразование состояния mute микрофона TE-20 для отображения., format_te20_monitor_audio_level(), Convert the TE20 web meter width (0..220) to a percentage.

### Community 86 - "Community 86"
Cohesion: 0.23
Nodes (10): apply_theme(), build_stylesheet(), create_palette(), Apply the shared palette and QSS to a QApplication or QWidget., _handle_thread_exception(), _handle_unhandled_exception(), main(), _show_crash_message() (+2 more)

### Community 87 - "Community 87"
Cohesion: 0.18
Nodes (3): Cookies, Response, TE20CallLogExportTests

### Community 89 - "Community 89"
Cohesion: 0.20
Nodes (5): Any, Получить статус вызова, Получить статус аудио, Получить статус видео, Получить полный статус устройства

### Community 90 - "Community 90"
Cohesion: 0.25
Nodes (9): classify_matrix_failure(), is_confirmed_matrix_credential_rejection(), MatrixFailureCategory, BaseException, Enum, str, Stable Matrix retry authority derived from typed outcomes., Return True only for explicit, safe Matrix credential rejection. (+1 more)

### Community 91 - "Community 91"
Cohesion: 0.22
Nodes (5): Core package exports with lazy imports., AtenPDUDataParser, Парсер данных для PDU Aten, Парсинг общей информации об устройстве, Парсинг статуса розеток из XML

### Community 92 - "Community 92"
Cohesion: 0.25
Nodes (4): dict, Compatibility bridge for explicit UI/test credentials and the provider., Генерация тестовых данных для кодеков, RequestCredentialStore

### Community 93 - "Community 93"
Cohesion: 0.22
Nodes (8): @fission-ai/openspec, description, devDependencies, @fission-ai/openspec, engines, node, name, private

### Community 96 - "Community 96"
Cohesion: 0.25
Nodes (4): Инициализация интерфейса, Создание виджета-заглушки с надписью Обновите данные, Apply the centralized theme for direct window construction., Создание панели времени обновления

### Community 98 - "Community 98"
Cohesion: 0.33
Nodes (3): QLabel, Compact round SIP registration state without an external icon pack., SIPRegistrationIndicator

### Community 100 - "Community 100"
Cohesion: 0.48
Nodes (5): decode_response(), export_with_pycurl(), main(), post_action(), pycurl_request()

### Community 101 - "Community 101"
Cohesion: 0.53
Nodes (4): application_root(), default_credentials_path(), Path, Resolve the project root from this stable module path, never ``cwd``.

### Community 103 - "Community 103"
Cohesion: 0.47
Nodes (5): build_legacy_context(), main(), parse_args(), Namespace, SSLContext

### Community 104 - "Community 104"
Cohesion: 0.60
Nodes (4): inspect_media_nodes(), main(), Inspect the Huawei endpoint UI without changing the diagnostic application.  U, visible_summary()

### Community 109 - "Community 109"
Cohesion: 0.50
Nodes (4): main(), parse_args(), Namespace, Run one sanitized, read-only GUI refresh against approved hardware.  The scrip

### Community 110 - "Community 110"
Cohesion: 0.67
Nodes (3): main(), Read Huawei endpoint SSH CLI help without changing configuration., receive()

## Knowledge Gaps
- **5 isolated node(s):** `name`, `private`, `description`, `@fission-ai/openspec`, `node`
  These have ≤1 connection - possible missing edges or undocumented components.
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VCSDiagnosticApp` connect `Community 9` to `Community 0`, `Community 6`, `Community 10`, `Community 16`, `Community 17`, `Community 18`, `Community 19`, `Community 20`, `Community 23`, `Community 24`, `Community 25`, `Community 26`, `Community 27`, `Community 28`, `Community 31`, `Community 37`, `Community 38`, `Community 39`, `Community 40`, `Community 41`, `Community 44`, `Community 45`, `Community 51`, `Community 55`, `Community 56`, `Community 59`, `Community 61`, `Community 64`, `Community 65`, `Community 72`, `Community 74`, `Community 75`, `Community 82`, `Community 83`, `Community 85`, `Community 86`, `Community 92`, `Community 95`, `Community 96`, `Community 99`, `Community 105`, `Community 109`, `Community 115`?**
  _High betweenness centrality (0.213) - this node is a cross-community bridge._
- **Why does `AuthenticationError` connect `Community 23` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 18`, `Community 21`, `Community 25`, `Community 29`, `Community 30`, `Community 31`, `Community 33`, `Community 37`, `Community 40`, `Community 44`, `Community 53`, `Community 54`, `Community 58`, `Community 64`, `Community 71`, `Community 73`, `Community 75`, `Community 83`, `Community 85`, `Community 92`, `Community 108`?**
  _High betweenness centrality (0.166) - this node is a cross-community bridge._
- **Why does `ConnectionError` connect `Community 83` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 15`, `Community 16`, `Community 18`, `Community 21`, `Community 25`, `Community 30`, `Community 31`, `Community 32`, `Community 33`, `Community 37`, `Community 40`, `Community 43`, `Community 44`, `Community 53`, `Community 54`, `Community 59`, `Community 64`, `Community 71`, `Community 73`, `Community 85`, `Community 92`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `VCSDiagnosticApp` (e.g. with `CredentialAttemptPlan` and `JsonCredentialProvider`) actually correct?**
  _`VCSDiagnosticApp` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 87 inferred relationships involving `AuthenticationError` (e.g. with `BaseExtronMatrixHandler` and `BaseHuaweiCodecHandler`) actually correct?**
  _`AuthenticationError` has 87 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `ConnectionError` (e.g. with `BaseExtronMatrixHandler` and `BaseHuaweiCodecHandler`) actually correct?**
  _`ConnectionError` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `CodecScreen` (e.g. with `InteractiveOperation` and `InteractiveSessionController`) actually correct?**
  _`CodecScreen` has 6 INFERRED edges - model-reasoned connections that need verification._
