"""LLM adapter — routes to local or remote LLM."""

from .backends import LlamaCppBackend, OpenAICompatibleBackend
from .config import PromoterConfig


class LLMAdapter:
    """Unified interface for local and remote LLMs.

    Provider presets:
    - openai    -> https://api.openai.com/v1
    - deepseek  -> https://api.deepseek.com
    - kimi      -> https://api.moonshot.cn/v1
    - llamacpp  -> local .gguf file via llama_cpp_python
    - none      -> disabled (rule-based fallback)

    For llamacpp, set TRUENEX_PROMOTER_LLM_MODEL_PATH to the .gguf file.
    If both base_url and model_path are set, base_url takes priority
    (HTTP server mode).
    """

    _PRESET_URLS: dict[str, str] = {
        "openai": "https://api.openai.com/v1",
        "deepseek": "https://api.deepseek.com",
        "kimi": "https://api.moonshot.cn/v1",
    }

    def __init__(self, config: PromoterConfig) -> None:
        self.config = config
        self.backend: LlamaCppBackend | OpenAICompatibleBackend | None = None
        if config.llm_provider != "none":
            self.backend = self._create_backend()

    def _create_backend(self) -> LlamaCppBackend | OpenAICompatibleBackend:
        provider = self.config.llm_provider

        # llama.cpp direct mode (local .gguf)
        if provider == "llamacpp":
            if self.config.llm_model_path:
                return LlamaCppBackend(
                    model_path=self.config.llm_model_path,
                    n_gpu_layers=self.config.llm_n_gpu_layers,
                    n_ctx=self.config.llm_n_ctx,
                    temperature=self.config.llm_temperature,
                    max_tokens=self.config.llm_max_tokens,
                )
            # Fallback to HTTP server mode
            base_url = self.config.llm_base_url or "http://localhost:8080/v1"
            return OpenAICompatibleBackend(
                base_url=base_url,
                api_key=self.config.llm_api_key,
                model=self.config.llm_model or "llama",
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
            )

        # Remote API mode
        base_url = self.config.llm_base_url or self._PRESET_URLS.get(provider, "")
        if not base_url:
            raise ValueError(
                f"Provider '{provider}' has no preset URL. "
                f"Set TRUENEX_PROMOTER_LLM_BASE_URL or use a known provider."
            )
        if not self.config.llm_model:
            raise ValueError(
                f"Provider '{provider}' requires a model name. "
                f"Set TRUENEX_PROMOTER_LLM_MODEL."
            )
        return OpenAICompatibleBackend(
            base_url=base_url,
            api_key=self.config.llm_api_key,
            model=self.config.llm_model,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
        )

    def is_available(self) -> bool:
        """Return True if an LLM is configured and reachable."""
        if self.backend is None:
            return False
        return self.backend.health_check()

    def generate(self, system_prompt: str, user_prompt: str) -> str | None:
        """Generate text via LLM. Returns None if no LLM configured."""
        if self.backend is None:
            return None
        return self.backend.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
