"""Service registry — all supported services, categories, and metadata."""

from __future__ import annotations

from connect.models import ServiceInfo, ServiceCategory

SERVICE_REGISTRY: dict[str, ServiceInfo] = {}

def _reg(id: str, name: str, desc: str, cat: ServiceCategory, **kw) -> ServiceInfo:
    info = ServiceInfo(id=id, name=name, description=desc, category=cat, **kw)
    SERVICE_REGISTRY[id] = info
    return info

# ── Communication ──
_reg("telegram_bot", "Telegram Bot", "Telegram bot integration for messaging", ServiceCategory.COMMUNICATION,
     icon="✈️", official=True, auth_type="token", supports_webhook=True, tags=["messaging", "bot"])
_reg("telegram_personal", "Telegram Personal", "Personal Telegram account messaging", ServiceCategory.COMMUNICATION,
     icon="✈️", official=True, auth_type="token", tags=["messaging", "personal"])
_reg("discord", "Discord", "Discord bot integration — messages, channels, roles", ServiceCategory.COMMUNICATION,
     icon="💬", official=True, auth_type="token", supports_webhook=True, tags=["messaging", "guild"])
_reg("slack", "Slack", "Slack workspace — messages, channels, files", ServiceCategory.COMMUNICATION,
     icon="🔷", official=True, auth_type="token", supports_webhook=True, tags=["messaging", "team"])
_reg("teams", "Microsoft Teams", "Microsoft Teams — messaging and channels", ServiceCategory.COMMUNICATION,
     icon="💼", official=True, auth_type="oauth", tags=["messaging", "microsoft"])
_reg("whatsapp", "WhatsApp Business", "WhatsApp Business API — messaging", ServiceCategory.COMMUNICATION,
     icon="📱", official=True, auth_type="token", tags=["messaging", "business"])

# ── Email ──
_reg("gmail", "Gmail", "Google Mail — read, send, manage emails", ServiceCategory.EMAIL,
     icon="📧", official=True, auth_type="oauth", supports_sync=True,
     permissions_available=["read", "send", "labels", "attachments"],
     tags=["google", "email"])
_reg("outlook", "Outlook", "Microsoft Outlook — email and calendar", ServiceCategory.EMAIL,
     icon="📨", official=True, auth_type="oauth", supports_sync=True,
     tags=["microsoft", "email"])
_reg("imap", "IMAP", "IMAP email server — read emails", ServiceCategory.EMAIL,
     icon="📬", official=True, auth_type="password", supports_sync=True,
     config_schema={"type": "object", "properties": {"host": {"type": "string"}, "port": {"type": "integer"}, "username": {"type": "string"}, "use_ssl": {"type": "boolean"}}},
     tags=["email", "protocol"])
_reg("smtp", "SMTP", "SMTP email server — send emails", ServiceCategory.EMAIL,
     icon="📤", official=True, auth_type="password",
     config_schema={"type": "object", "properties": {"host": {"type": "string"}, "port": {"type": "integer"}, "username": {"type": "string"}, "use_tls": {"type": "boolean"}}},
     tags=["email", "protocol"])
_reg("yahoo_mail", "Yahoo Mail", "Yahoo Mail integration", ServiceCategory.EMAIL,
     icon="📫", official=True, auth_type="oauth", tags=["email"])
_reg("proton_mail", "Proton Mail", "Proton Mail — encrypted email", ServiceCategory.EMAIL,
     icon="🔒", official=True, auth_type="api_key", tags=["email", "encrypted"])

# ── Development ──
_reg("github", "GitHub", "GitHub — repositories, issues, PRs, actions", ServiceCategory.DEVELOPMENT,
     icon="🐙", official=True, auth_type="oauth", supports_webhook=True, supports_sync=True,
     permissions_available=["repo", "issues", "prs", "actions", "admin"],
     tags=["git", "code", "ci"])
_reg("gitlab", "GitLab", "GitLab — repos, MRs, pipelines, CI/CD", ServiceCategory.DEVELOPMENT,
     icon="🦊", official=True, auth_type="oauth", supports_webhook=True,
     tags=["git", "ci"])
_reg("bitbucket", "Bitbucket", "Bitbucket — git repos and pipelines", ServiceCategory.DEVELOPMENT,
     icon="🔵", official=True, auth_type="oauth", tags=["git", "ci"])
_reg("docker_hub", "Docker Hub", "Docker Hub — container registry and images", ServiceCategory.DEVELOPMENT,
     icon="🐳", official=True, auth_type="token", tags=["containers", "registry"])
_reg("kubernetes", "Kubernetes", "Kubernetes — cluster management and monitoring", ServiceCategory.DEVELOPMENT,
     icon="☸️", official=True, auth_type="token", tags=["orchestration", "containers"])
_reg("jenkins", "Jenkins", "Jenkins CI/CD — jobs, pipelines, builds", ServiceCategory.DEVELOPMENT,
     icon="🤖", official=True, auth_type="token", tags=["ci", "automation"])
_reg("azure_devops", "Azure DevOps", "Azure DevOps — repos, pipelines, boards", ServiceCategory.DEVELOPMENT,
     icon="🟦", official=True, auth_type="oauth", tags=["devops", "microsoft"])
_reg("heroku", "Heroku", "Heroku — app deployment and management", ServiceCategory.DEVELOPMENT,
     icon="🚀", official=False, auth_type="token", tags=["paas", "deploy"])

# ── Productivity ──
_reg("notion", "Notion", "Notion — pages, databases, workspace", ServiceCategory.PRODUCTIVITY,
     icon="📝", official=True, auth_type="oauth", supports_sync=True,
     permissions_available=["read", "write", "databases", "comments"],
     tags=["notes", "wiki"])
_reg("jira", "Jira", "Jira — issues, sprints, projects", ServiceCategory.PRODUCTIVITY,
     icon="🔶", official=True, auth_type="oauth", supports_sync=True,
     tags=["project-management", "atlassian"])
_reg("linear", "Linear", "Linear — issue tracking, teams, cycles", ServiceCategory.PRODUCTIVITY,
     icon="⬆️", official=True, auth_type="oauth", supports_sync=True,
     tags=["project-management"])
_reg("clickup", "ClickUp", "ClickUp — tasks, docs, goals, whiteboards", ServiceCategory.PRODUCTIVITY,
     icon="🟢", official=True, auth_type="oauth", tags=["project-management"])
_reg("trello", "Trello", "Trello — boards, lists, cards", ServiceCategory.PRODUCTIVITY,
     icon="📋", official=True, auth_type="oauth", tags=["project-management", "atlassian"])
_reg("asana", "Asana", "Asana — projects, tasks, timelines", ServiceCategory.PRODUCTIVITY,
     icon="🎯", official=True, auth_type="oauth", tags=["project-management"])
_reg("todoist", "Todoist", "Todoist — tasks, projects, labels", ServiceCategory.PRODUCTIVITY,
     icon="✅", official=True, auth_type="oauth", supports_sync=True,
     tags=["productivity", "tasks"])
_reg("obsidian", "Obsidian", "Obsidian — knowledge base and notes", ServiceCategory.PRODUCTIVITY,
     icon="🗒️", official=True, auth_type="none", tags=["notes", "knowledge"])
_reg("confluence", "Confluence", "Confluence — docs, pages, spaces", ServiceCategory.PRODUCTIVITY,
     icon="📘", official=True, auth_type="oauth", tags=["wiki", "atlassian"])

# ── Google ──
_reg("google_drive", "Google Drive", "Google Drive — files and folders", ServiceCategory.CLOUD_STORAGE,
     icon="📂", official=True, auth_type="oauth", supports_sync=True,
     permissions_available=["read", "write", "share", "metadata"],
     tags=["storage", "google"])
_reg("google_docs", "Google Docs", "Google Docs — document editing", ServiceCategory.PRODUCTIVITY,
     icon="📄", official=True, auth_type="oauth", tags=["documents", "google"])
_reg("google_sheets", "Google Sheets", "Google Sheets — spreadsheet editing", ServiceCategory.PRODUCTIVITY,
     icon="📊", official=True, auth_type="oauth", tags=["spreadsheets", "google"])
_reg("google_calendar", "Google Calendar", "Google Calendar — events and schedules", ServiceCategory.PRODUCTIVITY,
     icon="📅", official=True, auth_type="oauth", supports_sync=True,
     permissions_available=["read", "write", "reminders"],
     tags=["calendar", "google"])
_reg("google_contacts", "Google Contacts", "Google Contacts — people and connections", ServiceCategory.PRODUCTIVITY,
     icon="👤", official=True, auth_type="oauth", tags=["contacts", "google"])

# ── Microsoft ──
_reg("onedrive", "OneDrive", "Microsoft OneDrive — cloud file storage", ServiceCategory.CLOUD_STORAGE,
     icon="☁️", official=True, auth_type="oauth", supports_sync=True, tags=["storage", "microsoft"])
_reg("sharepoint", "SharePoint", "Microsoft SharePoint — team sites and documents", ServiceCategory.PRODUCTIVITY,
     icon="🏢", official=True, auth_type="oauth", tags=["microsoft", "collaboration"])

# ── Cloud ──
_reg("dropbox", "Dropbox", "Dropbox — cloud file storage and sync", ServiceCategory.CLOUD_STORAGE,
     icon="📦", official=True, auth_type="oauth", supports_sync=True,
     permissions_available=["read", "write", "sharing"],
     tags=["storage"])
_reg("box", "Box", "Box — cloud content management", ServiceCategory.CLOUD_STORAGE,
     icon="📐", official=True, auth_type="oauth", tags=["storage", "enterprise"])
_reg("cloudflare", "Cloudflare", "Cloudflare — DNS, zones, workers, KV", ServiceCategory.CLOUD_PROVIDERS,
     icon="☁️", official=True, auth_type="token", tags=["cdn", "dns"])
_reg("aws", "AWS", "Amazon Web Services — EC2, S3, Lambda, IAM", ServiceCategory.CLOUD_PROVIDERS,
     icon="🟠", official=True, auth_type="token",
     permissions_available=["ec2", "s3", "lambda", "iam", "rds"],
     tags=["cloud", "infrastructure"])
_reg("azure", "Azure", "Microsoft Azure — VMs, storage, functions", ServiceCategory.CLOUD_PROVIDERS,
     icon="🟦", official=True, auth_type="oauth", tags=["cloud", "microsoft"])
_reg("gcp", "Google Cloud", "Google Cloud Platform — compute, storage, AI", ServiceCategory.CLOUD_PROVIDERS,
     icon="🟢", official=True, auth_type="oauth", tags=["cloud", "google"])
_reg("digitalocean", "DigitalOcean", "DigitalOcean — droplets, k8s, databases", ServiceCategory.CLOUD_PROVIDERS,
     icon="🔵", official=True, auth_type="token", tags=["cloud", "vps"])
_reg("vercel", "Vercel", "Vercel — frontend deployment and serverless", ServiceCategory.CLOUD_PROVIDERS,
     icon="▲", official=True, auth_type="oauth", tags=["hosting", "serverless"])
_reg("netlify", "Netlify", "Netlify — static site hosting and functions", ServiceCategory.CLOUD_PROVIDERS,
     icon="🌐", official=True, auth_type="oauth", tags=["hosting", "jamstack"])

# ── Database ──
_reg("postgresql", "PostgreSQL", "PostgreSQL database — queries and administration", ServiceCategory.DATABASES,
     icon="🐘", official=True, auth_type="password",
     config_schema={"type": "object", "properties": {"host": {"type": "string"}, "port": {"type": "integer"}, "database": {"type": "string"}, "username": {"type": "string"}}},
     tags=["sql", "relational"])
_reg("mysql", "MySQL", "MySQL database — queries and administration", ServiceCategory.DATABASES,
     icon="🐬", official=True, auth_type="password",
     config_schema={"type": "object", "properties": {"host": {"type": "string"}, "port": {"type": "integer"}, "database": {"type": "string"}, "username": {"type": "string"}}},
     tags=["sql", "relational"])
_reg("sqlite", "SQLite", "SQLite database — local file-based database", ServiceCategory.DATABASES,
     icon="🗄️", official=True, auth_type="none", tags=["sql", "embedded"])
_reg("mongodb", "MongoDB", "MongoDB — document database and aggregations", ServiceCategory.DATABASES,
     icon="🍃", official=True, auth_type="password", tags=["nosql", "documents"])
_reg("redis", "Redis", "Redis — in-memory data store and cache", ServiceCategory.DATABASES,
     icon="🔴", official=True, auth_type="password", tags=["cache", "key-value"])
_reg("supabase", "Supabase", "Supabase — PostgreSQL, auth, storage, realtime", ServiceCategory.DATABASES,
     icon="🔥", official=True, auth_type="token", tags=["backend", "baas"])
_reg("firebase", "Firebase", "Firebase — database, auth, storage, hosting", ServiceCategory.DATABASES,
     icon="🔥", official=True, auth_type="token", tags=["backend", "google"])

# ── AI Providers ──
_reg("openai", "OpenAI", "OpenAI — GPT-4o, GPT-4, GPT-3.5, embeddings, DALL·E", ServiceCategory.AI_PROVIDERS,
     icon="🧠", official=True, auth_type="api_key",
     permissions_available=["models", "completions", "embeddings", "images"],
     tags=["llm", "generative"])
_reg("anthropic", "Anthropic", "Anthropic — Claude 4, Claude 3, Claude 2", ServiceCategory.AI_PROVIDERS,
     icon="🤖", official=True, auth_type="api_key",
     tags=["llm", "generative"])
_reg("google_ai", "Google AI", "Google AI — Gemini, PaLM, embeddings", ServiceCategory.AI_PROVIDERS,
     icon="🟢", official=True, auth_type="api_key",
     tags=["llm", "generative", "google"])
_reg("openrouter", "OpenRouter", "OpenRouter — unified API for 200+ models", ServiceCategory.AI_PROVIDERS,
     icon="🔀", official=True, auth_type="api_key",
     tags=["llm", "aggregator"])
_reg("groq", "Groq", "Groq — ultra-fast inference with LPU", ServiceCategory.AI_PROVIDERS,
     icon="⚡", official=True, auth_type="api_key",
     tags=["llm", "fast"])
_reg("deepseek", "DeepSeek", "DeepSeek — open-source LLM API", ServiceCategory.AI_PROVIDERS,
     icon="🔮", official=True, auth_type="api_key",
     tags=["llm", "open-source"])
_reg("together", "Together AI", "Together AI — hosted open-source models", ServiceCategory.AI_PROVIDERS,
     icon="🤝", official=True, auth_type="api_key",
     tags=["llm", "open-source"])
_reg("fireworks", "Fireworks AI", "Fireworks AI — fast inference, open models", ServiceCategory.AI_PROVIDERS,
     icon="🎆", official=True, auth_type="api_key",
     tags=["llm", "fast"])
_reg("mistral", "Mistral AI", "Mistral — open-weight LLMs", ServiceCategory.AI_PROVIDERS,
     icon="🌬️", official=True, auth_type="api_key",
     tags=["llm", "open-source"])
_reg("cohere", "Cohere", "Cohere — LLM, embeddings, rerank, classify", ServiceCategory.AI_PROVIDERS,
     icon="🔷", official=True, auth_type="api_key",
     tags=["llm", "enterprise"])
_reg("perplexity", "Perplexity AI", "Perplexity — search-grounded LLM API", ServiceCategory.AI_PROVIDERS,
     icon="🔍", official=True, auth_type="api_key",
     tags=["llm", "search"])
_reg("ollama", "Ollama", "Ollama — local LLM runner (auto-discovered)", ServiceCategory.AI_PROVIDERS,
     icon="🦙", official=True, auth_type="none", auto_discoverable=True,
     tags=["llm", "local", "open-source"])
_reg("lm_studio", "LM Studio", "LM Studio — local model server (auto-discovered)", ServiceCategory.AI_PROVIDERS,
     icon="📥", official=True, auth_type="none", auto_discoverable=True,
     tags=["llm", "local"])
_reg("vllm", "vLLM", "vLLM — high-throughput local serving (auto-discovered)", ServiceCategory.AI_PROVIDERS,
     icon="⚙️", official=True, auth_type="none", auto_discoverable=True,
     tags=["llm", "local", "fast"])
_reg("openai_compat", "Custom OpenAI Compatible", "Any OpenAI-compatible API endpoint", ServiceCategory.AI_PROVIDERS,
     icon="🔗", official=True, auth_type="api_key",
     config_schema={"type": "object", "properties": {"base_url": {"type": "string"}, "api_key": {"type": "string"}}},
     tags=["llm", "compatible"])

# ── Media ──
_reg("youtube", "YouTube", "YouTube — videos, playlists, channels", ServiceCategory.MEDIA,
     icon="▶️", official=True, auth_type="oauth", tags=["video", "google"])
_reg("spotify", "Spotify", "Spotify — music, playlists, podcasts", ServiceCategory.MEDIA,
     icon="🎵", official=True, auth_type="oauth", tags=["music", "streaming"])
_reg("vimeo", "Vimeo", "Vimeo — video hosting and streaming", ServiceCategory.MEDIA,
     icon="🎬", official=False, auth_type="oauth", tags=["video"])

# ── Automation ──
_reg("zapier", "Zapier", "Zapier — cross-app automation and workflows", ServiceCategory.AUTOMATION,
     icon="⚡", official=True, auth_type="token", tags=["automation", "no-code"])
_reg("make", "Make (Integromat)", "Make — visual automation platform", ServiceCategory.AUTOMATION,
     icon="🔗", official=True, auth_type="token", tags=["automation", "no-code"])
_reg("n8n", "n8n", "n8n — self-hosted workflow automation", ServiceCategory.AUTOMATION,
     icon="🔄", official=True, auth_type="token", tags=["automation", "self-hosted"])
_reg("pipedream", "Pipedream", "Pipedream — developer workflow automation", ServiceCategory.AUTOMATION,
     icon="🔌", official=True, auth_type="oauth", tags=["automation", "developer"])

# ── Local Discovery ──
_reg("local_git", "Git", "Local Git installation", ServiceCategory.LOCAL,
     icon="🔀", official=True, auth_type="none", auto_discoverable=True,
     tags=["local", "vcs"])
_reg("local_docker", "Docker", "Local Docker daemon", ServiceCategory.LOCAL,
     icon="🐳", official=True, auth_type="none", auto_discoverable=True,
     tags=["local", "containers"])
_reg("local_python", "Python", "Local Python installation", ServiceCategory.LOCAL,
     icon="🐍", official=True, auth_type="none", auto_discoverable=True,
     tags=["local", "language"])
_reg("local_node", "Node.js", "Local Node.js installation", ServiceCategory.LOCAL,
     icon="🟢", official=True, auth_type="none", auto_discoverable=True,
     tags=["local", "language"])
_reg("local_github_cli", "GitHub CLI", "Local GitHub CLI (gh)", ServiceCategory.LOCAL,
     icon="🐙", official=True, auth_type="none", auto_discoverable=True,
     tags=["local", "cli"])
_reg("local_vscode", "VS Code", "Visual Studio Code installation", ServiceCategory.LOCAL,
     icon="💻", official=True, auth_type="none", auto_discoverable=True,
     tags=["local", "editor"])
_reg("local_cursor", "Cursor", "Cursor AI editor installation", ServiceCategory.LOCAL,
     icon="▽", official=True, auth_type="none", auto_discoverable=True,
     tags=["local", "editor", "ai"])
_reg("local_claude_code", "Claude Code", "Claude Code CLI installation", ServiceCategory.LOCAL,
     icon="🤖", official=True, auth_type="none", auto_discoverable=True,
     tags=["local", "cli", "ai"])


def get_service(service_id: str) -> ServiceInfo:
    return SERVICE_REGISTRY.get(service_id)


def get_all_services() -> list[ServiceInfo]:
    return list(SERVICE_REGISTRY.values())


def get_services_by_category(category: ServiceCategory) -> list[ServiceInfo]:
    return [s for s in SERVICE_REGISTRY.values() if s.category == category]


def get_auto_discoverable() -> list[ServiceInfo]:
    return [s for s in SERVICE_REGISTRY.values() if s.auto_discoverable]


def get_categories() -> list[dict]:
    cats = {}
    for s in SERVICE_REGISTRY.values():
        c = s.category
        if c not in cats:
            cats[c] = {"id": c.value, "name": c.value.replace("_", " ").title(), "count": 0}
        cats[c]["count"] += 1
    return list(cats.values())


def search_services(query: str, category: str = None) -> list[ServiceInfo]:
    q = query.lower()
    results = []
    for s in SERVICE_REGISTRY.values():
        if category and s.category.value != category:
            continue
        if (q in s.name.lower() or q in s.description.lower() or
            any(q in t.lower() for t in s.tags)):
            results.append(s)
    return results
