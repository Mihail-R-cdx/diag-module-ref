import ssl

from requests.adapters import HTTPAdapter


def create_legacy_ssl_context(verify_ssl: bool = False) -> ssl.SSLContext:
    """Build an SSL context that is more tolerant of older TLS stacks."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    if verify_ssl:
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    if hasattr(ssl, "TLSVersion"):
        try:
            context.minimum_version = ssl.TLSVersion.TLSv1
        except ValueError:
            pass
        try:
            context.maximum_version = ssl.TLSVersion.TLSv1_2
        except ValueError:
            pass

    for option_name in (
        "OP_LEGACY_SERVER_CONNECT",
        "OP_ALLOW_UNSAFE_LEGACY_RENEGOTIATION",
    ):
        option_value = getattr(ssl, option_name, None)
        if option_value:
            context.options |= option_value

    try:
        context.set_ciphers("DEFAULT@SECLEVEL=0")
    except ssl.SSLError:
        context.set_ciphers("DEFAULT")

    return context


class SSLAdapter(HTTPAdapter):
    """HTTP adapter that uses an explicitly supplied SSL context."""

    def __init__(self, ssl_context: ssl.SSLContext | None = None, **kwargs):
        self.ssl_context = ssl_context or create_legacy_ssl_context()
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = self.ssl_context
        return super().proxy_manager_for(*args, **kwargs)
