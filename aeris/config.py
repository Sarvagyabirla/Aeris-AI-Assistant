from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        return


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_data_dir() -> Path:
    if os.name == "nt" and os.getenv("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "Aeris"
    return Path.home() / ".aeris"


def _default_allowed_paths() -> tuple[Path, ...]:
    home = Path.home()
    candidates = [home / "Desktop", home / "Documents", home / "Downloads"]
    existing = tuple(path.resolve() for path in candidates if path.exists())
    return existing or (home.resolve(),)


@dataclass(frozen=True)
class AerisConfig:
    data_dir: Path
    allowed_paths: tuple[Path, ...]
    dry_run: bool = True
    ai_enabled: bool = True
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"
    allowed_domains: tuple[str, ...] = ("*",)
    voice_model: str = "small"
    voice_record_seconds: int = 6
    voice_device: str = "cpu"
    voice_language: str = "en"
    gmail_credentials_file: Path = Path("credentials.json")
    app_catalog_file: Path = Path("config/apps.windows.json")
    package_catalog_file: Path = Path("config/packages.windows.json")
    download_dir: Path = Path.home() / "Downloads"
    max_download_mb: int = 2048
    require_signed_installers: bool = True
    hands_free: bool = True
    wake_word: str = "aeris"
    startup_greeting: bool = True
    coding_workspace: Path = Path.home() / "Documents" / "Aeris Projects"

    @property
    def audit_log(self) -> Path:
        return self.data_dir / "audit.jsonl"

    @property
    def memory_db(self) -> Path:
        return self.data_dir / "memory.sqlite3"

    @classmethod
    def load(cls) -> "AerisConfig":
        _load_dotenv()
        data_dir = Path(os.getenv("AERIS_DATA_DIR", str(_default_data_dir()))).expanduser().resolve()
        configured_paths = os.getenv("AERIS_ALLOWED_PATHS", "").strip()
        if configured_paths:
            allowed_paths = tuple(
                Path(item).expanduser().resolve()
                for item in configured_paths.split(os.pathsep)
                if item.strip()
            )
        else:
            allowed_paths = _default_allowed_paths()

        domains = tuple(
            item.strip().lower()
            for item in os.getenv("AERIS_ALLOWED_DOMAINS", "*").split(",")
            if item.strip()
        ) or ("*",)

        data_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            data_dir=data_dir,
            allowed_paths=allowed_paths,
            dry_run=_env_bool("AERIS_DRY_RUN", True),
            ai_enabled=_env_bool("AERIS_AI_ENABLED", True),
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            gemini_model=os.getenv("AERIS_GEMINI_MODEL", "gemini-3.6-flash"),
            allowed_domains=domains,
            voice_model=os.getenv("AERIS_VOICE_MODEL", "small"),
            voice_record_seconds=max(2, int(os.getenv("AERIS_VOICE_SECONDS", "6"))),
            voice_device=os.getenv("AERIS_VOICE_DEVICE", "cpu").strip().lower(),
            voice_language=os.getenv("AERIS_VOICE_LANGUAGE", "en").strip().lower(),
            gmail_credentials_file=Path(
                os.getenv("AERIS_GMAIL_CREDENTIALS", "credentials.json")
            ).expanduser(),
            app_catalog_file=Path(os.getenv("AERIS_APP_CATALOG", "config/apps.windows.json")).expanduser(),
            package_catalog_file=Path(
                os.getenv("AERIS_PACKAGE_CATALOG", "config/packages.windows.json")
            ).expanduser(),
            download_dir=Path(
                os.getenv("AERIS_DOWNLOAD_DIR", str(Path.home() / "Downloads"))
            ).expanduser().resolve(),
            max_download_mb=max(1, int(os.getenv("AERIS_MAX_DOWNLOAD_MB", "2048"))),
            require_signed_installers=_env_bool("AERIS_REQUIRE_SIGNED_INSTALLERS", True),
            hands_free=_env_bool("AERIS_HANDS_FREE", True),
            wake_word=os.getenv("AERIS_WAKE_WORD", "aeris").strip().lower() or "aeris",
            startup_greeting=_env_bool("AERIS_STARTUP_GREETING", True),
            coding_workspace=Path(
                os.getenv(
                    "AERIS_CODING_WORKSPACE",
                    str(Path.home() / "Documents" / "Aeris Projects"),
                )
            ).expanduser().resolve(),
        )

    def with_overrides(self, **values: object) -> "AerisConfig":
        return replace(self, **values)

    def public_summary(self) -> dict[str, object]:
        return {
            "data_dir": str(self.data_dir),
            "allowed_paths": [str(path) for path in self.allowed_paths],
            "dry_run": self.dry_run,
            "ai_enabled": self.ai_enabled,
            "gemini_configured": bool(self.gemini_api_key),
            "offline_commands_available": True,
            "voice_device": self.voice_device,
            "voice_language": self.voice_language,
            "allowed_domains": list(self.allowed_domains),
            "download_dir": str(self.download_dir),
            "max_download_mb": self.max_download_mb,
            "require_signed_installers": self.require_signed_installers,
            "hands_free": self.hands_free,
            "wake_word": self.wake_word,
            "coding_workspace": str(self.coding_workspace),
        }
