"""UnifiedMessage schema — the canonical message format for all channels.

Every channel normalizes its input into a UnifiedMessage before processing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Media:
    """An attached media file (image, voice note, document, etc.)."""

    type: str          # "image", "audio", "document", "video"
    path: str          # Local file path or URL
    mime_type: str     # e.g., "image/png", "audio/ogg"
    filename: str = ""
    size_bytes: int = 0


@dataclass
class UnifiedMessage:
    """The canonical message format that all channels normalize to.

    This is the single data structure that flows through the entire pipeline.
    Every channel converts its native format into this before processing.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    text: str = ""
    language: str = "auto"                          # Detected language code
    channel: str = "cli"                            # Source channel name
    media: list[Media] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reply_to: str | None = None                     # ID of message being replied to
    metadata: dict = field(default_factory=dict)     # Channel-specific extras
    is_voice: bool = False                          # Was originally a voice message
    raw_text: str = ""                              # Original text before processing

    def __post_init__(self) -> None:
        """Preserve raw text if not explicitly set."""
        if not self.raw_text:
            self.raw_text = self.text

    @property
    def has_media(self) -> bool:
        """Check if the message has any media attachments."""
        return len(self.media) > 0

    @property
    def is_empty(self) -> bool:
        """Check if the message has no content at all."""
        return not self.text and not self.media
