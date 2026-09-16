"""Diff Engine for Gemini / Antigravity style precision code editing and visual diffs."""

from __future__ import annotations

import difflib
import os
import sys
from typing import Any, Optional


class DiffColors:
    """Terminal ANSI colors for diff visualization."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BG_RED = "\033[41m\033[37m"
    BG_GREEN = "\033[42m\033[30m"


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def render_diff(
    old_text: str,
    new_text: str,
    filename: str = "file",
    context_lines: int = 3,
    use_color: Optional[bool] = None,
) -> str:
    """Generate a clean, unified diff preview with additions (+), deletions (-), and line context."""
    if use_color is None:
        use_color = _supports_color()

    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=context_lines,
    ))

    if not diff:
        return f"ℹ️ ไม่พบการเปลี่ยนแปลงในไฟล์ {filename}"

    additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

    header = f"📝 [diff_block_start] {filename} (+{additions} / -{deletions})\n"
    if use_color:
        header = f"{DiffColors.BOLD}{DiffColors.CYAN}{header}{DiffColors.RESET}"

    out_lines = [header]

    for line in diff:
        # Strip trailing newline for clean formatting
        clean = line.rstrip("\r\n")
        if line.startswith("+++") or line.startswith("---"):
            if use_color:
                out_lines.append(f"{DiffColors.BOLD}{clean}{DiffColors.RESET}")
            else:
                out_lines.append(clean)
        elif line.startswith("@@"):
            if use_color:
                out_lines.append(f"{DiffColors.CYAN}{clean}{DiffColors.RESET}")
            else:
                out_lines.append(clean)
        elif line.startswith("+"):
            if use_color:
                out_lines.append(f"{DiffColors.GREEN}{clean}{DiffColors.RESET}")
            else:
                out_lines.append(clean)
        elif line.startswith("-"):
            if use_color:
                out_lines.append(f"{DiffColors.RED}{clean}{DiffColors.RESET}")
            else:
                out_lines.append(clean)
        else:
            if use_color:
                out_lines.append(f"{DiffColors.DIM}{clean}{DiffColors.RESET}")
            else:
                out_lines.append(clean)

    footer = "\n[diff_block_end]"
    if use_color:
        footer = f"{DiffColors.BOLD}{DiffColors.CYAN}{footer}{DiffColors.RESET}"
    out_lines.append(footer)

    return "\n".join(out_lines)


def replace_content_chunk(
    original_text: str,
    target_content: str,
    replacement_content: str,
    allow_multiple: bool = False,
) -> tuple[bool, str, str]:
    """
    Surgically replace a block of code inside original_text.
    Returns: (success, updated_text_or_error, diff_summary)
    """
    if not target_content:
        return False, "Error: target_content cannot be empty", ""

    # Normalize line endings for consistent matching
    norm_original = original_text.replace("\r\n", "\n")
    norm_target = target_content.replace("\r\n", "\n")
    norm_replacement = replacement_content.replace("\r\n", "\n")

    count = norm_original.count(norm_target)
    if count == 0:
        # Try stripped match diagnostics
        stripped_target = norm_target.strip()
        if stripped_target and stripped_target in norm_original:
            return (
                False,
                "Error: target_content not found exactly as specified (check indentation and leading/trailing whitespace)",
                "",
            )
        return (
            False,
            "Error: target_content does not match any existing code in the file",
            "",
        )

    if count > 1 and not allow_multiple:
        return (
            False,
            f"Error: target_content found {count} times in the file. Set allow_multiple=True or provide more surrounding context lines.",
            "",
        )

    if allow_multiple:
        updated = norm_original.replace(norm_target, norm_replacement)
    else:
        updated = norm_original.replace(norm_target, norm_replacement, 1)

    diff = render_diff(norm_original, updated, filename="edited_code")
    return True, updated, diff
