from __future__ import annotations

import customtkinter as ctk
from typing import Callable


class Sidebar(ctk.CTkFrame):
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
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._selected: str | None = None

        self._build()

    def _build(self):
        for label, _icon in self.ITEMS:

            if label == "---":
                sep = ctk.CTkFrame(self, height=2, fg_color="#555555")
                sep.pack(fill="x", padx=8, pady=6)
                continue

            btn = ctk.CTkButton(
                self,
                text=label,
                command=lambda l=label: self._select(l),
                fg_color="transparent",
                hover_color="#3a3a3a",
                anchor="w",
                corner_radius=4,
                height=26,
                font=ctk.CTkFont(size=11),
            )
            btn.pack(fill="x", padx=2, pady=1)
            self._buttons[label] = btn

        self._select("Home")

    def _select(self, label: str):
        if self._selected:
            prev = self._buttons.get(self._selected)
            if prev:
                prev.configure(fg_color="transparent")

        self._selected = label
        curr = self._buttons.get(label)
        if curr:
            curr.configure(fg_color="#1a5c2a", hover_color="#1e6e32")

        self._on_select(label)

    @property
    def selected(self) -> str | None:
        return self._selected
