# -*- coding: utf-8 -*-
"""
Ferramenta visual para calibrar regioes de HP, recurso e target.

Captura a janela do jogo e permite desenhar retangulos com o mouse.
As coordenadas sao salvas em hp_calibration.json na raiz do projeto.

Uso: python tools/calibrate_hp.py

Controles:
  - Clique e arraste para desenhar um retangulo
  - Tecla 1: definir Char HP
  - Tecla 2: definir Char Resource
  - Tecla 3: definir Target HP
  - Tecla R: resetar selecao
  - Tecla S: salvar e sair
  - ESC: sair sem salvar
"""

import json
import sys
import os
import tkinter as tk
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np
from PIL import Image, ImageTk

from src.infrastructure.window.service import WindowService
import config

CALIBRATION_FILE = Path(__file__).resolve().parents[1] / "hp_calibration.json"


class CalibrationTool:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd
        self.ws = WindowService()

        screenshot = self.ws.capture_hwnd(hwnd)
        self.img_bgr = screenshot
        self.img_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
        self.img_h, self.img_w = self.img_rgb.shape[:2]

        self.regions = {
            "char_hp": None,
            "char_resource": None,
            "target_hp": None,
        }

        self._current_label = "char_hp"
        self._start_x = None
        self._start_y = None
        self._rect_id = None

        self._build_ui()

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title("Calibrar HP — Arraste para desenhar retangulo")

        info = ttk = tk
        try:
            from tkinter import ttk as _ttk
            ttk = _ttk
        except Exception:
            pass

        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        # Canvas
        self.canvas = tk.Canvas(
            frame, width=self.img_w, height=self.img_h,
            cursor="cross", bg="black",
        )
        self.canvas.pack(side="left")

        self.photo = ImageTk.PhotoImage(
            Image.fromarray(self.img_rgb)
        )
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")

        # Eventos do mouse
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # Painel lateral
        side = tk.Frame(frame, padx=10, pady=10)
        side.pack(side="right", fill="y")

        tk.Label(side, text="Controles", font=("", 10, "bold")).pack(pady=(0, 8))

        self._info_label = tk.Label(side, text="Modo: Char HP", fg="green")
        self._info_label.pack()

        tk.Label(side, text="").pack()

        self._region_labels = {}
        for key, name in [
            ("char_hp", "Char HP"),
            ("char_resource", "Char Resource"),
            ("target_hp", "Target HP"),
        ]:
            lbl = tk.Label(side, text=f"{name}: --", fg="#888")
            lbl.pack(anchor="w")
            self._region_labels[key] = lbl

        tk.Label(side, text="").pack()
        tk.Label(side, text="Teclas:", font=("", 9, "bold")).pack(anchor="w")
        tk.Label(side, text="1 = Char HP").pack(anchor="w")
        tk.Label(side, text="2 = Char Resource").pack(anchor="w")
        tk.Label(side, text="3 = Target HP").pack(anchor="w")
        tk.Label(side, text="R = Resetar atual").pack(anchor="w")
        tk.Label(side, text="S = Salvar e Sair").pack(anchor="w")
        tk.Label(side, text="ESC = Sair sem salvar").pack(anchor="w")

        tk.Label(side, text="").pack()
        tk.Button(
            side, text="Salvar e Sair",
            command=self._save_and_exit,
        ).pack(fill="x", pady=2)
        tk.Button(
            side, text="Cancelar",
            command=self.root.destroy,
        ).pack(fill="x")

        # Bind teclas
        self.root.bind("<KeyPress-1>", lambda e: self._set_mode("char_hp"))
        self.root.bind("<KeyPress-2>", lambda e: self._set_mode("char_resource"))
        self.root.bind("<KeyPress-3>", lambda e: self._set_mode("target_hp"))
        self.root.bind("<KeyPress-r>", lambda e: self._reset_current())
        self.root.bind("<KeyPress-R>", lambda e: self._reset_current())
        self.root.bind("<KeyPress-s>", lambda e: self._save_and_exit())
        self.root.bind("<KeyPress-S>", lambda e: self._save_and_exit())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self._draw_saved_regions()

    def _set_mode(self, key: str):
        self._current_label = key
        names = {
            "char_hp": "Char HP",
            "char_resource": "Char Resource",
            "target_hp": "Target HP",
        }
        self._info_label.configure(
            text=f"Modo: {names.get(key, key)}", fg="green"
        )

    def _reset_current(self):
        self.regions[self._current_label] = None
        self._draw_saved_regions()

    def _on_press(self, event):
        self._start_x = event.x
        self._start_y = event.y
        if self._rect_id:
            self.canvas.delete(self._rect_id)

    def _on_drag(self, event):
        if self._rect_id:
            self.canvas.delete(self._rect_id)
        self._rect_id = self.canvas.create_rectangle(
            self._start_x, self._start_y,
            event.x, event.y,
            outline="lime", width=2,
        )

    def _on_release(self, event):
        if self._start_x is None or self._start_y is None:
            return

        x1 = min(self._start_x, event.x)
        y1 = min(self._start_y, event.y)
        x2 = max(self._start_x, event.x)
        y2 = max(self._start_y, event.y)

        w = x2 - x1
        h = y2 - y1

        if w < 5 or h < 3:
            return

        self.regions[self._current_label] = {
            "x": x1, "y": y1, "width": w, "height": h
        }

        self._draw_saved_regions()
        self._start_x = None
        self._start_y = None

    def _draw_saved_regions(self):
        self.canvas.delete("region")
        colors = {
            "char_hp": "green",
            "char_resource": "blue",
            "target_hp": "red",
        }
        for key, region in self.regions.items():
            if region is None:
                self._region_labels[key].configure(
                    text=f"{self._region_name(key)}: --", fg="#888"
                )
                continue

            x, y, w, h = region["x"], region["y"], region["width"], region["height"]
            color = colors.get(key, "white")
            self.canvas.create_rectangle(
                x, y, x + w, y + h,
                outline=color, width=2, tags="region",
            )
            label_text = self._region_name(key)
            self.canvas.create_text(
                x + w // 2, y - 10,
                text=label_text, fill=color, tags="region",
            )
            self._region_labels[key].configure(
                text=f"{label_text}: ({x},{y}) {w}x{h}", fg=color
            )

    @staticmethod
    def _region_name(key: str) -> str:
        return {
            "char_hp": "Char HP",
            "char_resource": "Char Resource",
            "target_hp": "Target HP",
        }.get(key, key)

    def _save_and_exit(self):
        data = {}
        for key, region in self.regions.items():
            if region:
                data[key] = region

        try:
            CALIBRATION_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Calibracao salva em: {CALIBRATION_FILE}")
        except Exception as e:
            print(f"Erro ao salvar: {e}")

        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    window = WindowService()

    try:
        hwnd = window.connect(title_substring=config.WINDOW_TITLE, timeout=10)
    except Exception as e:
        print(f"Janela '{config.WINDOW_TITLE}' nao encontrada: {e}")
        print("Abra o jogo primeiro e tente novamente.")
        sys.exit(1)

    tool = CalibrationTool(hwnd)
    tool.run()


if __name__ == "__main__":
    main()
