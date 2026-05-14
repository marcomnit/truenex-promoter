"""Hardware analyzer — detects GPU, VRAM, RAM, CPU and recommends LLM setup.

Uses only system tools (nvidia-smi, wmic) — zero external dependencies.
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GPUInfo:
    """Information about a single GPU."""

    name: str = ""
    vram_total_mb: int = 0
    vram_free_mb: int = 0
    vram_used_mb: int = 0
    is_external: bool = False  # Heuristic: eGPU detection


@dataclass
class HardwareProfile:
    """Complete hardware profile of the system."""

    gpus: list[GPUInfo] = field(default_factory=list)
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    cpu_cores: int = 0
    cpu_name: str = ""
    platform: str = ""

    @property
    def total_vram_mb(self) -> int:
        return sum(g.vram_total_mb for g in self.gpus)

    @property
    def total_vram_free_mb(self) -> int:
        return sum(g.vram_free_mb for g in self.gpus)

    @property
    def total_memory_mb(self) -> int:
        """Total usable memory = VRAM + system RAM."""
        return self.total_vram_mb + self.ram_total_mb

    def can_run_local(self, vram_required_mb: int) -> bool:
        """Check if local inference is possible.

        For models that fit entirely in VRAM: requires enough VRAM.
        For models with CPU offload: requires total memory (VRAM + RAM).
        """
        # Pure GPU inference
        if self.total_vram_free_mb >= vram_required_mb:
            return True
        # CPU-offload inference: need total memory >= required
        # We assume 70% of RAM is available for model offload
        available_with_offload = self.total_vram_free_mb + int(self.ram_available_mb * 0.7)
        return available_with_offload >= vram_required_mb

    def recommend(self) -> dict[str, Any]:
        """Generate a recommendation based on detected hardware."""
        # Model requirements (in MB)
        MODELS = {
            "nemotron-30b-q4": {
                "name": "Nemotron 3 Nano Omni 30B-A3B (Q4_K_XL)",
                "vram_mb": 25_600,  # ~25 GB
                "speed": "slow with CPU offload",
                "quality": "excellent",
            },
            "nemotron-30b-iq4": {
                "name": "Nemotron 3 Nano Omni 30B-A3B (IQ4_XS)",
                "vram_mb": 12_288,  # ~12 GB
                "speed": "moderate",
                "quality": "very good",
            },
            "nemotron-4b": {
                "name": "Nemotron 3 Nano 4B",
                "vram_mb": 6_144,   # ~6 GB
                "speed": "fast",
                "quality": "good",
            },
            "llama-3-8b-q4": {
                "name": "Llama 3 8B (Q4_K_M)",
                "vram_mb": 5_120,   # ~5 GB
                "speed": "fast",
                "quality": "good",
            },
        }

        recommendations: list[dict[str, Any]] = []
        for key, spec in MODELS.items():
            fits_vram = self.total_vram_free_mb >= spec["vram_mb"]
            fits_offload = self.can_run_local(spec["vram_mb"])
            recommendations.append({
                "key": key,
                **spec,
                "fits_vram": fits_vram,
                "fits_offload": fits_offload,
                "recommendation": (
                    "gpu" if fits_vram else
                    "offload" if fits_offload else
                    "no"
                ),
            })

        # Overall recommendation
        if any(r["recommendation"] == "gpu" for r in recommendations):
            overall = "local_gpu"
        elif any(r["recommendation"] == "offload" for r in recommendations):
            overall = "local_offload"
        else:
            overall = "api_only"

        return {
            "hardware": {
                "gpus": [
                    {
                        "name": g.name,
                        "vram_total_gb": round(g.vram_total_mb / 1024, 1),
                        "vram_free_gb": round(g.vram_free_mb / 1024, 1),
                    }
                    for g in self.gpus
                ],
                "ram_total_gb": round(self.ram_total_mb / 1024, 1),
                "ram_available_gb": round(self.ram_available_mb / 1024, 1),
                "cpu": self.cpu_name,
                "cpu_cores": self.cpu_cores,
            },
            "models": recommendations,
            "overall": overall,
            "advice": self._advice(overall),
        }

    def _advice(self, overall: str) -> str:
        if overall == "local_gpu":
            return (
                "Your GPU has enough VRAM to run models entirely on-device. "
                "Use provider=llamacpp for fastest inference."
            )
        elif overall == "local_offload":
            return (
                "Your GPU is too small for these models, but your system RAM allows "
                "CPU offload. Inference will be slow (~5-20 tokens/sec). "
                "Consider using an API for production, local for testing."
            )
        else:
            return (
                "Your hardware cannot run local LLMs efficiently. "
                "Use an API provider (openai, deepseek, kimi)."
            )


class HardwareAnalyzer:
    """Detect system hardware on Windows."""

    def analyze(self) -> HardwareProfile:
        profile = HardwareProfile()
        profile.platform = "win32"
        profile.gpus = self._detect_gpus()
        profile.ram_total_mb = self._detect_ram_total()
        profile.ram_available_mb = self._detect_ram_available()
        profile.cpu_name, profile.cpu_cores = self._detect_cpu()
        return profile

    def _detect_gpus(self) -> list[GPUInfo]:
        gpus: list[GPUInfo] = []
        if not shutil.which("nvidia-smi"):
            return gpus

        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.free,memory.used",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                return gpus

            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpus.append(
                        GPUInfo(
                            name=parts[0],
                            vram_total_mb=self._parse_mem(parts[1]),
                            vram_free_mb=self._parse_mem(parts[2]),
                            vram_used_mb=self._parse_mem(parts[3]),
                            is_external="eGPU" in parts[0] or "Thunderbolt" in parts[0],
                        )
                    )
        except Exception:
            pass

        return gpus

    def _parse_mem(self, value: str) -> int:
        """Parse '8192 MiB' -> 8192."""
        try:
            return int(value.replace("MiB", "").strip())
        except ValueError:
            return 0

    def _detect_ram_total(self) -> int:
        try:
            result = subprocess.run(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory", "/value"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            for line in result.stdout.split("\n"):
                if "TotalPhysicalMemory" in line:
                    val = line.split("=")[-1].strip()
                    return int(val) // (1024 * 1024)  # bytes -> MB
        except Exception:
            pass
        return 0

    def _detect_ram_available(self) -> int:
        try:
            result = subprocess.run(
                ["wmic", "OS", "get", "FreePhysicalMemory", "/value"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            for line in result.stdout.split("\n"):
                if "FreePhysicalMemory" in line:
                    val = line.split("=")[-1].strip()
                    return int(val) // 1024  # KB -> MB
        except Exception:
            pass
        return 0

    def _detect_cpu(self) -> tuple[str, int]:
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "Name,NumberOfCores", "/value"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            name = ""
            cores = 0
            for line in result.stdout.split("\n"):
                if "Name=" in line:
                    name = line.split("=")[-1].strip()
                elif "NumberOfCores=" in line:
                    cores = int(line.split("=")[-1].strip())
            return name, cores
        except Exception:
            return "", 0


def print_hardware_report() -> None:
    """Print a human-readable hardware report with recommendations."""
    analyzer = HardwareAnalyzer()
    profile = analyzer.analyze()
    rec = profile.recommend()

    hw = rec["hardware"]
    print("=" * 60)
    print("HARDWARE ANALYSIS")
    print("=" * 60)
    print(f"CPU: {hw['cpu']} ({hw['cpu_cores']} cores)")
    print(f"RAM: {hw['ram_total_gb']} GB total, {hw['ram_available_gb']} GB available")

    if hw["gpus"]:
        print("\nGPUs detected:")
        for i, gpu in enumerate(hw["gpus"]):
            print(f"  [{i}] {gpu['name']}")
            print(f"       VRAM: {gpu['vram_total_gb']} GB total, {gpu['vram_free_gb']} GB free")
    else:
        print("\nNo NVIDIA GPUs detected.")

    print("\n" + "-" * 60)
    print("MODEL RECOMMENDATIONS")
    print("-" * 60)

    for model in rec["models"]:
        status = {
            "gpu": "[GPU] Fits entirely in VRAM",
            "offload": "[OFFLOAD] Fits with CPU offload (slow)",
            "no": "[NO] Not enough memory",
        }[model["recommendation"]]
        print(f"\n{model['name']}")
        print(f"  Requires: ~{round(model['vram_mb']/1024)} GB")
        print(f"  Status:   {status}")
        print(f"  Speed:    {model['speed']}")

    print("\n" + "=" * 60)
    print(f"OVERALL: {rec['overall'].upper()}")
    print(rec["advice"])
    print("=" * 60)
