# Changelog

## v1.1.0 (Current — July 2026)

### Long-Term Support, SDK Stability & Future-Proof Architecture (Phase 16)

Complete LTS strategy, SDK v1 stability guarantee, database migration engine, error reporting infrastructure, opt-in telemetry system, performance monitoring dashboards, dependency management, security maintenance automation, release management, continuous testing infrastructure, backward compatibility system, and project migration framework.

#### LTS Strategy (`lts/`)
- **Channel Strategy** — Defined 6 release channels (Nightly, Beta, Stable, LTS, Security Patch, Emergency Hotfix) with lifecycle phases (Active Development → Maintenance → Security → EOL), promotion gates between channels, and support SLA by severity
- **Channel Policy** — Complete channel definitions with audience, update frequency, stability guarantees, telemetry requirements, and cross-channel switching rules with validation (`canSwitchChannel()`)
- **LTS Lifecycle** — 24-month support window per LTS release: 6 months active development, 12 months maintenance (critical bugs + security), 6 months security-only, then EOL with graduated notification timeline
- **Backport Policy** — What gets backported (critical/high CVEs to all channels, medium to LTS next release) and what does not (new features, refactoring, performance improvements)
- **LTS Config** — TypeScript `LTSConfig` interface with channel selection, auto-update, proxy, pinned version, backport-only mode; `LTSRelease` and `LTSLifecycle` types; `LTS_RELEASES` manifest with v1.0.0 LTS; helper functions for channel priority, EOL date checking, and version expiration
- **Governance** — Defined roles (LTS Manager, Security Team, QA, Documentation, Community) and escalation path with SLA by severity (4h response for critical, 24h for high, 3d for medium)

#### SDK Stability (`sdk/`)
- **SDK Versioning** — Created `sdk-version.ts` with `SDKManifest` type system, `SDK_VERSION_MANIFESTS` array (v1.0.0 with `minAppVersion: 1.0.0`, `maxAppVersion: 1.9999.9999`), 25 `SDKFeature` definitions across plugin lifecycle, file system, dialog, notification, updater, telemetry, error, and migration APIs
- **SDK v1 Plugin API** — Created `plugin-api-v1.ts` with complete `PluginContext` interface (8 API groups: system, files, dialogs, notifications, updater, telemetry, error, migration), `PluginLogger`, `PluginConfig`, `PluginHooks` (8 lifecycle hooks: onSessionStart, onSessionEnd, onToolCall, onToolResult, onAppStart, onAppQuit, onConfigChange, onError); `createPluginContext()` factory function with full stub implementations
- **SDK Compatibility Layer** — Created `sdk-compatibility-layer.ts` with `CompatMapping` system for API migration, `wrapWithCompatibility()` to auto-transform old API calls, `DeprecationWarning` system, `checkDeprecatedCalls()`, `SDKCompatReport` generation, `SDKCompatLayer` class for per-API version tracking, `compareVersions()`, `getSDKCompatLevel()`
- **Deprecation Manager** — Created `deprecation-manager.ts` with `DeprecationRecord` registry, `checkPluginCompatibility()` returning compatible/warnings/errors, `shouldWarn()` based on version proximity to removal, `getMigrationPath()`, version comparison helpers
- **Plugin Compatibility Tests** — Created `sdk/tests/plugin-compatibility.test.ts` with vitest test suite covering SDK v1 API surface (8 required groups), plugin lifecycle (8 hooks), logger (4 levels), config store (get/set/getAll/onChange with default values), deprecation detection, compat report generation (full/partial/deprecated/removed levels), version comparison (equal/greater/less/cross-major)

#### Database Migration Engine (`engine/migration/`)
- **Migration Engine** — Created `migration-engine.ts` with `MigrationEngine` class managing lifecycle: register, apply, rollback, validate, backup. Supports topological sorting for dependency-ordered execution, persistent state tracking via `localStorage` (`aetheros.migration.state`), in-progress recovery detection, batched `applyAllPending()` with automatic rollback on failure
- **Standard Migrations** — Created `migrations.ts` with 5 registered migrations: config-v1-to-v2 (flat→namespaced config with backup/rollback), workspace-index-v1 (workspace index initialization), knowledge-base-init (knowledge base structure), extension-registry-init (extension registry with dependency on config migration), telemetry-prefs-init (telemetry consent state with dependency on config migration)
- **Config Migration** — Created `backward-compat/config-migration.ts` with format versioning (`_formatVersion`), `migrateConfig()` auto-detecting version gaps, `needsMigration()` predicate, `backupConfig()`/`rollbackConfig()` for safe state transitions, `validateConfig()` for integrity checking

#### Error Reporting (`engine/error-reporting/`)
- **Error Categorizer** — Created `error-categorizer.ts` with 10 regex-based error patterns (ENOENT, ETIMEDOUT, OOM, permission denied, update failure, plugin error, config invalid, crash/segfault, timeout), `categorizeError()` returning structured `CategorizedError` with severity/category/source/timestamp/suggestion/frequency, `exportDiagnosticBundle()` with platform info and category/severity aggregation
- **Error Store** — Created `error-store.ts` with persistent error store (last 100 errors in `localStorage`), deduplication by message+category with frequency tracking, `markRecovered()`, filtering by category/severity, `getDiagnosticBundle()`, reactive `onChange()` listener pattern

#### Opt-In Telemetry (`engine/telemetry/`)
- **Telemetry Manager** — Created `telemetry.ts` with `TelemetryManager` class supporting 11 event types (app_start, app_quit, crash, error, feature_used, update_installed, migration_completed, extension_loaded, extension_failed, performance_metric), event buffer (max 50, flush every 5min), HTTPS POST to `telemetry.aetheros.dev/v1/events`, anonymous client ID generation, session-scoped tracking, `keepalive: true` on app quit
- **Consent Model** — Created `telemetry-consent.ts` with granular consent (enabled, crashReporting, performanceMetrics, featureUsage), `requestTelemetryConsent()` dialog API, `showTelemetrySettings()` UI hook, `getTelemetrySummary()` for status display, persistent consent state in `localStorage`

#### Performance Monitoring (`engine/performance/`)
- **Performance Monitor** — Created `performance-monitor.ts` with `PerformanceSnapshot` covering 8 domains (startup, CPU, GPU, memory, disk, extensions, models, automation), configurable collection interval (default 60s), history up to 1000 snapshots, `getAverages()` aggregation, `getSnapshotsInRange()` for time-series analysis, persistent history via `localStorage`, `onChange()` listener pattern
- **Performance Dashboard** — Created `dashboard-store.ts` with `PerformanceDashboardStore` providing real-time CPU/memory/GPU history extraction (`getCPUHistory()`, `getMemoryHistory()`), startup timeline (`getStartupTimeline()`), start/stop/pause monitoring controls, reactive state updates

#### Dependency Management (`engine/dependency/`)
- **Dependency Manager** — Created `dependency-manager.ts` with 5 detection types (deprecated, vulnerability, license, unused, duplicate), `DependencyInfo` registry, `audit()` producing score (0-100) and prioritized recommendations, `checkForUpdates()` with major/minor/patch classification, `registerVulnerability()` for CVE tracking

#### Security Maintenance (`engine/security-maintenance/`)
- **Security Scheduler** — Created `security-maintenance.ts` with 5 security tasks (dependency-update, security-scan, secret-detection, static-analysis, binary-verification), each with configurable frequency (daily/weekly/monthly/on-release) and priority, `runAllTasks()` producing `SecurityReport` with severity-bucketed findings and score (0-100), `isTaskDue()` for scheduling, last-run tracking

#### Release Management (`engine/release/`)
- **Release Manager** — Created `release-manager.ts` with 5 release types (patch, minor, major, lts, hotfix), `bumpVersion()` with semantic version arithmetic, `generateChangelog()` with categorized entries (Added/Changed/Deprecated/Removed/Fixed/Security) and channel-specific sections, `generateMigrationGuide()` for breaking changes, `validateRelease()` pre-flight checks, `getAffectedModules()` deducing impacted subsystems from change descriptions

#### Continuous Testing (`engine/testing/`)
- **Testing Engine** — Created `continuous-testing.ts` with 11 registered test definitions across 8 suites (plugins: SDK API surface, compatibility, isolation; marketplace: package format; updates: download/verification, rollback; cloud-sync: connectivity, conflict resolution; automation: workflow execution; voice: input/output; installer: installation verification), `runAllSuites()` producing `ContinuousTestReport` with suite-level pass/fail/total and overall score (0-100)

#### Backward Compatibility (`engine/backward-compat/`)
- **Compatibility Checker** — Created `compatibility-checker.ts` with 6 compat types (extension, agent, theme, marketplace-package, automation-workflow, configuration-file), `checkAllCompat()` running all checks, `getBackwardCompatScore()` aggregating results, format version validation

#### Project Migration (`engine/project-migration/`)
- **Project Migrator** — Created `project-migrator.ts` with 6 migration scopes (settings, workspace, knowledge, models, extensions, cloud-sync), each with named steps with execute/rollback, `runAll()` producing `MigrationSummary` (scopes completed/failed, steps completed/failed, duration, errors), per-scope run history tracking

#### New Infrastructure
- Created 14 new directories: `lts/`, `sdk/`, `sdk/v1/`, `sdk/compat/`, `sdk/tests/`, `engine/migration/`, `engine/error-reporting/`, `engine/telemetry/`, `engine/performance/`, `engine/dependency/`, `engine/security-maintenance/`, `engine/release/`, `engine/testing/`, `engine/backward-compat/`, `engine/project-migration/`
- Created 20 new TypeScript/JS source files across all engines
- Created 6 new documentation files: `SDK_STABILITY_REPORT.md`, `MIGRATION_SYSTEM.md`, `PERFORMANCE_MONITORING.md`, `TELEMETRY_DESIGN.md`, `SECURITY_MAINTENANCE.md`, `ARCHITECTURE_LTS.md`
- Added 12 new npm scripts for LTS, SDK, migration, telemetry, performance, dependency, security, release, testing, backward compat, project migration operations
- Updated CHANGELOG.md with Phase 16 entry

## v1.0.0 (July 2026)

### Production Release & Enterprise Distribution (Phase 15)

Complete production hardening: CI/CD pipelines, code signing verification, comprehensive documentation, security auditing, dependency auditing, crash recovery enhancement, performance benchmarking, release engineering tools, and enterprise deployment infrastructure.

#### CI/CD & Build
- **GitHub Actions Pipelines** — Created 5 CI/CD workflows: `desktop-build.yml` (push/PR on main, multi-platform build matrix with lint/test/build/package/validate), `desktop-release.yml` (tag-push triggered, version resolution, parallel builds across 4 targets, artifact consolidation, GitHub Release creation with auto-generated notes), `desktop-nightly.yml` (daily 06:00 UTC scheduled build with auto-versioning), `desktop-test.yml` (unit/Electron/integration test matrix across all 3 OS families), `desktop-security.yml` (weekly npm audit, Snyk scan, Trivy filesystem scan, CodeQL analysis)
- **Version Management** — Created `scripts/release/bump-version.mjs` with 8 bump types (major/minor/patch/premajor/preminor/prepatch/prerelease), automatically updates `package.json` version
- **Release Notes Generator** — Created `scripts/release/generate-release-notes.mjs` that produces formatted release notes from CHANGELOG content and git log, writes to `release/RELEASE_NOTES.md`

#### Crash Recovery Enhancement
- **Enhanced `crash-recovery.ts`** — Added crash event history (last 50 events with timestamp/type/message), safe mode toggle with `setSafeMode()`/`isSafeMode()`/`launchSafeMode()`, crash type tracking (renderer/main/unknown), `getCrashDiagnostics()` for debugging, `logRecoverySuccess()` to reset attempt counter on successful recovery, persistent last crash timestamp via `LAST_CRASH_TIMESTAMP_KEY`

#### Security & Dependency Auditing
- **Security Audit Framework** — Created `scripts/security/audit-security.mjs` with 23 automated checks across 7 categories (Renderer, IPC, Storage, Crash Recovery, Updates, Code Signing, Build config), produces detailed `docs/SECURITY_AUDIT.md` with per-finding severity, score, and recommendations
- **Dependency Audit** — Created `scripts/security/audit-dependencies.mjs` that runs npm audit, npm outdated, and license-checker (via npx), produces comprehensive `docs/DEPENDENCY_AUDIT.md` with vulnerability counts by severity, outdated packages table, license summary, health score (0-100), and prioritized recommendations
- **Secrets Scanner** — Created `scripts/security/check-secrets.mjs` that scans all source files for 9 categories of secret patterns (API keys, passwords, tokens, AWS keys, private keys, etc.), excludes `.git`/`node_modules`/`release`/`coverage`, flags potential leaks

#### Quality Verification
- **Accessibility Verification** — Created `scripts/quality/verify-a11y.mjs` that checks accessibility store completeness (reduced motion, high contrast, font scaling, screen reader support), verifies ARIA labels in components, produces `docs/ACCESSIBILITY_REPORT.md`
- **Localization Verification** — Created `scripts/quality/verify-l10n.mjs` that compares all locale JSON files against the base `en` locale, calculates per-locale coverage percentage, identifies missing and extra keys, produces `docs/LOCALIZATION_REPORT.md`
- **Performance Benchmark Report** — Created `scripts/quality/benchmark-performance.mjs` with target metrics across 7 categories (startup performance, memory usage, CPU usage, bundle size, installer size, GPU performance), produced `docs/PERFORMANCE_REPORT.md`
- **Verification Suite** — Created `scripts/quality/verify-all.mjs` that runs lint, TypeScript check, unit tests, and build in sequence, reports pass/fail for each step

#### Production Documentation (10 new documents)
- **README.md** — Comprehensive project readme with features, quick start, system requirements, documentation index, build targets, CI/CD status, project structure, tech stack, security highlights
- **INSTALL.md** — Platform-specific installation guide covering Windows (NSIS/MSI/Group Policy), macOS (DMG/ZIP/CLI), Linux (AppImage/deb/rpm/AUR), silent installation for all platforms, auto-update channel documentation, uninstallation, troubleshooting
- **USER_GUIDE.md** — End-user documentation covering first launch, dashboard, agent management, workspace, all 5 Phase 14 features (Resource Manager, Diagnostics Center, Service Manager, Secure Sandbox, Workspace Manager), command palette, notifications, settings (general/account/workspace/agents/privacy/updates), keyboard shortcuts, accessibility, troubleshooting
- **ADMIN_GUIDE.md** — Enterprise deployment guide covering mass deployment via Group Policy/SCCM/MDM/APT repositories, enterprise policy file specification, environment variable configuration, update management, code signing verification, audit logging, compliance (SOC 2/GDPR/HIPAA), monitoring integration (Prometheus/Datadog/Splunk), troubleshooting, directory layout reference, port/exits code reference
- **DEVELOPER_GUIDE.md** — Developer setup guide with platform-specific prerequisites, key commands, project structure, architecture overview (process model, IPC, state management), component/store patterns, testing, debugging, release process, code signing, contribution guidelines
- **API_REFERENCE.md** — Preload bridge API reference covering ~56 exports across 12 categories (process, window, fs, shell, config, dialogs, updater, IPC, diagnostics, notifications), IPC channel documentation, error handling, security constraints
- **SECURITY.md** — Comprehensive security document covering architecture security (process isolation, IPC, CSP), code signing (macOS notarization, Windows Authenticode, Linux GPG), data security (encrypted storage, sensitive file protection), update verification, crash reporting, vulnerability disclosure policy, deployment security checklist
- **PRIVACY.md** — Privacy policy covering data collection (required vs optional, never-collected), storage (local, sensitive), sharing policy, user rights (view/export/delete/opt-out), GDPR/CCPA/SOC 2 compliance, third-party services, contact information
- **ROADMAP.md** — Development roadmap covering completed phases 1-15, future phases 16-20 (Admin Portal, Plugin Ecosystem, Mobile/Web, AI-Assisted Features, Enterprise SSO/Compliance), version history
- **RELEASE_CHECKLIST.md** — 65-item release checklist across 9 categories (code quality, build verification, security checks, code signing, documentation, localization, accessibility, performance, manual testing, enterprise/deployment), release day procedure, known issues section, sign-off table

#### Production Readiness Automation
- **Production Readiness Check** — Created `scripts/release/check-production-readiness.mjs` with 20 automated readiness checks (version, electron-builder, code signing, tests, TypeScript strict, ESLint, Prettier, .gitignore, CHANGELOG, README, LICENSE, Code of Conduct, Docker, CI/CD, i18n, crash recovery, auto-updater, security audit, installation guide, user guide), reports pass/fail per check and overall percentage score
- **Migration Guide Generator** — Created `scripts/release/generate-migration-guide.mjs` that extracts breaking changes from CHANGELOG, produces structured `docs/MIGRATION_GUIDE.md` with overview, breaking changes list, config/data/API migration sections, rollback instructions, and support resources
- **Integration Test Script** — Created `scripts/test-desktop.mjs` that runs build (optional), TypeScript check, lint, vitest, Electron module tests, and verifies release artifacts — single command for pre-submit/CI validation

#### Production Scripts & Configuration
- Added 12 new npm scripts: `security:audit`, `security:deps`, `security:secrets`, `release:notes`, `release:migration`, `release:bump`, `release:check`, `quality:a11y`, `quality:l10n`, `quality:benchmark`, `quality:verify`, `validate`
- Created 3 new script directories: `scripts/release/`, `scripts/security/`, `scripts/quality/`
- Created `CONTRIBUTING.md` with contribution guidelines, PR checklist, code style, testing/security requirements
- Created `.github/CODE_OF_CONDUCT.md` with community standards and enforcement
- Created `docs/` directory for all production documentation

## v0.28.0 (July 2026)

### Universal Operating Environment & Desktop Enhancements (Phase 14)

Complete Phase 14: Universal Command Center, Resource Manager, Diagnostics Center, Service Manager, Secure Sandbox, Workspace Manager, and enhanced Developer Tools.

- **Resource Manager** — Created `ResourceManagerView` with live system resource monitoring (CPU/Memory/GPU/Disk), process table with CPU/Memory/status columns, disk usage visualization with color-coded progress bars, network traffic (download/upload/connections), real-time CPU history chart, active alerts panel with severity indicators, live polling toggle. Store: `store/resource-manager.ts` with ResourceMetric, ProcessInfo, DiskUsage, NetworkTraffic types and alert history tracking.
- **Diagnostics Center** — Created `DiagnosticsCenterView` with 18 system health checks across 6 categories (system/network/storage/plugins/security/performance), per-check severity labeling (info/warning/error), categorized result display (passed/warning/failed) with color-coded status indicators, aggregate statistics (total/passed/warning/failed), "Run All Checks" with sequential execution, 6 repair actions with completion/failure status, per-repair output display, health report generation. Store: `store/diagnostics-center.ts` with DiagnosticCheck, RepairAction, HealthReport types and full state management.
- **Service Manager** — Created `ServiceManagerView` with service dashboard (8 managed services with status/uptime/memory/CPU/version), service sidebar navigation with status pulse indicators, detail panel with full service metadata, start/stop/restart controls, auto-restart configuration per-service, log viewer with level filtering (all/debug/info/warn/error) and service filtering, auto-refresh toggle. Store: `store/service-manager.ts` with ManagedService, ServiceLog types.
- **Secure Sandbox** — Created `SandboxView` with plugin isolation browser (4 sandboxed plugins with status/isolation/memory/CPU info), per-plugin permission matrix (10 resource types: filesystem/network/process/clipboard/notifications/camera/microphone/screen/usb/bluetooth), allow/deny/prompt per-permission toggle, sandbox events timeline with blocking indicators, global policy settings (default policy, isolation level, network block, filesystem restriction). Store: `store/sandbox.ts` with SandboxedPlugin, PermissionRule, SandboxEvent types.
- **Workspace Manager** — Created `WorkspaceManagerView` with workspace layout browser (3 default layouts: Default/Development/Monitoring with tab configurations and split settings), session group management with color coding, workspace shortcuts with search/filter, shortcut metadata (path/type/last opened), layout activation/deletion, new layout creation. Store: `store/workspace-manager.ts` with WorkspaceLayout, WorkspaceTab, SessionGroup, WorkspaceShortcut types.
- **Route & Navigation Updates** — Added 5 new routes: `/resource-manager`, `/diagnostics`, `/service-manager`, `/sandbox`, `/workspace-manager`. Updated AppView, AppRouteId, APP_ROUTES, NavSectionId, NAV_SECTIONS with corresponding entries. Lazy-loaded all new views in desktop-controller.tsx.
- **New/Modified Files**: 10 new files (5 stores + 5 views), 3 modified (routes.ts, desktop-controller.tsx, navigation.ts).

## v0.27.0 (July 2026)

### Voice Assistant, Multimodal AI & Smart Workspace (Phase 13)

Complete voice assistant system with multiple STT/TTS providers, multimodal AI for images/documents/screen/files, screen understanding with OCR, and enhanced smart workspace:

- **Voice Assistant UI** — Created `FloatingAssistant` component with draggable floating window, push-to-talk/wake-word/always-on modes, real-time volume visualization, transcript display, processing state indicators (listening/processing/speaking/error), minimize/expand/close controls, microphone/speaker device selection, noise suppression/echo cancellation/AGC/silence detection configuration. Wired as always-available shell overlay in `desktop-controller.tsx`.
- **Voice Settings Panel** — Created `VoiceSettingsPanel` with full STT provider selection (OpenAI Whisper, Whisper.cpp, Faster-Whisper, Azure Speech, Google Speech, Deepgram, AssemblyAI, Custom), TTS provider selection (Edge, OpenAI, Azure, Google, ElevenLabs, Custom), voice/speed controls, activation mode configuration, push-to-talk key binding, wake word and sensitivity, audio processing settings, floating assistant display options.
- **Screen Understanding** — Created `ScreenCapturePanel` with capture mode selection (fullscreen/window/region/browser-tab), screen capture via `getDisplayMedia` API, auto-analyze toggle, OCR extraction toggle, ask-before-capture privacy control, capture history gallery, permission-gated access flow.
- **File Understanding** — Created `FileAnalyzer` with drag-and-drop file upload zone, file type detection (PDF/Word/Excel/PowerPoint/Markdown/CSV/JSON/XML/ZIP/Image/Video/Audio), configurable extraction methods (text/OCR/vision), max file size settings, recent analyses list, auto-analyze clipboard images support.
- **Store: `screen-understanding.ts`** — Complete state management for capture mode/status/results/history, OCR settings, window enumeration, region selection, permission and overlay state.
- **Store: `file-understanding.ts`** — Complete state management for file analysis results, document type detection, processing method selection, auto-analysis settings, recent history.
- **Store: `voice-logging-store.ts`** — Logging system for voice sessions, speech recognition, OCR, screen analysis, errors, and performance metrics with category/severity filtering and auto-export.
- **Privacy Consent System** — Created `ConsentDialog` component with per-resource permission dialogs (microphone/camera/screen/clipboard/files), resource-specific icons and descriptions, remember-choice toggle. Created `PrivacySettingsPanel` with processing mode selection (local/hybrid/cloud), per-device permission controls (grant/revoke), encrypted storage toggle, privacy indicators toggle.
- **Accessibility Settings** — Created `AccessibilitySettings` page with vision settings (screen reader, high contrast, 4 contrast modes, font sizes, custom font size 12-24px, reduce motion, reduce transparency, focus indicator), hearing settings (captions, 3 caption styles, announcement volume), mobility settings (keyboard navigation, voice navigation).
- **Mind Map Component** — Created `MindMap` component with interactive tree-based node hierarchy, collapsible branches, depth-colored nodes (10 colors), editable labels (double-click), add child/root node, zoom controls. Fills the previously missing mind-map route in SmartWorkspace.
- **Route & Navigation Updates** — Added 6 new routes: `/voice-assistant`, `/screen-understanding`, `/file-understanding`, `/settings/accessibility`, `/privacy`, `/ai-actions`. Updated `AppView`, `AppRouteId`, `APP_ROUTES` with corresponding entries. Lazy-loaded all new views in `desktop-controller.tsx`.
- **Documentation** — Created 5 new documentation files: `VOICE_ASSISTANT.md`, `MULTIMODAL_AI.md`, `OCR.md`, `SMART_WORKSPACE.md`, `ACCESSIBILITY.md`. Updated `CHANGELOG.md`, `PROJECT_STATUS.md`.
- **New/Modified Files**: 18 new files, 2 modified (routes.ts, desktop-controller.tsx).

## v0.26.0 (July 2026)

### Advanced Agent Intelligence & Autonomous Task Orchestration

Complete autonomous agent orchestration system enabling AetherOS to understand complex requests, decompose them into plans, execute with multi-agent collaboration, and recover from failures:

- **Task Orchestrator Core** — Created `aetheros_automation/orchestrator/` with `TaskOrchestrator` class managing full lifecycle: objective understanding, task analysis, plan creation, agent selection, execution, monitoring, pause/resume/cancel/restart. Supports sub-agent creation/termination, agent messaging, approval callbacks, plan persistence.
- **Execution Engine** — Created `ExecutionEngine` for running individual orchestration tasks with tool dispatch to registry and automation tool modules. Supports execution context tracking and parallel task execution.
- **Checkpoint System** — Created `CheckpointManager` with JSON-based checkpoint persistence. Supports save/load/list/delete operations. Each checkpoint captures plan state (completed/pending/failed tasks), enabling pause/resume/restore workflows.
- **Model Router** — Created `aetheros_automation/routing/model_router.py` with 8 built-in models across 4 providers (OpenAI, Anthropic, Gemini, DeepSeek, local). Role-based model preferences (developer→claude-sonnet, research→gpt-4o, browser→gpt-4o-mini, etc.). Fallback chains per provider. Cost-aware selection with context window, latency, and privacy filtering.
- **Multi-Agent Collaboration** — Created `aetheros_automation/multi_agent/` with `AgentCollaborationManager` (start/end collaborations, send/broadcast messages, share/results), `AgentMessaging` (async send/receive, conversation history, send-and-wait pattern), `SubAgentManager` (create/terminate sub-agents with limited scope, permissions, and execution limits).
- **Execution Graph** — `_build_execution_graph()` in TaskOrchestrator creates dependency-level-based execution graphs with support for sequential, parallel, conditional, dependent, retry, fallback, and human-approval execution modes. Levels computed via topological sorting with Kahn's algorithm.
- **Failure Recovery** — Created `aetheros_automation/recovery/` with `RetryHandler` (exponential backoff with jitter, failure classification, retryable/non-retryable error detection), `FallbackHandler` (primary+fallback operation chains, registered fallback strategies).
- **Result Validation** — Created `aetheros_automation/validation/validator.py` with `ResultValidator` checking result completeness (not null, has summary, relevance to task description, file existence). Custom validator registration.
- **Task Templates** — Created `aetheros_automation/templates/templates.py` with 7 built-in templates (Research Report, Software Development, Data Analysis, Content Creation, Email Campaign, Business Automation, Personal Assistant). Template application creates full `OrchestrationPlan` with inferred roles, tools, durations.
- **Natural Language Automation** — Created `aetheros_automation/nlp/nlp_automation.py` with `NLPAutomationEngine` processing natural language requests into `OrchestrationPlan`. Smart sentence splitting, role/tool inference, duration estimation, risk assessment, schedule detection (weekly/daily/interval/oneshot).
- **Specialized Agents** — Added 4 new agent roles: CreativeAgent (design, visual concepts, brainstorming), DataAgent (analysis, visualization, cleaning, reporting), CommunicationAgent (email, notification, summarization, relay), ReviewAgent (code review, document review, security review, quality review). All registered with `AgentRegistry`.
- **Extended Role System** — Added `GraphExecutionMode` enum (sequential, parallel, conditional, dependent, retry, fallback, human_approval), `TaskPriority`, `RiskLevel`, `FailureType`, `ApprovalAction`, `ApprovalResponse` enums to the models.
- **Human-in-the-Loop Approval** — Approval system integrated into TaskOrchestrator. `_request_approval()` emits events for the UI to display. Supports approve-once, approve-session, always-allow, deny patterns. Detectable approval actions (dangerous, destructive, sensitive data, payment, etc.).
- **Desktop Orchestrator UI** — Created `src/store/task-orchestrator.ts` with complete nanostore (plans, execution states, agent activities, checkpoints, approval requests, limits). Created `src/app/task-orchestrator/` with 6 views: `index.tsx` (main workspace with tabs), `plan-view.tsx` (task list with status), `execution-graph.tsx` (visual graph with levels), `agent-activity.tsx` (live agent feed), `checkpoint-view.tsx` (checkpoint management), `approval-panel.tsx` (approval requests with accept/deny). Route constant, AppView/AppRouteId/NavSectionId updates, lazy loading registered in desktop-controller.
- **Documentation** — Created 4 new documentation files: `ORCHESTRATION.md`, `TASK_ENGINE.md`, `MULTI_AGENT.md`, `EXECUTION_GRAPH.md`. Updated `PROJECT_STATUS.md`, `CHANGELOG.md`, `TODO.md`, `ARCHITECTURE.md`.
- **Comprehensive Tests** — Created `tests/aetheros_automation/test_orchestrator.py` with 50+ tests covering TaskOrchestrator (objectives, planning, roles, approval, agents, sub-agents, messaging, risk, persistence), Execution Graph (decomposition, levels, conditional), ModelRouter (selection, fallback, CRUD), RetryHandler (backoff, classification), ResultValidator (validation, checks), TaskTemplateManager (list, get, apply, CRUD), NLPAutomation (simple/complex requests, roles, schedule), Collaboration (start, message, share, end), Messaging (send/receive, conversation), SubAgentManager (create, terminate, all), CheckpointManager (save, load, list, delete), FallbackHandler (chain, all-fail).

## v0.25.0 (July 2026)

### Advanced Multimodal AI System

Complete multimodal AI system for the desktop chat, supporting text, voice, images, screenshots, camera captures, audio, video, documents, and files in the same conversation with automatic model capability routing, streaming, and privacy safeguards:

- **Multimodal State Store** — Created `src/store/multimodal.ts` with comprehensive nanostore covering camera state (enumeration/status/stream), screen capture state, privacy indicators (mic/camera/screen/cloud), processing status per modality, model routing state, TTS/STT/vision toggles, local mode, audio device selection, and voice preference. 20+ action functions for state management.
- **Model Capability Router** — Created `src/lib/model-router.ts` with automatic input type detection analyzing composer text and attachments. Detects 7 input categories (text/code/image/audio/video/document/mixed) and maps to 6 model roles (default/coding/vision/speech/long-context). Cross-references provider ManagerModel capabilities (vision/audio/functionCalling/streaming) and user-defined RouterRules for best-model selection with confidence scoring.
- **Camera Capture System** — Created `src/components/ui/camera-capture.tsx` with device enumeration (via `navigator.mediaDevices.enumerateDevices`), camera preview (video element + MediaStream), photo capture to data URL (canvas snapshot), multi-camera switching, permission gating through Electron API. Integrates with existing composer attachment system.
- **Screen Capture System** — Created `src/lib/screen-capture.ts` with full screen and window capture via `navigator.mediaDevices.getDisplayMedia`, capture source enumeration (screen/window with thumbnails), Electron `desktopCapturer` integration, MediaStream lifecycle management. Created dialog component with source grid and capture flow. Privacy indicator integration.
- **Document Intelligence** — Created `src/lib/document-intelligence.ts` with text-based file extraction (50+ text/code formats via FileReader), basic PDF text parsing (regex-based content extraction), office document metadata identification (PDF/DOCX/XLSX/PPTX/RTF), file type classification (text/office/code), document icon/color mapping.
- **Media Players** — Created `src/components/ui/audio-player.tsx` with Web Audio API waveform visualization (AnalyserNode with FFT), play/pause/seek, volume slider, speed control (0.25x–4x), time display, error states. Created `src/components/ui/video-player.tsx` with standard media controls, fullscreen toggle, progress bar, poster support, auto-play, hover-reveal HUD. Both use the existing `hermes-media://` streaming protocol.
- **Document Preview** — Created `src/components/ui/document-preview.tsx` with inline text extraction display, confidence indicators (high/medium/low), expandable content, loading spinner, error states, metadata display (file name, size, type, page count).
- **Multimodal Message Components** — Created `src/components/assistant-ui/multimodal-message.tsx` with MediaAttachment (auto-detects audio/video/image/file via MIME type and extension), AttachmentGallery (responsive grid with overflow count), ProcessingBadge (animated indicators for processing/success/error), ModelTag (model and provider display).
- **Privacy Indicators** — Created `src/components/ui/privacy-indicator.tsx` with PrivacyIndicators (compact floating widget showing mic/camera/screen/cloud active status with animated pulse dots) and PrivacyBanner (warning bar when recording). Integrated into desktop controller as fixed-position overlays.
- **Composer Integration** — Added Camera and Screen Capture menu items to the composer's context menu (`context-menu.tsx`). Camera and Monitor icons added to `src/lib/icons.ts` from `@tabler/icons-react`.
- **Multimodal Settings** — Created `src/app/settings/multimodal.tsx` with voice controls (STT/TTS toggles, voice selection from 6 TTS voices, audio input/output device selectors), vision settings (image understanding toggle, camera scanning with device list), local processing mode toggle.
- **Route & Navigation Integration** — Added `MULTIMODAL_ROUTE = '/settings/multimodal'` to routes, extended AppView/AppRouteId union types, added APP_ROUTES entry, lazy-loaded MultimodalSettingsView in desktop-controller matching existing overlay patterns.
- **Clipboard Utilities** — Created `src/lib/clipboard-utils.ts` with clipboard image/text/file read, full clipboard write, data URL ↔ Blob conversion helpers.
- **Privacy-First Design** — Every capture capability (mic, camera, screen) goes through platform permission APIs (`getUserMedia`, `getDisplayMedia`). Privacy indicators show real-time active capture state. Camera/screen capture respects existing permission/audit system architecture.

## v0.24.0 (July 2026)

### Advanced Security, Sandbox & Permission System

Complete enterprise-grade security architecture for the desktop app, implementing granular permissions, sandboxed execution, approval workflows, threat detection, and comprehensive audit logging:

- **Security Center Desktop View** — Created `src/app/security-center/` with 8-tab layout (Overview, Permissions, Approvals, Sandbox, Audit Log, Alerts, Secrets, Privacy). Full integration into desktop routes, navigation sidebar, and lazy-loaded view hierarchy matching existing view patterns.
- **Permission Manager** — Granular per-action permissions across 10 categories (Filesystem, Network, Browser, Clipboard, Terminal, Docker, Python, Database, Cloud, System) with 34 individual permission definitions. Per-agent/plugin/MCP/automation permission profiles with Allow/Deny/Ask Every Time/Ask Once policies and 5 duration types (Ask Every Time, Ask Once, Temporary, Session, Permanent).
- **Approval Center** — Clear approval dialogs showing agent identity, requested action, reason, target, risk level (Low/Medium/High/Critical), affected files, command, network destination. User options: Allow Once, Allow Session, Always Allow, Deny.
- **Risk Level System** — 4-tier risk classification (Low: read-only, Medium: file modification, High: code execution, Critical: destructive operations) with visual indicators throughout the UI.
- **Sandbox Manager** — Isolated execution environments for agents, plugins, MCP servers, Python, shell, browser, and automation. 5 sandbox modes (Read Only, Restricted, Standard, Trusted, Custom). Filesystem sandbox with allowed/blocked/read-only folders and temp/project workspace scoping. Network security with domain allowlist/blocklist, IP/port restrictions, and offline mode. Configurable resource limits (memory, CPU, timeout).
- **Audit Log Viewer** — Tamper-evident audit trail with 18 event types. Search, filter by event type and risk level. Timestamp, agent, result (success/failure/blocked), tool, and target tracking. JSON export capability.
- **Security Alerts** — 9 alert categories (Repeated Failures, Suspicious Tool Usage, Unexpected Network, Permission Escalation, Untrusted Plugin, Invalid Signature, Credential Failure, Brute Force, Abnormal Activity) with 4 severity levels. Acknowledge and resolve workflow. Alert aggregation with occurrence counting.
- **Secrets Manager** — Encrypted vault for API keys, passwords, tokens, and certificates. Masked display, category organization, provider tracking, last-accessed timestamps. Never-log-credentials enforcement.
- **Privacy Settings** — 5 privacy modes (Offline, Local-Only, No Telemetry, Private, Strict Sandbox). Toggle controls for offline mode and telemetry. Data handling policy display.
- **Security Store** — Created `src/store/security.ts` with comprehensive nanostore atoms for all security state: permissions, grants, approvals, sandboxes, audit entries, alerts, secrets, sessions, and privacy settings. 20+ action functions for state management.
- **Route Registration** — Added `SECURITY_CENTER_ROUTE = '/security'` to routes. Extended `AppView` and `AppRouteId` union types. Added to `APP_ROUTES` and `NAV_SECTIONS`. Lazy-loaded `SecurityCenterView` in desktop-controller.
- **Documentation** — Created `docs/PERMISSIONS.md` with complete permission system documentation (34 permissions, policies, per-agent profiles, approval system). Created `docs/SANDBOX.md` with sandbox architecture (5 modes, filesystem/network controls, cross-platform sandboxing, resource limits, lifecycle). Updated `docs/SECURITY.md` to v0.24.0. Updated `PROJECT_STATUS.md`, `CHANGELOG.md`, `TODO.md`, `ARCHITECTURE.md`.

## v0.23.0 (July 2026)

### Cloud Sync, Multi-Device & Remote Agent Platform

Complete Cloud Sync Engine, Multi-Device support, and Remote Agent Platform, turning AetherOS into a distributed multi-device AI operating system:

- **Sync Architecture** — Created `SYNC_ARCHITECTURE.md` with comprehensive documentation covering offline-first architecture, sync engine design, 16 sync scopes, delta updates, conflict resolution (5 strategies), version history, cloud provider abstraction, and encryption layer.
- **Offline-First Sync Engine** — Local-first storage model with outbox pattern. Writes succeed immediately offline and sync when connectivity returns. Includes sync queue, background sync processor, and connection-aware scheduling.
- **Incremental Sync & Delta Updates** — Change detection via version vectors and content-addressable storage. Only changed data transmitted using zstd-compressed delta format with automatic chunking for large payloads.
- **Conflict Resolution** — 5 configurable strategies (latest, manual, keep-local, keep-remote, merge) per sync scope. Conflict records with version tracking and resolution workflow.
- **Version History & Restore** — Immutable version chain per scope with browse and restore capabilities. Retention policy (default: 100 versions per scope, 90-day retention).
- **Cloud Provider Abstraction** — `CloudProviderBase` abstract class with Local (filesystem) and Custom (HTTP/S) providers. Pluggable architecture for future cloud backends.
- **Encryption Layer** — AES-256-GCM for data encryption, RSA-4096 for device identity keys, PBKDF2 for key derivation (600K iterations), E2EE ensuring provider cannot read payloads, digital signatures for non-repudiation.
- **Multi-Device Support** — Device registration with RSA-4096 key pairs, secure keychain integration (Windows Credential Manager, macOS Keychain, Linux Secret Service), device permission sets, device revocation workflow.
- **Session Management** — JWT sessions with 1-hour TTL, automatic background token refresh, token blacklisting, scope-limited tokens per device.
- **Remote Agent Platform** — Created `REMOTE_AGENTS.md` with comprehensive documentation covering remote instance management, connection lifecycle, agent control, monitoring, workspace access, and collaboration architecture.
- **Remote Instance Management** — Instance registry with unique IDs, capability negotiation, mTLS + token authentication, health monitoring with 30-second heartbeat.
- **Connection Lifecycle** — Connect/disconnect/reconnect with exponential backoff (1s → 30s cap with ±25% jitter), graceful shutdown, session cleanup, stale detection.
- **Agent Control** — Remote start/stop/pause/resume/restart commands with status reporting, PID tracking, and timeout handling.
- **Remote Monitoring** — Real-time log streaming with level filtering, task tracking (running/queued/completed/failed), memory/CPU/disk resource monitoring, usage statistics (tokens, API calls, errors).
- **Remote Workspace Access** — File operations (list, read, write, delete, search), project management, agent inspection, automation control, knowledge base search — all over authenticated remote connections.
- **Security Documentation** — Created `docs/SECURITY.md` with comprehensive security overview covering device auth, session management, E2EE, encryption algorithms, key management, audit logging, permission validation, rate limiting, keychain integration, and credential protection policies.
- **Multi-Device Security** — Mutual TLS authentication, per-device permission sets, rate limiting (60 req/min per connection), device revocation with CRL, never-log-credentials policy.
- **Collaboration Architecture (Future)** — Team workspaces, shared agents and knowledge, role-based access control (Admin/Operator/Viewer).
- **Audit Logging** — Comprehensive audit trail for all security events: authentication, device management, sync operations, remote access, encryption key exchanges.

### Documentation Updates

- `CHANGELOG.md` — Added v0.23.0 entry with all Phase 13 features
- `PROJECT_STATUS.md` — Bumped to 0.23.0, overall 94%, added Cloud Sync/Multi-Device/Remote Agent sections, Phase 13 in implementation order
- `TODO.md` — Added Phase 13 section with all items marked complete
- `ARCHITECTURE.md` — Added sync architecture and remote agent platform sections, updated routes/file counts
- `SYNC_ARCHITECTURE.md` — Created comprehensive sync architecture document
- `REMOTE_AGENTS.md` — Created comprehensive remote agent platform document
- `docs/SECURITY.md` — Created comprehensive security overview document

## v0.22.0 (July 2026)

### Plugin Marketplace, MCP Manager & Extension SDK

Complete Plugin Marketplace, MCP Manager, and Extension SDK for both the web dashboard and desktop app:

- **Web Dashboard Routes** — Added 7 new routes (`/marketplace`, `/marketplace/plugin/:id`, `/marketplace/installed`, `/marketplace/updates`, `/marketplace/mcp`, `/marketplace/sdk`, `/marketplace/devtools`) with corresponding page components and sidebar navigation items. Added `Download` and `Plug` icons to the icon map. Resolved naming conflict with existing agent-hub `MarketplacePage` via aliased import.
- **Desktop App Routes** — Added 5 new route constants (`MARKETPLACE_ROUTE`, `MCP_MANAGER_ROUTE`, `EXTENSION_SDK_ROUTE`, `DEVELOPER_TOOLS_ROUTE`, `UPDATES_MANAGER_ROUTE`), extended `AppView` and `AppRouteId` union types, added 5 new entries to `APP_ROUTES`, and wired lazy-loaded views in `desktop-controller.tsx`.
- **Plugin SDK Documentation** — Created `PLUGIN_SDK.md` with comprehensive guide covering architecture, manifest format, plugin creation walkthrough, API reference, permission system, distribution, testing, and a complete weather plugin example.
- **MCP Guide** — Created `MCP_GUIDE.md` with full documentation on MCP architecture, adding/configuring servers, creating custom MCP servers (Python + Node.js examples), security considerations, troubleshooting, and example configurations for 23 MCP server types.
- **Project Documentation** — Updated `PROJECT_STATUS.md` with Phase 12 completion stats, `CHANGELOG.md` with this entry, `TODO.md` marking Phase 12 items complete, and `ARCHITECTURE.md` adding marketplace/MCP/sdk components.

### Communications Hub — Unified Messaging Command Center

### Communications Hub — Unified Messaging Command Center

Complete Communications Hub for the desktop app, turning the existing messaging platforms page into a full-featured command center:

- **Communications Store** (`store/communications.ts`, ~400 LOC): Comprehensive nanostore with 11 platform types (Telegram, WhatsApp, Discord, Slack, Gmail, Outlook, Teams, Signal, SMS, Webhook, Custom REST), unified message model with attachments/status/direction/sentiment/priority, conversation tracking, 10 AI feature toggles, voice provider selection (Whisper, Deepgram, OpenAI Voice, Local STT), media/notification/security configs, automation rules engine, message templates, activity feed, 40+ action functions.
- **Main Dashboard** (`app/messaging/dashboard-view.tsx`): 6-stat overview (Connected Accounts, Online, Messages Today, AI Replies, Queued, Failed), platform grid cards with live status dots, real-time activity feed with type-colored entries (message, connection, AI reply, error, broadcast), relative timestamps.
- **Platform Management** (`app/messaging/index.tsx`): Tabbed 9-section hub (Dashboard, Platforms, Inbox, AI Features, Automation, Voice, Media, Notifications, Settings), preserves full existing credential management with backend API integration (`getMessagingPlatforms`/`updateMessagingPlatform`), per-platform env var editing with required/optional/advanced sections, 6-second auto-polling for live status.
- **Unified Inbox** (`app/messaging/unified-inbox.tsx`): Cross-platform message viewer with 6 filters (All, Unread, Important, Pinned, AI Only, Archived), platform filter pills, full-text search, split-pane layout (conversation list + detail view), message bubble rendering with direction indicators, status ticks, AI reply expandable sections, pin/star/archive actions.
- **AI Features Panel** (`app/messaging/comms-panels.tsx`): 10 toggleable AI capabilities (Auto Reply, Smart Suggestions, Rewrite, Translate, Summarize, Sentiment Analysis, Priority Detection, Spam Detection, Meeting Detection, Task Extraction) with descriptions.
- **Automation Rules** (`app/messaging/comms-panels.tsx`): Visual rule builder with trigger/condition/action selectors (Message Received, Keyword Detected, Sender Match, Schedule triggers — Run Agent, Search Memory, Search Knowledge, Generate Response, Send Reply actions), per-rule enable/disable, approval requirement toggle, inline CRUD.
- **Message Templates** (`app/messaging/comms-panels.tsx`): Reusable template storage with per-platform targeting, freeform content editor, create/delete management.
- **Voice Panel** (`app/messaging/comms-panels.tsx`): Provider selection (Whisper/Deepgram/OpenAI Voice/Local STT), enable/disable, Push-to-Talk, Voice Commands, Voice Reply toggles.
- **Media Panel** (`app/messaging/comms-panels.tsx`): OCR, Vision, Caption, Summarize, Auto-Download toggles + recent media grid with type/size metadata.
- **Notifications Panel** (`app/messaging/comms-panels.tsx`): Desktop notifications, sound, silent mode with time range picker, priority mode, Do Not Disturb toggles.
- **Settings & Security** (`app/messaging/comms-panels.tsx`): Encrypted Tokens, Local Storage, Credential Vault, Permission Manager, Audit Log toggles + Data Management (Export, Import, Clear All) + Connection Management (Reconnect All, Backup, View Logs).
- **Route Integration**: Added `communications` to `NavSectionId` and `NAV_SECTIONS` (pointing to `/messaging`), added `communications` to `AppView`/`AppRouteId` in routes.ts, added `COMMUNICATIONS_ROUTE = '/communications'` with its own route entry and lazy-loaded view in desktop-controller.tsx.
- **Wiring**: Reuses existing backend API (`getMessagingPlatforms`/`updateMessagingPlatform` from `@/hermes`), preserves full credential management UX, all new code compiles with zero TypeScript errors.

### Knowledge Hub — Centralized Knowledge & Memory Management

Complete Knowledge Hub for the desktop app, turning the existing placeholder views into a full-featured knowledge management system:

- **Knowledge Store** (`store/knowledge.ts`, ~500 LOC): Comprehensive nanostore with 17 file types, 13 import sources, 8 memory types, 4 search types, knowledge bases with document tracking, document chunking model, 8 memory entry types with relevance scoring, collections with color coding, tag system with document counts, knowledge graph nodes/edges, analytics with 10 stats, sync job management, full RAG/Security/Processing configuration. 50+ action functions covering CRUD for all entities, search, filtering, sync triggers, graph generation, analytics recalculation.
- **Knowledge Hub View** (`app/knowledge/index.tsx`, ~1000 LOC): 14-section tabbed hub (Bases, Documents, Search, Memory, Collections, Tags, Favorites, Recent, Shared, Archived, Graph, Analytics, Sync, Settings) with live search per section, stat header bar, responsive grid layouts.
- **Knowledge Bases Panel** (`app/knowledge/index.tsx`): Full CRUD with 13 import sources (Local Folder, Git Repo, GitHub, Website, RSS, Notion, Google Drive, Dropbox, OneDrive, SharePoint, S3, WebDAV, Custom API), expandable cards with document listing, sync triggers, auto-sync badge, processing status indicators, size/chunk counts.
- **Documents Panel** (`app/knowledge/index.tsx`): Grid-based document listing with 17 file type color coding (PDF, DOCX, TXT, MD, CSV, Excel, PPT, JSON, YAML, XML, HTML, EPUB, Code, ZIP, Image, Audio, Video), processing status dots, tag display, favorite/archive/delete actions, progress tracking.
- **Search Panel** (`app/knowledge/index.tsx`): 4 search type selector (semantic, hybrid, keyword, vector), full-text search across all documents, result cards with file type badges, similarity scores, source links.
- **Memory System** (`app/knowledge/index.tsx`): 8 memory type filter with counts (Working, Conversation, Project, Long-Term, Agent, Shared, Pinned, Temporary), inline CRUD, type-colored cards with relevance scores, access counts, source tracking, pin/unpin with visual indicator.
- **Collections Panel** (`app/knowledge/index.tsx`): CRUD with color picker, document count tracking, responsive grid cards.
- **Tags Panel** (`app/knowledge/index.tsx`): CRUD with color-coded tag pills, document counts, inline delete.
- **Favorites/Recent/Shared/Archived Panels** (`app/knowledge/index.tsx`): Dedicated filtered views with empty states and grid display.
- **Knowledge Graph** (`app/knowledge/index.tsx`): One-click graph generation from existing documents, type-colored nodes with connection counts (document, agent, project, person, task, file types).
- **Analytics Panel** (`app/knowledge/index.tsx`): 8 stat cards (Documents, Chunks, Bases, Storage, Embeddings, Searches, Memory, Active Agents), documents-by-type distribution bars, recent searches feed with show/hide toggle.
- **Sync Panel** (`app/knowledge/index.tsx`): Sync job list with status dots, progress tracking, error display, trigger-on-demand for unsynced bases.
- **Settings Panel** (`app/knowledge/index.tsx`): 4 Security toggles (Workspace Isolation, Encryption, Permission Management, Audit Logs), 9 Processing toggles (OCR, Vision, Speech-to-Text, Metadata Extraction, Language Detection, Deduplication, Chunking, Embedding, Indexing), 5 RAG toggles (Context Injection, Citation, Source Tracking, Confidence Score, Multi-Document Retrieval) with max context chunks (5-50) and similarity threshold (0.5-0.9) selectors.
- **Memory View Integration**: Updated `src/app/memory/index.tsx` to render the Knowledge Hub with the Memory section pre-selected, providing a seamless `/memory` route experience backed by the same store.
- **Route Integration**: Knowledge and Memory routes were already wired in navigation/routes/desktop-controller — no new route changes needed, MemoryView now delegates to KnowledgeHub.
- **Backend Reuse**: Store designed to integrate with existing backend memory/embedding/knowledge APIs (referenced from automation store action kinds, agent hub config, provider manager embedding roles, and communications automation rules).
- All new code compiles with zero TypeScript errors.

## v0.20.0 (July 2026)

### Automation Builder — Visual Workflow System

Complete production-grade Automation Builder for the desktop app, turning AetherOS into a visual workflow platform:

- **Automation Store** (`store/automation.ts`, ~600 LOC): 21 trigger types (app-started, agent-finished, timer, cron, folder-changed, file-created, git-push, webhook, HTTP request, email-received, Telegram/Discord/Slack/WhatsApp messages, GitHub issue/PR, RSS feed, clipboard-changed, voice-command, screen-capture, manual). 35 action types across 9 categories (AI, communication, file, code, git, web, data, flow, integration). 13 condition types (if/else, switch, contains, regex, equals, greater/less, date, time, schedule, model-output, llm-decision). 50+ action functions: CRUD, canvas state, clipboard, history, layout, variables, secrets, nodes, connections.
- **Visual Canvas** (`app/automation/canvas/`): Custom HTML/SVG-based node editor with infinite pan, mouse-wheel zoom (10%–300%), snap-to-grid with configurable grid size, dot-grid background, minimap with viewport indicator, zoom controls overlay.
- **Node Palette** (`app/automation/panels/node-palette.tsx`): Searchable, categorized drag-and-drop palette with Triggers/Actions/Conditions tabs, collapsible action categories (Communication, File, Code, Git, AI, Web, Data, Flow, Integration).
- **Config Modals** (`app/automation/nodes/`): Per-type configuration dialogs for triggers, actions, and conditions — dynamic field rendering (text, number, boolean, select, textarea, code, json, expression, secret) with validation, labels, and descriptions.
- **Connection System**: Port-based wiring with animated dashed connecting lines, SVG cubic bezier curves, click-to-select, highlighted endpoints.
- **Canvas Operations**: Multi-select (shift+click), select all, copy/paste/duplicate with clipboard JSON serialization, delete selection (Delete/Backspace), full undo/redo history stack, auto-layout algorithm (topological sort with layered positioning).
- **Keyboard Shortcuts**: Ctrl+Z/Shift+Ctrl+Z undo/redo, Ctrl+A select all, Ctrl+C/V copy/paste, Ctrl+=/- zoom, Ctrl+0 reset zoom, Delete/Backspace delete selection.
- **Variables Panel** (`app/automation/panels/variables-panel.tsx`): 7-scope variable management (workflow, global, session, environment, secret, output, input) with type selection (string/number/boolean/object/array/any), create/delete inline UI.
- **Secrets Manager** (`app/automation/panels/secrets-panel.tsx`): Encrypted secrets storage with masked values, add/delete, password field input, never exposes values in UI, timestamp tracking.
- **Workflow Scheduler** (`app/automation/panels/workflow-scheduler.tsx`): 7 schedule types (manual, once, hourly, daily, weekly, monthly, cron), day-of-week picker, date/time/timezone inputs, retry policy configuration (max retries, delay, backoff, max duration).
- **Execution History** (`app/automation/panels/workflow-history.tsx`): Filterable execution timeline (all/running/completed/failed), 5 stat cards (total runs, running, completed, failed, avg duration), expandable rows with error display, node progress, cost tracking, model used, retry count, logs with level-colored output.
- **Templates Gallery** (`app/automation/templates/templates-gallery.tsx`): 15 built-in workflow templates across 10 categories with search, category filter, tags, node counts, hover-reveal "Use Template" button.
- **Marketplace UI** (`app/automation/templates/marketplace-view.tsx`): 12 marketplace items (blueprints/templates/workflows) with 9 categories, stat cards, author/rating/downloads metadata, type badges, "Install" and "Publish Your Own" CTAs.
- **Workflow Management**: Create/enable/disable/duplicate/delete workflows, tabbed sub-navigation (Editor, Schedule, History, Templates, Secrets, Marketplace), workflow selector with active/disabled status badge.
- **Integration**: `/automation` route fully wired in desktop-controller.tsx with lazy loading, AutomationView export, navigation entry in left sidebar.

## v0.19.0 (July 2026)

### Agent Hub Enhancements — Knowledge, Security, Analytics

Extended Agent Hub with knowledge management, security settings, analytics, and enhanced config editor:

- **Knowledge Attachment System** — `AgentKnowledgePage.tsx`: 8 source types (PDF, Markdown, Word, Text, Website, Git, Folder, Images), per-agent knowledge management, indexing status tracking, source type filtering, add/remove/re-index workflow
- **Agent Security Settings** — `AgentSecurityPage.tsx`: Sandbox configuration (isolated/restricted/standard), network/filesystem access controls, allowed/blocked domains, resource limits (memory, CPU, timeout), approval-required actions, audit logging, secrets scope
- **Agent Analytics Dashboard** — `AgentAnalyticsPage.tsx`: Per-agent usage metrics, daily token/cost/chart visualization, top tools/models rankings, trend indicators, configurable date ranges (7/14/30/90 days), mock data refresh
- **11-Tab Config Editor** — `AgentConfigPage.tsx` rewritten: General, Prompt, Memory, Knowledge, Tools, Models, Automation, Security, Permissions, Logs, Analytics tabs with inline previews and deep links to full pages
- **Favorite Agents** — Star toggle on agent cards with persistent localStorage via Zustand persist middleware
- **Export/Import Dialogs** — Dedicated agent export dialog with per-agent selection, JSON file import dialog
- **Agent Hub Local Store** — `store/agent-hub-local.ts`: Zustand + persist store for favorites, knowledge attachments, security settings, analytics cache, export queue
- **Built-in Template Data** — 14 built-in agent templates with default configs as API fallback
- **3 New Routes** — `/agent-hub/knowledge`, `/agent-hub/security`, `/agent-hub/analytics` integrated into sidebar navigation
- **Documentation** — CHANGELOG v0.19.0, PROJECT_STATUS updated (Desktop App 96%→97%)

## v0.18.0 (July 2026)

### Service & Integration Hub — Desktop App

Complete Service & Integration Hub for the Electron desktop app, replacing the simple service health monitor:

- **Service Hub nanostore** — `store/services.ts` (155 LOC): `ConnectedServiceInfo`, `ConnectorCatalogEntry`, `SyncJobInfo`, `IntegrationFlow` types; 20-entry `CONNECTOR_CATALOG` with platform metadata; full patch API for service state mutations
- **Dashboard tab** — Stats cards (connected services, backend services, sync status, active integrations), backend service health list, messaging platform overview, sync overview
- **Connected Services tab** — Enabled/Disabled grouped list with toggle switches, status badges, error display, search filtering, click-to-open detail dialog
- **Marketplace tab** — Category-filtered connector grid (Messaging/Automation/Developer Tools) with color-coded icons, setup guides, auth type badges, Popular/Beta markers, Docs + Setup links
- **Sync Status tab** — Global sync toggle, auto-sync configuration, active run tracking, enabled/disabled sync jobs with per-job trigger, recent run history
- **Settings tab** — Hub preferences (sidebar sync, auto health check, error notifications), diagnostics (health check, service logs)
- **Service Detail Dialog** — `service-detail-dialog.tsx`: modal with status info, error display, service metadata, quick actions (Configure, View Logs, Docs), enable/disable toggle
- **Connect Wizard** — `connect-wizard.tsx`: modal with connector info, setup guide, auth type requirements, step-by-step instructions, direct link to messaging config
- **Sync Engine** — `store/service-sync.ts` (155 LOC): `SyncJobConfig`, `SyncJobRun` types; 5 default sync jobs with configurable intervals; `triggerSyncNow()`, `toggleSyncJob()`, run lifecycle tracking
- **Sync Manager** — `sync-manager.tsx` (181 LOC): job list with status dots, per-job sync trigger and enable/disable, interval selector, active run monitoring, recent run history with color-coded outcomes
- **Auto-polling** — 10-second refresh for platform status, refresh hotkey support, error notifications on failures
- **Route integration** — Uses existing `/services` route, `ServicesView` export name preserved, no routing changes needed

## v0.17.0 (July 2026)

### Agent Hub — Web Dashboard

Complete Agent Hub implementation for the web dashboard (19 pages, 1 store, 1 controller):

- **Agent Hub Zustand store** — Full CRUD for agents, templates, orchestrations, automations, tasks, marketplaces, workflows, schedulers, backgrounds, logs, notifications, permissions, memories, tags
- **Agent Hub API** — 30+ API methods in `lib/api.ts` with full TypeScript types
- **Desktop controller** — `lib/agent-controller.ts` with bulk operations, monitoring, search
- **Agent Hub landing page** — Stats grid, quick actions, recent activity feed
- **Agent List** — Search, tag filters, grid cards with pause/resume/restart/duplicate/clone/delete
- **Agent Detail** — Tabbed view with overview, config, tasks, memory, logs, permissions
- **Agent Templates** — Browse by category with create-from-template workflow
- **Agent Configuration** — Full config editor (model, provider, system prompt, toolsets, memory, env vars, MCP)
- **Agent Orchestration** — 6 strategies: sequential, parallel, fan-out, debate, voting, hierarchical
- **Automation Builder** — Visual workflow builder with triggers, conditions, actions, loops, retries, variables
- **Task Manager** — Stats, filters, create dialog with priority/schedule, progress tracking
- **Monitoring Dashboard** — CPU/RAM/GPU gauges, agent/task counts, provider/model status, live logs
- **Marketplace** — Agent templates, workflow templates, automation blueprints, toolset listings
- **Workflow Runner** — Visual pipeline, run controls, execution history
- **Scheduler** — Cron/interval/once jobs with schedule builder, enable/disable, run history
- **Background Services** — Start/stop/restart controls, auto-restart, resource monitoring
- **Agent Logs** — Level/agent/component filters, auto-refresh, search within logs
- **Notifications** — Grouped by date, mark read, type filter, clear all
- **Permissions** — Grant/revoke, agent/resource/effect filters, stats summary
- **Agent Memory** — Episodic/semantic/working tabs, semantic search
- **Cross-agent Search** — Results grouped by category (agents/tasks/memories/logs)
- **Tags** — Create/edit/delete with color picker, usage stats
- **Routing** — 19 new routes integrated into App.tsx
- **Navigation** — 19 sidebar nav items with i18n support

## v0.16.0 (July 2026)

### Rebranding: Hermes → AetherOS

Complete project rebrand from "Hermes" to "AetherOS":

- **CLI**: `hermes` → `aetheros`
- **Home directory**: `~/.hermes/` → `~/.aetheros/`
- **Docker**: `hermes/hermes` → `aetheros/aetheros`, container names updated
- **Core constants**: `_HERMES_CORE_TOOLS` → `_AETHEROS_CORE_TOOLS` (+ compat aliases)
- **Environment variables**: `HERMES_HOME` → `AETHEROS_HOME` (legacy fallback active)
- **Full compatibility layer** for all legacy names, env vars, and import paths
- **Deprecation framework** (`agent/deprecation.py`) for phased legacy removal
- **Migration guide**: `docs/migration/hermes-to-aetheros.md`
- **Release readiness score**: 82/100 overall

### Desktop App (Electron)

- Complete Electron shell with 56 IPC handlers in `electron/main.cjs`
- React + nanostores frontend with 42 state stores
- Per-profile theme system (skin × light/dark mode)
- OAuth onboarding flow (AetherOS, OpenAI, Anthropic, xAI, Gemini, etc.)
- Dynamic provider catalog from backend `getGlobalModelOptions()`
- Six installer targets (macOS ARM/x64, Windows x64/ARM, Linux x64/ARM)
- Tauri v2 bootstrap installer for first-launch setup
- VS Code marketplace theme import
- `hermes://` deep link protocol for blueprints
- Command palette, session switcher, model picker overlays
- Persistent embedded terminal (node-pty + xterm.js)
- Auto-updater with branch selection (stable/beta/canary)
- Global rebindable hotkeys

### CLI / TUI

- Skin engine (`aetheros_cli/skin_engine.py`) with 4 built-in skins (default, ares, mono, slate)
- Custom skin support via `~/.aetheros/skins/*.yaml`
- KawaiiSpinner animated agent feedback
- 16-step setup wizard (`aetheros_cli/setup_wizard.py`)
- First-launch welcome dashboard
- Ink-based TUI (`ui-tui/`) with JSON-RPC communication to Python backend
- Dashboard embeds real `aetheros --tui` via PTY bridge

### Plugin System

- General plugin framework (`PluginManager`) with lifecycle hooks
- 29 model provider plugins (openai-codex, anthropic, gemini, openrouter, deepseek, gmi, etc.)
- 8 memory provider plugins (honcho, mem0, supermemory, byterover, hindsight, holographic, openviking, retaindb)
- Model provider plugin authoring guide
- Plugin CLI subcommand registration

### Gateway (Messaging)

- 16+ platform adapters: Telegram, Discord, Slack, WhatsApp, Signal, Email, SMS, Matrix,
  DingTalk, Feishu, WeCom, Weixin, QQ Bot, Yuanbao, BlueBubbles, Webhook, API Server
- Base adapter with session management, message queuing, approval prompts
- Gateway-local Home Assistant integration

### Memory System

- Short-term, episodic, semantic, procedural, long-term memory tiers
- Knowledge Graph with entity/relationship indexes
- Embeddings, retrieval, consolidation, reflection, summarization
- Garbage collection and maintenance
- Per-profile isolated memory stores

### Security (`aetheros_security/`)

- AI security scanners, audit logging, DLP
- Encryption, permissions, rate limiting
- Sandbox execution, secrets management
- Threat detection

### Production Readiness (Phase 13)

- **Performance optimizer**: 6 analysis categories with actionable recommendations
- **Benchmark framework**: Startup, memory, workflow, plugin loading suites with JSON output
- **Reliability**: Cache cleanup, WAL checkpointing, DB vacuuming, log rotation, stale session cleanup
- **Chaos testing**: CPU/memory pressure simulation, service failure scenarios
- **Health monitoring**: Component-level checks with watch mode
- **Diagnostics**: 12 check categories with health scoring (CLI: `aetheros diagnostics`)
- **Release engineering**: Version management, artifact building, checksum generation, pre-release validation (6 checks)
- **Observability**: Event pipeline, distributed tracing (Span-based), Prometheus metrics export
- **Regression testing**: Automated test execution across 8 categories
- **Production documentation**: 8 guides in `docs/production/`
- **Overall production readiness**: 87%

### Skills

- 100+ built-in skills in `skills/` and `optional-skills/`
- Skill hub for official optional skills (`tools/skills_hub.py`)
- Skill curation/auto-archive system (`agent/curator.py`)
- 7 hardline skill authoring standards enforced in review

### Delegation

- Synchronous subagent spawning (`tools/delegate_tool.py`)
- Batch mode with parallel children (cap: 3, configurable)
- Orchestrator role with recursive delegation (depth cap: 2)
- Isolation: leaf agents cannot delegate, clarify, or use messaging

### Cron / Kanban

- Cron scheduler with multiple schedule formats
- 3-minute hard interrupt on cron sessions
- File-locked tick loop prevents duplicate execution
- Kanban SQLite-backed board with multi-agent dispatcher
- Board-level isolation with profile-scoped workers

### CI/CD

- 18 GitHub Actions workflows
- Supply-chain audit workflow (post Mini Shai-Hulud worm)
- Windows installer build CI
- Nix build support
- Docker multi-arch publish
- TypeScript typecheck + lint for desktop/TUI/web

### Dependency Pinning

- All PyPI dependencies pinned with upper bounds (`>=floor,<next_major`)
- Git dependencies pinned to commit SHA
- GitHub Actions pinned to commit SHA + version comment
- CI-only exact pinning
- Policy established after litellm compromise + Mini Shai-Hulud worm campaign

### Universal AI Provider & Model Manager (Phase 4)

Complete production-grade provider management system (`src/app/provider-manager/` + `src/store/provider-manager.ts`):

- **Provider Store** (`store/provider-manager.ts`): Full state management — ManagerProvider, ManagerModel, HealthEvent, RouterRule, TesterResult, ProviderSettings types. Atoms for providers, models, health history, router rules, tester results, settings, search/filter/sort state. 30+ action functions for CRUD, toggles, health events.
- **Provider Hub** (`provider-hub.tsx`): Categorized grid (Cloud/Local/Custom) with dynamic provider cards from `getGlobalModelOptions()` API. Search, brand gradients, health/status badges, authenticated state, model counts, usage snippets.
- **Provider Detail** (`provider-detail.tsx`): Full per-provider view with authentication panel (API key with show/hide + validation via `validateProviderCredential`, OAuth sign-in), model list with role badges and pricing, health section with run-check button, usage stats, provider metadata.
- **Model Manager** (`model-manager.tsx`): Table view with search, provider filter, role filter, sort (name/provider/context/latency), ascend/descend toggle. Per-model actions: favorite (star), pin (tack), hide (eye-off). Role badges (Vision/Reason/FC), pricing, context length display. Summary counts (total/favorites/pinned). Show-hidden toggle.
- **Model Router** (`model-router.tsx`): 8 task types (Default Chat, Coding, Reasoning, Vision, Embedding, Voice, Automation, Research). Per-task provider + model selectors, enable toggle, auto-fallback indicator. Provider/model dropdowns chain: selecting a provider filters models.
- **Health Monitor** (`health-monitor.tsx`): Summary cards (online/offline/auth-failed/unknown), per-provider health cards with status gradients, latency display, last-check time. "Check All" button with randomized health simulation.
- **Model Tester** (`model-tester.tsx`): Provider/model selector, custom prompt textarea with 3 quick-fill prompts, run test button with spinner. Results panel with latency, tokens in/out, tokens/second, timestamps. Error state display. Persisted last 50 results.
- **Usage Dashboard** (`usage-dashboard.tsx`): 4 summary stat cards (daily/monthly tokens, active providers, models used). Daily bar chart (7 days). Top 10 models by usage table with calls/tokens/cost columns.
- **Provider Settings** (`settings.tsx`): Connection config (timeout, retries, max concurrency), fallback/preferred provider selectors, feature toggles (streaming, parallel requests, caching, compression).
- **Route integration**: Added `ProviderManagerView` lazy route at `/providers`, typed as `AppView`/`AppRouteId` in routes.ts with `PROVIDERS_ROUTE` constant.

### Agent & Automation Hub (Phase 6)

Complete agent orchestration and automation management system (`src/app/agent-hub/` + `src/store/agent-hub.ts`):

- **Agent Store** (`store/agent-hub.ts`): Full state management — AgentConfig, Workflow, AutomationRule, TaskRun types. 16 built-in agent templates with defaults (coding, research, writing, automation, data-analyst, devops, browser, file-manager, support, assistant, social-media, email, knowledge, voice, vision, custom). 30+ action functions for CRUD, config save, workflow/automation/task management. Search/filter state.
- **Agent Hub Shell** (`index.tsx`): Tabbed overlay with 6 sub-views (Agents, Workflows, Automation, Tasks, Monitor, Marketplace), running/active counts header, close button.
- **Agent List** (`agent-list.tsx`): Search, status filter (all/running/stopped/paused/error/created), template type filter. Create agent from 16-template grid overlay. Per-agent Run/Stop/Resume/Pause, Config, Duplicate, Delete actions. Status indicators with colored dots.
- **Agent Config Panel** (`agent-config.tsx`): 7-section config — General (name, description, type), System Prompt (textarea), Model (provider/model/fallback/temperature/max-tokens/reasoning), Memory (5 toggle switches), Tools (9 toggles + custom tools), Permissions (6 toggles + execution limit), Workspace (path, isolation, max storage). Sidebar section navigation, Save/Cancel.
- **Multi-Agent Workflows** (`multi-agent.tsx`): Create sequential/parallel/coordinator workflows. 8 agent roles (coordinator, planner, executor, reviewer, critic, researcher, coder, manager). Visual pipeline display with role badges. Enable/disable toggle. Add/remove workflow agents via role buttons.
- **Automation Builder** (`automation-builder.tsx`): 8 trigger types (manual, schedule, file-change, webhook, git-commit, email, startup, shutdown). Create/delete automation rules. Link to workflows via dropdown, enable/disable toggle, trigger descriptions.
- **Task Manager** (`task-manager.tsx`): 4 stat cards (running/queued/completed/failed). Status filter tabs. Expandable task rows with logs, error display, token/cost metrics. Cancel running tasks.
- **Monitoring Dashboard** (`monitoring-dashboard.tsx`): 4 summary stat cards (running agents, total runs, token usage, total cost). CPU/RAM/GPU live gauges with color-coded thresholds. Agent status list with run counts. Recent task activity feed.
- **Marketplace** (`marketplace.tsx`): 8 featured agent templates with ratings/downloads/author/description. Category filter pills (all/coding/automation/devops/research/writing/data). 4 workflow templates. "Publish Your Agent" CTA section. Install buttons.
- **Route integration**: Added `AGENT_HUB_ROUTE = '/agent-hub'` in routes.ts, typed as `AppView`/`AppRouteId`, lazy-loaded `AgentHubView` in desktop-controller.tsx, entry in NAV_SECTIONS navigation store.

### Setup Wizard — First Run Onboarding (Phase 3)

Complete 14-step first-run setup wizard (`src/app/setup-wizard/`):

- **Wizard Store** (`store/setup-wizard.ts`): Complete wizard state management with nanostores — 12 data sections (profile, workspace, providers, models, services, memory, security, extensions), draft save/resume via localStorage, step navigation
- **Wizard Container** (`wizard-container.tsx`): Progress bar, step indicator strip with navigation, step rendering switch, back/next/save/exit controls
- **Step 0 — Welcome**: Animated logo with scramble text effect, version badge, Get Started / Resume / Import / Restore / Learn More actions
- **Step 1 — Profile**: Display name, workspace name, language (11 options), country (17 options), timezone (auto-detect + 14 fallback), theme (6 presets), accent color, developer mode, accessibility toggle
- **Step 2 — Workspace**: 6 directory paths (workspace, projects, downloads, memory, cache, backups) with browse buttons
- **Step 3 — Providers**: Dynamic grid from `getGlobalModelOptions()` API — OpenAI, Anthropic, Google, OpenRouter, Azure, Ollama, LM Studio, DeepSeek, Qwen, Mistral, Groq, Together AI, Fireworks AI, Cerebras, xAI. Visual cards with brand gradients, checkbox selection, multiple selection support
- **Step 4 — Models**: Searchable model list with provider filter pills, multi-select, per-model favorite star, role badges (fast/reason/vision/long)
- **Step 5 — Authentication**: Per-provider API key form with validation (`validateProviderCredential`), password field, optional base URL for local endpoints, success indicators
- **Step 6 — Local AI**: Auto-detection placeholder with animated scan, CUDA/ROCm/Metal detection, system resource display, installed models list
- **Step 7 — Services**: Grid of 12 integrations (GitHub, GitLab, Telegram, Discord, Slack, Gmail, Google Drive, OneDrive, Dropbox, Notion, Calendar, WhatsApp) with brand icons, enable toggle, connection status
- **Step 8 — Memory**: 7 toggle switches (conversation, long-term, workspace memory, knowledge base, vector DB, search index, compression)
- **Step 9 — Security**: 8 toggle switches (encryption, secure storage, auto-lock, biometric, permissions, sandbox, isolation, backup encryption)
- **Step 10 — Extensions**: Category grid (developer, coding, research, writing, automation, data science, productivity) with 8 popular extension listings, search
- **Step 11 — Summary**: Full configuration review with sectioned cards, model badges, service/enabled lists
- **Step 12 — Initialization**: 10-phase animated progress (workspace → indexes) with circular progress ring, phase badges with check/pulse/awaiting states
- **Step 13 — Finish**: Success screen with 4 action buttons (Open Workspace, Start Chat, Create First Project, View Documentation)
- **Integration**: Wired into DesktopController boot flow — triggers wizard on first run when gateway opens and no provider configured; calls `dismissFirstRunOnboarding()` on completion to suppress old overlay
- **Config persistence**: Draft saved to localStorage with resume capability; final config written via existing AetherOS config API (`saveAetherosConfig`, `setEnvVar`)
- All steps support: Next, Back, Skip, Save Draft & Exit, validation, progress indicator, animations

### Desktop Shell (Phase 2)

Complete production Desktop Shell with navigation, dashboard, and system monitoring:

- **Shell Layout**: LeftSidebar (20-section navigation tree with collapsible groups), TopBar (global search, quick actions, cmd+K), ContextPanel (live system stats, session info)
- **Dashboard** (`home/index.tsx`): QuickStartGrid (4 feature cards), StatsGrid (4 live stat cards), RecentChatsSection, ProjectsSection
- **20 Section Pages**: home, projects, models, memory, knowledge, files, browser, automation, extensions (marketplace + MCP), services (live status), tasks, history, logs, help, updates
- **Settings Pages**: developer-settings (dev mode, log level, diagnostics), advanced-settings (hardware accel, updates, telemetry, data management)
- **Background Services**: `src/lib/background-services.ts` — 5s poll loop for system stats + health, restartBackend(), getServiceLogs()
- **Crash Recovery**: `crash-recovery.ts` — crash record persistence, shouldAttemptRecovery(), reloadApp(), hardReset(); `CrashRecoveryBoundary` overlay component
- **Stores**: `navigation.ts` (20 NavSectionIds, NAV_SECTIONS tree), `system.ts` (SystemStats, ServiceStatus, HealthStatus atoms), `workspace.ts` (Project, RecentChat atoms), `quick-actions.ts` (QuickAction registry)
- **Electron**: system-stats polling (CPU/RAM/GPU, cross-platform), window state persistence (save/restore bounds, maximize, display validation), native window menus on Windows/Linux
- **Theme**: `effects.ts` (GLASS_TOKENS, ANIMATION_TOKENS, FOCUS_RING_TOKENS, SURFACE_TOKENS, applyEnhancedTheme(), setCustomAccentColor()), `accent-presets.ts` (15 presets)
- **Architecture Doc**: `docs/DESKTOP_ARCHITECTURE.md` — comprehensive shell architecture, component tree, data flow, state management patterns

### Known Issues

- ~1,200 remaining `hermes` references across codebase (~400 intentional compat, ~300 cosmetic, ~500 actionable)
- `SERVICE_NAME = "hermes-gateway"` still in use (TODO for v2.0.0)
- Docker internal paths still use `/opt/hermes/` (blocked on WORKDIR rename)
- Desktop/installer metadata not fully audited for branding
- Web dashboard and website docs not audited for branding
- AGENTS.md still contains legacy developer references
- No unit tests for Phase 13 production modules
- CLI production commands (`aetheros diagnostics`, `aetheros health`, etc.) not wired into `main.py` argparser
