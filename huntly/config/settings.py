from __future__ import annotations
"""Configuration and settings manager for Huntly."""

import os
from pathlib import Path
from typing import Any, Dict, List
import yaml
from dotenv import load_dotenv

# Load .env if present in workspace or user home
load_dotenv()
load_dotenv(Path.home() / ".huntly" / ".env")


class Settings:
    """Manages application settings, defaults, and API credentials."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.home_dir = Path.home() / ".huntly"
        self.home_dir.mkdir(parents=True, exist_ok=True)
        (self.home_dir / "exports").mkdir(parents=True, exist_ok=True)

        self.default_config_path = Path(__file__).resolve().parent / "default.yaml"
        self.user_config_path = config_path or (self.home_dir / "config.yaml")
        self._data: Dict[str, Any] = self._load_merged_config()

    def _load_merged_config(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if self.default_config_path.exists():
            with open(self.default_config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        if self.user_config_path.exists():
            with open(self.user_config_path, "r", encoding="utf-8") as f:
                user_data = yaml.safe_load(f) or {}
                self._deep_update(data, user_data)

        return data

    def _deep_update(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        for k, v in update.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                self._deep_update(base[k], v)
            else:
                base[k] = v

    @property
    def rapidapi_key(self) -> str:
        return os.getenv("RAPIDAPI_KEY", "")

    @property
    def nvidia_api_key(self) -> str:
        return os.getenv("NVIDIA_API_KEY", "")

    @property
    def openrouter_api_key(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", "")

    @property
    def ai_provider(self) -> str:
        return str(self._data.get("ai", {}).get("provider", "nvidia")).lower()

    @property
    def ai_api_key(self) -> str:
        prov = self.ai_provider
        if prov == "ollama":
            return "ollama"
        elif prov == "openrouter":
            return self.openrouter_api_key
        return self.nvidia_api_key

    @property
    def db_path(self) -> Path:
        return self.home_dir / "huntly.db"

    @property
    def resume_path(self) -> Path:
        raw = self._data.get("resume", {}).get("path", "~/Downloads/resume.pdf")
        return Path(os.path.expanduser(raw))

    @property
    def ai_model(self) -> str:
        m = self._data.get("ai", {}).get("model")
        prov = self.ai_provider
        if prov == "ollama" and (not m or "nemotron" in m):
            return "llama3.2"
        elif prov == "openrouter" and (not m or "nemotron" in m):
            return "meta-llama/llama-3.3-70b-instruct"
        if not m or m == "nvidia/nemotron-3-super-120b-a12b":
            return "nvidia/nemotron-3.5-super-vl-120b-a12b"
        return m

    @property
    def ai_base_url(self) -> str:
        url = self._data.get("ai", {}).get("base_url")
        prov = self.ai_provider
        if prov == "ollama" and (not url or "nvidia.com" in url):
            return "http://localhost:11434/v1"
        elif prov == "openrouter" and (not url or "nvidia.com" in url):
            return "https://openrouter.ai/api/v1"
        return url or "https://integrate.api.nvidia.com/v1"

    @property
    def daily_job_limit(self) -> int:
        return int(self._data.get("limits", {}).get("daily_job_limit", 50))

    @property
    def monthly_requests_limit(self) -> int:
        return int(self._data.get("limits", {}).get("monthly_requests_limit", 25))

    @property
    def monthly_jobs_limit(self) -> int:
        return int(self._data.get("limits", {}).get("monthly_jobs_limit", 250))

    @property
    def jobs_per_request(self) -> int:
        return int(
            self._data.get("limits", {}).get(
                "jobs_per_request",
                self._data.get("search", {}).get("jobs_per_request", 10),
            )
        )

    @property
    def match_threshold_green(self) -> int:
        return int(self._data.get("display", {}).get("match_threshold_green", 80))

    @property
    def match_threshold_yellow(self) -> int:
        return int(self._data.get("display", {}).get("match_threshold_yellow", 50))

    @property
    def default_time_frame(self) -> str:
        return self._data.get("search", {}).get("default_time_frame", "24h")

    @property
    def default_location(self) -> str:
        return self._data.get("search", {}).get("default_location", "")

    @property
    def default_remote(self) -> bool:
        return bool(self._data.get("search", {}).get("default_remote", True))

    @property
    def focus_regions(self) -> List[str]:
        return self._data.get("search", {}).get("focus_regions", ["United States", "Europe"])

    def save_user_config(self, updates: Dict[str, Any]) -> None:
        self._deep_update(self._data, updates)
        with open(self.user_config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self._data, f, default_flow_style=False)
