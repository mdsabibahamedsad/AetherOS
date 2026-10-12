function __fish_aetheros_subcommands
    printf "%s\t%s\n" chat "Interactive conversation with the AI"
    printf "%s\t%s\n" gateway "Manage the AetherOS gateway service"
    printf "%s\t%s\n" setup "Initial system setup and configuration"
    printf "%s\t%s\n" status "Show system status and health"
    printf "%s\t%s\n" cron "Manage scheduled cron jobs"
    printf "%s\t%s\n" doctor "Run system diagnostics"
    printf "%s\t%s\n" update "Update AetherOS components"
    printf "%s\t%s\n" repair "Repair corrupted system files"
    printf "%s\t%s\n" reset "Reset system settings to defaults"
    printf "%s\t%s\n" backup "Create system backups"
    printf "%s\t%s\n" restore "Restore from a backup"
    printf "%s\t%s\n" model "Manage AI models"
    printf "%s\t%s\n" settings "Configure system settings"
    printf "%s\t%s\n" uninstall "Uninstall AetherOS"
    printf "%s\t%s\n" version "Show version information"
    printf "%s\t%s\n" config "Manage configuration files"
    printf "%s\t%s\n" logs "View system logs"
    printf "%s\t%s\n" sessions "Manage active sessions"
    printf "%s\t%s\n" skills "Manage AI skills and capabilities"
    printf "%s\t%s\n" plugins "Manage plugins"
    printf "%s\t%s\n" mcp "Model Context Protocol operations"
    printf "%s\t%s\n" tools "Manage available tools"
    printf "%s\t%s\n" knowledge "Manage knowledge base"
    printf "%s\t%s\n" plan "Create execution plans"
    printf "%s\t%s\n" think "Reason through complex problems"
    printf "%s\t%s\n" analyze "Analyze data and patterns"
    printf "%s\t%s\n" agents "Manage autonomous agents"
    printf "%s\t%s\n" learn "Train the system on new data"
    printf "%s\t%s\n" whatsapp "WhatsApp integration"
    printf "%s\t%s\n" auth "Manage authentication"
    printf "%s\t%s\n" hooks "Manage system hooks"
    printf "%s\t%s\n" webhook "Manage webhook endpoints"
    printf "%s\t%s\n" debug "Debug system operations"
    printf "%s\t%s\n" dump "Export system diagnostics"
    printf "%s\t%s\n" security "Security configuration"
    printf "%s\t%s\n" profile "Manage profiles"
    printf "%s\t%s\n" insights "Generate system insights"
    printf "%s\t%s\n" memory "Manage conversational memory"
    printf "%s\t%s\n" acp "Agent Communication Protocol"
    printf "%s\t%s\n" enterprise "Enterprise features"
    printf "%s\t%s\n" dashboard "Launch the dashboard"
    printf "%s\t%s\n" desktop "Launch desktop client"
    printf "%s\t%s\n" hub "Access AetherOS Hub"
    printf "%s\t%s\n" market "Browse extensions marketplace"
    printf "%s\t%s\n" migrate "Run data migration"
    printf "%s\t%s\n" secrets "Manage secrets and keys"
    printf "%s\t%s\n" bundles "Manage extension bundles"
    printf "%s\t%s\n" checkpoints "Manage system checkpoints"
    printf "%s\t%s\n" fallback "Configure fallback behavior"
    printf "%s\t%s\n" pairing "Device pairing management"
    printf "%s\t%s\n" sdk "SDK operations"
    printf "%s\t%s\n" claw "CLI Automation Workflow"
    printf "%s\t%s\n" completion "Generate shell completion scripts"
end

function __fish_aetheros_global_flags
    printf "%s\t%s\n" --help "Show help information"
    printf "%s\t%s\n" --version "Show version"
    printf "%s\t%s\n" --profile "Profile to use"
    printf "%s\t%s\n" -p "Profile to use"
    printf "%s\t%s\n" --model "Model to use"
    printf "%s\t%s\n" -m "Model to use"
    printf "%s\t%s\n" --provider "Provider to use"
    printf "%s\t%s\n" --toolsets "Toolsets to enable"
    printf "%s\t%s\n" -t "Toolsets to enable"
    printf "%s\t%s\n" --resume "Resume from last state"
    printf "%s\t%s\n" -r "Resume from last state"
    printf "%s\t%s\n" --continue "Continue previous session"
    printf "%s\t%s\n" -c "Continue previous session"
    printf "%s\t%s\n" --quiet "Suppress non-essential output"
    printf "%s\t%s\n" -Q "Suppress non-essential output"
    printf "%s\t%s\n" --verbose "Enable verbose output"
    printf "%s\t%s\n" --tui "Launch terminal UI"
    printf "%s\t%s\n" --cli "Force CLI mode"
    printf "%s\t%s\n" --yolo "Skip safety confirmations"
    printf "%s\t%s\n" --debug "Enable debug mode"
    printf "%s\t%s\n" --json "Output in JSON format"
end

# Top-level subcommands
complete -c aetheros -n "__fish_use_subcommand" -f -a "(__fish_aetheros_subcommands)"
complete -c AetherOS -n "__fish_use_subcommand" -f -a "(__fish_aetheros_subcommands)"

# Global flags at any position
for cmd in aetheros AetherOS
    complete -c $cmd -n "not __fish_use_subcommand" -f -l help -d "Show help information"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l version -d "Show version"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l profile -r -d "Profile to use"
    complete -c $cmd -n "not __fish_use_subcommand" -f -s p -r -d "Profile to use"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l model -r -d "Model to use"
    complete -c $cmd -n "not __fish_use_subcommand" -f -s m -r -d "Model to use"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l provider -r -d "Provider to use"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l toolsets -r -d "Toolsets to enable"
    complete -c $cmd -n "not __fish_use_subcommand" -f -s t -r -d "Toolsets to enable (deprecated)"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l resume -d "Resume from last state"
    complete -c $cmd -n "not __fish_use_subcommand" -f -s r -d "Resume from last state"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l continue -d "Continue previous session"
    complete -c $cmd -n "not __fish_use_subcommand" -f -s c -d "Continue previous session"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l quiet -d "Suppress non-essential output"
    complete -c $cmd -n "not __fish_use_subcommand" -f -s Q -d "Suppress non-essential output"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l verbose -d "Enable verbose output"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l tui -d "Launch terminal UI"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l cli -d "Force CLI mode"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l yolo -d "Skip safety confirmations"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l debug -d "Enable debug mode"
    complete -c $cmd -n "not __fish_use_subcommand" -f -l json -d "Output in JSON format"
end

# Subcommand-specific completions
for cmd in aetheros AetherOS
    # Subcommands that accept models
    for sub in chat model
        complete -c $cmd -n "__fish_seen_subcommand_from $sub" -f -l model -r -d "Model to use"
        complete -c $cmd -n "__fish_seen_subcommand_from $sub" -f -s m -r -d "Model to use"
        complete -c $cmd -n "__fish_seen_subcommand_from $sub" -f -l provider -r -d "Provider to use"
    end

    # Subcommands that accept profiles
    for sub in chat setup profile
        complete -c $cmd -n "__fish_seen_subcommand_from $sub" -f -l profile -r -d "Profile to use"
        complete -c $cmd -n "__fish_seen_subcommand_from $sub" -f -s p -r -d "Profile to use"
    end

    # Subcommands that accept toolsets
    for sub in chat tools toolsets
        complete -c $cmd -n "__fish_seen_subcommand_from $sub" -f -l toolsets -r -d "Toolsets to enable"
        complete -c $cmd -n "__fish_seen_subcommand_from $sub" -f -s t -r -d "Toolsets to enable"
    end
end
