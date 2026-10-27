"""Settings, read once from the environment (.env is loaded if present)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _set(value: str) -> bool:
    return bool(value) and not value.startswith("your-")


@dataclass(frozen=True)
class Settings:
    sample_mode: bool = field(default_factory=lambda: _bool("SAMPLE_MODE", False))
    domain: str = field(default_factory=lambda: os.getenv("DOMAIN", "admin"))
    data_schema: str = field(default_factory=lambda: os.getenv("DATA_SCHEMA", "osef"))
    # DATA: Zetaris
    zetaris_rest_url: str = field(default_factory=lambda: os.getenv("ZETARIS_REST_URL", "http://localhost:8888/api/v1.0"))
    zetaris_org_id: str = field(default_factory=lambda: os.getenv("ZETARIS_ORG_ID", "1"))
    zetaris_api_key: str = field(default_factory=lambda: os.getenv("ZETARIS_API_KEY", ""))
    zetaris_timeout: float = field(default_factory=lambda: float(os.getenv("ZETARIS_TIMEOUT", "45")))
    # POWER: Meterless Nightshift (OpenAI-compatible)
    meterless_base_url: str = field(default_factory=lambda: os.getenv("METERLESS_BASE_URL", "http://127.0.0.1:8088/v1"))
    meterless_token: str = field(default_factory=lambda: os.getenv("METERLESS_RUNTIME_TOKEN", ""))
    model_fast: str = field(default_factory=lambda: os.getenv("METERLESS_MODEL_FAST", os.getenv("METERLESS_MODEL", "meterless/fast")))
    model_deep: str = field(default_factory=lambda: os.getenv("METERLESS_MODEL_DEEP", os.getenv("METERLESS_MODEL", "meterless/deep")))
    model_judge: str = field(default_factory=lambda: os.getenv("METERLESS_MODEL_JUDGE", os.getenv("METERLESS_MODEL", "meterless/auto")))
    meterless_app: str = field(default_factory=lambda: os.getenv("METERLESS_APP", "osef-hackathon"))
    llm_timeout: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT", "90")))
    record_llm: bool = field(default_factory=lambda: _bool("RECORD_LLM", True))
    # BUILD: Meterless H-MEM engine (Node service wrapping the reference implementation)
    hmem_url: str = field(default_factory=lambda: os.getenv("HMEM_URL", "http://127.0.0.1:8787"))
    hmem_space: str = field(default_factory=lambda: os.getenv("HMEM_SPACE", "default"))
    log_dir: Path = field(default_factory=lambda: ROOT / os.getenv("LOG_DIR", "logs"))

    @property
    def zetaris_ready(self) -> bool:
        return not self.sample_mode and _set(self.zetaris_api_key)

    @property
    def llm_ready(self) -> bool:
        return not self.sample_mode and _set(self.meterless_token)

    @property
    def domain_dir(self) -> Path:
        return ROOT / "domains" / self.domain


SETTINGS = Settings()
