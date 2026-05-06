#!/usr/bin/env bash
set -e

echo "=== GenAI RAG Installer ==="

# --- Python check ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 not found. Install Python 3.10+ and re-run."
  exit 1
fi

# --- Create venv if missing ---
if [ ! -d "qwen_env" ]; then
  python3 -m venv qwen_env
fi

# --- Activate venv ---
source qwen_env/bin/activate

# --- Install Python deps ---
pip install --upgrade pip
pip install -r requirements.txt

# --- Ensure Ollama path is visible ---
export PATH="/usr/local/bin:$PATH"

# --- Install Ollama if missing ---
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found. Installing..."
  curl -fsSL https://ollama.com/install.sh | sudo sh
  sudo systemctl start ollama
  sudo systemctl enable ollama
fi

# --- Verify Ollama installed correctly ---
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama installation failed. Install manually from https://ollama.com"
  exit 1
fi

# --- Pull model ---
ollama pull qwen2.5:0.5b-instruct-q4_0

echo "Installation complete."
echo "Run with:"
echo "  source qwen_env/bin/activate"
echo "  python -m server.app"

