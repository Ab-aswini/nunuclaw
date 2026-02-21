"""Scheduler tool — set reminders and recurring tasks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from nunuclaw.tools.base import BaseTool, ToolResult


@dataclass
class ScheduledTask:
    """A scheduled reminder or task."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    time: str = ""              # When to trigger (natural language or cron)
    recurring: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SchedulerTool(BaseTool):
    """Manage reminders and scheduled tasks.

    Phase 1: In-memory storage (lost on restart).
    Phase 2+: Persisted to SQLite with cron support.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}

    @property
    def name(self) -> str:
        return "scheduler"

    @property
    def description(self) -> str:
        return "Set reminders and manage scheduled tasks."

    @property
    def actions(self) -> list[str]:
        return ["set_reminder", "list_scheduled", "cancel_scheduled"]

    async def execute(self, action: str, params: dict) -> ToolResult:
        """Execute a scheduler action."""
        if action == "set_reminder":
            return self._set_reminder(params)
        elif action == "list_scheduled":
            return self._list_scheduled()
        elif action == "cancel_scheduled":
            return self._cancel(params)
        else:
            return ToolResult(success=False, error=f"Unknown action: {action}")

    def _set_reminder(self, params: dict) -> ToolResult:
        """Set a new reminder."""
        message = params.get("message", params.get("description", ""))
        time = params.get("time", params.get("when", ""))

        if not message:
            return ToolResult(success=False, error="Missing reminder message")

        task = ScheduledTask(description=message, time=time)
        self._tasks[task.id] = task

        return ToolResult(
            success=True,
            data=f"⏰ Reminder set: **{message}**\nID: {task.id}\nTime: {time or 'not specified'}",
        )

    def _list_scheduled(self) -> ToolResult:
        """List all active scheduled tasks."""
        active = [t for t in self._tasks.values() if t.is_active]

        if not active:
            return ToolResult(success=True, data="No active reminders.")

        lines = ["📋 **Scheduled Tasks:**\n"]
        for task in active:
            lines.append(f"- [{task.id}] {task.description} (at: {task.time or 'unset'})")

        return ToolResult(success=True, data="\n".join(lines))

    def _cancel(self, params: dict) -> ToolResult:
        """Cancel a scheduled task."""
        task_id = params.get("id", "")
        if not task_id:
            return ToolResult(success=False, error="Missing task 'id'")

        task = self._tasks.get(task_id)
        if not task:
            return ToolResult(success=False, error=f"Task {task_id} not found")

        task.is_active = False
        return ToolResult(success=True, data=f"Cancelled reminder: {task.description}")
