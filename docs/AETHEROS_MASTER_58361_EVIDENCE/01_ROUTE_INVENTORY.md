# AETHEROS MASTER 58361 — Route Inventory (source: `app/routes.ts`)

`APP_ROUTES` (all resolve; nav entries must point here):
`/`, `/:sessionId` (chat), `/home`, `/settings`, `/settings/developer`,
`/settings/advanced`, `/settings/multimodal`, `/settings/accessibility`,
`/command-center`, `/skills`, `/messaging`, `/communications`, `/artifacts`,
`/cron`, `/computer`, `/profiles`, `/providers`, `/agents`, `/agent-hub`,
`/projects`, `/models`, `/memory`, `/knowledge`, `/files`, `/browser`,
`/automation`, `/automation-center`, `/extensions`, `/extensions-center`,
`/services`, `/service-manager`, `/tasks`, `/history`, `/logs`, `/help`,
`/updates`, `/updates-manager`, `/marketplace`, `/mcp-manager`,
`/extension-sdk`, `/developer-tools`, `/sync`, `/sync-history`, `/devices`,
`/remote-instances`, `/connection-wizard`, `/conflict-resolution`,
`/remote-agent-dashboard`, `/security`, `/task-orchestrator`, `/swarm`,
`/agent-network`, `/agent-marketplace`, `/voice-assistant`,
`/screen-understanding`, `/file-understanding`, `/privacy`,
`/resource-manager`, `/diagnostics`, `/sandbox`, `/workspace-manager`,
`/ai-actions`, `/dashboard`, `/jarvis`.

Overlay views (modal over shell): agents, command-center, cron, profiles, settings.
Sidebar (`store/navigation.ts`, groups Workspace/AI/Work/System/More): home, chat,
jarvis-mode, projects, agents, models, memory, knowledge, files, browser, tasks,
automation, communications, orchestrator, activity(history), extensions, mcp,
security, services, diagnostics, resource-manager, settings + More:
service-manager, sandbox, workspaces, help, updates.
All sidebar routes verified present in `APP_ROUTES`. No route added or removed
in this pass.
