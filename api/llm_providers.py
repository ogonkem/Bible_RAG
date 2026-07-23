"""
LLM Provider abstraction — swap between Ollama (local, any model),
Anthropic Claude, or OpenAI ChatGPT via a single environment variable.

Usage:
    from api.llm_providers import get_llm_provider
    provider = get_llm_provider()
    for token in provider.generate_stream(prompt):
        ...
    answer = provider.generate(prompt)  # non-streaming convenience wrapper

Environment variables (set in .env):
    LLM_PROVIDER=ollama          # ollama | anthropic | openai
    OLLAMA_MODEL=mistral         # or llama3, llama2, phi3, etc. — any model pulled into Ollama
    ANTHROPIC_API_KEY=sk-ant-...
    ANTHROPIC_MODEL=claude-sonnet-4-5
    OPENAI_API_KEY=sk-...
    OPENAI_MODEL=gpt-4o-mini
"""

import json
import os
from abc import ABC, abstractmethod

import requests


class LLMProvider(ABC):
    @abstractmethod
    def generate_stream(self, prompt: str):
        """Yield successive text chunks for a given prompt."""
        raise NotImplementedError

    def generate(self, prompt: str) -> str:
        """Return the full generated text by consuming the stream."""
        return ''.join(self.generate_stream(prompt)).strip()


class OllamaProvider(LLMProvider):
    """
    Local, free. Works with ANY model you've pulled into Ollama —
    mistral, llama3, llama2, phi3, gemma, etc. Just change OLLAMA_MODEL.
    """

    def __init__(self):
        self.model = os.getenv('OLLAMA_MODEL', 'mistral')
        self.base_url = os.getenv('OLLAMA_URL', 'http://ollama:11434')
        # Ollama unloads an idle model after ~5 min by default; reloading
        # multi-GB weights from disk on the next request measured ~96s on
        # this CPU box before the first token streams. keep_alive keeps
        # the model resident so that cold load only happens once.
        self.keep_alive = os.getenv('OLLAMA_KEEP_ALIVE', '30m')

    def generate_stream(self, prompt: str):
        # (connect_timeout, per-chunk read timeout) — each token only
        # needs to arrive within read_timeout of the previous one, not
        # within one global deadline. read_timeout must still cover a
        # worst-case cold model load (see keep_alive above), hence 120s
        # rather than a value tuned for steady-state token gaps.
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "keep_alive": self.keep_alive,
            },
            stream=True,
            timeout=(10, 120),
        )
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            text = chunk.get('response')
            if text:
                yield text
            if chunk.get('done'):
                break


class AnthropicProvider(LLMProvider):
    """Claude via the Anthropic API. Requires ANTHROPIC_API_KEY."""

    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.model = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-5')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

    def generate_stream(self, prompt: str):
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        with client.messages.stream(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text


class OpenAIProvider(LLMProvider):
    """ChatGPT via the OpenAI API. Requires OPENAI_API_KEY."""

    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

    def generate_stream(self, prompt: str):
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        stream = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


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
