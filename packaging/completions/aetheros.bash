_aetheros_completion() {
    local cur prev words cword
    _init_completion -n := || return

    local subcommands="chat gateway setup status cron doctor update repair reset backup restore model settings uninstall version config logs sessions skills plugins mcp tools knowledge plan think analyze agents learn whatsapp auth hooks webhook debug dump security profile insights memory acp enterprise dashboard desktop hub market migrate secrets bundles checkpoints fallback pairing sdk claw completion"

    local global_flags="--help --version --profile -p --model -m --provider --toolsets -t --resume -r --continue -c --quiet -Q --verbose --tui --cli --yolo --debug --json"

    local connect_subcmds="chat gateway mcp tools"
    local system_subcmds="setup status cron doctor update repair reset"
    local data_subcmds="backup restore model settings config logs sessions"
    local extensions_subcmds="skills plugins hooks webhook"
    local advanced_subcmds="debug dump security profile insights memory acp enterprise"
    local ui_subcmds="dashboard desktop hub market"
    local admin_subcmds="migrate secrets bundles checkpoints fallback pairing sdk claw completion"
    local agent_subcmds="agents learn"
    local messaging_subcmds="whatsapp auth"
    local thinking_subcmds="plan think analyze"
    local other_subcmds="version uninstall"

    if [[ $cword -eq 1 ]]; then
        if [[ $cur == -* ]]; then
            COMPREPLY=($(compgen -W "$global_flags" -- "$cur"))
        else
            COMPREPLY=($(compgen -W "$subcommands" -- "$cur"))
        fi
        return
    fi

    local subcommand="${words[1]}"

    case "$subcommand" in
        chat|gateway|setup|status|update|repair|reset|restore|model|config|logs|sessions|skills|plugins|mcp|tools|knowledge|plan|think|analyze|agents|learn|whatsapp|auth|hooks|webhook|debug|dump|security|profile|insights|memory|acp|enterprise|dashboard|desktop|hub|market|migrate|secrets|bundles|checkpoints|fallback|pairing|sdk|claw|completion)
            COMPREPLY=($(compgen -W "$global_flags" -- "$cur"))
            ;;
        cron|doctor|backup|settings|uninstall|version)
            COMPREPLY=($(compgen -W "$global_flags" -- "$cur"))
            ;;
        *)
            COMPREPLY=($(compgen -W "$global_flags" -- "$cur"))
            ;;
    esac

    return 0
} &&
complete -F _aetheros_completion aetheros &&
complete -F _aetheros_completion AetherOS
