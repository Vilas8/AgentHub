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


@dataclass
class ModelResponse:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    provider: str = ""
    finish_reason: str = "stop"


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
            raise RuntimeError("Gemini API key not configured. Set GEMINI_API_KEY in .env")
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
            return ModelResponse(
                content=response.text,
                input_tokens=getattr(usage, "prompt_token_count", 0),
                output_tokens=getattr(usage, "candidates_token_count", 0),
                model=model,
                provider="gemini",
            )
        except Exception as e:
            logger.error("Gemini completion failed", error=str(e))
            raise


class OpenAIAdapter(ModelAdapter):
    provider_name = "openai"

    @property
    def is_available(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def complete(self, system_prompt, user_message, model, max_tokens=4096, temperature=0.7, **kwargs) -> ModelResponse:
        if not self.is_available:
            raise RuntimeError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
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
            return ModelResponse(
                content=choice.message.content or "",
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                model=model,
                provider="openai",
                finish_reason=choice.finish_reason or "stop",
            )
        except Exception as e:
            logger.error("OpenAI completion failed", error=str(e))
            raise


class AnthropicAdapter(ModelAdapter):
    provider_name = "anthropic"

    @property
    def is_available(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    async def complete(self, system_prompt, user_message, model, max_tokens=4096, temperature=0.7, **kwargs) -> ModelResponse:
        if not self.is_available:
            raise RuntimeError("Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env")
        try:
            import anthropic  # type: ignore
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = await client.messages.create(
                model=model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=max_tokens,
            )
            content = response.content[0].text if response.content else ""
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
