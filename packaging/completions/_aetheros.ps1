$script:AetherOSSubcommands = @(
    'chat', 'gateway', 'setup', 'status', 'cron', 'doctor',
    'update', 'repair', 'reset', 'backup', 'restore', 'model',
    'settings', 'uninstall', 'version', 'config', 'logs', 'sessions',
    'skills', 'plugins', 'mcp', 'tools', 'knowledge', 'plan',
    'think', 'analyze', 'agents', 'learn', 'whatsapp', 'auth',
    'hooks', 'webhook', 'debug', 'dump', 'security', 'profile',
    'insights', 'memory', 'acp', 'enterprise', 'dashboard', 'desktop',
    'hub', 'market', 'migrate', 'secrets', 'bundles', 'checkpoints',
    'fallback', 'pairing', 'sdk', 'claw', 'completion'
)

$script:AetherOSGlobalFlags = @(
    '--help', '--version', '--profile', '-p', '--model', '-m',
    '--provider', '--toolsets', '-t', '--resume', '-r', '--continue',
    '-c', '--quiet', '-Q', '--verbose', '--tui', '--cli', '--yolo',
    '--debug', '--json'
)

$script:AetherOSFlagArgMap = @{
    '--profile'  = 'ProfileName'
    '-p'         = 'ProfileName'
    '--model'    = 'ModelName'
    '-m'         = 'ModelName'
    '--provider' = 'ProviderName'
    '--toolsets' = 'ToolsetList'
    '-t'         = 'ToolsetList'
}

$script:AetherOSSubcommandDescriptions = @{
    'chat'       = 'Interactive conversation with the AI'
    'gateway'    = 'Manage the AetherOS gateway service'
    'setup'      = 'Initial system setup and configuration'
    'status'     = 'Show system status and health'
    'cron'       = 'Manage scheduled cron jobs'
    'doctor'     = 'Run system diagnostics'
    'update'     = 'Update AetherOS components'
    'repair'     = 'Repair corrupted system files'
    'reset'      = 'Reset system settings to defaults'
    'backup'     = 'Create system backups'
    'restore'    = 'Restore from a backup'
    'model'      = 'Manage AI models'
    'settings'   = 'Configure system settings'
    'uninstall'  = 'Uninstall AetherOS'
    'version'    = 'Show version information'
    'config'     = 'Manage configuration files'
    'logs'       = 'View system logs'
    'sessions'   = 'Manage active sessions'
    'skills'     = 'Manage AI skills and capabilities'
    'plugins'    = 'Manage plugins'
    'mcp'        = 'Model Context Protocol operations'
    'tools'      = 'Manage available tools'
    'knowledge'  = 'Manage knowledge base'
    'plan'       = 'Create execution plans'
    'think'      = 'Reason through complex problems'
    'analyze'    = 'Analyze data and patterns'
    'agents'     = 'Manage autonomous agents'
    'learn'      = 'Train the system on new data'
    'whatsapp'   = 'WhatsApp integration'
    'auth'       = 'Manage authentication'
    'hooks'      = 'Manage system hooks'
    'webhook'    = 'Manage webhook endpoints'
    'debug'      = 'Debug system operations'
    'dump'       = 'Export system diagnostics'
    'security'   = 'Security configuration'
    'profile'    = 'Manage profiles'
    'insights'   = 'Generate system insights'
    'memory'     = 'Manage conversational memory'
    'acp'        = 'Agent Communication Protocol'
    'enterprise' = 'Enterprise features'
    'dashboard'  = 'Launch the dashboard'
    'desktop'    = 'Launch desktop client'
    'hub'        = 'Access AetherOS Hub'
    'market'     = 'Browse extensions marketplace'
    'migrate'    = 'Run data migration'
    'secrets'    = 'Manage secrets and keys'
    'bundles'    = 'Manage extension bundles'
    'checkpoints' = 'Manage system checkpoints'
    'fallback'   = 'Configure fallback behavior'
    'pairing'    = 'Device pairing management'
    'sdk'        = 'SDK operations'
    'claw'       = 'CLI Automation Workflow'
    'completion' = 'Generate shell completion scripts'
}

$script:AetherOSFlagDescriptions = @{
    '--help'     = 'Show help information'
    '--version'  = 'Show version'
    '--profile'  = 'Profile to use'
    '-p'         = 'Profile to use'
    '--model'    = 'Model to use'
    '-m'         = 'Model to use'
    '--provider' = 'Provider to use'
    '--toolsets' = 'Toolsets to enable'
    '-t'         = 'Toolsets to enable (deprecated)'
    '--resume'   = 'Resume from last state'
    '-r'         = 'Resume from last state'
    '--continue' = 'Continue previous session'
    '-c'         = 'Continue previous session'
    '--quiet'    = 'Suppress non-essential output'
    '-Q'         = 'Suppress non-essential output'
    '--verbose'  = 'Enable verbose output'
    '--tui'      = 'Launch terminal UI'
    '--cli'      = 'Force CLI mode'
    '--yolo'     = 'Skip safety confirmations'
    '--debug'    = 'Enable debug mode'
    '--json'     = 'Output in JSON format'
}

function Get-AetherOSModelNames {
    $models = @('gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo',
                'claude-sonnet-4', 'claude-haiku-3', 'claude-opus-4',
                'llama-3-8b', 'llama-3-70b', 'mixtral-8x7b',
                'gemini-pro', 'gemini-ultra')

    try {
        $result = & aetheros model list 2>$null
        if ($result) {
            $modelsFromCmd = $result | Select-Object -Skip 1 | ForEach-Object { $_.Trim().Split()[0] }
            if ($modelsFromCmd) { $models = $modelsFromCmd }
        }
    } catch {}

    return $models
}

function Get-AetherOSProfileNames {
    $profiles = @('default', 'custom')
    $profDir = "$env:USERPROFILE\.aetheros\profiles"
    if (Test-Path -LiteralPath $profDir) {
        $found = Get-ChildItem -LiteralPath $profDir -Filter '*.json' -Name `
            | ForEach-Object { [System.IO.Path]::GetFileNameWithoutExtension($_) }
        if ($found) { $profiles += $found }
    }
    return $profiles | Sort-Object -Unique
}

function Expand-AetherOSCompletion {
    param(
        [string]$commandName,
        [string]$wordToComplete,
        [System.Management.Automation.CommandAst]$commandAst,
        [int]$cursorPosition
    )

    $result = @()

    $rawLine = $commandAst.Extent.Text
    $tokens = @()
    $parseErrors = $null
    [System.Management.Automation.PSParser]::Tokenize($rawLine, [ref]$tokens, [ref]$parseErrors) | Out-Null

    $currentTokenIndex = -1
    for ($i = 0; $i -lt $tokens.Count; $i++) {
        if ($tokens[$i].Start -le $cursorPosition -and $tokens[$i].End -ge $cursorPosition) {
            $currentTokenIndex = $i
            break
        }
    }

    $words = @()
    $hasColon = $false
    for ($i = 0; $i -lt $tokens.Count; $i++) {
        $text = $tokens[$i].Content
        if ($tokens[$i].Type -eq 'Command' -or $tokens[$i].Type -eq 'CommandParameter' -or
            ($tokens[$i].Type -eq 'String' -and $text -notmatch '^[''"\s]')) {
            if ($text -ne $commandName) {
                $words += $text
            }
        } elseif ($tokens[$i].Type -eq 'String' -and $text -match '^[''"](.+?)[''"]$') {
            if ($text -ne $commandName) {
                $words += $matches[1]
            }
        }
    }

    $wordToCompleteNorm = $wordToComplete.TrimStart("'").TrimStart('"')
    $isFlagValue = $false
    $lastFlagArg = $null

    if ($words.Count -gt 0) {
        $lastWord = $words[-1]
        $secondLastWord = if ($words.Count -gt 1) { $words[-2] } else { $null }

        if ($script:AetherOSFlagArgMap.ContainsKey($lastWord)) {
            $isFlagValue = $true
            $lastFlagArg = $lastWord
        } elseif ($secondLastWord -and $script:AetherOSFlagArgMap.ContainsKey($secondLastWord)) {
            $isFlagValue = $true
            $lastFlagArg = $secondLastWord
        }
    }

    $subcommandIndex = -1
    for ($i = 0; $i -lt $words.Count; $i++) {
        if ($words[$i] -notin $script:AetherOSGlobalFlags -and
            $words[$i] -notmatch '^--?\w' -and
            $words[$i] -notin $script:AetherOSFlagArgMap.Keys) {
            $subcommandIndex = $i
            break
        }
    }

    if ($isFlagValue) {
        switch ($lastFlagArg) {
            '--profile' { $result = Get-AetherOSProfileNames }
            '-p'        { $result = Get-AetherOSProfileNames }
            '--model'   { $result = Get-AetherOSModelNames }
            '-m'        { $result = Get-AetherOSModelNames }
            '--provider' { $result = @('openai', 'anthropic', 'ollama', 'together', 'groq', 'openrouter') }
        }
        return $result | Where-Object { $_ -like "$wordToCompleteNorm*" } | ForEach-Object {
            $desc = switch ($lastFlagArg) {
                '--profile' { "Profile" }
                '-p'        { "Profile" }
                '--model'   { "Model" }
                '-m'        { "Model" }
                '--provider' { "Provider" }
            }
            New-Object System.Management.Automation.CompletionResult (
                $_,
                $_,
                'ParameterValue',
                "$desc: $_"
            )
        }
    }

    if ($subcommandIndex -eq -1 -or $wordToComplete -eq '') {
        foreach ($sub in $script:AetherOSSubcommands) {
            if ($sub -like "$wordToCompleteNorm*") {
                $desc = if ($script:AetherOSSubcommandDescriptions.ContainsKey($sub)) {
                    $script:AetherOSSubcommandDescriptions[$sub]
                } else { "AetherOS $sub command" }
                $result += New-Object System.Management.Automation.CompletionResult (
                    $sub,
                    $sub,
                    'ParameterValue',
                    $desc
                )
            }
        }
    }

    if ($subcommandIndex -ge 0) {
        foreach ($flag in $script:AetherOSGlobalFlags) {
            if ($flag -like "$wordToCompleteNorm*") {
                $alreadyPresent = $false
                foreach ($w in $words) {
                    if ($w -eq $flag) { $alreadyPresent = $true; break }
                }
                if (-not $alreadyPresent) {
                    $desc = if ($script:AetherOSFlagDescriptions.ContainsKey($flag)) {
                        $script:AetherOSFlagDescriptions[$flag]
                    } else { "Global flag" }
                    $result += New-Object System.Management.Automation.CompletionResult (
                        $flag,
                        $flag,
                        'Parameter',
                        $desc
                    )
                }
            }
        }
    }

    $result | Sort-Object -Property CompletionText -Unique
}

$script:OriginalTabExpansion2 = $global:TabExpansion2

$global:TabExpansion2 = {
    param(
        [System.Management.Automation.CommandAst]$commandAst,
        [int]$cursorPosition
    )

    $commandName = $commandAst.GetCommandName()

    if ($commandName -eq 'aetheros' -or $commandName -eq 'AetherOS') {
        $wordToComplete = ''
        if ($commandAst.CommandElements) {
            $lastElementIndex = $commandAst.CommandElements.Count - 1
            $lastExtent = $commandAst.CommandElements[$lastElementIndex].Extent
            if ($cursorPosition -ge $lastExtent.StartColumn -and $cursorPosition -le $lastExtent.EndColumn) {
                $wordToComplete = $lastExtent.Text
            }
        }

        $result = Expand-AetherOSCompletion -commandName $commandName -wordToComplete $wordToComplete -commandAst $commandAst -cursorPosition $cursorPosition
        return $result
    }

    if ($script:OriginalTabExpansion2) {
        return & $script:OriginalTabExpansion2 $commandAst $cursorPosition
    }
}
