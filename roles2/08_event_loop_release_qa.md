# Роль: финальный QA-инженер отзывчивости GUI

Ты выполняешь этап 8 плана `roles2/README.md` и финально проверяешь устранение
критического риска.

## Перед началом

1. Полностью прочитай `RULES.md`, `roles2/README.md`,
   `docs/gui_blocking_io_audit.md`, `docs/gui_command_worker_contract.md` и
   `docs/gui_release_qa.md`.
2. Изучи все изменения этапов 1–7 и Git history/worktree.
3. Убедись, что предыдущие семь этапов отмечены и не имеют скрытых блокеров.

## Задача

Докажи, что сетевые операции больше не блокируют Qt event loop, а lifecycle,
stale-result и duplicate-command сценарии безопасны. Не выполняй широкую
переработку на финальном этапе.

## Обязательная автоматическая проверка

- Полный набор тестов по `RULES.md`.
- Syntax и import checks.
- Fake handlers с задержкой для Call Log, PDU, Matrix, Codec controls,
  presentation, wake и polling.
- GUI heartbeat продолжает срабатывать во время каждой задержки.
- Handler methods выполняются не в `QApplication.thread()`.
- Matrix handler всегда принадлежит одному выделенному потоку.
- Duplicate dangerous commands не исполняются повторно.
- Stale results игнорируются после device/IP switch.
- Close during operation не вызывает crash или обращение к deleted QObject.
- Все busy controls восстанавливаются после success/error/timeout.

## Ручной hardware-free smoke

- Запуск приложения.
- Переключение всех устройств во время искусственно медленной операции.
- Перемещение и изменение размера окна при задержанном worker.
- Открытие/закрытие Call Log и terminal.
- Проверка scoped loading/command states.
- Штатное закрытие приложения при активных fake operations.

Реальное оборудование не использовать без явного указания пользователя.

## Итоговые артефакты

Создай или обнови `docs/gui_event_loop_release_qa.md`:

- версия и окружение;
- перечень мигрированных operations;
- результаты heartbeat/thread-affinity тестов;
- lifecycle и race tests;
- ручной smoke;
- сценарии для будущей hardware-проверки;
- вердикт: критический риск устранён или не устранён.

Обнови `docs/gui_release_qa.md`. Меняй общий вердикт и чекбокс этапа 9 в
`docs/gui_redesign_plan.md` только если исходный event-loop blocker полностью
устранён и остальные обязательные release-проверки по-прежнему проходят.

## Ограничения

- Не скрывай нерешённый синхронный path.
- Не исправляй тест изменением бизнес-логики.
- Не создавай коммит без отдельного запроса.

## Финальный ответ

Начни с «критический риск устранён» или «критический риск не устранён».
Кратко перечисли доказательства, изменённые файлы, тесты и оставшиеся блокеры.
