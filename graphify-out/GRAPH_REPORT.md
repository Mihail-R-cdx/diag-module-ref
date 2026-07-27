# Graph Report - diag-module-ref@2ad5c67b5413  (2026-07-27)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3163 nodes · 8706 edges · 139 communities (103 shown, 36 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1099 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Final Frozen Baseline Policy
- Built from post-archive validated source commit: `2ad5c67b5413627cfc15fb327c0e6f856cf9b264`
- Indexed source ref: `origin/agent/frozen-project-graph-baseline-final-gate-repair`
- Target branch: `master`
- Stage: final.
- This is the frozen project baseline for subsequent project navigation.
- Do not rebuild or incrementally update the graph during active implementation, review, testing, or validation.
- Read `RULES.md`, `docs/project-graph-runbook.md`, and `graphify-out/baseline.json`.
- Compare `indexed_source_commit` with the current branch and analyze the branch diff separately.
- Refresh only at the approved post-archive graph checkpoint.

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
- Community 22
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 32
- Community 33
- Community 34
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
- Community 58
- Community 59
- Community 60
- Community 61
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
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
- Community 91
- Community 92
- Community 93
- Community 94
- Community 96
- Community 97
- Community 99
- Community 100
- Community 101
- Community 103
- Community 104
- Community 105
- Community 107
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
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 127
- Community 128
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139

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

## Communities (139 total, 36 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (37): Проверить, установлено ли соединение, CommandOutcomeUnknownError, An established codec session is no longer accepted by the device., A state-changing command may have reached the device without a reply., SessionInvalidError, _Context, _credential_identity(), _disconnect() (+29 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (58): application_root(), _canonical_nullable_string(), _canonical_required_string(), compute_snapshot_id(), default_snapshot_path(), _freeze_index(), _invalid_snapshot(), inventory_from_document() (+50 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (25): ProtocolError, HuaweiTE40Handler, Any, Exception, Проверка текущего адреса SIP сервера                  Returns:             str:, Return one authoritative sleep/audio sample for interactive polling., Разбудить устройство из режима сна., Получить текущий статус презентации. (+17 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (18): HuaweiTE20Handler, Any, Response, Получить информацию об устройстве, Получить системную информацию, Получить статус вызова, Decode TE20 responses as UTF-8 because the device often omits charset metadata., Получить статус аудио (+10 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (10): Унифицированный запуск обновления из полей ввода., Переключение между экранами, Submit a PDU outlet command without blocking the GUI thread., Показать сообщение об успехе, Генерация тестовых данных для матрицы, Осветлить HEX цвет на указанный процент, Инициализация всех экранов, Запускать обновление по Enter на списке устройств. (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (55): Add-SecretFinding(), Assert-Candidate(), Assert-CleanGit(), Assert-EvidenceCheckPassed(), Assert-EvidenceOnlyCommitDelta(), Assert-FinalSourceContainsGraphifyTooling(), Assert-FinalWorkflowGate(), Assert-GeneratedAllowlist() (+47 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (21): Reusable, device-agnostic widgets for the diagnostic GUI., configure_button(), EmptyState, ExclusiveActionGroup, QLabel, QWidget, Small reusable widgets styled by :mod:`gui.theme`.  The components intentionally, Colored status dot with optional adjacent text. (+13 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (4): PDUScreen, Aten outlet status and control screen., Disable only the controls for the outlet being changed., DeviceScreensOffscreenTest

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (4): ExtronIPLTPCS4iHandler, Any, Handler for PCS4i authoritative Telnet control and optional HTTP names., ExtronPCS4iSISTests

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (19): BaseHuaweiCodecHandler, ProtocolHandler, ABC, Any, Получить статус вызова, Получить статус аудио, Получить статус видео, Абстрактный базовый класс для всех обработчиков протоколов (+11 more)

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (25): AuthenticationError, Ошибка аутентификации, is_pdu_bulk_operation(), _is_sensitive_key(), Any, BaseException, Reusable redaction helpers for public diagnostic boundaries., Remove sensitive fields recursively without mutating application data. (+17 more)

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (29): Credential, CredentialProvider, normalize_credential(), ABC, Any, Local credential profile resolution at the application/core boundary.  Only the, Replaceable source of resolved request-scoped credentials., Resolve an explicitly requested or device-mapped profile. (+21 more)

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (14): Start one Aten PDU attempt with the GUI-selected credential., Start one model-aware PDU refresh attempt in a background worker., Обновление отображения времени, Обработка полученных данных от устройства, Обработка ошибок от устройства с автоматическим перебором credentials, Обработка обновления прогресса, Обработка обновления статуса, Обработка завершения работы Worker (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (18): EquipmentInventoryLoadError, Exception, Structured inventory load failure safe for application consumers., _default_handler_factory(), RoomContext, RoomResolutionResult, CodecDiagnosticStatus, EnrichmentPresentation (+10 more)

### Community 19 - "Community 19"
Cohesion: 0.10
Nodes (12): ExtronIN1804Handler, Обработчик для видеоматрицы Extron IN1804, Получение статуса сигналов на входах, Получение HDCP информации для входов, Получение текущих коммутаций, Получение полного статуса матрицы, Установка коммутации (выход всегда 1 для этой модели), Получить полный статус устройства (+4 more)

### Community 20 - "Community 20"
Cohesion: 0.09
Nodes (16): AtenPDUHandler, Any, Response, Подключение к PDU (проверка доступности), Универсальная функция для запросов к API Aten PDU, Попытка аутентификации с перебором паролей, Обработчик для PDU Aten (серия PE), Получение информации об устройстве (+8 more)

### Community 21 - "Community 21"
Cohesion: 0.14
Nodes (3): PolycomRPG310Handler, Any, Handler for Polycom RealPresence Group 310 over HTTPS REST.

### Community 22 - "Community 22"
Cohesion: 0.12
Nodes (23): The requested operation is not supported by the selected device., UnsupportedOperationError, build_pdu_bulk_outlet_sequence(), build_pdu_handler(), bulk_target_operation(), disconnect_quietly(), ensure_pdu_operation_supported(), _execute_absolute_outlet_policy() (+15 more)

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (3): MatrixController, MatrixOperationContext, Owns Matrix refresh, route, persistent session, and stale suppression.

### Community 25 - "Community 25"
Cohesion: 0.15
Nodes (11): BaseExtronMatrixHandler, Базовый класс для обработчиков матриц Extron, Установка TCP соединения с матрицей и аутентификация, Вход в Extron: ждем `login as:`, отправляем логин, ждем `Password:`, отправляем, Отправка команды и получение ответа, Чтение ответа от сокета, Читаем ответ, пока не появится одно из ожидаемых подстрок., MatrixAuthenticationError (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.16
Nodes (5): PDUOperationWorker, QRunnable, Background refresh/control worker for model-aware PDU operations., PDUOperationContractTests, ScriptedPDUHandler

### Community 28 - "Community 28"
Cohesion: 0.17
Nodes (4): DMPPollingContext, DMPPollingController, QThreadPool, Owns DMP polling context, callback authority, and credential handoff.

### Community 32 - "Community 32"
Cohesion: 0.12
Nodes (16): DMPCancelled, DMPUnsupportedModel, is_supported_dmp64_plus_variant(), The application-owned polling context was cancelled or superseded., The connected SIS endpoint is not one of the supported DMP variants., require_assigned_credentials(), ConnectionError, Ошибка подключения к устройству (+8 more)

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (6): HuaweiTE40DataParser, Парсер данных для Huawei TE40, Парсинг сырых данных от Huawei кодеков, Очистка версии ПО - ИСПРАВЛЕНО, Преобразование статуса презентации, HardwareLogRedactionTests

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (12): Обновление данных в зависимости от устройства, Refresh Biamp Tesira Forte CI read-only audio-DSP status., Start one Bar 310 attempt with the GUI-selected credential., Start one TE20 attempt with the GUI-selected credential., Обновление данных Huawei TE40 с перебором credentials, Обновление данных Polycom RPG 310 с перебором credentials, Обновление данных Extron IN1804 с перебором credentials, Исправление SIP регистрации для Huawei TE20 (+4 more)

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (17): ProtocolFactory, Фабрика для создания обработчиков протоколов., Зарегистрировать новый обработчик, Создает обработчик протокола указанного типа, Получить список поддерживаемых устройств, Core package exports with lazy imports., AtenPDUDataParser, HuaweiTE20DataParser (+9 more)

### Community 36 - "Community 36"
Cohesion: 0.11
Nodes (6): CodecScreen, Обработчик нажатия кнопки "Исправить" для SIP регистрации, Обновление отображения статуса презентации в GUI., Осветлить HEX цвет на указанный процент, Обновление данных экрана, Совместимый helper: разделение теперь задаёт общая тема строк.

### Community 38 - "Community 38"
Cohesion: 0.18
Nodes (5): build_meter_snapshot(), DMPTransportSession, Serialized SIS transaction layer for one DMP SSH channel/session., DMPProtocolTests, FakeChannel

### Community 39 - "Community 39"
Cohesion: 0.17
Nodes (6): Normalize the small status surface needed by PDUScreen., RelatedCodecStatusAdapter, FakeHuaweiStatusHandler, FakePolycomStatusHandler, RelatedCodecStatusAdapterTests, success_response()

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (23): Compatibility facade for public worker imports.  Worker implementations live in, BiampTesiraForteCIWorker, QRunnable, Read-only worker for Biamp Tesira Forte CI audio-DSP signal status., CodecSipFixWorker, QRunnable, Фоновый worker для установки SIP-сервера на поддерживаемых кодеках., PolycomCallLogWorker (+15 more)

### Community 41 - "Community 41"
Cohesion: 0.11
Nodes (13): ClickableImageWidget, load_database_excel(), load_database_json(), MainSchemeWindow, QWidget, Фильтрует список помещений в ComboBox на основе текста в поиске., Обновляет элементы в ComboBox, сохраняя текущий выбор, если возможно., Вызывается при выборе помещения в списке (клик или Enter). (+5 more)

### Community 42 - "Community 42"
Cohesion: 0.10
Nodes (22): order_codec_profiles(), _profile_key(), Any, Pure model/runtime codec transport ordering shared by all codec paths., Return the currently supported default profiles for one codec model., Put a supported saved profile first and deduplicate by port/SSL mode., supported_codec_profiles(), classify_codec_failure() (+14 more)

### Community 43 - "Community 43"
Cohesion: 0.17
Nodes (13): EquipmentInventory, EquipmentInventoryMetadata, EquipmentRecord, Enum, str, Pure PDU room and related codec resolution., Resolve exact PDU-room-codec context without side effects., _room_name_evidence() (+5 more)

### Community 44 - "Community 44"
Cohesion: 0.12
Nodes (15): ExtronIN1804DataParser, Парсер данных для Extron IN1804, Преобразование сырых данных в формат для GUI, MatrixBackgroundOperation, _MatrixCleanupOperation, MatrixOperationFailure, MatrixOperationHandle, MatrixOperationSignals (+7 more)

### Community 45 - "Community 45"
Cohesion: 0.16
Nodes (12): Queue, build_output_dir(), InteractivePlinkSession, main(), parse_args(), PlinkHelpCollector, prompt_value(), Namespace (+4 more)

### Community 46 - "Community 46"
Cohesion: 0.19
Nodes (4): active_chain(), PolycomWorkerOutcomeTests, public_output(), TE40WorkerOutcomeTests

### Community 47 - "Community 47"
Cohesion: 0.29
Nodes (3): RelatedCodecStatus, DummySession, EnrichmentControllerTests

### Community 48 - "Community 48"
Cohesion: 0.15
Nodes (12): CloudLinkBox300Handler, Any, Получить статус аудио, Получить статус видео, Вспомогательный метод для HTTP запросов, Установка соединения с CloudLink Box 300, Отправить команду устройству, Обработчик для Huawei CloudLink Box 300 (+4 more)

### Community 51 - "Community 51"
Cohesion: 0.16
Nodes (17): build_identity_command(), build_read_command(), build_recovery_command(), _channel_result(), dbfs_from_raw_meter(), DMPMeterChannel, DMPSessionPoisoned, flatten_snapshot_channels() (+9 more)

### Community 52 - "Community 52"
Cohesion: 0.14
Nodes (7): CredentialRequired, The device requested a credential, but none was assigned for this attempt., Extron IPL T PCS4i Telnet/SIS handler., SocketTelnetTransport, ExtronPCS4iAuthenticationTests, FakeTelnetTransport, make_handler()

### Community 53 - "Community 53"
Cohesion: 0.23
Nodes (15): CodecFailureCategory, Stable retry/recovery authority for codec refresh and interactive paths., OperationSemantic, str, PDUAttemptState, PDUCommonContext, PDUMutationLane, PDURefreshLane (+7 more)

### Community 54 - "Community 54"
Cohesion: 0.14
Nodes (8): Redact structured diagnostic text as well as Python containers., _redact_authorization_scheme(), redact_diagnostic(), _redact_key_value(), _redact_standalone_authorization_scheme(), redact_text(), Match, RedactionTests

### Community 55 - "Community 55"
Cohesion: 0.19
Nodes (4): CloudLinkBar310Handler, Парсинг ответа от сервера с обработкой двойной сериализации, Обработчик для Huawei CloudLink Bar 310, Download and parse the latest CloudLink Bar 310 call records.

### Community 56 - "Community 56"
Cohesion: 0.19
Nodes (8): Session, main(), parse_args(), prompt_value(), Any, Namespace, Response, Te20HttpToggleClient

### Community 57 - "Community 57"
Cohesion: 0.18
Nodes (16): CredentialConfigurationError, Safe error raised before network I/O when local credentials are invalid., DMPAttemptState, PendingDMPRetry, DMP-specific application polling lifecycle controller., # TODO: реализовать для Bar 310, # TODO: реализовать для TE-20, # TODO: реализовать для Polycom (+8 more)

### Community 58 - "Community 58"
Cohesion: 0.19
Nodes (9): BiampTesiraForteCIDataParser, Parser for Biamp Tesira Forte CI read-only audio-DSP status., BiampTesiraForteCIHandler, Collect read-only Input/Meter subscription values from Tesira TTP., BiampGUIBoundaryTest, BiampHandlerParserTest, BiampMainWindowRoutingTest, FakeBiampSession (+1 more)

### Community 59 - "Community 59"
Cohesion: 0.12
Nodes (7): ParameterRow, Card with a title, optional icon, and public body layout., Label/value/action row whose content can be updated in place., SectionCard, legacy_colors(), Return the legacy color contract backed by the central palette., QFrame

### Community 60 - "Community 60"
Cohesion: 0.11
Nodes (8): QDialog, Compatibility delegate for Extron DMP 64 Plus polling., Показать диалог ввода пароля с кастомными стилями, Показать диалог ввода логина и пароля., Вернуть логин по умолчанию для устройства., Создание верхней панели с выпадающим списком и IP-адресом, Обработка изменения выбранного устройства, QLineEdit

### Community 61 - "Community 61"
Cohesion: 0.15
Nodes (13): HTTPAdapter, decode_response(), export_with_pycurl(), main(), post_action(), pycurl_request(), lighten_color(), validate_ip() (+5 more)

### Community 63 - "Community 63"
Cohesion: 0.21
Nodes (5): active_chain(), Bar310CredentialRetryOwnershipTests, collect_outcomes(), RemainingProductionWorkerRetryOwnershipTests, TE20CredentialRetryOwnershipTests

### Community 64 - "Community 64"
Cohesion: 0.20
Nodes (9): build_output_dir(), main(), parse_args(), prompt_value(), Namespace, Path, SSHHelpCollector, strip_ansi() (+1 more)

### Community 65 - "Community 65"
Cohesion: 0.14
Nodes (8): PolycomDataParser, Преобразование статуса SIP, Парсер данных для Polycom устройств, Парсинг сырых данных от Polycom устройств, Преобразование статуса Selfview, Преобразование настроек LAN, Преобразование статуса двух мониторов, RequestLifecycleRegressionTests

### Community 66 - "Community 66"
Cohesion: 0.11
Nodes (3): Return one finite request cursor without mutating successful-index memory., Обновление IP адреса для выбранного устройства, Resolve all candidates once before any worker or handler is created.

### Community 67 - "Community 67"
Cohesion: 0.18
Nodes (3): Обновление отображения громкости в GUI, Обновление данных на экране, Преобразует строку вида '12' или '12%' в число.

### Community 69 - "Community 69"
Cohesion: 0.15
Nodes (7): DMPCancellationToken, Small thread-safe cancellation handle owned by the composition layer., wait_cancelable(), ExtronDMP64PlusMeterWorker, QRunnable, Long-lived DMP 64 Plus physical meter polling worker., DMPWorkerLifecycleTests

### Community 70 - "Community 70"
Cohesion: 0.50
Nodes (3): DMPTransactionTimeout, A SIS transaction timed out; the current session must be abandoned., DeviceTimeoutError

### Community 71 - "Community 71"
Cohesion: 0.13
Nodes (6): Исправление SIP регистрации для Huawei TE40, Обработчик нажатия кнопки 'Исправить' для SIP регистрации, Исправление SIP регистрации для Polycom RPG 310, Подготовить параметры подключения для SIP fix., Запустить установку SIP сервера в фоновом потоке., Исправление SIP регистрации для CloudLink Bar 310.

### Community 72 - "Community 72"
Cohesion: 0.17
Nodes (4): MatrixScreen, Reset displayed values without losing the selected route., Extron routing screen with the original switching contract., Publish a non-secret route intent.

### Community 74 - "Community 74"
Cohesion: 0.14
Nodes (10): CommandError, Ошибка выполнения команды на устройстве, BiampSession, BiampSessionManager, _DefaultBiampSessionManager, BaseException, Send one LF-terminated Tesira Text Protocol command., Connect through SSH first, then Telnet fallback. (+2 more)

### Community 75 - "Community 75"
Cohesion: 0.12
Nodes (5): EthernetClientInterface, EthernetClass, SerialClass, SerialOverEthernetClass, SerialInterface

### Community 76 - "Community 76"
Cohesion: 0.14
Nodes (4): Submit desired presentation state without blocking the GUI thread., Возвращает актуальные credentials с учётом IP-специфичного индекса., Read speaker volume on the serialized background lane., Read microphone mute/gain on the serialized background lane.

### Community 78 - "Community 78"
Cohesion: 0.29
Nodes (3): JsonCredentialProvider, Version-one plain-text JSON provider using only the standard ``json`` module., JsonCredentialProviderTests

### Community 79 - "Community 79"
Cohesion: 0.19
Nodes (7): HuaweiBar310DataParser, Парсер данных для Huawei CloudLink Bar 310, Парсинг сырых данных от Huawei CloudLink Bar 310, Преобразование типа вызова, Преобразование состояния конференции, Преобразование режима сна, Преобразование статуса микрофона (для Bar 310: On - выключен, Off - включен)

### Community 80 - "Community 80"
Cohesion: 0.17
Nodes (15): classify_matrix_failure(), DeviceError, DeviceNotFoundError, is_confirmed_matrix_credential_rejection(), MatrixFailureCategory, BaseException, Enum, Exception (+7 more)

### Community 81 - "Community 81"
Cohesion: 0.21
Nodes (4): CommandRejectedError, The device authoritatively rejected the requested command., AtenPDUPrimitiveTests, Response

### Community 82 - "Community 82"
Cohesion: 0.17
Nodes (6): CallLogWindow, QDialog, Window for displaying the last codec call records., Fill the table with up to ten latest call records., Placeholder for device-specific call history commands., PasswordDialog

### Community 83 - "Community 83"
Cohesion: 0.24
Nodes (4): BaseScreen, QWidget, Обновление данных экрана, Central design tokens and the application-wide PyQt5 theme.  Widgets should sele

### Community 84 - "Community 84"
Cohesion: 0.14
Nodes (4): Обработчик нажатия кнопки изменения громкости, Перестраивает карточки, сохраняя публичные ссылки на controls., Создаёт строки через общие компоненты этапа 4., Match firmware value edges to the two detail value columns.

### Community 85 - "Community 85"
Cohesion: 0.17
Nodes (8): Any, Получить текст ошибки, Получение полного статуса устройства, Получить информацию об устройстве, Получить системную информацию, Получить статус вызова, Получить статус аудио, Получить статус видео

### Community 86 - "Community 86"
Cohesion: 0.19
Nodes (6): CandidateT, CredentialAttemptPlan, Finite monotonic request cursor; persistence remains a caller decision., Advance exactly once to an unattempted higher candidate, never wrap., Return the index a caller may commit after final confirmed success., CredentialAttemptPlanTests

### Community 88 - "Community 88"
Cohesion: 0.26
Nodes (12): _attributes_for_alias(), _is_candidate_source(), _is_error_response(), _is_output_alias(), _issue(), _parse_aliases(), _parse_scalar(), _parse_subscription_values() (+4 more)

### Community 89 - "Community 89"
Cohesion: 0.28
Nodes (14): build_action_path(), http_post(), load_credentials(), load_ip_list(), main(), parse_args(), parse_json(), ping_probe() (+6 more)

### Community 92 - "Community 92"
Cohesion: 0.19
Nodes (3): Изменение громкости на 1 единицу, Submit an absolute target, preserving relative-button intent metadata., Возвращает текущее значение громкости из кеша или из отображаемой строки.

### Community 93 - "Community 93"
Cohesion: 0.15
Nodes (3): _literal_assignment(), ThemeOffscreenSmokeTest, ThemeSourceContractTest

### Community 94 - "Community 94"
Cohesion: 0.36
Nodes (8): _nested(), _object_data(), Any, Narrow related-codec status adapter., _read_huawei_call_status(), _read_huawei_presentation_status(), _string_value(), _successful_result()

### Community 96 - "Community 96"
Cohesion: 0.17
Nodes (7): dict, Compatibility bridge for explicit UI/test credentials and the provider., Делегат для выравнивания заголовков по правому краю, Генерация тестовых данных для кодеков, RequestCredentialStore, RightAlignHeaderDelegate, QStyledItemDelegate

### Community 99 - "Community 99"
Cohesion: 0.18
Nodes (3): Cookies, Response, TE20CallLogExportTests

### Community 103 - "Community 103"
Cohesion: 0.18
Nodes (4): _ParamikoBiampSession, _read_until_ttp_complete(), _telnet_write_login(), _TelnetBiampSession

### Community 104 - "Community 104"
Cohesion: 0.20
Nodes (4): Получить статус презентации, Разбудить устройство из режима сна., Установить SIP-сервер через тот же API, что и в референсном драйвере., Прочитать текущий SIP-сервер из конфигурации.

### Community 105 - "Community 105"
Cohesion: 0.29
Nodes (5): ExtronIN1804Worker, QRunnable, Worker для опроса матрицы Extron IN1804, collect(), ExtronIN1804WorkerRuntimeTests

### Community 108 - "Community 108"
Cohesion: 0.24
Nodes (5): _clean_command_echo(), _clean_frame(), DMPStreamFramer, _echo_comparison_text(), Frame CR/LF-delimited PTY stream data and filter command echo.

### Community 109 - "Community 109"
Cohesion: 0.22
Nodes (7): apply_theme(), build_stylesheet(), create_palette(), Apply the shared palette and QSS to a QApplication or QWidget., QPalette, main(), Launch the GUI with representative local data and no device I/O.

### Community 111 - "Community 111"
Cohesion: 0.22
Nodes (8): @fission-ai/openspec, description, devDependencies, @fission-ai/openspec, engines, node, name, private

### Community 114 - "Community 114"
Cohesion: 0.25
Nodes (4): Инициализация интерфейса, Создание виджета-заглушки с надписью Обновите данные, Apply the centralized theme for direct window construction., Создание панели времени обновления

### Community 116 - "Community 116"
Cohesion: 0.33
Nodes (5): ParserFactory, Any, Фабрика для получения парсера по типу устройства, Получить парсер для указанного типа устройства, Удобный метод для парсинга данных

### Community 117 - "Community 117"
Cohesion: 0.33
Nodes (3): QLabel, Compact round SIP registration state without an external icon pack., SIPRegistrationIndicator

### Community 120 - "Community 120"
Cohesion: 0.53
Nodes (4): application_root(), default_credentials_path(), Path, Resolve the project root from this stable module path, never ``cwd``.

### Community 122 - "Community 122"
Cohesion: 0.67
Nodes (5): _handle_thread_exception(), _handle_unhandled_exception(), main(), _show_crash_message(), _write_crash_log()

### Community 124 - "Community 124"
Cohesion: 0.47
Nodes (5): build_legacy_context(), main(), parse_args(), Namespace, SSLContext

### Community 125 - "Community 125"
Cohesion: 0.60
Nodes (4): inspect_media_nodes(), main(), Inspect the Huawei endpoint UI without changing the diagnostic application.  Usa, visible_summary()

### Community 133 - "Community 133"
Cohesion: 0.50
Nodes (4): main(), parse_args(), Namespace, Run one sanitized, read-only GUI refresh against approved hardware.  The script

### Community 134 - "Community 134"
Cohesion: 0.67
Nodes (3): main(), Read Huawei endpoint SSH CLI help without changing configuration., receive()

### Community 136 - "Community 136"
Cohesion: 0.67
Nodes (3): main(), parse_args(), Exercise Polycom GUI controls through SSH when Web UI sessions are full.  The sc

## Knowledge Gaps
- **5 isolated node(s):** `name`, `private`, `description`, `@fission-ai/openspec`, `node`
  These have ≤1 connection - possible missing edges or undocumented components.
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VCSDiagnosticApp` connect `Community 5` to `Community 133`, `Community 136`, `Community 12`, `Community 13`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 18`, `Community 24`, `Community 28`, `Community 29`, `Community 32`, `Community 33`, `Community 34`, `Community 35`, `Community 38`, `Community 41`, `Community 42`, `Community 51`, `Community 53`, `Community 54`, `Community 57`, `Community 60`, `Community 65`, `Community 66`, `Community 68`, `Community 69`, `Community 71`, `Community 77`, `Community 78`, `Community 83`, `Community 86`, `Community 93`, `Community 96`, `Community 97`, `Community 101`, `Community 107`, `Community 109`, `Community 110`, `Community 112`, `Community 113`, `Community 114`, `Community 118`, `Community 122`, `Community 126`?**
  _High betweenness centrality (0.206) - this node is a cross-community bridge._
- **Why does `AuthenticationError` connect `Community 13` to `Community 0`, `Community 2`, `Community 3`, `Community 131`, `Community 5`, `Community 132`, `Community 135`, `Community 11`, `Community 12`, `Community 14`, `Community 15`, `Community 19`, `Community 20`, `Community 21`, `Community 22`, `Community 25`, `Community 26`, `Community 32`, `Community 35`, `Community 38`, `Community 39`, `Community 40`, `Community 42`, `Community 43`, `Community 46`, `Community 47`, `Community 49`, `Community 51`, `Community 52`, `Community 53`, `Community 55`, `Community 57`, `Community 58`, `Community 63`, `Community 69`, `Community 70`, `Community 74`, `Community 80`, `Community 81`, `Community 86`, `Community 88`, `Community 96`, `Community 97`, `Community 103`, `Community 105`, `Community 106`, `Community 108`, `Community 119`?**
  _High betweenness centrality (0.161) - this node is a cross-community bridge._
- **Why does `ConnectionError` connect `Community 32` to `Community 0`, `Community 2`, `Community 3`, `Community 5`, `Community 11`, `Community 12`, `Community 13`, `Community 18`, `Community 19`, `Community 20`, `Community 21`, `Community 25`, `Community 26`, `Community 37`, `Community 38`, `Community 40`, `Community 42`, `Community 51`, `Community 52`, `Community 53`, `Community 55`, `Community 57`, `Community 58`, `Community 68`, `Community 69`, `Community 70`, `Community 74`, `Community 80`, `Community 81`, `Community 88`, `Community 96`, `Community 97`, `Community 103`, `Community 104`, `Community 106`, `Community 108`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `VCSDiagnosticApp` (e.g. with `CredentialAttemptPlan` and `JsonCredentialProvider`) actually correct?**
  _`VCSDiagnosticApp` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 87 inferred relationships involving `AuthenticationError` (e.g. with `BaseExtronMatrixHandler` and `BaseHuaweiCodecHandler`) actually correct?**
  _`AuthenticationError` has 87 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `ConnectionError` (e.g. with `BaseExtronMatrixHandler` and `BaseHuaweiCodecHandler`) actually correct?**
  _`ConnectionError` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `CodecScreen` (e.g. with `InteractiveOperation` and `InteractiveSessionController`) actually correct?**
  _`CodecScreen` has 6 INFERRED edges - model-reasoned connections that need verification._