"""
src/ui/tabs/draft_tab.py — Drafts & IDE Debug Review Tab for MAX.
Provides staged code draft viewing, unified diff color rendering,
IDE diagnostic scanning, and background automated test execution.
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Optional

try:
    from core.background_runner import BackgroundTestRunner, TestRunResult
    from core.draft_manager import CodeDraft, DraftManager
    from core.ide_inspector import IDEDiagnostic, IDEInspector
    from ui.themes import (
        FONT,
        FONT_BOLD,
        FONT_HDR,
        FONT_MONO,
        FONT_TINY,
        T,
    )
except (ImportError, ModuleNotFoundError):
    from src.core.background_runner import BackgroundTestRunner, TestRunResult  # type: ignore[no-redef]
    from src.core.draft_manager import CodeDraft, DraftManager  # type: ignore[no-redef]
    from src.core.ide_inspector import IDEDiagnostic, IDEInspector  # type: ignore[no-redef]
    from src.ui.themes import (  # type: ignore[no-redef]
        FONT,
        FONT_BOLD,
        FONT_HDR,
        FONT_MONO,
        FONT_TINY,
        T,
    )


class DraftReviewTab(tk.Frame):
    """
    Dedicated Tab in MAX Desktop GUI for reviewing staged code drafts,
    inspecting IDE debug diagnostics, and running tests in the background.
    """

    def __init__(
        self,
        parent: tk.Misc,
        tab_name: str = "📝 Drafts & Review",
        workspace_path: Optional[str | Path] = None,
        on_send_to_ai: Optional[Callable[[str], None]] = None,
        on_close: Optional[Callable[[DraftReviewTab], None]] = None,
    ) -> None:
        super().__init__(parent, bg=T["bg"])
        self.tab_name = tab_name
        self.workspace_path = Path(workspace_path).resolve() if workspace_path else Path.cwd()
        self.on_send_to_ai = on_send_to_ai
        self.on_close = on_close

        self.draft_manager = DraftManager.get_instance(self.workspace_path)
        self.ide_inspector = IDEInspector(self.workspace_path)
        self.test_runner = BackgroundTestRunner.get_instance(self.workspace_path)

        self._selected_draft_id: Optional[str] = None
        self._active_test_task_id: Optional[str] = None

        self._build_ui()
        self._refresh_drafts_list()
        self.draft_manager.add_listener(self._on_draft_event)

    def set_workspace_path(self, path: str | Path) -> None:
        """Update current project workspace path."""
        self.workspace_path = Path(path).resolve()
        self.draft_manager.workspace_path = self.workspace_path
        self.ide_inspector.workspace_path = self.workspace_path
        self.test_runner.workspace_path = self.workspace_path
        if hasattr(self, "_ws_label"):
            self._ws_label.config(text=f"📁 โฟลเดอร์: {self.workspace_path.name}")
        self._refresh_drafts_list()

    def _on_draft_event(self, draft: CodeDraft, event_type: str) -> None:
        """Called when DraftManager creates, applies, or discards a draft."""
        self.after(0, self._refresh_drafts_list)

    # ── UI Layout ─────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        # Top Header Bar
        top_bar = tk.Frame(self, bg=T["bg2"], pady=6, padx=10)
        top_bar.pack(fill="x", side="top")

        title_lbl = tk.Label(
            top_bar,
            text="📝 แบบร่าง & ตรวจทาน (Drafts & Debug Review)",
            bg=T["bg2"],
            fg=T["fg"],
            font=FONT_BOLD,
        )
        title_lbl.pack(side="left")

        self._ws_label = tk.Label(
            top_bar,
            text=f"📁 โฟลเดอร์: {self.workspace_path.name}",
            bg=T["bg2"],
            fg=T["sub"],
            font=FONT_TINY,
        )
        self._ws_label.pack(side="left", padx=(12, 0))

        if self.on_close:
            close_btn = tk.Button(
                top_bar,
                text="✕ ปิดแท็บ",
                bg=T["bg3"],
                fg=T["err_hdr"],
                font=FONT_TINY,
                relief="flat",
                command=lambda: self.on_close(self) if self.on_close else None,
                cursor="hand2",
            )
            close_btn.pack(side="right", padx=(6, 0))

        refresh_btn = tk.Button(
            top_bar,
            text="🔄 รีเฟรช",
            bg=T["bg3"],
            fg=T["fg"],
            font=FONT_TINY,
            relief="flat",
            command=self._refresh_drafts_list,
            cursor="hand2",
        )
        refresh_btn.pack(side="right", padx=(6, 0))

        clear_btn = tk.Button(
            top_bar,
            text="🧹 ล้างแบบร่างที่เสร็จแล้ว",
            bg=T["bg3"],
            fg=T["sub"],
            font=FONT_TINY,
            relief="flat",
            command=self._clear_finished_drafts,
            cursor="hand2",
        )
        clear_btn.pack(side="right")

        # Main Paned Window: Left (Drafts list), Right (Notebook Views)
        paned = tk.PanedWindow(self, orient="horizontal", bg=T["border"], sashwidth=4)
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        # ── Left Pane: Drafts List ────────────────────────────────────────────
        left_frame = tk.Frame(paned, bg=T["bg"], width=300)
        paned.add(left_frame, minsize=260)

        left_hdr = tk.Frame(left_frame, bg=T["bg2"], padx=8, pady=4)
        left_hdr.pack(fill="x")
        tk.Label(
            left_hdr,
            text="📋 รายการแบบร่าง (Staged Drafts)",
            bg=T["bg2"],
            fg=T["fg"],
            font=FONT_TINY,
        ).pack(side="left")

        self.drafts_tree = ttk.Treeview(
            left_frame,
            columns=("file", "status"),
            show="headings",
            selectmode="browse",
        )
        self.drafts_tree.heading("file", text="ไฟล์เป้าหมาย")
        self.drafts_tree.heading("status", text="สถานะ")
        self.drafts_tree.column("file", width=170)
        self.drafts_tree.column("status", width=85, anchor="center")
        self.drafts_tree.pack(fill="both", expand=True)
        self.drafts_tree.bind("<<TreeviewSelect>>", self._on_draft_selected)

        # Left bottom: Quick Diagnostics summary
        diag_box = tk.Frame(left_frame, bg=T["bg2"], padx=8, pady=6)
        diag_box.pack(fill="x", side="bottom")
        self.diag_summary_lbl = tk.Label(
            diag_box,
            text="🔍 พร้อมตรวจทาน IDE",
            bg=T["bg2"],
            fg=T["sub"],
            font=FONT_TINY,
            anchor="w",
        )
        self.diag_summary_lbl.pack(fill="x")

        # ── Right Pane: Sub-Notebook ──────────────────────────────────────────
        right_frame = tk.Frame(paned, bg=T["bg"])
        paned.add(right_frame, minsize=480)

        self.sub_notebook = ttk.Notebook(right_frame)
        self.sub_notebook.pack(fill="both", expand=True)

        # Tab 1: Diff & Code
        self.diff_tab = tk.Frame(self.sub_notebook, bg=T["bg"])
        self.sub_notebook.add(self.diff_tab, text=" 📝 Diff & พรีวิวโค้ด ")
        self._build_diff_view(self.diff_tab)

        # Tab 2: IDE Diagnostics
        self.diag_tab = tk.Frame(self.sub_notebook, bg=T["bg"])
        self.sub_notebook.add(self.diag_tab, text=" 🔍 ตรวจทาน IDE (Debug) ")
        self._build_diagnostics_view(self.diag_tab)

        # Tab 3: Background Test Runner
        self.test_tab = tk.Frame(self.sub_notebook, bg=T["bg"])
        self.sub_notebook.add(self.test_tab, text=" 🧪 ทดสอบเบื้องหลัง (Test) ")
        self._build_test_runner_view(self.test_tab)

    # ── Diff View ─────────────────────────────────────────────────────────────
    def _build_diff_view(self, parent: tk.Frame) -> None:
        toolbar = tk.Frame(parent, bg=T["bg2"], padx=8, pady=5)
        toolbar.pack(fill="x")

        self.diff_info_lbl = tk.Label(
            toolbar,
            text="กรุณาเลือกแบบร่างทางซ้ายมือ",
            bg=T["bg2"],
            fg=T["fg"],
            font=FONT_TINY,
        )
        self.diff_info_lbl.pack(side="left")

        self.apply_btn = tk.Button(
            toolbar,
            text="✅ นำไปใช้จริง (Apply)",
            bg="#1e7e34",
            fg="#ffffff",
            activebackground="#28a745",
            font=FONT_TINY,
            relief="flat",
            padx=10,
            pady=2,
            command=self._apply_current_draft,
            cursor="hand2",
            state="disabled",
        )
        self.apply_btn.pack(side="right", padx=(4, 0))

        self.discard_btn = tk.Button(
            toolbar,
            text="🗑 ยกเลิกแบบร่าง",
            bg=T["bg3"],
            fg=T["err_hdr"],
            font=FONT_TINY,
            relief="flat",
            padx=8,
            pady=2,
            command=self._discard_current_draft,
            cursor="hand2",
            state="disabled",
        )
        self.discard_btn.pack(side="right", padx=(4, 0))

        self.copy_diff_btn = tk.Button(
            toolbar,
            text="📋 คัดลอก Diff",
            bg=T["bg3"],
            fg=T["fg"],
            font=FONT_TINY,
            relief="flat",
            padx=8,
            pady=2,
            command=self._copy_diff_to_clipboard,
            cursor="hand2",
            state="disabled",
        )
        self.copy_diff_btn.pack(side="right")

        # Scrollable diff viewer
        diff_container = tk.Frame(parent, bg=T["code_bg"])
        diff_container.pack(fill="both", expand=True, padx=4, pady=4)

        self.diff_text = tk.Text(
            diff_container,
            bg=T["code_bg"],
            fg=T["code_fg"],
            font=FONT_MONO,
            wrap="none",
            relief="flat",
            padx=8,
            pady=8,
        )
        scroll_y = ttk.Scrollbar(diff_container, orient="vertical", command=self.diff_text.yview)
        scroll_x = ttk.Scrollbar(diff_container, orient="horizontal", command=self.diff_text.xview)
        self.diff_text.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.diff_text.pack(side="left", fill="both", expand=True)

        # Tags for colored diff rendering
        self.diff_text.tag_config("diff_add", foreground="#4ec9b0", background="#1e3a2f")
        self.diff_text.tag_config("diff_del", foreground="#f28b82", background="#3a1e22")
        self.diff_text.tag_config("diff_hdr", foreground="#8ab4f8", font=FONT_BOLD)
        self.diff_text.tag_config("diff_chunk", foreground="#dcdcaa", background="#2a2d2a")

    # ── IDE Diagnostics View ──────────────────────────────────────────────────
    def _build_diagnostics_view(self, parent: tk.Frame) -> None:
        toolbar = tk.Frame(parent, bg=T["bg2"], padx=8, pady=5)
        toolbar.pack(fill="x")

        tk.Button(
            toolbar,
            text="🔍 สแกนไฟล์ที่เลือก",
            bg=T["bg3"],
            fg=T["fg"],
            font=FONT_TINY,
            relief="flat",
            padx=8,
            pady=2,
            command=self._scan_current_file_diagnostics,
            cursor="hand2",
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            toolbar,
            text="📁 สแกนทั้งโปรเจกต์",
            bg=T["bg3"],
            fg=T["fg"],
            font=FONT_TINY,
            relief="flat",
            padx=8,
            pady=2,
            command=self._scan_project_diagnostics,
            cursor="hand2",
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            toolbar,
            text="🤖 ส่งให้ AI แก้ไขอัตโนมัติ",
            bg=T["bg3"],
            fg=T["accent"],
            font=FONT_TINY,
            relief="flat",
            padx=10,
            pady=2,
            command=self._send_diagnostics_to_ai,
            cursor="hand2",
        ).pack(side="right")

        # Treeview for diagnostics
        tree_frame = tk.Frame(parent, bg=T["bg"])
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.diag_tree = ttk.Treeview(
            tree_frame,
            columns=("severity", "source", "loc", "code", "message"),
            show="headings",
            selectmode="browse",
        )
        self.diag_tree.heading("severity", text="ประเภท")
        self.diag_tree.heading("source", text="แหล่งที่มา")
        self.diag_tree.heading("loc", text="ตำแหน่ง (บรรทัด:คอลัมน์)")
        self.diag_tree.heading("code", text="รหัสกฎ")
        self.diag_tree.heading("message", text="รายละเอียดข้อผิดพลาด")

        self.diag_tree.column("severity", width=70, anchor="center")
        self.diag_tree.column("source", width=90, anchor="center")
        self.diag_tree.column("loc", width=140)
        self.diag_tree.column("code", width=110)
        self.diag_tree.column("message", width=340)

        diag_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.diag_tree.yview)
        self.diag_tree.configure(yscrollcommand=diag_scroll_y.set)
        diag_scroll_y.pack(side="right", fill="y")
        self.diag_tree.pack(side="left", fill="both", expand=True)

    # ── Background Test Runner View ───────────────────────────────────────────
    def _build_test_runner_view(self, parent: tk.Frame) -> None:
        # Top toolbar with command and trigger
        top_ctrl = tk.Frame(parent, bg=T["bg2"], padx=8, pady=6)
        top_ctrl.pack(fill="x")

        tk.Label(
            top_ctrl,
            text="คำสั่งทดสอบ:",
            bg=T["bg2"],
            fg=T["fg"],
            font=FONT_TINY,
        ).pack(side="left", padx=(0, 4))

        self.test_cmd_var = tk.StringVar(value=f"{sys.executable} -m unittest discover -s tests")
        self.test_cmd_entry = tk.Entry(
            top_ctrl,
            textvariable=self.test_cmd_var,
            bg=T["composer_bg"],
            fg=T["fg"],
            insertbackground=T["fg"],
            font=FONT_MONO,
            relief="flat",
        )
        self.test_cmd_entry.pack(side="left", fill="x", expand=True, padx=4)

        self.start_test_btn = tk.Button(
            top_ctrl,
            text="▶ รันการทดสอบเบื้องหลัง",
            bg="#1a73e8",
            fg="#ffffff",
            activebackground="#1557b0",
            font=FONT_TINY,
            relief="flat",
            padx=12,
            pady=2,
            command=self._start_background_test,
            cursor="hand2",
        )
        self.start_test_btn.pack(side="left", padx=4)

        self.stop_test_btn = tk.Button(
            top_ctrl,
            text="⏹ หยุด",
            bg=T["bg3"],
            fg=T["err_hdr"],
            font=FONT_TINY,
            relief="flat",
            padx=8,
            pady=2,
            command=self._stop_background_test,
            cursor="hand2",
            state="disabled",
        )
        self.stop_test_btn.pack(side="left")

        # Quick presets
        preset_bar = tk.Frame(parent, bg=T["bg"], padx=8, pady=4)
        preset_bar.pack(fill="x")
        tk.Label(preset_bar, text="คำสั่งด่วน:", bg=T["bg"], fg=T["sub"], font=FONT_TINY).pack(side="left")

        presets = [
            ("ชุดทดสอบทั้งหมด (All)", f"{sys.executable} -m unittest discover -s tests"),
            ("ทดสอบ MCP & Builtins", f"{sys.executable} -m unittest tests/test_mcp_integration.py"),
            ("ทดสอบ Scenario จริง", f"{sys.executable} tests/verify_scenario.py"),
        ]
        for title, cmd_str in presets:
            btn = tk.Button(
                preset_bar,
                text=title,
                bg=T["bg2"],
                fg=T["fg"],
                font=FONT_TINY,
                relief="flat",
                padx=6,
                pady=1,
                command=lambda c=cmd_str: self.test_cmd_var.set(c),
                cursor="hand2",
            )
            btn.pack(side="left", padx=3)

        # Status Banner
        self.test_status_banner = tk.Frame(parent, bg=T["bg2"], padx=10, pady=5)
        self.test_status_banner.pack(fill="x", padx=4, pady=(2, 4))

        self.test_status_lbl = tk.Label(
            self.test_status_banner,
            text="⚪ สถานะ: พร้อมรันการทดสอบเบื้องหลัง",
            bg=T["bg2"],
            fg=T["fg"],
            font=FONT_BOLD,
        )
        self.test_status_lbl.pack(side="left")

        self.test_metrics_lbl = tk.Label(
            self.test_status_banner,
            text="",
            bg=T["bg2"],
            fg=T["sub"],
            font=FONT_TINY,
        )
        self.test_metrics_lbl.pack(side="right")

        # Terminal Console Box
        console_box = tk.Frame(parent, bg="#0d1117")
        console_box.pack(fill="both", expand=True, padx=4, pady=4)

        self.test_console = tk.Text(
            console_box,
            bg="#0d1117",
            fg="#c9d1d9",
            font=FONT_MONO,
            wrap="char",
            relief="flat",
            padx=8,
            pady=8,
        )
        con_scroll_y = ttk.Scrollbar(console_box, orient="vertical", command=self.test_console.yview)
        self.test_console.configure(yscrollcommand=con_scroll_y.set)
        con_scroll_y.pack(side="right", fill="y")
        self.test_console.pack(side="left", fill="both", expand=True)

    # ── Logic & Event Handlers ────────────────────────────────────────────────
    def _refresh_drafts_list(self) -> None:
        """Reload drafts from DraftManager."""
        for item in self.drafts_tree.get_children():
            self.drafts_tree.delete(item)

        drafts = self.draft_manager.list_drafts()
        pending_count = 0
        for d in reversed(drafts):
            filename = Path(d.file_path).name
            status_icon = "🟡 รอดำเนินการ" if d.status == "PENDING" else ("🟢 นำไปใช้แล้ว" if d.status == "APPLIED" else "⚪ ยกเลิกแล้ว")
            if d.has_syntax_error:
                status_icon += " ⚠️"
            if d.status == "PENDING":
                pending_count += 1
            self.drafts_tree.insert("", "end", iid=d.draft_id, values=(filename, status_icon))

        self.diag_summary_lbl.config(
            text=f"📋 แบบร่างทั้งหมด: {len(drafts)} (รอใช้: {pending_count})"
        )

        if self._selected_draft_id and self.draft_manager.get_draft(self._selected_draft_id):
            self.drafts_tree.selection_set(self._selected_draft_id)
        elif drafts:
            first_id = drafts[-1].draft_id
            self.drafts_tree.selection_set(first_id)
            self._load_draft_into_view(first_id)

    def _on_draft_selected(self, event: Any) -> None:
        sel = self.drafts_tree.selection()
        if not sel:
            return
        draft_id = sel[0]
        self._load_draft_into_view(draft_id)

    def _load_draft_into_view(self, draft_id: str) -> None:
        draft = self.draft_manager.get_draft(draft_id)
        if not draft:
            return

        self._selected_draft_id = draft_id
        rel_path = draft.file_path
        try:
            rel_path = os.path.relpath(draft.file_path, str(self.workspace_path))
        except ValueError:
            pass

        self.diff_info_lbl.config(
            text=f"📄 ไฟล์: {rel_path} | สถานะ: {draft.status} | สร้างเมื่อ: {draft.created_at}"
        )

        # Update Buttons
        can_apply = draft.status == "PENDING"
        self.apply_btn.config(state="normal" if can_apply else "disabled")
        self.discard_btn.config(state="normal" if can_apply else "disabled")
        self.copy_diff_btn.config(state="normal")

        # Render Diff with colors
        self.diff_text.delete("1.0", "end")
        lines = draft.diff_preview.splitlines(keepends=True)
        for line in lines:
            if line.startswith("+++") or line.startswith("---") or line.startswith("📝"):
                self.diff_text.insert("end", line, "diff_hdr")
            elif line.startswith("@@"):
                self.diff_text.insert("end", line, "diff_chunk")
            elif line.startswith("+"):
                self.diff_text.insert("end", line, "diff_add")
            elif line.startswith("-"):
                self.diff_text.insert("end", line, "diff_del")
            else:
                self.diff_text.insert("end", line)

        # Load diagnostics for this draft into diagnostics tree
        for item in self.diag_tree.get_children():
            self.diag_tree.delete(item)

        for d in draft.diagnostics:
            sev = d.get("severity", "info").upper()
            icon = "🔴 ERROR" if sev == "ERROR" else ("🟡 WARN" if sev == "WARNING" else "🔵 INFO")
            loc = f"{d.get('line', 1)}:{d.get('col', 1)}"
            self.diag_tree.insert(
                "",
                "end",
                values=(icon, d.get("source", "IDE"), loc, d.get("code", "-"), d.get("message", "")),
            )

    def _apply_current_draft(self) -> None:
        if not self._selected_draft_id:
            return
        draft = self.draft_manager.get_draft(self._selected_draft_id)
        if not draft:
            return

        confirm = messagebox.askyesno(
            "ยืนยันการนำแบบร่างไปใช้",
            f"คุณต้องการบันทึกการเปลี่ยนแปลงของแบบร่างนี้ลงในไฟล์:\n'{Path(draft.file_path).name}' หรือไม่?\n\n(ระบบจะสำรองไฟล์เดิมเป็น .bak ให้อัตโนมัติ)",
            parent=self,
        )
        if not confirm:
            return

        success, msg = self.draft_manager.apply_draft(self._selected_draft_id)
        if success:
            messagebox.showinfo("สำเร็จ", msg, parent=self)
            self._load_draft_into_view(self._selected_draft_id)
        else:
            messagebox.showerror("เกิดข้อผิดพลาด", msg, parent=self)

    def _discard_current_draft(self) -> None:
        if not self._selected_draft_id:
            return
        if messagebox.askyesno("ยืนยันการยกเลิก", "ต้องการยกเลิกแบบร่างนี้หรือไม่?", parent=self):
            self.draft_manager.discard_draft(self._selected_draft_id)
            self._refresh_drafts_list()

    def _clear_finished_drafts(self) -> None:
        cleared = self.draft_manager.clear_finished_drafts()
        self._refresh_drafts_list()
        messagebox.showinfo("ล้างแบบร่าง", f"ล้างแบบร่างที่เสร็จสิ้นแล้ว {cleared} รายการ", parent=self)

    def _copy_diff_to_clipboard(self) -> None:
        content = self.diff_text.get("1.0", "end-1c")
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("คัดลอก", "คัดลอกข้อความ Diff ไปยัง Clipboard เรียบร้อยแล้ว", parent=self)

    def _scan_current_file_diagnostics(self) -> None:
        """Scan active draft target file for diagnostics."""
        if not self._selected_draft_id:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกไฟล์แบบร่างทางซ้ายมือก่อนครับ", parent=self)
            return
        draft = self.draft_manager.get_draft(self._selected_draft_id)
        if not draft:
            return

        diags = self.ide_inspector.inspect_file(draft.file_path)
        self._display_diagnostics(diags)
        self.sub_notebook.select(self.diag_tab)

    def _scan_project_diagnostics(self) -> None:
        """Scan entire workspace project for diagnostics."""
        self.diag_summary_lbl.config(text="⏳ กำลังสแกนตรวจทานโปรเจกต์...")
        self.update_idletasks()

        def _worker():
            diags = self.ide_inspector.inspect_project(self.workspace_path)
            self.after(0, lambda: self._display_diagnostics(diags))

        threading.Thread(target=_worker, daemon=True).start()
        self.sub_notebook.select(self.diag_tab)

    def _display_diagnostics(self, diags: list[IDEDiagnostic]) -> None:
        for item in self.diag_tree.get_children():
            self.diag_tree.delete(item)

        err_cnt = sum(1 for d in diags if d.severity.lower() == "error")
        warn_cnt = sum(1 for d in diags if d.severity.lower() == "warning")

        for d in diags:
            icon = "🔴 ERROR" if d.severity.lower() == "error" else ("🟡 WARN" if d.severity.lower() == "warning" else "🔵 INFO")
            try:
                rel = os.path.relpath(d.file_path, str(self.workspace_path))
            except ValueError:
                rel = Path(d.file_path).name
            loc = f"{rel}:{d.line}:{d.col}"
            self.diag_tree.insert(
                "",
                "end",
                values=(icon, d.source, loc, d.code, d.message),
            )

        self.diag_summary_lbl.config(
            text=f"🔍 ตรวจพบ: 🔴 Errors: {err_cnt} | 🟡 Warnings: {warn_cnt}"
        )

    def _send_diagnostics_to_ai(self) -> None:
        """Send current diagnostic list as a prompt to the AI chat tab."""
        children = self.diag_tree.get_children()
        if not children:
            messagebox.showinfo("ข้อมูล", "ไม่พบข้อผิดพลาดที่ต้องส่งให้ AI แก้ไขครับ (สะอาดเรียบร้อย)", parent=self)
            return

        issues_text: list[str] = []
        for item in children[:20]:  # limit to top 20 issues
            item_data = self.diag_tree.item(item)
            raw_vals = item_data.get("values") if isinstance(item_data, dict) else None
            if isinstance(raw_vals, (list, tuple)) and len(raw_vals) >= 5:
                issues_text.append(f"- [{raw_vals[0]}] {raw_vals[2]} [{raw_vals[3]}]: {raw_vals[4]}")
            elif isinstance(raw_vals, (list, tuple)) and raw_vals:
                issues_text.append(f"- {' '.join(str(v) for v in raw_vals)}")

        prompt = (
            "กรุณาช่วยตรวจสอบและแก้ไขบั๊กตามรายงาน IDE Diagnostics ต่อไปนี้:\n"
            + "\n".join(issues_text)
            + "\n\nโปรดอธิบายสาเหตุและแนวทางการแก้ไขทีละจุดพร้อมระบุโค้ดที่ถูกต้อง"
        )

        if self.on_send_to_ai:
            self.on_send_to_ai(prompt)
        else:
            self.clipboard_clear()
            self.clipboard_append(prompt)
            messagebox.showinfo(
                "ส่งให้ AI",
                "คัดลอกข้อความ Diagnostics ไปยัง Clipboard แล้ว คุณสามารถวางในแชทเพื่อสั่ง AI ได้ทันที",
                parent=self,
            )

    # ── Background Test Logic ─────────────────────────────────────────────────
    def _start_background_test(self) -> None:
        cmd_str = self.test_cmd_var.get().strip()
        if not cmd_str:
            return

        self.start_test_btn.config(state="disabled")
        self.stop_test_btn.config(state="normal")
        self.test_status_lbl.config(
            text="🟡 กำลังรันการทดสอบเบื้องหลัง (Running)...",
            fg="#e3b341",
        )
        self.test_metrics_lbl.config(text="")
        self.test_console.delete("1.0", "end")
        self.test_console.insert("end", f"$ {cmd_str}\n\n")

        def _on_update(run: TestRunResult):
            self.after(0, lambda: self._update_test_console(run))

        def _on_finish(run: TestRunResult):
            self.after(0, lambda: self._finish_test_run(run))

        self._active_test_task_id = self.test_runner.start_test_run(
            custom_command=cmd_str,
            cwd=self.workspace_path,
            on_update=_on_update,
            on_finish=_on_finish,
        )

    def _update_test_console(self, run: TestRunResult) -> None:
        combined = run.stdout + run.stderr
        self.test_console.delete("1.0", "end")
        self.test_console.insert("end", f"$ {' '.join(run.command)}\n\n{combined}")
        self.test_console.see("end")

    def _finish_test_run(self, run: TestRunResult) -> None:
        self.start_test_btn.config(state="normal")
        self.stop_test_btn.config(state="disabled")
        self._update_test_console(run)

        color = "#4ec9b0" if run.status == "PASSED" else ("#f28b82" if run.status == "FAILED" else "#e3b341")
        self.test_status_lbl.config(text=f"{run.summary}", fg=color)
        self.test_metrics_lbl.config(
            text=f"⏱ ใช้เวลา: {run.duration_sec:.2f}s | Exit code: {run.exit_code}"
        )

    def _stop_background_test(self) -> None:
        if self._active_test_task_id:
            self.test_runner.cancel_run(self._active_test_task_id)
            self.stop_test_btn.config(state="disabled")
            self.start_test_btn.config(state="normal")
            self.test_status_lbl.config(text="⏹ การทดสอบถูกยกเลิก", fg=T["err_hdr"])
