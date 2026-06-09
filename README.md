# LiteLLM Proxy — JetBrains IDE / Azure OpenAI bridge

Routes any JetBrains IDE (WebStorm, IntelliJ, PyCharm, etc.) GitHub Copilot in **Azure OpenAI mode** to an OpenAI-compatible backend through a local LiteLLM proxy.

```
JetBrains IDE  ──(Azure format)──▶  middleware :4000  ──▶  LiteLLM :4001  ──▶  your backend
(Azure OpenAI mode)                                 (Azure→OpenAI translation)
```

## Architecture

| Component | Port | Purpose |
|---|---|---|
| **middleware.py** | `4000` | Strips `image_url` parts from messages (models without vision support reject them) |
| **LiteLLM** | `4001` | Translates Azure OpenAI format → standard OpenAI `/v1/chat/completions` format |
| **litellm_config.yaml** | — | Defines available models and routes them to your backend |

---

## 1. Prerequisites

### Install pipx and LiteLLM

```zsh
brew install pipx
pipx ensurepath
pipx install 'litellm[proxy]'
```

Then **restart your terminal** (or `source ~/.zshrc`) and verify:

```zsh
litellm --version
```

---

## 2. Configure `.env`

```zsh
cd /path/to/lite-llm-proxy-conf
cp .env.example .env
```

Edit `.env` with your backend credentials:

| Variable | Value |
|---|---|
| `CUSTOM_OPENAI_API_BASE` | Your backend's base URL (e.g. `https://your-api.example.com/v1`) |
| `CUSTOM_OPENAI_API_KEY` | Your backend API key |

> `LITELLM_MASTER_KEY` is commented out — no proxy-level auth needed since it runs on localhost only.

---

## 3. Start the proxy

```zsh
./start.sh
```

This launches **both** the middleware (port 4000) and LiteLLM (port 4001).

Verify it's running:

```zsh
curl http://localhost:4000/health
```

Keep the terminal open while using your IDE.

---

## 4. Configure your JetBrains IDE

1. Open copilot chat panel.
2. Open model selection dropdown.
3. Click `Manage Models`
4. Under Azure provider, click + Add models
3. Fill in:

| Field               | Value                                                                                      |
|---------------------|--------------------------------------------------------------------------------------------|
| **Model ID**        | Strict model id name e.g. `deepseek-v4-pro`                                                |
| **Deployement URL** | Pick one of the model URLs below     ( link must contain same model ID as the field above) |
| **API key**         | Anything — proxy doesn't check it (e.g. `no-auth`)                                         |
| **Model name**      | Any name you like for the model                                                            |
| **Vision**          | Untick!!!                                                                                  |

### Model Endpoint URLs

Use any of these as the **Endpoint URL** in the IDE settings:

| Model | Endpoint URL |
|---|---|
| **deepseek-v4-pro** | `http://localhost:4000/openai/deployments/deepseek-v4-pro/chat/completions` |
| **deepseek-v4-flash** | `http://localhost:4000/openai/deployments/deepseek-v4-flash/chat/completions` |
| **mimo-v2.5-pro-ultraspeed** | `http://localhost:4000/openai/deployments/mimo-v2.5-pro-ultraspeed/chat/completions` |
| **minimax-m3** | `http://localhost:4000/openai/deployments/minimax-m3/chat/completions` |
| **kimi-k2.6** | `http://localhost:4000/openai/deployments/kimi-k2.6/chat/completions` |

Feel free to add more models here. <br>
The URL format is:

```
http://localhost:4000/openai/deployments/{MODEL_NAME}/chat/completions
```

4. Click **Apply / OK**
5. In the Copilot chat panel, select your new Azure model from the dropdown

---

## 5. Adding more models

Add an entry in `litellm_config.yaml` under `model_list`:

```yaml
- model_name: your-new-model
  litellm_params:
    model: openai/your-new-model
    api_base: os.environ/CUSTOM_OPENAI_API_BASE
    api_key:  os.environ/CUSTOM_OPENAI_API_KEY
    supports_vision: false
```

Then restart: `./start.sh`

---

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| `Connection refused` on port 4000 | Proxy isn't running — run `./start.sh` |
| `Unrecognized Azure deployment URL` | Make sure the Endpoint URL includes the full path: `http://localhost:4000/openai/deployments/{model}/chat/completions` |
| `404` from proxy | The model name in the URL doesn't match any `model_name` in `litellm_config.yaml` |
| `image_url` / vision errors from backend | Middleware automatically strips image content — make sure `supports_vision: false` is set for non-vision models |
| Errors from your backend | Check `CUSTOM_OPENAI_API_BASE` and `CUSTOM_OPENAI_API_KEY` in `.env` |
| SSL error in IDE | Use `http://` not `https://` for localhost |

Tail proxy logs:
```zsh
tail -f litellm.log
```
