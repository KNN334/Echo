from pathlib import Path

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
