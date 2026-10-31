import os
import signal
import pytest
from unittest.mock import patch, MagicMock
from netlog.core.inspect import inspect_process, kill_process

def test_inspect_system_pid():
    info = inspect_process(0)
    assert info["pid"] == 0
    assert info["user"] == "root"
    assert info["status"] == "system"

    info_none = inspect_process(None)
    assert info_none["pid"] is None

def test_inspect_current_process():
    pid = os.getpid()
    info = inspect_process(pid)
    assert info["pid"] == pid
    assert "memory_rss" in info
    assert "cpu_percent" in info

def test_kill_process_system_pid():
    ok, msg = kill_process(0)
    assert not ok
    assert "Cannot terminate" in msg

@patch("os.kill")
def test_kill_process_success(mock_kill):
    mock_kill.return_value = None
    ok, msg = kill_process(99999, signal.SIGTERM)
    assert ok
    assert "Sent SIGTERM to PID 99999" in msg
    mock_kill.assert_called_once_with(99999, signal.SIGTERM)

@patch("os.kill", side_effect=PermissionError())
def test_kill_process_permission_denied(mock_kill):
    ok, msg = kill_process(1234, signal.SIGTERM)
    assert not ok
    assert "Permission denied" in msg
