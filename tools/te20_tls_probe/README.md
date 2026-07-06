# TE20 TLS Probe

Минимальный standalone-пробник для проверки HTTPS к Huawei TE20 через `urllib3` и legacy `SSLContext`.

## Запуск

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe "C:\link.ru\tools\te20_tls_probe\probe_te20_https.py" --host link.ru
```

Можно проверить конкретный endpoint:

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe "C:\link.ru\tools\te20_tls_probe\probe_te20_https.py" --host link.ru --path "/action.cgi?ActionID=WEB_RequestSessionIDAPI"
```
