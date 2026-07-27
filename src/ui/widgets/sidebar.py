from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class Sidebar(ttk.Frame):
    """
    Painel de navegacao esquerdo com os modulos do bot.
    """

    ITEMS = [
        ("Home", None),
        ("Attack", None),
        ("Potion", None),
        ("Pet Food", None),
        ("Buff", None),
        ("Helper", None),
        ("Fairy", None),
        ("Revive", None),
        ("Delete", None),
        ("BC", None),
        ("Hollow", None),
        ("---", None),
        ("Sell", None),
        ("DR Lure", None),
        ("Key", None),
    ]

    def __init__(
        self,
        parent,
        on_select: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self._on_select = on_select
        self._buttons: dict[str, ttk.Button] = {}
        self._selected: str | None = None

        self._build()

    def _build(self):
        for label, _icon in self.ITEMS:

            if label == "---":
                ttk.Separator(self, orient="horizontal").pack(
                    fill="x", pady=4, padx=8
                )
                continue

            btn = ttk.Button(
                self,
                text=label,
                command=lambda l=label: self._select(l),
            )
            btn.pack(fill="x", padx=4, pady=1)
            self._buttons[label] = btn

        self._select("Home")

    def _select(self, label: str):
        if self._selected:
            prev = self._buttons.get(self._selected)
            if prev:
                prev.configure(style="")
        self._selected = label
        curr = self._buttons.get(label)
        if curr:
            curr.configure(style="Accent.TButton")
        self._on_select(label)

    @property
    def selected(self) -> str | None:
        return self._selected
