"""
Provider-independent AI model adapter interface.

New providers: subclass ModelAdapter and register in ADAPTERS.
Business logic must never reference provider-specific APIs directly.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class ModelProviderError(Exception):
    """Base exception for model provider errors."""
    def __init__(self, message: str, provider: str, status_code: int = 502, retryable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable


class ModelAuthenticationError(ModelProviderError):
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, status_code=401, retryable=False)


class ModelRateLimitError(ModelProviderError):
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, status_code=429, retryable=True)


class ModelContextLengthError(ModelProviderError):
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, status_code=400, retryable=False)


@dataclass
class ModelResponse:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    provider: str = ""
    finish_reason: str = "stop"
    estimated_cost_minor: int = 0


def estimate_cost_minor(provider: str, model: str, input_tokens: int, output_tokens: int) -> int:
    """
    Estimate cost in minor currency units (USD cents) based on standard pricing tiers.
    E.g. $0.50 per 1M tokens -> ~0.00005 cents per token.
    """
    # Flash / 3.5 turbo tier: ~$0.35/1M input, $1.05/1M output
    # Pro / 4o / Claude 3.5 Sonnet tier: ~$3.00/1M input, $15.00/1M output
    is_pro = any(p in model.lower() for p in ["pro", "gpt-4", "sonnet", "opus"])
    if is_pro:
        cost_usd = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)
    else:
        cost_usd = (input_tokens * 0.35 / 1_000_000) + (output_tokens * 1.05 / 1_000_000)

    # Convert to cents (minor unit) rounded up to integer cents (or 1 cent minimum if used)
    cents = round(cost_usd * 100)
    return max(0, int(cents))



class ModelAdapter(ABC):
    """Abstract base for all model providers."""

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> ModelResponse:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...


class GeminiAdapter(ModelAdapter):
    provider_name = "gemini"

    @property
    def is_available(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    async def complete(self, system_prompt, user_message, model, max_tokens=4096, temperature=0.7, **kwargs) -> ModelResponse:
        if not self.is_available:
            raise ModelAuthenticationError("Gemini API key not configured. Set GEMINI_API_KEY in .env", "gemini")
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=settings.GEMINI_API_KEY)
            client = genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
            )
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: client.generate_content(user_message))
            usage = getattr(response, "usage_metadata", None)
            in_tok = getattr(usage, "prompt_token_count", 0) or 0
            out_tok = getattr(usage, "candidates_token_count", 0) or 0
            return ModelResponse(
                content=response.text,
                input_tokens=in_tok,
                output_tokens=out_tok,
                model=model,
                provider="gemini",
                estimated_cost_minor=estimate_cost_minor("gemini", model, in_tok, out_tok),
            )
        except Exception as e:
            err_msg = str(e)
            logger.error("Gemini completion failed", error=err_msg)
            if "quota" in err_msg.lower() or "429" in err_msg:
                raise ModelRateLimitError(f"Gemini rate limit exceeded: {err_msg}", "gemini")
            if "api_key" in err_msg.lower() or "permission" in err_msg.lower():
                raise ModelAuthenticationError(f"Gemini authentication failed: {err_msg}", "gemini")
            raise ModelProviderError(f"Gemini provider error: {err_msg}", "gemini")


class OpenAIAdapter(ModelAdapter):
    provider_name = "openai"

    @property
    def is_available(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def complete(self, system_prompt, user_message, model, max_tokens=4096, temperature=0.7, **kwargs) -> ModelResponse:
        if not self.is_available:
            raise ModelAuthenticationError("OpenAI API key not configured. Set OPENAI_API_KEY in .env", "openai")
        try:
            from openai import AsyncOpenAI  # type: ignore
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            choice = response.choices[0]
            in_tok = response.usage.prompt_tokens if response.usage else 0
            out_tok = response.usage.completion_tokens if response.usage else 0
            return ModelResponse(
                content=choice.message.content or "",
                input_tokens=in_tok,
                output_tokens=out_tok,
                model=model,
                provider="openai",
                finish_reason=choice.finish_reason or "stop",
                estimated_cost_minor=estimate_cost_minor("openai", model, in_tok, out_tok),
            )
        except Exception as e:
            err_msg = str(e)
            logger.error("OpenAI completion failed", error=err_msg)
            if "rate_limit" in err_msg.lower() or "429" in err_msg:
                raise ModelRateLimitError(f"OpenAI rate limit exceeded: {err_msg}", "openai")
            if "auth" in err_msg.lower() or "api_key" in err_msg.lower() or "401" in err_msg:
                raise ModelAuthenticationError(f"OpenAI authentication failed: {err_msg}", "openai")
            raise ModelProviderError(f"OpenAI provider error: {err_msg}", "openai")


class AnthropicAdapter(ModelAdapter):
    provider_name = "anthropic"

    @property
    def is_available(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    async def complete(self, system_prompt, user_message, model, max_tokens=4096, temperature=0.7, **kwargs) -> ModelResponse:
        if not self.is_available:
            raise ModelAuthenticationError("Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env", "anthropic")
        try:
            import anthropic  # type: ignore
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = await client.messages.create(
                model=model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=max_tokens,
            )
            first_block = response.content[0] if response.content else None
            content = getattr(first_block, "text", "") if first_block else ""
            in_tok = response.usage.input_tokens
            out_tok = response.usage.output_tokens
            return ModelResponse(
                content=content,
                input_tokens=in_tok,
                output_tokens=out_tok,
                model=model,
                provider="anthropic",
                finish_reason=response.stop_reason or "stop",
                estimated_cost_minor=estimate_cost_minor("anthropic", model, in_tok, out_tok),
            )
        except Exception as e:
            err_msg = str(e)
            logger.error("Anthropic completion failed", error=err_msg)
            if "rate_limit" in err_msg.lower() or "429" in err_msg:
                raise ModelRateLimitError(f"Anthropic rate limit exceeded: {err_msg}", "anthropic")
            if "authentication" in err_msg.lower() or "401" in err_msg:
                raise ModelAuthenticationError(f"Anthropic authentication failed: {err_msg}", "anthropic")
            raise ModelProviderError(f"Anthropic provider error: {err_msg}", "anthropic")

            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = await client.messages.create(
                model=model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=max_tokens,
            )
            first_block = response.content[0] if response.content else None
            content = getattr(first_block, "text", "") if first_block else ""
            return ModelResponse(
                content=content,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=model,
                provider="anthropic",
                finish_reason=response.stop_reason or "stop",
            )
        except Exception as e:
            logger.error("Anthropic completion failed", error=str(e))
            raise


class OllamaAdapter(ModelAdapter):
    provider_name = "ollama"

    @property
    def is_available(self) -> bool:
        return bool(settings.OLLAMA_BASE_URL)

    async def complete(self, system_prompt, user_message, model, max_tokens=4096, temperature=0.7, **kwargs) -> ModelResponse:
        try:
            import httpx
            payload = {
                "model": model,
                "prompt": f"System: {system_prompt}\n\nUser: {user_message}",
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(f"{settings.OLLAMA_BASE_URL}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return ModelResponse(
                    content=data.get("response", ""),
                    model=model,
                    provider="ollama",
                )
        except Exception as e:
            logger.error("Ollama completion failed", error=str(e))
            raise


class DevelopmentAdapter(ModelAdapter):
    """
    Development-only adapter. Returns clearly labeled simulated responses.
    NEVER use in production. Only active when no real API keys are configured.
    """
    provider_name = "development"

    @property
    def is_available(self) -> bool:
        return True  # Always available as fallback

    async def complete(self, system_prompt, user_message, model, max_tokens=4096, temperature=0.7, **kwargs) -> ModelResponse:
        logger.warning(
            "Using DEVELOPMENT adapter — no real AI provider configured. "
            "Configure an API key in .env for real responses."
        )
        await asyncio.sleep(0.5)  # Simulate latency
        content = (
            f"[DEVELOPMENT ADAPTER — NOT A REAL AI RESPONSE]\n\n"
            f"System prompt received: {system_prompt[:100]}...\n\n"
            f"Your query: {user_message[:200]}\n\n"
            "To get real AI responses, configure one of: GEMINI_API_KEY, OPENAI_API_KEY, "
            "ANTHROPIC_API_KEY, or OLLAMA_BASE_URL in your .env file."
        )
        return ModelResponse(
            content=content,
            input_tokens=len(user_message.split()),
            output_tokens=len(content.split()),
            model=model,
            provider="development",
        )


# Registry of all adapters
_ADAPTERS: dict[str, ModelAdapter] = {
    "gemini": GeminiAdapter(),
    "openai": OpenAIAdapter(),
    "anthropic": AnthropicAdapter(),
    "ollama": OllamaAdapter(),
    "development": DevelopmentAdapter(),
}


def get_model_adapter(provider: str) -> ModelAdapter:
    """Get the best available adapter. Falls back to dev adapter if provider unavailable."""
    adapter = _ADAPTERS.get(provider)
    if adapter and adapter.is_available:
        return adapter

    # Fallback: try any available real provider
    for name in ["gemini", "openai", "anthropic", "ollama"]:
        candidate = _ADAPTERS[name]
        if candidate.is_available:
            logger.warning("Requested provider unavailable, falling back", requested=provider, fallback=name)
            return candidate

    logger.warning("No AI provider configured, using development adapter")
    return _ADAPTERS["development"]


def list_available_providers() -> list[str]:
    return [name for name, adapter in _ADAPTERS.items() if adapter.is_available and name != "development"]
