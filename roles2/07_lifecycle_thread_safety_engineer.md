# Роль: инженер lifecycle и thread safety

Ты выполняешь этап 7 плана `roles2/README.md`.

## Перед началом

1. Прочитай все документы и результаты этапов 1–6.
2. Повторно проаудируй `gui`, `core` и callbacks timers/signals.
3. Проверь Git и сохрани несвязанные изменения.

## Задача

Закрой оставшиеся lifecycle- и thread-safety-пробелы после миграции команд.
Это не этап новой архитектуры: исправляй только остаточные блокировки,
cleanup, stale results и состояние controls.

## Обязательные проверки и исправления

- Ни один `connect`, `disconnect`, handler read/write или polling не
  выполняется в GUI thread.
- Смена device/IP инвалидирует связанные operations.
- Закрытие окна останавливает GUI timers, инициирует безопасный shutdown
  actors и не обращается к удалённым QObject.
- Worker references живут до finished и затем освобождаются.
- Ошибка и exception всегда снимают scoped busy-state.
- Duplicate dangerous action блокируется до завершения.
- Network operations имеют конечные timeout на уровне существующего handler
  API; не меняй протокол, если timeout нельзя добавить локально и безопасно.
- Никакие logs/errors не раскрывают credentials.
- Старые legacy helpers не остаются доступным обходным синхронным путём.

Обнови `docs/gui_blocking_io_audit.md`: каждая строка должна иметь статус
`исправлено`, `не сетевой вызов` или точный нерешённый blocker.

## Обязательные тесты

- close during delayed command;
- device/IP switch during delayed result;
- actor shutdown при connect/command error;
- отсутствие сигналов к deleted widgets;
- heartbeat при задержке каждого класса operation;
- source-contract проверка отсутствия известных прямых GUI handler calls;
- полный существующий набор тестов.

## Ограничения

- Не ослабляй тесты для достижения зелёного результата.
- Не используй принудительное завершение потоков.
- Не объявляй риск устранённым при наличии хотя бы одного сетевого GUI path.

## Проверка готовности

- Threading-аудит не содержит нерешённых GUI-thread сетевых операций.
- Все hardware-free тесты проходят детерминированно.
- После проверки отмечен только этап 7.

## Финальный ответ

Начни с вердикта по технической готовности к финальному QA, затем перечисли
закрытые остаточные риски, тесты и любые блокеры.
