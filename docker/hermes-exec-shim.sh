#!/bin/sh
# shellcheck shell=sh
# COMPATIBILITY WRAPPER — delegates to aetheros-exec-shim.sh.
#
# This file is kept for backward compatibility with scripts that
# reference the old filename. New deployments should reference
# docker/aetheros-exec-shim.sh directly.
#
# TODO: Remove this wrapper once all deployment scripts have been
# updated to reference docker/aetheros-exec-shim.sh.

exec /opt/aetheros/bin/aetheros "$@"
