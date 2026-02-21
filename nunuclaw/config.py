"""Configuration management for NunuClaw.

Loads config from ~/.nunuclaw/config.json, environment variables, or defaults.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_config_dir() -> Path:
    """Return the default NunuClaw config directory."""
    return Path.home() / ".nunuclaw"


@dataclass
class ModelTierConfig:
    """Configuration for a single model tier."""

    provider: str = ""
    model: str = ""
    fallback: str = ""


@dataclass
class ChannelConfig:
    """Configuration for a channel."""

    enabled: bool = False
    token: str = ""
    allow_from: list[str] = field(default_factory=list)
    port: int = 3000


@dataclass
class SecurityConfig:
    """Security and sandbox settings."""

    monthly_cost_limit_usd: float = 30.0
    sandbox_mode: bool = True
    confirm_dangerous_actions: bool = True
    workspace_path: str = ""


@dataclass
class MemoryConfig:
    """Memory / database settings."""

    database: str = ""
    auto_profile: bool = True
    history_limit: int = 1000


@dataclass
class NunuConfig:
    """Root configuration for NunuClaw."""

    # Agent identity
    name: str = "NunuClaw"
    version: str = "0.1.0"
    language: str = "auto"

    # Model tiers
    tier1: ModelTierConfig = field(default_factory=lambda: ModelTierConfig(
        provider="ollama", model="gemma:2b", fallback="groq",
    ))
    tier2: ModelTierConfig = field(default_factory=lambda: ModelTierConfig(
        provider="groq", model="llama-3.1-8b-instant", fallback="anthropic_haiku",
    ))
    tier3: ModelTierConfig = field(default_factory=lambda: ModelTierConfig(
        provider="anthropic", model="claude-sonnet-4-5-20250929", fallback="tier4",
    ))
    tier4: ModelTierConfig = field(default_factory=lambda: ModelTierConfig(
        provider="anthropic", model="claude-opus-4-6", fallback="ask_human",
    ))

    # Channels
    cli: ChannelConfig = field(default_factory=lambda: ChannelConfig(enabled=True))
    telegram: ChannelConfig = field(default_factory=lambda: ChannelConfig(enabled=False))
    whatsapp: ChannelConfig = field(default_factory=lambda: ChannelConfig(enabled=False))
    web: ChannelConfig = field(default_factory=lambda: ChannelConfig(enabled=False, port=3000))

    # Security
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # Memory
    memory: MemoryConfig = field(default_factory=MemoryConfig)

    # Skills
    skills_auto_detect: bool = True
    skills_enabled: list[str] = field(default_factory=lambda: ["developer"])

    # Config directory
    config_dir: Path = field(default_factory=_default_config_dir)

    def __post_init__(self) -> None:
        """Set computed defaults after initialization."""
        if not self.security.workspace_path:
            self.security.workspace_path = str(self.config_dir / "workspace")
        if not self.memory.database:
            self.memory.database = str(self.config_dir / "memory.db")

    @property
    def workspace_path(self) -> Path:
        """Return the resolved workspace path."""
        return Path(self.security.workspace_path)

    @property
    def database_path(self) -> Path:
        """Return the resolved database path."""
        return Path(self.memory.database)

    @property
    def log_dir(self) -> Path:
        """Return the log directory."""
        return self.config_dir / "logs"


def _load_env_overrides(config: NunuConfig) -> None:
    """Override config values from environment variables."""
    if api_key := os.getenv("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = api_key
    if api_key := os.getenv("GROQ_API_KEY"):
        os.environ["GROQ_API_KEY"] = api_key
    if ollama_host := os.getenv("OLLAMA_HOST"):
        os.environ["OLLAMA_HOST"] = ollama_host
    if limit := os.getenv("NUNUCLAW_COST_LIMIT"):
        config.security.monthly_cost_limit_usd = float(limit)


def _dict_to_config(data: dict) -> NunuConfig:
    """Convert a JSON dict to a NunuConfig."""
    config = NunuConfig()

    # Agent identity
    agent = data.get("agent", {})
    config.name = agent.get("name", config.name)
    config.version = agent.get("version", config.version)
    config.language = agent.get("language", config.language)

    # Model tiers
    models = data.get("models", {})
    for tier_name in ("tier1", "tier2", "tier3", "tier4"):
        if tier_data := models.get(tier_name):
            tier = getattr(config, tier_name)
            tier.provider = tier_data.get("provider", tier.provider)
            tier.model = tier_data.get("model", tier.model)
            tier.fallback = tier_data.get("fallback", tier.fallback)

    # Channels
    channels = data.get("channels", {})
    for ch_name in ("cli", "telegram", "whatsapp", "web"):
        if ch_data := channels.get(ch_name):
            ch = getattr(config, ch_name)
            ch.enabled = ch_data.get("enabled", ch.enabled)
            ch.token = ch_data.get("token", ch.token)
            ch.allow_from = ch_data.get("allow_from", ch.allow_from)
            if "port" in ch_data:
                ch.port = ch_data["port"]

    # Security
    if sec := data.get("security"):
        config.security.monthly_cost_limit_usd = sec.get(
            "monthly_cost_limit_usd", config.security.monthly_cost_limit_usd
        )
        config.security.sandbox_mode = sec.get("sandbox_mode", config.security.sandbox_mode)
        config.security.confirm_dangerous_actions = sec.get(
            "confirm_dangerous_actions", config.security.confirm_dangerous_actions
        )
        config.security.workspace_path = sec.get(
            "workspace_path", config.security.workspace_path
        )

    # Memory
    if mem := data.get("memory"):
        config.memory.database = mem.get("database", config.memory.database)
        config.memory.auto_profile = mem.get("auto_profile", config.memory.auto_profile)
        config.memory.history_limit = mem.get("history_limit", config.memory.history_limit)

    # Skills
    if skills := data.get("skills"):
        config.skills_auto_detect = skills.get("auto_detect", config.skills_auto_detect)
        config.skills_enabled = skills.get("enabled", config.skills_enabled)

    return config


def _config_to_dict(config: NunuConfig) -> dict:
    """Convert a NunuConfig to a JSON-serializable dict."""
    return {
        "agent": {
            "name": config.name,
            "version": config.version,
            "language": config.language,
        },
        "models": {
            f"tier{i}": {"provider": t.provider, "model": t.model, "fallback": t.fallback}
            for i, t in enumerate(
                [config.tier1, config.tier2, config.tier3, config.tier4], start=1
            )
        },
        "channels": {
            "cli": {"enabled": config.cli.enabled},
            "telegram": {
                "enabled": config.telegram.enabled,
                "token": config.telegram.token,
                "allow_from": config.telegram.allow_from,
            },
            "whatsapp": {"enabled": config.whatsapp.enabled},
            "web": {"enabled": config.web.enabled, "port": config.web.port},
        },
        "security": {
            "monthly_cost_limit_usd": config.security.monthly_cost_limit_usd,
            "sandbox_mode": config.security.sandbox_mode,
            "confirm_dangerous_actions": config.security.confirm_dangerous_actions,
            "workspace_path": config.security.workspace_path,
        },
        "memory": {
            "database": config.memory.database,
            "auto_profile": config.memory.auto_profile,
            "history_limit": config.memory.history_limit,
        },
        "skills": {
            "auto_detect": config.skills_auto_detect,
            "enabled": config.skills_enabled,
        },
    }


def load_config(config_path: Path | None = None) -> NunuConfig:
    """Load NunuClaw configuration from file, env vars, and defaults.

    Priority: env vars > config file > defaults.
    Creates default config file if it doesn't exist.
    """
    config_dir = _default_config_dir()
    config_file = config_path or (config_dir / "config.json")

    # Load from file if exists
    if config_file.exists():
        with open(config_file) as f:
            data = json.load(f)
        config = _dict_to_config(data)
    else:
        config = NunuConfig()

    config.config_dir = config_dir

    # Apply env overrides
    _load_env_overrides(config)

    # Ensure directories exist
    config.config_dir.mkdir(parents=True, exist_ok=True)
    config.workspace_path.mkdir(parents=True, exist_ok=True)
    config.log_dir.mkdir(parents=True, exist_ok=True)

    # Save default config if it doesn't exist
    if not config_file.exists():
        save_config(config, config_file)

    return config


def save_config(config: NunuConfig, config_path: Path | None = None) -> None:
    """Save configuration to JSON file."""
    config_file = config_path or (config.config_dir / "config.json")
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        json.dump(_config_to_dict(config), f, indent=2)
