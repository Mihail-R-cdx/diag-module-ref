import os
import ssl
from typing import Any, Dict

try:
    import pycurl
except ImportError:
    pycurl = None


def inspect_te20_https_stack() -> Dict[str, Any]:
    """Return TE20 HTTPS transport diagnostics before any network activity starts."""
    result = {
        "ready": False,
        "transport": "requests/OpenSSL",
        "details": ssl.OPENSSL_VERSION,
        "warning": "",
    }

    if pycurl is None:
        result["warning"] = (
            "Для TE20 по HTTPS требуется pycurl с backend Schannel. "
            "В текущем Python модуль pycurl не найден."
        )
        return result

    pycurl_version = pycurl.version
    result["details"] = pycurl_version

    if os.name == "nt":
        if "Schannel" in pycurl_version:
            result["ready"] = True
            result["transport"] = "pycurl/Schannel"
            return result

        result["transport"] = "pycurl"
        result["warning"] = (
            "Для TE20 по HTTPS на Windows требуется pycurl, собранный с Schannel. "
            f"Текущий backend: {pycurl_version}"
        )
        return result

    result["transport"] = "pycurl"
    result["warning"] = (
        "Текущий HTTPS transport для TE20 проверен только на Windows с pycurl/Schannel. "
        f"Текущий backend: {pycurl_version}"
    )
    return result
