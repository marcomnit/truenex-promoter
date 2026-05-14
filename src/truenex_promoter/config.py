"""Configuration for the promoter agent."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PromoterConfig:
    """Promoter agent configuration."""

    # Target repo to promote
    github_owner: str = "marcomnit"
    github_repo: str = "truenex-memory"
    github_token: str = ""

    # Project metadata (used for content generation)
    project_name: str = "Truenex Memory"
    project_description: str = (
        "Local-first, persistent memory store for AI agents with global search and project context."
    )
    project_url: str = "https://memory.truenex.ai"
    project_tags: tuple[str, ...] = ("ai", "memory", "mcp", "agents", "local-first")

    # Monitoring
    check_interval_minutes: int = 60
    star_milestones: tuple[int, ...] = (10, 25, 50, 100, 250, 500, 1000)

    # Paths
    state_dir: Path = Path.home() / ".truenex-promoter"
    log_file: Path = Path.home() / ".truenex-promoter" / "activity.log"

    # LLM configuration
    llm_provider: str = "none"  # none, openai, deepseek, kimi, llamacpp
    llm_base_url: str = ""      # override preset URL
    llm_api_key: str = ""       # API key (empty for local llama.cpp)
    llm_model: str = ""         # e.g. gpt-4, deepseek-chat, llama-3-8b
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    llm_model_path: str = ""      # path to .gguf file (for llamacpp direct)
    llm_n_gpu_layers: int = -1     # -1 = all layers on GPU
    llm_n_ctx: int = 4096

    # Feature toggles
    enable_awesome_finder: bool = True
    enable_social_drafts: bool = True

    @classmethod
    def from_env(cls) -> "PromoterConfig":
        """Load config from environment variables."""
        return cls(
            github_owner=os.getenv("TRUENEX_PROMOTER_OWNER", "marcomnit"),
            github_repo=os.getenv("TRUENEX_PROMOTER_REPO", "truenex-memory"),
            github_token=os.getenv("TRUENEX_PROMOTER_GITHUB_TOKEN", ""),
            project_name=os.getenv("TRUENEX_PROMOTER_PROJECT_NAME", "Truenex Memory"),
            project_description=os.getenv(
                "TRUENEX_PROMOTER_PROJECT_DESCRIPTION",
                "Local-first, persistent memory store for AI agents with global search and project context.",
            ),
            project_url=os.getenv("TRUENEX_PROMOTER_PROJECT_URL", "https://memory.truenex.ai"),
            check_interval_minutes=int(os.getenv("TRUENEX_PROMOTER_INTERVAL", "60")),
            llm_provider=os.getenv("TRUENEX_PROMOTER_LLM_PROVIDER", "none"),
            llm_base_url=os.getenv("TRUENEX_PROMOTER_LLM_BASE_URL", ""),
            llm_api_key=os.getenv("TRUENEX_PROMOTER_LLM_API_KEY", ""),
            llm_model=os.getenv("TRUENEX_PROMOTER_LLM_MODEL", ""),
            llm_temperature=float(os.getenv("TRUENEX_PROMOTER_LLM_TEMPERATURE", "0.7")),
            llm_max_tokens=int(os.getenv("TRUENEX_PROMOTER_LLM_MAX_TOKENS", "2000")),
            llm_model_path=os.getenv("TRUENEX_PROMOTER_LLM_MODEL_PATH", ""),
            llm_n_gpu_layers=int(os.getenv("TRUENEX_PROMOTER_LLM_N_GPU_LAYERS", "-1")),
            llm_n_ctx=int(os.getenv("TRUENEX_PROMOTER_LLM_N_CTX", "4096")),
        )

    def ensure_dirs(self) -> None:
        """Create state and log directories."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
