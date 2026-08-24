import os
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    host: str = os.getenv("PI_PUSH_HOST", "0.0.0.0")
    port: int = int(os.getenv("PI_PUSH_PORT", "8000"))
    base_dir: Path = Path(os.getenv("PI_PUSH_BASE_DIR", "./uploads")).resolve()
    allow_absolute_paths: bool = os.getenv("PI_PUSH_ALLOW_ABSOLUTE_PATHS", "true").lower() in ("true", "1", "yes")
    enable_exec: bool = os.getenv("PI_PUSH_ENABLE_EXEC", "true").lower() in ("true", "1", "yes")
    default_exec_timeout: int = int(os.getenv("PI_PUSH_DEFAULT_EXEC_TIMEOUT", "60"))

    def ensure_base_dir(self) -> None:
        """Create base directory if it doesn't already exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_base_dir()
