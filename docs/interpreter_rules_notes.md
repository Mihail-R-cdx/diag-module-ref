---
mode: agent
apply: apply

# Python Interpreter Rules - Implementation Notes

## Key Rules from Python path.md

- **Обязательное правило:** Всегда использовать явный путь к Python-интерпретатору.
- **Интерпретатор:** "C:\\Program Files\\anaconda3\\python.exe"
- **Рабочая директория:** "." (относительный путь)

## Shell Command Execution

При выполнении shell-команд с интерпретатором Python:

```
command: ""C:\\Program Files\\anaconda3\\python.exe" --version"
cwd: "."  # относительный путь
```

## Common Issues

1. **InvalidPath error** — путь к интерпретатору должен быть правильно экранирован с кавычками.
2. **Пробелы в путях** — обязательно заключать путь в кавычки при использовании в shell-командах.
3. **cwd** — для избежания проблем с пробелами использовать относительный путь ".".
