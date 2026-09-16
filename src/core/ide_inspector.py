"""
src/core/ide_inspector.py — IDE Debug & Diagnostics Inspector for MAX.
Provides syntax validation, static analysis, linter checks (Flake8/Ruff/Pyrefly/compiler),
and structured diagnostic reporting for files and workspace projects.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class IDEDiagnostic:
    """Represents a single IDE diagnostic or debug issue."""
    file_path: str
    line: int
    col: int
    severity: str  # "error", "warning", "info"
    code: str      # e.g., "syntax-error", "F401", "E501", "missing-import"
    message: str
    source: str    # "SyntaxCheck", "AST", "Compiler", "Pyrefly", "Flake8", "Ruff"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_line(self) -> str:
        icon = "🔴" if self.severity.lower() == "error" else ("🟡" if self.severity.lower() == "warning" else "🔵")
        rel_path = self.file_path
        try:
            rel_path = os.path.relpath(self.file_path)
        except ValueError:
            pass
        return f"{icon} [{self.source}] {rel_path}:{self.line}:{self.col} [{self.code}] {self.message}"


class IDEInspector:
    """
    Inspector that scans files or entire project workspaces for syntax errors,
    compiler diagnostics, and linter warnings.
    """

    def __init__(self, workspace_path: Optional[str | Path] = None) -> None:
        self.workspace_path = Path(workspace_path).resolve() if workspace_path else Path.cwd()

    def inspect_file(
        self,
        file_path: str | Path,
        content: Optional[str] = None,
    ) -> list[IDEDiagnostic]:
        """
        Inspect a specific file for syntax and static analysis errors.
        If content is provided, inspects that in-memory content instead of reading from disk.
        """
        target = Path(file_path).resolve()
        diagnostics: list[IDEDiagnostic] = []

        if content is None:
            if not target.exists():
                return [
                    IDEDiagnostic(
                        file_path=str(target),
                        line=1,
                        col=1,
                        severity="error",
                        code="file-not-found",
                        message=f"File does not exist: {target}",
                        source="IDEInspector",
                    )
                ]
            try:
                content = target.read_text(encoding="utf-8", errors="replace")
            except Exception as ex:
                return [
                    IDEDiagnostic(
                        file_path=str(target),
                        line=1,
                        col=1,
                        severity="error",
                        code="read-error",
                        message=f"Cannot read file: {ex}",
                        source="IDEInspector",
                    )
                ]

        # 1. Python Syntax & AST Check
        if target.suffix.lower() == ".py":
            diagnostics.extend(self._check_python_syntax(str(target), content))

        # 2. External Linter check (Flake8 / Ruff) if available on system
        if target.suffix.lower() == ".py" and target.exists() and content == target.read_text(encoding="utf-8", errors="replace"):
            linter_diags = self._run_external_linter(str(target))
            diagnostics.extend(linter_diags)

        return diagnostics

    def _check_python_syntax(self, file_path: str, code: str) -> list[IDEDiagnostic]:
        """Check Python syntax using AST parsing and built-in compile()."""
        diagnostics: list[IDEDiagnostic] = []
        try:
            ast.parse(code, filename=file_path)
            compile(code, file_path, "exec")
        except SyntaxError as ex:
            diagnostics.append(
                IDEDiagnostic(
                    file_path=file_path,
                    line=ex.lineno or 1,
                    col=ex.offset or 1,
                    severity="error",
                    code="syntax-error",
                    message=str(ex.msg or ex),
                    source="SyntaxCheck",
                )
            )
        except Exception as ex:
            diagnostics.append(
                IDEDiagnostic(
                    file_path=file_path,
                    line=1,
                    col=1,
                    severity="error",
                    code="compile-error",
                    message=str(ex),
                    source="Compiler",
                )
            )
        return diagnostics

    def _run_external_linter(self, file_path: str) -> list[IDEDiagnostic]:
        """Run available system linter (ruff or flake8) on a file."""
        diagnostics: list[IDEDiagnostic] = []
        # Try ruff first (fastest)
        ruff_cmd = [sys.executable, "-m", "ruff", "check", "--output-format=text", file_path]
        try:
            res = subprocess.run(ruff_cmd, capture_output=True, text=True, timeout=5)
            if res.stdout:
                # Format: path:line:col: CODE Message
                pattern = re.compile(r"^([^:]+):(\d+):(\d+):\s*([A-Z0-9]+)\s*(.*)$")
                for line in res.stdout.splitlines():
                    m = pattern.match(line.strip())
                    if m:
                        diagnostics.append(
                            IDEDiagnostic(
                                file_path=m.group(1),
                                line=int(m.group(2)),
                                col=int(m.group(3)),
                                severity="warning",
                                code=m.group(4),
                                message=m.group(5),
                                source="Ruff",
                            )
                        )
                return diagnostics
        except Exception:
            pass

        # Try flake8
        flake8_cmd = [sys.executable, "-m", "flake8", "--isolated", file_path]
        try:
            res = subprocess.run(flake8_cmd, capture_output=True, text=True, timeout=5)
            pattern = re.compile(r"^([^:]+):(\d+):(\d+):\s*([A-Z0-9]+)\s*(.*)$")
            for line in (res.stdout + res.stderr).splitlines():
                m = pattern.match(line.strip())
                if m:
                    diagnostics.append(
                        IDEDiagnostic(
                            file_path=m.group(1),
                            line=int(m.group(2)),
                            col=int(m.group(3)),
                            severity="warning",
                            code=m.group(4),
                            message=m.group(5),
                            source="Flake8",
                        )
                    )
        except Exception:
            pass

        return diagnostics

    def inspect_project(
        self,
        project_path: Optional[str | Path] = None,
        max_files: int = 150,
    ) -> list[IDEDiagnostic]:
        """Scan all relevant source files in the project workspace."""
        root = Path(project_path).resolve() if project_path else self.workspace_path
        diagnostics: list[IDEDiagnostic] = []

        if not root.exists() or not root.is_dir():
            return [
                IDEDiagnostic(
                    file_path=str(root),
                    line=1,
                    col=1,
                    severity="error",
                    code="dir-not-found",
                    message=f"Project directory not found: {root}",
                    source="IDEInspector",
                )
            ]

        # Scan python files
        py_files: list[Path] = []
        exclude_dirs = {".git", ".venv", "venv", "__pycache__", "build", "dist", ".idea", ".gemini", "node_modules"}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
            for f in filenames:
                if f.endswith(".py"):
                    py_files.append(Path(dirpath) / f)
                    if len(py_files) >= max_files:
                        break
            if len(py_files) >= max_files:
                break

        for p in py_files:
            file_diags = self.inspect_file(p)
            diagnostics.extend(file_diags)

        return diagnostics

    def review_code_draft(
        self,
        file_path: str | Path,
        proposed_code: str,
    ) -> dict[str, Any]:
        """
        Compare diagnostics before and after applying a proposed code change.
        Returns whether the draft is safe to apply and any newly introduced issues.
        """
        target = Path(file_path).resolve()
        orig_diags = self.inspect_file(target) if target.exists() else []
        draft_diags = self.inspect_file(target, content=proposed_code)

        orig_codes = {f"{d.line}:{d.code}:{d.message}" for d in orig_diags}
        new_issues = [d for d in draft_diags if f"{d.line}:{d.code}:{d.message}" not in orig_codes]
        fixed_issues = [d for d in orig_diags if f"{d.line}:{d.code}:{d.message}" not in {f"{d.line}:{d.code}:{d.message}" for d in draft_diags}]

        has_syntax_error = any(d.severity == "error" for d in draft_diags)

        return {
            "is_valid": not has_syntax_error,
            "original_issue_count": len(orig_diags),
            "draft_issue_count": len(draft_diags),
            "new_issues": [d.to_dict() for d in new_issues],
            "fixed_issues": [d.to_dict() for d in fixed_issues],
            "all_draft_diagnostics": [d.to_dict() for d in draft_diags],
            "summary": (
                f"✅ ผ่านการตรวจทาน: ไวยากรณ์ถูกต้อง ปราศจาก Error (แก้ {len(fixed_issues)} จุด)"
                if not has_syntax_error
                else f"❌ พบข้อผิดพลาดทางไวยากรณ์ {len([d for d in draft_diags if d.severity == 'error'])} จุดในแบบร่าง!"
            ),
        }

    def format_report(self, diagnostics: list[IDEDiagnostic]) -> str:
        """Format a list of diagnostics into readable Markdown for user or LLM."""
        if not diagnostics:
            return "✅ ตรวจทานเสร็จสิ้น: ไม่พบข้อผิดพลาดหรือคำเตือนในโค้ด (Clean)"

        errors = [d for d in diagnostics if d.severity.lower() == "error"]
        warnings = [d for d in diagnostics if d.severity.lower() == "warning"]
        infos = [d for d in diagnostics if d.severity.lower() not in ("error", "warning")]

        lines = [
            "### 🔍 รายงานการตรวจทาน IDE Diagnostics & Debug",
            f"- **ข้อผิดพลาด (Errors):** {len(errors)} จุด",
            f"- **คำเตือน (Warnings):** {len(warnings)} จุด",
            f"- **ข้อมูลเพิ่มเติม (Infos):** {len(infos)} จุด\n",
            "| ลำดับ | ประเภท | แหล่งที่มา | ตำแหน่ง (ไฟล์:บรรทัด:คอลัมน์) | รหัสกฎ | รายละเอียด |",
            "| :---: | :---: | :---: | :--- | :---: | :--- |",
        ]

        for i, d in enumerate(diagnostics, 1):
            badge = "🔴 Error" if d.severity.lower() == "error" else ("🟡 Warning" if d.severity.lower() == "warning" else "🔵 Info")
            try:
                loc = f"{os.path.relpath(d.file_path)}:{d.line}:{d.col}"
            except ValueError:
                loc = f"{d.file_path}:{d.line}:{d.col}"
            clean_msg = d.message.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {i} | {badge} | {d.source} | `{loc}` | `{d.code}` | {clean_msg} |")

        return "\n".join(lines)
