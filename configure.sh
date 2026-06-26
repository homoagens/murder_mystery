#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "  Murder Mystery - LLM configuration"
echo "========================================"
echo ""
echo "This will write a .env file for Murder Mystery."
echo "Point it at any OpenAI-compatible endpoint"
echo "(Ollama, LM Studio, vLLM, llama.cpp, OpenAI, Groq, OpenRouter...)."
echo ""

read -p "Base URL [http://localhost:11434/v1]: " BASE_URL
BASE_URL=${BASE_URL:-http://localhost:11434/v1}

read -p "Default model [llama3.2]: " MODEL
MODEL=${MODEL:-llama3.2}

read -p "API key (press Enter for none): " API_KEY

read -p "Use a different model per role (writer/detective/suspect)? [y/N]: " PER_ROLE
if [[ "$PER_ROLE" =~ ^[Yy]$ ]]; then
    read -p "  writer model [${MODEL}]: " WRITER_MODEL
    WRITER_MODEL=${WRITER_MODEL:-$MODEL}
    read -p "  detective model [${MODEL}]: " DETECTIVE_MODEL
    DETECTIVE_MODEL=${DETECTIVE_MODEL:-$MODEL}
    read -p "  suspect model [${MODEL}]: " SUSPECT_MODEL
    SUSPECT_MODEL=${SUSPECT_MODEL:-$MODEL}
else
    WRITER_MODEL=""
    DETECTIVE_MODEL=""
    SUSPECT_MODEL=""
fi

read -p "Web UI port [7860]: " WEB_PORT
WEB_PORT=${WEB_PORT:-7860}

if [ -f .env ]; then
    cp .env .env.backup
    echo ""
    echo "Existing .env backed up to .env.backup"
fi

{
    echo "LLM_PROVIDER=openai"
    echo "LLM_BASE_URL=${BASE_URL}"
    echo "LLM_API_KEY=${API_KEY}"
    echo "DEFAULT_MODEL=${MODEL}"
    [ -n "$WRITER_MODEL" ]    && echo "WRITER_MODEL=${WRITER_MODEL}"
    [ -n "$DETECTIVE_MODEL" ] && echo "DETECTIVE_MODEL=${DETECTIVE_MODEL}"
    [ -n "$SUSPECT_MODEL" ]   && echo "SUSPECT_MODEL=${SUSPECT_MODEL}"
    echo ""
    echo "WEB_HOST=0.0.0.0"
    echo "WEB_PORT=${WEB_PORT}"
} > .env

echo ""
echo "Configuration saved to .env:"
echo "  provider:  openai-compatible"
echo "  base URL:  ${BASE_URL}"
echo "  model:     ${MODEL}"
[ -n "$WRITER_MODEL" ]    && echo "  writer:    ${WRITER_MODEL}"
[ -n "$DETECTIVE_MODEL" ] && echo "  detective: ${DETECTIVE_MODEL}"
[ -n "$SUSPECT_MODEL" ]   && echo "  suspect:   ${SUSPECT_MODEL}"
echo "  port:      ${WEB_PORT}"
echo ""
echo "Run ./start.sh to launch Murder Mystery."
echo ""
