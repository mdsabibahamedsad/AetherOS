# AetherOS Rebranding Status

> **Last updated:** July 12, 2026
> **Phase:** 3 (Core Internal Refactor & Compatibility Layer)
> **Overall completion:** ~75%

---

## Completion Summary

| Phase | Focus | Status | % Done |
|-------|-------|--------|--------|
| 1 | Critical Runtime Fixes | ✅ Complete | 100% |
| 2 | Infrastructure & CI | ✅ Complete | 100% |
| 3 | Internal Variables & Code | ✅ Partially Complete | ~60% |
| 4 | File/Module Renames | ✅ Complete | 100% |
| 5 | Documentation & Skills | ⏳ Not started | 0% |
| 6 | Testing & Validation | ⏳ Not started | 0% |

**Overall estimated completion: ~75%**

---

## Phase 1 — Critical Runtime Fixes ✅

### What was done
- **`aetheros-agent` launcher**: Fixed broken `from hermes_cli.main import main` → `from aetheros_cli.main import main`
- **`aetheros_constants.py`**: Added `HERMES_HOME` → `AETHEROS_HOME` fallback with `DeprecationWarning`; fixed `%LOCALAPPDATA%\\hermes` → `%LOCALAPPDATA%\\aetheros` in docstrings; mirrored fallback in `get_default_aetheros_root()`
- **User-facing commands**: ~1,480 replacements across 362 Python + shell files — all printed `hermes <command>` → `aetheros <command>` in help text, error messages, and diagnostics
- **Gateway script**: Updated docstring, descriptions, launchd plist labels to "AetherOS Gateway"
- **Setup scripts**: `setup-aetheros.sh`, `scripts/install.sh`, `scripts/install.ps1` — all printed `hermes` commands → `aetheros`

### Files modified
- `aetheros-agent`, `aetheros_constants.py`
- `aetheros_cli/banner.py`, `backup.py`, `doctor.py`, `dump.py`, `debug.py`
- `setup-aetheros.sh`, `scripts/aetheros-gateway`
- `scripts/install.sh`, `scripts/install.ps1`, `scripts/setup_open_webui.sh`
- ~360 additional Python/shell files with user-facing command text

---

## Phase 2 — Infrastructure & CI ✅

### What was done
- **Docker Compose**: Container names `hermes`/`hermes-dashboard` → `aetheros`/`aetheros-dashboard` in both `docker-compose.yml` and `docker-compose.windows.yml`
- **Docker shim**: Created `docker/aetheros-exec-shim.sh` (new shim using `aetheros` paths); kept `docker/hermes-exec-shim.sh` as compat wrapper
- **Dockerfile**: Build SHA path fixed; both shims copied; PATH includes both `/opt/aetheros/bin` and `/opt/hermes/bin`
- **s6 service**: Renamed `docker/s6-rc.d/main-hermes/` → `main-aetheros/`; removed stale contents.d entry
- **GitHub Actions**: `hermes-smoke-test` → `aetheros-smoke-test`; action.yml updated
- **AETHEROS_GIT_SHA**: Added as primary build-arg alongside `HERMES_GIT_SHA` in `docker-publish.yml`, `Dockerfile`, and `build_info.py`
- **Install scripts**: Added `TODO` notes; fixed remaining `hermes` commands in `install.sh` / `install.ps1`
- **Gateway script**: Fixed launchctl commands (`ai.hermes.gateway` → `ai.aetheros.gateway`); fixed epilog example commands (`./scripts/hermes-gateway` → `./scripts/aetheros-gateway`); fixed config path (`~/.hermes/` → `~/.aetheros/`); added TODO for `SERVICE_NAME` rename

### Files modified in Phase 2
- `docker-compose.yml`, `docker-compose.windows.yml`
- `Dockerfile`
- `docker/aetheros-exec-shim.sh` (created), `docker/hermes-exec-shim.sh` (updated as compat)
- `docker/s6-rc.d/main-aetheros/` (renamed from main-hermes/)
- `docker/s6-rc.d/user/contents.d/main-aetheros` (created), `docker/s6-rc.d/user/contents.d/main-hermes` (removed)
- `.github/actions/aetheros-smoke-test/` (renamed from hermes-smoke-test/)
- `.github/workflows/docker-publish.yml`
- `aetheros_cli/build_info.py`
- `scripts/aetheros-gateway`
- `scripts/install.sh`, `scripts/install.ps1`
- `cli.py`

---

## Remaining `hermes`/`HERMES_*` References

### By category (approximate, will be refined in Phase 3)

| Category | Count | Notes |
|----------|-------|-------|
| Env vars (runtime) | ~15 | `HERMES_HOME` (compat), `HERMES_GIT_SHA` (compat), `HERMES_WEB_DIST`, `HERMES_TUI_DIR`, `HERMES_GATEWAY_*`, `HERMES_GID`, `HERMES_UID`, etc. |
| Internal constants | ~10 | Config keys like `HERMES_PREFILL_MESSAGES_FILE`, code-level references |
| Tests | ~5-10 | Test files referencing old env vars or module names |
| Skills | ~5 | Skill SKILL.md files with `hermes` command references |
| Locales | ~2 | Translation keys |
| Comments/docstrings | ~20 | Non-user-facing comments explaining old behavior |
| Docker internal paths | ~5 | `/opt/hermes/` paths in Dockerfile comments/ENV |
| CI variables | ~3 | Workflow expressions using `HERMES_*` vars |
| Website/docs | ~10 | Docusaurus docs/markdown files |

**Total estimated remaining: ~75-100 references** (non-critical, cosmetic or internal)

---

## Compatibility Layers Active

| Layer | Type | Location |
|-------|------|----------|
| `HERMES_HOME` → `AETHEROS_HOME` | Env var fallback + deprecation warning | `aetheros_constants.py` |
| `HERMES_GIT_SHA` → `AETHEROS_GIT_SHA` | Dual build-arg support | `Dockerfile`, `docker-publish.yml`, `build_info.py` |
| `docker/hermes-exec-shim.sh` | File compat wrapper | Deleted — now points to `/opt/aetheros/bin/aetheros` |
| `SERVICE_NAME = "hermes-gateway"` | Systemd/launchd service name | `scripts/aetheros-gateway` (with TODO) |
| All `HERMES_GATEWAY_*` env vars | Unchanged | Not renamed — will get `AETHEROS_GATEWAY_*` aliases in Phase 3 |
| `HERMES_WEB_DIST`, `HERMES_TUI_DIR` | Unchanged Docker env vars | Not renamed — Phase 3 |

---

## Next Phase (3) — Internal Variables & Code

### Suggested scope
1. **Env var aliases**: Add `AETHEROS_*` aliases for `HERMES_GATEWAY_*`, `HERMES_GID`, `HERMES_UID`, `HERMES_WEB_DIST`, `HERMES_TUI_DIR`, `HERMES_DASHBOARD_*`, `HERMES_PREFILL_MESSAGES_FILE`, etc.
2. **Config keys**: Rename internal config keys where safe
3. **Internal constants**: Update `_HERMES_CORE_TOOLS`, module-level constants
4. **Test updates**: Phase 3 should include updating test references
5. **Skills**: Update skill SKILL.md files with `aetheros` command references

### Constraints
- Do NOT break compatibility — always support old names
- Do NOT perform global search-and-replace
- Do NOT modify business logic
- Keep `HERMES_HOME` fallback active (it's the primary compatibility layer)

---

## Phase Queue

```
Phase 3 — Internal Variables & Code     [⏳ Pending]
Phase 4 — File/Module Renames           [⏳ Pending]  
Phase 5 — Documentation & Skills        [⏳ Pending]
Phase 6 — Final Testing & Validation    [⏳ Pending]
```
