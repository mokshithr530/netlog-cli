import pytest
from pathlib import Path
from netlog.core.config import load_config, parse_simple_toml, DEFAULT_CONFIG

def test_default_config_fallback(tmp_path):
    missing_file = tmp_path / "nonexistent.toml"
    cfg = load_config(missing_file)
    assert cfg["interval"] == 1.0
    assert cfg["rows"] is None
    assert cfg["sort_by"] == "default"

def test_parse_simple_toml():
    content = """
    # Comments
    interval = 2.5
    rows = 30
    process = "brave"
    enabled = true
    """
    res = parse_simple_toml(content)
    assert res["interval"] == 2.5
    assert res["rows"] == 30
    assert res["process"] == "brave"
    assert res["enabled"] is True

def test_load_valid_toml_file(tmp_path):
    conf_file = tmp_path / "config.toml"
    conf_file.write_text("""
[general]
interval = 0.5
rows = 40
sort_by = "pid"

[filter]
process = "curl"
""", encoding="utf-8")

    cfg = load_config(conf_file)
    assert cfg["interval"] == 0.5
    assert cfg["rows"] == 40
    assert cfg["sort_by"] == "pid"
    assert cfg["process"] == "curl"
