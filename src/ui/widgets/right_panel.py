from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
from typing import Callable

from src.ui.session_registry import SessionRegistry


class RightPanel(ctk.CTkFrame):
    """
    Painel direito: lista de janelas do jogo abertas + Start/Stop.
    """

    def __init__(
        self,
        parent,
        on_select: Callable[[str], None] | None = None,
        on_action: Callable[[str], None] | None = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self._selected_label: str | None = None
        self._running: bool = False
        self._on_select_callback = on_select
        self._on_action_callback = on_action

        self._build()

        SessionRegistry.observe(self._schedule_refresh)

    def _build(self):
        ctk.CTkLabel(
            self, text="Characters",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="center", pady=(0, 4))

        list_frame = ctk.CTkFrame(self, fg_color="transparent")
        list_frame.pack(fill="both", expand=True)

        scrollbar = ctk.CTkScrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self._listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=10,
            exportselection=False,
            bg="#2b2b2b",
            fg="#dcdcdc",
            selectbackground="#1a5c2a",
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=0,
        )
        self._listbox.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self._listbox.yview)

        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        self._listbox.bind("<Double-Button-1>", self._on_double_click)

        self._action_btn = ctk.CTkButton(
            self,
            text="Start",
            state="disabled",
            command=self._on_action,
            height=30,
        )
        self._action_btn.pack(fill="x", pady=(8, 0))

        self._hint_label = ctk.CTkLabel(
            self,
            text="Selecione um character",
            text_color="#888888",
        )
        self._hint_label.pack(pady=(4, 0))

        self._refresh()

    def _schedule_refresh(self):
        self.after(0, self._refresh)

    def _refresh(self):
        sessions = SessionRegistry.get_all()
        current_selection = self._selected_label

        self._listbox.delete(0, "end")

        for label, info in sorted(sessions.items()):
            self._listbox.insert("end", info.get("display", label))

        if current_selection and current_selection in sessions:
            # Encontra pelo display
            for idx, (label, info) in enumerate(sorted(sessions.items())):
                if label == current_selection:
                    self._listbox.selection_set(idx)
                    break
        elif sessions:
            self._listbox.selection_set(0)
            first_label = sorted(sessions.keys())[0]
            self._select(first_label)

        if not sessions:
            self._selected_label = None
            self._running = False
            self._action_btn.configure(state="disabled", text="Start")
            self._hint_label.configure(text="Selecione um character")

    def _on_select(self, event):
        selection = self._listbox.curselection()
        if selection:
            display = self._listbox.get(selection[0])
            # Encontra a chave da sessao pelo display
            sessions = SessionRegistry.get_all()
            for label, info in sessions.items():
                if info.get("display", label) == display:
                    self._select(label)
                    return

    def _select(self, label: str):
        self._selected_label = label
        self._action_btn.configure(state="normal")
        self._update_action_button()
        sessions = SessionRegistry.get_all()
        display = sessions.get(label, {}).get("display", label)
        self._hint_label.configure(text=f"Character: {display}")
        if self._on_select_callback:
            self._on_select_callback(label)

    def _on_action(self):
        if self._selected_label is None:
            return
        self._running = not self._running
        self._update_action_button()
        if self._on_action_callback:
            self._on_action_callback(self._selected_label)

    def _on_double_click(self, event):
        """Duplo clique: foca a janela do jogo."""
        selection = self._listbox.curselection()
        if not selection:
            return
        display = self._listbox.get(selection[0])
        sessions = SessionRegistry.get_all()
        for label, info in sessions.items():
            if info.get("display", label) == display:
                hwnd = info.get("hwnd")
                if hwnd:
                    import win32gui
                    try:
                        win32gui.SetForegroundWindow(hwnd)
                    except Exception:
                        pass
                return

    def _update_action_button(self):
        if self._running:
            self._action_btn.configure(text="Stop", fg_color="#8b0000", hover_color="#a00000")
        else:
            self._action_btn.configure(text="Start", fg_color="#1a5c2a", hover_color="#1e6e32")

    @property
    def selected_label(self) -> str | None:
        return self._selected_label

    @property
    def running(self) -> bool:
        return self._running
