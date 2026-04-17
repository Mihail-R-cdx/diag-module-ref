"""Скрипт для редактирования main_window.py"""

# Читаем файл
with open(r'gui\main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем код создания HuaweiBar310Worker
old_code = """            self.current_worker = HuaweiBar310Worker(
                ip_address=ip_address,
                port=self.huawei_settings.get('port', 443),
                username=creds['username'],
                password=creds['password']
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name"""

new_code = """            # Передаем creds_list в конструктор worker для корректной работы перебора
            self.current_worker = HuaweiBar310Worker(
                ip_address=ip_address,
                port=self.huawei_settings.get('port', 443),
                username=creds['username'],
                password=creds['password'],
                creds_list=creds_list
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name"""

content = content.replace(old_code, new_code)

# Записываем обратно
with open(r'gui\main_window.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Файл успешно обновлен")
