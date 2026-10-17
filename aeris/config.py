from __future__ import annotations

import json
import os
import sys
import tempfile
import warnings
from dataclasses import asdict, dataclass, replace
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
    return existing


def resource_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    project_root = Path(__file__).resolve().parent.parent
    if (project_root / "config" / "apps.windows.json").is_file():
        return project_root
    return Path(__file__).resolve().parent / "resources"


def _atomic_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".settings-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class SettingsRecoveryError(RuntimeError):
    """Credential and settings publication could not be confirmed together."""


def _credential_recovery_file(data_dir: Path) -> Path:
    return data_dir / "credential-recovery.json"


def _credential_recovery_message() -> str:
    return (
        "Credential/settings recovery is required. Simulation enabled; AI and listening disabled. "
        "Repair credential storage, then explicitly replace or clear the Gemini key and save Settings. "
        "Existing files are preserved."
    )


@dataclass
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
    hands_free: bool = False
    wake_word: str = "aeris"
    startup_greeting: bool = True
    coding_workspace: Path = Path.home() / "Documents" / "Aeris Projects"
    recovery_message: str = ""
    timezone_name: str = "Asia/Kolkata"
    automation_mode: str = 'task'

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
        
        settings_file = data_dir / "settings.json"
        settings = {}
        recovery_message = ""
        if settings_file.exists():
            try:
                settings = json.loads(settings_file.read_text(encoding="utf-8"))
                if not isinstance(settings, dict):
                    raise ValueError("Settings must be an object")
                for name in ("dry_run", "ai_enabled", "hands_free", "startup_greeting", "require_signed_installers"):
                    if name in settings and type(settings[name]) is not bool:
                        raise ValueError("Invalid saved boolean")
                for name, minimum, maximum in (("voice_record_seconds", 2, 30), ("max_download_mb", 1, 2048)):
                    if name in settings and (type(settings[name]) is not int or not minimum <= settings[name] <= maximum):
                        raise ValueError("Invalid saved numeric bound")
                for name in ("allowed_paths", "allowed_domains", "voice_device", "voice_language", "voice_model", "wake_word",
                             "coding_workspace", "download_dir", "gemini_model", "gmail_credentials_file",
                             "app_catalog_file", "package_catalog_file", "timezone_name"):
                    if name in settings and not isinstance(settings[name], str):
                        raise ValueError("Invalid saved string")
                if "voice_device" in settings and settings["voice_device"] not in {"cpu", "cuda", "auto"}:
                    raise ValueError("Invalid saved device")
                if "wake_word" in settings and not 1 <= len(settings["wake_word"].strip()) <= 80:
                    raise ValueError("Invalid saved wake phrase")
                if 'automation_mode' in settings and (not isinstance(settings['automation_mode'], str) or settings['automation_mode'] not in {'assist', 'task', 'trusted'}):
                    raise ValueError('Invalid automation mode')
            except (OSError, ValueError):
                warnings.warn("Settings unreadable: simulation enabled and file access disabled.", RuntimeWarning)
                recovery_message = "Settings are invalid. Original file preserved. Simulation, AI and listening disabled; repair settings.json."
                settings = {"allowed_paths": "", "dry_run": True, "hands_free": False, "ai_enabled": False}
        # Validate effective environment values before converting them. Saved settings
        # retain precedence. Never interpret an unknown boolean as permission for live use.
        invalid_environment = False
        if 'automation_mode' not in settings and os.getenv('AERIS_AUTOMATION_MODE', 'task') not in {'assist', 'task', 'trusted'}:
            invalid_environment = True
        for key, env_key in (("dry_run", "AERIS_DRY_RUN"), ("ai_enabled", "AERIS_AI_ENABLED"),
                             ("hands_free", "AERIS_HANDS_FREE"), ("startup_greeting", "AERIS_STARTUP_GREETING"),
                             ("require_signed_installers", "AERIS_REQUIRE_SIGNED_INSTALLERS")):
            value = os.getenv(env_key)
            if key not in settings and value is not None and value.strip().lower() not in {"1", "true", "yes", "on", "0", "false", "no", "off"}:
                invalid_environment = True
        for key, env_key, minimum, maximum in (("voice_record_seconds", "AERIS_VOICE_SECONDS", 2, 30),
                                                ("max_download_mb", "AERIS_MAX_DOWNLOAD_MB", 1, 2048)):
            value = os.getenv(env_key)
            if key not in settings and value is not None:
                try:
                    if not minimum <= int(value) <= maximum:
                        invalid_environment = True
                except ValueError:
                    invalid_environment = True
        if "voice_device" not in settings and os.getenv("AERIS_VOICE_DEVICE", "cpu").strip().lower() not in {"cpu", "cuda", "auto"}:
            invalid_environment = True
        if "wake_word" not in settings and not 1 <= len(os.getenv("AERIS_WAKE_WORD", "aeris").strip()) <= 80:
            invalid_environment = True
        if invalid_environment:
            recovery_message = "Environment settings are invalid. Simulation enabled; AI, listening and file access disabled. Repair AERIS_* values or save valid Settings."
            settings.update({"allowed_paths": "", "dry_run": True, "ai_enabled": False, "hands_free": False,
                             "voice_record_seconds": 6, "max_download_mb": 2048, "voice_device": "cpu", "wake_word": "aeris"})
            settings['automation_mode'] = 'assist'

        from .secrets import read_key, write_key
        recovery_file = _credential_recovery_file(data_dir)
        # Existence, rather than trusting journal contents, is sufficient. A
        # crash between the keyring and settings writes cannot prove agreement.
        credential_unavailable = recovery_file.exists() or recovery_file.is_symlink()
        stored_key = None
        if credential_unavailable:
            recovery_message = _credential_recovery_message()
            settings.update({"dry_run": True, "ai_enabled": False, "hands_free": False})
        else:
            try:
                legacy_key = settings.get("gemini_api_key")
                if legacy_key:
                    write_key(data_dir, legacy_key)
                    migrated = {key: value for key, value in settings.items() if key != "gemini_api_key"}
                    _atomic_settings(settings_file, migrated)
                    settings = migrated
                stored_key = read_key(data_dir)
            except (RuntimeError, OSError):
                # Keep original legacy settings on migration failure; never use an env key
                # to silently bypass a failed credential backend.
                credential_unavailable = True
                recovery_message = "Credential storage is unavailable. Text commands remain available in simulation; AI and listening disabled. Repair the OS keyring backend, then retry Settings. Original data preserved."
                settings.update({"dry_run": True, "ai_enabled": False, "hands_free": False})
                
        def get_val(key: str, env_key: str, default: str) -> str:
            if key in settings and settings[key] is not None:
                return str(settings[key])
            val = os.getenv(env_key)
            return val if val is not None else default
            
        def get_bool(key: str, env_key: str, default: bool) -> bool:
            if key in settings and settings[key] is not None:
                return str(settings[key]).strip().lower() in {"1", "true", "yes", "on", "true"} if isinstance(settings[key], str) else bool(settings[key])
            return _env_bool(env_key, default)

        configured_paths = get_val("allowed_paths", "AERIS_ALLOWED_PATHS", "").strip()
        if configured_paths:
            allowed_paths = tuple(
                Path(item).expanduser().resolve()
                for item in configured_paths.split(os.pathsep)
                if item.strip()
            )
        else:
            allowed_paths = () if "allowed_paths" in settings else _default_allowed_paths()

        domains = tuple(
            item.strip().lower()
            for item in get_val("allowed_domains", "AERIS_ALLOWED_DOMAINS", "*").split(",")
            if item.strip()
        ) or ("*",)

        data_dir.mkdir(parents=True, exist_ok=True)
        from .reminders import reminder_timezone
        try:
            reminder_timezone(get_val("timezone_name", "AERIS_TIMEZONE", "Asia/Kolkata"))
        except ValueError:
            recovery_message = "Reminder timezone is invalid or unavailable. Simulation enabled; AI/listening disabled. Choose a supported timezone in Settings."
            settings.update({"timezone_name": "Asia/Kolkata", "dry_run": True, "ai_enabled": False, "hands_free": False})
        config = cls(
            data_dir=data_dir,
            recovery_message=recovery_message,
            timezone_name=get_val("timezone_name", "AERIS_TIMEZONE", "Asia/Kolkata"),
            automation_mode=get_val('automation_mode', 'AERIS_AUTOMATION_MODE', 'task'),
            allowed_paths=allowed_paths,
            dry_run=get_bool("dry_run", "AERIS_DRY_RUN", True),
            ai_enabled=get_bool("ai_enabled", "AERIS_AI_ENABLED", True),
            gemini_api_key=None if credential_unavailable else stored_key or (None if settings.get("gemini_key_cleared") else os.getenv("GEMINI_API_KEY")) or None,
            gemini_model=get_val("gemini_model", "AERIS_GEMINI_MODEL", "gemini-3.6-flash"),
            allowed_domains=domains,
            voice_model=get_val("voice_model", "AERIS_VOICE_MODEL", "small"),
            voice_record_seconds=max(2, int(get_val("voice_record_seconds", "AERIS_VOICE_SECONDS", "6"))),
            voice_device=get_val("voice_device", "AERIS_VOICE_DEVICE", "cpu").strip().lower(),
            voice_language=get_val("voice_language", "AERIS_VOICE_LANGUAGE", "en").strip().lower(),
            gmail_credentials_file=Path(
                get_val("gmail_credentials_file", "AERIS_GMAIL_CREDENTIALS", "credentials.json")
            ).expanduser(),
            app_catalog_file=Path(get_val("app_catalog_file", "AERIS_APP_CATALOG", str(resource_root() / "config/apps.windows.json"))).expanduser(),
            package_catalog_file=Path(
                get_val("package_catalog_file", "AERIS_PACKAGE_CATALOG", str(resource_root() / "config/packages.windows.json"))
            ).expanduser(),
            download_dir=Path(
                get_val("download_dir", "AERIS_DOWNLOAD_DIR", str(Path.home() / "Downloads"))
            ).expanduser().resolve(),
            max_download_mb=max(1, int(get_val("max_download_mb", "AERIS_MAX_DOWNLOAD_MB", "2048"))),
            require_signed_installers=get_bool("require_signed_installers", "AERIS_REQUIRE_SIGNED_INSTALLERS", True),
            hands_free=get_bool("hands_free", "AERIS_HANDS_FREE", False),
            wake_word=get_val("wake_word", "AERIS_WAKE_WORD", "aeris").strip().lower() or "aeris",
            startup_greeting=get_bool("startup_greeting", "AERIS_STARTUP_GREETING", True),
            coding_workspace=Path(
                get_val("coding_workspace", "AERIS_CODING_WORKSPACE", str(Path.home() / "Documents" / "Aeris Projects"))
            ).expanduser().resolve(),
        )
        config.validate()
        return config

    def validate(self) -> None:
        from .reminders import reminder_timezone
        reminder_timezone(self.timezone_name)
        if self.automation_mode not in {'assist', 'task', 'trusted'}:
            raise ValueError('Unsupported automation mode')
        for name in ("dry_run", "ai_enabled", "hands_free", "startup_greeting", "require_signed_installers"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        if not 2 <= self.voice_record_seconds <= 30 or not 1 <= self.max_download_mb <= 2048:
            raise ValueError("Voice duration or download size is out of bounds")
        if self.voice_device not in {"cpu", "cuda", "auto"}:
            raise ValueError("Unsupported voice device")
        if not self.wake_word.strip() or len(self.wake_word) > 80:
            raise ValueError("Wake phrase must contain 1–80 characters")

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
            "timezone_name": self.timezone_name,
        }

    def save(self) -> None:
        self.validate()
        settings_file = self.data_dir / "settings.json"
        
        # Merge with existing
        settings = {}
        if settings_file.exists():
            try:
                settings = json.loads(settings_file.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ValueError("Settings file is unreadable. Original preserved; repair it before saving.") from exc
                
        if not isinstance(settings, dict):
            raise ValueError("Existing settings must be an object")
        from .secrets import read_key, write_key
        previous_key = read_key(self.data_dir)
        settings.pop("gemini_api_key", None)
        for key, value in asdict(self).items():
            if key in {"gemini_api_key", "data_dir", "recovery_message"}:
                continue
            if isinstance(value, Path):
                value = str(value)
            elif key == "allowed_paths":
                value = os.pathsep.join(str(path) for path in value)
            elif key == "allowed_domains":
                value = ",".join(value)
            settings[key] = value
        settings["gemini_key_cleared"] = not bool(self.gemini_api_key)
        recovery_file = _credential_recovery_file(self.data_dir)
        recovery_was_pending = recovery_file.exists() or recovery_file.is_symlink()
        # A secret-free intent journal is durable before any key mutation. It
        # deliberately contains neither old/new credentials nor their hashes.
        _atomic_settings(recovery_file, {"version": 1, "state": "credential_settings_update_pending"})
        try:
            write_key(self.data_dir, self.gemini_api_key)
            _atomic_settings(settings_file, settings)
        except Exception as save_error:
            try:
                write_key(self.data_dir, previous_key)
            except Exception as exc:
                raise SettingsRecoveryError(_credential_recovery_message()) from exc
            if recovery_was_pending:
                # Restoring the previous key cannot resolve a transaction that
                # was already uncertain before this explicit retry began.
                raise SettingsRecoveryError(_credential_recovery_message()) from save_error
            try:
                recovery_file.unlink()
            except OSError as exc:
                raise SettingsRecoveryError(_credential_recovery_message()) from exc
            raise
        try:
            recovery_file.unlink()
        except OSError as exc:
            raise SettingsRecoveryError(_credential_recovery_message()) from exc
