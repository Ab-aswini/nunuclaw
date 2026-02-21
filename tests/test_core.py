"""Tests for NunuClaw core components."""

from __future__ import annotations

import asyncio
import pytest

from nunuclaw.config import load_config, NunuConfig, _dict_to_config, _config_to_dict
from nunuclaw.gateway.message import UnifiedMessage, Media
from nunuclaw.understanding.language import detect_language
from nunuclaw.understanding.complexity import score_complexity, quick_score
from nunuclaw.understanding.intent import _keyword_classify
from nunuclaw.engine.planner import TaskStep, TaskPlan, _is_math_query
from nunuclaw.engine.verifier import verify_step_result
from nunuclaw.engine.models.base import ModelResponse
from nunuclaw.engine.models.router import score_to_tier
from nunuclaw.tools.base import ToolResult
from nunuclaw.tools.calculator import CalculatorTool
from nunuclaw.tools.file_manager import FileManagerTool
from nunuclaw.tools.scheduler import SchedulerTool
from nunuclaw.tools.registry import ToolRegistry
from nunuclaw.delivery.formatter import format_for_channel


# ─── Config Tests ────────────────────────────────────────────────

class TestConfig:
    def test_default_config(self):
        config = NunuConfig()
        assert config.name == "NunuClaw"
        assert config.version == "0.1.0"
        assert config.cli.enabled is True
        assert config.telegram.enabled is False

    def test_tier_defaults(self):
        config = NunuConfig()
        assert config.tier1.provider == "ollama"
        assert config.tier2.provider == "groq"
        assert config.tier3.provider == "anthropic"

    def test_config_roundtrip(self):
        config = NunuConfig()
        data = _config_to_dict(config)
        restored = _dict_to_config(data)
        assert restored.name == config.name
        assert restored.tier1.model == config.tier1.model


# ─── Gateway Tests ───────────────────────────────────────────────

class TestUnifiedMessage:
    def test_create_message(self):
        msg = UnifiedMessage(user_id="test", text="Hello", channel="cli")
        assert msg.user_id == "test"
        assert msg.text == "Hello"
        assert msg.raw_text == "Hello"
        assert not msg.is_empty
        assert not msg.has_media

    def test_empty_message(self):
        msg = UnifiedMessage()
        assert msg.is_empty

    def test_media_message(self):
        media = Media(type="image", path="/tmp/test.png", mime_type="image/png")
        msg = UnifiedMessage(text="Look", media=[media])
        assert msg.has_media


# ─── Language Detection Tests ────────────────────────────────────

class TestLanguageDetection:
    def test_english(self):
        result = detect_language("Hello, how are you?")
        assert result.code == "en"
        assert result.confidence > 0.5

    def test_hindi(self):
        result = detect_language("नमस्ते, आप कैसे हैं?")
        assert result.code == "hi"
        assert result.confidence > 0.5

    def test_tamil(self):
        result = detect_language("வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?")
        assert result.code == "ta"

    def test_empty(self):
        result = detect_language("")
        assert result.code == "en"  # Default

    def test_mixed_hinglish(self):
        result = detect_language("Mera assignment complete करो photosynthesis पर")
        assert result.is_mixed or result.code == "hi"


# ─── Complexity Scoring Tests ────────────────────────────────────

class TestComplexity:
    def test_simple_task(self):
        result = score_complexity("hello", num_steps_estimate=1)
        assert result.score <= 3
        assert result.recommended_tier == 1

    def test_complex_code_task(self):
        result = score_complexity(
            "Create a FastAPI endpoint",
            requires_code=True,
            requires_file=True,
            requires_web=True,
            num_steps_estimate=5,
        )
        assert result.score >= 6
        assert result.recommended_tier >= 3

    def test_quick_score_simple(self):
        result = quick_score("What time is it?")
        assert result.score <= 4

    def test_quick_score_code(self):
        result = quick_score("Write a Python function to sort a list")
        assert result.score >= 3

    def test_quick_score_search(self):
        result = quick_score("Search for Claude API pricing")
        assert result.score >= 2


# ─── Intent Classification Tests ────────────────────────────────

class TestIntentClassification:
    def test_code_intent(self):
        result = _keyword_classify("Write code for a REST API", "en", 5, 3)
        assert result.intent == "WRITE_CODE"

    def test_debug_intent(self):
        result = _keyword_classify("Debug this error in my function", "en", 5, 3)
        assert result.intent == "DEBUG_CODE"

    def test_search_intent(self):
        result = _keyword_classify("Search for Python tutorials", "en", 3, 2)
        assert result.intent == "WEB_SEARCH"

    def test_help_intent(self):
        result = _keyword_classify("What can you do?", "en", 1, 1)
        assert result.intent == "HELP"

    def test_reminder_intent(self):
        result = _keyword_classify("Remind me to buy milk", "en", 2, 1)
        assert result.intent == "SET_REMINDER"

    def test_general_chat(self):
        result = _keyword_classify("Hello there!", "en", 1, 1)
        assert result.intent == "GENERAL_CHAT"


# ─── Model Router Tests ─────────────────────────────────────────

class TestModelRouter:
    def test_score_to_tier(self):
        assert score_to_tier(1) == 1
        assert score_to_tier(3) == 1
        assert score_to_tier(4) == 2
        assert score_to_tier(5) == 2
        assert score_to_tier(6) == 3
        assert score_to_tier(8) == 3
        assert score_to_tier(9) == 4
        assert score_to_tier(10) == 4

    def test_score_clamping(self):
        assert score_to_tier(0) == 1
        assert score_to_tier(15) == 4


# ─── Task Planning Tests ────────────────────────────────────────

class TestTaskPlanning:
    def test_math_query_detection(self):
        assert _is_math_query("2 + 2")
        assert _is_math_query("3.14 * 2")
        assert not _is_math_query("Hello world")
        assert not _is_math_query("What is 2+2?")

    def test_task_step_defaults(self):
        step = TaskStep(description="Test step")
        assert step.status == "pending"
        assert step.retry_count == 2
        assert step.on_failure == "escalate"


# ─── Verifier Tests ──────────────────────────────────────────────

class TestVerifier:
    def test_valid_result(self):
        result = verify_step_result("Write code", "def hello(): pass")
        assert result.passed

    def test_empty_result(self):
        result = verify_step_result("Write code", "")
        assert not result.passed

    def test_error_result(self):
        result = verify_step_result("Write code", "Error: something failed")
        assert not result.passed


# ─── Calculator Tool Tests ───────────────────────────────────────

class TestCalculatorTool:
    @pytest.fixture
    def calc(self):
        return CalculatorTool()

    @pytest.mark.asyncio
    async def test_addition(self, calc):
        result = await calc.execute("compute", {"expression": "2 + 3"})
        assert result.success
        assert "5" in result.data

    @pytest.mark.asyncio
    async def test_multiplication(self, calc):
        result = await calc.execute("compute", {"expression": "7 * 8"})
        assert result.success
        assert "56" in result.data

    @pytest.mark.asyncio
    async def test_division(self, calc):
        result = await calc.execute("compute", {"expression": "10 / 3"})
        assert result.success

    @pytest.mark.asyncio
    async def test_division_by_zero(self, calc):
        result = await calc.execute("compute", {"expression": "5 / 0"})
        assert not result.success

    @pytest.mark.asyncio
    async def test_unit_conversion(self, calc):
        result = await calc.execute("convert_units", {
            "value": 5, "from": "km", "to": "miles"
        })
        assert result.success
        assert "3.1" in result.data

    @pytest.mark.asyncio
    async def test_temperature_conversion(self, calc):
        result = await calc.execute("convert_units", {
            "value": 100, "from": "c", "to": "f"
        })
        assert result.success
        assert "212" in result.data


# ─── File Manager Tool Tests ────────────────────────────────────

class TestFileManagerTool:
    @pytest.fixture
    def fm(self, tmp_path):
        return FileManagerTool(workspace_path=str(tmp_path))

    @pytest.mark.asyncio
    async def test_create_and_read(self, fm):
        await fm.execute("create_file", {"path": "test.txt", "content": "Hello NunuClaw"})
        result = await fm.execute("read_file", {"path": "test.txt"})
        assert result.success
        assert "Hello NunuClaw" in result.data

    @pytest.mark.asyncio
    async def test_list_files(self, fm):
        await fm.execute("create_file", {"path": "a.txt", "content": "A"})
        await fm.execute("create_file", {"path": "b.txt", "content": "B"})
        result = await fm.execute("list_files", {"directory": "."})
        assert result.success
        assert "a.txt" in result.data
        assert "b.txt" in result.data

    @pytest.mark.asyncio
    async def test_delete_file(self, fm):
        await fm.execute("create_file", {"path": "delete_me.txt", "content": "bye"})
        result = await fm.execute("delete_file", {"path": "delete_me.txt"})
        assert result.success
        result = await fm.execute("read_file", {"path": "delete_me.txt"})
        assert not result.success

    @pytest.mark.asyncio
    async def test_sandbox_escape(self, fm):
        result = await fm.execute("read_file", {"path": "../../etc/passwd"})
        assert not result.success


# ─── Scheduler Tool Tests ───────────────────────────────────────

class TestSchedulerTool:
    @pytest.fixture
    def scheduler(self):
        return SchedulerTool()

    @pytest.mark.asyncio
    async def test_set_reminder(self, scheduler):
        result = await scheduler.execute("set_reminder", {
            "message": "Buy milk", "time": "5pm"
        })
        assert result.success
        assert "Buy milk" in result.data

    @pytest.mark.asyncio
    async def test_list_empty(self, scheduler):
        result = await scheduler.execute("list_scheduled", {})
        assert result.success
        assert "No active" in result.data


# ─── Delivery Tests ──────────────────────────────────────────────

class TestDelivery:
    def test_format_cli(self):
        result = format_for_channel("Hello", "cli")
        assert result == "Hello"

    def test_format_with_cost(self):
        result = format_for_channel("Hello", "cli", cost=0.05)
        assert "0.05" in result

    def test_format_empty(self):
        result = format_for_channel("", "cli")
        assert result == "No response generated."


# ─── Tool Registry Tests ────────────────────────────────────────

class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        calc = CalculatorTool()
        registry.register(calc)
        assert registry.get_tool("calculator") is calc

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        assert "calculator" in registry.list_tools()

    def test_missing_tool(self):
        registry = ToolRegistry()
        assert registry.get_tool("nonexistent") is None
