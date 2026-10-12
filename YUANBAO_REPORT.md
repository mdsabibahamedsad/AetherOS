# Yuanbao API Improvements Report

## Implemented API Features

The Yuanbao adapter's infrastructure already includes:

### ✅ Protocol Layer (`yuanbao_proto.py`)
- `encode_query_group_info(group_code)` — encodes query_group_info request
- `decode_query_group_info_rsp(data)` — decodes response with `group_name`, `owner_id`, `owner_nickname`, `member_count`
- `encode_get_group_member_list(group_code, offset, limit)` — encodes member list request
- `decode_get_group_member_list_rsp(data)` — decodes response with `members` array
- All existing and stable — used by the `GroupQueryService`

### ✅ Service Layer (`yuanbao.py`)
- `GroupQueryService` class (line 3835)
- `query_group_info_raw(group_code)` — low-level WS query (line 3852)
- `query_group_info(group_code)` — higher-level AI tool wrapper
- `get_group_member_list(group_code)` — member list for @mention resolution
- `_member_cache` — 5-minute TTL cache on the adapter

## Remaining Work

### `get_chat_info` Method Enhancement (Blocked)

The `get_chat_info` method at line 4856 currently returns only chat_id-based metadata:

```python
async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
    if chat_id.startswith("group:"):
        return {"name": chat_id, "type": "group"}
    return {"name": chat_id, "type": "dm"}
```

Should be enhanced to:

```python
async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
    # 1. Check per-chat metadata cache (5 min TTL)
    # 2. For groups: query via GroupQueryService.query_group_info_raw()
    # 3. Cache result with timestamp
    # 4. Fall back to chat_id-based metadata on failure
```

Infrastructure available:
- `self._group_query.query_group_info_raw(group_code)` returns `{"group_name", "owner_id", "owner_nickname", "member_count"}`
- Cache pattern mirrors `_member_cache` and `MediaResolveMiddleware._resource_cache`

### Cache Design

```
_chat_info_cache: Dict[str, Dict] = {}
  Key: f"chat_info:{chat_id}"
  Value: {
    "name": str,
    "type": "group" | "dm",
    "member_count": int,  # for groups
    "group_code": str,    # for groups
    "_ts": float          # cache timestamp
  }
  TTL: 300 seconds (5 minutes)
```

### API Error Handling

- **Token expiry**: Catch 401 responses and trigger token force-refresh
- **Rate limiting**: Exponential backoff on 429 responses
- **Network errors**: Log and fall back to chat_id-based metadata
- **Empty responses**: Return fallback metadata, log at debug level

## Remaining Limitations

1. **Blocked by file size**: `yuanbao.py` is 205K chars (2x the tool's limit), preventing inline edits
2. **No member list in get_chat_info**: Currently planned for name + count only; full member list requires pagination
3. **Caching not persisted**: Cache is in-memory only, lost on process restart

## Recommended Implementation Approach

Use a text editor or sed script to replace lines 4856-4867 in `gateway/platforms/yuanbao.py`:

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
            logger.debug("[%s] get_chat_info query failed for %s: %s",
                         self.name, group_code, exc)
        return {"name": chat_id, "type": "group", "group_code": group_code}
    return {"name": chat_id, "type": "dm"}
```
