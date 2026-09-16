"""
src/ui/dialogs/team_config_dialog.py — Dialog for configuring Multi-Agent Team Room members.
Allows configuring Provider, Model, System Prompt, and parameters for each agent role.
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
        self.geometry("860x650")
        self.minsize(780, 560)
        self.configure(bg=T["bg"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.profiles = profiles
        # Deep copy configs
        self.agents = [TeamAgentConfig.from_dict(a.to_dict()) for a in agents]
        self.on_save = on_save
        self._current_agent_idx = 0

        self._build_ui()
        self._load_agent_to_ui(0)

    def _build_ui(self) -> None:
        body = tk.Frame(self, bg=T["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(body, bg=T["bg"])
        header.pack(fill="x", pady=(0, 14))

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

        # Top agent selector tabs
        self._tab_bar = tk.Frame(body, bg=T["bg"])
        self._tab_bar.pack(fill="x", pady=(0, 14))
        self._agent_tab_buttons: list[tk.Button] = []

        for idx, agent in enumerate(self.agents):
            btn = tk.Button(
                self._tab_bar,
                text=f"{agent.icon} {agent.name}",
                bg=T["bg2"],
                fg=T["fg"],
                font=FONT_BOLD,
                relief="flat",
                padx=16,
                pady=6,
                cursor="hand2",
                command=lambda i=idx: self._switch_agent(i),
            )
            btn.pack(side="left", padx=(0, 8))
            self._agent_tab_buttons.append(btn)

        # Main agent editor card
        self._card = tk.Frame(
            body,
            bg=T["bg2"],
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground=T["border"],
        )
        self._card.pack(fill="both", expand=True)

        # 1. Enabled toggle & description
        top_row = tk.Frame(self._card, bg=T["bg2"])
        top_row.pack(fill="x", pady=(0, 12))

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

        self._desc_lbl = tk.Label(
            top_row,
            text="",
            bg=T["bg2"],
            fg=T["fg_dim"],
            font=FONT_TINY,
        )
        self._desc_lbl.pack(side="right")

        # 2. Provider & Model row
        row2 = tk.Frame(self._card, bg=T["bg2"])
        row2.pack(fill="x", pady=(0, 12))

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
            width=24,
            font=FONT,
        )
        self._model_box.grid(row=0, column=3, sticky="w", pady=4)

        # 3. Temperature row
        row3 = tk.Frame(self._card, bg=T["bg2"])
        row3.pack(fill="x", pady=(0, 12))

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

        # 4. System Prompt editor
        tk.Label(
            self._card,
            text="คำสั่งระบบประจำบทบาท (System Prompt / Instructions):",
            bg=T["bg2"],
            fg=T["fg"],
            font=FONT_BOLD,
        ).pack(anchor="w", pady=(6, 4))

        prompt_box_frame = tk.Frame(self._card, bg=T["bg"], bd=1, relief="solid")
        prompt_box_frame.pack(fill="both", expand=True, pady=(0, 4))

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

    def _save_current_agent_from_ui(self) -> None:
        if 0 <= self._current_agent_idx < len(self.agents):
            agent = self.agents[self._current_agent_idx]
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

        # Update tab button styles
        for i, btn in enumerate(self._agent_tab_buttons):
            if i == idx:
                btn.configure(bg=T["accent"], fg="#ffffff")
            else:
                btn.configure(bg=T["bg2"], fg=T["fg"])

        self._enabled_var.set(agent.enabled)
        self._desc_lbl.configure(text=agent.role_description)

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
