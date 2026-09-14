from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import pydantic

from .audit import AuditLogger
from .models import ActionRequest, ActionResult, PermissionLevel
from .permissions import ApprovalCallback, PermissionEngine

import inspect
ToolHandler = Callable[..., ActionResult]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    permission: PermissionLevel
    handler: ToolHandler
    required_args: tuple[str, ...] = ()
    arguments_schema: dict[str, Any] | None = None
    model: type[pydantic.BaseModel] | None = None

    def public_definition(self) -> dict[str, Any]:
        spec = {
            "name": self.name,
            "description": self.description,
            "permission": self.permission.value,
        }
        if self.model:
            spec["arguments_schema"] = self.model.model_json_schema()
        elif self.arguments_schema:
            spec["arguments_schema"] = self.arguments_schema
        elif self.required_args:
            spec["required_arguments"] = list(self.required_args)
        return spec


class ToolRegistry:
    def __init__(
        self,
        permissions: PermissionEngine,
        audit: AuditLogger,
        dry_run: bool = True,
    ):
        self.permissions = permissions
        self.audit = audit
        self.dry_run = dry_run
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def definitions(self) -> list[dict[str, Any]]:
        return [self._tools[name].public_definition() for name in sorted(self._tools)]

    @staticmethod
    def _audit_request(request: ActionRequest) -> dict[str, Any]:
        return {
            "tool": request.tool,
            "arguments": request.arguments,
            "request_id": request.request_id,
        }

    def execute(
        self,
        request: ActionRequest,
        approval_callback: ApprovalCallback | None = None,
        token: Any = None,
    ) -> ActionResult:
        if token:
            token.raise_if_cancelled()
        spec = self._tools.get(request.tool)
        if not spec:
            result = ActionResult(False, f"Unknown tool: {request.tool}", error="unknown_tool")
            self.audit.write("tool_rejected", request=self._audit_request(request), reason=result.error)
            return result

        if self.permissions.stopped and request.tool not in {"system.resume", "system.status"}:
            result = ActionResult(False, "Aeris is stopped. Say 'resume Aeris' first.", error="kill_switch")
            self.audit.write("tool_rejected", request=self._audit_request(request), reason=result.error)
            return result

        missing = [key for key in spec.required_args if key not in request.arguments]
        if missing:
            result = ActionResult(
                False,
                f"Missing required arguments for {request.tool}: {', '.join(missing)}",
                error="invalid_arguments",
            )
            self.audit.write("tool_rejected", request=self._audit_request(request), reason=result.error)
            return result

        arguments = request.arguments
        if spec.model:
            try:
                # Runtime validation of arguments using Pydantic
                validated = spec.model.model_validate(request.arguments)
                arguments = validated.model_dump()
            except pydantic.ValidationError as e:
                result = ActionResult(False, f"Invalid arguments for {request.tool}: {e}", error="invalid_arguments")
                self.audit.write("tool_rejected", request=self._audit_request(request), reason=result.error)
                return result

        decision = self.permissions.authorize(request, spec.permission, approval_callback)
        if not decision.allowed:
            result = ActionResult(False, decision.reason, error="permission_denied")
            self.audit.write(
                "permission_denied", request=self._audit_request(request), reason=decision.reason
            )
            return result

        never_simulate = {"system.stop", "system.resume", "system.status"}
        if self.dry_run and request.tool not in never_simulate:
            result = ActionResult(True, f"Dry run: would execute {request.preview()}", dry_run=True)
            self.audit.write("tool_dry_run", request=self._audit_request(request))
            return result

        self.audit.write("tool_started", request=self._audit_request(request))
        try:
            if token:
                token.raise_if_cancelled()
            sig = inspect.signature(spec.handler)
            if "token" in sig.parameters:
                result = spec.handler(dict(arguments), token=token)
            else:
                result = spec.handler(dict(arguments))
        except Exception as exc:  # defensive boundary around OS integrations
            result = ActionResult(False, f"{request.tool} failed safely.", error=str(exc))
        self.audit.write(
            "tool_finished",
            request=self._audit_request(request),
            success=result.success,
            message=result.message,
            error=result.error,
        )
        return result
