"""Task history — log and retrieve past task executions."""

from __future__ import annotations

from nunuclaw.memory.store import MemoryStore


class TaskHistory:
    """Manages task history for learning and pattern detection."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def log_task(
        self,
        task_id: str,
        user_id: str,
        message: str,
        intent: str,
        status: str,
        result: str = "",
        cost: float = 0.0,
        duration: int = 0,
    ) -> None:
        """Log a completed task."""
        await self.store.save_task(
            task_id=task_id,
            user_id=user_id,
            message=message,
            intent=intent,
            status=status,
            result=result,
            cost=cost,
            duration=duration,
        )

    async def get_recent(self, user_id: str, limit: int = 10) -> list[dict]:
        """Get recent tasks for a user."""
        return await self.store.get_recent_tasks(user_id, limit)
