#!/usr/bin/env bash
set -euo pipefail

echo "export YTM_CLIENT_ID=$(op read 'op://Private/Google YouTube Playlist Creator OAuth/username')"
echo "export YTM_CLIENT_SECRET=$(op read 'op://Private/Google YouTube Playlist Creator OAuth/password')"
