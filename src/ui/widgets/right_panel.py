from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from src.ui.session_registry import SessionRegistry


class RightPanel(ttk.Frame):
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
        header = ttk.Label(self, text="Janelas", font=("", 9, "bold"))
        header.pack(anchor="w", pady=(0, 4))

        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self._listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=10,
            exportselection=False,
        )
        self._listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._listbox.yview)

        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        self._action_btn = ttk.Button(
            self,
            text="Start",
            state="disabled",
            command=self._on_action,
        )
        self._action_btn.pack(fill="x", pady=(8, 0))

        self._hint_label = ttk.Label(self, text="Selecione uma janela")
        self._hint_label.pack(pady=(4, 0))

        self._refresh()

    def _schedule_refresh(self):
        self.after(0, self._refresh)

    def _refresh(self):
        sessions = SessionRegistry.get_all()
        current_selection = self._selected_label

        self._listbox.delete(0, "end")

        for label in sorted(sessions.keys()):
            self._listbox.insert("end", label)

        if current_selection and current_selection in sessions:
            idx = sorted(sessions.keys()).index(current_selection)
            self._listbox.selection_set(idx)
        elif sessions:
            self._listbox.selection_set(0)
            first = sorted(sessions.keys())[0]
            self._select(first)

        if not sessions:
            self._selected_label = None
            self._running = False
            self._action_btn.configure(state="disabled", text="Start")
            self._hint_label.configure(text="Selecione uma janela")

    def _on_select(self, event):
        selection = self._listbox.curselection()
        if selection:
            label = self._listbox.get(selection[0])
            self._select(label)

    def _select(self, label: str):
        self._selected_label = label
        self._action_btn.configure(state="normal")
        self._update_action_button()
        self._hint_label.configure(text=f"Janela: {label}")
        if self._on_select_callback:
            self._on_select_callback(label)

    def _on_action(self):
        if self._selected_label is None:
            return
        self._running = not self._running
        self._update_action_button()
        if self._on_action_callback:
            self._on_action_callback(self._selected_label)

    def _update_action_button(self):
        if self._running:
            self._action_btn.configure(text="Stop")
        else:
            self._action_btn.configure(text="Start")

    @property
    def selected_label(self) -> str | None:
        return self._selected_label

    @property
    def running(self) -> bool:
        return self._running
