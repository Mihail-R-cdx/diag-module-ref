"""
Фабрика для создания обработчиков протоколов.
"""

from typing import Dict, Optional, List
# Убираем импорт ProtocolHandler отсюда, он будет использоваться как строка

class ProtocolFactory:
    """Фабрика для создания обработчиков протоколов"""
    
    _handlers = {
        'huawei_te20': ('handlers.huawei.te20', 'HuaweiTE20Handler'),
        'huawei_te40': ('handlers.huawei.te40', 'HuaweiTE40Handler'),
        'huawei_box300': ('handlers.huawei.box300', 'CloudLinkBox300Handler'),
        'huawei_bar310': ('handlers.huawei.bar310', 'CloudLinkBar310Handler'), 
        'polycom_rpg310': ('handlers.polycom.rpg310', 'PolycomRPG310Handler'),
        'extron_in1804': ('handlers.extron.in1804', 'ExtronIN1804Handler'),
    }
    
    @classmethod
    def register_handler(cls, protocol_type: str, module_path: str, class_name: str):
        """Зарегистрировать новый обработчик"""
        cls._handlers[protocol_type.lower()] = (module_path, class_name)
    
    @staticmethod
    def create_handler(protocol_type: str, ip_address: str, 
                      credentials: Optional[Dict] = None, **kwargs):
        """
        Создает обработчик протокола указанного типа
        """
        handler_info = ProtocolFactory._handlers.get(protocol_type.lower())
        
        if handler_info:
            module_path, class_name = handler_info
            
            try:
                # Динамический импорт
                import importlib
                module = importlib.import_module(module_path)
                handler_class = getattr(module, class_name)
                
                if credentials is None:
                    credential_kwargs = {}
                elif hasattr(credentials, 'as_handler_kwargs'):
                    credential_kwargs = credentials.as_handler_kwargs()
                else:
                    credential_kwargs = {
                        key: value
                        for key, value in credentials.items()
                        if key in {'username', 'password'}
                    }
                
                return handler_class(
                    ip_address=ip_address,
                    **credential_kwargs,
                    **kwargs
                )
            except (ImportError, AttributeError) as e:
                print(f"Error creating handler: {e}")
                return None
        
        return None
    
    @staticmethod
    def get_supported_devices() -> List[str]:
        """Получить список поддерживаемых устройств"""
        return list(ProtocolFactory._handlers.keys())
