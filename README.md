<p align="center">
  <h1 align="center">🦀 NunuClaw</h1>
  <p align="center"><strong>Universal, lightweight, autonomous AI assistant</strong></p>
  <p align="center">SLM → LLM cost-intelligent routing · Multilingual · Offline-capable</p>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#features">Features</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#roadmap">Roadmap</a> •
  <a href="LICENSE">License</a>
</p>

---

## What is NunuClaw?

NunuClaw is an **autonomous AI assistant** designed to run on any device and serve diverse users — developers, students, shopkeepers, and professionals — through any channel (CLI, Telegram, WhatsApp, Voice, Web).

**Core Innovation:** SLM → LLM cost-intelligent routing — every task starts on the cheapest capable model and escalates only when needed.

```
User Message → Language Detection → Intent + Complexity → Cheapest Model → Execute → Deliver
                                         ↓
                            Score 1-3 → Local SLM (free)
                            Score 4-5 → Groq API (cheap)
                            Score 6-8 → Claude Sonnet (moderate)
                            Score 9-10 → Claude Opus (premium)
```

## Quick Start

```bash
# Clone
git clone https://github.com/Ab-aswini/nunuclaw.git
cd nunuclaw

# Install
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -e .

# Configure (set at least one API key)
set GROQ_API_KEY=your_key       # Free tier at console.groq.com
# or
set ANTHROPIC_API_KEY=your_key

# Run
nunuclaw setup                  # Check configuration
nunuclaw start                  # Interactive REPL
nunuclaw chat "Hello NunuClaw"  # One-shot message
nunuclaw status                 # System health
```

## Architecture

NunuClaw follows a **5-layer architecture**:

```
┌─────────────────────────────────────────────────┐
│  Layer 1: GATEWAY                               │
│  CLI · Telegram · WhatsApp · Web · Voice        │
│  → Normalizes all input to UnifiedMessage       │
├─────────────────────────────────────────────────┤
│  Layer 2: UNDERSTANDING ENGINE                  │
│  Language Detection (8 Indian languages)        │
│  Intent Classification (30+ categories)         │
│  Complexity Scoring (1-10)                      │
├─────────────────────────────────────────────────┤
│  Layer 3: TASK ENGINE                           │
│  Task Planner → Step Executor → Verifier        │
│  Model Router: SLM → LLM escalation            │
│  Providers: Ollama · Groq · Anthropic           │
├─────────────────────────────────────────────────┤
│  Layer 4: MEMORY & LEARNING                     │
│  SQLite: profiles, tasks, conversations         │
│  Auto user-role detection                       │
│  Persistent facts & preferences                 │
├─────────────────────────────────────────────────┤
│  Layer 5: DELIVERY                              │
│  Channel-specific formatting                    │
│  Cost tracking & display                        │
│  TTS (Phase 2+)                                 │
└─────────────────────────────────────────────────┘
```

## Features

### Phase 1 (Current) ✅

| Feature | Description |
|---------|-------------|
| **CLI Channel** | Rich terminal with panels, markdown, colors |
| **3 AI Providers** | Ollama (local), Groq (cloud), Anthropic (Claude) |
| **SLM→LLM Router** | Cost-intelligent model selection with auto-escalation |
| **30+ Intents** | Code, search, documents, scheduling, files, git, chat |
| **8 Languages** | Hindi, Tamil, Telugu, Bengali, Kannada, Malayalam, Gujarati, Odia |
| **5 Tools** | File manager, calculator, web search, scheduler, code tools |
| **SQLite Memory** | User profiles, task history, conversations, persistent facts |
| **Sandbox Security** | File operations restricted to workspace directory |
| **Cost Tracking** | Per-request cost display, monthly limits |

### Core Tools

| Tool | Capabilities |
|------|-------------|
| `file_manager` | Create, read, edit, delete, list (sandboxed) |
| `calculator` | Math expressions, unit conversions (length, weight, temp) |
| `web_search` | DuckDuckGo search, page fetching |
| `scheduler` | Set reminders, list, cancel |
| `code_tools` | Write, debug, explain code via LLM |

## Configuration

NunuClaw auto-creates config at `~/.nunuclaw/config.json` on first run:

```json
{
  "models": {
    "tier1": { "provider": "ollama", "model": "gemma:2b" },
    "tier2": { "provider": "groq", "model": "llama-3.1-8b-instant" },
    "tier3": { "provider": "anthropic", "model": "claude-sonnet-4-5-20250929" },
    "tier4": { "provider": "anthropic", "model": "claude-opus-4-6" }
  },
  "security": {
    "monthly_cost_limit_usd": 30.0,
    "sandbox_mode": true
  }
}
```

**Environment Variables:**
| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | One of these | Free at [console.groq.com](https://console.groq.com) |
| `ANTHROPIC_API_KEY` | required | From [console.anthropic.com](https://console.anthropic.com) |
| `OLLAMA_HOST` | Optional | Default: `http://localhost:11434` |
| `NUNUCLAW_COST_LIMIT` | Optional | Override monthly cost limit |

## Project Structure

```
nunuclaw/
├── config.py              # Config system (JSON + env vars)
├── main.py                # CLI entry point + NunuClawAgent
├── gateway/
│   ├── message.py         # UnifiedMessage schema
│   ├── router.py          # Channel router
│   └── channels/
│       ├── base.py        # BaseChannel ABC
│       └── cli.py         # Rich-based CLI
├── understanding/
│   ├── language.py        # Unicode script detection
│   ├── intent.py          # SLM + keyword classification
│   └── complexity.py      # 1-10 scoring algorithm
├── engine/
│   ├── planner.py         # LLM-powered task decomposition
│   ├── executor.py        # Step execution + escalation
│   ├── verifier.py        # Result verification
│   └── models/
│       ├── base.py        # Provider interface
│       ├── ollama.py      # Local SLM
│       ├── groq.py        # Groq cloud
│       ├── anthropic.py   # Claude (Haiku/Sonnet/Opus)
│       └── router.py      # Tier-based model router
├── tools/
│   ├── base.py            # BaseTool + ToolResult
│   ├── registry.py        # Tool discovery
│   ├── file_manager.py    # Sandboxed file ops
│   ├── calculator.py      # Math + units
│   ├── web_search.py      # DuckDuckGo search
│   └── scheduler.py       # Reminders
├── memory/
│   ├── store.py           # SQLite (5 tables)
│   ├── profile.py         # Auto role detection
│   └── history.py         # Task history
└── delivery/
    ├── formatter.py       # Channel formatting
    └── tts.py             # TTS stub
```

## Testing

```bash
# Unit tests (47 tests)
pip install -e ".[dev]"
pytest tests/test_core.py -v

# Sandbox integration tests (76 tests)
python tests/sandbox_test.py
```

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 1** | Foundation — CLI, core engine, 5 tools | ✅ Complete |
| **Phase 2** | Channels — Telegram, WhatsApp, Voice I/O | 🔮 Planned |
| **Phase 3** | Intelligence — Skill packs, learning, context | 🔮 Planned |
| **Phase 4** | Scale — Multi-user, cloud sync, marketplace | 🔮 Planned |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/Ab-aswini">Ab-aswini</a>
</p>
