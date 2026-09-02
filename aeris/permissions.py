from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Callable

from .models import ActionRequest, PermissionLevel

ApprovalCallback = Callable[[ActionRequest, PermissionLevel, str], bool]


@dataclass
class ApprovalGrant:
    fingerprint: str
    expires_at: float
    used: bool = False


class ApprovalManager:
    """Issues one-time approvals bound to the exact action and arguments."""

    def __init__(self, ttl_seconds: int = 90):
        self.ttl_seconds = ttl_seconds
        self._grants: dict[str, ApprovalGrant] = {}
        self._lock = threading.Lock()

    def issue(self, request: ActionRequest) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._grants[token] = ApprovalGrant(
                fingerprint=request.fingerprint(),
                expires_at=time.monotonic() + self.ttl_seconds,
            )
        return token

    def consume(self, token: str, request: ActionRequest) -> bool:
        with self._lock:
            grant = self._grants.get(token)
            if not grant or grant.used or grant.expires_at < time.monotonic():
                return False
            if grant.fingerprint != request.fingerprint():
                return False
            grant.used = True
            return True


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


class PermissionEngine:
    def __init__(self, approval_manager: ApprovalManager | None = None):
        self.approvals = approval_manager or ApprovalManager()
        self._session_approvals: set[str] = set()
        self._kill_switch = False
        self._lock = threading.Lock()

    @property
    def stopped(self) -> bool:
        with self._lock:
            return self._kill_switch

    def stop(self) -> None:
        with self._lock:
            self._kill_switch = True

    def resume(self) -> None:
        with self._lock:
            self._kill_switch = False

    def clear_session(self) -> None:
        self._session_approvals.clear()

    def authorize(
        self,
        request: ActionRequest,
        level: PermissionLevel,
        callback: ApprovalCallback | None,
    ) -> AuthorizationDecision:
        if level is PermissionLevel.BLOCKED:
            return AuthorizationDecision(False, "This capability is blocked by the security policy.")

        if level is PermissionLevel.AUTO:
            return AuthorizationDecision(True, "Safe automatic action.")

        if callback is None:
            return AuthorizationDecision(
                False, "Approval is required, but no approval interface is available."
            )

        if level is PermissionLevel.SESSION:
            if request.tool in self._session_approvals:
                return AuthorizationDecision(True, "Approved for this session.")
            if callback(request, level, request.preview()):
                self._session_approvals.add(request.tool)
                return AuthorizationDecision(True, "Session approval granted.")
            return AuthorizationDecision(False, "Session approval was denied.")

        if not callback(request, level, request.preview()):
            return AuthorizationDecision(False, "Action confirmation was denied.")
        token = self.approvals.issue(request)
        if not self.approvals.consume(token, request):
            return AuthorizationDecision(False, "The approval token was invalid or expired.")
        return AuthorizationDecision(True, "Exact action confirmed.")
