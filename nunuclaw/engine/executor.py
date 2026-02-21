"""Task executor — runs task plans step by step with SLM→LLM escalation.

Handles dependencies, retries, escalation, and progress tracking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from nunuclaw.engine.models.router import ModelRouter
from nunuclaw.engine.planner import TaskPlan, TaskStep
from nunuclaw.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executes task plans step by step.

    Features:
    - Sequential execution with dependency resolution
    - SLM→LLM escalation on failure
    - Retry logic with configurable limits
    - Cost tracking per step and per plan
    """

    def __init__(
        self,
        model_router: ModelRouter,
        tool_registry: ToolRegistry,
    ) -> None:
        self.model_router = model_router
        self.tool_registry = tool_registry

    async def execute_plan(self, plan: TaskPlan) -> str:
        """Execute a complete task plan and return the final result.

        Args:
            plan: The task plan to execute.

        Returns:
            The final result text from executing all steps.
        """
        plan.status = "executing"
        results: dict[str, str] = {}
        final_result = ""

        for step in plan.steps:
            # Check dependencies
            for dep_id in step.depends_on:
                dep_step = next((s for s in plan.steps if s.id == dep_id), None)
                if dep_step and dep_step.status != "completed":
                    step.status = "failed"
                    step.error = f"Dependency {dep_id} not completed"
                    continue

            # Execute the step
            result = await self._execute_step(step, results, plan.original_message)

            if step.status == "completed":
                results[step.id] = result
                final_result = result

        # Determine plan status
        failed_steps = [s for s in plan.steps if s.status == "failed"]
        if failed_steps:
            if all(s.status == "failed" for s in plan.steps):
                plan.status = "failed"
            else:
                plan.status = "completed"  # Partial success
        else:
            plan.status = "completed"

        plan.completed_at = datetime.now(timezone.utc)
        plan.total_cost = self.model_router.total_cost

        return final_result

    async def _execute_step(
        self,
        step: TaskStep,
        previous_results: dict[str, str],
        original_message: str,
    ) -> str:
        """Execute a single step with escalation and retry logic."""
        step.status = "running"

        # Handle direct LLM generation (no tool needed)
        if step.tool == "llm_direct":
            return await self._execute_llm_direct(step, original_message)

        # Handle system commands
        if step.tool == "system":
            return await self._execute_system(step)

        # Try to find and execute the tool
        tool = self.tool_registry.get_tool(step.tool)
        if tool:
            try:
                result = await tool.execute(step.action, step.params)
                if result.success:
                    step.status = "completed"
                    step.result = str(result.data) if result.data else ""
                    return step.result
                else:
                    step.error = result.error or "Tool execution failed"
            except Exception as e:
                step.error = str(e)

        # Tool failed or not found — fall back to LLM
        return await self._execute_llm_direct(step, original_message)

    async def _execute_llm_direct(self, step: TaskStep, original_message: str) -> str:
        """Execute a step by directly querying the LLM."""
        prompt = step.params.get("prompt", original_message) or original_message

        system_prompt = (
            "You are NunuClaw, a helpful AI assistant. "
            "Respond concisely and helpfully. "
            "If the user asks you to do something, either do it or explain what you'd do."
        )

        response = await self.model_router.generate(
            prompt=prompt,
            complexity_score=step.model_tier * 2,  # Approximate
            system=system_prompt,
            max_tokens=2048,
            temperature=0.7,
        )

        if response.success:
            step.status = "completed"
            step.result = response.text
            return response.text
        else:
            step.status = "failed"
            step.error = response.error or "LLM generation failed"
            return f"❌ Sorry, I couldn't complete this task. Error: {step.error}"

    async def _execute_system(self, step: TaskStep) -> str:
        """Handle system commands (help, status)."""
        step.status = "completed"

        if step.action == "help":
            step.result = (
                "🦀 **NunuClaw** — I can help you with:\n\n"
                "- **Code**: Write, debug, explain code\n"
                "- **Search**: Find information on the web\n"
                "- **Files**: Create, read, edit files\n"
                "- **Documents**: Create DOCX, PDF, XLSX, PPTX\n"
                "- **Math**: Calculate expressions, convert units\n"
                "- **Reminders**: Set reminders and schedules\n"
                "- **Git**: Commit, push, create PRs\n\n"
                "Just tell me what you need! 😊"
            )
            return step.result

        elif step.action == "status":
            cost = self.model_router.total_cost
            step.result = (
                f"🦀 **NunuClaw Status**\n\n"
                f"- Version: 0.1.0\n"
                f"- Session cost: ${cost:.4f}\n"
                f"- Status: Running ✅\n"
            )
            return step.result

        step.result = "Unknown system command"
        return step.result
