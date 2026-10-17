"""Selected local scope eligibility. Broad roots never authorize secret stores."""
import json
import os
import threading
from pathlib import Path

from .config import _atomic_settings


def protected_target(path):
    parts = [part.casefold() for part in Path(path).parts]
    protected = {'.git', '.ssh', '.aws', '.azure', '.gnupg', '.kube', 'credentials',
                 'login data', 'login data-journal', 'web data', 'cookies', 'key4.db',
                 'logins.json', 'credentials.json', 'token.json', 'oauth-token.json',
                 'recovery-keys.txt', 'bitlocker-recovery-key.txt'}
    if any(part in protected or part.startswith('.env') and part != '.env.example' for part in parts):
        return True
    joined = '/'.join(parts)
    if any(fragment in joined for fragment in ('/windows/', '/microsoft/credentials', '/microsoft/protect', '/microsoft/crypto')):
        return True
    if os.name == 'nt' and 'users' in parts:
        index = parts.index('users')
        if index + 1 < len(parts) and parts[index + 1] not in {Path.home().name.casefold(), 'public'}:
            return True
    return False


CAPABILITY_CATEGORIES = {'desktop': 'Applications, windows, audio and display', 'clipboard': 'Clipboard',
                         'files': 'Local files and coding projects', 'browser': 'Browser operations',
                         'downloads': 'Downloads', 'packages': 'Software plans and installations',
                         'email': 'Email account operations', 'calendar': 'Calendar account operations',
                         'vision': 'Screen context and analysis'}


class AccessProfile:
    def __init__(self, path=None):
        self.path = path
        self.disabled = frozenset()
        self.error = ''
        if path and path.exists():
            try:
                values = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(values, list) or any(item not in CAPABILITY_CATEGORIES for item in values):
                    raise ValueError('Malformed capability profile')
                self.disabled = frozenset(values)
            except (OSError, ValueError, TypeError):
                self.disabled = frozenset(CAPABILITY_CATEGORIES)
                self.error = 'Access profile is unreadable. Capability access is disabled; review each category to recover.'

    @staticmethod
    def category(tool):
        if tool.startswith('desktop.clipboard'):
            return 'clipboard'
        if tool.startswith('coding.'):
            return 'files'
        return tool.split('.')[0]

    def allows(self, tool):
        return self.category(tool) not in self.disabled

    def set_enabled(self, category, enabled):
        if category not in CAPABILITY_CATEGORIES:
            raise ValueError('Unknown access category')
        updated = self.disabled - {category} if enabled else self.disabled | {category}
        if not enabled:
            self.disabled = frozenset(updated)
        if self.path:
            _atomic_settings(self.path, sorted(updated))
        self.disabled = frozenset(updated)
        self.error = ''


class ScopePolicy:
    def __init__(self, roots, state_path=None):
        self._lock = threading.RLock()
        self._roots = tuple(Path(root).expanduser().resolve() for root in roots)
        self.revoked = set()
        self.state_path = state_path
        self.error = ''
        if state_path and state_path.exists():
            try:
                payload = json.loads(state_path.read_text(encoding='utf-8'))
                if not isinstance(payload, list) or len(payload) > 256 or any(not isinstance(item, str) or not Path(item).is_absolute() for item in payload):
                    raise ValueError('Invalid revocations')
                self.revoked = {Path(item).resolve() for item in payload}
            except (OSError, ValueError):
                self._roots = ()
                self.error = 'Saved scope revocations are unreadable. File access is disabled; repair access-revocations.json.'

    @property
    def roots(self):
        with self._lock:
            return tuple(root for root in self._roots if root not in self.revoked)

    def replace(self, roots):
        with self._lock:
            self._roots = tuple(Path(root).expanduser().resolve() for root in roots)

    def _save(self, revoked):
        if self.state_path:
            _atomic_settings(self.state_path, sorted(str(item) for item in revoked))

    def allow(self, root):
        with self._lock:
            value = Path(root).resolve()
            updated = self.revoked - {value}
            self._save(updated)
            self.revoked = updated

    def revoke(self, root):
        with self._lock:
            value = Path(root).resolve()
            self.revoked.add(value)
            self._roots = tuple(item for item in self._roots if item != value)
            # Revocation is effective even if persistence fails; report failure to
            # the UI and never silently regrant through unrelated Settings saves.
            self._save(self.revoked)

    def check(self, candidate):
        with self._lock:
            if self.error:
                raise PermissionError(self.error)
            if any(candidate == root or candidate.is_relative_to(root) for root in self.revoked):
                raise PermissionError('This local scope was revoked. Explicitly review access before granting it again.')
            if not any(candidate == root or candidate.is_relative_to(root) for root in self._roots):
                raise PermissionError('This path is outside the granted local scopes.')
        if protected_target(candidate):
            raise PermissionError('Protected credentials, security data or repository internals are excluded from broad file access.')
