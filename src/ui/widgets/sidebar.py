from __future__ import annotations

import customtkinter as ctk
from typing import Callable


class Sidebar(ctk.CTkFrame):

    ITEMS = [
        ("Home", "\u2302"),
        ("Attack", "\u2694"),
        ("Potion", "\u2697"),
        ("Pet", "\u2665"),
        ("Buff", "\u21E7"),
        ("Helper", "\u2699"),
        ("Fairy", "\u2726"),
        ("Revive", "\u2715"),
        ("Delete", "\u2717"),
        ("BC", "\u25C6"),
        ("Hollow", "\u25CE"),
        ("---", None),
        ("Sell", "\u25C8"),
        ("DR Lure", "\u25C9"),
        ("Key", "\u26BF"),
    ]

    def __init__(self, parent, on_select: Callable[[str], None], **kwargs):
        super().__init__(parent, **kwargs)
        self._font = ctk.CTkFont(family="Segoe UI", size=16)
        self._icon_font = ctk.CTkFont(family="Segoe UI", size=16)
        self._on_select = on_select
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._icon_labels: dict[str, ctk.CTkLabel] = {}
        self._selected: str | None = None
        self._build()

    def _build(self):
        for label, icon in self.ITEMS:
            if label == "---":
                ctk.CTkFrame(self, height=2, fg_color="#555555").pack(
                    fill="x", padx=8, pady=6
                )
                continue

            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=2, pady=1)
            row.grid_columnconfigure(0, minsize=28)
            row.grid_columnconfigure(1, weight=1)

            icon_lbl = ctk.CTkLabel(
                row, text=icon or "",
                font=self._font, width=28, anchor="center",
            )
            icon_lbl.grid(row=0, column=0, padx=(4, 0))
            self._icon_labels[label] = icon_lbl

            btn = ctk.CTkButton(
                row, text=label,
                command=lambda l=label: self._select(l),
                fg_color="transparent", hover_color="#3a3a3a",
                anchor="w", corner_radius=4, height=36,
                font=self._font,
            )
            btn.grid(row=0, column=1, sticky="ew", padx=(0, 4))
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
