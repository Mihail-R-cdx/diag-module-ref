# Проверка GUI на Polycom RealPresence Group 310

Дата проверки: 1 июля 2026 года.

## Версия и окружение

- Ветка `master`, `HEAD` `4082448c997b4d2157455073ac24583cfe242351`.
- Проверялось текущее незакоммиченное рабочее дерево; несвязанные
  пользовательские изменения сохранены, коммит не создавался.
- Windows Server 2019 (`10.0.17763`), Python `3.12.9`, Qt `5.15.2`,
  PyQt `5.15.11`.
- Обязательный Anaconda-интерпретатор отсутствует; использован доступный
  Python `3.12.9`.
- GUI-модель: `Polycom RPG 310`; адрес в отчёте: `10.10.0.x`.
- После выполненного пользователем reboot DHCP назначил устройству новый
  адрес; в отчёте оба фактических адреса остаются замаскированы.
- ICMP, HTTPS `443` и SSH `22` доступны.

Credentials использовались только в памяти для подключения. Их значения,
cookies и session data не сохранялись и не выводились. После обнаружения
ошибки выбора credential-профиля QA-runner был ограничен одной явно
разрешённой парой; перебор отключён.

## Read-only GUI refresh

Первый и повторный refresh штатной кнопкой прошли успешно:

- loading → частичный HTTPS result → полный SSH result → success;
- duplicate click заблокирован disabled-состоянием кнопки;
- два result payload применены в правильном порядке;
- повторный refresh не создал duplicate/stale отображение;
- terminal/debug view работал, совпадений с username/password не найдено;
- Qt heartbeat обычного refresh: максимальный разрыв `47 ms`.

Наличие и корректность полей проверены без публикации значений:

| Поле | Результат |
| --- | --- |
| model, firmware, serial, MAC, uptime | получены и отображены |
| SIP registration | получена и отображена |
| SIP address | получен; добавлено отсутствовавшее отображение в parser |
| call state | получен; активного звонка не было |
| presentation state | получен; исходно не активна |
| speaker volume | получена |
| microphone mute/audio state | CLI mute state получен; физически микрофон не подключён |
| camera state | получено |
| network information | IP/MAC получены |
| call log | GUI загрузил `10` записей; номера и строки не сохранялись |

Отдельного speaker-mute статуса устройство не предоставляет: GUI реализует
его безопасным циклом speaker volume `текущее значение ↔ 0`.

## GUI controls и восстановление

Перед каждым выполненным циклом refresh подтверждал отсутствие активного
звонка.

| Control | Исходное | Тестовое | Финальное | Результат |
| --- | ---: | ---: | ---: | --- |
| Speaker volume | `48` | `50` | `48` | изменение и rollback подтверждены чтением |
| Speaker mute | `48` | `0` | `48` | mute и rollback подтверждены чтением |
| Microphone mute | `Unmuted` | `Muted` | `Unmuted` | выполнен по ложному GUI-признаку подключения; полностью восстановлен |
| Presentation | Stop | Start не подтвердился | Stop | вход не подключён; финальный Stop подтверждён |
| Wake | состояние sleeping не сообщалось | не выполнялось | без изменений | кнопка wake не показывалась |

Первая volume-попытка выявила ошибку GUI: `48 → 49` не подтверждалось,
поскольку Polycom принимает шаг `2%`. Исходное `48` было подтверждено.
После исправления один аппаратный шаг прошёл как `48 → 50 → 48`.

SIP Fix, reboot, reset, firmware upgrade, изменение сети, credentials и
конфигурации не выполнялись.

## Qt heartbeat и race-сценарии

| Сценарий | Максимальный разрыв heartbeat | Результат |
| --- | ---: | --- |
| refresh/connect | `47 ms` | event loop отзывчив |
| Call Log до исправления | `453 ms` | подтверждена синхронная блокировка |
| volume cycle | `9.312 s` | критическая блокировка GUI thread |
| speaker mute cycle | `9.312 s` | критическая блокировка GUI thread |
| microphone mute cycle | `19.015 s` | критическая блокировка GUI thread |
| presentation cycle | `17.015 s` | Start не подтверждён, Stop восстановлен |
| неудачная первая volume-попытка | `11.297 s` | критическая блокировка GUI thread |
| auth-error после session limit | `47 ms` | корректный error state |

- Duplicate refresh click заблокирован.
- При смене модели во время read-only запроса поздняя ошибка не обновила новый
  экран, refresh control восстановился.
- Hardware-free regression подтверждает heartbeat во время двухсекундной
  фоновой загрузки Polycom Call Log, отбрасывание late result и безопасный
  cleanup.
- Реальный Call Log после исправления успешен: `10` записей, heartbeat
  `47 ms`, late/cleanup ошибок нет.
- SSH `callinfo all` перед каждой поздней управляющей командой однозначно
  подтверждал отсутствие активного звонка. Microphone и presentation были
  выполнены реальными GUI-кнопками с заранее открытой SSH-сессией, поскольку
  штатный control flow блокировался на HTTPS session limit.

## Исправленные дефекты

1. REST response body и credentials могли попадать в Polycom terminal/debug
   log. Payload/response и секреты теперь обезличиваются.
2. Worker/parser печатали полные Polycom payloads. Вывод ограничен именами
   полей.
3. SIP address читался handler, но не передавался в GUI. Поле добавлено.
4. При отсутствии SSH audio data GUI ошибочно показывал микрофон подключённым.
   Дополнительно выяснено, что `mute near get` отвечает даже без физического
   микрофона. Теперь такой ответ не считается признаком подключения:
   отображается «Не определено», control скрывается.
5. Speaker volume использовал неподдерживаемый шаг `1%`. Для Polycom
   установлен аппаратный шаг `2%`.
6. Polycom Call Log выполнялся в GUI thread. Загрузка перенесена в worker с
   request identity, late-result и closed-window защитой.
7. `disconnect()` закрывал только локальный opener и оставлял server-side web
   session. Добавлен best-effort `Logout` перед локальным cleanup; Polycom
   worker теперь вызывает его в `finally` даже после ошибки.
8. QA-runner из-за общего сброса credential index мог начать с другой
   встроенной пары. Для Polycom hardware QA он теперь оставляет в памяти
   ровно выбранную разрешённую пару.
9. Закрытие главного окна не сбрасывало долгоживущую codec control-сессию.
   `closeEvent()` теперь явно вызывает `reset_volume_session()`.

## Session-limit blocker и cleanup

После нескольких успешных GUI-запусков устройство стало отвечать
`Maximum Number Of Per User Sessions Exceeded`. Браузер показал только форму
входа без списка/кнопки завершения старых сессий. Это подтвердило дефект
отсутствующего server-side logout.

Пользователь вручную перезагрузил тестовый кодек, после чего DHCP назначил
новый адрес. Post-reboot проверка успешна: штатный GUI refresh прошёл без
auth-error, а семь последовательных циклов `connect → Logout → disconnect`
дали `7/7` успешных подключений и `7/7` подтверждённых server logout.
Накопление web-сессий после исправления не воспроизводится.

Все volume/mute/presentation device states, которые фактически изменялись,
восстановлены; активных GUI workers/handlers после завершения нет.

Один прямой unauthenticated read-only запрос `login.html/login.js` был
выполнен только для локализации logout endpoint; session data и response body
не сохранялись.

## Автоматические тесты

- Полный hardware-free набор после исправлений: `46` тестов, `OK`.
- `compileall` для `main.py`, `gui`, `core`, `handlers`, `tests`, `tools`:
  успешно.
- Импорт GUI и Polycom-модулей: успешно.
- Добавлены regression-тесты redaction, SIP address/unavailable microphone,
  server logout, Polycom volume step и async Call Log heartbeat.

## Непроверенные сценарии и блокеры

- Presentation Start отправлен через GUI, но устройство не подтвердило Start;
  финальный Stop подтверждён. SSH CLI не возвращает JSON-поля
  `success/error.id/error.code`, поэтому safe error codes отсутствуют.
- Polycom volume/mute/presentation controls остаются синхронными и блокируют
  Qt event loop до `19 s`. Их перенос требует общего command-worker
  lifecycle с гарантированным rollback.
- Microphone и presentation source физически не подключены. Mic control после
  исправления скрыт; Presentation Start ожидаемо не подтверждается.
- Отдельный реальный wake не применим: sleeping state и wake control не были
  доступны.

## Изменённые файлы

- `handlers/polycom/rpg310.py`;
- `core/parser.py`;
- `core/worker.py`;
- `gui/main_window.py`;
- `gui/screens/codec_screen.py`;
- `tests/test_codec_screen.py`;
- `tests/test_hardware_log_redaction.py`;
- `tools/real_hardware_readonly_smoke.py`;
- `tools/polycom_ssh_gui_controls_qa.py`;
- `docs/gui_polycom_real_hardware_qa.md`;
- `docs/gui_real_hardware_qa.md`.

## Итоговый вердикт

**Polycom hardware-проверка не пройдена.** Read-only поля, refresh,
terminal/debug view, Call Log, speaker volume/mute и microphone mute с
rollback функционально подтверждены. Presentation Start не подтвердился,
поскольку вход не подключён; финальный Stop восстановлен. Исправленный logout
подтверждён `7/7` реальными циклами, но синхронные codec controls блокируют Qt
event loop до `19 s`.
