from __future__ import annotations

import customtkinter as ctk
from typing import Callable

from src.ui.session_registry import SessionRegistry


class RightPanel(ctk.CTkFrame):

    def __init__(self, parent, on_select=None, on_action=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._on_select_callback = on_select
        self._on_action_callback = on_action
        self._selected_label: str | None = None
        self._running = False
        self._build()
        SessionRegistry.observe(self._schedule_refresh)

    def _build(self):
        ctk.CTkLabel(self, text="Characters", font=ctk.CTkFont(weight="bold")).pack(anchor="center", pady=(0, 4))

        # Lista de chars
        list_frame = ctk.CTkFrame(self, fg_color="transparent")
        list_frame.pack(fill="both", expand=True)

        import tkinter as tk
        scrollbar = ctk.CTkScrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self._listbox = tk.Listbox(
            list_frame, yscrollcommand=scrollbar.set, height=8,
            exportselection=False, bg="#2b2b2b", fg="#dcdcdc",
            selectbackground="#1a5c2a", selectforeground="#ffffff",
            borderwidth=0, highlightthickness=0,
        )
        self._listbox.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self._listbox.yview)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        self._listbox.bind("<Double-Button-1>", self._on_double_click)

        # HUD do personagem selecionado
        self._hud = ctk.CTkFrame(self, corner_radius=8, border_width=1, border_color="#333")
        self._hud.pack(fill="x", pady=(8, 4), padx=2)

        self._face_label = ctk.CTkLabel(self._hud, text="?", font=ctk.CTkFont(size=28), width=50)
        self._face_label.pack(pady=(8, 2))

        self._hud_name = ctk.CTkLabel(self._hud, text="--", font=ctk.CTkFont(weight="bold"))
        self._hud_name.pack()

        self._hud_level = ctk.CTkLabel(self._hud, text="Lv --", font=ctk.CTkFont(size=11), text_color="#888")
        self._hud_level.pack()

        hp_row = ctk.CTkFrame(self._hud, fg_color="transparent")
        hp_row.pack(fill="x", padx=8, pady=(6, 0))
        ctk.CTkLabel(hp_row, text="HP", width=20, font=ctk.CTkFont(size=10)).pack(side="left")
        self._hud_hp_bar = ctk.CTkProgressBar(hp_row, width=100, height=8, progress_color="#22aa22")
        self._hud_hp_bar.pack(side="left", padx=4)
        self._hud_hp_bar.set(0)

        res_row = ctk.CTkFrame(self._hud, fg_color="transparent")
        res_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(res_row, text="MP", width=20, font=ctk.CTkFont(size=10)).pack(side="left")
        self._hud_res_bar = ctk.CTkProgressBar(res_row, width=100, height=8, progress_color="#4488cc")
        self._hud_res_bar.pack(side="left", padx=4)
        self._hud_res_bar.set(0)

        # Start/Stop
        self._action_btn = ctk.CTkButton(self, text="Start", state="disabled",
                                          command=self._on_action, height=30)
        self._action_btn.pack(fill="x", pady=(6, 0))

        self._refresh()

    def update_hud(self, name="--", level=0, hp_pct=0.0, res_pct=0.0, profession=""):
        self._hud_name.configure(text=name or "--")
        self._hud_level.configure(text=f"Lv {level}" if level else "Lv --")
        self._hud_hp_bar.set(hp_pct / 100.0)
        self._hud_res_bar.set(res_pct / 100.0)
        # Face por profissao
        faces = {"Monk": "\U0001F94B", "Wizard": "\U0001F9D9", "Assassin": "\U0001F977",
                 "Tamer": "\U0001F9D8", "Fairy": "\U0001F9DA"}
        self._face_label.configure(text=faces.get(profession, "?"))

    def _schedule_refresh(self):
        self.after(0, self._refresh)

    def _refresh(self):
        sessions = SessionRegistry.get_all()
        current = self._selected_label
        self._listbox.delete(0, "end")
        for label, info in sorted(sessions.items()):
            self._listbox.insert("end", info.get("display", label))
        if current and current in sessions:
            for idx, (label, _) in enumerate(sorted(sessions.items())):
                if label == current:
                    self._listbox.selection_set(idx); break
        elif sessions:
            self._listbox.selection_set(0)
            self._select(sorted(sessions.keys())[0])
        if not sessions:
            self._selected_label = None; self._running = False
            self._action_btn.configure(state="disabled", text="Start")

    def _on_select(self, event):
        sel = self._listbox.curselection()
        if sel:
            display = self._listbox.get(sel[0])
            sessions = SessionRegistry.get_all()
            for label, info in sessions.items():
                if info.get("display", label) == display:
                    self._select(label); return

    def _select(self, label: str):
        self._selected_label = label
        self._action_btn.configure(state="normal")
        self._update_action_btn()
        if self._on_select_callback:
            self._on_select_callback(label)

    def _on_action(self):
        if not self._selected_label: return
        self._running = not self._running
        self._update_action_btn()
        if self._on_action_callback:
            self._on_action_callback(self._selected_label)

    def _update_action_btn(self):
        if self._running:
            self._action_btn.configure(text="Stop", fg_color="#8b0000", hover_color="#a00000")
        else:
            self._action_btn.configure(text="Start", fg_color="#2a8c3d", hover_color="#236e30")

    def _on_double_click(self, event):
        sel = self._listbox.curselection()
        if sel:
            display = self._listbox.get(sel[0])
            sessions = SessionRegistry.get_all()
            for label, info in sessions.items():
                if info.get("display", label) == display:
                    hwnd = info.get("hwnd")
                    if hwnd:
                        import win32gui
                        try: win32gui.SetForegroundWindow(hwnd)
                        except: pass
                    return

    @property
    def selected_label(self) -> str | None:
        return self._selected_label

    @property
    def running(self) -> bool:
        return self._running
