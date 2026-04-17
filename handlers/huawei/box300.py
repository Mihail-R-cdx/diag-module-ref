from core.base_handler import BaseHuaweiCodecHandler
from typing import Dict, Any, Optional

class CloudLinkBox300Handler(BaseHuaweiCodecHandler):
    """Обработчик для Huawei CloudLink Box 300"""
    
    def __init__(self, ip_address: str, port: int = 443,
                 username: str = 'admin', password: str = '',
                 use_ssl: bool = True, verify_ssl: bool = False):
        super().__init__(ip_address, port, username, password, use_ssl, verify_ssl)
        self.device_model = 'Huawei CloudLink Box 300'
        self._setup_session()
    
    def connect(self) -> bool:
        """Установка соединения с CloudLink Box 300"""
        try:
            self.base_url = f"{'https' if self.use_ssl else 'http'}://{self.ip_address}:{self.port}"
            response = self._make_request('GET', '/rest/v1/system/device-info')
            if response:
                self._connected = True
                self._connection_time = datetime.datetime.now()
                return True
        except Exception as e:
            self._last_error = str(e)
        return False
    
    def disconnect(self) -> None:
        """Разорвать соединение"""
        if self.session:
            self.session.close()
        self._connected = False
        self._connection_time = None
    
    def send_command(self, command: str, data: Optional[Dict] = None) -> Dict:
        """Отправить команду устройству"""
        if not self.is_connected():
            return {'error': 'Not connected'}
        
        command_map = {
            'dial': '/rest/v1/call/dial',
            'hangup': '/rest/v1/call/hangup',
            'mute': '/rest/v1/audio/mute',
            'volume': '/rest/v1/audio/volume',
            'camera_move': '/rest/v1/camera/move',
            'presentation_start': '/rest/v1/presentation/start',
            'presentation_stop': '/rest/v1/presentation/stop'
        }
        
        endpoint = command_map.get(command, f'/rest/v1/{command}')
        return self._make_request('POST', endpoint, data) or {}
    
    def get_status(self) -> Dict[str, Any]:
        """Получение полного статуса устройства"""
        if not self.is_connected():
            return {'error': 'Not connected'}
        
        status = {
            'device_info': self.get_device_info(),
            'system': self.get_system_info(),
            'call': self.get_call_status(),
            'audio': self.get_audio_status(),
            'video': self.get_video_status(),
            'network': self.get_network_status(),
            'timestamp': datetime.datetime.now().isoformat()
        }
        return status
    
    def get_device_info(self) -> Dict[str, str]:
        """Получить информацию об устройстве"""
        response = self._make_request('GET', '/rest/v1/system/device-info')
        if response:
            return {
                'model': 'Huawei CloudLink Box 300',
                'serial': response.get('serialNumber', 'N/A'),
                'version': response.get('softwareVersion', 'N/A'),
                'mac': response.get('macAddress', 'N/A'),
                'ip': self.ip_address,
                'uptime': response.get('uptime', 'N/A')
            }
        return {'model': 'Huawei CloudLink Box 300', 'error': 'Unable to get device info'}
    
    def get_system_info(self) -> Dict[str, Any]:
        """Получить системную информацию"""
        response = self._make_request('GET', '/rest/v1/system/status')
        return response or {}
    
    def get_call_status(self) -> Dict[str, Any]:
        """Получить статус вызова"""
        response = self._make_request('GET', '/rest/v1/call/status')
        if response:
            return {
                'active_calls': response.get('activeCalls', 0),
                'call_type': response.get('callType', 'idle'),
                'remote_number': response.get('remoteNumber', ''),
                'remote_name': response.get('remoteName', ''),
                'duration': response.get('duration', 0),
                'protocol': response.get('protocol', ''),
                'bandwidth': response.get('bandwidth', 0),
                'packet_loss': response.get('packetLoss', 0),
                'jitter': response.get('jitter', 0),
                'latency': response.get('latency', 0)
            }
        return {}
    
    def get_audio_status(self) -> Dict[str, Any]:
        """Получить статус аудио"""
        response = self._make_request('GET', '/rest/v1/audio/status')
        return response or {}
    
    def get_video_status(self) -> Dict[str, Any]:
        """Получить статус видео"""
        response = self._make_request('GET', '/rest/v1/video/status')
        return response or {}
    
    def get_network_status(self) -> Dict[str, Any]:
        """Получить статус сети"""
        response = self._make_request('GET', '/rest/v1/network/status')
        return response or {}
    
    def _make_request(self, method: str, endpoint: str, 
                      data: Optional[Dict] = None, retries: int = 2) -> Optional[Dict]:
        """Вспомогательный метод для HTTP запросов"""
        if not self.session:
            return None
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retries):
            try:
                auth = (self.credentials.get('username', 'admin'), 
                       self.credentials.get('password', ''))
                
                if method.upper() == 'GET':
                    response = self.session.get(url, auth=auth, timeout=10)
                else:
                    response = self.session.post(url, json=data, auth=auth, timeout=10)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    self._last_error = 'Authentication failed'
                    
            except Exception as e:
                self._last_error = str(e)
                if attempt == retries - 1:
                    return None
                continue
        
        return None

