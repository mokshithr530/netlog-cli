from typing import List, Optional
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich import box
from netlog.core.models import NetworkSnapshot, ConnectionInfo
from netlog.core.resolver import AsyncDNSResolver
from netlog.core.geoip import AsyncGeoIPResolver

STATUS_COLORS = {
    "ESTABLISHED": "bold green",
    "SYN_SENT": "bold magenta",
    "SYN_RECV": "magenta",
    "FIN_WAIT1": "yellow",
    "FIN_WAIT2": "yellow",
    "TIME_WAIT": "dim yellow",
    "CLOSE": "dim white",
    "CLOSE_WAIT": "dark_orange",
    "LAST_ACK": "dark_orange",
    "LISTEN": "bold cyan",
    "CLOSING": "red",
    "NONE": "dim white",
    "STATELESS": "bright_blue",
}

def format_rate(kbps: float) -> str:
    if kbps >= 1024.0:
        return f"{kbps / 1024.0:.1f} MB/s"
    return f"{kbps:.1f} KB/s"

def create_header_panel(snapshot: NetworkSnapshot, is_paused: bool = False) -> Panel:
    text = Text()
    text.append(" 🌐 NETLOG-CLI ", style="bold black on bright_cyan")
    if is_paused:
        text.append(" [PAUSED] ", style="bold bright_white on red")
    text.append("  |  Active Sockets: ", style="bold white")
    text.append(str(snapshot.total_connections), style="bold yellow")
    text.append("  |  Tracked Processes: ", style="bold white")
    text.append(str(snapshot.active_processes_count), style="bold yellow")
    text.append("  |  ▼ Down: ", style="bold green")
    text.append(format_rate(snapshot.system_download_rate), style="bold bright_green")
    if snapshot.download_sparkline:
        text.append(f" {snapshot.download_sparkline}", style="bright_green")
    text.append("  ▲ Up: ", style="bold cyan")
    text.append(format_rate(snapshot.system_upload_rate), style="bold bright_cyan")
    if snapshot.upload_sparkline:
        text.append(f" {snapshot.upload_sparkline}", style="bright_cyan")

    return Panel(
        text,
        box=box.ROUNDED,
        border_style="bright_blue",
        padding=(0, 1),
    )

def create_footer_panel(
    sort_mode: str = "default",
    is_paused: bool = False,
    search_query: Optional[str] = None,
    is_searching: bool = False
) -> Panel:
    text = Text()
    if is_searching:
        text.append(" 🔍 SEARCH: ", style="bold black on bright_yellow")
        text.append(f" {search_query or ''}_ ", style="bold bright_white")
        text.append(" (Enter: Apply | Esc: Clear)", style="dim white")
    else:
        text.append(" [q] ", style="bold cyan")
        text.append("Quit  ", style="dim white")
        text.append(" [/] ", style="bold cyan")
        if search_query:
            text.append(f"Filter: '{search_query}'  ", style="bold bright_green")
        else:
            text.append("Filter  ", style="dim white")
        text.append(" [s] ", style="bold cyan")
        text.append(f"Sort: {sort_mode}  ", style="bold yellow")
        text.append(" [p/space] ", style="bold cyan")
        text.append("Resume  " if is_paused else "Pause  ", style="bold red" if is_paused else "dim white")
        text.append(" [r] ", style="bold cyan")
        text.append("Reset Sort", style="dim white")
    return Panel(text, box=box.ROUNDED, border_style="grey37", padding=(0, 1))

def create_connections_table(
    connections: List[ConnectionInfo],
    resolver: AsyncDNSResolver,
    max_rows: int = 25,
    filter_process: Optional[str] = None,
    filter_query: Optional[str] = None,
    sort_by: str = "default",
    geoip_resolver: Optional[AsyncGeoIPResolver] = None
) -> Table:
    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold bright_white on grey23",
        expand=True,
        row_styles=["none", "dim"],
    )

    table.add_column("PID", justify="right", style="cyan", no_wrap=True, width=7)
    table.add_column("Process", style="bold white", width=16)
    table.add_column("Proto", justify="center", style="yellow", width=6)
    table.add_column("Local Endpoint", style="green", width=25)
    table.add_column("Remote Endpoint", style="bright_blue", width=25)
    table.add_column("Peer / Geo", style="italic bright_white", width=26)
    table.add_column("State", justify="center", width=14)
    table.add_column("Status / Alert", style="bold red")

    filtered = list(connections)
    active_search = filter_query or filter_process
    if active_search:
        q = active_search.lower()
        filtered = [
            c for c in filtered
            if q in c.process_name.lower()
            or q in c.remote_endpoint.lower()
            or q in c.local_endpoint.lower()
            or (c.local_service and q in c.local_service.lower())
            or (c.remote_service and q in c.remote_service.lower())
            or q in c.status.lower()
            or q in c.proto.lower()
            or (c.pid is not None and q in str(c.pid))
        ]

    if sort_by == "pid":
        filtered.sort(key=lambda c: c.pid or 0)
    elif sort_by == "process":
        filtered.sort(key=lambda c: (c.process_name or "").lower())
    elif sort_by == "state":
        filtered.sort(key=lambda c: c.status)
    elif sort_by == "proto":
        filtered.sort(key=lambda c: c.proto)

    for conn in filtered[:max_rows]:
        pid_str = str(conn.pid) if conn.pid else "-"
        state_color = STATUS_COLORS.get(conn.status, "white")
        state_text = Text(conn.status, style=state_color)

        peer_host = resolver.resolve(conn.raddr)
        if geoip_resolver and conn.raddr:
            geo = geoip_resolver.lookup(conn.raddr)
            if geo and geo.country_code:
                peer_host = f"{peer_host} [{geo.country_code}]"

        if len(peer_host) > 25:
            peer_host = peer_host[:22] + "..."

        alert_text = Text()
        if conn.is_suspicious:
            alert_text.append("⚠ " + conn.anomaly_reason, style="bold red")
        else:
            alert_text.append("OK", style="dim green")

        proc_disp = conn.process_name
        if len(proc_disp) > 15:
            proc_disp = proc_disp[:13] + ".."

        l_endpoint = f"{conn.local_endpoint} ({conn.local_service})" if conn.local_service else conn.local_endpoint
        r_endpoint = f"{conn.remote_endpoint} ({conn.remote_service})" if conn.remote_service and conn.raddr else conn.remote_endpoint

        table.add_row(
            pid_str,
            proc_disp,
            conn.proto,
            l_endpoint,
            r_endpoint,
            peer_host,
            state_text,
            alert_text,
        )

    return table

def render_dashboard(
    snapshot: NetworkSnapshot,
    resolver: AsyncDNSResolver,
    filter_process: Optional[str] = None,
    max_rows: int = 25,
    sort_by: str = "default",
    is_paused: bool = False,
    geoip_resolver: Optional[AsyncGeoIPResolver] = None,
    is_searching: bool = False,
    search_buffer: str = ""
) -> Layout:
    active_filter = search_buffer if is_searching else filter_process
    layout = Layout()
    layout.split_column(
        Layout(create_header_panel(snapshot, is_paused=is_paused), size=3),
        Layout(create_connections_table(snapshot.connections, resolver, max_rows, filter_query=active_filter, sort_by=sort_by, geoip_resolver=geoip_resolver)),
        Layout(create_footer_panel(sort_mode=sort_by, is_paused=is_paused, search_query=active_filter, is_searching=is_searching), size=3)
    )
    return layout
