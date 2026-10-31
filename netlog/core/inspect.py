import os
import signal
import time
from typing import Optional, Dict, Any, Tuple
import psutil

def inspect_process(pid: Optional[int]) -> Dict[str, Any]:
    """
    Safely retrieves comprehensive system information for a target process.
    Handles terminated, zombie, and access-restricted processes gracefully.
    """
    if pid is None or pid <= 0:
        return {
            "pid": pid,
            "name": "System / Kernel",
            "cmdline": "[kernel thread or system idle]",
            "user": "root",
            "status": "system",
            "memory_rss": "0 MB",
            "memory_vms": "0 MB",
            "cpu_percent": "0.0%",
            "created": "-",
            "cwd": "-",
            "parent": "-"
        }

    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            name = proc.name()
            try:
                cmdline = " ".join(proc.cmdline()) or name
            except Exception:
                cmdline = name

            try:
                username = proc.username()
            except Exception:
                username = "unknown"

            try:
                status = proc.status()
            except Exception:
                status = "unknown"

            try:
                mem = proc.memory_info()
                rss_mb = f"{mem.rss / (1024 * 1024):.1f} MB"
                vms_mb = f"{mem.vms / (1024 * 1024):.1f} MB"
            except Exception:
                rss_mb, vms_mb = "N/A", "N/A"

            try:
                cpu = f"{proc.cpu_percent():.1f}%"
            except Exception:
                cpu = "N/A"

            try:
                created_t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(proc.create_time()))
            except Exception:
                created_t = "N/A"

            try:
                cwd = proc.cwd()
            except Exception:
                cwd = "N/A"

            try:
                parent = proc.parent()
                parent_str = f"{parent.name()} (PID {parent.pid})" if parent else "None"
            except Exception:
                parent_str = "N/A"

            return {
                "pid": pid,
                "name": name,
                "cmdline": cmdline,
                "user": username,
                "status": status,
                "memory_rss": rss_mb,
                "memory_vms": vms_mb,
                "cpu_percent": cpu,
                "created": created_t,
                "cwd": cwd,
                "parent": parent_str
            }
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return {
            "pid": pid,
            "name": "Terminated",
            "cmdline": "[Process has exited]",
            "user": "unknown",
            "status": "terminated",
            "memory_rss": "0 MB",
            "memory_vms": "0 MB",
            "cpu_percent": "0.0%",
            "created": "-",
            "cwd": "-",
            "parent": "-"
        }
    except psutil.AccessDenied:
        return {
            "pid": pid,
            "name": f"PID {pid} (Restricted)",
            "cmdline": "[Permission denied: Run with sudo/root to inspect]",
            "user": "root/other",
            "status": "restricted",
            "memory_rss": "N/A",
            "memory_vms": "N/A",
            "cpu_percent": "N/A",
            "created": "-",
            "cwd": "-",
            "parent": "-"
        }

def kill_process(pid: int, sig: int = signal.SIGTERM) -> Tuple[bool, str]:
    """
    Sends a signal to terminate a process by PID.
    """
    if pid <= 0:
        return False, "Cannot terminate system or root PID 0"

    try:
        os.kill(pid, sig)
        sig_name = "SIGTERM" if sig == signal.SIGTERM else "SIGKILL"
        return True, f"Sent {sig_name} to PID {pid}"
    except ProcessLookupError:
        return False, f"PID {pid} no longer exists"
    except PermissionError:
        return False, f"Permission denied killing PID {pid} (run with sudo)"
    except Exception as e:
        return False, f"Error killing PID {pid}: {e}"
