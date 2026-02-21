"""NunuClaw Sandbox Test - ASCII-safe version for Windows."""

import asyncio
import os
import sys
import tempfile
import shutil

PASS = 0
FAIL = 0

def log_pass(msg):
    global PASS
    PASS += 1
    print(f"  [PASS] {msg}")

def log_fail(msg):
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {msg}")


def test_config():
    print("\n" + "=" * 60)
    print("TEST 1: Config System")
    print("=" * 60)
    from nunuclaw.config import NunuConfig, _config_to_dict, _dict_to_config, _load_env_overrides

    config = NunuConfig()
    print(f"  Name: {config.name} | Version: {config.version}")
    print(f"  Tiers: {config.tier1.provider} > {config.tier2.provider} > {config.tier3.provider} > {config.tier4.provider}")

    if config.name == "NunuClaw" and config.cli.enabled:
        log_pass("Default config creation")
    else:
        log_fail("Default config creation")

    data = _config_to_dict(config)
    restored = _dict_to_config(data)
    if restored.name == config.name and restored.tier1.model == config.tier1.model:
        log_pass("Config serialization roundtrip")
    else:
        log_fail("Config serialization roundtrip")

    os.environ["NUNUCLAW_COST_LIMIT"] = "99"
    _load_env_overrides(config)
    if config.security.monthly_cost_limit_usd == 99.0:
        log_pass("Env var override (NUNUCLAW_COST_LIMIT=99)")
    else:
        log_fail("Env var override")
    del os.environ["NUNUCLAW_COST_LIMIT"]


def test_gateway():
    print("\n" + "=" * 60)
    print("TEST 2: Gateway - UnifiedMessage")
    print("=" * 60)
    from nunuclaw.gateway.message import UnifiedMessage, Media

    msg = UnifiedMessage(user_id="test-user", text="Hello!", channel="cli")
    if msg.text == "Hello!" and not msg.is_empty and not msg.has_media:
        log_pass(f"Basic message (id={msg.id[:8]})")
    else:
        log_fail("Basic message creation")

    empty = UnifiedMessage()
    if empty.is_empty:
        log_pass("Empty message detection")
    else:
        log_fail("Empty message detection")

    media = Media(type="image", path="/tmp/pic.png", mime_type="image/png")
    msg2 = UnifiedMessage(text="Look", media=[media])
    if msg2.has_media and len(msg2.media) == 1:
        log_pass("Media attachment handling")
    else:
        log_fail("Media attachment handling")

    voice = UnifiedMessage(text="transcribed", is_voice=True)
    if voice.is_voice and voice.raw_text == "transcribed":
        log_pass("Voice message + raw_text preservation")
    else:
        log_fail("Voice message handling")


def test_language():
    print("\n" + "=" * 60)
    print("TEST 3: Language Detection")
    print("=" * 60)
    from nunuclaw.understanding.language import detect_language

    # English
    r = detect_language("Hello, how are you?")
    print(f"    English text -> {r.code} ({r.name}, conf={r.confidence:.2f})")
    if r.code == "en": log_pass("English detection")
    else: log_fail(f"English: got {r.code}")

    # Hindi (Devanagari script detection)
    r = detect_language("\u0928\u092e\u0938\u094d\u0924\u0947")  # namaste in Hindi
    print(f"    Hindi text -> {r.code} ({r.name}, conf={r.confidence:.2f})")
    if r.code == "hi": log_pass("Hindi detection")
    else: log_fail(f"Hindi: got {r.code}")

    # Tamil
    r = detect_language("\u0bb5\u0ba3\u0b95\u0bcd\u0b95\u0bae\u0bcd")  # vanakkam
    print(f"    Tamil text -> {r.code} ({r.name}, conf={r.confidence:.2f})")
    if r.code == "ta": log_pass("Tamil detection")
    else: log_fail(f"Tamil: got {r.code}")

    # Telugu
    r = detect_language("\u0c24\u0c46\u0c32\u0c41\u0c17\u0c41")
    print(f"    Telugu text -> {r.code} ({r.name}, conf={r.confidence:.2f})")
    if r.code == "te": log_pass("Telugu detection")
    else: log_fail(f"Telugu: got {r.code}")

    # Bengali
    r = detect_language("\u09ac\u09be\u0982\u09b2\u09be")
    print(f"    Bengali text -> {r.code} ({r.name}, conf={r.confidence:.2f})")
    if r.code == "bn": log_pass("Bengali detection")
    else: log_fail(f"Bengali: got {r.code}")

    # Kannada
    r = detect_language("\u0c95\u0ca8\u0ccd\u0ca8\u0ca1")
    print(f"    Kannada text -> {r.code} ({r.name}, conf={r.confidence:.2f})")
    if r.code == "kn": log_pass("Kannada detection")
    else: log_fail(f"Kannada: got {r.code}")

    # Malayalam
    r = detect_language("\u0d2e\u0d32\u0d2f\u0d3e\u0d33\u0d02")
    print(f"    Malayalam text -> {r.code} ({r.name}, conf={r.confidence:.2f})")
    if r.code == "ml": log_pass("Malayalam detection")
    else: log_fail(f"Malayalam: got {r.code}")

    # Empty fallback
    r = detect_language("")
    if r.code == "en": log_pass("Empty -> English fallback")
    else: log_fail(f"Empty: got {r.code}")


def test_complexity():
    print("\n" + "=" * 60)
    print("TEST 4: Complexity Scoring")
    print("=" * 60)
    from nunuclaw.understanding.complexity import score_complexity, quick_score

    s1 = score_complexity("hello", num_steps_estimate=1)
    print(f"    Simple:   score={s1.score}, tier={s1.recommended_tier}")
    if s1.score <= 3 and s1.recommended_tier == 1:
        log_pass("Simple task -> Tier 1 (Local SLM)")
    else:
        log_fail(f"Simple: score={s1.score}")

    s2 = score_complexity("Build API", requires_code=True, requires_web=True,
                          requires_file=True, num_steps_estimate=5, content_length="long")
    print(f"    Complex:  score={s2.score}, tier={s2.recommended_tier}")
    if s2.score >= 6 and s2.recommended_tier >= 3:
        log_pass("Complex code task -> Tier 3+ (Standard LLM)")
    else:
        log_fail(f"Complex: score={s2.score}")

    s3 = score_complexity("Generate invoice", requires_file=True, accuracy_critical=True)
    print(f"    Critical: score={s3.score}, tier={s3.recommended_tier}")
    if s3.score >= 5:
        log_pass("Accuracy-critical -> higher score")
    else:
        log_fail(f"Critical: score={s3.score}")

    qs1 = quick_score("Search for Python tutorials online")
    qs2 = quick_score("Write a Python function to sort and then save to file")
    qs3 = quick_score("Hi")
    print(f"    Quick: search={qs1.score}, code+file={qs2.score}, chat={qs3.score}")
    if qs2.score > qs3.score:
        log_pass("Quick score: code > chat")
    else:
        log_fail("Quick score ordering wrong")


def test_intent():
    print("\n" + "=" * 60)
    print("TEST 5: Intent Classification (Keyword)")
    print("=" * 60)
    from nunuclaw.understanding.intent import _keyword_classify, INTENT_CATEGORIES

    tests = [
        ("Write code for a REST API", "WRITE_CODE"),
        ("Debug this error in my code", "DEBUG_CODE"),
        ("Search for Python tutorial", "WEB_SEARCH"),
        ("Summarize this article", "SUMMARIZE"),
        ("Create a word document", "CREATE_DOCX"),
        ("Create a PDF invoice", "CREATE_PDF"),
        ("Remind me to call mom", "SET_REMINDER"),
        ("Show status", "STATUS"),
        ("What can you do?", "HELP"),
        ("Remember my name is Aswini", "MEMORY_UPDATE"),
        ("Git commit and push", "GIT_OPERATION"),
        ("Hello there!", "GENERAL_CHAT"),
    ]

    for text, expected in tests:
        result = _keyword_classify(text, "en", 3, 2)
        ok = result.intent == expected
        mark = "[PASS]" if ok else "[FAIL]"
        print(f"    {mark} '{text}' -> {result.intent}")
        if ok: log_pass(f"Intent: {expected}")
        else: log_fail(f"Intent: expected {expected}, got {result.intent}")

    print(f"    Categories: {len(INTENT_CATEGORIES)}")
    if len(INTENT_CATEGORIES) >= 25:
        log_pass(f"Intent catalog ({len(INTENT_CATEGORIES)} categories)")
    else:
        log_fail("Catalog too small")


def test_model_router():
    print("\n" + "=" * 60)
    print("TEST 6: Model Router")
    print("=" * 60)
    from nunuclaw.engine.models.router import score_to_tier, ModelRouter
    from nunuclaw.config import NunuConfig

    mapping = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 3, 8: 3, 9: 4, 10: 4}
    ok = all(score_to_tier(s) == t for s, t in mapping.items())
    if ok:
        log_pass("score_to_tier mapping (10 values)")
    else:
        log_fail("score_to_tier mapping")

    if score_to_tier(0) == 1 and score_to_tier(100) == 4:
        log_pass("Edge clamping (0->1, 100->4)")
    else:
        log_fail("Edge clamping")

    config = NunuConfig()
    router = ModelRouter(config)
    p1 = router.get_provider(1)
    p2 = router.get_provider(2)
    p3 = router.get_provider(3)
    p4 = router.get_provider(4)
    print(f"    T1={p1.provider_name}, T2={p2.provider_name}, T3={p3.provider_name}, T4={p4.provider_name}")
    if p1 and p4:
        log_pass("All 4 providers initialized")
    else:
        log_fail("Provider init")

    if router.total_cost == 0.0:
        log_pass("Cost tracker starts at $0.00")
    else:
        log_fail("Cost tracker")


def test_planner():
    print("\n" + "=" * 60)
    print("TEST 7: Task Planner")
    print("=" * 60)
    from nunuclaw.engine.planner import TaskStep, TaskPlan, _is_math_query

    assert _is_math_query("2 + 2")
    assert _is_math_query("3.14 * 2")
    assert not _is_math_query("Hello world")
    log_pass("Math query detection")

    step = TaskStep(description="Test")
    if step.status == "pending" and step.retry_count == 2:
        log_pass("TaskStep defaults")
    else:
        log_fail("TaskStep defaults")

    plan = TaskPlan(user_id="test", original_message="Hello")
    if plan.status == "planning" and plan.total_cost == 0.0:
        log_pass("TaskPlan creation")
    else:
        log_fail("TaskPlan creation")


def test_verifier():
    print("\n" + "=" * 60)
    print("TEST 8: Step Verifier")
    print("=" * 60)
    from nunuclaw.engine.verifier import verify_step_result

    if verify_step_result("task", "def hello(): return 42").passed:
        log_pass("Valid result passes")
    else:
        log_fail("Valid result rejected")

    if not verify_step_result("task", "").passed:
        log_pass("Empty result fails")
    else:
        log_fail("Empty result passed")

    if not verify_step_result("task", "Error: connection refused").passed:
        log_pass("Error result detected")
    else:
        log_fail("Error result not caught")


def test_calculator():
    print("\n" + "=" * 60)
    print("TEST 9: Calculator Tool")
    print("=" * 60)
    from nunuclaw.tools.calculator import CalculatorTool
    calc = CalculatorTool()

    async def run():
        tests = [
            ("2 + 3", "5"),
            ("7 * 8", "56"),
            ("2 ** 10", "1024"),
            ("(15 + 5) * 3 - 10", "50"),
        ]
        for expr, expected in tests:
            r = await calc.execute("compute", {"expression": expr})
            if r.success and expected in r.data:
                log_pass(f"{r.data}")
            else:
                log_fail(f"compute({expr}): {r.error or r.data}")

        r = await calc.execute("compute", {"expression": "5 / 0"})
        if not r.success:
            log_pass("Division by zero caught")
        else:
            log_fail("Division by zero not caught")

        r = await calc.execute("convert_units", {"value": 5, "from": "km", "to": "miles"})
        if r.success:
            log_pass(f"{r.data}")
        else:
            log_fail("km->miles conversion")

        r = await calc.execute("convert_units", {"value": 100, "from": "c", "to": "f"})
        if r.success and "212" in r.data:
            log_pass(f"{r.data}")
        else:
            log_fail("Temperature conversion")

        r = await calc.execute("convert_units", {"value": 1, "from": "kg", "to": "lbs"})
        if r.success:
            log_pass(f"{r.data}")
        else:
            log_fail("kg->lbs conversion")

    asyncio.run(run())


def test_file_manager():
    print("\n" + "=" * 60)
    print("TEST 10: File Manager (Sandboxed)")
    print("=" * 60)
    from nunuclaw.tools.file_manager import FileManagerTool

    workspace = tempfile.mkdtemp(prefix="nunuclaw_sandbox_")
    fm = FileManagerTool(workspace_path=workspace)
    print(f"    Workspace: {workspace}")

    async def run():
        r = await fm.execute("create_file", {"path": "hello.txt", "content": "Hello NunuClaw!"})
        if r.success: log_pass("Create file: hello.txt")
        else: log_fail(f"Create: {r.error}")

        r = await fm.execute("read_file", {"path": "hello.txt"})
        if r.success and "Hello NunuClaw!" in r.data:
            log_pass(f"Read file: '{r.data}'")
        else:
            log_fail(f"Read: {r.error}")

        r = await fm.execute("create_file", {"path": "src/main.py", "content": "print('hi')"})
        if r.success: log_pass("Nested dir creation: src/main.py")
        else: log_fail(f"Nested dir: {r.error}")

        r = await fm.execute("edit_file", {"path": "hello.txt", "content": "Updated!"})
        r2 = await fm.execute("read_file", {"path": "hello.txt"})
        if r.success and r2.data == "Updated!":
            log_pass("Edit file: content updated")
        else:
            log_fail("Edit file")

        r = await fm.execute("list_files", {"directory": "."})
        if r.success and "hello.txt" in r.data:
            log_pass("List files")
        else:
            log_fail("List files")

        r = await fm.execute("delete_file", {"path": "hello.txt"})
        r2 = await fm.execute("read_file", {"path": "hello.txt"})
        if r.success and not r2.success:
            log_pass("Delete file: confirmed gone")
        else:
            log_fail("Delete file")

        # SECURITY: Sandbox escape attempts
        r = await fm.execute("read_file", {"path": "../../etc/passwd"})
        if not r.success:
            log_pass("SECURITY: Relative path escape BLOCKED")
        else:
            log_fail("SECURITY: Escape not blocked!")

        r = await fm.execute("create_file", {"path": "../../../escape.txt", "content": "bad"})
        if not r.success:
            log_pass("SECURITY: Write escape BLOCKED")
        else:
            log_fail("SECURITY: Write escape not blocked!")

    asyncio.run(run())
    shutil.rmtree(workspace, ignore_errors=True)


def test_scheduler():
    print("\n" + "=" * 60)
    print("TEST 11: Scheduler Tool")
    print("=" * 60)
    from nunuclaw.tools.scheduler import SchedulerTool
    scheduler = SchedulerTool()

    async def run():
        r = await scheduler.execute("list_scheduled", {})
        if r.success and "No active" in r.data:
            log_pass("Empty reminders list")
        else:
            log_fail("Empty list")

        r = await scheduler.execute("set_reminder", {"message": "Buy milk", "time": "5pm"})
        if r.success and "Buy milk" in r.data:
            log_pass("Set reminder: Buy milk")
        else:
            log_fail("Set reminder")

        r = await scheduler.execute("set_reminder", {"message": "Call Mom", "time": "8pm"})
        if r.success:
            log_pass("Set reminder: Call Mom")
        else:
            log_fail("Set reminder 2")

        r = await scheduler.execute("list_scheduled", {})
        if "Buy milk" in r.data and "Call Mom" in r.data:
            log_pass("List shows both reminders")
        else:
            log_fail("List reminders")

    asyncio.run(run())


def test_registry():
    print("\n" + "=" * 60)
    print("TEST 12: Tool Registry")
    print("=" * 60)
    from nunuclaw.tools.registry import ToolRegistry

    registry = ToolRegistry()
    registry.register_defaults(workspace_path=tempfile.mkdtemp())
    tools = registry.list_tools()
    print(f"    Tools: {tools}")

    if "calculator" in tools and "file_manager" in tools and "web_search" in tools:
        log_pass(f"Default tools ({len(tools)} registered)")
    else:
        log_fail("Missing tools")

    for n, d in registry.list_tools_with_descriptions().items():
        print(f"      {n}: {d}")
    log_pass("Tool descriptions available")


def test_memory():
    print("\n" + "=" * 60)
    print("TEST 13: Memory Store (SQLite)")
    print("=" * 60)
    from nunuclaw.memory.store import MemoryStore

    db_path = os.path.join(tempfile.mkdtemp(), "test.db")

    async def run():
        store = MemoryStore(db_path)
        await store.connect()
        log_pass(f"DB connected: {os.path.basename(db_path)}")

        await store.upsert_user("u1", name="Aswini", detected_role="developer")
        p = await store.get_user("u1")
        if p and p["name"] == "Aswini":
            log_pass(f"User profile: {p['name']}")
        else:
            log_fail("User profile")

        await store.upsert_user("u1", primary_language="en")
        p = await store.get_user("u1")
        if p["primary_language"] == "en":
            log_pass("Profile update")
        else:
            log_fail("Profile update")

        await store.save_task("t1", "u1", "Write code", "WRITE_CODE", "completed", cost=0.002)
        await store.save_task("t2", "u1", "Search", "WEB_SEARCH", "completed", cost=0.001)
        tasks = await store.get_recent_tasks("u1")
        if len(tasks) == 2:
            log_pass(f"Task history: {len(tasks)} tasks")
        else:
            log_fail("Task history")

        await store.add_conversation("u1", "user", "Hello!", "cli")
        await store.add_conversation("u1", "assistant", "Hi!", "cli")
        hist = await store.get_conversation_history("u1")
        if len(hist) == 2:
            log_pass(f"Conversation: {len(hist)} turns")
        else:
            log_fail("Conversation history")

        await store.remember("u1", "name", "Aswini", "personal")
        await store.remember("u1", "pref", "dark mode", "preference")
        mems = await store.recall("u1")
        if len(mems) >= 2:
            log_pass(f"Memory: {len(mems)} facts stored")
        else:
            log_fail("Memory store")

        mems = await store.recall("u1", "name")
        if len(mems) >= 1 and mems[0]["value"] == "Aswini":
            log_pass(f"Memory recall: found '{mems[0]['value']}'")
        else:
            log_fail("Memory recall")

        await store.close()
        log_pass("DB closed cleanly")

    asyncio.run(run())
    os.unlink(db_path)


def test_delivery():
    print("\n" + "=" * 60)
    print("TEST 14: Delivery Formatter")
    print("=" * 60)
    from nunuclaw.delivery.formatter import format_for_channel

    if format_for_channel("Hello", "cli") == "Hello":
        log_pass("CLI plain format")
    else:
        log_fail("CLI plain")

    r = format_for_channel("Hello", "cli", cost=0.05)
    if "$0.05" in r:
        log_pass("CLI with cost footer")
    else:
        log_fail("CLI cost")

    if format_for_channel("", "cli") == "No response generated.":
        log_pass("Empty response handling")
    else:
        log_fail("Empty response")


def test_pipeline():
    print("\n" + "=" * 60)
    print("TEST 15: Full Pipeline Simulation")
    print("=" * 60)
    from nunuclaw.gateway.message import UnifiedMessage
    from nunuclaw.understanding.language import detect_language
    from nunuclaw.understanding.complexity import quick_score
    from nunuclaw.understanding.intent import _keyword_classify
    from nunuclaw.engine.planner import TaskStep, TaskPlan
    from nunuclaw.delivery.formatter import format_for_channel

    msg = UnifiedMessage(user_id="sandbox:test", text="Write a Python function to sort a list", channel="cli")

    lang = detect_language(msg.text)
    print(f"    1. Language: {lang.code}")

    complexity = quick_score(msg.text)
    print(f"    2. Complexity: {complexity.score}/10 -> Tier {complexity.recommended_tier}")

    intent = _keyword_classify(msg.text, lang.code, complexity.score, complexity.recommended_tier)
    print(f"    3. Intent: {intent.intent}")
    print(f"    4. Tools: {intent.requires_tools}")

    plan = TaskPlan(user_id=msg.user_id, original_message=msg.text, intent=intent.intent,
                   steps=[TaskStep(description="Write sort function", tool="code_tools",
                                  model_tier=complexity.recommended_tier)], status="ready")
    print(f"    5. Plan: {len(plan.steps)} steps")

    formatted = format_for_channel("def sort_list(lst): return sorted(lst)", "cli", cost=0.001)
    print(f"    6. Output: {formatted[:50]}")

    if lang.code == "en" and intent.intent == "WRITE_CODE" and plan.status == "ready":
        log_pass("Full pipeline: Gateway -> Understanding -> Plan -> Delivery")
    else:
        log_fail("Pipeline simulation")


# ================================
#  RUN ALL
# ================================
if __name__ == "__main__":
    print("\nNunuClaw Sandbox Testing")
    print("-" * 60)

    test_config()
    test_gateway()
    test_language()
    test_complexity()
    test_intent()
    test_model_router()
    test_planner()
    test_verifier()
    test_calculator()
    test_file_manager()
    test_scheduler()
    test_registry()
    test_memory()
    test_delivery()
    test_pipeline()

    print("\n" + "-" * 60)
    total = PASS + FAIL
    print(f"SANDBOX RESULTS: {PASS}/{total} passed, {FAIL} failed")
    print("-" * 60)

    if FAIL == 0:
        print("ALL SANDBOX TESTS PASSED!")
    else:
        print(f"WARNING: {FAIL} test(s) failed")
        sys.exit(1)
