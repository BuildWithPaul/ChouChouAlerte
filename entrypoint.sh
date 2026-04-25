#!/bin/sh
set -e

# Fix permissions on mounted data volume
mkdir -p /app/data
chown -R appuser:appuser /app/data 2>/dev/null || true

# Drop to non-root user and exec CMD
exec su -s /bin/sh appuser -c "exec $*"