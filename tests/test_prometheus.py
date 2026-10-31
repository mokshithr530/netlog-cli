import urllib.request
import time
import pytest
from netlog.core.models import NetworkSnapshot, ConnectionInfo, ProcessNetworkStats
from netlog.core.metrics import RateCalculator
from netlog.exporters.prometheus import generate_prometheus_metrics, start_prometheus_server

def test_generate_prometheus_metrics():
    conn = ConnectionInfo(
        fd=1,
        family="IPv4",
        proto="TCP",
        laddr="127.0.0.1",
        lport=8080,
        raddr="1.1.1.1",
        rport=443,
        status="ESTABLISHED",
        pid=123,
        process_name="curl",
        user="test"
    )
    snapshot = NetworkSnapshot(
        timestamp=time.time(),
        total_connections=1,
        active_processes_count=1,
        system_bytes_sent=1000,
        system_bytes_recv=2000,
        system_upload_rate=5.5,
        system_download_rate=12.3,
        connections=[conn],
        processes={123: ProcessNetworkStats(pid=123, name="curl", user="test", connections_count=1, established_count=1, listen_count=0)}
    )

    metrics = generate_prometheus_metrics(snapshot)
    assert "netlog_active_connections 1" in metrics
    assert "netlog_tracked_processes 1" in metrics
    assert 'netlog_connections_by_state{state="ESTABLISHED"} 1' in metrics
    assert 'netlog_connections_by_protocol{protocol="TCP"} 1' in metrics
    assert "netlog_bandwidth_download_kbps 12.30" in metrics
    assert "netlog_bandwidth_upload_kbps 5.50" in metrics
    assert "netlog_system_bytes_recv_total 2000" in metrics
    assert "netlog_system_bytes_sent_total 1000" in metrics

def test_prometheus_http_server():
    rate_engine = RateCalculator()
    server = start_prometheus_server(rate_engine, port=19100, host="127.0.0.1", background=True)
    time.sleep(0.1)

    try:
        url = "http://127.0.0.1:19100/metrics"
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "netlog_active_connections" in content
    finally:
        server.server_close()
