"""Task planner — breaks parsed intents into executable step plans.

The planner uses the model router to decompose complex tasks into
ordered steps with tool assignments and model tier recommendations.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from nunuclaw.engine.models.router import ModelRouter
from nunuclaw.understanding.intent import ParsedIntent

logger = logging.getLogger(__name__)


@dataclass
class TaskStep:
    """A single executable step in a task plan."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    tool: str = ""                         # Tool name from registry
    action: str = ""                       # Method on the tool
    params: dict = field(default_factory=dict)
    model_tier: int = 1                    # 1-4
    depends_on: list[str] = field(default_factory=list)
    retry_count: int = 2
    timeout_seconds: int = 60
    on_failure: str = "escalate"           # "escalate" | "retry" | "ask_human" | "skip"

    # Runtime state
    status: str = "pending"                # "pending" | "running" | "completed" | "failed"
    result: str = ""
    error: str = ""


@dataclass
class TaskPlan:
    """A complete execution plan for a user request."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    original_message: str = ""
    intent: str = ""
    steps: list[TaskStep] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_time: int = 0                # Seconds
    status: str = "planning"               # "planning" | "executing" | "completed" | "failed"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    total_cost: float = 0.0


_PLANNING_PROMPT = """You are the task planner for NunuClaw AI assistant.
Break the user's request into executable steps.

Available tools: file_manager, web_search, code_tools, calculator, scheduler, system
Available actions per tool:
- file_manager: create_file, read_file, edit_file, delete_file, list_files
- web_search: search, fetch_page
- code_tools: write_code, debug_code, explain_code
- calculator: compute, convert_units
- scheduler: set_reminder, list_scheduled
- system: status, help

User request: {message}
Intent: {intent}

Output a JSON array of steps, each with:
- "description": what this step does
- "tool": tool name
- "action": action name
- "params": dict of params
- "model_tier": 1 (simple) to 4 (complex)

Keep it minimal — as few steps as possible.
Respond with ONLY the JSON array, no other text."""


async def create_plan(
    intent: ParsedIntent,
    original_message: str,
    user_id: str,
    model_router: ModelRouter,
) -> TaskPlan:
    """Create an execution plan from a parsed intent.

    For simple intents (GENERAL_CHAT, HELP, STATUS), creates a single-step plan.
    For complex intents, uses the model to decompose into multiple steps.
    """
    plan = TaskPlan(
        user_id=user_id,
        original_message=original_message,
        intent=intent.intent,
    )

    # Simple intents — single-step plans
    if intent.intent in ("GENERAL_CHAT", "HELP", "STATUS", "FEEDBACK"):
        plan.steps = [_create_simple_step(intent)]
        plan.status = "ready"
        return plan

    # Simple calculator
    if intent.intent == "GENERAL_CHAT" and _is_math_query(original_message):
        plan.steps = [TaskStep(
            description="Calculate the expression",
            tool="calculator",
            action="compute",
            params={"expression": original_message},
            model_tier=1,
        )]
        plan.status = "ready"
        return plan

    # Try AI-powered planning for complex tasks
    prompt = _PLANNING_PROMPT.format(
        message=original_message,
        intent=intent.intent,
    )

    response = await model_router.generate(
        prompt=prompt,
        complexity_score=min(intent.complexity_score, 5),
        system="You are a precise task planner. Output only valid JSON arrays.",
        max_tokens=500,
        temperature=0.3,
    )

    if response.success:
        try:
            json_text = response.text.strip()
            if json_text.startswith("```"):
                json_text = json_text.split("\n", 1)[1].rsplit("```", 1)[0]
            steps_data = json.loads(json_text)

            if isinstance(steps_data, list):
                for i, step_data in enumerate(steps_data):
                    plan.steps.append(TaskStep(
                        description=step_data.get("description", f"Step {i+1}"),
                        tool=step_data.get("tool", ""),
                        action=step_data.get("action", ""),
                        params=step_data.get("params", {}),
                        model_tier=step_data.get("model_tier", intent.recommended_tier),
                    ))

            if plan.steps:
                plan.status = "ready"
                return plan
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse plan JSON: {e}")

    # Fallback: create a single LLM-powered step
    plan.steps = [TaskStep(
        description=f"Process: {original_message}",
        tool="llm_direct",
        action="generate",
        params={"prompt": original_message},
        model_tier=intent.recommended_tier,
    )]
    plan.status = "ready"
    return plan


def _create_simple_step(intent: ParsedIntent) -> TaskStep:
    """Create a single step for simple intents."""
    if intent.intent == "HELP":
        return TaskStep(
            description="Show help information",
            tool="system",
            action="help",
            model_tier=1,
        )
    elif intent.intent == "STATUS":
        return TaskStep(
            description="Show system status",
            tool="system",
            action="status",
            model_tier=1,
        )
    else:
        return TaskStep(
            description="Respond to user",
            tool="llm_direct",
            action="generate",
            params={"prompt": ""},
            model_tier=intent.recommended_tier,
        )


def _is_math_query(text: str) -> bool:
    """Check if the text looks like a math expression."""
    import re
    math_pattern = re.compile(r"^[\d\s\+\-\*/\(\)\.\^%]+$")
    return bool(math_pattern.match(text.strip()))
