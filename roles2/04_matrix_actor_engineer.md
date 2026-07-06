# Роль: инженер persistent Matrix actor

Ты выполняешь этап 4 плана `roles2/README.md`.

## Перед началом

1. Прочитай `RULES.md`, `roles2/README.md`, оба threading-документа и
   результаты этапа 3.
2. Изучи `MatrixScreen`, `ensure_matrix_persistent_handler()`,
   `on_matrix_keepalive()`, `disconnect_matrix_persistent_handler()` и
   `ExtronIN1804Handler`.
3. Проверь Git и готовность этапов 1–3.

## Задача

Перенеси persistent Extron-сеанс в один выделенный поток-владелец. Ни GUI, ни
`QThreadPool`-задачи не должны напрямую обращаться к этому handler.

## Архитектурные требования

- QObject actor живёт в dedicated `QThread`.
- Handler создаётся actor-ом после запуска потока и никогда не покидает его.
- Connect, routing, status, keepalive и disconnect сериализованы одной
  очередью.
- Keepalive timer создаётся и работает в потоке actor-а.
- GUI общается с actor только queued signals/slots.
- Для каждой команды передаются request id, target device/IP и параметры.
- Поздний status/routing result не обновляет другой экран.
- Shutdown не использует `terminate()` и учитывает сетевой timeout.

Сохрани существующие terminal logs, routing semantics и persistent-session
поведение. Не запускай одновременно legacy keepalive и actor keepalive.

## Обязательные тесты

- все handler-методы выполняются в одном не-GUI потоке;
- routing и keepalive не пересекаются;
- несколько routing requests обрабатываются последовательно;
- stale result игнорируется после смены устройства;
- disconnect/shutdown выполняется в actor thread;
- delayed handler не блокирует GUI heartbeat;
- ошибка connect возвращает понятное состояние и не оставляет zombie thread.

## Ограничения

- Не менять Extron-команды, порт, credentials или parser.
- Не хранить handler в `VCSDiagnosticApp` как доступный GUI объект.
- Не использовать polling через `processEvents()` или nested event loop.

## Проверка готовности

- Source audit не находит прямых Matrix handler calls из GUI callbacks.
- Поток корректно завершается при смене модели и закрытии приложения.
- Полный тестовый набор проходит.
- Обнови threading-аудит и отметь только этап 4.

## Финальный ответ

Опиши actor lifecycle, сериализацию команд, shutdown, тесты и ограничения
проверки без реальной Matrix.
