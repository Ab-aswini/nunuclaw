"""Intent classification and entity extraction.

Uses an SLM/LLM to classify user messages into intent categories
and extract relevant entities. No separate ML model needed.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from nunuclaw.engine.models.router import ModelRouter
from nunuclaw.understanding.complexity import quick_score

logger = logging.getLogger(__name__)

# All supported intent categories (from PRD Section 7.2)
INTENT_CATEGORIES = [
    # Communication
    "SEND_MESSAGE", "REPLY_MESSAGE", "DRAFT_MESSAGE", "READ_MESSAGES",
    # Document creation
    "CREATE_DOCX", "CREATE_XLSX", "CREATE_PDF", "CREATE_PPTX", "CREATE_TEXT",
    # Research
    "WEB_SEARCH", "SUMMARIZE", "COMPARE", "FACT_CHECK",
    # Code
    "WRITE_CODE", "DEBUG_CODE", "EXPLAIN_CODE", "DEPLOY_CODE", "GIT_OPERATION",
    # Scheduling
    "SET_REMINDER", "SET_RECURRING", "BOOK_APPOINTMENT", "CHECK_CALENDAR",
    # File operations
    "READ_FILE", "EDIT_FILE", "ORGANIZE_FILES", "CONVERT_FILE", "DOWNLOAD_FILE",
    # System
    "STATUS", "MEMORY_UPDATE", "PREFERENCE_SET", "HELP", "FEEDBACK",
    # General
    "GENERAL_CHAT",
]

# Tools typically needed for each intent
INTENT_TOOLS: dict[str, list[str]] = {
    "WRITE_CODE": ["code_tools", "file_manager"],
    "DEBUG_CODE": ["code_tools", "file_manager"],
    "EXPLAIN_CODE": ["code_tools"],
    "DEPLOY_CODE": ["code_tools", "deploy_tool"],
    "GIT_OPERATION": ["git_manager"],
    "WEB_SEARCH": ["web_search"],
    "SUMMARIZE": ["web_search"],
    "COMPARE": ["web_search"],
    "CREATE_DOCX": ["document_maker", "file_manager"],
    "CREATE_XLSX": ["document_maker", "file_manager"],
    "CREATE_PDF": ["document_maker", "file_manager"],
    "CREATE_PPTX": ["document_maker", "file_manager"],
    "CREATE_TEXT": ["file_manager"],
    "SET_REMINDER": ["scheduler"],
    "SET_RECURRING": ["scheduler"],
    "READ_FILE": ["file_manager"],
    "EDIT_FILE": ["file_manager"],
    "SEND_MESSAGE": ["messenger"],
    "STATUS": ["system"],
    "HELP": ["system"],
}


@dataclass
class ParsedIntent:
    """Result of intent classification and entity extraction."""

    intent: str = "GENERAL_CHAT"
    entities: dict = field(default_factory=dict)
    complexity_score: int = 3
    recommended_tier: int = 1
    language: str = "en"
    requires_tools: list[str] = field(default_factory=list)
    raw_response: str = ""


_CLASSIFICATION_PROMPT = """You are an intent classifier for NunuClaw AI assistant.
Analyze the user's message and output a JSON object with these fields:
- "intent": One of the following categories: {categories}
- "entities": A dict of extracted entities (topic, format, language, framework, etc.)
- "content_length": "short", "medium", or "long" — expected output length

User message: {message}

Respond with ONLY valid JSON, no other text."""


async def classify_intent(
    text: str,
    language: str,
    model_router: ModelRouter,
) -> ParsedIntent:
    """Classify the intent of a user message.

    Uses the model router to classify with the cheapest available model.
    Falls back to keyword-based classification if no model is available.

    Args:
        text: The user's message text.
        language: Detected language code.
        model_router: The model router for AI-powered classification.

    Returns:
        ParsedIntent with classified intent, entities, complexity, and tool requirements.
    """
    # First, get a quick complexity score from text heuristics
    complexity = quick_score(text)

    # Try AI-powered classification
    prompt = _CLASSIFICATION_PROMPT.format(
        categories=", ".join(INTENT_CATEGORIES),
        message=text,
    )

    response = await model_router.generate(
        prompt=prompt,
        complexity_score=2,  # Classification is a simple task
        system="You are a precise intent classifier. Output only valid JSON.",
        max_tokens=200,
        temperature=0.1,
    )

    if response.success:
        try:
            # Try to parse JSON from the response
            json_text = response.text.strip()
            # Handle potential markdown code blocks
            if json_text.startswith("```"):
                json_text = json_text.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(json_text)

            intent = data.get("intent", "GENERAL_CHAT")
            if intent not in INTENT_CATEGORIES:
                intent = "GENERAL_CHAT"

            entities = data.get("entities", {})
            content_length = data.get("content_length", "short")

            # Re-score complexity with extracted info
            complexity = quick_score(text)

            return ParsedIntent(
                intent=intent,
                entities=entities,
                complexity_score=complexity.score,
                recommended_tier=complexity.recommended_tier,
                language=language,
                requires_tools=INTENT_TOOLS.get(intent, []),
                raw_response=response.text,
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse intent JSON: {e}")

    # Fallback: keyword-based classification
    return _keyword_classify(text, language, complexity.score, complexity.recommended_tier)


def _keyword_classify(
    text: str,
    language: str,
    complexity_score: int,
    recommended_tier: int,
) -> ParsedIntent:
    """Simple keyword-based intent classification as fallback."""
    text_lower = text.lower()

    intent = "GENERAL_CHAT"
    entities: dict = {}

    # Code-related
    if any(w in text_lower for w in [
        "write code", "write a function", "write a script", "write a program",
        "create function", "create a function", "create a script",
        "build", "implement", "function to", "python function",
        "javascript function", "class for", "module for",
    ]):
        intent = "WRITE_CODE"
    elif any(w in text_lower for w in ["debug", "fix", "error", "bug"]):
        intent = "DEBUG_CODE"
    elif any(w in text_lower for w in ["explain code", "what does this"]):
        intent = "EXPLAIN_CODE"

    # Search/research
    elif any(w in text_lower for w in ["search", "find", "look up", "google"]):
        intent = "WEB_SEARCH"
    elif any(w in text_lower for w in ["summarize", "summary", "tldr"]):
        intent = "SUMMARIZE"

    # Documents
    elif any(w in text_lower for w in ["docx", "word document"]):
        intent = "CREATE_DOCX"
    elif any(w in text_lower for w in ["xlsx", "spreadsheet", "excel"]):
        intent = "CREATE_XLSX"
    elif any(w in text_lower for w in ["pdf"]):
        intent = "CREATE_PDF"
    elif any(w in text_lower for w in ["pptx", "presentation", "slides"]):
        intent = "CREATE_PPTX"

    # Scheduling
    elif any(w in text_lower for w in ["remind", "reminder", "alarm"]):
        intent = "SET_REMINDER"

    # File operations
    elif any(w in text_lower for w in ["read file", "open file", "show file"]):
        intent = "READ_FILE"
    elif any(w in text_lower for w in ["edit file", "modify file", "change file"]):
        intent = "EDIT_FILE"

    # System
    elif any(w in text_lower for w in ["status", "health", "cost"]):
        intent = "STATUS"
    elif any(w in text_lower for w in ["help", "what can you do"]):
        intent = "HELP"
    elif any(w in text_lower for w in ["remember", "my name is"]):
        intent = "MEMORY_UPDATE"

    # Git
    elif any(w in text_lower for w in ["git", "commit", "push", "pull request"]):
        intent = "GIT_OPERATION"

    return ParsedIntent(
        intent=intent,
        entities=entities,
        complexity_score=complexity_score,
        recommended_tier=recommended_tier,
        language=language,
        requires_tools=INTENT_TOOLS.get(intent, []),
    )
