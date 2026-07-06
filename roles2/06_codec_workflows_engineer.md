# Роль: инженер фоновых Codec workflows

Ты выполняешь этап 6 плана `roles2/README.md`.

## Перед началом

1. Прочитай обязательные правила, threading-аудит, worker contract и
   результаты этапа 5.
2. Изучи presentation, sleep/wake, `_wait_until_device_wakes()`,
   `_run_presentation_countdown()`, monitor audio polling и их timers.
3. Проверь Git и готовность этапов 1–5.

## Задача

Перенеси presentation, sleep/wake и monitor-audio polling из GUI thread,
устранив сетевой I/O и вложенные event loops в GUI.

## Требования

- Presentation command и readback выполняются worker-ом.
- Проверка sleep, wake command и ожидание пробуждения выполняются вне GUI
  thread как последовательный workflow.
- Пользовательское подтверждение пробуждения остаётся в GUI до запуска
  worker-а.
- Countdown реализуется обычным GUI `QTimer` без nested `QEventLoop`.
- Monitor-audio timer только инициирует фоновый запрос.
- Пока предыдущий poll активен, следующий tick пропускается или
  коалесцируется.
- Presentation/wake controls имеют scoped busy-state.
- Смена устройства, закрытие экрана или новый workflow инвалидируют старые
  результаты.
- Terminal log доставляется сигналами и не содержит secrets.

## Обязательные тесты

- delayed presentation и wake polling не блокируют heartbeat;
- в GUI thread нет handler sleep/read/write;
- countdown не запускает nested event loop;
- monitor polling не выполняется параллельно сам с собой;
- stale workflow не обновляет новый device screen;
- cancel в confirmation не создаёт worker;
- timeout и wake failure корректно возвращают controls;
- существующие TE20 sleeping states сохраняются.

## Ограничения

- Не менять device commands и timeout semantics без явного обоснования.
- Не маскировать failure как success.
- Не подключаться к реальным кодекам.

## Проверка готовности

- Presentation/wake/polling paths не выполняют сеть в GUI thread.
- Полный тестовый набор проходит.
- Обнови threading-аудит и отметь только этап 6.

## Финальный ответ

Опиши state machine/workflow, timers, stale protection, тесты и оставшиеся
threading-риски.
