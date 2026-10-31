import threading
import time
import collections
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from netlog.core.models import NetworkSnapshot
from netlog.core.metrics import RateCalculator
from netlog.core.anomaly import AnomalyDetector

def generate_prometheus_metrics(snapshot: NetworkSnapshot) -> str:
    """
    Renders a standard Prometheus text exposition format (/metrics) payload.
    """
    lines = []

    # Active Connections
    lines.append("# HELP netlog_active_connections Total number of active network connections")
    lines.append("# TYPE netlog_active_connections gauge")
    lines.append(f"netlog_active_connections {snapshot.total_connections}")

    # Tracked Processes
    lines.append("# HELP netlog_tracked_processes Total number of active processes with network sockets")
    lines.append("# TYPE netlog_tracked_processes gauge")
    lines.append(f"netlog_tracked_processes {snapshot.active_processes_count}")

    # Connections by State
    state_counts = collections.Counter(c.status for c in snapshot.connections)
    lines.append("# HELP netlog_connections_by_state Number of connections grouped by socket status")
    lines.append("# TYPE netlog_connections_by_state gauge")
    for state, count in sorted(state_counts.items()):
        lines.append(f'netlog_connections_by_state{{state="{state}"}} {count}')

    # Connections by Protocol
    proto_counts = collections.Counter(c.proto for c in snapshot.connections)
    lines.append("# HELP netlog_connections_by_protocol Number of connections grouped by protocol")
    lines.append("# TYPE netlog_connections_by_protocol gauge")
    for proto, count in sorted(proto_counts.items()):
        lines.append(f'netlog_connections_by_protocol{{protocol="{proto}"}} {count}')

    # Bandwidth Rates
    lines.append("# HELP netlog_bandwidth_download_kbps Current system download throughput in KB/s")
    lines.append("# TYPE netlog_bandwidth_download_kbps gauge")
    lines.append(f"netlog_bandwidth_download_kbps {snapshot.system_download_rate:.2f}")

    lines.append("# HELP netlog_bandwidth_upload_kbps Current system upload throughput in KB/s")
    lines.append("# TYPE netlog_bandwidth_upload_kbps gauge")
    lines.append(f"netlog_bandwidth_upload_kbps {snapshot.system_upload_rate:.2f}")

    # Cumulative Bytes
    lines.append("# HELP netlog_system_bytes_recv_total Total system bytes received")
    lines.append("# TYPE netlog_system_bytes_recv_total counter")
    lines.append(f"netlog_system_bytes_recv_total {snapshot.system_bytes_recv}")

    lines.append("# HELP netlog_system_bytes_sent_total Total system bytes sent")
    lines.append("# TYPE netlog_system_bytes_sent_total counter")
    lines.append(f"netlog_system_bytes_sent_total {snapshot.system_bytes_sent}")

    # Suspicious / Anomalies
    suspicious_count = sum(1 for c in snapshot.connections if c.is_suspicious)
    lines.append("# HELP netlog_anomalies_detected Total suspicious or security anomaly connections")
    lines.append("# TYPE netlog_anomalies_detected gauge")
    lines.append(f"netlog_anomalies_detected {suspicious_count}")

    lines.append("")
    return "\n".join(lines)


class _MetricsHandler(BaseHTTPRequestHandler):
    rate_engine: Optional[RateCalculator] = None
    anomaly_detector: Optional[AnomalyDetector] = None

    def log_message(self, format, *args):
        # Silence default stderr request logging
        pass

    def do_GET(self):
        if self.path in ("/metrics", "/metrics/"):
            if not self.rate_engine:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Rate engine not initialized\n")
                return

            snapshot = self.rate_engine.capture_snapshot()
            if self.anomaly_detector:
                self.anomaly_detector.inspect_connections(snapshot.connections, snapshot.processes)

            payload = generate_prometheus_metrics(snapshot).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/":
            body = b"<html><body><h1>netlog-cli Prometheus Exporter</h1><p><a href='/metrics'>Metrics Endpoint</a></p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found\n")


def start_prometheus_server(
    rate_engine: RateCalculator,
    port: int = 9100,
    host: str = "0.0.0.0",
    anomaly_detector: Optional[AnomalyDetector] = None,
    background: bool = True
) -> HTTPServer:
    """
    Starts a zero-dependency HTTP server exposing /metrics for Prometheus scrapers.
    """
    _MetricsHandler.rate_engine = rate_engine
    _MetricsHandler.anomaly_detector = anomaly_detector or AnomalyDetector()

    server = HTTPServer((host, port), _MetricsHandler)
    if background:
        thread = threading.Thread(target=server.serve_forever, daemon=True, name="netlog-prometheus")
        thread.start()
    return server
