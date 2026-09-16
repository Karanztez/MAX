"""
src/core/draft_manager.py — Code Drafts & Staging Manager for MAX.
Allows creating, reviewing, testing, and applying staged code changes
before modifying original workspace files.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from .ide_inspector import IDEInspector, IDEDiagnostic
    from .mcp.diff_engine import render_diff
except (ImportError, ModuleNotFoundError):
    from src.core.ide_inspector import IDEInspector, IDEDiagnostic  # type: ignore[no-redef]
    from src.core.mcp.diff_engine import render_diff  # type: ignore[no-redef]


@dataclass
class CodeDraft:
    """Represents a staged code change draft."""
    draft_id: str
    file_path: str
    original_content: str
    draft_content: str
    diff_preview: str
    status: str = "PENDING"  # PENDING, APPLIED, DISCARDED
    created_at: str = ""
    applied_at: Optional[str] = None
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    has_syntax_error: bool = False
    test_summary: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DraftManager:
    """
    Singleton manager for staged code drafts.
    Integrates with IDEInspector for automated static review of drafts.
    """

    _instance: Optional[DraftManager] = None
    _lock = threading.Lock()

    def __init__(self, workspace_path: Optional[str | Path] = None) -> None:
        self.workspace_path = Path(workspace_path).resolve() if workspace_path else Path.cwd()
        self._drafts: dict[str, CodeDraft] = {}
        self._inspector = IDEInspector(workspace_path=self.workspace_path)
        self._listeners: list[Callable[[CodeDraft, str], None]] = []

    @classmethod
    def get_instance(cls, workspace_path: Optional[str | Path] = None) -> DraftManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(workspace_path=workspace_path)
            return cls._instance

    def add_listener(self, callback: Callable[[CodeDraft, str], None]) -> None:
        """Register a callback for draft events: (draft, event_type: 'created'|'applied'|'discarded')."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[CodeDraft, str], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self, draft: CodeDraft, event_type: str) -> None:
        for cb in list(self._listeners):
            try:
                cb(draft, event_type)
            except Exception:
                pass

    def create_draft(
        self,
        file_path: str | Path,
        draft_content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> CodeDraft:
        """Create a new staged code draft and run IDE diagnostics on it."""
        target = Path(file_path).resolve()
        draft_id = f"draft_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        original_content = ""
        if target.exists() and target.is_file():
            try:
                original_content = target.read_text(encoding="utf-8", errors="replace")
            except Exception:
                original_content = ""

        # Compute diff
        try:
            rel_name = os.path.relpath(str(target), str(self.workspace_path))
        except ValueError:
            rel_name = target.name
        diff_text = render_diff(original_content, draft_content, filename=rel_name, use_color=False)

        # Inspect draft for syntax & linter diagnostics
        review = self._inspector.review_code_draft(target, draft_content)
        diags = review.get("all_draft_diagnostics", [])
        has_syntax_err = not review.get("is_valid", True)

        draft = CodeDraft(
            draft_id=draft_id,
            file_path=str(target),
            original_content=original_content,
            draft_content=draft_content,
            diff_preview=diff_text,
            status="PENDING",
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            diagnostics=diags,
            has_syntax_error=has_syntax_err,
            metadata=metadata or {},
        )

        self._drafts[draft_id] = draft
        self._notify(draft, "created")
        return draft

    def get_draft(self, draft_id: str) -> Optional[CodeDraft]:
        return self._drafts.get(draft_id)

    def list_drafts(self, status: Optional[str] = None) -> list[CodeDraft]:
        if status:
            return [d for d in self._drafts.values() if d.status.upper() == status.upper()]
        return list(self._drafts.values())

    def apply_draft(self, draft_id: str, create_backup: bool = True) -> tuple[bool, str]:
        """Apply a pending draft to the file on disk."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return False, f"Draft '{draft_id}' not found."
        if draft.status == "APPLIED":
            return True, "Draft is already applied."

        target = Path(draft.file_path)
        try:
            # Backup original if requested
            if create_backup and target.exists():
                backup_path = target.with_suffix(target.suffix + ".bak")
                shutil.copy2(target, backup_path)

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(draft.draft_content, encoding="utf-8")

            draft.status = "APPLIED"
            draft.applied_at = time.strftime("%Y-%m-%d %H:%M:%S")
            self._notify(draft, "applied")
            return True, f"นำแบบร่างไปใช้กับไฟล์ '{target.name}' สำเร็จเรียบร้อยแล้ว"
        except Exception as ex:
            return False, f"เกิดข้อผิดพลาดในการเขียนไฟล์: {ex}"

    def discard_draft(self, draft_id: str) -> bool:
        """Discard a staged draft."""
        draft = self._drafts.get(draft_id)
        if not draft:
            return False
        draft.status = "DISCARDED"
        self._notify(draft, "discarded")
        return True

    def clear_finished_drafts(self) -> int:
        """Remove applied or discarded drafts from history."""
        to_del = [k for k, v in self._drafts.items() if v.status in ("APPLIED", "DISCARDED")]
        for k in to_del:
            self._drafts.pop(k, None)
        return len(to_del)
