#!/usr/bin/env bash
# Start the production standalone server locally (the Docker image does the same copy at build time).
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf .next/standalone/public .next/standalone/.next/static
cp -r public .next/standalone/public
mkdir -p .next/standalone/.next
cp -r .next/static .next/standalone/.next/static
# Bind address comes from BIND_HOST: the shell's own HOSTNAME holds the machine name, not an address.
export PORT="${PORT:-3000}" HOSTNAME="${BIND_HOST:-0.0.0.0}"
exec node .next/standalone/server.js
