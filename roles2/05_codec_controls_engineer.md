# Роль: инженер фоновых Codec volume/mute controls

Ты выполняешь этап 5 плана `roles2/README.md`.

## Перед началом

1. Прочитай `RULES.md`, `roles2/README.md`, threading-аудит, worker contract и
   результаты этапов 3–4.
2. Изучи все volume/mute methods, `_get_or_create_volume_handler()`, delayed
   refresh timers и device-specific handler API.
3. Проверь Git и готовность этапов 1–4.

## Задача

Убери синхронные Codec volume/mute connect, command, readback и disconnect из
GUI thread для всех поддерживаемых кодеков.

## Требования

- Worker получает snapshot device/IP/credentials/target value.
- Handler целиком создаётся и закрывается внутри worker.
- Speaker и microphone semantics, диапазоны и mute-логика сохраняются.
- Во время команды блокируется только соответствующая группа controls.
- Повторные быстрые изменения коалесцируются: выполняется текущее действие и
  затем последнее запрошенное значение, а не очередь всех промежуточных
  кликов.
- Readback запускается асинхронно и не перезаписывает более новое значение.
- Ошибка возвращает controls в доступное состояние и не подтверждает
  неподтверждённое значение.
- Старый `volume_session_handler` не должен использоваться из GUI thread.

## Обязательные тесты

- delayed set/get volume не блокирует heartbeat;
- handler вызывается не в GUI thread;
- серия быстрых кликов не создаёт серию опасных сетевых вызовов;
- mute/unmute сохраняет restore-value;
- stale readback не откатывает более новую команду;
- ошибки и исключения восстанавливают кнопки;
- все четыре codec model paths сохраняют прежние ranges и method selection.

## Ограничения

- Не менять handler API, диапазоны или пользовательскую семантику.
- Не мигрировать presentation/wake/monitor polling — это этап 6.
- Не обращаться к оборудованию.

## Проверка готовности

- Volume/mute path не содержит сетевых handler calls в GUI thread.
- Existing codec tests и новый delayed-handler набор проходят.
- Обнови threading-аудит и отметь только этап 5.

## Финальный ответ

Опиши worker flow, coalescing, readback ordering, тесты и оставшиеся Codec
блокировки.
