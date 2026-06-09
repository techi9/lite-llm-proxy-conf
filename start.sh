#!/usr/bin/env zsh
set -a
source "$(dirname "$0")/.env"
set +a

unset PORT
unset LITELLM_MASTER_KEY

# Free ports 4000 and 4001
for port in 4000 4001; do
  existing_pid=$(lsof -ti:$port 2>/dev/null)
  if [[ -n "$existing_pid" ]]; then
    echo "Killing existing process on port $port (PID $existing_pid)..."
    kill "$existing_pid" && sleep 1
  fi
done

cd "$(dirname "$0")"

# Resolve the Python that ships with the litellm pipx venv.
# pipx installs a wrapper in ~/.local/bin but the real venv is in
# ~/.local/pipx/venvs/litellm/bin/
LITELLM_BIN=$(command -v litellm)
# Follow symlink to the real script inside the venv
LITELLM_REAL=$(readlink "$LITELLM_BIN" 2>/dev/null || echo "$LITELLM_BIN")
# If readlink returned a relative path, resolve it relative to the symlink dir
if [[ "$LITELLM_REAL" != /* ]]; then
  LITELLM_REAL="$(dirname "$LITELLM_BIN")/$LITELLM_REAL"
fi
PYTHON=$(dirname "$LITELLM_REAL")/python
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=$(dirname "$LITELLM_REAL")/python3
fi
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: could not find Python next to litellm binary ($LITELLM_REAL)" >&2
  exit 1
fi
echo "Using Python: $PYTHON"

# Install aiohttp into the same venv if not present
"$PYTHON" -c "import aiohttp" 2>/dev/null || "$PYTHON" -m pip install -q aiohttp

# Start LiteLLM on port 4001 in background
echo "Starting LiteLLM on :4001..."
litellm --config litellm_config.yaml --port 4001 &
LITELLM_PID=$!
sleep 4

# Start middleware on port 4000 in foreground (strips image_url before forwarding to 4001)
echo "Starting middleware on :4000..."
trap "kill $LITELLM_PID 2>/dev/null" EXIT
"$PYTHON" middleware.py
