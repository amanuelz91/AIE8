#!/bin/bash
# Script to install all Guardrails validators
# Make sure you've configured your API key first using:
#   uv run python configure_guardrails.py [API_KEY]

set -e

echo "🛡️  Installing Guardrails validators..."
echo ""

VALIDATORS=(
    "hub://tryolabs/restricttotopic"
    "hub://guardrails/detect_jailbreak"
    "hub://guardrails/competitor_check"
    "hub://arize-ai/llm_rag_evaluator"
    "hub://guardrails/profanity_free"
    "hub://guardrails/guardrails_pii"
)

for validator in "${VALIDATORS[@]}"; do
    echo "Installing $validator..."
    uv run guardrails hub install "$validator"
    echo ""
done

echo "✅ All validators installed successfully!"

