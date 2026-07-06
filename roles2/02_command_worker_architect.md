# Роль: архитектор фоновых command workers

Ты выполняешь этап 2 плана `roles2/README.md`.

## Перед началом

1. Полностью прочитай `RULES.md` и `roles2/README.md`.
2. Полностью прочитай `docs/gui_blocking_io_audit.md`.
3. Изучи существующие `WorkerSignals`, `QRunnable`, `QThreadPool`,
   request identity и UI states.
4. Проверь готовность этапа 1 и состояние Git.

## Задача

Создай минимальную общую инфраструктуру для выполнения одноразовых device
commands вне GUI thread. Пока не мигрируй Matrix, PDU и Codec product-flow:
этим займутся следующие роли.

## Обязательный результат

Реализуй переиспользуемый command worker со следующими свойствами:

- immutable context: request id, device, IP, action и безопасные параметры;
- сигналы result, error, status, terminal log и finished;
- выполнение callable/operation в `QThreadPool`;
- нормализованная ошибка без утечки credentials;
- `finally` cleanup;
- cancellation/stale marker означает «не применять результат», а не
  небезопасное принудительное завершение потока;
- worker не читает и не изменяет QWidget;
- handler не передаётся из GUI и создаётся внутри операции.

Определи небольшой GUI-side coordinator или helper для:

- регистрации активной команды;
- проверки request identity;
- запрета дублирования одного action;
- scoped busy-state только связанных controls;
- безопасного удаления ссылки после finished.

Добавь документ `docs/gui_command_worker_contract.md` с правилами использования
инфраструктуры следующими этапами.

## Обязательные тесты

- медленная операция выполняется не в `QApplication.thread()`;
- heartbeat GUI продолжает срабатывать во время задержки;
- result/error доставляются в GUI thread;
- поздний результат отклоняется по request id;
- duplicate action не запускается второй раз;
- cleanup выполняется при успехе и исключении;
- текст ошибки не содержит переданный тестовый secret.

## Ограничения

- Не создавай worker, который захватывает QWidget, экран или main window.
- Не передавай существующий handler в `QThreadPool`.
- Не меняй device handlers и сетевые протоколы.
- Не мигрируй конкретные команды до следующих этапов.

## Проверка готовности

- Все новые тесты hardware-free и детерминированы.
- Инфраструктура не нарушает существующие refresh workers.
- Полный набор тестов проходит.
- После проверки отмечен только этап 2 в `roles2/README.md`.

## Финальный ответ

Опиши API worker/coordinator, thread ownership, защиту от stale/duplicate
результатов, тесты и ограничения.
