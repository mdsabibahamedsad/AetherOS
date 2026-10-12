#compdef aetheros AetherOS

typeset -A opt_args
local context state state_descr line

_aetheros() {
    local -a subcommands
    subcommands=(
        'chat:Interactive conversation with the AI'
        'gateway:Manage the AetherOS gateway service'
        'setup:Initial system setup and configuration'
        'status:Show system status and health'
        'cron:Manage scheduled cron jobs'
        'doctor:Run system diagnostics'
        'update:Update AetherOS components'
        'repair:Repair corrupted system files'
        'reset:Reset system settings to defaults'
        'backup:Create system backups'
        'restore:Restore from a backup'
        'model:Manage AI models'
        'settings:Configure system settings'
        'uninstall:Uninstall AetherOS'
        'version:Show version information'
        'config:Manage configuration files'
        'logs:View system logs'
        'sessions:Manage active sessions'
        'skills:Manage AI skills and capabilities'
        'plugins:Manage plugins'
        'mcp:Model Context Protocol operations'
        'tools:Manage available tools'
        'knowledge:Manage knowledge base'
        'plan:Create execution plans'
        'think:Reason through complex problems'
        'analyze:Analyze data and patterns'
        'agents:Manage autonomous agents'
        'learn:Train the system on new data'
        'whatsapp:WhatsApp integration'
        'auth:Manage authentication'
        'hooks:Manage system hooks'
        'webhook:Manage webhook endpoints'
        'debug:Debug system operations'
        'dump:Export system diagnostics'
        'security:Security configuration'
        'profile:Manage profiles'
        'insights:Generate system insights'
        'memory:Manage conversational memory'
        'acp:Agent Communication Protocol'
        'enterprise:Enterprise features'
        'dashboard:Launch the dashboard'
        'desktop:Launch desktop client'
        'hub:Access AetherOS Hub'
        'market:Browse extensions marketplace'
        'migrate:Run data migration'
        'secrets:Manage secrets and keys'
        'bundles:Manage extension bundles'
        'checkpoints:Manage system checkpoints'
        'fallback:Configure fallback behavior'
        'pairing:Device pairing management'
        'sdk:SDK operations'
        'claw:CLI Automation Workflow'
        'completion:Generate shell completion scripts'
    )

    local -a global_flags
    global_flags=(
        '--help[Show help information]'
        '--version[Show version]'
        '--profile[Profile to use]:profile:_aetheros_profiles'
        '-p[Profile to use]:profile:_aetheros_profiles'
        '--model[Model to use]:model:_aetheros_models'
        '-m[Model to use]:model:_aetheros_models'
        '--provider[Provider to use]:provider:_aetheros_providers'
        '--toolsets[Toolsets to enable]:toolsets:'
        '-t[Toolsets to enable]:toolsets:'
        '--resume[Resume from last state]'
        '-r[Resume from last state]'
        '--continue[Continue previous session]'
        '-c[Continue previous session]'
        '--quiet[Suppress non-essential output]'
        '-Q[Suppress non-essential output]'
        '--verbose[Enable verbose output]'
        '--tui[Launch terminal UI]'
        '--cli[Force CLI mode]'
        '--yolo[Skip safety confirmations]'
        '--debug[Enable debug mode]'
        '--json[Output in JSON format]'
    )

    _arguments -C \
        "$global_flags[@]" \
        "1: :{_describe 'subcommand' subcommands}" \
        "*::arg:->args"
}

_aetheros_profiles() {
    _alternative "profiles:profile:(default custom $(command ls ~/.aetheros/profiles/ 2>/dev/null | sed 's/\.json//g'))"
}

_aetheros_models() {
    _alternative "models:model:($(command aetheros model list 2>/dev/null | tail -n +2 || echo 'gpt-4o gpt-4o-mini llama3 claude-sonnet claude-haiku'))"
}

_aetheros_providers() {
    _alternative "providers:provider:(openai anthropic ollama together groq openrouter)"
}

_aetheros "$@"
