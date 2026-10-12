# Setup Wizard — Step Reference

## Steps

### 1. Welcome
- Animated welcome screen
- AetherOS version + system info
- License + privacy notice
- Continue button

### 2. Profile
- Display name (required)
- Workspace name (required)
- Preferred language
- Region
- Timezone
- Accessibility options

### 3. Theme
- Light / Dark / System / High Contrast
- Live preview before applying

### 4. AI Provider
- Choose one or more providers:
  - OpenAI, Anthropic, Google Gemini, OpenRouter
  - Ollama, LM Studio, llama.cpp
  - OpenAI Compatible, Azure OpenAI
  - Custom Provider
- Multiple providers supported simultaneously

### 5. Model Selection
- Load available models per provider
- Assign models to roles: Default, Reasoning, Coding, Vision, Fast, Cheap, Offline

### 6. Local AI
- Auto-detect Ollama, LM Studio installations
- Configure endpoint URL
- Install option if missing

### 7. API Configuration
- API keys (encrypted via AES-256-GCM)
- Base URLs
- Organization IDs
- Azure deployment settings
- Proxy, timeout, retry

### 8. Connect Services
- GitHub, Google, Gmail, Telegram, Discord, Slack
- WhatsApp Business, Microsoft, Notion, Linear, Jira, GitLab
- Skip / Connect Later available

### 9. Knowledge Import
- Import: Documents, Projects, Git repos, Notes
- Support: Markdown, PDF, TXT, CSV, JSON, DOCX, XLSX, source code
- File type filtering
- Skip if desired

### 10. Workspace
- Create: Projects, Knowledge, Downloads, Extensions, Logs, Models, Cache
- Each dir gets a `.gitkeep`

### 11. Permissions
- Notifications, Auto Update, Background Service, Startup
- Crash Reports (on by default)
- Analytics (off by default, optional)

### 12. Summary
- Review all selections before applying

### 13. Finish
- Generate configuration files
- Encrypt and store secrets
- Create workspace structure
- Write profile
- Launch AetherOS Dashboard

## Navigation

Every step supports:
- **Next** — advance to next step
- **Previous** — go back to previous step
- **Skip** — jump to Summary (skip remaining optional steps)
- **Save Progress** — wizard state persisted to `config/setup-wizard-state.json`
- **Resume Later** — state saved, can close and reopen
- **Reset** — clears saved wizard state
