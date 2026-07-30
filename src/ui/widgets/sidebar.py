from __future__ import annotations

import customtkinter as ctk
from typing import Callable


class Sidebar(ctk.CTkFrame):

    ITEMS = [
        ("Home", "\u2302", "#555555"),
        ("Attack", "\u2694", "#cc4444"),
        ("Potion", "\u2697", "#44aa44"),
        ("Pet", "\u2665", "#cc88cc"),
        ("Buff", "\u21E7", "#cccc44"),
        ("Helper", "\u2699", "#888888"),
        ("Fairy", "\u2726", "#cc88cc"),
        ("Revive", "\u2715", "#cc4444"),
        ("Delete", "\u2717", "#888888"),
        ("BC", "\u25C6", "#4488cc"),
        ("Hollow", "\u25CE", "#8844cc"),
        ("---", None, None),
        ("Sell", "\u25C8", "#cc8844"),
        ("DR Lure", "\u25C9", "#cc44cc"),
        ("Key", "\u26BF", "#cc8844"),
    ]

    COLORS = {
        "Attack": "#cc4444", "Potion": "#44aa44", "Pet": "#cc88cc",
        "Buff": "#cccc44", "Helper": "#888888", "Fairy": "#cc88cc",
        "Revive": "#cc4444", "Delete": "#888888", "BC": "#4488cc",
        "Hollow": "#8844cc", "Sell": "#cc8844", "DR Lure": "#cc44cc",
        "Key": "#cc8844",
    }

    def __init__(self, parent, on_select: Callable[[str], None],
                 on_toggle: Callable[[str, bool], None] | None = None, **kwargs):
        super().__init__(parent, **kwargs)
        self._font = ctk.CTkFont(family="Segoe UI", size=14)
        self._icon_font = ctk.CTkFont(family="Segoe UI", size=17)
        self._on_select = on_select
        self._on_toggle = on_toggle
        self._cards: dict[str, ctk.CTkFrame] = {}
        self._switches: dict[str, ctk.CTkSwitch] = {}
        self._selected: str | None = None
        self._build()

    def _build(self):
        for label, icon, color in self.ITEMS:
            if label == "---":
                ctk.CTkFrame(self, height=2, fg_color="#555555").pack(fill="x", padx=8, pady=6)
                continue

            card = ctk.CTkFrame(self, corner_radius=6, border_width=2,
                                fg_color="transparent", border_color="#333333")
            card.pack(fill="x", padx=4, pady=2)

            card.grid_columnconfigure(1, weight=1)

            icon_lbl = ctk.CTkLabel(card, text=icon, font=self._icon_font,
                                    width=28, text_color=color)
            icon_lbl.grid(row=0, column=0, padx=(4, 0), pady=4)

            name_btn = ctk.CTkButton(card, text=label, font=self._font,
                                     fg_color="transparent", hover_color="#3a3a3a",
                                     anchor="w", height=28,
                                     command=lambda l=label: self._select(l))
            name_btn.grid(row=0, column=1, sticky="ew", padx=(2, 4), pady=4)

            sw = ctk.CTkSwitch(card, text="",
                               command=lambda l=label, s=None: self._toggle(l),
                               width=36)
            sw.grid(row=0, column=2, padx=(0, 8), pady=4)

            self._cards[label] = card
            self._switches[label] = sw

        self._select("Home")

    def _select(self, label: str):
        if self._selected:
            prev = self._cards.get(self._selected)
            if prev:
                prev.configure(fg_color="transparent", border_color="#333333")
        self._selected = label
        curr = self._cards.get(label)
        if curr:
            curr.configure(fg_color="#1a2a1a", border_color="#2a5c2a")
        self._on_select(label)

    def _toggle(self, label: str):
        sw = self._switches.get(label)
        if sw and self._on_toggle:
            self._on_toggle(label, sw.get())
        self._update_glow(label)

    def _update_glow(self, label: str):
        card = self._cards.get(label)
        sw = self._switches.get(label)
        if card and sw:
            if sw.get():
                color = self.COLORS.get(label, "#44aa44")
                card.configure(border_color=color)
            else:
                if label == self._selected:
                    card.configure(border_color="#2a5c2a")
                else:
                    card.configure(border_color="#333333")

    def set_enabled(self, label: str, enabled: bool):
        sw = self._switches.get(label)
        if sw:
            if sw.get() != enabled:
                sw.select() if enabled else sw.deselect()
            self._update_glow(label)

    def is_enabled(self, label: str) -> bool:
        sw = self._switches.get(label)
        return sw.get() if sw else False

    @property
    def selected(self) -> str | None:
        return self._selected
