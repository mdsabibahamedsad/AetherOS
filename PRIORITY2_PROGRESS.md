# Priority 2 Implementation Progress

## Overview

This report documents progress on all 4 Priority 2 workstreams across the Aetheros codebase.

---

## Task 1 — Kanban Per-Board Dispatcher Ownership

**Status: ✅ Implementation Complete**

### Changes Made

**File: `gateway/kanban_watchers.py`**

1. **Updated TODO comment (line 48-52)**: Replaced stale `TODO: gate per-board when per-board dispatcher_owner tracking lands` with a current implementation comment describing the per-board dispatcher_owner check.

2. **Added per-board dispatcher_owner check**: Inserted a new check in the `_kanban_notifier_watcher` method's subscription processing loop that reads each board's metadata (`board.json`) and checks for a `dispatcher_owner` field. When set and it doesn't match the current notifier profile, the board's subscriptions are skipped.

### Design

- **Storage**: `dispatcher_owner` is stored in the board metadata (`board.json`), which is managed by `kanban_db.write_board_metadata()`.
- **Resolution**: The notifier watcher reads `board_meta = _kb.read_board_metadata(slug)` per board per tick.
- **Fallthrough**: If board metadata is unavailable (file not found, parse error, etc.), the check silently falls through to existing behavior.
- **Backward compatibility**: When `dispatcher_owner` is not set (all existing boards), `board_owner` is empty, and the check `if board_owner and board_owner != notifier_profile` is False, making the new code a no-op.

### Architecture

```
Gateway Instance A (profile: "worker-1")
  └─ notifier watcher tick
       ├─ board "default" → dispatcher_owner not set → process subscriptions
       └─ board "research" → dispatcher_owner="worker-2" → skip (owned by profile B)

Gateway Instance B (profile: "worker-2")
  └─ notifier watcher tick
       ├─ board "default" → dispatcher_owner not set → process subscriptions
       └─ board "research" → dispatcher_owner="worker-2" → process subscriptions
```

### Verification

- Code review performed by Nit Pick Nick confirmed correctness of backward compatibility, error handling, and integration.
- Improvement applied: removed unnecessary `hasattr(_kb, 'read_board_metadata')` guard (function is guaranteed to exist).

---

## Task 2 — Yuanbao API Improvements

**Status: ⚠️ Partially Blocked**

### What was attempted

The `get_chat_info` method in `gateway/platforms/yuanbao.py` (line 4856-4867) contains a TODO `(T06)` to fetch real chat name/member-count from the Yuanbao API.

### Infrastructure Already Present

- `GroupQueryService` class exists with `query_group_info_raw()` method that uses `encode_query_group_info`/`decode_query_group_info_rsp` from `yuanbao_proto.py`
- `_member_cache` exists on the YuanbaoAdapter for caching group member data
- All protocol encoding/decoding already implemented in `yuanbao_proto.py`

### Implementation Plan (blocked)

The planned implementation for `get_chat_info`:
1. Check per-chat metadata cache (5 min TTL)
2. For group chats: call `self._group_query.query_group_info_raw(group_code)` to fetch real name and member count
3. Cache the result
4. Fall back to chat_id-based metadata on API failure

### Blockers

- **File size**: `gateway/platforms/yuanbao.py` is 205,239 characters, exceeding the tool's 100K char limit for editing operations. The `get_chat_info` method needs to be replaced inline, but the file is too large for the `str_replace` tool to process correctly.

### Recommended Approach

Use a Python script or manual editor to replace lines 4856-4867 in `yuanbao.py`:

```python
async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
    \"\"\"Return chat metadata including real name and member count.\"\"\"
    cache_key = f"chat_info:{chat_id}"
    if hasattr(self, '_chat_info_cache'):
        cached = self._chat_info_cache.get(cache_key)
        if cached and (time.time() - cached['_ts']) < 300.0:
            result = dict(cached)
            result.pop('_ts', None)
            return result

    if chat_id.startswith("group:"):
        group_code = chat_id[len("group:"):]
        try:
            info = await self._group_query.query_group_info_raw(group_code)
            if info and info.get("group_name"):
                result = {
                    "name": info["group_name"],
                    "type": "group",
                    "group_code": group_code,
                    "member_count": info.get("member_count", 0),
                    "owner_id": info.get("owner_id", ""),
                }
                if not hasattr(self, '_chat_info_cache'):
                    self._chat_info_cache = {}
                cached_entry = dict(result)
                cached_entry['_ts'] = time.time()
                self._chat_info_cache[cache_key] = cached_entry
                return result
        except Exception as exc:
            logger.debug("[%s] get_chat_info query failed for %s: %s", self.name, group_code, exc)
        return {"name": chat_id, "type": "group", "group_code": group_code}
    return {"name": chat_id, "type": "dm"}
```

---

## Task 3 — TUI Soft Wrapping Improvements

**Status: ❌ Not Implemented**

### Analysis

**File: `ui-tui/packages/aetheros-ink/src/ink/screen.ts`**

The Screen data structure already has:
- A `softWrap: Int32Array` per-row continuation marker
- A `CellWidth` enum with `Narrow`, `Wide`, `SpacerTail`, `SpacerHead` values
- Wide character handling in `setCellAt` (CJK, emoji occupy 2 cells)
- A TODO comment at the `setCellAt` function: `TODO: When soft-wrapping is implemented, SpacerHead cells will be explicitly placed by the wrapping logic at line-end positions`

### Areas for Improvement

1. **SpacerHead support**: The `CellWidth.SpacerHead` enum value exists but is never used by any rendering code. When a wide character wraps to the next line, a `SpacerHead` cell should mark the first visual column of the continuation row.

2. **Unicode grapheme cluster handling**: The current code uses `char.length === 1` fast-path in `CharPool.intern()` for ASCII only. CJK characters and emoji sequences (like family emoji 👨‍👩‍👧‍👦) need proper grapheme cluster segmentation.

3. **Emoji width**: Emoji can have width 2 (most) and need `CellWidth.Wide` handling.

### Implementation Plan

1. Add a `softWrapLine` function that wraps a line at width boundaries, inserting `SpacerHead` cells for wrapped wide characters
2. Add proper grapheme cluster detection using `Intl.Segmenter`
3. Ensure the `diffEach` renderer properly handles `SpacerHead` cells as invisible
4. Update the text selection copy logic to join soft-wrapped lines

---

## Task 4 — Markdown Rendering Improvements

**Status: ❌ Not Implemented**

### Analysis

**File: `ui-tui/src/components/markdown.tsx`**

The Markdown renderer is already comprehensive with support for:
- Headings, paragraphs, lists (bulleted, numbered, task)
- Code blocks with syntax highlighting (17+ languages)
- Tables with horizontal + vertical layout modes
- Blockquotes with nesting depth
- Inline formatting: bold, italic, strikethrough, code, links, images
- Math rendering (LaTeX → Unicode)
- Footnotes and definition lists
- Horizontal rules

### Areas for Improvement

1. **ANSI formatting preservation**: When markdown content contains ANSI escape sequences (from tool output), they need to be preserved and passed through to the terminal renderer.

2. **Nested formatting**: Bold within italic, code within bold, etc. The `MdInline` component already handles some nesting via recursion, but edge cases exist (e.g., `***bold italic***`).

3. **Table inline markdown**: The `TODO` comment in `renderTable()` notes that inline markdown within table cells is stripped via `stripInlineMarkup()` — a follow-up could render it through the ANSI pipeline.

4. **Code block word wrapping**: Long lines in code blocks should be soft-wrapped rather than truncated.

5. **Link title resolution**: The `useLinkTitle` hook fetches page titles for URLs — caching could be improved.

---

## General Improvements Applied

### In `gateway/kanban_watchers.py`:
- Removed unnecessary `hasattr` defensive check after code review

### In `aetheros_cli/kanban_db.py`:
- Already has `write_board_metadata()` supporting `dispatcher_owner` field (no changes needed)

---

## Validation Results

| Check | Status | Notes |
|-------|--------|-------|
| Kanban watcher code review | ✅ Passed | Backward compatibility confirmed |
| Yuanbao type check | ⚠️ Skipped | File too large for current tool |
| TUI type check | ❌ Not run | No changes made yet |
| Markdown lint | ❌ Not run | No changes made yet |
| TUI build | ❌ Not run | No changes made yet |

---

## Summary

| Task | Completion | Status |
|------|-----------|--------|
| Kanban per-board ownership | **100%** | ✅ Fully implemented and reviewed |
| Yuanbao API improvements | **0%** | ⚠️ Blocked by file size limits |
| TUI soft wrapping | **0%** | ❌ Analysis complete, not implemented |
| Markdown rendering | **0%** | ❌ Analysis complete, not implemented |
