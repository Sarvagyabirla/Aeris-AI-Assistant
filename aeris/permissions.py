from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Callable

from .models import ActionRequest, PermissionLevel
from .state import app_store

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
        self._session_approvals: dict[str, float] = {}
        self._generation = 0
        self._kill_switch = False
        self._lock = threading.Lock()

    @property
    def stopped(self) -> bool:
        with self._lock:
            return self._kill_switch

    def stop(self) -> None:
        with self._lock:
            self._kill_switch = True
            self._generation += 1
            self._session_approvals.clear()
            app_store.set("kill_switch_active", True)

    def resume(self) -> None:
        with self._lock:
            self._kill_switch = False
            app_store.set("kill_switch_active", False)

    def clear_session(self) -> None:
        with self._lock:
            self._session_approvals.clear()
            self._generation += 1

    def authorize(
        self,
        request: ActionRequest,
        level: PermissionLevel,
        callback: ApprovalCallback | None,
    ) -> AuthorizationDecision:
        if self.stopped and request.tool not in {"system.status", "system.resume"}:
            return AuthorizationDecision(False, "Kill switch is active. Action blocked.")

        if level is PermissionLevel.BLOCKED:
            return AuthorizationDecision(False, "This capability is blocked by the security policy.")

        if level is PermissionLevel.AUTO:
            return AuthorizationDecision(True, "Safe automatic action.")

        if callback is None:
            return AuthorizationDecision(
                False, "Approval is required, but no approval interface is available."
            )

        if level is PermissionLevel.SESSION:
            fingerprint = request.fingerprint()
            with self._lock:
                generation = self._generation
                if self._session_approvals.get(fingerprint, 0) > time.monotonic():
                    return AuthorizationDecision(True, "Approved for this exact scope until expiry.")
            if callback(request, level, request.preview()):
                with self._lock:
                    if self._kill_switch or generation != self._generation or request.fingerprint() != fingerprint:
                        return AuthorizationDecision(False, "Approval invalidated; request a fresh scope.")
                    self._session_approvals[fingerprint] = time.monotonic() + self.approvals.ttl_seconds
                return AuthorizationDecision(True, "Session approval granted.")
            return AuthorizationDecision(False, "Session approval was denied.")

        fingerprint = request.fingerprint()
        with self._lock:
            generation = self._generation
        if not callback(request, level, request.preview()):
            return AuthorizationDecision(False, "Action confirmation was denied.")
        with self._lock:
            if self._kill_switch or generation != self._generation or request.fingerprint() != fingerprint:
                return AuthorizationDecision(False, "Confirmation invalidated; request a fresh preview.")
        token = self.approvals.issue(request)
        if not self.approvals.consume(token, request):
            return AuthorizationDecision(False, "The approval token was invalid or expired.")
        return AuthorizationDecision(True, "Exact action confirmed.")
