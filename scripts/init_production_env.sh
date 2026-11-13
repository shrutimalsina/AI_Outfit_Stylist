#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
if [[ -e .env || -L .env ]]; then
    echo ".env already exists. Inspect it locally and preserve the password for any existing database." >&2
    exit 1
fi
password=$(openssl rand -hex 32)
(set -o noclobber; printf 'POSTGRES_PASSWORD=%s\n' "$password" > .env)
echo "Created private .env"
