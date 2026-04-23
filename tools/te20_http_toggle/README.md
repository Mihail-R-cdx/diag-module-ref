# TE20 HTTP Toggle

Отдельная утилита для переключения `enable_http` на Huawei TE20 через `WEB_GetCfgParamAPI` и `WEB_SaveCfgParamAPI`.

## Запуск

```powershell
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe .\tools\te20_http_toggle\toggle_te20_http.py --host 192.168.1.100 --username api --mode enable
```

Если пароль не указан аргументом, утилита запросит его интерактивно.

## Режимы

Включить HTTP:

```powershell
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe .\tools\te20_http_toggle\toggle_te20_http.py --host 192.168.1.100 --username api --mode enable
```

Выключить HTTP:

```powershell
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe .\tools\te20_http_toggle\toggle_te20_http.py --host 192.168.1.100 --username api --mode disable
```

## Схема подключения

По умолчанию используется `--scheme auto`:

- сначала `HTTP:80`
- потом `HTTPS:443`

Можно явно указать:

```powershell
--scheme http
--scheme https
```

## Ограничение

Если на устройстве `HTTP` уже выключен, а Python не может договориться с `HTTPS:443` из-за старого TLS TE20, включить `enable_http` этим скриптом может не получиться. В таком случае сначала придётся включить HTTP вручную через web UI.
