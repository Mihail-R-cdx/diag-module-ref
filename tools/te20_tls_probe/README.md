# TE20 TLS Probe

Минимальный standalone-пробник для проверки HTTPS к Huawei TE20 через `urllib3` и legacy `SSLContext`.

## Запуск

```powershell
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe "C:\root folder\temp\diag module agent mode\diagnostic\tools\te20_tls_probe\probe_te20_https.py" --host 192.168.1.100
```

Можно проверить конкретный endpoint:

```powershell
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe "C:\root folder\temp\diag module agent mode\diagnostic\tools\te20_tls_probe\probe_te20_https.py" --host 192.168.1.100 --path "/action.cgi?ActionID=WEB_RequestSessionIDAPI"
```
