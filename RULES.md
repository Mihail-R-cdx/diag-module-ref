---
mode: agent
apply: apply
---

# Python Execution Rules for Agent Mode

## Git Repository

Git repository initialized at `C:\root folder\git repo`.

For agent-run Git commands in this repository, use:
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/git repo" -C "C:\root folder\git repo" <git-command>`

Reason: the agent cannot persist `safe.directory` in its global `.gitconfig`, so this inline override is required across sessions.

Examples:
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/git repo" -C "C:\root folder\git repo" status`
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/git repo" -C "C:\root folder\git repo" add .`
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/git repo" -C "C:\root folder\git repo" commit -m "Initial commit"`
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/git repo" -C "C:\root folder\git repo" log --oneline`
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/git repo" -C "C:\root folder\git repo" push`

## Интерпретатор Python

**Обязательное правило:** Всегда используй явный путь к Python-интерпретатору.

```yaml
python_interpreter: "C:\\Program Files\\anaconda3\\python.exe"
python_interpreter_quoted: "\"C:\\Program Files\\anaconda3\\python.exe\""
working_directory: "."  # относительный путь для избежания проблем с пробелами
```

## Работа с файлами и экранирование

**Обязательное правило:** При работе с файлами, содержащими кириллицу или специальные символы в путях, используй raw-строки (`r''`) в Python для избежания проблем с экранированием.

**Пример:**
```python
# Правильно
with open(r'gui\screens\codec_screen.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Неправильно
with open('gui\screens\codec_screen.py', 'r', encoding='utf-8') as f:
    content = f.read()  # \s может быть воспринято как escape-последовательность
```

**Совет:** При необходимости модификации файлов через Python-скрипты, создавайте отдельный скрипт и запускайте его через интерпретатор Python.
