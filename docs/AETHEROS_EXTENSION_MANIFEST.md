# Extension Manifest Reference (Master 44)

Required: `id`, `name`, `version` (semver), `publisher_id`,
`extension_type` (skill|tool_pack|mcp_server|mcp_tool_provider|agent|
model_provider|browser|computer|research|automation|memory_provider|
ui|integration|workflow_component), `apiVersion: "1"`.

Optional: displayName, description, publisher, homepage, repository,
license, icon, categories, keywords, engineVersion, platforms,
architectures, dependencies `{id: range}` (^/~/>=/exact; `*` and
bare words fail closed), optionalDependencies, capabilities,
permissions (string or scoped object), entrypoints (package-relative,
`..` rejected), tools[] (`name` required), skills[], mcpServers[],
agents[], workflows[], settings, commands[], events[], network/
filesystem requirement hints, secrets[] (scope names, brokered),
updatePolicy.

Unknown fields → invalid. Empty permission strings, nameless tools,
bad pins → invalid. Validation is fail-closed (`validate()` non-empty
= reject with reasons).
