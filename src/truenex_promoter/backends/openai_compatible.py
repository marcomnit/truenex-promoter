"""OpenAI-compatible backend (works with OpenAI, DeepSeek, Kimi, llama.cpp)."""

import json
import urllib.error
import urllib.request
from typing import Any


class OpenAICompatibleBackend:
    """Call any OpenAI-compatible API endpoint.

    Supports:
    - OpenAI (https://api.openai.com/v1)
    - DeepSeek (https://api.deepseek.com)
    - Kimi / Moonshot (https://api.moonshot.cn/v1)
    - llama.cpp server (http://localhost:8080/v1)
    - Any other compatible endpoint
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a chat completion request."""
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API error {e.code}: {body}") from e
        except KeyError as e:
            raise RuntimeError(f"Unexpected LLM response format: {e}") from e

    def health_check(self) -> bool:
        """Quick check if the endpoint is reachable."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers={
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False
