complete -c netlog -s i -l interval -d "Sampling interval in seconds" -x
complete -c netlog -s p -l process -d "Filter by process name" -x -a "(__fish_complete_proc)"
complete -c netlog -s c -l config -d "Path to custom config.toml" -r
complete -c netlog -s n -l rows -d "Maximum table rows" -x
complete -c netlog -l once -d "Capture single snapshot and exit"
complete -c netlog -l export-csv -d "Export snapshot to CSV" -r
complete -c netlog -l export-json -d "Stream snapshots as JSON lines" -r
complete -c netlog -l prometheus-port -d "Expose Prometheus /metrics endpoint on port" -x
complete -c netlog -l headless -d "Run as background daemon without TUI"
complete -c netlog -s v -l version -d "Show version"
complete -c netlog -s h -l help -d "Show help"
