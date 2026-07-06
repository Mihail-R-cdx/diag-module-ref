# Дизайн-система GUI

## Назначение

Единая тема находится в `gui/theme.py` и рассчитана на PyQt5 со стилем
`Fusion`. Она задаёт визуальную основу референса `ToBeGUI.png`: почти чёрный
фон, несколько уровней тёмных поверхностей, тонкие холодно-серые границы,
синий основной action, зелёные успешные/активные состояния, красные опасные
состояния и оранжевые предупреждения.

Тема не меняет layout экранов и бизнес-логику. Старый словарь `colors`
сохраняется через `legacy_colors()`, поэтому экраны можно переводить на новые
правила поэтапно.

## Архитектура

`gui/theme.py` экспортирует:

- `COLORS` — семантическая палитра;
- `SPACING` — шкала отступов;
- `RADII` — радиусы;
- `SIZES` — высоты controls, ширина scroll bar и границы;
- `TYPOGRAPHY` — семейство, размеры и насыщенность шрифта;
- `legacy_colors()` — совместимый словарь для существующих экранов;
- `create_palette()` — `QPalette` для обычного и disabled-состояния;
- `build_stylesheet()` — общий QSS;
- `apply_theme(target)` — применение палитры и QSS к `QApplication` или
  отдельному окну.

В `main.py` сначала выбирается `Fusion`, затем тема применяется к
`QApplication`. `VCSDiagnosticApp.set_dark_theme()` использует тот же
`apply_theme()`, чтобы окно оставалось корректным при создании напрямую в
тестах или вспомогательных инструментах.

## Токены

### Цвета

| Семантика | Токен | Значение |
| --- | --- | --- |
| Фон приложения | `background` | `#0D1117` |
| Основная поверхность | `surface` | `#151B23` |
| Поднятая поверхность/control | `surface_raised` | `#1B232D` |
| Hover поверхности | `surface_hover` | `#222C38` |
| Граница | `border` | `#2B3644` |
| Усиленная граница | `border_strong` | `#3B495A` |
| Основное действие | `primary` | `#2F6FED` |
| Успех/активность | `success` | `#24A85A` |
| Ошибка/опасность | `danger` | `#E05260` |
| Предупреждение | `warning` | `#F59E0B` |
| Основной текст | `text_primary` | `#F2F5F8` |
| Вторичный текст | `text_secondary` | `#A6B0BE` |
| Неактивный текст | `text_muted` | `#6F7B8A` |
| Focus ring | `focus` | `#78A7FF` |

Hover и pressed-цвета действий также являются токенами, а не вычисляются в
виджетах.

### Геометрия и типографика

- Отступы: `2, 4, 8, 12, 16, 24, 32 px`.
- Радиусы: `4, 6, 8, 12 px`; `pill` предназначен для индикаторов.
- Высота обычного поля: `40 px`, компактной кнопки: `32 px`.
- Основной шрифт: `Segoe UI`, затем `Inter`, `Arial`, `sans-serif`.
- Основной текст: `10 pt`, увеличенный: `11 pt`, подпись: `9 pt`,
  заголовок: `16 pt`.

Новые layout должны брать значения из `SPACING`, а не создавать ещё одну
локальную шкалу.

## Семантические роли

QSS выбирает виджеты по dynamic property `uiRole` и `status`. Видимый текст
кнопки не должен быть селектором.

```python
refresh_button.setProperty("uiRole", "primary")
mute_button.setProperty("uiRole", "active")
delete_button.setProperty("uiRole", "danger")
card.setProperty("uiRole", "card")
status_label.setProperty("status", "success")
```

Поддерживаемые `uiRole`:

- кнопки: `primary`, `secondary` (базовый стиль), `success`, `active`,
  `danger`;
- контейнеры: `card`, `toolbar`, `statusBar`;
- labels: `fieldLabel`, `secondary`, `emptyTitle`;
- terminal output: `terminal`.

Поддерживаемые `status` для `QLabel`: `success`, `danger`, `error`, `warning`,
`muted`, `inactive`.

Если property меняется после показа виджета, QSS нужно переприменить:

```python
button.setProperty("uiRole", "active")
button.style().unpolish(button)
button.style().polish(button)
button.update()
```

Существующие ссылки на кнопки, их сигналы и обработчики при этом сохраняются.

## Покрытые состояния

Общий QSS определяет normal, hover, focus, pressed и disabled для кнопок,
полей и combo box. Также заданы:

- primary/success/active/danger variants кнопок;
- selection и disabled-состояния полей и combo box;
- таблицы, headers, selection и grid;
- вертикальные и горизонтальные scroll bars;
- карточки и group box;
- progress bar;
- checkbox/radio disabled;
- dialogs, menus, tooltips и terminal.

Focus обозначается светло-синей границей без изменения геометрии control.
Disabled-состояние остаётся читаемым, но не использует цвет активного action.

## Правила дальнейшей миграции

1. Не добавлять новые hex/rgb-цвета вне `gui/theme.py`.
2. Для нового семантического случая сначала добавить токен или роль в тему.
3. Не привязывать QSS к русскому/английскому тексту control.
4. Не удалять существующие атрибуты виджетов и signal wiring во время
   визуальной миграции.
5. Локальный `setStyleSheet()` допустим только для действительно уникальной
   визуализации; повторяющийся стиль переносится в общую тему.
6. Для цветного runtime-статуса предпочтителен property `status`; прямую
   подстановку цвета следует удалить на этапе миграции соответствующего экрана.
7. Для совместимости старые экраны получают `parent.colors`, но новые
   компоненты должны использовать semantic properties и общую тему.

## Ещё не мигрированные локальные стили

Этап 2 намеренно не перестраивает экраны целиком. Старые inline-QSS пока
остаются в:

- `gui/screens/codec_screen.py` — строки параметров и динамические controls;
- `gui/screens/matrix_screen.py` — таблица и информационная панель;
- `gui/screens/pdu_screen.py` — группы, таблица, статусы и outlet-кнопки;
- `gui/screens/audio_dsp_screen.py` — device/source cards и таблицы;
- `gui/dialogs/call_log_window.py` — таблица журнала звонков;
- первом, перекрытом более поздним определением `show_password_dialog()` в
  `gui/main_window.py`.

Их поэкранная миграция относится к следующим этапам плана.
