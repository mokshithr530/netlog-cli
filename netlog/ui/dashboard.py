from typing import List, Optional, Tuple, Dict, Any
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
    is_searching: bool = False,
    confirm_kill: Optional[Tuple[int, str]] = None,
    status_msg: str = "",
) -> Panel:
    text = Text()
    if confirm_kill:
        pid, name = confirm_kill
        text.append(" ⚠ CONFIRM KILL: ", style="bold bright_white on red")
        text.append(f" Terminate process '{name}' (PID: {pid})? ", style="bold yellow")
        text.append("[y] Yes, Send SIGTERM  ", style="bold green")
        text.append("[n/Esc] Cancel", style="dim white")
    elif status_msg:
        text.append(f" {status_msg} ", style="bold bright_white on blue")
    elif is_searching:
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
        text.append(" [↑/↓] ", style="bold cyan")
        text.append("Select  ", style="dim white")
        text.append(" [Enter] ", style="bold cyan")
        text.append("Inspect  ", style="dim white")
        text.append(" [k] ", style="bold cyan")
        text.append("Kill  ", style="dim white")
        text.append(" [s] ", style="bold cyan")
        text.append(f"Sort: {sort_mode}  ", style="bold yellow")
        text.append(" [p] ", style="bold cyan")
        text.append("Resume  " if is_paused else "Pause  ", style="bold red" if is_paused else "dim white")
        text.append(" [r] ", style="bold cyan")
        text.append("Reset", style="dim white")
    return Panel(text, box=box.ROUNDED, border_style="grey37", padding=(0, 1))

def create_inspect_modal(
    conn: ConnectionInfo,
    proc_info: Dict[str, Any],
    resolver: AsyncDNSResolver,
    geoip_resolver: Optional[AsyncGeoIPResolver] = None
) -> Panel:
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold cyan", width=20)
    grid.add_column(style="bright_white")

    grid.add_row("Process Name:", f"{proc_info.get('name', conn.process_name)} (PID: {proc_info.get('pid', conn.pid)})")
    grid.add_row("User / Owner:", str(proc_info.get("user", conn.user)))
    grid.add_row("Command Line:", str(proc_info.get("cmdline", "-"))[:90])
    grid.add_row("Parent Process:", str(proc_info.get("parent", "-")))
    grid.add_row("Process Status:", str(proc_info.get("status", "-")))
    grid.add_row("Memory (RSS / VMS):", f"{proc_info.get('memory_rss', 'N/A')} / {proc_info.get('memory_vms', 'N/A')}")
    grid.add_row("Working Directory:", str(proc_info.get("cwd", "-")))
    grid.add_row("Started At:", str(proc_info.get("created", "-")))
    grid.add_row("─" * 20, "─" * 50)
    grid.add_row("Socket Protocol:", f"{conn.proto} ({conn.family})")
    l_svc = f" ({conn.local_service})" if conn.local_service else ""
    grid.add_row("Local Endpoint:", f"{conn.local_endpoint}{l_svc}")
    r_svc = f" ({conn.remote_service})" if conn.remote_service else ""
    grid.add_row("Remote Endpoint:", f"{conn.remote_endpoint}{r_svc}")
    grid.add_row("Socket State:", conn.status)

    peer_host = resolver.resolve(conn.raddr)
    if geoip_resolver and conn.raddr:
        geo = geoip_resolver.lookup(conn.raddr)
        if geo and geo.summary():
            peer_host = f"{peer_host} {geo.summary()}"
    grid.add_row("DNS / GeoIP:", peer_host)

    if conn.is_suspicious:
        grid.add_row("Security Alert:", f"[bold red]⚠ {conn.anomaly_reason}[/bold red]")

    return Panel(
        grid,
        title=f"[bold bright_white on blue] 🔍 Process Inspector: {proc_info.get('name', conn.process_name)} (PID {proc_info.get('pid', conn.pid)}) [/bold bright_white on blue]",
        subtitle="[dim white]Press [Enter] or [Esc] to close | [k] to terminate process[/dim white]",
        box=box.ROUNDED,
        border_style="bright_cyan",
        padding=(1, 2)
    )

def get_filtered_connections(
    connections: List[ConnectionInfo],
    filter_query: Optional[str] = None,
    sort_by: str = "default"
) -> List[ConnectionInfo]:
    filtered = list(connections)
    if filter_query:
        q = filter_query.lower()
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

    return filtered

def create_connections_table(
    connections: List[ConnectionInfo],
    resolver: AsyncDNSResolver,
    max_rows: int = 25,
    filter_process: Optional[str] = None,
    filter_query: Optional[str] = None,
    sort_by: str = "default",
    geoip_resolver: Optional[AsyncGeoIPResolver] = None,
    selected_index: Optional[int] = None
) -> Table:
    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold bright_white on grey23",
        expand=True,
        row_styles=["none", "dim"],
    )

    table.add_column("PID", justify="right", style="cyan", no_wrap=True, width=8)
    table.add_column("Process", style="bold white", width=16)
    table.add_column("Proto", justify="center", style="yellow", width=6)
    table.add_column("Local Endpoint", style="green", width=25)
    table.add_column("Remote Endpoint", style="bright_blue", width=25)
    table.add_column("Peer / Geo", style="italic bright_white", width=26)
    table.add_column("State", justify="center", width=14)
    table.add_column("Status / Alert", style="bold red")

    active_search = filter_query or filter_process
    filtered = get_filtered_connections(connections, filter_query=active_search, sort_by=sort_by)

    for idx, conn in enumerate(filtered[:max_rows]):
        is_selected = (selected_index is not None and idx == selected_index)
        pid_base = str(conn.pid) if conn.pid else "-"
        pid_str = f"▶ {pid_base}" if is_selected else pid_base
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

        row_style = "bold bright_white on blue" if is_selected else None

        table.add_row(
            pid_str,
            proc_disp,
            conn.proto,
            l_endpoint,
            r_endpoint,
            peer_host,
            state_text,
            alert_text,
            style=row_style,
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
    search_buffer: str = "",
    selected_index: int = 0,
    inspecting_conn: Optional[ConnectionInfo] = None,
    inspect_data: Optional[Dict[str, Any]] = None,
    confirm_kill: Optional[Tuple[int, str]] = None,
    status_msg: str = "",
) -> Layout:
    active_filter = search_buffer if is_searching else filter_process
    layout = Layout()
    header_panel = create_header_panel(snapshot, is_paused=is_paused)
    footer_panel = create_footer_panel(
        sort_mode=sort_by,
        is_paused=is_paused,
        search_query=active_filter,
        is_searching=is_searching,
        confirm_kill=confirm_kill,
        status_msg=status_msg,
    )

    if inspecting_conn and inspect_data:
        center_view = create_inspect_modal(inspecting_conn, inspect_data, resolver, geoip_resolver=geoip_resolver)
    else:
        center_view = create_connections_table(
            snapshot.connections,
            resolver,
            max_rows=max_rows,
            filter_query=active_filter,
            sort_by=sort_by,
            geoip_resolver=geoip_resolver,
            selected_index=selected_index if not is_searching else None
        )

    layout.split_column(
        Layout(header_panel, size=3),
        Layout(center_view),
        Layout(footer_panel, size=3)
    )
    return layout
