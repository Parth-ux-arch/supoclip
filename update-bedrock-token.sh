#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/opt/supoclip/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE does not exist."
    exit 1
fi

TOKEN="${1:-}"

if [ -z "$TOKEN" ]; then
    echo "================================================="
    echo " Update AWS Bedrock Bearer Token (SupoClip)"
    echo "================================================="
    echo "Paste the new Bearer Token (input will be hidden):"
    read -rsp "Token: " TOKEN
    echo ""
fi

if [ -z "$TOKEN" ]; then
    echo "Error: No token provided. Aborting."
    exit 1
fi

# Strip surrounding quotes if user included them
TOKEN="${TOKEN%\"}"
TOKEN="${TOKEN#\"}"
TOKEN="${TOKEN%\'}"
TOKEN="${TOKEN#\'}"

# Update AWS_BEARER_TOKEN_BEDROCK in .env using python to avoid sed escape issues with special chars
python3 -c "
import sys
token = sys.argv[1]
env_path = '$ENV_FILE'
with open(env_path, 'r') as f:
    lines = f.readlines()
found = False
with open(env_path, 'w') as f:
    for line in lines:
        if line.startswith('AWS_BEARER_TOKEN_BEDROCK='):
            f.write(f'AWS_BEARER_TOKEN_BEDROCK=\"{token}\"\n')
            found = True
        else:
            f.write(line)
    if not found:
        f.write(f'AWS_BEARER_TOKEN_BEDROCK=\"{token}\"\n')
" "$TOKEN"

chmod 600 "$ENV_FILE"
echo "-> AWS Bedrock Bearer Token updated in $ENV_FILE"

echo "-> Updating and recreating SupoClip containers with new environment..."
(cd /opt/supoclip && docker compose up -d)

echo "Done! The new Bedrock token has been applied and services restarted."
