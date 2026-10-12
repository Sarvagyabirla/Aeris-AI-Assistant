"""Optional OS credential storage; never fall back to plaintext files."""
from pathlib import Path


def _account(data_dir: Path) -> str:
    return str(data_dir.resolve()) + ":gemini"


def read_key(data_dir: Path) -> str | None:
    try:
        import keyring
        return keyring.get_password("Aeris", _account(data_dir))
    except ImportError:
        return None
    except Exception as exc:
        raise RuntimeError("OS credential storage is unavailable; configure its backend.") from exc


def write_key(data_dir: Path, value: str | None) -> None:
    try:
        import keyring
        if value:
            keyring.set_password("Aeris", _account(data_dir), value)
        elif keyring.get_password("Aeris", _account(data_dir)) is not None:
            keyring.delete_password("Aeris", _account(data_dir))
    except ImportError as exc:
        if value:
            raise RuntimeError("Install keyring to save credentials securely.") from exc
    except Exception as exc:
        raise RuntimeError("Credential update failed; no plaintext fallback was written.") from exc