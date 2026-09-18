import re
import datetime
from collections.abc import Mapping, Sequence
from typing import Dict, Any
from core.exceptions import ParseError
from core.call_activity import (
    CallActivity,
    call_activity_from_model_evidence,
    publish_call_activity_evidence,
)
from utils.te20_audio import format_te20_monitor_audio_level


def _publish_huawei_codec_evidence(
    parsed: Dict[str, Any], raw_data: Mapping[str, Any], *,
    call_binding: str = "huawei_call_activity",
) -> None:
    """Publish only documented Huawei-family protocol values as room authority.

    This is deliberately an exact parser boundary.  It may understand the
    protocol tokens below, whereas the shared room projection must never infer
    meaning from these (or translated display) strings.
    """
    if "call_status" in raw_data:
        activity = call_activity_from_model_evidence(call_binding, raw_data.get("call_status"))
        if activity is CallActivity.ACTIVE:
            parsed["_room_codec_call_active"] = True
        elif activity is CallActivity.INACTIVE:
            parsed["_room_codec_call_active"] = False
        publish_call_activity_evidence(
            parsed, binding_key=call_binding, evidence=raw_data.get("call_status")
        )
    presentation = raw_data.get("presentation_local", raw_data.get("presentation"))
    if presentation in {"Start", "auxOpen"}:
        parsed["_room_codec_presentation_active"] = True
    elif presentation in {"Stop", "auxClose"}:
        parsed["_room_codec_presentation_active"] = False
    registration = raw_data.get("sip_status")
    if registration in {"On", "SIP_STATE_OK"}:
        parsed["_room_codec_registration_active"] = True
    elif registration in {"Off", "EMPTY"}:
        parsed["_room_codec_registration_active"] = False
    microphone = raw_data.get("mic_mute")
    if microphone in {"On", "Muted"}:
        parsed["microphone_muted"] = True
    elif microphone in {"Off", "Unmuted"}:
        parsed["microphone_muted"] = False
    speaker = raw_data.get("speaker_mute")
    if speaker in {"On", "Muted"}:
        parsed["speaker_muted"] = True
    elif speaker in {"Off", "Unmuted"}:
        parsed["speaker_muted"] = False
    speaker_volume = raw_data.get("speaker_volume")
    if isinstance(speaker_volume, (int, float)) and not isinstance(speaker_volume, bool):
        parsed["speaker_volume"] = speaker_volume
        if speaker not in {"On", "Muted", "Off", "Unmuted"}:
            parsed["speaker_muted"] = speaker_volume == 0


def _publish_polycom_codec_evidence(parsed: Dict[str, Any], raw_data: Mapping[str, Any]) -> None:
    """Publish only documented Polycom protocol values as room authority."""
    activity = call_activity_from_model_evidence("polycom_call_activity", raw_data.get("call_status"))
    if activity is CallActivity.ACTIVE:
        parsed["_room_codec_call_active"] = True
    elif activity is CallActivity.INACTIVE:
        parsed["_room_codec_call_active"] = False
    publish_call_activity_evidence(
        parsed, binding_key="polycom_call_activity", evidence=raw_data.get("call_status")
    )
    presentation = raw_data.get("presentation")
    if presentation in {"Start", "Started"}:
        parsed["_room_codec_presentation_active"] = True
    elif presentation in {"Stop", "Stopped"}:
        parsed["_room_codec_presentation_active"] = False
    registration = raw_data.get("sip_status")
    if registration == "online":
        parsed["_room_codec_registration_active"] = True
    elif registration == "offline":
        parsed["_room_codec_registration_active"] = False
    microphone = raw_data.get("mic_mute")
    if microphone in {"on", "Muted"}:
        parsed["microphone_muted"] = True
    elif microphone in {"off", "Unmuted"}:
        parsed["microphone_muted"] = False
    speaker_volume = raw_data.get("speaker_volume")
    if isinstance(speaker_volume, (int, float)) and not isinstance(speaker_volume, bool):
        parsed["speaker_volume"] = speaker_volume
        parsed["speaker_muted"] = speaker_volume == 0


class BiampTesiraForteCIDataParser:
    """Parser for Biamp Tesira Forte CI read-only audio-DSP status."""

    model = "Biamp Tesira Forte CI"
    manufacturer = "Biamp"

    @staticmethod
    def parse_raw_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(raw_data, Mapping):
            raise ValueError("Biamp payload must be a mapping")

        raw_sources = raw_data.get("signal_sources")
        if not isinstance(raw_sources, Sequence) or isinstance(raw_sources, (str, bytes, bytearray)):
            raise ValueError("signal_sources must be a sequence")

        device_info = raw_data.get("device_info") if isinstance(raw_data.get("device_info"), Mapping) else {}
        ip_address = (
            device_info.get("ip_address")
            or raw_data.get("ip_address")
            or raw_data.get("IPAddress")
        )
        signal_sources = []

        for source_index, raw_source in enumerate(raw_sources, start=1):
            if not isinstance(raw_source, Mapping):
                continue
            alias = raw_source.get("alias")
            attribute = raw_source.get("subscription_attribute")
            rows = raw_source.get("rows")
            if not alias or attribute not in {"peaks", "levels"}:
                continue
            if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
                continue

            normalized_rows = []
            for row_index, raw_row in enumerate(rows, start=1):
                if isinstance(raw_row, Mapping):
                    value = raw_row.get("value")
                    state = raw_row.get("state")
                    channel_number = raw_row.get("channel_number", row_index)
                else:
                    value = raw_row
                    state = None
                    channel_number = row_index
                normalized_rows.append(
                    {
                        "channel_number": channel_number,
                        "value": value,
                        "state": BiampTesiraForteCIDataParser._state_for_value(value, state),
                    }
                )

            if normalized_rows:
                signal_sources.append(
                    {
                        "alias": str(alias),
                        "subscription_attribute": str(attribute),
                        "update_interval_ms": int(raw_source.get("update_interval_ms") or 500),
                        "rows": normalized_rows,
                    }
                )

        if not signal_sources:
            raise ValueError("Biamp payload did not contain useful signal source values")

        parsed = {
            "device_info": {
                "model": BiampTesiraForteCIDataParser.model,
                "manufacturer": BiampTesiraForteCIDataParser.manufacturer,
                "ip_address": ip_address,
            },
            "signal_sources": signal_sources,
            "ip_address": ip_address,
            "model": BiampTesiraForteCIDataParser.model,
            "manufacturer": BiampTesiraForteCIDataParser.manufacturer,
            "type": "audio_dsp",
        }
        connection_profile = raw_data.get("connection_profile")
        if isinstance(connection_profile, Mapping):
            parsed["connection_profile"] = dict(connection_profile)
        return parsed

    @staticmethod
    def _state_for_value(value, existing_state):
        if existing_state in {"present", "absent", "unknown"}:
            return existing_state
        if isinstance(value, bool):
            return "present" if value else "absent"
        if value is None:
            return "unknown"
        return None


class HuaweiTE40DataParser:
    """Парсер данных для Huawei TE40"""
    
    @staticmethod
    def parse_raw_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг сырых данных от Huawei кодеков"""
        parsed = {}
        
        if not raw_data:
            return parsed
        
        # Модель и версия
        parsed['Модель'] = raw_data.get('model', 'Huawei TE40')
        parsed['Версия ПО'] = HuaweiTE40DataParser._clean_version(raw_data.get('version', ''))
        parsed['Серийный номер'] = raw_data.get('serial_number', 'N/A')
        parsed['MAC адрес'] = raw_data.get('mac_address', 'N/A')
        
        # Статусы SIP
        sip_status = HuaweiTE40DataParser._map_sip_status(raw_data.get('sip_status', 'Off'))
        parsed['SIP регистрация'] = sip_status
        HuaweiTE40DataParser._publish_room_codec_evidence(parsed, raw_data)
        parsed['SIP адрес'] = raw_data.get('sip_server', 'N/A')
        parsed['SIP номер'] = raw_data.get('sip_number', 'N/A')
        
        # Время работы
        parsed['Время работы'] = raw_data.get('uptime', 'N/A')
        if raw_data.get('uptime') not in (None, '', 'N/A'):
            parsed['uptime'] = raw_data.get('uptime')
        
        # Статус звонка
        parsed['Статус звонка'] = HuaweiTE40DataParser._map_call_status(
            raw_data.get('call_status', 'No Call')
        )
        publish_call_activity_evidence(
            parsed, binding_key="huawei_call_activity", evidence=raw_data.get('call_status')
        )
        
        # Презентация
        parsed['Режим презентации'] = HuaweiTE40DataParser._map_presentation(
            raw_data.get('presentation', 'Stop')
        )
        
        # Аудио статусы
        microphone_status = raw_data.get('mic_connection_status') or HuaweiTE40DataParser._map_mic_status(
            raw_data.get('mic_mute', 'Off')
        )
        parsed['Статус микрофона'] = microphone_status
        parsed['microphone_status'] = microphone_status
        parsed['Статус динамика'] = HuaweiTE40DataParser._map_speaker_status(
            raw_data.get('speaker_mute', 'Off')
        )
        if 'speaker_volume' in raw_data and raw_data.get('speaker_volume') is not None:
            parsed['Громкость динамиков'] = str(raw_data.get('speaker_volume'))
            parsed['speaker_volume'] = raw_data.get('speaker_volume')
        # TE40's configured primary microphone gain is a numeric wire value.
        # It is deliberately independent from MicSwitch/mute evidence.
        microphone_volume = raw_data.get('mic_volume')
        if isinstance(microphone_volume, (int, float)) and not isinstance(microphone_volume, bool):
            if 0 <= microphone_volume <= 24:
                parsed['microphone_volume'] = microphone_volume
                parsed['Громкость микрофона'] = str(microphone_volume - 12)
        if (
            'monitor_mic_value' in raw_data
            and raw_data.get('monitor_mic_value') is not None
        ):
            parsed['Звук в помещении (микрофон)'] = (
                format_te20_monitor_audio_level(
                    raw_data.get('monitor_mic_value')
                )
            )
            parsed['monitor_mic_value'] = raw_data.get(
                'monitor_mic_value'
            )
        if (
            'monitor_speaker_value' in raw_data
            and raw_data.get('monitor_speaker_value') is not None
        ):
            parsed['Звук из динамиков (выход кодека)'] = (
                format_te20_monitor_audio_level(
                    raw_data.get('monitor_speaker_value')
                )
            )
            parsed['monitor_speaker_value'] = raw_data.get(
                'monitor_speaker_value'
            )
        if raw_data.get('mic_connection_status') == 'Микрофон не подключён':
            parsed['Mute микрофона'] = 'Микрофон не подключён'
        elif 'mic_mute' in raw_data:
            parsed['mic_mute'] = raw_data.get('mic_mute')
            parsed['Mute микрофона'] = HuaweiTE40DataParser._map_microphone_mute_status(
                raw_data.get('mic_mute')
            )
        # Камера
        camera_status = raw_data.get('camera_connection_status') or HuaweiTE40DataParser._map_camera_status(
            raw_data.get('camera_status', 'OffOff')
        )
        parsed['Статус камеры'] = camera_status
        parsed['camera_status'] = camera_status
        
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

    @staticmethod
    def _publish_room_codec_evidence(parsed: Dict[str, Any], raw_data: Mapping[str, Any]) -> None:
        _publish_huawei_codec_evidence(parsed, raw_data)


class HuaweiTE20DataParser:
    """Парсер данных для Huawei TE20"""
    
    @staticmethod
    def parse_raw_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг сырых данных от Huawei TE20 в формат, ожидаемый маппингом"""
        parsed = {}
        
        if not raw_data:
            return parsed
        
        print("=" * 50)
        print("Парсер TE-20 получил данные:", raw_data)
        print("=" * 50)
        
        # 1. Основные поля, которые ожидает маппинг
        mapping_fields = {
            'Модель': raw_data.get('model', 'Huawei TE20'),
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
        HuaweiTE20DataParser._publish_room_codec_evidence(parsed, raw_data)
        
        # 2. Специальные поля для маппинга
        
        # Статус звонка
        if 'call_status' in raw_data:
            parsed['call_status'] = raw_data['call_status']
            # Также добавляем в Статус звонка для прямого маппинга
            parsed['Статус звонка'] = raw_data['call_status']
            publish_call_activity_evidence(
                parsed, binding_key="huawei_call_activity", evidence=raw_data['call_status']
            )
        
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
            parsed['Звук в помещении (микрофон)'] = (
                format_te20_monitor_audio_level(
                    raw_data['monitor_mic_value']
                )
            )
            parsed['monitor_mic_value'] = raw_data['monitor_mic_value']

        if 'monitor_speaker_value' in raw_data and raw_data['monitor_speaker_value'] is not None:
            parsed['Звук из динамиков (выход кодека)'] = (
                format_te20_monitor_audio_level(
                    raw_data['monitor_speaker_value']
                )
            )
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

    @staticmethod
    def _publish_room_codec_evidence(parsed: Dict[str, Any], raw_data: Mapping[str, Any]) -> None:
        _publish_huawei_codec_evidence(parsed, raw_data)
        
        

class HuaweiBar310DataParser:
    """Парсер данных для Huawei CloudLink Bar 310"""
    
    @staticmethod
    def parse_raw_data(
        raw_data: Dict[str, Any], expected_identity: str = "Huawei CloudLink Bar 310"
    ) -> Dict[str, Any]:
        """Convert only validated canonical Bar 310 observations for display."""
        if not isinstance(raw_data, Mapping):
            raise ParseError("Bar 310 payload is not an object")
        if raw_data.get("model") != expected_identity:
            raise ParseError("Bar 310 model evidence is missing or invalid")
        version = raw_data.get("version")
        if not isinstance(version, str) or not version.strip() or version.casefold() == "unknown":
            raise ParseError("Bar 310 version evidence is missing or invalid")
        cleaned_version = HuaweiBar310DataParser._clean_version(version)
        if not cleaned_version or cleaned_version.casefold() == "unknown":
            raise ParseError("Bar 310 display version is unusable")

        parsed = {
            "Модель": expected_identity,
            "Версия ПО": cleaned_version,
        }
        direct_fields = {
            "serial_number": "Серийный номер",
            "camera_version": "Версия камеры",
            "mic_version": "Версия микрофона",
            "mac_address": "MAC адрес",
            "sip_server": "SIP адрес",
            "sip_number": "SIP номер",
            "uptime": "Время работы",
        }
        for source, target in direct_fields.items():
            if source in raw_data and raw_data[source] is not None:
                parsed[target] = raw_data[source]
        _publish_huawei_codec_evidence(parsed, raw_data, call_binding="cloudlink_call_activity")

        if "sip_status" in raw_data and raw_data["sip_status"] is not None:
            parsed["SIP регистрация"] = HuaweiBar310DataParser._map_sip_status(
                raw_data["sip_status"]
            )
        if "call_status" in raw_data and raw_data["call_status"] is not None:
            parsed["Статус звонка"] = HuaweiBar310DataParser._map_call_status(
                raw_data["call_status"]
            )
            publish_call_activity_evidence(
                parsed, binding_key="cloudlink_call_activity", evidence=raw_data["call_status"]
            )
        if "presentation" in raw_data and raw_data["presentation"] is not None:
            parsed["Режим презентации"] = HuaweiBar310DataParser._map_presentation(
                raw_data["presentation"]
            )
        if "sleep_mode" in raw_data and raw_data["sleep_mode"] is not None:
            parsed["Режим сна"] = HuaweiBar310DataParser._map_sleep_mode(
                raw_data["sleep_mode"]
            )
        if "mic_connection_status" in raw_data and raw_data["mic_connection_status"] is not None:
            parsed["Статус микрофона"] = raw_data["mic_connection_status"]
        if "mic_volume" in raw_data and raw_data["mic_volume"] is not None:
            parsed["Громкость микрофона"] = str(raw_data["mic_volume"])
            parsed["microphone_volume"] = raw_data["mic_volume"]
        if "speaker_mute" in raw_data and raw_data["speaker_mute"] is not None:
            parsed["Статус динамика"] = HuaweiBar310DataParser._map_speaker_status(
                raw_data["speaker_mute"]
            )
        if "speaker_volume" in raw_data and raw_data["speaker_volume"] is not None:
            parsed["Громкость динамиков"] = str(raw_data["speaker_volume"])
            parsed["speaker_volume"] = raw_data["speaker_volume"]
        if "camera_status" in raw_data and raw_data["camera_status"] is not None:
            camera_states = {"On": "Подключена", "Off": "Не подключена"}
            parsed["Статус камеры"] = camera_states.get(
                raw_data["camera_status"], raw_data["camera_status"]
            )
        return parsed
    
    @staticmethod
    def _clean_version(version: str) -> str:
        """Очистка версии ПО"""
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
        
        print(
            "PolycomDataParser получил поля:",
            sorted(str(key) for key in raw_data),
        )
        
        # Основные поля
        parsed['Модель'] = raw_data.get('model', 'Polycom RealPresence Group 310')
        parsed['Версия ПО'] = raw_data.get('version', 'N/A')
        parsed['IP адрес'] = raw_data.get('ip_address', 'N/A')
        if raw_data.get('mac_address'):
            parsed['MAC адрес'] = raw_data.get('mac_address')
        
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
        _publish_polycom_codec_evidence(parsed, raw_data)
        sip_address = raw_data.get('sip_address')
        if sip_address:
            parsed['SIP адрес'] = sip_address
        
        # Статус звонка
        call_status = raw_data.get('call_status', 'No Call')
        parsed['Статус звонка'] = PolycomDataParser._map_call_status(call_status)
        publish_call_activity_evidence(
            parsed, binding_key="polycom_call_activity", evidence=raw_data.get('call_status')
        )
        
        # Громкость
        volume = raw_data.get('speaker_volume')
        if volume is not None:
            parsed['Громкость динамиков'] = f"{volume}%"
            parsed['speaker_volume'] = volume
        
        # Статус микрофона
        mic_mute = raw_data.get('mic_mute')
        if mic_mute:
            parsed['mic_mute'] = mic_mute
            parsed['Статус микрофона'] = 'Не определено'
            parsed['Mute микрофона'] = PolycomDataParser._map_mic_status(mic_mute)
        else:
            parsed['Статус микрофона'] = 'Не доступно'
            parsed['Mute микрофона'] = 'Не доступно'

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
        
        print(
            "PolycomDataParser подготовил поля:",
            sorted(str(key) for key in parsed),
        )
        
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

    _MODEL_INPUT_COUNTS = {
        "1804": 4,
        "1806": 6,
        "1808": 8,
        "1608": 8,
    }
    
    @staticmethod
    def parse(data):
        """Преобразование сырых данных в формат для GUI"""
        if not data:
            return {}
        if isinstance(data, Mapping) and data.get("capabilities") is not None:
            return ExtronMatrixDataParser.parse(data)
        
        parsed = {}
        
        # Основная информация
        device_info = data.get('device_info', {})
        model = device_info.get('model') if isinstance(device_info, Mapping) else None
        parsed['model'] = model if isinstance(model, str) and model.strip() and model.casefold() != 'unknown' else None
        temperature = device_info.get('temperature') if isinstance(device_info, Mapping) else None
        parsed['temperature'] = temperature if isinstance(temperature, (int, float)) and not isinstance(temperature, bool) else None
        
        # Параметры матрицы
        inputs_num = data.get('inputs_num')
        expected_inputs = ExtronIN1804DataParser._recognized_input_count(parsed['model'])
        parsed['inputs_num'] = (
            inputs_num
            if isinstance(inputs_num, int) and inputs_num > 0 and inputs_num == expected_inputs
            else None
        )
        parsed['outputs_num'] = data.get('outputs_num', 1)
        parsed['input_names'] = data.get('input_names', [])
        parsed['output_names'] = data.get('output_names', [])
        parsed['connection_protocol'] = data.get('connection_protocol', 'Unknown')
        
        # Статусы сигналов
        signal_status = data.get('signal_status', [])
        parsed['signal_status'] = {}
        for status in signal_status:
            input_num = status.get('input')
            if isinstance(input_num, int) and parsed['inputs_num'] is not None and 1 <= input_num <= parsed['inputs_num']:
                present = status.get('has_signal')
                parsed['signal_status'][input_num] = {
                    'has_signal': present if isinstance(present, bool) else None,
                    'status_text': status.get('status')
                }
        
        # HDCP информация
        parsed['input_hdcp_auth'] = data.get('input_hdcp_auth', [])
        parsed['input_hdcp_status'] = data.get('input_hdcp_status', [])
        parsed['hdcp_present'] = [
            ExtronIN1804DataParser._normalize_hdcp(value)
            for value in (parsed['input_hdcp_status'] if isinstance(parsed['input_hdcp_status'], (list, tuple)) else ())
        ]
        parsed['output_hdcp'] = data.get('output_hdcp', '')
        
        # Коммутации
        connections = data.get('connections', [])
        connection = connections[0] if isinstance(connections, (list, tuple)) and len(connections) == 1 else None
        parsed['current_connection'] = (
            connection
            if isinstance(connection, int) and parsed['inputs_num'] is not None and 1 <= connection <= parsed['inputs_num']
            else None
        )
        
        return parsed

    @staticmethod
    def _normalize_hdcp(raw):
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            return None
        return True if value == 2 else False if value in {0, 1} else None

    @classmethod
    def _recognized_input_count(cls, model):
        if not isinstance(model, str):
            return None
        normalized = model.casefold()
        for token, count in cls._MODEL_INPUT_COUNTS.items():
            if token in normalized:
                return count
        return None


class ExtronMatrixDataParser:
    """Normalize exact-profile Matrix evidence for single and multi-output UI.

    The handler has already selected the profile.  This parser accepts no
    arbitrary digits as route authority and only exposes compatibility fields
    when a single logical output has proven route evidence.
    """

    @staticmethod
    def _legacy_hdcp_state(value, profile):
        if value in {"ABSENT", "PRESENT_HDCP", "PRESENT_NO_HDCP", "UNKNOWN"}:
            return value
        try:
            value = int(str(value).strip())
        except (TypeError, ValueError):
            return "UNKNOWN"
        if value == 0:
            return "ABSENT"
        return ({1: "PRESENT_NO_HDCP", 2: "PRESENT_HDCP"} if profile == "legacy" else {1: "PRESENT_HDCP", 2: "PRESENT_NO_HDCP"}).get(value, "UNKNOWN")

    @staticmethod
    def parse(data):
        if not isinstance(data, Mapping):
            return {}
        caps = data.get("capabilities")
        if caps is None:
            return ExtronIN1804DataParser.parse(data)
        inputs = tuple(getattr(caps, "available_input_ids", ()) or ())
        outputs = tuple(getattr(caps, "available_output_ids", ()) or ())
        routes_raw = data.get("routes") if isinstance(data.get("routes"), Mapping) else {}
        routes = {
            output_id: routes_raw.get(output_id)
            if routes_raw.get(output_id) in inputs else None
            for output_id in outputs
        }
        signal_raw = data.get("signal_status") if isinstance(data.get("signal_status"), Mapping) else {}
        signal = {item: signal_raw.get(item) if isinstance(signal_raw.get(item), bool) else None for item in inputs}
        input_hdcp_raw = data.get("input_hdcp_status")
        input_hdcp = input_hdcp_raw if isinstance(input_hdcp_raw, Mapping) else {
            item: input_hdcp_raw[index]
            for index, item in enumerate(inputs)
            if isinstance(input_hdcp_raw, (list, tuple)) and index < len(input_hdcp_raw)
        }
        output_hdcp_raw = data.get("output_hdcp")
        output_hdcp = output_hdcp_raw if isinstance(output_hdcp_raw, Mapping) else ({1: output_hdcp_raw} if outputs == (1,) else {})
        auth_raw = data.get("input_hdcp_auth")
        input_hdcp_auth = auth_raw if isinstance(auth_raw, Mapping) else {
            item: auth_raw[index]
            for index, item in enumerate(inputs)
            if isinstance(auth_raw, (list, tuple)) and index < len(auth_raw)
        }
        input_names = data.get("input_names") if isinstance(data.get("input_names"), Mapping) else {}
        output_names = data.get("output_names") if isinstance(data.get("output_names"), Mapping) else {}
        info = data.get("device_info") if isinstance(data.get("device_info"), Mapping) else {}
        parsed = {
            "model": info.get("model"), "temperature": info.get("temperature"),
            "logical_input_ids": list(getattr(caps, "logical_input_ids", ())),
            "logical_output_ids": list(getattr(caps, "logical_output_ids", ())),
            "available_input_ids": list(inputs), "available_output_ids": list(outputs),
            "input_names": {item: input_names.get(item) for item in inputs},
            "output_names": {item: output_names.get(item) for item in outputs},
            "signal_presence": signal, "signal_status": {item: {"has_signal": value} for item, value in signal.items()},
            "input_hdcp": {item: ExtronMatrixDataParser._legacy_hdcp_state(input_hdcp.get(item), getattr(caps, "input_hdcp_profile", "modern")) for item in inputs},
            "output_hdcp": {item: output_hdcp.get(item) for item in outputs},
            "input_hdcp_auth": {item: input_hdcp_auth.get(item) for item in inputs}, "routes": routes,
            "inputs_num": len(inputs), "outputs_num": len(outputs),
            "connection_protocol": data.get("connection_protocol", "Unknown"),
        }
        if outputs == (1,):
            parsed["current_connection"] = routes[1]
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
        'biamp_tesira_forte_ci': BiampTesiraForteCIDataParser,
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
