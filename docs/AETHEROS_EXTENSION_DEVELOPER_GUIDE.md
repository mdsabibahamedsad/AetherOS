# Extension Developer Guide (Master 44)

## Layout

```
my-ext/
  manifest.json
  extension/main.py        # declared entrypoints only
  extension/smoke.py       # optional dynamic smoke entry
  schemas/ assets/ README.md LICENSE
```

## Manifest essentials

id (`[a-z0-9._-]{2,128}`), semver version, publisher_id, type (one of
14), apiVersion "1", engineVersion ≤ 44, permissions (string or
`{permission, paths|domains|origins|names}`), entrypoints (no `..`),
tools/skills/mcp_servers/agents/workflows declarations.

## Build / validate / sign

```
aetheros extension validate manifest.json
aetheros extension package ./my-ext --dest my-ext.aetherext
aetheros extension sign my-ext.aetherext privkey.b64
# embed signature/signature.json, distribute
```

Builds are deterministic (sorted entries, fixed timestamps) — rebuilding
the same tree yields identical bytes.

## Dev mode

Load local directories; unsigned allowed ONLY with visible dev-trust
flag (`dev_allow_unsigned`, logged in verdict). Production default
denies unsigned. `extension doctor` + verify + permission review expose
real state; reload = reinstall from directory.

## Rules

No executables outside declared locations; no postinstall network;
no credential reads without `secrets.read_scoped` + approval; MCP
descriptions must be benign (scanned); state migrations must be
idempotent (v1→v2 backup/verify/commit in host storage API).
