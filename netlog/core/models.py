from dataclasses import dataclass, field
from typing import Optional, List, Dict
import time
from netlog.core.services import get_service_name

@dataclass
class ConnectionInfo:
    fd: int
    family: str
    proto: str
    laddr: str
    lport: int
    raddr: Optional[str]
    rport: Optional[int]
    status: str
    pid: Optional[int]
    process_name: str
    user: str
    hostname: Optional[str] = None
    country: Optional[str] = None
    org: Optional[str] = None
    is_suspicious: bool = False
    anomaly_reason: str = ""

    @property
    def local_endpoint(self) -> str:
        return f"{self.laddr}:{self.lport}"

    @property
    def remote_endpoint(self) -> str:
        if not self.raddr:
            return "*:*"
        return f"{self.raddr}:{self.rport}"

    @property
    def local_service(self) -> Optional[str]:
        return get_service_name(self.lport, self.proto)

    @property
    def remote_service(self) -> Optional[str]:
        return get_service_name(self.rport, self.proto) if self.rport else None

@dataclass
class ProcessNetworkStats:
    pid: int
    name: str
    user: str
    connections_count: int
    established_count: int
    listen_count: int
    connections: List[ConnectionInfo] = field(default_factory=list)
    bytes_sent: int = 0
    bytes_recv: int = 0
    upload_rate: float = 0.0    # KB/s
    download_rate: float = 0.0  # KB/s
    last_sample_time: float = field(default_factory=time.time)

@dataclass
class NetworkSnapshot:
    timestamp: float
    total_connections: int
    active_processes_count: int
    system_bytes_sent: int
    system_bytes_recv: int
    system_upload_rate: float
    system_download_rate: float
    connections: List[ConnectionInfo]
    processes: Dict[int, ProcessNetworkStats]
    download_sparkline: str = ""
    upload_sparkline: str = ""
