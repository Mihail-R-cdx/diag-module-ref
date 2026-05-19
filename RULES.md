---
mode: agent
apply: apply
---

# Python Execution Rules for Agent Mode

## Git Repository

Primary working Git repository:
`C:\root folder\temp\diag module agent mode\diagnostic`

Secondary repository path mentioned in older notes:
`C:\root folder\git repo`

Current state note: `C:\root folder\git repo` may be empty or have no commits. For normal work on this application, use the primary working repository above.

For agent-run Git commands in the primary working repository, use:
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/temp/diag module agent mode/diagnostic" -C "C:\root folder\temp\diag module agent mode\diagnostic" <git-command>`

Reason: the agent cannot persist `safe.directory` in its global `.gitconfig`, so this inline override is required across sessions. When commands are escalated, Git runs as user `Mih`, while the repository `.git` directory may be owned by `CodexSandboxOffline`; without the inline `safe.directory`, Git can report "detected dubious ownership".

Commit permission rule: commands that write to the Git index or create commits, such as `git add` and `git commit`, may fail inside the sandbox with `Unable to create .git/index.lock: Permission denied`. Run those commands with escalated permissions and include the inline `safe.directory` override.

Examples:
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/temp/diag module agent mode/diagnostic" -C "C:\root folder\temp\diag module agent mode\diagnostic" status`
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/temp/diag module agent mode/diagnostic" -C "C:\root folder\temp\diag module agent mode\diagnostic" add -- gui/main_window.py`
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/temp/diag module agent mode/diagnostic" -C "C:\root folder\temp\diag module agent mode\diagnostic" commit -m "Commit message"`
`"C:\Program Files\Git\cmd\git.exe" -c safe.directory="C:/root folder/temp/diag module agent mode/diagnostic" -C "C:\root folder\temp\diag module agent mode\diagnostic" log --oneline`

## Python Interpreter

Mandatory rule: always use an explicit path to the Python interpreter.

```yaml
python_interpreter: "C:\\Program Files\\anaconda3\\python.exe"
python_interpreter_quoted: "\"C:\\Program Files\\anaconda3\\python.exe\""
working_directory: "."  # relative path to avoid issues with spaces
```

## Files and Escaping

Mandatory rule: when working with files whose paths may include Cyrillic or special characters, prefer Python raw strings (`r''`) to avoid escaping issues.

Example:

```python
# Correct
with open(r'gui\screens\codec_screen.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Incorrect
with open('gui\screens\codec_screen.py', 'r', encoding='utf-8') as f:
    content = f.read()
```

Tip: if file modification through a Python helper script is needed, create a separate script and run it through the Python interpreter.

## GUI Launch Rules

Mandatory rule: launch the local GUI application as a detached process outside the sandbox. Do not run it as a blocking foreground command inside the sandbox, because timeout handling can terminate the process and close the window.

Recommended command:

```powershell
Start-Process -FilePath 'C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe' -ArgumentList '.\main.py' -WorkingDirectory 'C:\root folder\temp\diag module agent mode\diagnostic'
```

Notes:
- use an escalated run when launching the GUI from the agent
- prefer `Start-Process`, not direct blocking `python .\main.py`
- use this rule for manual testing of the local application window
