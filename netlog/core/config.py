import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

DEFAULT_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "netlog"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.toml"

DEFAULT_CONFIG: Dict[str, Any] = {
    "interval": 1.0,
    "rows": None,
    "sort_by": "default",
    "process": None,
    "prometheus_port": None,
    "ignored_processes": [],
}

def parse_simple_toml(content: str) -> Dict[str, Any]:
    """Lightweight fallback parser for basic key-value config lines."""
    result: Dict[str, Any] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if v.isdigit():
                result[k] = int(v)
            elif v.lower() == "true":
                result[k] = True
            elif v.lower() == "false":
                result[k] = False
            else:
                try:
                    result[k] = float(v)
                except ValueError:
                    result[k] = v
    return result

def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Loads configuration from ~/.config/netlog/config.toml if present,
    merging onto built-in defaults.
    """
    path = config_path or DEFAULT_CONFIG_FILE
    config = dict(DEFAULT_CONFIG)

    if not path.is_file():
        return config

    try:
        content = path.read_text(encoding="utf-8")
        raw_data = {}
        if tomllib:
            raw_data = tomllib.loads(content)
        else:
            raw_data = parse_simple_toml(content)

        # Flatten nested sections (e.g. [general], [filter])
        for key, val in raw_data.items():
            if isinstance(val, dict):
                for sub_k, sub_v in val.items():
                    config[sub_k] = sub_v
            else:
                config[key] = val
    except Exception:
        # Fallback to defaults on parse error
        pass

    return config
