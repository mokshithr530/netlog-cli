import argparse
import sys
import time
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
        "-n", "--rows",
        type=int,
        default=25,
        help="Maximum rows to display in the live table (default: 25)"
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
        "-v", "--version",
        action="version",
        version=f"netlog-cli {__version__}"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    console = Console()

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

        table = create_connections_table(
            snapshot.connections,
            dns_resolver,
            max_rows=args.rows,
            filter_process=args.process,
            geoip_resolver=geoip_resolver
        )
        console.print(table)
        dns_resolver.shutdown()
        geoip_resolver.shutdown()
        return

    # Live Interactive Loop
    sort_modes = ["default", "pid", "process", "state", "proto"]
    sort_idx = 0
    is_paused = False
    is_searching = False
    search_buffer = ""
    active_filter = args.process
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
                visible_conns = get_filtered_connections(
                    snapshot.connections,
                    filter_query=effective_filter,
                    sort_by=current_sort,
                )
                max_visible = min(len(visible_conns), args.rows)
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
                            active_filter = args.process
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
                            active_filter = args.process
                            search_buffer = ""
                            selected_idx = 0

                if not is_paused and (now - last_sample_time >= args.interval):
                    snapshot = rate_engine.capture_snapshot()
                    anomaly_detector.inspect_connections(snapshot.connections, snapshot.processes)

                    if args.export_json:
                        TrafficExporter.export_json(snapshot.connections, args.export_json)
                    last_sample_time = now

                layout = render_dashboard(
                    snapshot,
                    dns_resolver,
                    filter_process=effective_filter,
                    max_rows=args.rows,
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
        dns_resolver.shutdown()
        geoip_resolver.shutdown()
        console.print("\n[bold cyan]netlog-cli stopped cleanly. Goodbye![/bold cyan]")

if __name__ == "__main__":
    main()
