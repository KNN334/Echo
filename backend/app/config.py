import json
from pathlib import Path
from typing import Annotated

from pydantic import PositiveInt, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ECHO_", env_file=".env", extra="ignore")

    reports_dir: Path = ROOT / "reports" / "full_baseline"
    dra_results_file: Path = ROOT / "reports" / "lvseg_ablation" / "results.json"
    camus_assets_dir: Path = ROOT / "web" / "src" / "assets"
    upload_dir: Path = ROOT / "backend" / "data" / "uploads"
    uploads_enabled: bool = False
    upload_max_bytes: PositiveInt = 50 * 1024 * 1024
    upload_formats: list[str] = [".png", ".jpg", ".jpeg", ".avi", ".mp4", ".zip"]
    inference_checkpoint: Path | None = None
    inference_sha256: str | None = None
    inference_max_frames: PositiveInt = 300
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            value = json.loads(value) if value.lstrip().startswith("[") else value.split(",")
        return [item.strip().rstrip("/") for item in value if item.strip()]
