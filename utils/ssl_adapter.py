from requests.adapters import HTTPAdapter

class SSLAdapter(HTTPAdapter):
    """Адаптер для старых SSL протоколов"""
    
    def init_poolmanager(self, *args, **kwargs):
        """Инициализация пула соединений с SSL контекстом"""
        import ssl
        context = ssl.create_default_context()
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

