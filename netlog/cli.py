import argparse
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.live import Live

from netlog import __version__
from netlog.core.metrics import RateCalculator
from netlog.core.resolver import AsyncDNSResolver
from netlog.core.geoip import AsyncGeoIPResolver
from netlog.core.anomaly import AnomalyDetector
from netlog.core.inspect import inspect_process, kill_process
from netlog.ui.dashboard import (
    render_dashboard,
    create_connections_table,
    get_filtered_connections,
)
from netlog.core.models import ConnectionInfo
from netlog.core.config import load_config
from netlog.ui.keyboard import KeyboardInput
from netlog.exporters.logger import TrafficExporter

def parse_args():
    parser = argparse.ArgumentParser(
        prog="netlog",
        description="High-performance CLI network telemetry dashboard tracking socket states, live bandwidth, and async DNS."
    )
    parser.add_argument(
        "-i", "--interval",
        type=float,
        default=1.0,
        help="Refresh sampling interval in seconds (default: 1.0)"
    )
    parser.add_argument(
        "-p", "--process",
        type=str,
        default=None,
        help="Filter connections matching process name (case-insensitive substring)"
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to custom configuration file (default: ~/.config/netlog/config.toml)"
    )
    parser.add_argument(
        "-n", "--rows",
        type=int,
        default=None,
        help="Maximum rows to display in table (default: auto-detected from terminal height)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Capture a single snapshot, display in terminal, and exit immediately"
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        metavar="PATH",
        help="Export snapshot to CSV file"
    )
    parser.add_argument(
        "--export-json",
        type=str,
        metavar="PATH",
        help="Stream snapshots as structured JSON lines"
    )
    parser.add_argument(
        "--prometheus-port",
        type=int,
        metavar="PORT",
        default=None,
        help="Expose Prometheus /metrics endpoint on specified HTTP port"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run as a headless background daemon (e.g. for Prometheus scraping without TUI)"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"netlog-cli {__version__}"
    )
    return parser.parse_args()

def get_effective_rows(console: Console, user_rows: Optional[int]) -> int:
    """Computes visible table rows, auto-adapting to terminal height if unconfigured."""
    if user_rows and user_rows > 0:
        return user_rows
    # Auto-detect from terminal height: subtract header (3), footer (3), and table headers (2)
    return max(5, console.size.height - 8)

def main():
    args = parse_args()
    console = Console()

    cfg_path = Path(args.config) if args.config else None
    cfg = load_config(cfg_path)

    interval = args.interval if args.interval != 1.0 else cfg.get("interval", 1.0)
    process_filter = args.process if args.process is not None else cfg.get("process")
    rows_setting = args.rows if args.rows is not None else cfg.get("rows")
    prom_port = args.prometheus_port if args.prometheus_port is not None else cfg.get("prometheus_port")

    rate_engine = RateCalculator()
    dns_resolver = AsyncDNSResolver()
    geoip_resolver = AsyncGeoIPResolver()
    anomaly_detector = AnomalyDetector()

    if args.once:
        snapshot = rate_engine.capture_snapshot()
        anomaly_detector.inspect_connections(snapshot.connections, snapshot.processes)

        if args.export_csv:
            TrafficExporter.export_csv(snapshot.connections, args.export_csv)
            console.print(f"[green]✔ Exported {len(snapshot.connections)} records to {args.export_csv}[/green]")

        if args.export_json:
            TrafficExporter.export_json(snapshot.connections, args.export_json)
            console.print(f"[green]✔ Exported {len(snapshot.connections)} records to {args.export_json}[/green]")

        effective_rows = get_effective_rows(console, rows_setting)
        table = create_connections_table(
            snapshot.connections,
            dns_resolver,
            max_rows=effective_rows,
            filter_process=process_filter,
            geoip_resolver=geoip_resolver
        )
        console.print(table)
        dns_resolver.shutdown()
        geoip_resolver.shutdown()
        return

    prom_server = None
    if prom_port:
        from netlog.exporters.prometheus import start_prometheus_server
        prom_server = start_prometheus_server(
            rate_engine,
            port=prom_port,
            anomaly_detector=anomaly_detector,
            background=not args.headless
        )
        console.print(f"[green]✔ Prometheus exporter listening on http://0.0.0.0:{prom_port}/metrics[/green]")
        if args.headless:
            console.print("[cyan]Running in headless daemon mode. Press Ctrl+C to stop.[/cyan]")
            try:
                prom_server.serve_forever()
            except KeyboardInterrupt:
                console.print("\n[yellow]Headless exporter stopped cleanly.[/yellow]")
            finally:
                prom_server.server_close()
                dns_resolver.shutdown()
                geoip_resolver.shutdown()
            return

    # Live Interactive Loop
    sort_modes = ["default", "pid", "process", "state", "proto"]
    cfg_sort = cfg.get("sort_by", "default")
    sort_idx = sort_modes.index(cfg_sort) if cfg_sort in sort_modes else 0
    is_paused = False
    is_searching = False
    search_buffer = ""
    active_filter = process_filter
    selected_idx = 0
    is_inspecting = False
    inspect_conn = None
    inspect_data = None
    confirm_kill = None
    status_msg = ""
    status_msg_time = 0.0

    snapshot = rate_engine.capture_snapshot()
    anomaly_detector.inspect_connections(snapshot.connections, snapshot.processes)
    last_sample_time = time.time()

    try:
        with KeyboardInput() as kbd, Live(console=console, screen=True, auto_refresh=True) as live:
            while True:
                # Poll non-blocking keyboard input (50ms timeout)
                key = kbd.get_key(timeout=0.05)
                now = time.time()

                if status_msg and (now - status_msg_time > 3.0):
                    status_msg = ""

                current_sort = sort_modes[sort_idx]
                effective_filter = search_buffer if is_searching else active_filter
                effective_rows = get_effective_rows(console, rows_setting)
                visible_conns = get_filtered_connections(
                    snapshot.connections,
                    filter_query=effective_filter,
                    sort_by=current_sort,
                )
                max_visible = min(len(visible_conns), effective_rows)
                if max_visible > 0:
                    selected_idx = max(0, min(selected_idx, max_visible - 1))
                else:
                    selected_idx = 0

                if confirm_kill:
                    if key:
                        if key.lower() == 'y':
                            pid, name = confirm_kill
                            ok, msg = kill_process(pid)
                            status_msg = msg
                            status_msg_time = now
                            confirm_kill = None
                        elif key.lower() in ('n', 'q') or key == '\x1b':
                            confirm_kill = None
                elif is_inspecting:
                    if key:
                        if key in ('\r', '\n', '\x1b', 'q', 'Q'):
                            is_inspecting = False
                            inspect_conn = None
                            inspect_data = None
                        elif key.lower() == 'k':
                            if inspect_conn and inspect_conn.pid and inspect_conn.pid > 0:
                                confirm_kill = (inspect_conn.pid, inspect_conn.process_name)
                                is_inspecting = False
                elif is_searching:
                    if key:
                        if key in ('\r', '\n'):  # Enter: confirm search
                            is_searching = False
                            active_filter = search_buffer if search_buffer.strip() else None
                        elif key == '\x1b':  # Escape: cancel search
                            is_searching = False
                            search_buffer = ""
                            active_filter = process_filter
                        elif key in ('\x7f', '\x08'):  # Backspace
                            search_buffer = search_buffer[:-1]
                        elif len(key) == 1 and 32 <= ord(key) <= 126:
                            search_buffer += key
                else:
                    if key:
                        key_lower = key.lower()
                        if key in ('q', '\x03'):
                            break
                        elif key == '/':
                            is_searching = True
                            search_buffer = active_filter or ""
                        elif key == 'up':
                            selected_idx = max(0, selected_idx - 1)
                        elif key == 'down':
                            selected_idx = min(max_visible - 1, selected_idx + 1)
                        elif key in ('\r', '\n'):
                            if visible_conns:
                                inspect_conn = visible_conns[selected_idx]
                                inspect_data = inspect_process(inspect_conn.pid)
                                is_inspecting = True
                        elif key_lower == 'k':
                            if visible_conns:
                                target = visible_conns[selected_idx]
                                if target.pid and target.pid > 0:
                                    confirm_kill = (target.pid, target.process_name)
                                else:
                                    status_msg = "Cannot kill system / idle socket (no PID)"
                                    status_msg_time = now
                        elif key_lower == 's':
                            sort_idx = (sort_idx + 1) % len(sort_modes)
                        elif key_lower in ('p', ' '):
                            is_paused = not is_paused
                        elif key_lower == 'r':
                            sort_idx = 0
                            active_filter = process_filter
                            search_buffer = ""
                            selected_idx = 0

                if not is_paused and (now - last_sample_time >= interval):
                    snapshot = rate_engine.capture_snapshot()
                    anomaly_detector.inspect_connections(snapshot.connections, snapshot.processes)

                    if args.export_json:
                        TrafficExporter.export_json(snapshot.connections, args.export_json)
                    last_sample_time = now

                layout = render_dashboard(
                    snapshot,
                    dns_resolver,
                    filter_process=effective_filter,
                    max_rows=effective_rows,
                    sort_by=current_sort,
                    is_paused=is_paused,
                    geoip_resolver=geoip_resolver,
                    is_searching=is_searching,
                    search_buffer=search_buffer,
                    selected_index=selected_idx,
                    inspecting_conn=inspect_conn if is_inspecting else None,
                    inspect_data=inspect_data if is_inspecting else None,
                    confirm_kill=confirm_kill,
                    status_msg=status_msg,
                )
                live.update(layout)

    except KeyboardInterrupt:
        pass
    finally:
        if prom_server:
            try:
                prom_server.server_close()
            except Exception:
                pass
        dns_resolver.shutdown()
        geoip_resolver.shutdown()
        console.print("\n[bold cyan]netlog-cli stopped cleanly. Goodbye![/bold cyan]")

if __name__ == "__main__":
    main()
