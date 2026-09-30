"""Guard that keeps document text on the machine when an LLM endpoint is configured."""

import ipaddress
from urllib.parse import urlparse

from data_ingestor.core.exceptions import ConfigurationError


def is_loopback_url(url: str | None) -> bool:
    """True only for http(s) URLs whose host is literally localhost or a loopback address.

    Hostnames are never resolved: a name that merely points at a local address today could
    point elsewhere tomorrow. Userinfo tricks such as ``http://127.0.0.1@host`` are judged by
    the real host, which is what ``urlparse`` returns as ``hostname``.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = parsed.hostname
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not host:
        return False
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_local_llm_endpoint(url: str | None) -> None:
    """Raise unless ``url`` is a loopback endpoint.

    # #CRITICAL: Privacy: Document text must never leave the machine through an LLM call
    # #VERIFY: Called at startup and again before each LLM converter is built

    Raises:
        ConfigurationError: If the endpoint is unset or not loopback
    """
    if not is_loopback_url(url):
        msg = (
            "Marker LLM mode is enabled but MARKER_LLM_BASE_URL is unset or not a local endpoint. "
            "Document text must not leave this machine: point it at a loopback address "
            "(localhost, 127.0.0.0/8, ::1) or set MARKER_USE_LLM=false."
        )
        raise ConfigurationError(msg)
