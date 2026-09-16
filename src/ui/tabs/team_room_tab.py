"""
src/ui/tabs/team_room_tab.py — Multi-Agent Team Room Tab for MAX.
Orchestrates collaborative workflows among specialized AI agents:
Planner -> Coder -> Reviewer (with per-agent independent Provider, Model, and System Prompt).
"""

from dataclasses import asdict
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Any, Optional

try:
    from core.ai_client import AIClient
    from ui.dialogs.team_config_dialog import TeamAgentConfig, TeamConfigDialog, get_default_team_agents
    from ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_HDR
    from ui.widgets.context_menu import attach_text_context_menu
    from ui.widgets.message_bubble import MessageBubble
    from ui.widgets.scrollable_frame import ScrollableFrame
except (ImportError, ModuleNotFoundError):
    from src.core.ai_client import AIClient  # type: ignore[no-redef]
    from src.ui.dialogs.team_config_dialog import (  # type: ignore[no-redef]
        TeamAgentConfig,
        TeamConfigDialog,
        get_default_team_agents,
    )
    from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_HDR  # type: ignore[no-redef]
    from src.ui.widgets.context_menu import attach_text_context_menu  # type: ignore[no-redef]
    from src.ui.widgets.message_bubble import MessageBubble  # type: ignore[no-redef]
    from src.ui.widgets.scrollable_frame import ScrollableFrame  # type: ignore[no-redef]


class AgentTeamTab(tk.Frame):
    """
    Multi-Agent Team Room Session:
    User submits a single prompt or goal, and the AI Team (Planner, Coder, Reviewer)
    collaboratively works together in sequence.
    """

    def __init__(
        self,
        parent: tk.Misc,
        tab_name: str = "👥 Team Room",
        profiles: Optional[list[dict[str, Any]]] = None,
        default_profile_id: str = "",
    ) -> None:
        super().__init__(parent, bg=T["bg"])
        self.tab_name = tab_name
        self.profiles = profiles or []
        self.default_profile_id = default_profile_id
        self._is_running = False
        self._stop_requested = False
        self._bubbles: list[MessageBubble] = []

        # Initialize default team agents
        self.agents = get_default_team_agents()
        self._init_agents_with_defaults()

        self._build_ui()

    def _init_agents_with_defaults(self) -> None:
        """Assign default profiles to agents if unassigned."""
        active_prof = next((p for p in self.profiles if p["id"] == self.default_profile_id), None)
        if not active_prof and self.profiles:
            active_prof = self.profiles[0]

        for agent in self.agents:
            if not agent.profile_id and active_prof:
                agent.profile_id = active_prof["id"]
                agent.profile_name = active_prof["name"]
                if not agent.model:
                    agent.model = active_prof["model"]

    def _build_ui(self) -> None:
        # 1. Team Header Bar
        self._header = tk.Frame(
            self,
            bg=T["bg2"],
            padx=12,
            pady=6,
            highlightthickness=1,
            highlightbackground=T["border"],
        )
        self._header.pack(fill="x", padx=16, pady=(4, 4))

        # Left: Team Badges
        self._badge_frame = tk.Frame(self._header, bg=T["bg2"])
        self._badge_frame.pack(side="left")
        self._render_agent_badges()

        # Right: Config & Action buttons
        self._btn_frame = tk.Frame(self._header, bg=T["bg2"])
        self._btn_frame.pack(side="right")

        self._stop_btn = tk.Button(
            self._btn_frame,
            text="⏹ หยุด",
            bg=T["err_hdr"],
            fg="#ffffff",
            activebackground=T["bg3"],
            activeforeground="#ffffff",
            font=FONT_TINY,
            relief="flat",
            padx=10,
            pady=3,
            state="disabled",
            cursor="hand2",
            command=self._stop_pipeline,
        )
        self._stop_btn.pack(side="right", padx=(6, 0))

        self._config_btn = tk.Button(
            self._btn_frame,
            text="⚙ ตั้งค่าทีม",
            bg=T["bg"],
            fg=T["fg"],
            activebackground=T["bg3"],
            activeforeground=T["accent"],
            font=FONT_TINY,
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._open_team_config,
        )
        self._config_btn.pack(side="right", padx=(6, 0))

        self._clear_btn = tk.Button(
            self._btn_frame,
            text="🗑 ล้างห้อง",
            bg=T["bg"],
            fg=T["fg_dim"],
            activebackground=T["bg3"],
            activeforeground=T["err_hdr"],
            font=FONT_TINY,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._clear_chat,
        )
        self._clear_btn.pack(side="right")

        # 2. Scrollable Messages Area
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=6)

        # 3. Status Bar
        self.status_var = tk.StringVar(value="พร้อมสั่งการทีม AI (Planner ➔ Coder ➔ Reviewer)")
        self._status_lbl = tk.Label(
            self,
            textvariable=self.status_var,
            bg=T["bg"],
            fg=T["fg_dim"],
            font=FONT_TINY,
            anchor="w",
            padx=18,
        )
        self._status_lbl.pack(fill="x", pady=(2, 0))

        # 4. Composer Card
        self._composer = tk.Frame(
            self,
            bg=T["composer_bg"],
            padx=14,
            pady=10,
            highlightthickness=1,
            highlightbackground=T["border"],
        )
        self._composer.pack(fill="x", padx=16, pady=(4, 6))

        # Composer text entry
        entry_wrap = tk.Frame(self._composer, bg=T["bg2"], bd=1, relief="solid")
        entry_wrap.pack(fill="x", expand=True, side="left", padx=(0, 10))

        self.entry = tk.Entry(
            entry_wrap,
            bg=T["bg2"],
            fg=T["fg"],
            insertbackground=T["fg"],
            font=FONT,
            relief="flat",
            bd=0,
        )
        self.entry.pack(fill="x", padx=8, pady=8)
        self.entry.bind("<Return>", lambda _e: self._send_task())
        attach_text_context_menu(self.entry, is_editable=True)

        self._run_btn = tk.Button(
            self._composer,
            text="🚀 ส่งโจทย์ให้ทีม",
            bg=T["accent"],
            fg="#ffffff",
            activebackground=T["accent_hover"],
            activeforeground="#ffffff",
            font=FONT_BOLD,
            relief="flat",
            padx=18,
            pady=6,
            cursor="hand2",
            command=self._send_task,
        )
        self._run_btn.pack(side="right")

    def _render_agent_badges(self) -> None:
        """Render small badges for each active agent in the header."""
        for widget in self._badge_frame.winfo_children():
            widget.destroy()

        enabled_agents = [a for a in self.agents if a.enabled]
        for i, agent in enumerate(enabled_agents):
            model_short = agent.model.split("/")[-1] if agent.model else "default"
            badge = tk.Label(
                self._badge_frame,
                text=f"{agent.icon} {agent.name} [{model_short}]",
                bg=T["bg3"],
                fg=agent.hdr_color,
                font=FONT_TINY,
                padx=8,
                pady=2,
            )
            badge.pack(side="left", padx=(0, 4))

            if i < len(enabled_agents) - 1:
                arrow = tk.Label(
                    self._badge_frame,
                    text="➔",
                    bg=T["bg2"],
                    fg=T["fg_dim"],
                    font=FONT_TINY,
                )
                arrow.pack(side="left", padx=(0, 4))

    def _open_team_config(self) -> None:
        def _on_save(new_agents: list[TeamAgentConfig]) -> None:
            self.agents = new_agents
            self._render_agent_badges()
            self.status_var.set("อัปเดตการตั้งค่าทีม AI สำเร็จ")

        TeamConfigDialog(self, self.profiles, self.agents, _on_save)

    def _clear_chat(self) -> None:
        if self._is_running:
            messagebox.showwarning("เตือน", "ทีมกำลังทำงานอยู่ กรุณากดปุ่ม หยุด ก่อนล้างห้อง", parent=self)
            return
        for b in self._bubbles:
            b.destroy()
        self._bubbles.clear()
        self.status_var.set("ล้างการสนทนาในห้องทีมแล้ว")

    def _stop_pipeline(self) -> None:
        if self._is_running:
            self._stop_requested = True
            self.status_var.set("⏹ กำลังหยุดการทำงานของทีม...")
            self._stop_btn.configure(state="disabled")

    def _add_bubble(
        self,
        role: str,
        text: str,
        bg: str,
        hdr_color: str,
        is_thinking: bool = False,
    ) -> MessageBubble:
        bubble = MessageBubble(
            self.scroll.inner,
            role=role,
            content=text,
            bg_card=bg,
            hdr_color=hdr_color,
            is_thinking=is_thinking,
        )
        self._bubbles.append(bubble)
        self.scroll.scroll_bottom()
        return bubble

    def _send_task(self) -> None:
        if self._is_running:
            return
        task = self.entry.get().strip()
        if not task:
            return

        self.entry.delete(0, "end")
        self._is_running = True
        self._stop_requested = False
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")

        # 1. Display User Task Bubble
        self._add_bubble("คุณ (โจทย์สำหรับทีม)", task, T["bg_user"], T["user_hdr"])

        # 2. Launch background pipeline
        threading.Thread(target=self._run_team_pipeline, args=(task,), daemon=True).start()

    def _create_agent_client(self, agent: TeamAgentConfig) -> AIClient:
        """Create an AIClient customized for this specific agent role."""
        prof = next((p for p in self.profiles if p["id"] == agent.profile_id), None)
        if not prof and self.profiles:
            prof = self.profiles[0]

        api_key = prof["api_key"] if prof else ""
        base_url = prof["base_url"] if prof else ""
        api_mode = prof.get("api_mode", "chat_completions") if prof else "chat_completions"
        model = agent.model or (prof["model"] if prof else "default")

        return AIClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            api_mode=api_mode,
            system_prompt=agent.system_prompt,
            timeout=120,
        )

    def _run_team_pipeline(self, user_task: str) -> None:
        """Sequential Multi-Agent Execution Pipeline."""
        active_agents = [a for a in self.agents if a.enabled]
        agent_outputs: dict[str, str] = {}

        try:
            for idx, agent in enumerate(active_agents):
                if self._stop_requested:
                    self.after(
                        0,
                        lambda a_name=agent.name: self.status_var.set(
                            f"⏹ ผู้ใช้หยุดการทำงานก่อนถึง {a_name}"
                        ),
                    )
                    break

                self.after(
                    0,
                    lambda a=agent, i=idx + 1, total=len(active_agents): self.status_var.set(
                        f"[{i}/{total}] {a.icon} {a.name} กำลังดำเนินการ..."
                    ),
                )

                # Prepare agent-specific context prompt
                prompt_content = self._build_agent_prompt(agent.id, user_task, agent_outputs)

                # Create Thinking Bubble for this agent
                model_tag = agent.model.split("/")[-1] if agent.model else "default"
                role_label = f"{agent.icon} {agent.name} [{model_tag}]"

                # We must create UI bubble in the main thread
                bubble_event = threading.Event()
                thinking_bubble: list[Optional[MessageBubble]] = [None]

                def _create_bubble() -> None:
                    thinking_bubble[0] = self._add_bubble(
                        role=role_label,
                        text="",
                        bg=T["bg_ai"],
                        hdr_color=agent.hdr_color,
                        is_thinking=True,
                    )
                    bubble_event.set()

                self.after(0, _create_bubble)
                bubble_event.wait()
                bubble = thinking_bubble[0]

                # Run Agent Client
                client = self._create_agent_client(agent)
                start_time = time.monotonic()
                full_reply = ""

                def _on_chunk(token: str) -> None:
                    if bubble:
                        self.after(0, lambda t=token: bubble.append_stream_chunk(t))

                try:
                    full_reply = client.stream_ask(
                        prompt_content,
                        on_chunk=_on_chunk,
                        temperature=agent.temperature,
                        max_tokens=agent.max_tokens,
                    )
                except Exception as ex:
                    full_reply = f"❌ เกิดข้อผิดพลาดในบทบาท {agent.name}: {ex}"

                elapsed = time.monotonic() - start_time
                agent_outputs[agent.id] = full_reply

                if bubble:
                    self.after(
                        0,
                        lambda b=bubble, r=full_reply, rl=role_label, el=elapsed: b.finish_processing(
                            r, rl, el
                        ),
                    )

            if not self._stop_requested:
                self.after(0, lambda: self.status_var.set("✨ ทีม AI ดำเนินการครบทุกขั้นตอนเรียบร้อย"))
        finally:
            self.after(0, self._on_pipeline_finished)

    def _build_agent_prompt(
        self, agent_id: str, user_task: str, previous_outputs: dict[str, str]
    ) -> str:
        """Construct tailored prompt injecting previous agents' insights."""
        if agent_id == "planner":
            return (
                f"เป้าหมาย / ความต้องการจากผู้ใช้:\n"
                f"\"\"\"\n{user_task}\n\"\"\"\n\n"
                f"กรุณาวิเคราะห์โจทย์ ออกแบบสถาปัตยกรรม (Architecture) "
                f"และกำหนดแผนขั้นตอนการพัฒนาที่ละเอียดและชัดเจนสำหรับ Coder"
            )
        elif agent_id == "coder":
            planner_spec = previous_outputs.get("planner", "(ไม่มีแผนงานจาก Planner)")
            return (
                f"[โจทย์จากผู้ใช้]:\n{user_task}\n\n"
                f"[แผนสถาปัตยกรรมและข้อกำหนดจาก Planner]:\n{planner_spec}\n\n"
                f"คำสั่ง: กรุณาเขียนโค้ดและพัฒนา Solution ฉบับสมบูรณ์ พร้อมคำอธิบายและแนวทางการรัน/ทดสอบ"
            )
        elif agent_id == "reviewer":
            planner_spec = previous_outputs.get("planner", "(ไม่มีแผนงานจาก Planner)")
            coder_code = previous_outputs.get("coder", "(ไม่มีโค้ดจาก Coder)")
            return (
                f"[โจทย์จากผู้ใช้]:\n{user_task}\n\n"
                f"[แผนงานจาก Planner]:\n{planner_spec}\n\n"
                f"[โค้ดที่เขียนโดย Coder]:\n{coder_code}\n\n"
                f"คำสั่ง: กรุณาตรวจทานโค้ด (Code Review) หาบั๊ก ขอบเขตความปลอดภัย (Security) "
                f"จุดปรับปรุงประสิทธิภาพ (Performance) และสรุปความพร้อมของโค้ด"
            )
        else:
            # Generic fallback
            history_summary = "\n\n".join(
                f"[{k.upper()}]:\n{v}" for k, v in previous_outputs.items()
            )
            return f"User Goal:\n{user_task}\n\nPrevious outputs:\n{history_summary}\n\nPlease proceed."

    def _on_pipeline_finished(self) -> None:
        self._is_running = False
        self._stop_requested = False
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self.scroll.scroll_bottom()
