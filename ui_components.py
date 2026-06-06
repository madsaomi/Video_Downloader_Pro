import customtkinter as ctk
from tkinter import Menu
from typing import Tuple

ACCENT_COLOR: str = "#6366F1"
ACCENT_HOVER: str = "#4F46E5"
SUCCESS_COLOR: str = "#10B981"
SUCCESS_HOVER: str = "#059669"
WARNING_COLOR: str = "#F59E0B"
PLAYLIST_BADGE: str = "#3B82F6"

BG_DARK: Tuple[str, str] = ("#F2F4F7", "#09090B")
CARD_BG: Tuple[str, str] = ("#FFFFFF", "#121217")
CARD_BG_ALT: Tuple[str, str] = ("#F9FAFB", "#1A1A21")
CARD_BORDER: Tuple[str, str] = ("#E4E7EC", "#1A1A21")
TEXT_PRIMARY: Tuple[str, str] = ("#101828", "#F9FAFB")
TEXT_SECONDARY: Tuple[str, str] = ("#667085", "#A1A1AA")
SECONDARY_BTN: Tuple[str, str] = ("#E4E7EC", "#272730")
SECONDARY_BTN_HOVER: Tuple[str, str] = ("#D1D5DB", "#3F3F46")
SURFACE_DIM: Tuple[str, str] = ("#F2F4F7", "#1E1E26")


class ToastNotification(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk, message: str, type: str = "info", duration: int = 3000, **kwargs) -> None:
        super().__init__(master, corner_radius=12, **kwargs)

        colors: dict = {
            "info": ("#E4E7EC", "#1E1E26"),
            "success": ("#D1FADF", "#064E3B"),
            "error": ("#FEE4E2", "#7A271A"),
            "warning": ("#FEF0C7", "#7A4300"),
        }
        text_colors: dict = {
            "info": ("#101828", "#F9FAFB"),
            "success": ("#039855", "#34D399"),
            "error": ("#D92D20", "#F87171"),
            "warning": ("#DC6803", "#FBBF24"),
        }
        bg_color = colors.get(type, colors["info"])
        text_color = text_colors.get(type, text_colors["info"])

        self.configure(fg_color=bg_color)

        self.label = ctk.CTkLabel(self, text=message, font=ctk.CTkFont(size=14, weight="bold"), text_color=text_color)
        self.label.pack(padx=20, pady=12)

        self.duration: int = duration
        self._target_y: float = 60
        self._y: float = -100

        self.place(relx=0.5, y=int(self._y), anchor="n")
        self.lift()
        self._show_anim()

    def _show_anim(self) -> None:
        self._y += 8
        if self._y <= self._target_y:
            self.place(relx=0.5, y=int(self._y), anchor="n")
            self.after(12, self._show_anim)
        else:
            self.after(self.duration, self._hide_anim)

    def _hide_anim(self) -> None:
        self._y -= 8
        if self._y >= -100:
            self.place(relx=0.5, y=int(self._y), anchor="n")
            self.after(12, self._hide_anim)
        else:
            self.destroy()


def show_context_menu(event) -> None:
    menu = Menu(event.widget.master, tearoff=0)
    menu.add_command(label="Вырезать", command=lambda: event.widget.event_generate("<<Cut>>"))
    menu.add_command(label="Копировать", command=lambda: event.widget.event_generate("<<Copy>>"))
    menu.add_command(label="Вставить", command=lambda: event.widget.event_generate("<<Paste>>"))

    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()
