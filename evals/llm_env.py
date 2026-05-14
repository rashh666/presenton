"""Build llmai ClientConfig from environment (mirrors servers/fastapi/utils/llm_config.py)."""

from __future__ import annotations

import os
import time

from llmai.shared import (
    AnthropicClientConfig,
    AzureOpenAIClientConfig,
    CerebrasClientConfig,
    ChatGPTClientConfig,
    ClientConfig,
    GoogleClientConfig,
    LiteLLMClientConfig,
    OpenAIApiType,
    OpenAIClientConfig,
    OpenRouterClientConfig,
    VertexAIClientConfig,
)


def _normalize_openai_compatible_base_url(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if not u:
        return u
    if u.endswith("/v1"):
        return u
    base = u.split("?", 1)[0]
    if "/v1" in base:
        return u
    return f"{u}/v1"


def _get_codex_access_token() -> str:
    access_token = (os.environ.get("CODEX_ACCESS_TOKEN") or "").strip()
    if not access_token:
        raise ValueError(
            "Codex OAuth access token is not set (CODEX_ACCESS_TOKEN). "
            "Use another LLM= value for eval runs."
        )
    expires_str = (os.environ.get("CODEX_TOKEN_EXPIRES") or "").strip()
    if expires_str:
        try:
            expires_ms = int(expires_str)
            now_ms = int(time.time() * 1000)
            if now_ms >= expires_ms - 60_000:
                raise ValueError(
                    "Codex access token appears expired; refresh via the app or pick LLM=anthropic/openai."
                )
        except ValueError as e:
            if "Codex access token" in str(e):
                raise
    return access_token


def get_llm_config() -> ClientConfig:
    llm = (os.environ.get("LLM") or "").strip().lower()
    if not llm:
        raise ValueError(
            "LLM is not set. Export LLM (e.g. anthropic, openai) or load userConfig.json via env_sync."
        )

    if llm == "openai":
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        return OpenAIClientConfig(api_key=api_key, api_type=OpenAIApiType.COMPLETIONS)

    if llm == "google":
        api_key = (os.environ.get("GOOGLE_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set")
        return GoogleClientConfig(api_key=api_key)

    if llm == "vertex":
        api_key = (os.environ.get("VERTEX_API_KEY") or "").strip()
        project = (os.environ.get("VERTEX_PROJECT") or "").strip()
        location = (os.environ.get("VERTEX_LOCATION") or "").strip()
        base_url = (os.environ.get("VERTEX_BASE_URL") or "").strip() or None
        if api_key and (project or location):
            raise ValueError(
                "Vertex configuration is ambiguous: use VERTEX_API_KEY OR VERTEX_PROJECT/VERTEX_LOCATION."
            )
        if api_key:
            return VertexAIClientConfig(api_key=api_key, base_url=base_url)
        if not project:
            raise ValueError("Vertex: set VERTEX_API_KEY or VERTEX_PROJECT")
        return VertexAIClientConfig(project=project, location=location or None, base_url=base_url)

    if llm == "azure":
        api_key = (os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
        api_version = (os.environ.get("AZURE_OPENAI_API_VERSION") or "").strip()
        endpoint = (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip()
        base_url = (os.environ.get("AZURE_OPENAI_BASE_URL") or "").strip()
        deployment = (os.environ.get("AZURE_OPENAI_DEPLOYMENT") or "").strip()
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is not set")
        if not api_version:
            raise ValueError("AZURE_OPENAI_API_VERSION is not set")
        if not endpoint and not base_url:
            raise ValueError("AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_BASE_URL is required")
        return AzureOpenAIClientConfig(
            api_key=api_key,
            api_version=api_version,
            endpoint=endpoint or None,
            base_url=base_url or None,
            deployment=deployment or None,
        )

    if llm == "anthropic":
        api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        return AnthropicClientConfig(api_key=api_key)

    if llm == "openrouter":
        api_key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        base_url = (os.environ.get("OPENROUTER_BASE_URL") or "").strip() or None
        return OpenRouterClientConfig(api_key=api_key, base_url=base_url)

    if llm == "cerebras":
        api_key = (os.environ.get("CEREBRAS_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("CEREBRAS_API_KEY is not set")
        base_url = (os.environ.get("CEREBRAS_BASE_URL") or "").strip() or None
        return CerebrasClientConfig(api_key=api_key, base_url=base_url)

    if llm == "litellm":
        base_url = _normalize_openai_compatible_base_url(os.environ.get("LITELLM_BASE_URL") or "")
        if not base_url:
            raise ValueError("LITELLM_BASE_URL is not set")
        lk = (os.environ.get("LITELLM_API_KEY") or "").strip()
        return LiteLLMClientConfig(base_url=base_url, api_key=lk if lk else None)

    if llm == "ollama":
        url = (os.environ.get("OLLAMA_URL") or "http://localhost:11434").strip().rstrip("/")
        return OpenAIClientConfig(base_url=f"{url}/v1", api_key="ollama")

    if llm == "custom":
        base_url = (os.environ.get("CUSTOM_LLM_URL") or "").strip()
        if not base_url:
            raise ValueError("CUSTOM_LLM_URL is not set")
        return OpenAIClientConfig(
            base_url=base_url,
            api_key=(os.environ.get("CUSTOM_LLM_API_KEY") or "").strip() or "null",
        )

    if llm == "codex":
        return ChatGPTClientConfig(
            access_token=_get_codex_access_token(),
            account_id=(os.environ.get("CODEX_ACCOUNT_ID") or "").strip() or None,
        )

    raise ValueError(
        f"Unsupported LLM={llm!r}. Use: openai, google, vertex, azure, openrouter, cerebras, "
        "anthropic, litellm, ollama, custom, codex"
    )


def get_extra_body() -> dict | None:
    if (os.environ.get("LLM") or "").strip().lower() == "custom":
        dt = (os.environ.get("DISABLE_THINKING") or "").strip().lower()
        if dt in {"1", "true", "yes", "on"}:
            return {"enable_thinking": False}
    return None


def get_model() -> str:
    llm = (os.environ.get("LLM") or "").strip().lower()
    override = (os.environ.get("PRESENTON_MODEL") or "").strip()
    if override:
        return override

    if llm == "openai":
        return (os.environ.get("OPENAI_MODEL") or "").strip() or "gpt-4o"
    if llm == "google":
        return (os.environ.get("GOOGLE_MODEL") or "").strip() or "gemini-2.0-flash"
    if llm == "vertex":
        return (os.environ.get("VERTEX_MODEL") or "").strip() or "gemini-2.0-flash"
    if llm == "azure":
        return (
            (os.environ.get("AZURE_OPENAI_MODEL") or "").strip()
            or (os.environ.get("AZURE_OPENAI_DEPLOYMENT") or "").strip()
            or "gpt-4o"
        )
    if llm == "openrouter":
        return (os.environ.get("OPENROUTER_MODEL") or "").strip() or "openai/gpt-4o-mini"
    if llm == "cerebras":
        return (os.environ.get("CEREBRAS_MODEL") or "").strip() or "llama3.1-8b"
    if llm == "anthropic":
        return (os.environ.get("ANTHROPIC_MODEL") or "").strip() or "claude-sonnet-4-20250514"
    if llm == "ollama":
        return (os.environ.get("OLLAMA_MODEL") or "").strip() or "llama3.2"
    if llm == "custom":
        return (os.environ.get("CUSTOM_MODEL") or "").strip() or "gpt-4o-mini"
    if llm == "litellm":
        return (os.environ.get("LITELLM_MODEL") or "").strip() or "gpt-4o-mini"
    if llm == "codex":
        return (os.environ.get("CODEX_MODEL") or "").strip() or "gpt-5.1"
    return "gpt-4o"
