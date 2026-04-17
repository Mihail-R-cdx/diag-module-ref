#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для диагностики повреждений в worker.py"""

with open(r'core\worker.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

print(f"Всего строк: {len(lines)}")

# Ищем JSON-объект в файле
import re
json_matches = re.findall(r'\{[^}]*"text"[^}]*\}', content, re.DOTALL)
if json_matches:
    print(f"Найдено {len(json_matches)} JSON-объектов в файле")
    with open(r'debug_output.txt', 'w', encoding='utf-8') as f:
        f.write(f"Всего строк: {len(lines)}\n\n")
        f.write("--- Строки 350-380 ---\n")
        for i in range(349, min(380, len(lines))):
            f.write(f"{i+1:4d}: {repr(lines[i])}\n")
        
        f.write("\n--- Строки 380-410 ---\n")
        for i in range(379, min(410, len(lines))):
            f.write(f"{i+1:4d}: {repr(lines[i])}\n")
        
        f.write(f"\nНайдено {len(json_matches)} JSON-объектов в файле:\n")
        for i, match in enumerate(json_matches):
            f.write(f"\n--- JSON #{i+1} ---\n")
            f.write(match[:1000])
    
    print("Результаты записаны в debug_output.txt")
else:
    print("JSON-объектов не найдено")
