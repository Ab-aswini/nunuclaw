"""User profile manager — auto-detect user role from usage patterns."""

from __future__ import annotations

from nunuclaw.memory.store import MemoryStore


class ProfileManager:
    """Manages user profiles and auto-detection of user roles.

    Analyzes usage patterns to infer user role (developer, student,
    shopkeeper, business) without ever asking directly.
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def ensure_profile(self, user_id: str, channel: str) -> dict:
        """Get or create a user profile."""
        profile = await self.store.get_user(user_id)
        if not profile:
            await self.store.upsert_user(
                user_id,
                preferred_channel=channel,
                primary_language="en",
            )
            profile = await self.store.get_user(user_id)
        return profile or {"user_id": user_id}

    async def update_from_message(self, user_id: str, text: str, language: str) -> None:
        """Update profile based on a new message.

        Tracks language usage and will be extended in Phase 2+
        for full role detection from usage patterns.
        """
        await self.store.upsert_user(user_id, primary_language=language)
