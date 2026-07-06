# План устранения блокировки GUI event loop

## Цель

Устранить критический риск зависания PyQt5-интерфейса: ни один сетевой
`connect`, `disconnect`, read/write или handler-команда не должен выполняться
в GUI thread.

План не предназначен для изменения протоколов, credentials или бизнес-смысла
команд. Каждая роль запускается в отдельной новой сессии строго по порядку.

## Порядок запуска

| Этап | Роль | Промт | Основной результат |
| --- | --- | --- | --- |
| 1 | Аудитор блокирующих операций | `roles2/01_blocking_io_auditor.md` | Полная карта синхронных GUI-вызовов |
| 2 | Архитектор command workers | `roles2/02_command_worker_architect.md` | Общая безопасная worker-инфраструктура |
| 3 | Инженер Call Log и PDU | `roles2/03_call_log_pdu_engineer.md` | Фоновые call log и PDU-команды |
| 4 | Инженер Matrix actor | `roles2/04_matrix_actor_engineer.md` | Persistent Matrix-сеанс вне GUI thread |
| 5 | Инженер Codec controls | `roles2/05_codec_controls_engineer.md` | Фоновые volume/mute-команды |
| 6 | Инженер Codec workflows | `roles2/06_codec_workflows_engineer.md` | Presentation, wake и polling вне GUI thread |
| 7 | Инженер lifecycle и thread safety | `roles2/07_lifecycle_thread_safety_engineer.md` | Cleanup, stale results, timeouts и полный аудит |
| 8 | Финальный QA-инженер | `roles2/08_event_loop_release_qa.md` | Доказательство отзывчивости и финальный вердикт |

## Чек-лист

- [ ] Этап 1 — аудит блокирующих операций
- [ ] Этап 2 — общая command-worker инфраструктура
- [ ] Этап 3 — Call Log и PDU
- [ ] Этап 4 — Matrix actor
- [ ] Этап 5 — Codec volume/mute
- [ ] Этап 6 — Codec presentation/wake/polling
- [ ] Этап 7 — lifecycle и полный thread-safety аудит
- [ ] Этап 8 — финальная приёмка

## Общие обязательные правила

- Полностью прочитать `RULES.md`, этот файл и результаты предыдущих этапов.
- Проверить Git и сохранить несвязанные пользовательские изменения.
- Не подключаться к реальному оборудованию без явного указания пользователя.
- Не менять credentials, протоколы, retry-политику и смысл device-команд.
- Не передавать один handler между произвольными потоками.
- Handler должен создаваться, использоваться и закрываться в одном worker или
  в одном выделенном потоке-владельце.
- Виджеты разрешено читать и изменять только в GUI thread.
- Worker получает снимок входных данных, а не ссылки на изменяемые виджеты.
- Не использовать `QThread.terminate()` и принудительное уничтожение потоков.
- Не создавать коммит без отдельного запроса.
- После успешной проверки отмечать только свой этап в этом чек-листе.

## Общий критерий завершения

При искусственной задержке handler на две секунды окно продолжает обрабатывать
перемещение, переключение экранов и Qt-таймер heartbeat. Поздние результаты не
применяются после смены модели/IP или закрытия окна, а опасная команда не
дублируется повторным нажатием.

## Дополнительная hardware-проверка

После завершения программных этапов в отдельной сессии можно запустить
`roles2/09_real_hardware_qa.md`. Эта роль проверяет GUI на Huawei TE-20,
Huawei TE-40, CloudLink Bar 310 и Extron IN1804. Read-only проверки разрешены
в рамках указанных пользователем адресов; любые команды, меняющие состояние,
требуют отдельного подтверждения и обязательного восстановления.

Текущее сопоставление оборудования:

- `link.ru` — CloudLink Bar 310;
- `link.ru` — Huawei TE-20;
- `link.ru` — Huawei TE-40;
- `link.ru` — Extron IN1804.

## Отдельная приёмка Polycom

Для совершенно новой программы с тем же внешним GUI используй
`roles2/10_polycom_rpg310_real_hardware_qa.md`. Роль является независимым
black-box/contract протоколом и не опирается на язык, toolkit, структуру
файлов или архитектуру текущего проекта. Она учитывает динамический DHCP,
server-side Logout, лимит Web UI сессий, независимый SSH, partial results,
Polycom volume step, physical mic/presentation availability, heartbeat, race
и cleanup.
