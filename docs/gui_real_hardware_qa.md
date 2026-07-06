# Проверка GUI на реальном оборудовании

## Дополнительная проверка Polycom

Отдельная проверка `Polycom RPG 310` от 1 июля 2026 года описана в
[`docs/gui_polycom_real_hardware_qa.md`](gui_polycom_real_hardware_qa.md).
Read-only refresh и speaker volume/mute с rollback подтверждены, но итоговый
вердикт — **«не пройдена»**. После ручного reboot исправленный server logout
подтверждён семью успешными циклами без накопления сессий; async Call Log
сохраняет heartbeat `47 ms`. Presentation input физически не подключён, а
синхронные codec controls блокируют Qt heartbeat до `19 s`.

Дата проверки: 30 июня 2026 года.

## Версия Git и окружение

- Ветка `master`, `HEAD` `4082448c997b4d2157455073ac24583cfe242351`.
- Проверялось текущее рабочее дерево с незакоммиченными пользовательскими
  файлами; несвязанные изменения сохранены, коммит не создавался.
- Windows Server 2019 (`10.0.17763`), Python `3.12.9`, Qt `5.15.2`,
  PyQt `5.15.11`.
- Обязательный Anaconda-интерпретатор отсутствует; использован доступный
  Python `3.12.9`.

## Проверенные устройства

| Устройство | Адрес | Порт | ICMP/TCP | Read-only refresh |
| --- | --- | ---: | --- | --- |
| CloudLink Bar 310 | `10.10.0.x` | 443 | доступен/открыт | успешно |
| Huawei TE-20 | `10.10.0.x` | 80 | доступен/открыт | успешно |
| Huawei TE-40 | `10.10.0.x` | 443 | доступен/открыт | успешно |
| Extron IN1804 | `10.10.0.x` | 22023 | доступен/открыт | успешно |

Проверялись только четыре явно предоставленных адреса. Сканирование сети и
подключение к другим узлам не выполнялись. Все устройства успешно
аутентифицировались первой встроенной credential-парой; значения credentials
не выводились и не копировались в QA-инструменты.

## Preflight и исходные состояния

- Bar 310: не в звонке, presentation не активна, режим сна выключен,
  конференция в ожидании.
- TE-20: звонка нет, presentation остановлена, microphone mute выключен.
- TE-40: не в звонке, presentation не активна.
- IN1804: исходный активный вход — `2`.
- SIP на трёх кодеках прочитан; на момент проверки устройства показывали
  состояние «не зарегистрирован».
- До завершения read-only preflight state-changing команды не запускались.

## CloudLink Bar 310

- Session/CSRF application flow, refresh и повторный refresh успешны.
- Получены model, firmware, serial, MAC, uptime, SIP, call, presentation,
  sleep и audio states.
- Журнал звонков загружен через GUI: `4` записи; номера и содержимое записей
  не сохранялись.
- GUI volume cycle успешен: `13 → 14 → 13`; исходная громкость повторно
  прочитана с устройства и подтверждена.
- Перед presentation test устройство сообщило sleep и было пробуждено через
  подтверждённый GUI flow. Без видеосигнала Presentation Start устройство не
  подтвердило; финальное состояние повторно прочитано как `Stop`.
- Диагностический повтор без источника вернул:
  `success=0`, `error.id=100666941`, `error.code=100687877`; presentation
  осталась `Stop`. GUI показывает понятную причину «нет видеосигнала» с этими
  кодами.
- После подключения видео Bar310 автоматически сообщил `Start`. Полный GUI
  cycle успешен: `Start → Stop → Start → Stop`; первый Stop, повторный Start
  и финальный Stop подтверждены чтением с устройства.
- После исправления stdout и terminal log не содержат совпадений с
  username/password или auth payload.
- Максимальный разрыв Qt heartbeat обычного refresh — `47 ms`.
- Call Log выполняется синхронно в GUI thread: `0.47 s`, разрыв heartbeat
  `469 ms`.
- Presentation/wake flow дал разрыв heartbeat до `5.032 s`.
- Успешный presentation cycle с видео дал максимальный разрыв `422 ms`.

## Huawei TE-20

- HTTP application flow, refresh и повторный refresh успешны.
- Получены firmware, hardware/logical versions, model, serial, MAC, uptime,
  SIP, call, presentation, power, speaker/microphone и monitor-audio values.
- Журнал звонков загружен через GUI: `9` записей; персональные значения не
  сохранялись.
- GUI volume cycle успешен: `15 → 16 → 15`; исходная громкость восстановлена
  и повторно подтверждена устройством.
- Speaker mute cycle успешен: `15 → 0 → 15`; исходное значение подтверждено.
- Presentation cycle успешен: `Stopped → Started → Stopped`.
- При отдельной проверке устройство сообщило `sleep=On`. GUI-кнопка
  «Разбудить» выполнена; повторное чтение подтвердило `sleep=Off`.
- Три последовательных monitor-audio poll успешны, максимум `16 ms`.
- Максимальный разрыв Qt heartbeat — `47 ms`.
- После исправления stdout и terminal log не содержат credentials, session
  data или auth payload.

## Huawei TE-40

- HTTPS application flow, refresh и повторный refresh успешны; fallback не
  потребовался.
- Получены firmware, model, serial, MAC, uptime, SIP, call, presentation и
  speaker/microphone states.
- Журнал звонков загружен через GUI: `10` записей; персональные значения не
  сохранялись.
- GUI volume cycle успешен: `13 → 14 → 13`; исходная громкость восстановлена
  и повторно подтверждена устройством.
- Speaker mute cycle успешен: `13 → 0 → 13`; исходное значение подтверждено.
- Без сигнала на презентационном входе Start не подтверждался. После
  подключения сигнала повторный GUI cycle успешен:
  `Stop → Start → Stop`; финальный `Stop` подтверждён.
- Диагностический повтор без сигнала вернул:
  `success=0`, `error.id=100666963`, `error.code=100687877`; состояние
  осталось `Stop`. GUI теперь показывает понятную причину «нет видеосигнала»
  с этими кодами вместо общего warning.
- Обычный refresh сохраняет heartbeat в пределах `47 ms`.
- Синхронный volume flow дал максимальный разрыв heartbeat `1.031 s`.
- Mute flow дал разрыв heartbeat `1.093 s`. Успешный presentation cycle с
  подключённым сигналом — `953 ms` (первая попытка без сигнала — `1.500 s`).
- Call Log выполняется синхронно в GUI thread: `0.75 s`, разрыв heartbeat
  `750 ms`.
- После исправления stdout и terminal log не содержат credentials или
  response body с session data.

## Extron IN1804

- Device information, input/output names, signal, HDCP, routing и status
  refresh получены успешно.
- Исходный routing перед управляющим тестом — вход `2`.
- GUI routing cycle успешен: `2 → 1 → 2`; целевой и восстановленный маршруты
  подтверждены чтением с устройства.
- Persistent session установлена. Три read-only keepalive/status-запроса
  успешны; максимум `0.907 s`.
- Cleanup успешен: persistent handler закрыт, keepalive timer остановлен.
- После refresh stdout и terminal log не содержат credentials.
- Основной worker работает вне GUI thread, но последующее создание persistent
  handler выполняется синхронно: воспроизводимый разрыв Qt heartbeat
  `4.125–4.141 s`.
- Keepalive также синхронен в GUI thread и может блокировать его до `0.907 s`.

## Отзывчивость GUI и race-сценарии

- Обычные codec refresh выполняются через workers и сохраняют Qt heartbeat.
- Сценарий Bar310 → TE-40 во время активного read-only запроса успешно
  отбрасывает поздний результат: данные Bar310 не применились к экрану TE-40.
- Найден и исправлен lifecycle-дефект: после такого переключения refresh
  оставался disabled. Теперь progress закрывается, кнопка восстанавливается,
  повторный реальный race проходит.
- Duplicate click пользовательской кнопки заблокирован её disabled state.
- Реальные auth-error и connection-timeout не провоцировались, чтобы не
  создавать lockout и не обращаться к невыделенному тестовому адресу.
- Закрытие завершает workers и persistent Extron session штатно.

## Команды, меняющие состояние

После отдельного подтверждения пользователя выполнен только тест громкости
динамиков через реальные GUI controls:

- Bar 310: `13 → 14 → 13`, восстановление подтверждено;
- TE-20: `15 → 16 → 15`, восстановление подтверждено;
- TE-40: `13 → 14 → 13`, восстановление подтверждено.

Также после отдельного разрешения выполнена GUI-команда wake для TE-20:
`sleep On → Off`; awake state подтверждён. Обратного перевода в сон не было,
поскольку пользователь разрешил оставить устройство пробуждённым, а отдельной
безопасной GUI-команды sleep нет.

Дополнительно выполнены:

- TE-20 speaker mute: `15 → 0 → 15`, восстановлен;
- TE-40 speaker mute: `13 → 0 → 13`, восстановлен;
- TE-20 presentation: `Stopped → Started → Stopped`, восстановлена;
- Bar310 без видео: ожидаемая no-signal ошибка и итоговый `Stop`; после
  подключения видео: `Start → Stop → Start → Stop`, восстановлена;
- TE-40 presentation с подключённым входным сигналом:
  `Stop → Start → Stop`, восстановлена;
- IN1804 routing: `2 → 1 → 2`, восстановлен.

Перед командами подтверждено отсутствие активного звонка. SIP fix,
reboot/reset/upgrade и другие необратимые команды не запускались. Все
изменённые volume/mute/presentation/routing states восстановлены; кодеки
намеренно оставлены awake по разрешению пользователя.

## Автоматические и regression-тесты

- Полный hardware-free набор после исправлений: `39` тестов, `OK`.
- `compileall` для `main.py`, `gui`, `core`, `handlers`, `tests` и QA-runner:
  успешно.
- Добавлены regression-тесты redaction для Bar310, TE20 и TE40.
- Добавлен regression-тест восстановления refresh после смены устройства во
  время запроса.
- `tools/real_hardware_readonly_smoke.py` повторяет штатный GUI flow,
  измеряет Qt heartbeat и выводит только обезличенные агрегаты.

## Исправленные дефекты

1. Worker/handler logs раскрывали username/password, auth payload,
   session/CSRF data и полные response bodies. Логи обезличены без изменения
   credentials, запросов или протоколов.
2. После смены устройства во время активного запроса refresh оставался
   disabled. Смена устройства теперь сбрасывает progress и восстанавливает
   control; защита от late update сохранена.
3. TE-40 без сигнала возвращал только общий presentation warning. Ответ
   `id=100666963`, `code=100687877` теперь преобразуется в понятное сообщение
   о необходимости подключить источник; добавлен regression-тест.
4. Bar310 без источника возвращает `id=100666941`, `code=100687877`.
   Сообщение GUI уточнено до явного отсутствия видеосигнала и содержит
   диагностические коды; добавлен regression-тест.

## Изменённые файлы

- `core/worker.py`;
- `core/te20_worker.py`;
- `handlers/huawei/bar310.py`;
- `handlers/huawei/te20.py`;
- `handlers/huawei/te40.py`;
- `gui/main_window.py`;
- `gui/screens/codec_screen.py`;
- `tests/test_hardware_log_redaction.py`;
- `tools/real_hardware_readonly_smoke.py`;
- `docs/gui_real_hardware_qa.md`;
- `docs/gui_release_qa.md`.

## Непроверенные сценарии

- Microphone mute/volume: подключённые микрофоны не обнаружены, controls были
  скрыты как unavailable.
- SIP fix, reboot/reset/upgrade и прочие команды без безопасного rollback.
- Wake проверен отдельной кнопкой TE-20 и как часть presentation flow Bar310;
  отдельной wake-кнопки у остальных моделей в текущем GUI нет.
- Реальный auth-error, выделенный timeout IP и физическое отключение сети.
- Закрытие Call Log во время загрузки: текущая загрузка синхронна и не даёт
  окну обработать close до завершения запроса.

## Известные ограничения и блокеры

- `CodecScreen.open_call_log_window()` синхронно подключается и читает журнал
  в GUI thread.
- `ensure_matrix_persistent_handler()` синхронно подключает IN1804 в GUI
  thread после завершения worker.
- `on_matrix_keepalive()` синхронно выполняет сетевой запрос в GUI thread.
- Codec volume controls синхронно создают/используют handler и выполняют
  set/get в GUI thread; на TE-40 измерен stall `1.031 s`.
- Codec mute/presentation используют тот же синхронный control flow. Измерены
  stall `1.093 s` на mute TE-40, `1.500 s` на presentation TE-40 и
  `5.032 s` на presentation/wake Bar310.
- Bar310 без входного источника ожидаемо отклоняет Start с диагностическими
  кодами; с подключённым видео полный цикл `Start → Stop → Start → Stop`
  успешен.
- TE-40 требует активный сигнал на презентационном входе: без сигнала Start
  не подтверждается, с сигналом цикл `Stop → Start → Stop` успешен.
- Эти блокировки воспроизведены на реальном оборудовании и не являются
  ограничением offscreen-среды. Для исправления требуется worker/actor
  lifecycle из незавершённых этапов `roles2`.

## Итоговый вердикт

**Hardware-проверка не пройдена.** Обязательный read-only functional smoke
успешен на всех четырёх устройствах, а volume cycle успешно выполнен и
восстановлен на трёх кодеках. Mute TE20/TE40, presentation TE20, wake и
routing IN1804, presentation TE40 и presentation Bar310 с видео успешны и
завершены в подтверждённых безопасных состояниях. Bar310 без источника
корректно остаётся в `Stop` и показывает понятную ошибку. Утечки credentials
и stale-control дефект исправлены. Релиз блокируют подтверждённые зависания
GUI thread при Call Log, codec controls, создании persistent Extron session
и keepalive.
