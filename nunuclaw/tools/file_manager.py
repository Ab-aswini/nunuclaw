"""File manager tool — create, read, edit, delete, list files.

All operations are sandboxed to the workspace directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from nunuclaw.tools.base import BaseTool, ToolResult


class FileManagerTool(BaseTool):
    """Manage files within the sandboxed workspace."""

    def __init__(self, workspace_path: str = "") -> None:
        self._workspace = Path(workspace_path) if workspace_path else Path.cwd()

    @property
    def name(self) -> str:
        return "file_manager"

    @property
    def description(self) -> str:
        return "Create, read, edit, delete, and list files in the workspace."

    @property
    def actions(self) -> list[str]:
        return ["create_file", "read_file", "edit_file", "delete_file", "list_files"]

    def _safe_path(self, path: str) -> Path | None:
        """Resolve and validate a path is within the workspace."""
        try:
            resolved = (self._workspace / path).resolve()
            if str(resolved).startswith(str(self._workspace.resolve())):
                return resolved
        except Exception:
            pass
        return None

    async def execute(self, action: str, params: dict) -> ToolResult:
        """Execute a file operation."""
        actions_map = {
            "create_file": self._create_file,
            "read_file": self._read_file,
            "edit_file": self._edit_file,
            "delete_file": self._delete_file,
            "list_files": self._list_files,
        }

        handler = actions_map.get(action)
        if not handler:
            return ToolResult(success=False, error=f"Unknown action: {action}")

        try:
            return await handler(params)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _create_file(self, params: dict) -> ToolResult:
        """Create a new file with content."""
        path = params.get("path", "")
        content = params.get("content", "")

        if not path:
            return ToolResult(success=False, error="Missing 'path' parameter")

        safe = self._safe_path(path)
        if not safe:
            return ToolResult(success=False, error=f"Path '{path}' is outside workspace")

        safe.parent.mkdir(parents=True, exist_ok=True)
        safe.write_text(content, encoding="utf-8")

        return ToolResult(
            success=True,
            data=f"Created file: {path}",
            files=[str(safe)],
        )

    async def _read_file(self, params: dict) -> ToolResult:
        """Read file contents."""
        path = params.get("path", "")

        if not path:
            return ToolResult(success=False, error="Missing 'path' parameter")

        safe = self._safe_path(path)
        if not safe:
            return ToolResult(success=False, error=f"Path '{path}' is outside workspace")

        if not safe.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        content = safe.read_text(encoding="utf-8")
        return ToolResult(success=True, data=content)

    async def _edit_file(self, params: dict) -> ToolResult:
        """Edit an existing file."""
        path = params.get("path", "")
        content = params.get("content", "")

        if not path:
            return ToolResult(success=False, error="Missing 'path' parameter")

        safe = self._safe_path(path)
        if not safe:
            return ToolResult(success=False, error=f"Path '{path}' is outside workspace")

        safe.write_text(content, encoding="utf-8")
        return ToolResult(
            success=True,
            data=f"Updated file: {path}",
            files=[str(safe)],
        )

    async def _delete_file(self, params: dict) -> ToolResult:
        """Delete a file."""
        path = params.get("path", "")

        if not path:
            return ToolResult(success=False, error="Missing 'path' parameter")

        safe = self._safe_path(path)
        if not safe:
            return ToolResult(success=False, error=f"Path '{path}' is outside workspace")

        if not safe.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        safe.unlink()
        return ToolResult(success=True, data=f"Deleted: {path}")

    async def _list_files(self, params: dict) -> ToolResult:
        """List files in a directory."""
        directory = params.get("directory", ".")

        safe = self._safe_path(directory)
        if not safe:
            return ToolResult(success=False, error=f"Path '{directory}' is outside workspace")

        if not safe.exists():
            return ToolResult(success=False, error=f"Directory not found: {directory}")

        files = []
        for item in sorted(safe.iterdir()):
            prefix = "📁" if item.is_dir() else "📄"
            size = f" ({item.stat().st_size}B)" if item.is_file() else ""
            files.append(f"{prefix} {item.name}{size}")

        return ToolResult(success=True, data="\n".join(files) if files else "(empty)")
