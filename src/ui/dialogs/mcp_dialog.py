"""
mcp_dialog.py — Dialog for configuring Model Context Protocol (MCP) servers & tools.
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from typing import Any, Optional

from src.core.mcp_manager import MCPManager
from src.ui.themes import T, FONT, FONT_BOLD, FONT_TINY, FONT_TITLE


class MCPManagerDialog(tk.Toplevel):
    """Dialog for configuring and managing Model Context Protocol (MCP) servers & tools."""

    def __init__(self, parent: tk.Misc, manager: MCPManager,
                 on_update: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._on_update = on_update
        self.title("Model Context Protocol (MCP) Tools")
        self.geometry("780x560")
        self.minsize(700, 480)
        self.configure(bg=T["bg"])
        self.transient(parent.winfo_toplevel())

        body = tk.Frame(self, bg=T["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        header = tk.Frame(body, bg=T["bg"])
        header.pack(fill="x")
        tk.Label(header, text="MCP Tools & Servers", bg=T["bg"], fg=T["fg"],
                 font=FONT_TITLE).pack(side="left")

        self._enabled_var = tk.BooleanVar(value=self.manager.enabled)
        chk = tk.Checkbutton(
            header, text="เปิดใช้งาน Tool Calling", variable=self._enabled_var,
            command=self._toggle_enabled, bg=T["bg"], fg=T["fg"],
            activebackground=T["bg"], activeforeground=T["fg"],
            selectcolor=T["bg3"], font=FONT_BOLD, cursor="hand2"
        )
        chk.pack(side="right")

        tk.Label(
            body,
            text="เชื่อมต่อ MCP Servers เพื่อให้ AI เรียกใช้เครื่องมือภายนอก (stdio JSON-RPC) หรือใช้ Built-in Tools",
            bg=T["bg"], fg=T["fg_dim"], font=FONT_TINY
        ).pack(anchor="w", pady=(2, 12))

        nb = ttk.Notebook(body)
        nb.pack(fill="both", expand=True)

        # Tab 1: Tools list
        tools_tab = tk.Frame(nb, bg=T["bg2"], padx=12, pady=12)
        nb.add(tools_tab, text="🛠 รายการเครื่องมือ (Tools)")

        self._tools_text = tk.Text(
            tools_tab, bg=T["bg2"], fg=T["fg"], relief="flat", bd=0,
            font=FONT, padx=8, pady=8, state="disabled"
        )
        tools_sb = ttk.Scrollbar(tools_tab, orient="vertical", command=self._tools_text.yview)
        self._tools_text.configure(yscrollcommand=tools_sb.set)
        tools_sb.pack(side="right", fill="y")
        self._tools_text.pack(fill="both", expand=True)

        # Tab 2: Servers list & editor
        servers_tab = tk.Frame(nb, bg=T["bg2"], padx=12, pady=12)
        nb.add(servers_tab, text="🌐 เซิร์ฟเวอร์ MCP (Servers)")

        srv_top = tk.Frame(servers_tab, bg=T["bg2"])
        srv_top.pack(fill="x", pady=(0, 8))

        self._srv_listbox = tk.Listbox(
            srv_top, height=5, bg=T["bg"], fg=T["fg"], font=FONT,
            selectbackground=T["accent"], relief="flat", highlightbackground=T["border"]
        )
        self._srv_listbox.pack(side="left", fill="both", expand=True)
        self._srv_listbox.bind("<<ListboxSelect>>", self._on_select_server)

        srv_btns = tk.Frame(srv_top, bg=T["bg2"])
        srv_btns.pack(side="right", fill="y", padx=(8, 0))

        tk.Button(srv_btns, text="＋ เพิ่ม", command=self._add_server_prompt,
                  bg=T["bg_btn"], fg=T["fg"], font=FONT, relief="flat",
                  padx=10, pady=4, cursor="hand2").pack(fill="x", pady=(0, 4))
        tk.Button(srv_btns, text="− ลบ", command=self._delete_server,
                  bg=T["bg_btn"], fg=T["err_hdr"], font=FONT, relief="flat",
                  padx=10, pady=4, cursor="hand2").pack(fill="x", pady=(0, 4))
        tk.Button(srv_btns, text="⚡ เชื่อมต่อ", command=self._connect_selected,
                  bg=T["accent"], fg="#fff", font=FONT, relief="flat",
                  padx=10, pady=4, cursor="hand2").pack(fill="x")

        form = tk.Frame(servers_tab, bg=T["bg2"])
        form.pack(fill="x", pady=(6, 0))

        self._srv_name_var = tk.StringVar()
        self._srv_cmd_var = tk.StringVar()
        self._srv_args_var = tk.StringVar()

        tk.Label(form, text="ชื่อ Server", bg=T["bg2"], fg=T["fg_dim"], font=FONT_TINY).grid(row=0, column=0, sticky="w", pady=2)
        tk.Entry(form, textvariable=self._srv_name_var, bg=T["bg"], fg=T["fg"], font=FONT, relief="flat").grid(row=0, column=1, sticky="ew", padx=6, pady=2)

        tk.Label(form, text="คำสั่ง (Command)", bg=T["bg2"], fg=T["fg_dim"], font=FONT_TINY).grid(row=1, column=0, sticky="w", pady=2)
        tk.Entry(form, textvariable=self._srv_cmd_var, bg=T["bg"], fg=T["fg"], font=FONT, relief="flat").grid(row=1, column=1, sticky="ew", padx=6, pady=2)

        tk.Label(form, text="พารามิเตอร์ (Args)", bg=T["bg2"], fg=T["fg_dim"], font=FONT_TINY).grid(row=2, column=0, sticky="w", pady=2)
        tk.Entry(form, textvariable=self._srv_args_var, bg=T["bg"], fg=T["fg"], font=FONT, relief="flat").grid(row=2, column=1, sticky="ew", padx=6, pady=2)

        form.columnconfigure(1, weight=1)

        tk.Button(form, text="💾 บันทึกการแก้ไขเซิร์ฟเวอร์", command=self._save_server_edit,
                  bg=T["bg_btn"], fg=T["fg"], font=FONT, relief="flat", padx=12, pady=5, cursor="hand2").grid(row=3, column=1, sticky="e", pady=(8, 0))

        footer = tk.Frame(body, bg=T["bg"])
        footer.pack(fill="x", pady=(12, 0))
        self._status_var = tk.StringVar(value="")
        tk.Label(footer, textvariable=self._status_var, bg=T["bg"], fg=T["ai_hdr"], font=FONT_TINY).pack(side="left")
        tk.Button(footer, text="ปิด", command=self.destroy, bg=T["bg_btn"], fg=T["fg"],
                  font=FONT, padx=14, pady=6, relief="flat", cursor="hand2").pack(side="right")

        self.bind("<Escape>", lambda _e: self.destroy())
        self._refresh()

    def _toggle_enabled(self) -> None:
        self.manager.enabled = self._enabled_var.get()
        if self._on_update:
            self._on_update()
        self._refresh()

    def _refresh(self) -> None:
        tools = self.manager.get_all_tools()
        self._tools_text.configure(state="normal")
        self._tools_text.delete("1.0", tk.END)
        self._tools_text.insert(tk.END, f"สถานะ Tool Calling: {'🟢 เปิดใช้งาน' if self.manager.enabled else '⚪ ปิดใช้งาน'}\n")
        self._tools_text.insert(tk.END, f"จำนวนเครื่องมือทั้งหมด: {len(tools)} เครื่องมือ\n\n")

        for t in tools:
            prefix = "[Built-in]" if t.server_name == "builtin" else f"[{t.server_name}]"
            self._tools_text.insert(tk.END, f"• {t.name} {prefix}\n")
            self._tools_text.insert(tk.END, f"   คำอธิบาย: {t.description or '-'}\n")
            props = t.input_schema.get("properties", {})
            if props:
                param_strs = [f"{k} ({v.get('type', 'any')})" for k, v in props.items()]
                self._tools_text.insert(tk.END, f"   พารามิเตอร์: {', '.join(param_strs)}\n")
            self._tools_text.insert(tk.END, "\n")
        self._tools_text.configure(state="disabled")

        self._srv_listbox.delete(0, tk.END)
        servers = self.manager.server_configs.get("servers", {})
        for name in servers:
            conn = self.manager.servers.get(name)
            status = "🟢 เชื่อมต่อแล้ว" if (conn and conn.is_connected) else "⚪ ออฟไลน์"
            self._srv_listbox.insert(tk.END, f"{name} ({status})")

    def _on_select_server(self, _e: object = None) -> None:
        sel = self._srv_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        servers = list(self.manager.server_configs.get("servers", {}).keys())
        if idx < len(servers):
            name = servers[idx]
            cfg = self.manager.server_configs["servers"][name]
            self._srv_name_var.set(name)
            self._srv_cmd_var.set(cfg.get("command", ""))
            args = cfg.get("args", [])
            self._srv_args_var.set(" ".join(args) if isinstance(args, list) else str(args))

    def _add_server_prompt(self) -> None:
        name = simpledialog.askstring("เพิ่ม MCP Server", "ระบุชื่อ Server (เช่น my_server):", parent=self)
        if not name:
            return
        self.manager.add_server(name.strip(), "python", ["-m", "mcp_server_module"])
        self._refresh()
        self._status_var.set(f"เพิ่ม Server '{name}' แล้ว")

    def _delete_server(self) -> None:
        sel = self._srv_listbox.curselection()
        if not sel:
            return
        servers = list(self.manager.server_configs.get("servers", {}).keys())
        name = servers[sel[0]]
        if messagebox.askyesno("ยืนยันการลบ", f"ต้องการลบเซิร์ฟเวอร์ '{name}' หรือไม่?", parent=self):
            self.manager.remove_server(name)
            self._refresh()
            self._status_var.set(f"ลบ Server '{name}' แล้ว")

    def _save_server_edit(self) -> None:
        name = self._srv_name_var.get().strip()
        cmd = self._srv_cmd_var.get().strip()
        args = [a.strip() for a in self._srv_args_var.get().split() if a.strip()]
        if not name or not cmd:
            self._status_var.set("กรุณากรอกชื่อและคำสั่งให้ครบถ้วน")
            return
        self.manager.add_server(name, cmd, args)
        self._refresh()
        self._status_var.set(f"บันทึกการตั้งค่า '{name}' แล้ว")

    def _connect_selected(self) -> None:
        sel = self._srv_listbox.curselection()
        if not sel:
            self._status_var.set("กรุณาเลือก Server จากรายการก่อน")
            return
        servers = list(self.manager.server_configs.get("servers", {}).keys())
        name = servers[sel[0]]
        self._status_var.set(f"กำลังเชื่อมต่อไปยัง {name}...")
        self.update_idletasks()
        ok = self.manager.connect_server(name)
        if ok:
            self._status_var.set(f"เชื่อมต่อกับ '{name}' สำเร็จ ✓")
        else:
            conn = self.manager.servers.get(name)
            err = conn.error_message if conn else "Failed to start"
            self._status_var.set(f"เชื่อมต่อไม่สำเร็จ: {err}")
        self._refresh()
        if self._on_update:
            self._on_update()
