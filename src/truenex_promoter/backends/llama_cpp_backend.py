"""Direct llama.cpp backend via llama_cpp_python.

Uses llama_cpp.Llama directly (no HTTP server needed).
Keeps the model loaded in memory for fast repeated inference.
"""

import sys
from typing import Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


class LlamaCppBackend:
    """Direct llama.cpp Python backend."""

    def __init__(
        self,
        model_path: str,
        n_gpu_layers: int = -1,
        n_ctx: int = 4096,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> None:
        from llama_cpp import Llama

        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self.temperature = temperature
        self.max_tokens = max_tokens

        print(f"[LlamaCppBackend] Loading {model_path} ...")
        self._llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=False,
        )
        print("[LlamaCppBackend] Model loaded.")

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a chat completion request."""
        response = self._llm.create_chat_completion(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response["choices"][0]["message"]["content"]

    def health_check(self) -> bool:
        """Quick check if the model is loaded."""
        return self._llm is not None
