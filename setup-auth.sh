#!/usr/bin/env bash
set -euo pipefail

eval "$(./env.sh)"

echo "Using client ID: ${YTM_CLIENT_ID:0:20}..."

uv run python -c "
import os
client_id = os.environ['YTM_CLIENT_ID']
client_secret = os.environ['YTM_CLIENT_SECRET']
print(f'Python sees client_id: {client_id[:20]}...')
from ytmusicapi import setup_oauth
setup_oauth(
    filepath='oauth.json',
    client_id=client_id,
    client_secret=client_secret,
)
"
