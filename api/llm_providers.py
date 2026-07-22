"""
LLM Provider abstraction — swap between Ollama (local, any model),
Anthropic Claude, or OpenAI ChatGPT via a single environment variable.

Usage:
    from api.llm_providers import get_llm_provider
    provider = get_llm_provider()
    answer = provider.generate(prompt)

Environment variables (set in .env):
    LLM_PROVIDER=ollama          # ollama | anthropic | openai
    OLLAMA_MODEL=mistral         # or llama3, llama2, phi3, etc. — any model pulled into Ollama
    ANTHROPIC_API_KEY=sk-ant-...
    ANTHROPIC_MODEL=claude-sonnet-4-5
    OPENAI_API_KEY=sk-...
    OPENAI_MODEL=gpt-4o-mini
"""

import os
from abc import ABC, abstractmethod

import requests


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the full generated text for a given prompt."""
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    """
    Local, free. Works with ANY model you've pulled into Ollama —
    mistral, llama3, llama2, phi3, gemma, etc. Just change OLLAMA_MODEL.
    """

    def __init__(self):
        self.model = os.getenv('OLLAMA_MODEL', 'mistral')
        self.base_url = os.getenv('OLLAMA_URL', 'http://ollama:11434')

    def generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get('response', '').strip()


class AnthropicProvider(LLMProvider):
    """Claude via the Anthropic API. Requires ANTHROPIC_API_KEY."""

    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.model = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-5')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

    def generate(self, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()


class OpenAIProvider(LLMProvider):
    """ChatGPT via the OpenAI API. Requires OPENAI_API_KEY."""

    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

    def generate(self, prompt: str) -> str:
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content.strip()


_PROVIDER_REGISTRY = {
    'ollama': OllamaProvider,
    'anthropic': AnthropicProvider,
    'openai': OpenAIProvider,
}


def get_llm_provider() -> LLMProvider:
    """
    Factory: reads LLM_PROVIDER env var and returns the right provider instance.
    Defaults to 'ollama' (free, local) if not set.
    """
    provider_name = os.getenv('LLM_PROVIDER', 'ollama').lower()

    if provider_name not in _PROVIDER_REGISTRY:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider_name}'. "
            f"Choose from: {', '.join(_PROVIDER_REGISTRY.keys())}"
        )

    return _PROVIDER_REGISTRY[provider_name]()
