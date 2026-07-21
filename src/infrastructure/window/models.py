from dataclasses import dataclass

@dataclass
class WindowInfo:
    hwnd: int
    width: int
    height: int