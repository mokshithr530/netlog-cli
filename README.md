# 🌐 netlog-cli

[![Release](https://img.shields.io/github/v/release/mokshithr530/netlog-cli?color=blue&style=flat-square)](https://github.com/mokshithr530/netlog-cli/releases)
[![CI Test Suite](https://img.shields.io/github/actions/workflow/status/mokshithr530/netlog-cli/ci.yml?branch=main&label=CI&style=flat-square)](https://github.com/mokshithr530/netlog-cli/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg?style=flat-square)](https://www.python.org/)
[![CLI: Rich TUI](https://img.shields.io/badge/Interface-Rich%20TUI-brightgreen.svg?style=flat-square)](https://github.com/Textualize/rich)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)

A high-performance Linux terminal network telemetry dashboard tracking socket lifecycles, per-process bandwidth consumption, asynchronous reverse DNS resolution, GeoIP enrichment, and connection anomaly alerts in real time.

![netlog-cli Live Terminal Dashboard](assets/demo.svg)

---

## ⚡ Overview

`netlog-cli` bridges the gap between low-level socket utilities (`ss`, `lsof`, `netstat`) and high-level process monitors (`htop`, `nethogs`). It aggregates raw system internet sockets (TCP/UDP), maps them back to the generating processes, computes real-time upload/download delta rates, and resolves remote peer hostnames asynchronously without blocking the UI rendering thread.

```text
       ┌────────────────────────┐
       │ Linux Kernel / Sockets │
       └───────────┬────────────┘
                   │ psutil.net_connections()
                   ▼
       ┌────────────────────────┐       ┌───────────────────────┐
       │ SocketMonitor (Core)   ├──────►│ RateCalculator (KB/s)│
       └───────────┬────────────┘       └───────────┬───────────┘
                   │                                │
                   ▼                                ▼
       ┌────────────────────────┐       ┌───────────────────────┐
       │ AsyncDNSResolver       │       │ AnomalyDetector       │
       │ (Thread Pool + LRU)    │       │ (Heuristic Security)  │
       └───────────┬────────────┘       └───────────┬───────────┘
                   │                                │
                   └───────────────┬────────────────┘
                                   ▼
                   ┌────────────────────────────────┐
                   │ Rich Live Terminal Dashboard   │
                   └────────────────────────────────┘
```

---

## 🚀 Features

- **Real-Time Terminal TUI:** Clean, auto-refreshing interface powered by `Rich` with zero screen flickering.
- **Interactive Search & Filter Mode (`/`):** Press `/` to filter connections in real time by process name, remote IP, port, or connection state without restarting.
- **Interactive Hotkey Controls:** Cycle live sort modes (`s` for PID, process name, socket state, protocol), freeze/pause updates (`p` or `Space`), and reset sort (`r`).
- **Live Bandwidth History Sparklines:** Rolling Unicode sparklines (` ▂▄▆██▆▄▂`) tracking system upload and download throughput over time.
- **Process-Level Attribution:** Maps active TCP and UDP sockets to their originating PID, command name, and user.
- **Differential Rate Engine:** Computes rolling delta bandwidth rates (Down / Up KB/s) for both the system and individual processes.
- **Non-Blocking Async Reverse DNS:** Background worker pool resolves remote IP addresses into hostnames with an LRU cache, preventing network lag from stalling the UI.
- **GeoIP & ASN Enrichment:** Automatically tags public remote endpoints with country codes and network autonomous systems.
- **Security & Anomaly Detection:** Flags cleartext legacy protocols (Telnet, FTP, TFTP) and abnormal socket spikes.
- **Exporting Capabilities:** Dump point-in-time snapshots to clean CSV or stream structured JSON lines for SIEM/audit logging.

---

### ⌨️ Interactive Keybindings

| Key | Action | Description |
| :--- | :--- | :--- |
| `q` | **Quit** | Exits `netlog-cli` cleanly and restores terminal state |
| `/` | **Filter / Search** | Type query to filter by process name, port, IP, or state |
| `s` | **Cycle Sort** | Cycles sort modes (`pid` → `process` → `state` → `proto` → `default`) |
| `p` or `Space` | **Pause / Resume** | Freezes live socket polling for manual inspection |
| `r` | **Reset** | Clears active filters and restores default sort order |

---

## 📦 Installation & Deployment

### Local Installation
```bash
git clone https://github.com/mokshithr530/netlog-cli.git
cd netlog-cli
pip install -e .
```

### Run via Docker
To monitor host network sockets from inside Docker, launch with `--net=host`:
```bash
docker build -t netlog-cli .
docker run --rm -it --net=host netlog-cli
```

---

## 🛠️ Usage

### 1. Launch the Live Dashboard
```bash
netlog
```

### 2. Filter by Process Name (e.g., Brave or Python)
```bash
netlog --process brave
```

### 3. Adjust Sampling Interval
```bash
netlog -i 0.5 --rows 30
```

### 4. Single-Shot Snapshot (Scripting & Piping)
```bash
netlog --once
```

### 5. Export Sockets to CSV or JSONL
```bash
netlog --once --export-csv /tmp/network_audit.csv
netlog --export-json /tmp/network_stream.jsonl
```

### 6. Prometheus Metrics Exporter Mode
Run with an embedded HTTP server exposing Prometheus `/metrics` (or headlessly as a daemon):
```bash
# Run with live interactive TUI and background exporter
netlog --prometheus-port 9100

# Run headlessly in the background (ideal for systemd or container agents)
netlog --prometheus-port 9100 --headless
```

---

## ⌨️ Interactive Keyboard Controls

| Key | Action |
| :--- | :--- |
| `↑` / `↓` | Select and highlight connection row |
| `Enter` | Open **Process Inspector Modal** (view cmdline, parent, memory RSS, socket info) |
| `k` | **Terminate process** (prompts confirmation to send `SIGTERM`) |
| `/` | **Live Search & Filter** (matches process name, PID, port, service name, or state) |
| `s` | Cycle sort order (`default` → `pid` → `process` → `state` → `proto`) |
| `p` / `Space` | Pause / resume real-time sampling |
| `r` | Reset filters and sorting back to default |
| `q` / `Ctrl+C` | Cleanly exit dashboard |

---

## 📦 Arch Linux / AUR Packaging

Build and install natively on Arch Linux / Omarchy:
```bash
cd packaging
makepkg -si
```

---

## 🖥️ Sample Output

```text
 🌐 NETLOG-CLI   |  Active Sockets: 42  |  Tracked Processes: 18  |  ▼ Down: 124.5 KB/s  ▲ Up: 18.2 KB/s 

    PID  Process           Proto  Local Endpoint         Remote Endpoint        Peer Hostname             State        Status / Alert 
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── 
   7576  antigravity       TCP    10.0.2.238:36410       172.217.114.4:443      172.217.114.4             ESTABLISHED  OK             
   7653  brave             TCP    10.0.2.238:45212       142.250.190.46:443     google.com                ESTABLISHED  OK             
  25340  wacli             TCP    10.0.2.238:40118       57.144.55.32:443       whatsapp.net              ESTABLISHED  OK             
    738  NetworkManager    UDP    10.0.2.238:68          192.168.3.2:67         lan                       STATELESS    OK             
   1010  Hyprland          TCP    127.0.0.1:37952        *:*                    *:*                       LISTEN       OK             
    999  legacy_service    TCP    192.168.1.10:45000     45.33.32.156:23        insecure-host.net         ESTABLISHED  ⚠ Insecure Telnet
```

---

## 🔒 Permissions & Troubleshooting

`netlog` reads the kernel socket table and maps each socket back to the process that owns it. On a
normal desktop that works without privileges. On hardened Linux distributions, sockets owned by
other system users can be hidden from an unprivileged process, and those sockets appear as
`System / Idle` in the dashboard instead of their real process.

There are two ways to see them:

### Grant the two capabilities (recommended)

`netlog` needs `CAP_NET_ADMIN` (to read the socket table) and `CAP_SYS_PTRACE` (to attribute a
socket to its owning process). Grant them to the Python interpreter instead of running as root:

```bash
sudo setcap cap_net_admin,cap_sys_ptrace=eip "$(which python3)"
```

Then run `netlog` as usual. Capabilities are cleared whenever the interpreter binary is replaced
(for example by a Python upgrade), so re-run the command after upgrading Python.

### Run with sudo

If you prefer not to set capabilities, run the dashboard with `sudo netlog`. This works everywhere
but runs the tool as root; prefer the `setcap` route when you can.

If sockets still show as `System / Idle` after either option, check `kernel.yama.ptrace_scope` on
distributions that restrict ptrace, and make sure you are not inside a container without
`--pid=host` / `--net=host`.

---

## 🧪 Running Unit Tests

```bash
pytest -v
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
- Check existing issues or submit a new [Bug Report or Feature Request](https://github.com/mokshithr530/netlog-cli/issues).
- Please read the [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting a Pull Request.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
