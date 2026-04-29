import re
import datetime
from typing import Dict, Any


class HuaweiTE40DataParser:
    """Парсер данных для Huawei TE-40"""
    
    @staticmethod
    def parse_raw_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг сырых данных от Huawei кодеков"""
        parsed = {}
        
        if not raw_data:
            return parsed
        
        # Модель и версия
        parsed['Модель'] = raw_data.get('model', 'Huawei TE-40')
        parsed['Версия ПО'] = HuaweiTE40DataParser._clean_version(raw_data.get('version', ''))
        parsed['Серийный номер'] = raw_data.get('serial_number', 'N/A')
        parsed['MAC адрес'] = raw_data.get('mac_address', 'N/A')
        
        # Статусы SIP
        sip_status = HuaweiTE40DataParser._map_sip_status(raw_data.get('sip_status', 'Off'))
        parsed['SIP регистрация'] = sip_status
        parsed['SIP адрес'] = raw_data.get('sip_server', 'N/A')
        parsed['SIP номер'] = raw_data.get('sip_number', 'N/A')
        
        # Время работы
        parsed['Время работы'] = raw_data.get('uptime', 'N/A')
        
        # Статус звонка
        parsed['Статус звонка'] = HuaweiTE40DataParser._map_call_status(
            raw_data.get('call_status', 'No Call')
        )
        
        # Презентация
        parsed['Режим презентации'] = HuaweiTE40DataParser._map_presentation(
            raw_data.get('presentation', 'Stop')
        )
        
        # Аудио статусы
        if raw_data.get('mic_connection_status'):
            parsed['Статус микрофона'] = raw_data.get('mic_connection_status')
        else:
            parsed['Статус микрофона'] = HuaweiTE40DataParser._map_mic_status(
                raw_data.get('mic_mute', 'Off')
            )
        parsed['Статус динамика'] = HuaweiTE40DataParser._map_speaker_status(
            raw_data.get('speaker_mute', 'Off')
        )
        if 'speaker_volume' in raw_data and raw_data.get('speaker_volume') is not None:
            parsed['Громкость динамиков'] = str(raw_data.get('speaker_volume'))
        if raw_data.get('mic_connection_status') == 'Микрофон не подключён':
            parsed['Mute микрофона'] = 'Микрофон не подключён'
        elif 'mic_mute' in raw_data:
            parsed['mic_mute'] = raw_data.get('mic_mute')
            parsed['Mute микрофона'] = HuaweiTE40DataParser._map_microphone_mute_status(
                raw_data.get('mic_mute')
            )
        # Камера
        parsed['Статус камеры'] = HuaweiTE40DataParser._map_camera_status(
            raw_data.get('camera_status', 'OffOff')
        )
        
        # WAN IP
        if 'wan_ip' in raw_data:
            parsed['WAN IP'] = raw_data['wan_ip']
        
        return parsed
    
    @staticmethod
    def _clean_version(version: str) -> str:
        """Очистка версии ПО - ИСПРАВЛЕНО"""
        if not version:
            return "Unknown"
        version = version.replace("TEX0 ", "")
        # Убираем все управляющие символы
        version = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', version)
        # Убираем лишние пробелы
        version = ' '.join(version.split())
        return version.strip()
    
    @staticmethod
    def _map_sip_status(status: str) -> str:
        """Преобразование статуса SIP"""
        mapping = {
            'On': 'Зарегистрирован',
            'Off': 'Не зарегистрирован',
            'SIP_STATE_OK': 'Зарегистрирован',
            'EMPTY': 'Не зарегистрирован'
        }
        return mapping.get(status, status)
    
    @staticmethod
    def _map_call_status(status: str) -> str:
        """Преобразование статуса звонка"""
        mapping = {
            'No Call': 'Не в звонке',
            'Calling': 'В звонке',
            'Disconnected': 'Разъединен'
        }
        return mapping.get(status, status)
    
    @staticmethod
    def _map_presentation(presentation: str) -> str:
        """Преобразование статуса презентации"""
        mapping = {
            'Start': 'Демонстрируется',
            'Stop': 'Не демонстрируется',
            'auxOpen': 'Демонстрируется',
            'auxClose': 'Не демонстрируется'
        }
        return mapping.get(presentation, presentation)
    
    @staticmethod
    def _map_mic_status(mic_status: str) -> str:
        """Преобразование статуса микрофона"""
        mapping = {
            'On': 'Выключен',
            'Off': 'Включен'
        }
        return mapping.get(mic_status, mic_status)

    @staticmethod
    def _map_microphone_mute_status(status: str) -> str:
        text = str(status).strip().lower()
        if text.startswith('off') or 'включ' in text or 'unmuted' in text:
            return 'Unmuted'
        if text.startswith('on') or 'выключ' in text or 'muted' in text:
            return 'Muted'
        return str(status)
    
    @staticmethod
    def _map_speaker_status(speaker_status: str) -> str:
        """Преобразование статуса динамика"""
        mapping = {
            'On': 'Выключен',
            'Off': 'Включен'
        }
        return mapping.get(speaker_status, speaker_status)
    
    @staticmethod
    def _map_camera_status(camera_status: str) -> str:
        """Преобразование статуса камеры"""
        if camera_status == 'OffOff':
            return 'Не подключена'
        elif camera_status == 'OnOn':
            return 'Обе камеры подключены'
        elif camera_status == 'OnOff':
            return 'Камера 1 подключена'
        elif camera_status == 'OffOn':
            return 'Камера 2 подключена'
        else:
            return camera_status


class HuaweiTE20DataParser:
    """Парсер данных для Huawei TE-20"""
    
    @staticmethod
    def parse_raw_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг сырых данных от Huawei TE-20 в формат, ожидаемый маппингом"""
        parsed = {}
        
        if not raw_data:
            return parsed
        
        print("=" * 50)
        print("Парсер TE-20 получил данные:", raw_data)
        print("=" * 50)
        
        # 1. Основные поля, которые ожидает маппинг
        mapping_fields = {
            'Модель': raw_data.get('model', 'Huawei TE-20'),
            'Версия ПО': HuaweiTE20DataParser._clean_version(raw_data.get('version', '')),
            'Серийный номер': raw_data.get('serial_number', 'N/A'),
            'MAC адрес': raw_data.get('wan_mac', 'N/A'),
            'SIP регистрация': HuaweiTE20DataParser._map_sip_status(raw_data.get('sip_status', 'Off')),
            'SIP адрес': raw_data.get('sip_address', 'N/A'),
            'Время работы': raw_data.get('uptime', 'N/A'),
        }
        
        # Добавляем только непустые значения
        for key, value in mapping_fields.items():
            if value and value != 'N/A':
                parsed[key] = value
        
        # 2. Специальные поля для маппинга
        
        # Статус звонка
        if 'call_status' in raw_data:
            parsed['call_status'] = raw_data['call_status']
            # Также добавляем в Статус звонка для прямого маппинга
            parsed['Статус звонка'] = raw_data['call_status']
        
        # Режим презентации (для маппинга в Статус презентации)
        if 'presentation_local' in raw_data:
            parsed['Режим презентации'] = raw_data['presentation_local']
            # Сохраняем оригинал для специальной обработки
            parsed['presentation'] = raw_data['presentation_local']
        
        # Громкость динамика
        if 'speaker_volume' in raw_data:
            parsed['Громкость динамика'] = str(raw_data['speaker_volume'])
            parsed['speaker_volume'] = raw_data['speaker_volume']
        
        # Для обратной совместимости
        if 'mic_mute' in raw_data:
            parsed['mic_mute'] = raw_data['mic_mute']
            parsed['Mute микрофона'] = HuaweiTE20DataParser._map_mic_mute_status(raw_data['mic_mute'])
        
        # Статус микрофона
        if 'mic_version' in raw_data:
            parsed['Статус микрофона'] = (
                'Не подключён'
                if raw_data.get('mic_version') in (None, [], '', 'N/A')
                else 'Подключён'
            )
            parsed['mic_connection_status'] = parsed['Статус микрофона']
        elif 'mic_mute' in raw_data:
            parsed['Статус микрофона'] = raw_data['mic_mute']
        
        # Для TE-20 камера в интерфейсе всегда считается подключенной.
        parsed['camera_status'] = 'Подключена'
        parsed['Статус камеры'] = 'Подключена'
        
        # 3. Дополнительные поля для информации
        if 'wan_ipv4' in raw_data and raw_data['wan_ipv4']:
            parsed['WAN IP'] = raw_data['wan_ipv4']
        
        if 'remote_mic_status' in raw_data:
            parsed['Удаленный микрофон'] = raw_data['remote_mic_status']
        
        if 'conference_type' in raw_data:
            parsed['Тип конференции'] = raw_data['conference_type']
        
        if 'power_status' in raw_data:
            parsed['Статус питания'] = raw_data['power_status']

        if 'monitor_mic_value' in raw_data and raw_data['monitor_mic_value'] is not None:
            parsed['Звук в помещении (микрофон)'] = str(raw_data['monitor_mic_value'])
            parsed['monitor_mic_value'] = raw_data['monitor_mic_value']

        if 'monitor_speaker_value' in raw_data and raw_data['monitor_speaker_value'] is not None:
            parsed['Звук из динамиков (выход кодека)'] = str(raw_data['monitor_speaker_value'])
            parsed['monitor_speaker_value'] = raw_data['monitor_speaker_value']
        
        if 'hard_version' in raw_data:
            parsed['Аппаратная версия'] = raw_data['hard_version']
        
        if 'logic_version' in raw_data:
            parsed['Логическая версия'] = raw_data['logic_version']
        
        print("=" * 50)
        print("Парсер TE-20 вернул для GUI:", parsed)
        print("=" * 50)
        
        return parsed
    
    @staticmethod
    def _clean_version(version: str) -> str:
        """Очистка версии ПО"""
        if not version:
            return "Unknown"
        # Убираем все управляющие символы
        version = re.sub(r'\\[a-zA-Z]', '', version)
        version = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', version)
        # Убираем TE20 из начала строки
        version = version.replace("TE20 ", "")
        # Убираем лишние пробелы
        version = ' '.join(version.split())
        return version.strip()
    
    @staticmethod
    def _map_sip_status(status: str) -> str:
        """Преобразование статуса SIP"""
        if status == 'On':
            return 'Зарегистрирован'
        elif status == 'Off':
            return 'Не зарегистрирован'
        elif status == 'SIP_STATE_OK':
            return 'Зарегистрирован'
        else:
            return status

    @staticmethod
    def _map_mic_mute_status(status: str) -> str:
        """Преобразование состояния mute микрофона TE-20 для отображения."""
        status_text = str(status).strip().lower()
        if status_text.startswith('off') or 'включ' in status_text or 'unmuted' in status_text:
            return 'Unmuted'
        if status_text.startswith('on') or 'выключ' in status_text or 'muted' in status_text:
            return 'Muted'
        return status
        
        

class HuaweiBar310DataParser:
    """Парсер данных для Huawei CloudLink Bar 310"""
    
    @staticmethod
    def parse_raw_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг сырых данных от Huawei CloudLink Bar 310"""
        parsed = {}
        
        if not raw_data:
            return parsed
        
        # Модель и версия
        parsed['Модель'] = raw_data.get('model', 'Huawei CloudLink Bar 310')
        parsed['Версия ПО'] = HuaweiBar310DataParser._clean_version(raw_data.get('version', ''))
        parsed['Серийный номер'] = raw_data.get('serial_number', 'N/A')
        parsed['Версия микрофона'] = raw_data.get('mic_version', 'N/A')
        parsed['MAC адрес'] = raw_data.get('mac_address', 'N/A')
        
        # Статусы SIP
        sip_status = HuaweiBar310DataParser._map_sip_status(raw_data.get('sip_status', 'Off'))
        parsed['SIP регистрация'] = sip_status
        parsed['SIP адрес'] = raw_data.get('sip_server', 'N/A')
        parsed['SIP номер'] = raw_data.get('sip_number', 'N/A')
        
        # Время работы
        parsed['Время работы'] = raw_data.get('uptime', 'N/A')
        
        # Статус звонка
        parsed['Статус звонка'] = HuaweiBar310DataParser._map_call_status(
            raw_data.get('call_status', 'No Call')
        )
        
        # Тип вызова и состояние конференции
        parsed['Тип вызова'] = HuaweiBar310DataParser._map_call_type(
            raw_data.get('call_type', 'Unknown')
        )
        parsed['Состояние конференции'] = HuaweiBar310DataParser._map_conference_state(
            raw_data.get('conference_state', 'Idle')
        )
        
        # Презентация
        parsed['Режим презентации'] = HuaweiBar310DataParser._map_presentation(
            raw_data.get('presentation', 'Stop')
        )
        
        # Режим сна
        parsed['Режим сна'] = HuaweiBar310DataParser._map_sleep_mode(
            raw_data.get('sleep_mode', 'Off')
        )
        
        # Аудио статусы
        if raw_data.get('mic_connection_status'):
            parsed['Статус микрофона'] = raw_data.get('mic_connection_status')
        else:
            parsed['Статус микрофона'] = HuaweiBar310DataParser._map_mic_status(
                raw_data.get('mic_mute', 'Off')
            )
        if 'mic_volume' in raw_data and raw_data.get('mic_volume') is not None:
            parsed['Громкость микрофона'] = str(raw_data.get('mic_volume'))
        
        parsed['Статус динамика'] = HuaweiBar310DataParser._map_speaker_status(
            raw_data.get('speaker_mute', 'Off')
        )
        if 'speaker_volume' in raw_data and raw_data.get('speaker_volume') is not None:
            parsed['Громкость динамиков'] = str(raw_data.get('speaker_volume'))
        
        
        parsed['Статус камеры'] = 'Подключена'
        
        # WAN IP
        if 'wan_ip' in raw_data:
            parsed['WAN IP'] = raw_data['wan_ip']
        
        return parsed
    
    @staticmethod
    def _clean_version(version: str) -> str:
        """Очистка версии ПО"""
        if not version:
            return "Unknown"
        # Убираем все управляющие символы
        version = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', version)
        # Убираем лишние пробелы
        version = ' '.join(version.split())
        return version.strip()
    
    @staticmethod
    def _map_sip_status(status: str) -> str:
        """Преобразование статуса SIP"""
        mapping = {
            'On': 'Зарегистрирован',
            'Off': 'Не зарегистрирован',
            'SIP_STATE_OK': 'Зарегистрирован',
            'EMPTY': 'Не зарегистрирован'
        }
        return mapping.get(status, status)
    
    @staticmethod
    def _map_call_status(status: str) -> str:
        """Преобразование статуса звонка"""
        mapping = {
            'No Call': 'Не в звонке',
            'Calling': 'В звонке',
            'Disconnected': 'Разъединен',
            'Connected': 'Подключен'
        }
        return mapping.get(status, status)
    
    @staticmethod
    def _map_call_type(call_type: str) -> str:
        """Преобразование типа вызова"""
        mapping = {
            'Unknown': 'Неизвестно',
            'H.323': 'H.323',
            'SIP': 'SIP',
            'Phone call': 'Аудиозвонок',
            'H.323 (IP) call': 'H.323 звонок',
            'SIP (IP) call': 'SIP звонок',
            'ISDN call': 'ISDN звонок'
        }
        return mapping.get(call_type, call_type)
    
    @staticmethod
    def _map_conference_state(state: str) -> str:
        """Преобразование состояния конференции"""
        mapping = {
            'Idle': 'Ожидание',
            'Making call': 'Вызов',
            'Answering': 'Ответ',
            'Rejecting': 'Отклонение',
            'Unknown': 'Неизвестно'
        }
        return mapping.get(state, state)
    
    @staticmethod
    def _map_presentation(presentation: str) -> str:
        """Преобразование статуса презентации"""
        mapping = {
            'Start': 'Демонстрируется',
            'Stop': 'Не демонстрируется',
            'auxOpen': 'Демонстрируется',
            'auxClose': 'Не демонстрируется'
        }
        return mapping.get(presentation, presentation)
    
    @staticmethod
    def _map_sleep_mode(sleep_mode: str) -> str:
        """Преобразование режима сна"""
        mapping = {
            'On': 'Включен',
            'Off': 'Выключен',
            'sleep': 'Включен',
            'unsleep': 'Выключен'
        }
        return mapping.get(sleep_mode, sleep_mode)
    
    @staticmethod
    def _map_mic_status(mic_status: str) -> str:
        """Преобразование статуса микрофона (для Bar 310: On - выключен, Off - включен)"""
        mapping = {
            'On': 'Выключен',
            'Off': 'Включен'
        }
        return mapping.get(mic_status, mic_status)
    
    @staticmethod
    def _map_speaker_status(speaker_status: str) -> str:
        """Преобразование статуса динамика (для Bar 310: On - выключен, Off - включен)"""
        mapping = {
            'On': 'Выключен',
            'Off': 'Включен'
        }
        return mapping.get(speaker_status, speaker_status)


class PolycomDataParser:
    """Парсер данных для Polycom устройств"""
    
    @staticmethod
    def parse_raw_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг сырых данных от Polycom устройств"""
        parsed = {}
        
        if not raw_data:
            return parsed
        
        print("=" * 50)
        print("PolycomDataParser получил данные:", raw_data)
        print("=" * 50)
        
        # Основные поля
        parsed['Модель'] = raw_data.get('model', 'Polycom RealPresence Group 310')
        parsed['Версия ПО'] = raw_data.get('version', 'N/A')
        parsed['IP адрес'] = raw_data.get('ip_address', 'N/A')
        
        # Серийный номер
        serial = raw_data.get('serial_number')
        if serial and serial != 'N/A':
            parsed['Серийный номер'] = serial
        
        # Время работы
        uptime = raw_data.get('uptime')
        if uptime and uptime != 'N/A':
            parsed['Время работы'] = uptime
        
        # SIP регистрация
        sip_status = raw_data.get('sip_status')
        if sip_status:
            if sip_status == 'online':
                parsed['SIP регистрация'] = 'Зарегистрирован'
            elif sip_status == 'offline':
                parsed['SIP регистрация'] = 'Не зарегистрирован'
            else:
                parsed['SIP регистрация'] = sip_status.capitalize()
        
        # Статус звонка
        call_status = raw_data.get('call_status', 'No Call')
        parsed['Статус звонка'] = PolycomDataParser._map_call_status(call_status)
        
        # Громкость
        volume = raw_data.get('speaker_volume')
        if volume is not None:
            parsed['Громкость динамиков'] = f"{volume}%"
            print(f"Добавлена громкость: {parsed['Громкость динамиков']}")
        
        # Статус микрофона
        mic_mute = raw_data.get('mic_mute')
        if mic_mute:
            parsed['mic_mute'] = mic_mute
            parsed['Статус микрофона'] = 'Подключён'
            parsed['Mute микрофона'] = PolycomDataParser._map_mic_status(mic_mute)
        else:
            parsed['Статус микрофона'] = 'Подключён'

        # Статус презентации
        presentation = raw_data.get('presentation')
        if presentation:
            parsed['Режим презентации'] = PolycomDataParser._map_presentation(presentation)

        # Статус камеры
        camera_source = raw_data.get('camera_source')
        camera_status = raw_data.get('camera_status')
        if camera_source == -1:
            parsed['Статус камеры'] = 'Не подключена'
        elif camera_status:
            parsed['Статус камеры'] = PolycomDataParser._map_camera_status(camera_status)
        
        print("=" * 50)
        print("PolycomDataParser вернул для GUI:", parsed)
        print("=" * 50)
        
        return parsed
    

    @staticmethod
    def _map_call_status(status: str) -> str:
        """Преобразование статуса звонка"""
        mapping = {
            'Active': 'Активен',
            'Incoming': 'Входящий',
            'Registered': 'Зарегистрирован',
            'Ended': 'Завершен',
            'No Call': 'Нет звонка'
        }
        return mapping.get(status, status)
    
    @staticmethod
    def _map_mic_status(status: str) -> str:
        """Преобразование статуса микрофона"""
        mapping = {
            'on': 'Muted',
            'off': 'Unmuted'
        }
        return mapping.get(status.lower(), status)

    @staticmethod
    def _map_presentation(status: str) -> str:
        """Преобразование статуса презентации"""
        mapping = {
            'Start': 'Демонстрируется',
            'Stop': 'Не демонстрируется',
            'Started': 'Демонстрируется',
            'Stopped': 'Не демонстрируется'
        }
        return mapping.get(status, status)
    
    @staticmethod
    def _map_camera_status(status: str) -> str:
        """Преобразование статуса камеры"""
        mapping = {
            'on': 'Выключена (Mute)',
            'off': 'Включена'
        }
        return mapping.get(status.lower(), status)
    
    @staticmethod
    def _map_selfview(status: str) -> str:
        """Преобразование статуса Selfview"""
        mapping = {
            'on': 'Включено',
            'off': 'Выключено',
            'auto': 'Авто'
        }
        return mapping.get(status.lower(), status)
    
    @staticmethod
    def _map_auto_answer(status: str) -> str:
        """Преобразование статуса автоответа"""
        mapping = {
            'yes': 'Да',
            'no': 'Нет',
            'donotdisturb': 'Не беспокоить'
        }
        return mapping.get(status.lower(), status)
    
    @staticmethod
    def _map_lan_settings(settings: str) -> str:
        """Преобразование настроек LAN"""
        mapping = {
            'auto': 'Авто',
            '10hdx': '10 Мбит/с, Half Duplex',
            '10fdx': '10 Мбит/с, Full Duplex',
            '100hdx': '100 Мбит/с, Half Duplex',
            '100fdx': '100 Мбит/с, Full Duplex',
            '1000hdx': '1000 Мбит/с, Half Duplex',
            '1000fdx': '1000 Мбит/с, Full Duplex'
        }
        return mapping.get(settings.lower(), settings)
    
    @staticmethod
    def _map_dual_monitor(status: str) -> str:
        """Преобразование статуса двух мониторов"""
        mapping = {
            'yes': 'Да',
            'no': 'Нет'
        }
        return mapping.get(status.lower(), status)
    
    @staticmethod
    def _map_camera_tracking(tracking: str) -> str:
        """Преобразование статуса слежения камеры"""
        mapping = {
            'on': 'Включено',
            'off': 'Выключено',
            'voice': 'Голос',
            'groupframe': 'Группа',
            'framegroup': 'Группа'
        }
        return mapping.get(tracking.lower(), tracking)


class ExtronIN1804DataParser:
    """Парсер данных для Extron IN1804"""
    
    @staticmethod
    def parse(data):
        """Преобразование сырых данных в формат для GUI"""
        if not data:
            return {}
        
        parsed = {}
        
        # Основная информация
        device_info = data.get('device_info', {})
        parsed['model'] = device_info.get('model', 'Unknown')
        parsed['temperature'] = device_info.get('temperature', 0)
        
        # Параметры матрицы
        parsed['inputs_num'] = data.get('inputs_num', 8)
        parsed['outputs_num'] = data.get('outputs_num', 1)
        parsed['input_names'] = data.get('input_names', [])
        parsed['output_names'] = data.get('output_names', [])
        parsed['connection_protocol'] = data.get('connection_protocol', 'Unknown')
        
        # Статусы сигналов
        signal_status = data.get('signal_status', [])
        parsed['signal_status'] = {}
        for status in signal_status:
            input_num = status.get('input')
            parsed['signal_status'][input_num] = {
                'has_signal': status.get('has_signal', False),
                'status_text': status.get('status', 'Unknown')
            }
        
        # HDCP информация
        parsed['input_hdcp_auth'] = data.get('input_hdcp_auth', [])
        parsed['input_hdcp_status'] = data.get('input_hdcp_status', [])
        parsed['output_hdcp'] = data.get('output_hdcp', '')
        
        # Коммутации
        connections = data.get('connections', [])
        parsed['current_connection'] = connections[0] if connections else 1
        
        return parsed


class AtenPDUDataParser:
    """Парсер данных для PDU Aten"""
    
    @staticmethod
    def parse_device_info(raw_data: dict) -> dict:
        """Парсинг общей информации об устройстве"""
        parsed = {}
        
        # Маппинг полей для отображения
        field_mapping = {
            'model': 'Модель',
            'firmware': 'Версия прошивки',
            'serial': 'Серийный номер',
            'name': 'Имя устройства',
            'uptime': 'Время работы',
            'temperature': 'Температура'
        }
        
        for key, display_name in field_mapping.items():
            if key in raw_data:
                parsed[display_name] = str(raw_data[key])
        
        return parsed
    
    @staticmethod
    def parse_outlets_status(xml_text: str) -> list:
        """Парсинг статуса розеток из XML"""
        import xml.etree.ElementTree as ET
        
        outlets = []
        try:
            root = ET.fromstring(xml_text)
            for child in root:
                if child.tag.isdigit():
                    outlet_num = int(child.tag)
                    status = child.text.strip() if child.text else "unknown"
                    outlets.append({
                        'number': outlet_num,
                        'status': status,  # 'on' или 'off'
                        'name': f"Розетка {outlet_num}"  # Будет заменено позже
                    })
        except ET.ParseError:
            # Если не XML, пробуем другие форматы
            pass
        
        # Сортируем по номеру розетки
        outlets.sort(key=lambda x: x['number'])
        return outlets



# Фабрика парсеров для удобства
class ParserFactory:
    """Фабрика для получения парсера по типу устройства"""
    
    _parsers = {
        'huawei_te40': HuaweiTE40DataParser,
        'huawei_bar310': HuaweiBar310DataParser,
        'polycom': PolycomDataParser,
    }
    
    @classmethod
    def get_parser(cls, device_type: str):
        """Получить парсер для указанного типа устройства"""
        return cls._parsers.get(device_type)
    
    @classmethod
    def parse(cls, device_type: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Удобный метод для парсинга данных"""
        parser = cls.get_parser(device_type)
        if parser:
            return parser.parse_raw_data(raw_data)
        return raw_data
