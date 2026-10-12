# AetherOS Marketplace Guide

## Overview

The AetherOS Extension Marketplace is a managed platform for discovering, installing, updating, and managing extensions. It supports both public and private registries.

## CLI Commands

```
aetheros marketplace search    Search the marketplace
aetheros marketplace install   Install an extension
aetheros marketplace update    Update extensions
aetheros marketplace remove    Remove an extension
aetheros marketplace list      List installed extensions
aetheros marketplace info      Show extension details
aetheros marketplace popular   Show popular extensions
aetheros marketplace refresh   Refresh the cache
aetheros marketplace sources   List configured sources
```

## Searching

```bash
# Basic search
aetheros marketplace search "code assistant"

# Filter by kind
aetheros marketplace search --kind tool "search"

# Filter by publisher
aetheros marketplace search --publisher "aetheros"

# Only verified extensions
aetheros marketplace search --verified

# Sort by downloads
aetheros marketplace search --sort downloads

# JSON output for scripting
aetheros marketplace search "git" --json | jq
```

## Installing

```bash
# From marketplace
aetheros marketplace install my-plugin

# From Git URL
aetheros marketplace install https://github.com/owner/repo.git

# From owner/repo shorthand
aetheros marketplace install owner/repo

# From local .aep package
aetheros marketplace install ./my-plugin.aep

# Force reinstall
aetheros marketplace install my-plugin --force
```

## Publishing

Build and publish your plugin:

```bash
aetheros sdk build
aetheros sdk publish ./my-plugin-1.0.0.aep
```
