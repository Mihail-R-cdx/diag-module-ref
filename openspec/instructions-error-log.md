# Инструкции, где раньше были ошибки

**Правка файлов в worktree** — используй `single_find_and_replace` с путём относительно `.worktrees/implementation-matrix-immutable-515211c5/...`; `edit_existing_file` с worktree-путём падает (только читает основной checkout). Редактируй по одному `single_find_and_replace` за раз: параллельные вызовы правки импортов в один файл конфликтуют и портят содержимое. Не используй для правки файлов bash `sed`/`awk`.

**Python** — НЕ используй команду `python` из PATH (её нет). Запускай тесты только через явный путь `$Python = "C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe"` и затем `& $Python -m unittest ...`. Для точного exit-кода используй `*> "логи.log"` и `$LASTEXITCODE`, а не `2>&1 | Select-Object` (последнее в PowerShell превращает stderr в ошибку и искажает результат).

**OpenSpec** — `.\openspec.cmd` не найдёт `node_modules` в чистом sibling worktree. Сначала выполни `npm ci` (после добавления portable Node в PATH), иначе `openspec.cmd` упадёт с "missing dependency". Устанавливай node-путь только через env `DIAG_NODE_HOME` в памяти процесса, не добавляя user-specific полный путь в tracked-файлы.

**Worktree и ветки** — рабочий git-репозиторий это `.worktrees/...`, а не основной checkout; `git status/diff/log/пуш` выполняй внутри worktree. `view_diff` показывает диф основного checkout, а не worktree — для дифв ворктри используй `git diff --name-only` / `git diff`.

**Коммиты/пуш** — пушь через `git push origin HEAD:agent/<branch>`, а не `git push` (текущая ветка `codex/...` не является review-веткой). После пуша в уже существующий PR его надо вручную пометить "ready for review" через `gh pr ready <номер>`, т.к. `gh pr create`/новый коммит не делает этого автоматически.

**Worktree не содержит `node_modules`** — проверить заранее перед openspec-валидацией командой `Test-Path`.

**Файлы screen-модулей в worktree** — вставляй новый метод аккуратно: проверь, что код `__init__` не оказался поглощён телом нового метода (audio_dsp_screen). После правки запускай `ast.parse` по каждому изменённому файлу.

**gui/main_window.py (очень большой, >28k токенов)** — `single_find_and_replace`/`edit_existing_file` вешают VSCode и молча не применяют правки. Применяй все правки этого файла через Python-хелпер: последовательные `str.replace(old, new, 1)` с проверкой `count==1` (уникальность якоря), затем `ast.parse`.

**Инвалидация switch-контекста при смене снапшота** — `replace_equipment_inventory_state` вызывает `_supersede_model_actions`, который очищает активный контекст устройства, поэтому `_current_equipment_switch_binding()` возвращает None и републикация прерывается до инвалидации. Сначала принудительно увеличь `_equipment_switch_context_generation` и обнули `_equipment_switch_context_binding`, затем пытайся републиковать — иначе устаревшая публикация со старым binding примет `_accept_equipment_switch_publication`.
