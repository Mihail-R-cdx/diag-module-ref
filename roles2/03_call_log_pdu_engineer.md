# Роль: инженер фоновых Call Log и PDU-команд

Ты выполняешь этап 3 плана `roles2/README.md`.

## Перед началом

1. Прочитай `RULES.md`, `roles2/README.md`,
   `docs/gui_blocking_io_audit.md` и `docs/gui_command_worker_contract.md`.
2. Изучи Call Log paths всех кодеков, `PDUScreen`,
   `VCSDiagnosticApp.control_pdu_outlet()` и существующий `AtenPDUWorker`.
3. Проверь готовность этапов 1–2 и Git.

## Задача

Перенеси получение журнала звонков и PDU on/off/reboot из GUI thread в
одноразовые command workers, не меняя команды и протоколы.

## Call Log

- Открывай диалог сразу и показывай loading.
- Создавай, используй и закрывай codec handler внутри worker.
- Передавай в GUI только нормализованные записи или ошибку.
- Не обновляй закрытый диалог и не применяй результат после смены
  device/IP.
- Запрещай параллельную загрузку одного журнала.

## PDU

- Создавай Aten handler, выполняй `connect`, команду и `disconnect` в worker.
- Блокируй только controls выбранной розетки.
- Не допускай duplicate on/off/reboot до finished.
- Запускай refresh после подтверждённого успеха через существующий безопасный
  refresh flow.
- При ошибке возвращай controls в доступное состояние и показывай однозначный
  статус.

## Обязательные тесты

- delayed call log и PDU handler не останавливают heartbeat;
- handler создан и использован не в GUI thread;
- duplicate PDU click создаёт ровно одну команду;
- stale call-log result игнорируется;
- success/error восстанавливают scoped controls;
- disconnect вызывается в worker при успехе и исключении;
- существующая нормализация максимум десяти call records сохранена.

## Ограничения

- Не менять PDU confirmation dialog и смысл on/off/reboot.
- Не менять codec call-log команды.
- Не обращаться к реальному оборудованию.
- Не начинать миграцию Matrix и остальных Codec controls.

## Проверка готовности

- В Call Log и PDU paths нет сетевого I/O из GUI thread.
- Полный набор тестов проходит.
- Обнови `docs/gui_blocking_io_audit.md` фактическим статусом этих цепочек.
- После проверки отмечен только этап 3 в `roles2/README.md`.

## Финальный ответ

Перечисли мигрированные операции, изменённые файлы, тесты, thread guarantees
и оставшиеся синхронные цепочки.
