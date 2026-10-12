# Browser Workspace

The AetherOS Browser Workspace provides a complete web browsing environment inside the desktop application. It supports tabs, bookmarks, history, downloads, AI page analysis, web automation, and secure browsing with privacy controls.

## Architecture

```
aetheros_automation/browser_automation/
├── __init__.py                  # Package exports
├── browser_facade.py            # Main facade coordinating all subsystems
├── tab_manager.py               # Tab lifecycle, groups, pinning
├── bookmark_manager.py          # Bookmark CRUD with persistence
├── history_manager.py           # Browsing history with search
├── download_manager.py          # Download tracking and lifecycle
├── web_search_manager.py        # Multi-provider search management
├── browser_workflow_engine.py   # Visual workflow execution engine
├── ai_browser_assistant.py      # AI-powered page analysis
├── research_mode.py             # Multi-source research with contradiction detection
├── computer_use_manager.py      # Desktop interaction (mouse/keyboard/screen)
├── page_analyzer.py             # Page content extraction and analysis
├── prompt_injection_protection.py # Security scanning for malicious content
└── browser_permissions.py       # Granular browser permission management

apps/desktop/src/store/
├── browser-workspace.ts         # Tab, history, bookmark, download state
├── browser-automation.ts        # Workflow builder state
└── browser-permissions.ts       # Permission and computer use state

apps/desktop/src/app/browser-workspace/
├── index.tsx                    # Main browser workspace component
├── ai-assistant.tsx             # AI browser assistant panel
└── automation-builder.tsx       # Visual workflow builder
```

## Features

### Tab Management
- Open, close, duplicate, pin tabs
- Tab groups for organization
- Split view support
- Private browsing mode
- Tab history with back/forward navigation

### Bookmarks
- Add, edit, delete bookmarks
- Folder organization
- Tags for categorization
- Search and filter
- Import/export via JSON

### History
- Automatic visit tracking
- Search and date filtering
- Most visited pages
- Clear individual entries or all history

### Downloads
- Full lifecycle management (pending → downloading → completed/failed)
- Pause, resume, cancel
- Security scan status tracking
- Active downloads view

### Web Search
- Multiple search providers (Google, Bing, DuckDuckGo, Brave)
- Custom search provider support
- Search suggestions (provider-dependent)
- Search history tracking

### AI Page Analysis
- Page summarization
- Email, link, and price extraction
- Table and article extraction
- Form analysis
- Reading time estimation

### Web Automation
- Visual drag-and-drop workflow builder
- 18 node types covering navigation, interaction, data, flow, and integration
- Variable support with template interpolation
- Scheduling (once, daily, weekly, cron)
- Execution tracking with results

### Research Mode
- Multi-source research sessions
- Finding extraction with confidence scoring
- Contradiction detection across sources
- Auto-generated reports with citations
- Knowledge Hub integration

### Security
- Prompt injection detection (17+ patterns)
- Hidden content scanning
- Script injection detection
- Domain blocklisting
- Sensitive domain detection (banking, email, etc.)
- Granular permission system (18 permission types)
- Risk-level-based approval requirements

### Computer Use
- Screen capture and understanding
- Mouse control (click, move, drag)
- Keyboard input and shortcuts
- Window detection and focus
- All actions require explicit user permission

## Permissions

| Permission | Risk Level | Requires Approval |
|-----------|------------|-------------------|
| read_page | low | No |
| access_domain | low | No |
| navigate | low | No |
| use_cookies | medium | No |
| download_files | medium | No |
| screenshot | medium | No |
| fill_forms | medium | No |
| open_popups | medium | No |
| upload_files | high | Yes |
| submit_forms | high | Yes |
| access_clipboard | high | Yes |
| use_camera | high | Yes |
| use_microphone | high | Yes |
| control_browser | high | Yes |
| execute_js | high | Yes |
| external_communication | high | Yes |
| sensitive_website | critical | Yes |
| control_desktop | critical | Yes |

## Existing Systems Reused

- **Playwright Browser Automation** (`aetheros_automation/browser/`) — underyling browser engine
- **Vision System** (`tools/vision_tools.py`) — page screenshot analysis
- **Web Search Tools** (`tools/web_tools.py`) — search backend integration
- **Permission System** (`aetheros_automation/permissions/`) — permission grants
- **Security System** (`aetheros_automation/security/`) — sandbox and activity monitoring
- **Task Orchestrator** (`aetheros_automation/orchestrator/`) — workflow execution
- **Credential Vault** (`aetheros_automation/security/`) — credential management
- **Knowledge Hub** (`aetheros_automation/knowledge/`) — research report storage
- **Browser Tools** (`tools/browser_tool.py`) — AI agent browser interaction tools
