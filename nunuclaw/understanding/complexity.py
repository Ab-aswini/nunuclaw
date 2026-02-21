"""Complexity scoring — rates task complexity on a 1-10 scale.

The score determines which model tier handles the task.
Based on the algorithm defined in PRD Section 6.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComplexityScore:
    """Result of complexity analysis."""

    score: int               # 1-10
    recommended_tier: int    # 1-4
    factors: dict[str, int]  # Breakdown of contributing factors
    explanation: str         # Human-readable explanation


def score_complexity(
    text: str,
    requires_web: bool = False,
    requires_file: bool = False,
    requires_code: bool = False,
    requires_multi_domain: bool = False,
    content_length: str = "short",     # "short", "medium", "long"
    accuracy_critical: bool = False,
    num_steps_estimate: int = 1,
) -> ComplexityScore:
    """Score the complexity of a task on a 1-10 scale.

    Uses the algorithm from PRD Section 6:
    - Number of steps (+1 to +3)
    - Requires web access (+1)
    - Requires file creation (+1)
    - Requires code execution (+2)
    - Requires multi-domain knowledge (+2)
    - Content length (+0 to +2)
    - Accuracy criticality (+0 to +3)

    Args:
        text: The task description text.
        requires_web: Whether the task needs internet access.
        requires_file: Whether the task creates/modifies files.
        requires_code: Whether the task involves code execution.
        requires_multi_domain: Whether the task spans multiple knowledge areas.
        content_length: Expected output length: "short", "medium", "long".
        accuracy_critical: Whether errors would have serious consequences.
        num_steps_estimate: Estimated number of steps to complete.

    Returns:
        ComplexityScore with score, recommended tier, factors breakdown, and explanation.
    """
    factors: dict[str, int] = {}
    score = 0

    # Number of steps
    if num_steps_estimate <= 1:
        factors["steps"] = 1
    elif num_steps_estimate <= 3:
        factors["steps"] = 2
    else:
        factors["steps"] = 3
    score += factors["steps"]

    # Web access
    if requires_web:
        factors["web"] = 1
        score += 1

    # File creation
    if requires_file:
        factors["file"] = 1
        score += 1

    # Code execution
    if requires_code:
        factors["code"] = 2
        score += 2

    # Multi-domain knowledge
    if requires_multi_domain:
        factors["multi_domain"] = 2
        score += 2

    # Content length
    length_scores = {"short": 0, "medium": 1, "long": 2}
    length_score = length_scores.get(content_length, 0)
    if length_score:
        factors["content_length"] = length_score
        score += length_score

    # Accuracy criticality
    if accuracy_critical:
        factors["accuracy"] = 3
        score += 3

    # Clamp to 1-10
    score = max(1, min(10, score))

    # Determine tier
    if score <= 3:
        tier = 1
    elif score <= 5:
        tier = 2
    elif score <= 8:
        tier = 3
    else:
        tier = 4

    # Build explanation
    tier_names = {1: "Local SLM", 2: "Fast Cloud", 3: "Standard LLM", 4: "Premium LLM"}
    explanation = (
        f"Complexity: {score}/10 → Tier {tier} ({tier_names[tier]}). "
        f"Factors: {', '.join(f'{k}={v}' for k, v in factors.items())}"
    )

    return ComplexityScore(
        score=score,
        recommended_tier=tier,
        factors=factors,
        explanation=explanation,
    )


def quick_score(text: str) -> ComplexityScore:
    """Quick heuristic scoring based on text analysis alone.

    Analyzes keywords and patterns to estimate complexity without
    needing explicit parameter flags. Used as a first-pass scorer.
    """
    text_lower = text.lower()

    # Detect indicators from text content
    requires_web = any(
        w in text_lower
        for w in ["search", "find", "look up", "google", "browse", "fetch", "download", "url"]
    )
    requires_file = any(
        w in text_lower
        for w in ["create file", "save", "write to", "docx", "pdf", "xlsx", "pptx", "document"]
    )
    requires_code = any(
        w in text_lower
        for w in ["code", "debug", "function", "class", "api", "endpoint", "script", "deploy",
                   "python", "javascript", "git", "commit", "push"]
    )
    requires_multi_domain = any(
        w in text_lower
        for w in ["compare", "analyze", "research", "strategy", "plan", "vs", "versus"]
    )

    # Estimate content length from cues
    content_length = "short"
    if any(w in text_lower for w in ["detailed", "comprehensive", "essay", "report", "page"]):
        content_length = "long"
    elif any(w in text_lower for w in ["summarize", "explain", "describe", "list"]):
        content_length = "medium"

    # Estimate steps
    num_steps = 1
    if " and " in text_lower or " then " in text_lower:
        num_steps = max(num_steps, text_lower.count(" and ") + text_lower.count(" then ") + 1)

    accuracy_critical = any(
        w in text_lower
        for w in ["invoice", "bill", "tax", "gst", "financial", "legal", "payment"]
    )

    return score_complexity(
        text=text,
        requires_web=requires_web,
        requires_file=requires_file,
        requires_code=requires_code,
        requires_multi_domain=requires_multi_domain,
        content_length=content_length,
        accuracy_critical=accuracy_critical,
        num_steps_estimate=num_steps,
    )
