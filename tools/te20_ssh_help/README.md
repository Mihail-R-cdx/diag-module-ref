# TE20 SSH Help Collector

Скрипт подключается к TE20 по SSH, отправляет `?` в CLI и рекурсивно собирает help-дерево.

## Запуск

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe .\tools\te20_ssh_help\collect_te20_ssh_help.py
```

Можно передать параметры:

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe .\tools\te20_ssh_help\collect_te20_ssh_help.py --host link.ru --username admin --max-depth 4
```

Если `--host`, `--username` или `--password` не указаны, скрипт запросит их интерактивно.

## Вариант через PuTTY/plink

Если `Paramiko` не может договориться со старым SSH-стеком TE20, можно использовать `plink.exe` из комплекта PuTTY:

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe .\tools\te20_ssh_help\collect_te20_ssh_help_plink.py --plink-path "C:\Users\admin\Downloads\putty-0.73-ru-17\PuTTY\plink.exe" --host link.ru --username admin
```

Пароль при этом будет запрошен интерактивно.

## Что сохраняется

После запуска создаётся папка:

```text
tools/te20_ssh_help/output/<ip>_<timestamp>/
```

Внутри:

- `session.txt` — текстовый отчёт
- `session.json` — структурированный дамп с сырым выводом и найденными командами

## Замечания

- По умолчанию используется логин `debug`, потому что он чаще всего встречается в документации Huawei для SSH CLI.
- Глубина обхода по умолчанию `3`, чтобы не уходить в слишком долгий сбор.
- Если CLI поддерживает слишком большой help-лес, увеличивай `--max-depth` постепенно.
