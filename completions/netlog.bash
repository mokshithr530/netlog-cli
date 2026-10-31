_netlog_completions() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="-i --interval -p --process -c --config -n --rows --once --export-csv --export-json --prometheus-port --headless -v --version -h --help"

    case "${prev}" in
        -c|--config|--export-csv|--export-json)
            COMPREPLY=( $(compgen -f -- "${cur}") )
            return 0
            ;;
        -p|--process)
            local procs
            procs=$(ps -e -o comm= 2>/dev/null | sort -u)
            COMPREPLY=( $(compgen -W "${procs}" -- "${cur}") )
            return 0
            ;;
        -i|--interval|-n|--rows|--prometheus-port)
            return 0
            ;;
    esac

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
        return 0
    fi
}
complete -F _netlog_completions netlog
