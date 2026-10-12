# Kanban Per-Board Dispatcher Ownership Report

## Ownership Model

Each board has an optional `dispatcher_owner` field stored in its `board.json` metadata. This field identifies which gateway profile (or instance) owns the dispatch loop for that board.

```
Board Metadata (board.json):
  ├── slug: "research"
  ├── name: "Research Tasks"
  ├── dispatcher_owner: "worker-2"    ← NEW FIELD
  └── ...
```

### Resolution Order

When the notifier/dispatcher watcher processes a subscription:

1. **Per-board check**: Read `board_meta.dispatcher_owner` from `board.json`
2. **If set and doesn't match current profile**: Skip the subscription
3. **If not set or unavailable**: Fall through to existing `notifier_profile` check

## Dispatcher Lifecycle

### Dispatcher Watcher (`_kanban_dispatcher_watcher`)

The dispatcher watcher already iterates every board per tick:

```python
def _tick_once() -> list[tuple[str, Optional[object]]]:
    boards = _kb.list_boards(include_archived=False)
    for b in boards:
        slug = b.get("slug") or _kb.DEFAULT_BOARD
        out.append((slug, _tick_once_for_board(slug)))
    return out
```

The per-board `dispatcher_owner` gating is applied in the **notifier** watcher, not the dispatcher watcher itself. The dispatcher already correctly operates per-board:

- Each board has its own DB connection via `_kb.connect(board=slug)`
- Claims are per-board (separate SQLite databases)
- Worker spawns are per-board (env injection of `AETHEROS_KANBAN_BOARD`)

### Notifier Watcher (`_kanban_notifier_watcher`)

The notifier now has the per-board gating:

```
Gateway A (profile: "worker-1")
  → tick for board "default" (no dispatcher_owner) → processes subs
  → tick for board "research" (dispatcher_owner: "worker-2") → SKIPS

Gateway B (profile: "worker-2")
  → tick for board "default" (no dispatcher_owner) → processes subs
  → tick for board "research" (dispatcher_owner: "worker-2") → processes subs
```

## Concurrency Behavior

| Scenario | Behavior |
|----------|----------|
| Same board, two gateways | Only the gateway matching `dispatcher_owner` processes notifications |
| Different boards, same gateway | Both boards processed as long as `dispatcher_owner` matches or is unset |
| Missing `dispatcher_owner` | Falls through to existing `notifier_profile` check (backward compatible) |
| Board metadata unavailable | Silently falls through (resilient) |
| Multiple profiles on same board | Existing `notifier_profile` check still applies |

## Architecture Changes

### Files Modified

**`gateway/kanban_watchers.py`** (+16 lines)
- Removed stale TODO comment
- Added per-board `dispatcher_owner` check in subscription processing loop
- Updated comment to reflect current implementation

### Files Not Changed (Already Suitable)

**`aetheros_cli/kanban_db.py`** — Already supports:
- `read_board_metadata(slug)` — reads `board.json`
- `write_board_metadata(..., dispatcher_owner=...)` — already accepts arbitrary kwargs
- Per-board DB isolation via `kanban_db_path(board=slug)`

### Setting Up Per-Board Dispatch

```bash
# CLI: set dispatcher_owner on a board
aetheros kanban boards metadata research \
  --set dispatcher_owner=worker-2

# Or programmatically:
from aetheros_cli import kanban_db as kb
kb.write_board_metadata("research", dispatcher_owner="worker-2")
```

## Testing Notes

Tests should verify:

1. Board with `dispatcher_owner` matching current profile → processes subs normally
2. Board with `dispatcher_owner` not matching → skips subs
3. Board without `dispatcher_owner` set → backward compatible (processes subs)
4. Board metadata missing/corrupt → gracefully falls through
5. Multiple boards with mixed ownership → correct per-board routing
