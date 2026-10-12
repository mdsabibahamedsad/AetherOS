# Frontend Test Coverage Report

**Generated:** July 11, 2026
**Target:** Web Dashboard (`web/`)

---

## Executive Summary

The web dashboard (`web/`) has **zero existing tests** — no `.test.tsx` or `.test.ts` files were found. This is a significant gap for a project with 20+ pages, dozens of components, hooks, stores, and utilities.

The desktop app (`apps/desktop/`) has **83 test files** with reasonable coverage of its components, hooks, stores, and utilities.

---

## Dashboard Coverage Analysis (web/)

### File Inventory

| Category | Count | Files With Tests | Coverage |
|----------|-------|-----------------|----------|
| Pages | 20+ | 0 | 0% |
| Components | ~30+ | 0 | 0% |
| Hooks | ~15 | 0 | 0% |
| Stores/Contexts | ~10 | 0 | 0% |
| Lib/Utilities | ~20 | 0 | 0% |
| i18n | ~15 locale files | 0 | 0% |
| Plugins | ~5 files | 0 | 0% |
| Themes | ~5 files | 0 | 0% |

### Page Inventory (web/src/pages/)

| Page | Exists | Tests |
|------|--------|-------|
| AnalyticsPage | ✅ | ❌ |
| ChannelsPage | ✅ | ❌ |
| ChatPage | ✅ | ❌ |
| ConfigPage | ✅ | ❌ |
| CronPage | ✅ | ❌ |
| DocsPage | ✅ | ❌ |
| EnvPage | ✅ | ❌ |
| FilesPage | ✅ | ❌ |
| LogsPage | ✅ | ❌ |
| McpPage | ✅ | ❌ |
| ModelsPage | ✅ | ❌ |
| PairingPage | ✅ | ❌ |
| PluginsPage | ✅ | ❌ |
| ProfileBuilderPage | ✅ | ❌ |
| ProfilesPage | ✅ | ❌ |
| SessionsPage | ✅ | ❌ |
| SkillsPage | ✅ | ❌ |
| SystemPage | ✅ | ❌ |
| WebhooksPage | ✅ | ❌ |

### Component Inventory (web/src/components/)

Key components identified:
- Backdrop
- SidebarFooter
- SidebarStatusStrip
- AuthWidget
- ProfileSwitcher
- ProfileScopeBanner
- LanguageSwitcher
- ThemeSwitcher
- Sidebar components

All without tests.

### Test Infrastructure Considerations

To add tests, the dashboard needs:

1. **Test runner configuration** — vitest (used by ui-tui, available in workspace)
2. **Component test utilities** — React Testing Library
3. **Mock setup** — for:
   - API calls (`lib/api.ts`)
   - Plugin hooks (`plugins/`)
   - i18n (`i18n/`)
   - Theme (`themes/`)
   - Router context
   - Gateway connection
4. **Coverage reporting** — vitest `--coverage` with v8 or istanbul

---

## Desktop App Test Status (apps/desktop/)

### Test Files Found: 83

| Category | File Count | Examples |
|----------|-----------|----------|
| Chat/Composer | ~15 | `use-composer-actions`, `rich-editor`, `message-utils` |
| Components | ~20 | Markdown, streaming, tool approval, shell |
| Stores | ~10 | Sessions, panes, prompts, composer state |
| Lib | ~20 | i18n, filesystem, keybindings, gateway client |
| Settings | ~5 | Settings config, theme installation |
| Hooks | ~10 | Various |

### Desktop Test Gaps

| Area | Exists | Tests |
|------|--------|-------|
| Electron main process | ✅ | ❌ |
| Preload bridge | ✅ | ❌ |
| Theme system | ✅ | ✅ (limited) |
| Profiles | ✅ | ❌ |
| Session management UI | ✅ | ❌ |

---

## Recommended Test Plan (Dashboard)

### Phase 1: Infrastructure (1-2 days)
1. Add vitest config to `web/vite.config.ts` 
2. Add `@testing-library/react` and related packages
3. Create test setup file with mocks for:
   - API client (`lib/api.ts`)
   - i18n context
   - Router context  
   - Theme context
4. Create test utilities and helpers

### Phase 2: Utilities (2-3 days)
1. `lib/api.ts` — unit tests for API client
2. `lib/utils.ts` — unit tests for utility functions
3. `i18n/` — unit tests for i18n system
4. `themes/` — theme logic tests

### Phase 3: Components (3-5 days)
1. `Sidebar` — render, nav, collapse
2. `AuthWidget` — login/logout states
3. `LanguageSwitcher` — language toggle
4. `ThemeSwitcher` — theme toggle
5. `ProfileSwitcher` — profile selection
6. `Backdrop` — render states
7. `SidebarStatusStrip` — status display

### Phase 4: Pages (5-7 days)
1. `SessionsPage` — session list, create, delete
2. `ConfigPage` — config display and editing
3. `SkillsPage` — skill browse and install
4. `CronPage` — cron job management
5. `FilesPage` — file browse
6. `ModelsPage` — model selection
7. `ChatPage` — chat UI and PTY bridge
8. Other pages

### Phase 5: Hooks and Contexts (2-3 days)
1. `useSidebarStatus`
2. `useSystemActions`
3. `useProfileScope`
4. Various contexts

---

## Timeline Estimate

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: Infrastructure | 1-2 days | 1-2 days |
| Phase 2: Utilities | 2-3 days | 3-5 days |
| Phase 3: Components | 3-5 days | 6-10 days |
| Phase 4: Pages | 5-7 days | 11-17 days |
| Phase 5: Hooks | 2-3 days | 13-20 days |

**Total estimate**: 2-3 weeks for a single developer focused on testing.

### Coverage Targets

| Phase | Target Coverage |
|-------|----------------|
| After Phase 2 | ~20% (utilities, i18n) |
| After Phase 3 | ~40% (utilities + components) |
| After Phase 4 | ~70% (all pages + utilities + components) |
| After Phase 5 | ~80-85% |

Reaching 90%+ would require comprehensive integration tests for the complex pages (Chat, Sessions, Cron) which are harder to mock.

---

## Blocking Items

1. **No test runner configured** for `web/` — vitest exists in workspace but not set up for dashboard
2. **No React Testing Library** — needs to be added to `web/package.json`
3. **Complex mock surface** — PTY bridge, WebSocket gateway, and plugin hooks are difficult to test
4. **Design system dependency** — `@nous-research/ui` DS components need test rendering support
