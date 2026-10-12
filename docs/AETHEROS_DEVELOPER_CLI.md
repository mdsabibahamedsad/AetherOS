# AetherOS Developer CLI Reference

Standalone developer CLI: `python -m aetheros_platform.cli`.
Only commands that actually work are exposed.

> NOTE: integration into the main `aetheros` binary is BLOCKED by a pre-existing startup crash (`conflicting subparser: agent` from `aetheros_cli/agent_network_cmd.py:34` vs `agents/cli.py:445`). The standalone CLI below is the real, tested developer surface.

## `init`

```
usage: aetheros-platform init [-h] [--dest DEST]
                              {agent,skill,tool,mcp,a2a,extension} name

positional arguments:
  {agent,skill,tool,mcp,a2a,extension}
  name

options:
  -h, --help            show this help message and exit
  --dest DEST
```

## `dev`

```
usage: aetheros-platform dev [-h] [--port PORT] [--bind BIND]

options:
  -h, --help   show this help message and exit
  --port PORT
  --bind BIND
```

## `schema`

```
usage: aetheros-platform schema [-h] [--name NAME] [--ts]

options:
  -h, --help   show this help message and exit
  --name NAME
  --ts
```

## `api`

```
usage: aetheros-platform api [-h] [--bind BIND] [--port PORT] {list,serve}

positional arguments:
  {list,serve}

options:
  -h, --help    show this help message and exit
  --bind BIND
  --port PORT
```

## `test`

```
usage: aetheros-platform test [-h] [--project PROJECT]

options:
  -h, --help         show this help message and exit
  --project PROJECT
```

## `package`

```
usage: aetheros-platform package [-h] [--project PROJECT] [--file FILE]
                                 [--name NAME] [--version VERSION]
                                 [--dest DEST]
                                 {build,publish,install}

positional arguments:
  {build,publish,install}

options:
  -h, --help            show this help message and exit
  --project PROJECT
  --file FILE
  --name NAME
  --version VERSION
  --dest DEST
```

## `auth`

```
usage: aetheros-platform auth [-h] [--name NAME] [--scopes SCOPES]
                              [--owner OWNER] [--key-id KEY_ID]
                              {key-create,key-list,key-revoke}

positional arguments:
  {key-create,key-list,key-revoke}

options:
  -h, --help            show this help message and exit
  --name NAME
  --scopes SCOPES
  --owner OWNER
  --key-id KEY_ID
```

### Workflows

```bash
# five minutes to a running agent
export PYTHONPATH=$PWD AETHEROS_HOME=$PWD/.dev-home
python -m aetheros_platform.cli auth key-create --name dev --scopes agents:write,tasks:write,tasks:read --owner me
python -m aetheros_platform.cli dev --port 8765  # local gateway
python -m aetheros_platform.cli init agent my-agent --dest .
python -m aetheros_platform.cli test --project my-agent
```
