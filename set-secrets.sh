#!/usr/bin/env bash
set -e

ENV_FILE="/opt/supoclip/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE does not exist."
    exit 1
fi

echo "================================================="
echo " SupoClip Secure Credential Setup (No Echo/Logs)"
echo "================================================="
echo "Your input will NOT be displayed on screen."
echo ""

read -sp "1. Enter AssemblyAI API Key: " AAI_KEY
echo ""
if [ -n "$AAI_KEY" ]; then
    sed -i "s|^ASSEMBLY_AI_API_KEY=.*|ASSEMBLY_AI_API_KEY=$AAI_KEY|" "$ENV_FILE"
    echo "-> AssemblyAI API Key updated in .env"
fi

echo ""
read -sp "2. Enter AWS Bedrock Bearer Token: " BEDROCK_KEY
echo ""
if [ -n "$BEDROCK_KEY" ]; then
    sed -i "s|^AWS_BEARER_TOKEN_BEDROCK=.*|AWS_BEARER_TOKEN_BEDROCK=$BEDROCK_KEY|" "$ENV_FILE"
    echo "-> AWS Bedrock Bearer Token updated in .env"
fi

unset AAI_KEY BEDROCK_KEY
chmod 600 "$ENV_FILE"
echo ""
echo "Done! Credentials safely stored in $ENV_FILE with permissions 600."
