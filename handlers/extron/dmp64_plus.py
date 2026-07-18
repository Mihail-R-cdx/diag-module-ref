"""Extron DMP 64 Plus SIS-over-SSH meter handler."""

from __future__ import annotations

from typing import Any, Callable

from core.dmp64_plus import (
    DMPCancellationToken,
    DMPTransportSession,
    DMPUnsupportedModel,
    SIS_PORT,
    build_meter_snapshot,
    is_supported_dmp64_plus_variant,
    require_assigned_credentials,
)
from core.exceptions import AuthenticationError, ConnectionError
from core.redaction import redact_exception


class ExtronDMP64PlusHandler:
    """Read physical DMP 64 Plus input/output meters through one SSH SIS session."""

    def __init__(
        self,
        ip_address: str,
        username: str | None = None,
        password: str | None = None,
        *,
        port: int = SIS_PORT,
        timeout: float = 1.5,
        transport_factory: Callable[..., DMPTransportSession] | None = None,
    ) -> None:
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.transport_factory = transport_factory or _ParamikoDMPSession.open
        self.session: DMPTransportSession | None = None
        self.discovered_model: str | None = None

    def connect(self) -> bool:
        require_assigned_credentials(self.username, self.password)
        try:
            self.session = self.transport_factory(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
            )
            self.discovered_model = self.session.read_model_identity()
            if not is_supported_dmp64_plus_variant(self.discovered_model):
                raise DMPUnsupportedModel(
                    "Unsupported Extron DMP 64 Plus variant: "
                    f"{self.discovered_model or '<empty>'}"
                )
            return True
        except AuthenticationError:
            self.session = None
            raise
        except DMPUnsupportedModel:
            self.disconnect()
            raise
        except Exception as error:
            self.session = None
            if _looks_like_paramiko_authentication(error):
                raise AuthenticationError("Extron DMP 64 Plus rejected the assigned credential.") from error
            safe_error = redact_exception(error, (self.username, self.password))
            raise ConnectionError(f"Extron DMP 64 Plus SSH/SIS connection failed: {safe_error}") from error

    def get_meter_snapshot(self, cancellation: DMPCancellationToken | None = None) -> dict[str, Any]:
        if self.session is None:
            raise ConnectionError("Extron DMP 64 Plus handler is not connected.")
        return build_meter_snapshot(
            self.session,
            ip_address=self.ip_address,
            discovered_model=self.discovered_model,
            cancellation=cancellation,
        )

    def disconnect(self) -> None:
        session = self.session
        self.session = None
        if session is not None:
            try:
                session.close()
            except Exception:
                pass


class _ParamikoDMPSession:
    @staticmethod
    def open(
        *,
        ip_address: str,
        port: int,
        username: str,
        password: str,
        timeout: float,
    ) -> DMPTransportSession:
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                ip_address,
                port=port,
                username=username,
                password=password,
                timeout=timeout,
                banner_timeout=timeout,
                auth_timeout=timeout,
                look_for_keys=False,
                allow_agent=False,
            )
            transport = client.get_transport()
            if transport is None:
                raise ConnectionError("SSH transport was not established.")
            channel = transport.open_session()
            channel.get_pty(term="vt100")
            channel.invoke_shell()
            channel.settimeout(timeout)
        except Exception:
            try:
                client.close()
            finally:
                raise

        def close() -> None:
            try:
                channel.close()
            finally:
                client.close()

        return DMPTransportSession(
            channel,
            close_callback=close,
            transaction_timeout=timeout,
        )


def _looks_like_paramiko_authentication(error: BaseException) -> bool:
    try:
        import paramiko
    except Exception:
        return False
    return isinstance(
        error,
        (
            paramiko.AuthenticationException,
            paramiko.BadAuthenticationType,
            paramiko.PartialAuthentication,
        ),
    )


__all__ = ["DMPUnsupportedModel", "ExtronDMP64PlusHandler"]
