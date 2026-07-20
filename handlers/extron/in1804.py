"""Обработчик для видеоматрицы Extron IN1804"""

import re
import time
from core.base_handler import BaseExtronMatrixHandler
from core.exceptions import (
    AuthenticationError,
    CommandOutcomeUnknownError,
    ConnectionError,
    ProtocolError,
)


class ExtronIN1804Handler(BaseExtronMatrixHandler):
    """Обработчик для матрицы Extron IN1804"""
    
    MODEL_PATTERNS = {
        '1804': {'inputs': 4, 'outputs': 1},
        '1806': {'inputs': 6, 'outputs': 1},
        '1808': {'inputs': 8, 'outputs': 1},
        '1608': {'inputs': 8, 'outputs': 1},
    }
    
    def __init__(self, ip_address: str, port: int = 22023, username: str = None, password: str = None):
        super().__init__(ip_address, port, username, password)
        self.model = 'Unknown'
        self.inputs_num = 8
        self.outputs_num = 1
        self.strict_session_failures = True

    @staticmethod
    def _raise_if_fatal_failure(error):
        if isinstance(
            error,
            (
                AuthenticationError,
                CommandOutcomeUnknownError,
                ConnectionError,
                ProtocolError,
            ),
        ):
            raise error
    
    def get_status(self) -> dict:
        """Получить полный статус устройства"""
        return self.get_full_status()
    
    def get_device_info(self) -> dict:
        """Получить базовую информацию об устройстве"""
        info = {'model': 'Unknown', 'temperature': 0}
        try:
            # Получаем модель
            result = self.send_command('1I')
            if result and result.get('success') and result.get('response'):
                model_str = result['response'].strip()
                info['model'] = model_str
                self.model = model_str
                print(f"Model received: {model_str}")  # Для отладки
                
                # Определяем количество входов по модели
                for pattern, config in self.MODEL_PATTERNS.items():
                    if pattern in model_str:
                        self.inputs_num = config['inputs']
                        break
            
            # Получаем температуру
            try:
                result = self.send_command('w20STAT')
                if result and result.get('success') and result.get('response'):
                    temp_str = result['response'].strip()
                    if temp_str and temp_str.isdigit():
                        info['temperature'] = int(temp_str)
                        print(f"Temperature received: {temp_str}")  # Для отладки
            except Exception as e:
                self._raise_if_fatal_failure(e)
                print(f"Temperature command failed: {e}")
                info['temperature'] = 0
                
        except Exception as e:
            self._raise_if_fatal_failure(e)
            print(f"Error in get_device_info: {e}")
        
        return info
    
    def get_input_names(self):
        """Получение названий входов"""
        names = []
        for i in range(self.inputs_num):
            try:
                command = f'wI{i+1}VNAM'
                result = self.send_command(command)
                if result and result.get('success') and result.get('response'):
                    name = result['response']
                    names.append(name if name else f"Input {i+1}")
                else:
                    names.append(f"Input {i+1}")
                time.sleep(0.2)
            except Exception as e:
                self._raise_if_fatal_failure(e)
                print(f"Error getting input name for {i+1}: {e}")
                names.append(f"Input {i+1}")
        return names
    
    def get_output_names(self):
        """Получение названий выходов"""
        names = []
        try:
            result = self.send_command('wO1VNAM')
            if result and result.get('success') and result.get('response'):
                name = result['response']
                names.append(name if name else "Main Output")
            else:
                names.append("Main Output")
        except Exception as e:
            self._raise_if_fatal_failure(e)
            print(f"Error getting output name: {e}")
            names.append("Main Output")
        return names
    
    def get_signal_status(self):
        """Получение статуса сигналов на входах"""
        statuses = []
        
        try:
            result = self.send_command('w0LS')
            if result and result.get('success') and result.get('response'):
                signal_response = result['response']
                print(f"Signal status response: {signal_response}")
                
                # Парсим статусы сигналов
                # Обычно ответ выглядит как "In00 0*1*0*1*0*0*1*0"
                match = re.search(r'In00\s+([0\*1]+)', signal_response)
                if match:
                    status_str = match.group(1)
                    status_parts = status_str.split('*')
                    for i, status in enumerate(status_parts):
                        if i < self.inputs_num:
                            statuses.append({
                                'input': i + 1,
                                'has_signal': status == '1',
                                'status': 'Active' if status == '1' else 'No Signal'
                            })
                else:
                    # Альтернативный парсинг - просто строка с разделителями
                    if '*' in signal_response:
                        status_parts = signal_response.split('*')
                        for i, status in enumerate(status_parts):
                            status = status.strip()
                            if i < self.inputs_num:
                                statuses.append({
                                    'input': i + 1,
                                    'has_signal': status == '1',
                                    'status': 'Active' if status == '1' else 'No Signal'
                                })
                    else:
                        # Если не удалось распарсить, создаем заглушки
                        for i in range(self.inputs_num):
                            statuses.append({
                                'input': i + 1,
                                'has_signal': False,
                                'status': 'Unknown'
                            })
            else:
                # Если команда не удалась, создаем заглушки
                for i in range(self.inputs_num):
                    statuses.append({
                        'input': i + 1,
                        'has_signal': False,
                        'status': 'Unknown'
                    })
                    
        except Exception as e:
            self._raise_if_fatal_failure(e)
            print(f"Error in get_signal_status: {e}")
            for i in range(self.inputs_num):
                statuses.append({
                    'input': i + 1,
                    'has_signal': False,
                    'status': 'Unknown'
                })
        
        return statuses
    
    def get_hdcp_info(self):
        """Получение HDCP информации для входов"""
        input_hdcp_auth = []
        input_hdcp_status = []
        
        for i in range(self.inputs_num):
            try:
                # HDCP авторизация
                result = self.send_command(f'wE{i+1}HDCP')
                if result and result.get('success') and result.get('response'):
                    hdcp_auth = result['response']
                    try:
                        input_hdcp_auth.append(int(hdcp_auth) if hdcp_auth else 0)
                    except:
                        input_hdcp_auth.append(0)
                else:
                    input_hdcp_auth.append(0)
                
                time.sleep(0.2)
                
                # HDCP статус
                result = self.send_command(f'wI{i+1}HDCP')
                if result and result.get('success') and result.get('response'):
                    hdcp_status = result['response']
                    input_hdcp_status.append(hdcp_status)
                else:
                    input_hdcp_status.append('0')
                
                time.sleep(0.2)
                
            except Exception as e:
                self._raise_if_fatal_failure(e)
                print(f"Error getting HDCP info for input {i+1}: {e}")
                input_hdcp_auth.append(0)
                input_hdcp_status.append('0')
        
        # HDCP статус выхода
        output_hdcp = '0'
        try:
            result = self.send_command('wO1HDCP')
            if result and result.get('success') and result.get('response'):
                output_hdcp = result['response']
        except Exception as e:
            self._raise_if_fatal_failure(e)
            print(f"Error getting output HDCP: {e}")
        
        return {
            'input_auth': input_hdcp_auth,
            'input_status': input_hdcp_status,
            'output_status': output_hdcp
        }
    
    def get_connections(self):
        """Получение текущих коммутаций"""
        connections = []
        
        try:
            # Для IN1804 используем команду '!'
            result = self.send_command('!')
            if result and result.get('success') and result.get('response'):
                response_str = result['response']
                print(f"Connections response: {response_str}")
                # Извлекаем цифры из ответа
                digits = ''.join(filter(str.isdigit, response_str))
                if digits:
                    connections.append(int(digits))
                else:
                    connections.append(1)  # Значение по умолчанию
            else:
                return []
                
        except Exception as e:
            self._raise_if_fatal_failure(e)
            print(f"Error in get_connections: {e}")
            return []
        
        return connections
    
    def get_full_status(self):
        """Получение полного статуса матрицы"""
        status = {}
        
        # Базовая информация
        status['device_info'] = self.get_device_info()
        
        # Названия входов и выходов
        status['input_names'] = self.get_input_names()
        status['output_names'] = self.get_output_names()
        
        # Статус сигналов
        status['signal_status'] = self.get_signal_status()
        
        # HDCP информация
        hdcp_info = self.get_hdcp_info()
        status['input_hdcp_auth'] = hdcp_info['input_auth']
        status['input_hdcp_status'] = hdcp_info['input_status']
        status['output_hdcp'] = hdcp_info['output_status']
        
        # Коммутации
        status['connections'] = self.get_connections()
        
        # Дополнительная информация
        status['inputs_num'] = self.inputs_num
        status['outputs_num'] = self.outputs_num
        status['connection_protocol'] = self.connection_protocol
        
        return status
    
    def set_connection(self, output_num, input_num):
        """Установка коммутации (выход всегда 1 для этой модели)"""
        if output_num != 1:
            raise ValueError("This matrix has only one output")
        
        if input_num < 1 or input_num > self.inputs_num:
            raise ValueError(f"Input number must be between 1 and {self.inputs_num}")
        
        # Отправляем команду в зависимости от модели
        if '1804' in self.model or '1608' in self.model:
            command = f'{input_num}*1!'
        elif '1808' in self.model:
            command = f'{input_num}*1!'
        else:
            command = f'{input_num}*1!'
        
        print(f"Sending switch command: {command}")
        result = self.send_command(command, replay_safe=False)
        
        if result and result.get('success'):
            print(f"Successfully switched to input {input_num}")
            return True
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            raise Exception(f"Failed to switch: {error}")    
    
