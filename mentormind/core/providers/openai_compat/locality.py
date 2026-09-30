"""Is an endpoint URL on the premises or on the internet? Decides a provider's cloud flag."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit


def is_private_url(url: str) -> bool:
    """True when ``url`` points at this machine or a private network (not the internet).

    Loopback/private/link-local/CGNAT addresses (the last covers Tailscale), ``localhost``,
    single-label LAN hostnames and ``.local``/``.lan``/``.internal`` names count as private.
    Anything else is treated as cloud: guessing wrong in that direction only costs a refusal.
    """
    host = (urlsplit(url).hostname or "").lower()
    if not host:
        return False
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return not ipaddress.ip_address(host).is_global
    except ValueError:
        return "." not in host or host.endswith((".local", ".lan", ".internal", ".home.arpa"))
