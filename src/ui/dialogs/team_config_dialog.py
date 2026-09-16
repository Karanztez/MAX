"""
src/ui/dialogs/team_config_dialog.py — Dialog for configuring Multi-Agent Team Room members.
Allows configuring Provider, Model, System Prompt, and parameters for each agent role.
Supports dynamically adding, removing, and reordering team members with same or different models.
"""

from dataclasses import dataclass, asdict
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Callable

try:
    from ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_TITLE
    from ui.widgets.context_menu import attach_text_context_menu
except (ImportError, ModuleNotFoundError):
    from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_TITLE  # type: ignore[no-redef]
    from src.ui.widgets.context_menu import attach_text_context_menu  # type: ignore[no-redef]


@dataclass
class TeamAgentConfig:
    id: str
    name: str
    icon: str
    role_description: str
    enabled: bool = True
    profile_id: str = ""
    profile_name: str = ""
    model: str = ""
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    hdr_color: str = "#60a5fa"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TeamAgentConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def get_default_team_agents() -> list[TeamAgentConfig]:
    """Return standard 3-agent software engineering team."""
    return [
        TeamAgentConfig(
            id="planner",
            name="Planner",
            icon="📋",
            role_description="วิเคราะห์ความต้องการ ออกแบบโครงสร้างสถาปัตยกรรม และวางแผนงาน",
            enabled=True,
            profile_id="",
            profile_name="",
            model="",
            system_prompt=(
                "You are an expert Software Architect & Technical Planner. "
                "Your role is to thoroughly analyze the user's requirements, determine the best architecture, "
                "break down the tasks into logical implementation steps, specify component designs and data models, "
                "and formulate precise, actionable specifications for the Coder. Output clear, well-structured plans."
            ),
            temperature=0.6,
            max_tokens=4096,
            hdr_color="#60a5fa",  # Soft Blue
        ),
        TeamAgentConfig(
            id="coder",
            name="Coder",
            icon="💻",
            role_description="รับข้อกำหนดจาก Planner แล้วเขียนโค้ดและพัฒนา Solution ที่สมบูรณ์",
            enabled=True,
            profile_id="",
            profile_name="",
            model="",
            system_prompt=(
                "You are a Senior Full-Stack Software Engineer. "
                "Your role is to implement complete, production-ready, clean, and robust code based on "
                "the user's request and the Planner's architectural specification. "
                "Write clear, modular, well-commented code with proper error handling and unit test guidance."
            ),
            temperature=0.4,
            max_tokens=4096,
            hdr_color="#34d399",  # Soft Emerald Green
        ),
        TeamAgentConfig(
            id="reviewer",
            name="Reviewer",
            icon="🔍",
            role_description="ตรวจทานโค้ด ตรวจสอบความปลอดภัย หักมุมบั๊ก และประเมินคุณภาพ",
            enabled=True,
            profile_id="",
            profile_name="",
            model="",
            system_prompt=(
                "You are a Staff QA Engineer & Security Auditor. "
                "Your role is to critically inspect the Coder's implementation against the original requirements and Planner's spec. "
                "Look for potential bugs, edge cases, security vulnerabilities, performance bottlenecks, and style issues. "
                "Provide constructive feedback, corrected code snippets if necessary, and a final quality verdict."
            ),
            temperature=0.5,
            max_tokens=4096,
            hdr_color="#fbbf24",  # Soft Amber Gold
        ),
    ]


PRESET_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "Tester",
        "icon": "🧪",
        "role_description": "เขียน Unit Tests และทดสอบความถูกต้องของระบบ",
        "system_prompt": (
            "You are a QA Automation & Test Engineer. "
            "Write comprehensive, robust, and clean unit/integration tests for the code created by the team. "
            "Cover edge cases, error conditions, boundary values, and provide mock examples."
        ),
        "temperature": 0.3,
        "hdr_color": "#a78bfa",  # Soft Purple
    },
    {
        "name": "Security",
        "icon": "🛡️",
        "role_description": "ตรวจสอบช่องโหว่ความปลอดภัยและวิเคราะห์ภัยคุกคาม",
        "system_prompt": (
            "You are a Cybersecurity & Penetration Testing Specialist. "
            "Analyze the architecture and code for security vulnerabilities (OWASP Top 10, injection, auth bypass, data leaks), "
            "and suggest concrete hardening measures."
        ),
        "temperature": 0.3,
        "hdr_color": "#f87171",  # Soft Red
    },
    {
        "name": "Docs",
        "icon": "📝",
        "role_description": "เขียนคู่มือการใช้งาน, API Docs, และสรุปวิธีติดตั้ง",
        "system_prompt": (
            "You are a Technical Writer. "
            "Create clear, professional, and thorough documentation, README, and API guides based on "
            "the system designed and implemented by the team."
        ),
        "temperature": 0.5,
        "hdr_color": "#38bdf8",  # Soft Sky Blue
    },
    {
        "name": "DevOps",
        "icon": "🚀",
        "role_description": "ออกแบบ Docker, CI/CD Pipeline, และแนวทางการ Deploy",
        "system_prompt": (
            "You are a Senior DevOps & Cloud Infrastructure Engineer. "
            "Design Dockerfile, CI/CD pipeline, environment configs, and deployment scripts for this application."
        ),
        "temperature": 0.4,
        "hdr_color": "#fb923c",  # Soft Orange
    },
    {
        "name": "Researcher",
        "icon": "🔬",
        "role_description": "ค้นคว้าข้อมูล เทคโนโลยี เปรียบเทียบ Best Practices",
        "system_prompt": (
            "You are a Deep Tech Researcher & Analyst. "
            "Investigate relevant libraries, frameworks, architectural trade-offs, and state-of-the-art solutions."
        ),
        "temperature": 0.5,
        "hdr_color": "#2dd4bf",  # Soft Teal
    },
    {
        "name": "Custom Agent",
        "icon": "🤖",
        "role_description": "สมาชิกผู้ช่วยในทีม AI กำหนดบทบาทตามต้องการ",
        "system_prompt": "You are a specialized AI assistant in the team. Follow user instructions and collaborate with your teammates.",
        "temperature": 0.6,
        "hdr_color": "#818cf8",  # Soft Indigo
    },
]


class TeamConfigDialog(tk.Toplevel):
    """Configuration Dialog for setting up Team Room agents."""

    def __init__(
        self,
        parent: tk.Misc,
        profiles: list[dict[str, Any]],
        agents: list[TeamAgentConfig],
        on_save: Callable[[list[TeamAgentConfig]], None],
    ) -> None:
        super().__init__(parent)
        self.title("⚙ ตั้งค่าทีม AI (Team Room Configuration)")
        self.geometry("920x700")
        self.minsize(820, 600)
        self.configure(bg=T["bg"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.profiles = profiles
        # Deep copy configs
        self.agents = [TeamAgentConfig.from_dict(a.to_dict()) for a in agents]
        self.on_save = on_save
        self._current_agent_idx = 0
        self._agent_tab_buttons: list[tk.Button] = []
        self._ignore_name_traces = False

        self._build_ui()
        self._render_tab_bar()
        self._load_agent_to_ui(0)

    def _build_ui(self) -> None:
        body = tk.Frame(self, bg=T["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(body, bg=T["bg"])
        header.pack(fill="x", pady=(0, 12))

        tk.Label(
            header,
            text="👥 ตั้งค่าสมาชิกในทีม AI",
            bg=T["bg"],
            fg=T["fg"],
            font=FONT_TITLE,
        ).pack(side="left")

        save_btn = tk.Button(
            header,
            text="💾 บันทึกการตั้งค่าทีม",
            command=self._on_save_clicked,
            bg=T["accent"],
            fg="#ffffff",
            activebackground=T["accent_hover"],
            activeforeground="#ffffff",
            relief="flat",
            font=FONT_BOLD,
            padx=16,
            pady=6,
            cursor="hand2",
        )
        save_btn.pack(side="right")

        # Top agent selector tabs (Scrollable / dynamic)
        tab_container = tk.Frame(body, bg=T["bg"])
        tab_container.pack(fill="x", pady=(0, 12))

        self._tab_bar = tk.Frame(tab_container, bg=T["bg"])
        self._tab_bar.pack(side="left", fill="x", expand=True)

        # Main agent editor card
        self._card = tk.Frame(
            body,
            bg=T["bg2"],
            padx=18,
            pady=14,
            highlightthickness=1,
            highlightbackground=T["border"],
        )
        self._card.pack(fill="both", expand=True)

        # 1. Enabled toggle & action buttons (Move Left, Move Right, Delete)
        top_row = tk.Frame(self._card, bg=T["bg2"])
        top_row.pack(fill="x", pady=(0, 10))

        self._enabled_var = tk.BooleanVar(value=True)
        self._enabled_cb = tk.Checkbutton(
            top_row,
            text="เปิดใช้งาน Agent บทบาทนี้ในทีม",
            variable=self._enabled_var,
            bg=T["bg2"],
            fg=T["fg"],
            selectcolor=T["bg2"],
            activebackground=T["bg2"],
            activeforeground=T["accent"],
            font=FONT_BOLD,
        )
        self._enabled_cb.pack(side="left")

        # Action bar: Move left/right, Delete
        action_bar = tk.Frame(top_row, bg=T["bg2"])
        action_bar.pack(side="right")

        self._btn_move_left = tk.Button(
            action_bar,
            text="◀ ลำดับก่อนหน้า",
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg"],
            activeforeground=T["fg"],
            font=FONT_TINY,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._move_current_agent(-1),
        )
        self._btn_move_left.pack(side="left", padx=(0, 4))

        self._btn_move_right = tk.Button(
            action_bar,
            text="ลำดับถัดไป ▶",
            bg=T["bg3"],
            fg=T["fg"],
            activebackground=T["bg"],
            activeforeground=T["fg"],
            font=FONT_TINY,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._move_current_agent(1),
        )
        self._btn_move_right.pack(side="left", padx=(0, 8))

        self._btn_delete = tk.Button(
            action_bar,
            text="🗑 ลบสมาชิกนี้",
            bg=T["bg3"],
            fg=T["err_hdr"],
            activebackground=T["err_hdr"],
            activeforeground="#ffffff",
            font=FONT_TINY,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._delete_current_agent,
        )
        self._btn_delete.pack(side="left")

        # 2. Member Name, Icon, and Role Description row
        row_identity = tk.Frame(self._card, bg=T["bg2"])
        row_identity.pack(fill="x", pady=(0, 10))

        tk.Label(row_identity, text="ไอคอน:", bg=T["bg2"], fg=T["fg"], font=FONT).pack(side="left", padx=(0, 6))
        self._icon_var = tk.StringVar(value="🤖")
        self._icon_box = ttk.Combobox(
            row_identity,
            textvariable=self._icon_var,
            values=["📋", "💻", "🔍", "🧪", "🛡️", "📝", "🚀", "🎨", "🔬", "🤖", "⚡", "📊", "💡"],
            width=4,
            font=FONT,
        )
        self._icon_box.pack(side="left", padx=(0, 14))
        self._icon_var.trace_add("write", lambda *_: self._on_identity_change())

        tk.Label(row_identity, text="ชื่อสมาชิก:", bg=T["bg2"], fg=T["fg"], font=FONT).pack(side="left", padx=(0, 6))
        self._name_var = tk.StringVar(value="Agent")
        self._name_entry = tk.Entry(
            row_identity,
            textvariable=self._name_var,
            bg=T["bg"],
            fg=T["fg"],
            insertbackground=T["fg"],
            font=FONT_BOLD,
            width=14,
            bd=1,
            relief="solid",
        )
        self._name_entry.pack(side="left", padx=(0, 14))
        self._name_var.trace_add("write", lambda *_: self._on_identity_change())

        tk.Label(row_identity, text="คำอธิบายบทบาท:", bg=T["bg2"], fg=T["fg"], font=FONT).pack(side="left", padx=(0, 6))
        self._desc_var = tk.StringVar()
        self._desc_entry = tk.Entry(
            row_identity,
            textvariable=self._desc_var,
            bg=T["bg"],
            fg=T["fg"],
            insertbackground=T["fg"],
            font=FONT,
            bd=1,
            relief="solid",
        )
        self._desc_entry.pack(side="left", fill="x", expand=True)

        # 3. Provider & Model row (Can choose same or different model freely)
        row2 = tk.Frame(self._card, bg=T["bg2"])
        row2.pack(fill="x", pady=(0, 10))

        tk.Label(row2, text="ผู้ให้บริการ (Provider):", bg=T["bg2"], fg=T["fg"], font=FONT).grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=4
        )
        self._prov_var = tk.StringVar()
        self._prov_box = ttk.Combobox(
            row2,
            textvariable=self._prov_var,
            values=[p["name"] for p in self.profiles],
            state="readonly",
            width=22,
            font=FONT,
        )
        self._prov_box.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=4)
        self._prov_var.trace_add("write", self._on_dialog_provider_change)

        tk.Label(row2, text="โมเดล (Model):", bg=T["bg2"], fg=T["fg"], font=FONT).grid(
            row=0, column=2, sticky="w", padx=(0, 10), pady=4
        )
        self._model_var = tk.StringVar()
        self._model_box = ttk.Combobox(
            row2,
            textvariable=self._model_var,
            state="readonly",
            width=26,
            font=FONT,
        )
        self._model_box.grid(row=0, column=3, sticky="w", pady=4)

        # 4. Temperature row
        row3 = tk.Frame(self._card, bg=T["bg2"])
        row3.pack(fill="x", pady=(0, 10))

        tk.Label(row3, text="ความสร้างสรรค์ (Temperature):", bg=T["bg2"], fg=T["fg"], font=FONT).pack(
            side="left", padx=(0, 10)
        )
        self._temp_var = tk.DoubleVar(value=0.7)
        self._temp_scale = tk.Scale(
            row3,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient="horizontal",
            variable=self._temp_var,
            bg=T["bg2"],
            fg=T["fg"],
            highlightthickness=0,
            length=180,
        )
        self._temp_scale.pack(side="left", padx=(0, 10))

        # 5. System Prompt editor
        tk.Label(
            self._card,
            text="คำสั่งระบบประจำบทบาท (System Prompt / Instructions):",
            bg=T["bg2"],
            fg=T["fg"],
            font=FONT_BOLD,
        ).pack(anchor="w", pady=(4, 4))

        prompt_box_frame = tk.Frame(self._card, bg=T["bg"], bd=1, relief="solid")
        prompt_box_frame.pack(fill="both", expand=True, pady=(0, 2))

        self._prompt_text = tk.Text(
            prompt_box_frame,
            bg=T["bg"],
            fg=T["fg"],
            insertbackground=T["fg"],
            font=FONT,
            wrap="word",
            bd=0,
            padx=10,
            pady=8,
        )
        self._prompt_text.pack(fill="both", expand=True)
        attach_text_context_menu(self._prompt_text, is_editable=True)

    def _render_tab_bar(self) -> None:
        """Render tab buttons for all agents and a + Add Member button."""
        for w in self._tab_bar.winfo_children():
            w.destroy()
        self._agent_tab_buttons.clear()

        for idx, agent in enumerate(self.agents):
            btn = tk.Button(
                self._tab_bar,
                text=f"{agent.icon} {agent.name}",
                bg=T["accent"] if idx == self._current_agent_idx else T["bg2"],
                fg="#ffffff" if idx == self._current_agent_idx else T["fg"],
                font=FONT_BOLD,
                relief="flat",
                padx=14,
                pady=5,
                cursor="hand2",
                command=lambda i=idx: self._switch_agent(i),
            )
            btn.pack(side="left", padx=(0, 6))
            self._agent_tab_buttons.append(btn)

        # "+ เพิ่มสมาชิก" button
        add_btn = tk.Button(
            self._tab_bar,
            text="＋ เพิ่มสมาชิก",
            bg=T["bg3"],
            fg=T["accent"],
            activebackground=T["accent"],
            activeforeground="#ffffff",
            font=FONT_BOLD,
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._show_add_agent_menu,
        )
        add_btn.pack(side="left", padx=(4, 0))

    def _show_add_agent_menu(self) -> None:
        """Display popup menu with agent presets or custom agent."""
        self._save_current_agent_from_ui()
        menu = tk.Menu(self, tearoff=False, bg=T["bg2"], fg=T["fg"], activebackground=T["accent"], font=FONT)
        for p in PRESET_TEMPLATES:
            menu.add_command(
                label=f"{p['icon']} {p['name']} — {p['role_description'][:32]}...",
                command=lambda preset=p: self._add_agent_from_preset(preset),
            )
        menu.add_separator()
        menu.add_command(
            label="🤖 สมาชิกใหม่แบบกำหนดเอง (Custom Agent)",
            command=lambda: self._add_agent_from_preset({
                "name": f"Agent {len(self.agents) + 1}",
                "icon": "🤖",
                "role_description": "บทบาทเสริมสำหรับทีม AI",
                "system_prompt": "You are a specialized AI assistant in the team. Follow user instructions and collaborate with teammates.",
                "temperature": 0.5,
                "hdr_color": "#818cf8",
            }),
        )

        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _add_agent_from_preset(self, preset: dict[str, Any]) -> None:
        """Instantiate new agent and switch to it."""
        num = 1
        existing_ids = {a.id for a in self.agents}
        base_id = preset["name"].lower().replace(" ", "_")
        new_id = base_id
        while new_id in existing_ids:
            num += 1
            new_id = f"{base_id}_{num}"

        # Inherit active provider & model (can share the exact same model or different models!)
        active_prof = self.profiles[0] if self.profiles else None
        cur_agent = self.agents[self._current_agent_idx] if self.agents else None
        prof_id = cur_agent.profile_id if cur_agent and cur_agent.profile_id else (active_prof["id"] if active_prof else "")
        prof_name = cur_agent.profile_name if cur_agent and cur_agent.profile_name else (active_prof["name"] if active_prof else "")
        model = cur_agent.model if cur_agent and cur_agent.model else (active_prof["model"] if active_prof else "")

        new_agent = TeamAgentConfig(
            id=new_id,
            name=preset["name"],
            icon=preset["icon"],
            role_description=preset["role_description"],
            enabled=True,
            profile_id=prof_id,
            profile_name=prof_name,
            model=model,
            system_prompt=preset["system_prompt"],
            temperature=preset.get("temperature", 0.6),
            hdr_color=preset.get("hdr_color", "#818cf8"),
        )
        self.agents.append(new_agent)
        new_idx = len(self.agents) - 1
        self._render_tab_bar()
        self._switch_agent(new_idx)

    def _delete_current_agent(self) -> None:
        """Remove currently selected agent if team has >1 members."""
        if len(self.agents) <= 1:
            messagebox.showwarning("คำเตือน", "ไม่สามารถลบสมาชิกได้ ทีมต้องมีสมาชิกอย่างน้อย 1 คน", parent=self)
            return

        del self.agents[self._current_agent_idx]
        if self._current_agent_idx >= len(self.agents):
            self._current_agent_idx = len(self.agents) - 1

        self._render_tab_bar()
        self._load_agent_to_ui(self._current_agent_idx)

    def _move_current_agent(self, direction: int) -> None:
        """Reorder agents: direction -1 for left/earlier, +1 for right/later."""
        new_idx = self._current_agent_idx + direction
        if 0 <= new_idx < len(self.agents):
            self._save_current_agent_from_ui()
            self.agents[self._current_agent_idx], self.agents[new_idx] = (
                self.agents[new_idx],
                self.agents[self._current_agent_idx],
            )
            self._current_agent_idx = new_idx
            self._render_tab_bar()
            self._load_agent_to_ui(new_idx)

    def _on_identity_change(self) -> None:
        """Update active tab button label when name or icon is changed in entry."""
        if self._ignore_name_traces:
            return
        if 0 <= self._current_agent_idx < len(self._agent_tab_buttons):
            name = self._name_var.get().strip() or "Agent"
            icon = self._icon_var.get().strip() or "🤖"
            btn = self._agent_tab_buttons[self._current_agent_idx]
            btn.configure(text=f"{icon} {name}")

    def _save_current_agent_from_ui(self) -> None:
        if 0 <= self._current_agent_idx < len(self.agents):
            agent = self.agents[self._current_agent_idx]
            agent.name = self._name_var.get().strip() or agent.name
            agent.icon = self._icon_var.get().strip() or agent.icon
            agent.role_description = self._desc_var.get().strip()
            agent.enabled = self._enabled_var.get()
            prov_name = self._prov_var.get()
            prof = next((p for p in self.profiles if p["name"] == prov_name), None)
            if prof:
                agent.profile_id = prof["id"]
                agent.profile_name = prof["name"]
            agent.model = self._model_var.get()
            agent.temperature = float(self._temp_var.get())
            agent.system_prompt = self._prompt_text.get("1.0", "end-1c").strip()

    def _load_agent_to_ui(self, idx: int) -> None:
        if not (0 <= idx < len(self.agents)):
            return
        self._current_agent_idx = idx
        agent = self.agents[idx]

        self._ignore_name_traces = True
        try:
            self._name_var.set(agent.name)
            self._icon_var.set(agent.icon)
            self._desc_var.set(agent.role_description)
        finally:
            self._ignore_name_traces = False

        # Update tab button styles
        for i, btn in enumerate(self._agent_tab_buttons):
            if i == idx:
                btn.configure(bg=T["accent"], fg="#ffffff")
            else:
                btn.configure(bg=T["bg2"], fg=T["fg"])

        self._enabled_var.set(agent.enabled)

        # Update button states
        self._btn_move_left.configure(state="normal" if idx > 0 else "disabled")
        self._btn_move_right.configure(state="normal" if idx < len(self.agents) - 1 else "disabled")
        self._btn_delete.configure(state="normal" if len(self.agents) > 1 else "disabled")

        # Profile selection
        current_prof = next((p for p in self.profiles if p["id"] == agent.profile_id), None)
        if not current_prof:
            current_prof = self.profiles[0] if self.profiles else None

        if current_prof:
            self._prov_var.set(current_prof["name"])
            self._model_box.configure(values=current_prof["models"])
            if agent.model and agent.model in current_prof["models"]:
                self._model_var.set(agent.model)
            else:
                self._model_var.set(current_prof["model"])

        self._temp_var.set(agent.temperature)
        self._prompt_text.delete("1.0", "end")
        self._prompt_text.insert("1.0", agent.system_prompt)

    def _switch_agent(self, new_idx: int) -> None:
        if new_idx == self._current_agent_idx:
            return
        self._save_current_agent_from_ui()
        self._load_agent_to_ui(new_idx)

    def _on_dialog_provider_change(self, *_: object) -> None:
        name = self._prov_var.get()
        prof = next((p for p in self.profiles if p["name"] == name), None)
        if prof:
            self._model_box.configure(values=prof["models"])
            self._model_var.set(prof["model"])

    def _on_save_clicked(self) -> None:
        self._save_current_agent_from_ui()
        enabled_count = sum(1 for a in self.agents if a.enabled)
        if enabled_count == 0:
            messagebox.showwarning("คำเตือน", "กรุณาเปิดใช้งานอย่างน้อย 1 Agent ในทีม", parent=self)
            return

        if self.on_save:
            self.on_save(self.agents)
        self.destroy()
