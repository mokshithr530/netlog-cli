import socket
from typing import Optional, Dict

COMMON_SERVICES: Dict[int, str] = {
    20: "ftp-data",
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    67: "dhcp",
    68: "dhcp",
    80: "http",
    110: "pop3",
    123: "ntp",
    143: "imap",
    443: "https",
    465: "smtps",
    587: "smtp-sub",
    853: "dns-tls",
    993: "imaps",
    995: "pop3s",
    1080: "socks",
    1433: "mssql",
    1521: "oracle",
    2049: "nfs",
    2375: "docker",
    2376: "docker-s",
    3000: "http-dev",
    3306: "mysql",
    3389: "rdp",
    5000: "http-dev",
    5432: "postgres",
    5900: "vnc",
    6379: "redis",
    8000: "http-alt",
    8080: "http-proxy",
    8443: "https-alt",
    9000: "http-alt",
    9090: "prometheus",
    9092: "kafka",
    9200: "elastic",
    9993: "zerotier",
    27017: "mongodb",
}

_SERVICE_CACHE: Dict[tuple, Optional[str]] = {}

def get_service_name(port: Optional[int], proto: str = "tcp") -> Optional[str]:
    """
    Resolves a port number to its common service name.
    Checks common definitions first, then system services with caching.
    """
    if port is None or port <= 0:
        return None

    proto_lower = proto.lower()
    cache_key = (port, proto_lower)
    if cache_key in _SERVICE_CACHE:
        return _SERVICE_CACHE[cache_key]

    if port in COMMON_SERVICES:
        svc = COMMON_SERVICES[port]
        _SERVICE_CACHE[cache_key] = svc
        return svc

    try:
        svc = socket.getservbyport(port, proto_lower)
        _SERVICE_CACHE[cache_key] = svc
        return svc
    except (OSError, socket.error):
        _SERVICE_CACHE[cache_key] = None
        return None
