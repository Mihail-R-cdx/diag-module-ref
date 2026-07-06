# Текущее состояние GUI

## Назначение и границы аудита

Документ фиксирует устройство и поведение GUI до визуальной переработки. Источники:
`main.py`, `gui/main_window.py`, `gui/screens/*.py`, `gui/dialogs/*.py`,
`core/worker.py`, `core/te20_worker.py` и существующие тесты.

В рамках аудита реальные устройства не опрашивались, команды управления не
отправлялись. Значения credentials здесь намеренно не приводятся.

## Запуск и структура модулей

- Точка входа: `main.py:main()`.
- Создаётся `QApplication`, применяется стиль `Fusion`, затем создаётся и
  показывается `gui.main_window.VCSDiagnosticApp`.
- Необработанные исключения главного и фоновых Python-потоков дописываются в
  `app_crash.log`; ошибка главного потока дополнительно показывается через
  `QMessageBox.critical`.
- Главное окно: `VCSDiagnosticApp(QMainWindow)`, базовая геометрия
  `950 x 950`, заголовок `Диагностический модуль ММК`.
- Центральная компоновка сверху вниз:
  1. панель выбора и подключения;
  2. `screen_container: QStackedWidget`;
  3. нижняя строка времени последнего успешного обновления.
- Экраны создаются один раз в `init_screens()` и хранятся в `screens`:
  `codec`, `matrix`, `pdu`, `audio_dsp`.
- Пятая страница стека — `placeholder_widget` с текстом `Обновите данные`.
  Она видна при старте и после каждой смены выбранной модели.
- Базовый класс экранов — `BaseScreen(QWidget)`. Его публичные контракты:
  `init_ui()`, `update_data(data)`, `refresh()`.

## Поддерживаемые устройства и маршрутизация

| Группа | Выбираемая модель | Экран | Запуск опроса |
| --- | --- | --- | --- |
| Кодеки ВКС | Huawei TE-20 | `CodecScreen` | `refresh_huawei_te20()` |
| Кодеки ВКС | Huawei TE-40 | `CodecScreen` | `refresh_huawei_te40()` |
| Кодеки ВКС | CloudLink Bar 310 | `CodecScreen` | `refresh_huawei_bar310()` |
| Кодеки ВКС | Polycom RPG 310 | `CodecScreen` | `refresh_polycom_rpg310()` |
| Коммутационное оборудование | Extron IN1804 | `MatrixScreen` | `refresh_extron_in1804()` |
| Audio DSP | Biamp Tesira Forte CI | `AudioDSPScreen` | `refresh_biamp_tesira_forte_ci()` |
| Управление питанием | Aten PE8208AV | `PDUScreen` | `refresh_aten_pdu()` |

Названия групп находятся в том же `device_combo`, но отключены и не должны
становиться текущим устройством. Закомментированный CloudLink Box 300 не является
доступным типом оборудования.

При смене модели `on_device_change()`:

- сбрасывает долгоживущую codec-сессию и TE-20 polling;
- закрывает persistent-сессию Extron при уходе с Extron;
- перестраивает набор строк кодека;
- сохраняет ожидаемый `current_screen_type`;
- возвращает стек на заглушку;
- обновляет заголовок окна.

Поле IP при смене модели автоматически не меняется: метод
`update_ip_for_device()` существует, но из `on_device_change()` не вызывается.

## Верхняя панель

Ключевые виджеты, имена которых используются обработчиками и не должны исчезать
при редизайне:

- `device_combo: QComboBox` — модель оборудования;
- `ip_entry: QLineEdit` — IP, стартовое значение `link.ru`;
- `password_btn: QPushButton` — `Пароль`;
- `refresh_btn: QPushButton` — `Обновить данные`;
- `debug_btn: QPushButton` — `Отладка`.

Связи:

- `device_combo.currentTextChanged -> on_device_change`;
- Enter в `device_combo` и `ip_entry.returnPressed -> trigger_refresh_from_input`;
- `password_btn.clicked -> show_password_dialog`;
- `refresh_btn.clicked -> refresh_data`;
- `debug_btn.clicked -> show_debug_window`.

`show_password_dialog()` фактически открывает модальный диалог с полями
`Логин` и `Пароль`. Оба обязательны. Новая пара помещается в начало хранимого в
памяти списка устройства; существующая пара переносится в начало. Для пары
также сбрасывается IP-зависимый индекс credentials. Данные на диск не
сохраняются.

Глобальный event filter логирует пользовательские активации всех доступных
`QPushButton` мышью или клавиатурой в `logs/button_clicks.log`: время, выбранную
модель, IP и подпись кнопки. Секреты в этот журнал не включаются.

## Сигналы, обработчики, workers и общий сценарий обновления

`refresh_data()` является основным контрактом обновления:

1. Проверяет непустой IPv4 и диапазон каждого октета.
2. Синхронно выполняет один ping с коротким timeout. При неуспехе показывает
   `Ping неуспешен` и не запускает worker.
3. Сбрасывает индекс credentials на первый для пары модель/IP.
4. Показывает соответствующий экран и очищает его данные.
5. Запускает модель-специфичный `QRunnable` в глобальном `QThreadPool`.

Все workers предоставляют совместимый объект `signals`:

- `result(dict) -> on_device_data_received`;
- `error(tuple) -> on_device_error`;
- `progress(int) -> on_progress_update`;
- `status(str) -> on_status_update`;
- `finished() -> on_worker_finished`;
- дополнительно могут выдавать `terminal_log(str)`, `connected()` и
  `disconnected()`.

Во время запуска `refresh_btn` отключается и получает текст подключения.
`show_progress_dialog()` показывает модальный `QProgressDialog` 0–100 без кнопки
отмены. Статусы worker меняют подпись, progress меняет значение. `finished`
закрывает диалог через 100 мс и возвращает кнопке исходный текст.

При результате:

- ответ без содержательных значений вызывает предупреждение `Нет данных`;
- успешные credentials и, если есть, профиль подключения запоминаются;
- `update_data(data)` вызывается у экрана из `current_screen_type`;
- обновляется `last_update_time`;
- для полного результата показывается информационный диалог успеха;
- Polycom сначала может выдать `_partial_update` с HTTPS-данными, затем
  продолжить SSH-опрос и выдать полный результат.

При ошибке:

- ошибки авторизации распознаются по типу и набору текстовых признаков;
- последовательно пробуются следующие credentials;
- после исчерпания вариантов показывается отдельное предупреждение авторизации;
- connection/timeout, SSL и прочие ошибки получают разные тексты;
- кнопка обновления снова включается.

## Нижняя строка

- Статическая подпись: `Предыдущее обновление данных:`.
- `time_display` показывает `Никогда` до первого содержательного результата,
  затем относительное время (`Только что`, минуты, часы или дни).
- `update_timer` создан, но не подключён и не запущен. Поэтому относительное
  время пересчитывается только при новом успешном результате, а не непрерывно.
- Отдельного постоянного индикатора соединения в текущем GUI нет.

## Экран кодеков

### Компоновка и параметры

`CodecScreen` — вертикальная прокручиваемая область из трёх блоков, разделённых
линиями. `param_count == 15`.

Блок 1:

- Версия прошивки;
- Модель кодеков;
- Серийный номер;
- MAC адрес.

Блок 2:

- SIP регистрация;
- Время работы.

Блок 3:

- Статус звонка;
- Статус презентации;
- для TE-20, TE-40 и Polycom — `Mute микрофона`, для остальных —
  `Громкость микрофона`;
- Громкость динамиков;
- Статус камеры;
- Статус микрофона;
- только для TE-20 — звук в помещении и звук из динамиков;
- Журнал звонков;
- оставшиеся позиции до 15 заполняются строками `Доп. параметр N`.

Ключевые коллекции динамических виджетов:

- `param_widgets`;
- `presentation_buttons`;
- `sip_fix_buttons`;
- `volume_buttons`;
- `mute_buttons`;
- `wake_buttons`;
- `wake_countdown_labels`.

Их имена и семантику следует сохранять до переноса всех обработчиков.

### Действия

- SIP: при значении `Не зарегистрирован` строка становится красной и появляется
  кнопка `Исправить`. Перед командой показывается подтверждение установки
  `link.ru`. Текущий эффективный обработчик поддерживает TE-40,
  CloudLink Bar 310 и Polycom; TE-20 сообщает, что поддержка будет добавлена.
- Презентация: кнопки `Выкл`/`Вкл` вызывают `set_presentation("Stop"/"Start")`.
  На 1,5 секунды блокируется только пара кнопок строки, значение меняется
  оптимистично и затем перечитывается.
- Громкость динамиков: `Muted/Unmuted`, `-`, `+`. Шаг равен 1.
- Микрофон: mute для всех кодеков; `-`/`+` показываются только когда строкой
  является `Громкость микрофона`.
- Диапазоны динамиков: TE-20/TE-40 0–21, Bar 310 0–15, Polycom 0–100.
- Диапазоны микрофона: TE-20/TE-40 0–21, Bar 310 0–15, Polycom -20–30.
- Mute реализован установкой 0 и восстановлением последнего ненулевого значения.
- `Открыть` в строке журнала показывает `CallLogWindow`, синхронно читает до
  десяти записей и выводит номер комнаты, начало, длительность и скорость.

Управление громкостью, презентацией, пробуждением и чтение call log используют
долгоживущий `volume_session_handler`. При смене устройства и при исключении он
отключается. Профили подключения перебираются отдельно для каждой модели.

### Специальное поведение TE-20

- `monitor_audio_timer` каждые 3 секунды синхронно читает sleep mode и
  `get_monitor_audio_params`, пока активен экран TE-20.
- Во сне четыре поля получают `недоступно в режиме Сна`, элементы микрофона
  скрываются и появляется `Разбудить`.
- После wake запускается видимый обратный отсчёт 7 секунд, затем перечитываются
  monitor audio и микрофон.
- При старте презентации спящего устройства запрашивается подтверждение,
  выполняется wake, до 15 секунд проверяется выход из сна и показывается
  отдельный двухсекундный progress countdown.

### Таймеры кодека

- `volume_refresh_timer`: single-shot, 1500 мс;
- `presentation_refresh_timer`: single-shot, 1500 мс;
- `monitor_audio_timer`: периодический, 3000 мс;
- `wake_countdown_timer`: периодический, 1000 мс;
- дополнительные `QTimer.singleShot`: визуальный feedback кнопок, повторное
  включение управления и быстрые перечитывания.

## Экран Extron IN1804

`MatrixScreen` показывает таблицу 8 входов и одного реально используемого
выхода. Колонки:

- `Сигнал` — зелёная/красная точка;
- `HDCP` — активная/неактивная точка;
- `Входы` — имя входа;
- имя первого выхода — активная связь.

Нижняя информационная панель: температура, модель, протокол подключения.

Клик обрабатывается только в колонке выхода. Он синхронно вызывает
`handler.set_connection(1, input_num)`, а через 300 мс синхронно перечитывает
`get_connections()` и обновляет только точки коммутации.

Главное окно держит `matrix_persistent_handler`; `matrix_keepalive_timer`
каждые 15 секунд отправляет `w20STAT`. Сессия закрывается при уходе с Extron и
при закрытии окна.

Терминальные сообщения опроса выводятся в read-only `MatrixTerminalDialog`.
Диалог не открывается автоматически при опросе, но накапливает строки и
доступен через `Отладка`.

Ключевые контракты: `matrix_table`, `matrix_data`, `current_connection`,
`temp_value`, `model_value`, `protocol_value`, `on_output_cell_clicked()`,
`request_status_update()`, `update_connection_display()`.

## Экран Aten PE8208AV

`PDUScreen` содержит:

- группу `Информация об устройстве`: модель и IP;
- группу `Управление розетками`;
- локальную кнопку `Обновить статус`;
- таблицу колонок `№`, `Статус`, `Название`, `Вкл`, `Выкл`, `Перезаг`.

Статус показывается emoji-галочкой или крестом. Для каждой строки создаются три
кнопки. Перед `on`, `off`, `reboot` показывается подтверждение. Затем
`outlet_control_signal(int, str) -> on_outlet_control() ->
VCSDiagnosticApp.control_pdu_outlet()` синхронно создаёт handler, выполняет
команду, показывает результат и при успехе запускает полный refresh.

Ключевые контракты: `outlets_table`, `outlets`, `outlet_names`, `device_info`,
`info_labels`, `outlet_control_signal`, `on_outlet_button_click()`.

## Экран Biamp Tesira Forte CI

`AudioDSPScreen` является read-only:

- верхняя группа `Device`: модель и IP;
- ниже — прокручиваемая сетка по две карточки в строке;
- карточка соответствует signal source и имеет заголовок
  `alias (subscription_attribute)`;
- таблица карточки: `Channel number`, `Value`;
- boolean `True` зелёный, `False` вторичный серый;
- при отсутствии источников показывается `No signal sources`.

Публичные контракты: `container`, `content_layout`, `info_group`, `model_value`,
`ip_value`, `sources_layout`, `clear_data()`, `update_data(data)`, `refresh()`.

## Диалоги и специальные окна

- `QProgressDialog` — общий прогресс фонового опроса/SIP fix.
- `MatrixTerminalDialog` — единый класс read-only terminal для Extron, TE-20 и
  остальных codec-команд; `reset_session()`, `append_line()`.
- `CallLogWindow` — последние 10 звонков; `set_call_records()`,
  `clear_records()`, `normalize_record()`.
- Диалог credentials — логин и пароль, только в памяти.
- Подтверждения: PDU-команды, SIP fix, пробуждение спящего кодека.
- Информационные/ошибочные сообщения: ping, validation, успех опроса, отсутствие
  данных, авторизация, connection/SSL, неподдерживаемые функции и команды.

`show_debug_window()` выбирает terminal по текущей модели: отдельный TE-20,
отдельный Extron, общий codec terminal для остальных, включая PDU и Biamp.

## Состояния интерфейса

| Состояние | Текущее представление |
| --- | --- |
| До первого запроса / после смены модели | Страница `Обновите данные` |
| Некорректный или пустой IP | Warning dialog; экран не меняется |
| Ping неуспешен | Warning dialog; worker не запускается |
| Загрузка | Целевой экран очищается, `QProgressDialog`, refresh отключён |
| Перебор credentials | Обновляется подпись попытки/terminal |
| Частичный Polycom-результат | Экран уже заполнен HTTPS-данными, progress продолжается для SSH |
| Успех | Экран заполнен, time display обновлён, modal information |
| Нет полезных данных | Warning `Нет данных` |
| Ошибка авторизации | Перебор credentials, затем warning |
| Connection/timeout/SSL/иная ошибка | Critical dialog с отдельным текстом |
| Недоступное значение | `Не доступно`, `—` или `<unavailable>` в зависимости от экрана |
| TE-20 во сне | Оранжевый текст, скрытые controls, кнопка wake |
| Выполнение команды | Локальный feedback неоднороден; часть операций синхронна |
| Неактивное управление | refresh или пара presentation-кнопок disabled |

Постоянного inline-статуса `подключено/отключено`, единой ошибки в теле экрана и
единого loading/empty/error-компонента сейчас нет.

## Контракты, которые нельзя случайно сломать

Наиболее важные имена главного окна:

- `colors`, `device_to_screen`, `device_credentials`,
  `current_credential_index`, `device_connection_profiles`;
- `screens`, `screen_container`, `placeholder_widget`,
  `current_screen_type`, `current_screen`;
- `device_combo`, `ip_entry`, `password_btn`, `refresh_btn`, `debug_btn`,
  `time_display`;
- `current_worker`, `progress_dialog`;
- persistent Extron-поля и `matrix_keepalive_timer`.

Наиболее важные публичные/межмодульные методы:

- `refresh_data()`, все `refresh_<device>()`;
- `on_device_data_received()`, `on_device_error()`, `on_worker_finished()`;
- `show_progress_dialog()`, `hide_progress_dialog()`;
- `get_current_credential_index()`, `set_current_credential_index()`;
- `get_device_connection_profile()`, `set_device_connection_profile()`;
- `ensure_matrix_persistent_handler()`, `disconnect_matrix_persistent_handler()`;
- `control_pdu_outlet()`, `on_fix_sip_registration()`;
- terminal helper-методы;
- `CodecScreen.update_parameters_display()`, `update_data()`,
  `reset_volume_session()` и методы управления;
- `MatrixScreen.update_data()`, `PDUScreen.update_data()`,
  `AudioDSPScreen.update_data()`.

Динамические кнопки не имеют `objectName`; их обработчики зависят от текста,
словарей ссылок и замыканий. При введении object names нельзя удалять текущие
атрибуты до переноса обработчиков.

## Ручные smoke-сценарии

Все сценарии с реальным ответом выполнять только на разрешённом тестовом
оборудовании. Для UI-only проверки workers и handlers должны быть заменены
fixtures/fakes.

### Общие

1. Открыть окно в `950 x 950`: видна верхняя панель, заглушка и `Никогда`.
2. Пройти все выбираемые модели: заголовки групп не выбираются, экран снова
   становится заглушкой, заголовок окна меняется.
3. Проверить пустой IP, неправильный формат и fake ping failure.
4. На fake worker проверить progress/status, успешный result, пустой result,
   auth retry и connection error.
5. Проверить Enter в IP и combo, Password dialog, Debug dialog и button log.

### Huawei TE-20

1. Fake result заполняет все codec-поля и запускает monitor polling.
2. Проверить speaker mute/+/-, mic mute, presentation on/off, call log.
3. Имитировать Sleep: недоступные строки, wake, 7-секундный countdown и resume.
4. Сменить модель и убедиться, что polling и handler остановлены.

### Huawei TE-40

1. Проверить HTTPS/HTTP profile fallback на fake handler.
2. Проверить codec-параметры, громкость, mic mute и presentation.
3. Для незарегистрированного SIP проверить подтверждение и SIP-fix worker.
4. Проверить call log success/empty/error.

### CloudLink Bar 310

1. Проверить опрос и перебор credentials.
2. Проверить диапазон громкости 0–15, presentation и call log.
3. Проверить SIP fix и отображение auth/request errors.

### Polycom RPG 310

1. Получить partial HTTPS result, затем полный SSH result.
2. Убедиться, что progress остаётся видимым на SSH-фазе.
3. Проверить диапазон громкости, mic mute, presentation, SIP fix и call log.

### Extron IN1804

1. Fake result заполняет 8 входов, сигнал, HDCP, текущую связь, модель,
   температуру и протокол.
2. Кликнуть только колонку выхода: одна команда коммутации, затем быстрый status.
3. Проверить terminal log, keepalive, смену модели и закрытие persistent handler.

### Aten PE8208AV

1. Fake result заполняет модель, IP и восемь розеток.
2. Для каждой команды проверить Yes/No; при Yes — ровно один signal/handler call.
3. Проверить success, failure, exception и автоматический refresh после success.

### Biamp Tesira Forte CI

1. Fake result строит карточки источников по две в строке.
2. Проверить boolean-цвета, несколько каналов, пустой список и clear/reload.
3. Убедиться, что экран не содержит управляющих команд.

## Автоматические тесты и пробелы

Существует один файл `tests/test_biamp_tesira_forte_ci_audio_signal_status.py`.
Он покрывает:

- discovery/subscription и transport fallback Biamp handler;
- нормализацию данных Biamp parser;
- статическое наличие маршрута Biamp в главном окне;
- offscreen-рендер карточки Audio DSP;
- отсутствие Biamp protocol-команд в GUI-модулях.

Не покрыты:

- создание полного `VCSDiagnosticApp` и его начальные контракты;
- маршрутизация остальных шести моделей;
- signal wiring и состояния progress/error/success/auth retry;
- codec controls, timers, sleep/wake и call log;
- Extron table/switch/keepalive;
- PDU table/confirmation/signal;
- диалог credentials и нижняя строка;
- освобождение workers/handlers при смене модели и закрытии окна;
- размеры, прокрутка, keyboard navigation и accessibility.

Запуск тестов не состоялся: обязательный по `RULES.md` интерпретатор
`C:\Program Files\anaconda3\python.exe` отсутствует. Другой найденный
интерпретатор намеренно не использовался. Реальное GUI и реальные сетевые
запросы также не запускались.

## Технические риски переделки

1. В `gui/main_window.py` несколько методов определены повторно:
   `show_password_dialog`, `fix_sip_huawei_te40`, `on_sip_fix_result`,
   `on_sip_fix_error`, `on_fix_sip_registration`. Работает только последнее
   определение каждого имени. При переносе легко восстановить устаревшую ветку.
2. `PDUScreen.update_info_panel()` обращается к `info_labels['firmware']` и
   `info_labels['status']`, хотя создаются только `model` и `ip_address`.
   Соответствующий payload может вызвать `KeyError`.
3. `clear_data()` экранов ищет `table`, `status_label` и labels с property
   `data_field`, но фактические виджеты обычно не имеют этих имён/properties.
   Поэтому старые значения могут оставаться видимыми во время загрузки.
4. Codec control, call log, TE-20 polling/wake, Extron switch/status/keepalive и
   PDU control выполняют сетевую работу в GUI thread. Медленный ответ замораживает
   окно; визуальная переделка не должна маскировать или усугублять это.
5. `current_worker` один на всё окно. Поздний сигнал старого worker после смены
   модели способен обновить уже другой экран; request identity отсутствует.
6. Отмена progress фактически недоступна (`setCancelButton(None)`), а workers
   обычно не останавливаются при смене модели/закрытии окна.
7. Успех и ошибки в основном modal; постоянного состояния соединения нет.
8. `update_timer` не запущен, поэтому нижнее относительное время устаревает.
9. В ветке общего matrix routing вызывается отсутствующий
   `refresh_matrix_data()`. Сейчас ветка практически перекрыта явным Extron,
   но сломается при добавлении второй модели matrix.
10. В исходниках есть mojibake-строки (включая одно сообщение wake failure и
    отдельные тексты восстановления кнопки). Редизайн не должен копировать их
    как целевые пользовательские тексты.
11. Hardcoded credentials и их in-memory перебор связаны с логикой подключения.
    Их нельзя переносить в QSS/компоненты, выводить в UI или button logs.
12. Дублированные inline QSS и зависимости от текста кнопок делают массовую
    замену стилей рискованной; перенос следует делать через сохранение ссылок и
    поэкранные contract tests.
13. `CallLogWindow.load_from_device()` — placeholder с `NotImplementedError`;
    реальный путь идёт напрямую через `CodecScreen.open_call_log_window()`.
14. `gui/dialogs/password_dialog.py` — пустой placeholder и не участвует в
    фактическом диалоге credentials.

## Минимальный защитный набор для следующих этапов

Перед изменением product-кода желательно добавить hardware-free offscreen-тесты:

1. Полное создание окна: размер, пять страниц стека, семь selectable devices,
   заглушка, верхняя и нижняя панели.
2. Табличный тест `device -> screen -> refresh method` с подменой ping/workers.
3. Fake-result tests для каждого `update_data()`.
4. Signal tests для PDU и presentation/volume actions без handler imports.
5. Fake timer/handler tests для Extron и TE-20 с явной проверкой cleanup.
6. Проверку, что редизайн сохраняет перечисленные атрибуты и публичные методы.
