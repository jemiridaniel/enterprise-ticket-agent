from typing import List, Literal
import httpx

from ..config import settings

Role = Literal["system", "user", "assistant"]


# ---------- Helpers ----------

def _messages_to_prompt(messages: List[dict]) -> str:
    """
    Convert chat-style messages into a single text prompt.
    Used for Gemini, which accepts plain text (or separate role messages if needed).
    """
    lines = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)


# ---------- Ollama (local Llama 3.1) ----------

async def _call_ollama(messages: List[dict]) -> str:
    """
    Call a local LLM served by Ollama using its OpenAI-compatible API.

    Assumes:
      - Ollama is running on LLAMA_API_BASE_URL (default http://localhost:11434)
      - The model name is in LLAMA_MODEL (e.g. "llama3.1:8b")
    Docs: https://github.com/ollama/ollama/blob/main/docs/openai.md
    """
    base_url = (settings.LLAMA_API_BASE_URL or "http://localhost:11434").rstrip("/")
    model = settings.LLAMA_MODEL or "llama3.1:8b"

    url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": model,
        "messages": messages,  # OpenAI-style: [{role, content}, ...]
        "temperature": 0.2,
    }

    # Ollama doesn't require auth by default, but we keep the header for compatibility
    headers = {
        "Authorization": f"Bearer {settings.LLAMA_API_KEY or 'none'}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # OpenAI-style response: {"choices": [{"message": {"content": "..."}}]}
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        # Fallback so you can inspect unexpected responses
        return str(data)


# ---------- Gemini (HTTP REST API) ----------

async def _call_gemini(messages: List[dict]) -> str:
    """
    Call Gemini via the REST API using httpx.

    Default: v1 endpoint with a model like "gemini-1.5-flash".
    You can override the base URL with GEMINI_API_BASE_URL if needed.
    Docs: https://ai.google.dev/api/rest
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")

    model_name = settings.GEMINI_MODEL or "gemini-1.5-flash"

    # Base URL – can be overridden by env, but usually you don't need to
    base = (settings.GEMINI_API_BASE_URL or "https://generativelanguage.googleapis.com").rstrip("/")

    # v1 models endpoint: /v1/models/{model}:generateContent
    url = f"{base}/v1/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"

    prompt = _messages_to_prompt(messages)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
        return text.strip()
    except (KeyError, IndexError, TypeError):
        # Fallback so you can inspect error payloads
        return str(data)


# ---------- Public dispatcher ----------

async def call_llm(messages: List[dict]) -> str:
    """
    Single entrypoint for the rest of the app.

    Chooses the backend based on `settings.LLM_PROVIDER`:
      - "ollama" or "llama"  -> local Ollama Llama 3.1
      - "gemini"             -> Google Gemini via REST
    """
    provider = (settings.LLM_PROVIDER or "ollama").lower()

    if provider in ("ollama", "llama"):
        return await _call_ollama(messages)
    elif provider == "gemini":
        return await _call_gemini(messages)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")
