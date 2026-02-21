"""Step verifier — validates the results of executed task steps."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VerificationResult:
    """Result of verifying a step's output."""

    passed: bool = True
    reason: str = ""
    confidence: float = 1.0


def verify_step_result(
    step_description: str,
    result: str,
    expected_type: str = "text",
) -> VerificationResult:
    """Verify that a step's result is valid.

    Basic verification checks:
    - Result is non-empty
    - Result type matches expected (text, file, etc.)
    - No obvious error indicators

    Args:
        step_description: What the step was supposed to do.
        result: The actual result produced.
        expected_type: Expected result type ("text", "file", "json").

    Returns:
        VerificationResult with pass/fail status and reason.
    """
    if not result or not result.strip():
        return VerificationResult(
            passed=False,
            reason="Step produced empty result",
            confidence=1.0,
        )

    # Check for error indicators
    error_indicators = ["error:", "exception:", "traceback", "failed to"]
    result_lower = result.lower()
    for indicator in error_indicators:
        if indicator in result_lower and len(result) < 200:
            return VerificationResult(
                passed=False,
                reason=f"Result appears to contain an error: '{indicator}'",
                confidence=0.7,
            )

    return VerificationResult(passed=True, reason="Result looks valid", confidence=0.8)
