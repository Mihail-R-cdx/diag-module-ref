# TE20 HTTP:80 Check

Standalone-утилита без зависимостей от текущего проекта. Она:

- читает список IP из `.txt` файла
- читает логин/пароль из `.json`
- проверяет TCP доступность `80` порта
- делает `POST` на:
  - `WEB_RequestSessionIDAPI`
  - `WEB_RequestCertificateAPI`
- сохраняет отчёты в `json`, `csv` и `txt`

## Формат файлов

### IP list

`ips.txt`

```text
192.168.1.100
192.168.1.101
192.168.1.102
```

### Credentials

`creds.json`

```json
{
  "username": "api",
  "password": "pass"
}
```

## Запуск

```powershell
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe "C:\root folder\temp\diag module agent mode\diagnostic\tools\te20_http80_check\check_te20_http80.py" --ips "C:\path\ips.txt" --creds "C:\path\creds.json"
```

## Результаты

В папке `output/<timestamp>/` создаются:

- `results.json`
- `results.csv`
- `summary.txt`

## Значения overall

- `api_available` — API по `HTTP:80` отвечает успешно хотя бы на один из двух запросов
- `http_open_but_api_rejected` — порт `80` доступен, но TE20 отвергает API
- `http_failed` — HTTP-запрос не удался
- `port_closed` — TCP подключение к `80` не открылось
- `no_ping` — устройство не отвечает на `ping`
- `bad_password` — порт `80` доступен, но логин/пароль отклонены
- `http_disabled` — порт `80` доступен, но HTTP policy/API на TE20 выключены

## Формат summary.txt

Итоговый `summary.txt` содержит по одной строке на устройство в одном из форматов:

```text
<ip> - ok
<ip> - err (password)
<ip> - err (no 80)
<ip> - err (no ping)
<ip> - err (http off)
```
