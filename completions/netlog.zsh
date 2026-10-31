#compdef netlog

_netlog() {
    local -a options
    options=(
        '(-i --interval)'{-i,--interval}'[Sampling interval in seconds]:seconds'
        '(-p --process)'{-p,--process}'[Filter by process name]:process:_processes'
        '(-c --config)'{-c,--config}'[Custom configuration file]:config file:_files'
        '(-n --rows)'{-n,--rows}'[Maximum table rows]:rows'
        '--once[Capture single snapshot and exit]'
        '--export-csv[Export snapshot to CSV]:file:_files'
        '--export-json[Stream snapshots as JSON lines]:file:_files'
        '--prometheus-port[Expose Prometheus /metrics endpoint]:port'
        '--headless[Run as background daemon without TUI]'
        '(-v --version)'{-v,--version}'[Show version]'
        '(-h --help)'{-h,--help}'[Show help]'
    )
    _arguments -s $options
}

_netlog "$@"
