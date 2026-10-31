import pytest
from netlog.core.services import get_service_name
from netlog.core.models import ConnectionInfo

def test_common_services_lookup():
    assert get_service_name(80) == "http"
    assert get_service_name(443) == "https"
    assert get_service_name(22) == "ssh"
    assert get_service_name(5432) == "postgres"
    assert get_service_name(6379) == "redis"
    assert get_service_name(53, "udp") == "dns"
    assert get_service_name(None) is None
    assert get_service_name(0) is None
    assert get_service_name(-1) is None

def test_connection_info_service_properties():
    conn = ConnectionInfo(
        fd=10,
        family="IPv4",
        proto="TCP",
        laddr="127.0.0.1",
        lport=5432,
        raddr="1.1.1.1",
        rport=53,
        status="ESTABLISHED",
        pid=100,
        process_name="postgres",
        user="postgres"
    )
    assert conn.local_service == "postgres"
    assert conn.remote_service == "dns"

def test_stateless_no_remote_service():
    conn = ConnectionInfo(
        fd=11,
        family="IPv4",
        proto="UDP",
        laddr="0.0.0.0",
        lport=5353,
        raddr=None,
        rport=None,
        status="STATELESS",
        pid=101,
        process_name="avahi",
        user="avahi"
    )
    assert conn.remote_service is None
