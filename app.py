import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import copy
import os
import io
import re
import sys
import requests
from PIL import Image
from typing import Optional
from downloader import VideoDownloader
from history_manager import HistoryManager
import subprocess
import platform
import ctypes
from ctypes import wintypes

from urllib.parse import urlparse

from ui_components import (
    ACCENT_COLOR, ACCENT_HOVER, SUCCESS_COLOR, SUCCESS_HOVER,
    PLAYLIST_BADGE, BG_DARK, CARD_BG, CARD_BG_ALT,
    CARD_BORDER, TEXT_PRIMARY, TEXT_SECONDARY, SECONDARY_BTN,
    SECONDARY_BTN_HOVER, SURFACE_DIM, ToastNotification, show_context_menu,
)
from windows import SearchWindow, PlaylistWindow, SupportedSitesWindow


def _is_valid_url(url: str) -> bool:
    if ' ' in url:
        return False
    try:
        result = urlparse(url)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


def _get_downloads_folder() -> str:
    try:
        shell32 = ctypes.windll.shell32
        SHGetKnownFolderPath = shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [
            wintypes.GUID, wintypes.DWORD, wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]

        guid = wintypes.GUID(
            0x374DE290, 0x123F, 0x4565,
            (0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B),
        )
        p_path = ctypes.c_wchar_p()
        if SHGetKnownFolderPath(guid, 0, None, ctypes.byref(p_path)) == 0:
            return p_path.value
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Downloads")

ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Video Downloader Pro")
        self.minsize(800, 750)
        self.configure(fg_color=BG_DARK)
        self.downloader = VideoDownloader()
        self.fetched_info = None
        self._thumb_image: Optional[ctk.CTkImage] = None
        self._cancel_event = threading.Event()
        self._download_queue = []
        self._is_downloading = False

        self.history_mgr = HistoryManager()
        theme = self.history_mgr.get_setting("theme")
        if theme:
            ctk.set_appearance_mode(theme)

        saved_geo = self.history_mgr.get_setting("window_geometry")
        self.geometry(saved_geo if saved_geo else "850x880")
        self.bind("<Configure>", self._on_window_configure)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ═══ SIDEBAR ═══
        self.sidebar_frame = ctk.CTkFrame(self, fg_color=CARD_BG, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Video\nDownloader Pro", font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXT_PRIMARY)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(60, 30))

        self.hamburger_btn = ctk.CTkButton(self, text="☰", width=40, height=40, corner_radius=8, fg_color=CARD_BG, hover_color=SECONDARY_BTN, font=ctk.CTkFont(size=20), command=self.toggle_sidebar)
        self.hamburger_btn.place(x=10, y=10)
        self.sidebar_expanded = True
        self._sidebar_animating = False

        self.nav_btn_download = ctk.CTkButton(self.sidebar_frame, text="Скачать", font=ctk.CTkFont(size=15), fg_color="transparent", text_color=TEXT_PRIMARY, hover_color=SECONDARY_BTN, anchor="w", command=lambda: self.select_frame_by_name("download"))
        self.nav_btn_download.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.nav_btn_history = ctk.CTkButton(self.sidebar_frame, text="История", font=ctk.CTkFont(size=15), fg_color="transparent", text_color=TEXT_PRIMARY, hover_color=SECONDARY_BTN, anchor="w", command=lambda: self.select_frame_by_name("history"))
        self.nav_btn_history.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.nav_btn_settings = ctk.CTkButton(self.sidebar_frame, text="Настройки", font=ctk.CTkFont(size=15), fg_color="transparent", text_color=TEXT_PRIMARY, hover_color=SECONDARY_BTN, anchor="w", command=lambda: self.select_frame_by_name("settings"))
        self.nav_btn_settings.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        # ═══ FRAMES ═══
        self.download_frame = ctk.CTkScrollableFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.download_frame.grid_columnconfigure(0, weight=1)
        
        self.history_frame = ctk.CTkScrollableFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.history_frame.grid_columnconfigure(0, weight=1)
        
        self.settings_frame = ctk.CTkScrollableFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.settings_frame.grid_columnconfigure(0, weight=1)

        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

        container = self.download_frame

        # MAIN SEARCH
        # Batch Mode Switch
        self.batch_mode_var = ctk.BooleanVar(value=False)
        self.batch_mode_switch = ctk.CTkSwitch(container, text="Пакетная загрузка", variable=self.batch_mode_var, command=self._toggle_batch_mode, font=ctk.CTkFont(size=14))
        self.batch_mode_switch.grid(row=0, column=0, padx=40, pady=(20, 0), sticky="w")
        
        search_card = ctk.CTkFrame(container, fg_color="transparent")
        search_card.grid(row=1, column=0, padx=40, pady=(40, 10), sticky="ew")
        search_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(search_card, text="Ссылка на видео или поисковый запрос",
                     font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY,
                     anchor="w").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        urls = self.history_mgr.get_urls()
        self.url_entry = ctk.CTkComboBox(search_card, height=56, font=ctk.CTkFont(size=16), corner_radius=12,
                                         values=urls if urls else [""], border_width=1, border_color=CARD_BORDER,
                                         button_color=CARD_BG, button_hover_color=SECONDARY_BTN, 
                                         dropdown_fg_color=CARD_BG, dropdown_text_color=TEXT_PRIMARY)
        self.url_entry.grid(row=1, column=0, sticky="ew")
        
        self.batch_entry = ctk.CTkTextbox(search_card, height=120, font=ctk.CTkFont(size=14), corner_radius=12, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER)
        self.batch_entry.grid(row=1, column=0, sticky="ew")
        self.batch_entry.grid_remove()
        if not urls:
            self.url_entry.set("")

        self.paste_btn = ctk.CTkButton(search_card, text="Вставить", command=self.paste_url,
                                       width=100, height=56, corner_radius=12,
                                       fg_color=SECONDARY_BTN, hover_color=SECONDARY_BTN_HOVER, 
                                       text_color=TEXT_PRIMARY, font=ctk.CTkFont(weight="bold"))
        self.paste_btn.grid(row=1, column=1, padx=(10, 10))

        self.info_btn = ctk.CTkButton(search_card, text="Поиск", command=self.start_get_info,
                                      width=100, height=56, corner_radius=12, font=ctk.CTkFont(size=15, weight="bold"),
                                      fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER)
        self.info_btn.grid(row=1, column=2)

        # PREVIEW CARD
        self.preview_card = ctk.CTkFrame(container, fg_color=CARD_BG, corner_radius=16, border_width=0)
        self.preview_card.grid(row=2, column=0, padx=40, pady=10, sticky="ew")
        self.preview_card.grid_columnconfigure(1, weight=1)

        self.thumb_label = ctk.CTkLabel(self.preview_card, text="Превью",
                                        width=200, height=112, corner_radius=12,
                                        fg_color=CARD_BG_ALT, text_color=TEXT_SECONDARY,
                                        font=ctk.CTkFont(size=13))
        self.thumb_label.grid(row=0, column=0, rowspan=2, padx=16, pady=16)

        self.video_title_label = ctk.CTkLabel(self.preview_card, text="Введите ссылку выше",
                                              wraplength=450, justify="left",
                                              font=ctk.CTkFont(size=16, weight="bold"),
                                              text_color=TEXT_PRIMARY)
        self.video_title_label.grid(row=0, column=1, padx=10, pady=(20, 0), sticky="nw")

        self.duration_label = ctk.CTkLabel(self.preview_card, text="",
                                           font=ctk.CTkFont(size=14), text_color=TEXT_SECONDARY)
        self.duration_label.grid(row=1, column=1, padx=10, pady=(4, 20), sticky="nw")

        # FORMAT SELECTION
        format_card = ctk.CTkFrame(container, fg_color=CARD_BG, corner_radius=16, border_width=0)
        format_card.grid(row=3, column=0, padx=40, pady=10, sticky="ew")
        format_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(format_card, text="Качество", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT_PRIMARY).grid(row=0, column=0, padx=20, pady=16, sticky="w")

        fmt_frame = ctk.CTkFrame(format_card, fg_color="transparent")
        fmt_frame.grid(row=0, column=1, padx=16, pady=16, sticky="e")

        self.format_combo = ctk.CTkComboBox(fmt_frame, values=["—"], width=180,
                                            height=36, corner_radius=8, state="readonly",
                                            font=ctk.CTkFont(size=14), command=self._on_format_change,
                                            fg_color=SURFACE_DIM, border_width=0, button_color=SURFACE_DIM, 
                                            dropdown_fg_color=CARD_BG)
        self.format_combo.pack(side="left")

        self.audio_format_combo = ctk.CTkComboBox(fmt_frame, values=["MP3", "FLAC", "WAV", "M4A"], width=90,
                                                  height=36, corner_radius=8, state="readonly",
                                                  font=ctk.CTkFont(size=14), fg_color=SURFACE_DIM, border_width=0, button_color=SURFACE_DIM)
        self.audio_format_combo.set("MP3")
        self.audio_format_combo.pack(side="left", padx=(10, 0))
        self.audio_format_combo.pack_forget()

        # ADVANCED TOGGLE
        self.advanced_visible = False
        self.adv_btn = ctk.CTkButton(container, text="Расширенные настройки ▼", command=self.toggle_advanced,
                                     fg_color="transparent", text_color=TEXT_SECONDARY, hover_color=BG_DARK,
                                     font=ctk.CTkFont(size=14, underline=False))
        self.adv_btn.grid(row=4, column=0, pady=(10, 5))

        # ADVANCED FRAME
        self.adv_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.adv_frame.grid(row=5, column=0, padx=40, sticky="ew")
        self.adv_frame.grid_columnconfigure(0, weight=1)
        self.adv_frame.grid_remove()

        cookies_card = ctk.CTkFrame(self.adv_frame, fg_color=CARD_BG, corner_radius=12)
        cookies_card.grid(row=0, column=0, pady=5, sticky="ew")
        cookies_card.grid_columnconfigure(1, weight=1)
        
        self.use_browser_cookies = ctk.CTkCheckBox(cookies_card, text="Cookies из браузера:", font=ctk.CTkFont(size=14),
                                                   command=self._on_browser_checkbox)
        self.use_browser_cookies.grid(row=0, column=0, padx=16, pady=12, sticky="w")
        self.browser_combo = ctk.CTkComboBox(cookies_card, values=["chrome", "edge", "firefox", "opera", "brave"],
                                             width=110, height=28, corner_radius=6, fg_color=SURFACE_DIM, border_width=0, button_color=SURFACE_DIM)
        self.browser_combo.set("chrome")
        self.browser_combo.grid(row=0, column=1, padx=(0, 16), pady=12, sticky="w")

        ctk.CTkLabel(cookies_card, text="Или файл cookies.txt:", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")
        self.cookies_entry = ctk.CTkEntry(cookies_card, height=32, corner_radius=8, fg_color=SURFACE_DIM, border_width=0)
        self.cookies_entry.grid(row=1, column=1, padx=(0, 8), pady=(0, 12), sticky="ew")
        self.cookies_btn = ctk.CTkButton(cookies_card, text="Обзор", command=self.browse_cookies, width=70, height=32, corner_radius=8, fg_color=SECONDARY_BTN, hover_color=SECONDARY_BTN_HOVER, text_color=TEXT_PRIMARY)
        self.cookies_btn.grid(row=1, column=2, padx=(0, 16), pady=(0, 12))

        folder_card = ctk.CTkFrame(self.adv_frame, fg_color=CARD_BG, corner_radius=12)
        folder_card.grid(row=1, column=0, pady=5, sticky="ew")
        folder_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(folder_card, text="Папка сохранения:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=16, pady=12, sticky="w")
        self.folder_entry = ctk.CTkEntry(folder_card, height=32, corner_radius=8, fg_color=SURFACE_DIM, border_width=0)
        self.folder_entry.grid(row=0, column=1, padx=(0, 8), pady=12, sticky="ew")
        self.folder_entry.insert(0, _get_downloads_folder())
        self.folder_btn = ctk.CTkButton(folder_card, text="Обзор", command=self.browse_folder, width=70, height=32, corner_radius=8, fg_color=SECONDARY_BTN, hover_color=SECONDARY_BTN_HOVER, text_color=TEXT_PRIMARY)
        self.folder_btn.grid(row=0, column=2, padx=(0, 16), pady=12)

        subs_card = ctk.CTkFrame(self.adv_frame, fg_color=CARD_BG, corner_radius=12)
        subs_card.grid(row=2, column=0, pady=5, sticky="ew")
        subs_card.grid_columnconfigure(1, weight=1)
        
        self.trim_var = ctk.BooleanVar(value=False)
        self.trim_check = ctk.CTkCheckBox(subs_card, text="Обрезка по времени", variable=self.trim_var, command=self._on_trim_toggle, font=ctk.CTkFont(size=14))
        self.trim_check.grid(row=0, column=0, padx=16, pady=12, sticky="w")
        trim_frame = ctk.CTkFrame(subs_card, fg_color="transparent")
        trim_frame.grid(row=0, column=1, padx=(0, 16), pady=12, sticky="e")
        self.trim_start_entry = ctk.CTkEntry(trim_frame, placeholder_text="00:00", width=60, height=28, state="disabled", fg_color=SURFACE_DIM, border_width=0)
        self.trim_start_entry.pack(side="left")
        ctk.CTkLabel(trim_frame, text="-", font=ctk.CTkFont(size=13)).pack(side="left", padx=4)
        self.trim_end_entry = ctk.CTkEntry(trim_frame, placeholder_text="00:00", width=60, height=28, state="disabled", fg_color=SURFACE_DIM, border_width=0)
        self.trim_end_entry.pack(side="left")

        self.sponsorblock_var = ctk.BooleanVar(value=True)
        self.sponsor_check = ctk.CTkCheckBox(subs_card, text="Вырезать спонсоров", variable=self.sponsorblock_var, font=ctk.CTkFont(size=14))
        self.sponsor_check.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        self.subs_var = ctk.BooleanVar(value=False)
        self.auto_subs_var = ctk.BooleanVar(value=True)
        self.subs_check = ctk.CTkCheckBox(subs_card, text="Субтитры", variable=self.subs_var, font=ctk.CTkFont(size=14), command=self._on_subs_toggle)
        self.subs_check.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="w")
        
        subs_options = ctk.CTkFrame(subs_card, fg_color="transparent")
        subs_options.grid(row=2, column=1, padx=(0, 16), pady=(0, 12), sticky="e")
        self.subs_lang_combo = ctk.CTkComboBox(subs_options, values=["ru", "en", "ru, en", "de", "fr", "es"], width=70, height=28, fg_color=SURFACE_DIM, border_width=0, button_color=SURFACE_DIM)
        self.subs_lang_combo.set("ru, en")
        self.subs_lang_combo.pack(side="left", padx=(0, 8))
        self.subs_mode_combo = ctk.CTkComboBox(subs_options, values=["Вшить в видео", "Стиль YouTube", "Отдельный файл (.srt)"], width=160, height=28, fg_color=SURFACE_DIM, border_width=0, button_color=SURFACE_DIM, state="readonly")
        self.subs_mode_combo.set("Вшить в видео")
        self.subs_mode_combo.pack(side="left", padx=(0, 8))
        self.auto_subs_check = ctk.CTkCheckBox(subs_options, text="Авто", variable=self.auto_subs_var, font=ctk.CTkFont(size=12))
        self.auto_subs_check.pack(side="left")

        self.subs_avail_label = ctk.CTkLabel(self.adv_frame, text="", font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY)
        self.subs_avail_label.grid(row=3, column=0, padx=24, pady=0, sticky="w")

        # PLAYLIST CARD
        self.playlist_card = ctk.CTkFrame(container, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=PLAYLIST_BADGE)
        self.playlist_card.grid(row=6, column=0, padx=40, pady=10, sticky="ew")
        self.playlist_card.grid_columnconfigure(0, weight=1)
        self.playlist_card.grid_remove()

        # DOWNLOAD BUTTON
        self.download_btn = ctk.CTkButton(container, text="Скачать", command=self.start_download,
                                          height=56, corner_radius=12,
                                          font=ctk.CTkFont(size=18, weight="bold"),
                                          fg_color=SUCCESS_COLOR, hover_color=SUCCESS_HOVER)
        self.download_btn.grid(row=7, column=0, padx=40, pady=(20, 10), sticky="ew")
        self.download_btn.configure(state="disabled")

        self.cancel_btn = ctk.CTkButton(container, text="Отменить", command=self.cancel_download,
                                        height=56, corner_radius=12,
                                        font=ctk.CTkFont(size=18, weight="bold"),
                                        fg_color="#E11D48", hover_color="#BE123C")
        self.cancel_btn.grid(row=7, column=0, padx=40, pady=(20, 10), sticky="ew")
        self.cancel_btn.grid_remove()

        # PROGRESS
        progress_frame = ctk.CTkFrame(container, fg_color="transparent")
        progress_frame.grid(row=8, column=0, padx=40, pady=(0, 30), sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(progress_frame, text="Ожидание...",
                                         font=ctk.CTkFont(size=14), text_color=TEXT_SECONDARY)
        self.status_label.grid(row=0, column=0, sticky="w")

        self.queue_label = ctk.CTkLabel(progress_frame, text="",
                                        font=ctk.CTkFont(size=13, weight="bold"), text_color=PLAYLIST_BADGE)
        self.queue_label.grid(row=0, column=1, sticky="e")

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=8, corner_radius=4,
                                                progress_color=ACCENT_COLOR, fg_color=SURFACE_DIM)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.progress_bar.set(0)

        self.build_history_tab()
        self.build_settings_tab()
        self.select_frame_by_name("download")

        self._setup_context_menus()
        self.hamburger_btn.lift()
        self.bind("<Control-v>", lambda e: self.paste_url())
        self.bind("<Return>", lambda e: self.start_get_info() if self.info_btn.cget('state') == 'normal' else None)

    def select_frame_by_name(self, name: str) -> None:
        self.nav_btn_download.configure(fg_color=SECONDARY_BTN if name == "download" else "transparent", text_color=ACCENT_COLOR if name == "download" else TEXT_PRIMARY)
        self.nav_btn_history.configure(fg_color=SECONDARY_BTN if name == "history" else "transparent", text_color=ACCENT_COLOR if name == "history" else TEXT_PRIMARY)
        self.nav_btn_settings.configure(fg_color=SECONDARY_BTN if name == "settings" else "transparent", text_color=ACCENT_COLOR if name == "settings" else TEXT_PRIMARY)

        if name == "download":
            self.download_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.download_frame.grid_forget()
        
        if name == "history":
            self.history_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.history_frame.grid_forget()
            
        if name == "settings":
            self.settings_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.settings_frame.grid_forget()

    def toggle_sidebar(self) -> None:
        if self._sidebar_animating:
            return
        self._sidebar_animating = True
        if self.sidebar_expanded:
            self._animate_sidebar(200, 0, 12)
            self.sidebar_expanded = False
        else:
            self._animate_sidebar(0, 200, 12)
            self.sidebar_expanded = True

    def _animate_sidebar(self, current: int, target: int, frames: int, _count: int = 0) -> None:
        if _count >= frames:
            self.sidebar_frame.configure(width=target)
            if target == 0:
                self.sidebar_frame.grid_remove()
            self._sidebar_animating = False
            return
        frac = (_count + 1) / frames
        width = int(current + (target - current) * frac)
        if width > 0 and not self.sidebar_frame.winfo_ismapped():
            self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.configure(width=width)
        self.update_idletasks()
        self.after(16, lambda: self._animate_sidebar(current, target, frames, _count + 1))

    def show_toast(self, message: str, type: str = "info", duration: int = 3000) -> None:
        ToastNotification(self, message, type=type, duration=duration)

    def _toggle_batch_mode(self) -> None:
        if self.batch_mode_var.get():
            self.url_entry.grid_remove()
            self.batch_entry.grid()
        else:
            self.batch_entry.grid_remove()
            self.url_entry.grid()

    def toggle_advanced(self) -> None:
        if self.advanced_visible:
            self.adv_frame.grid_remove()
            self.adv_btn.configure(text="Расширенные настройки ▼")
            self.advanced_visible = False
        else:
            self.adv_frame.grid()
            self.adv_btn.configure(text="Расширенные настройки ▲")
            self.advanced_visible = True
            
        # We can simulate animation by just calling update_idletasks()
        self.update_idletasks()


    def _on_format_change(self, choice: str) -> None:
        if "аудио" in choice.lower() or "audio" in choice.lower():
            if not self.audio_format_combo.winfo_ismapped():
                self.audio_format_combo.pack(side="left", padx=(8, 0))
        else:
            if self.audio_format_combo.winfo_ismapped():
                self.audio_format_combo.pack_forget()

    def _on_trim_toggle(self) -> None:
        if self.trim_var.get():
            self.trim_start_entry.configure(state="normal")
            self.trim_end_entry.configure(state="normal")
        else:
            self.trim_start_entry.configure(state="disabled")
            self.trim_end_entry.configure(state="disabled")

    def _on_subs_toggle(self) -> None:
        enabled = self.subs_var.get()
        state = "normal" if enabled else "disabled"
        readonly_state = "readonly" if enabled else "disabled"
        self.subs_lang_combo.configure(state=state)
        self.subs_mode_combo.configure(state=readonly_state)
        self.auto_subs_check.configure(state=state)

    def _update_subs_avail_label(self, subtitle_langs: Optional[dict]) -> None:
        if not subtitle_langs:
            self.subs_avail_label.configure(text="")
            return
        manual = subtitle_langs.get('manual', [])
        auto = subtitle_langs.get('auto', [])
        parts = []
        if manual:
            parts.append(f"{', '.join(manual[:8])}{'...' if len(manual) > 8 else ''}")
        if auto:
            parts.append(f"авто: {len(auto)} яз.")
        self.subs_avail_label.configure(
            text=("Доступно: " + "  |  ".join(parts)) if parts else "Субтитры не обнаружены"
        )

    def _setup_context_menus(self) -> None:
        if hasattr(self.url_entry, "_entry"):
            self.url_entry._entry.bind("<Button-3>", show_context_menu)

        if hasattr(self.cookies_entry, "_entry"):
            self.cookies_entry._entry.bind("<Button-3>", show_context_menu)

        if hasattr(self.folder_entry, "_entry"):
            self.folder_entry._entry.bind("<Button-3>", show_context_menu)

        if hasattr(self.browser_combo, "_entry"):
            self.browser_combo._entry.bind("<Button-3>", show_context_menu)

    # ─── EXTRA TABS ───
    def build_history_tab(self) -> None:
        for w in self.history_frame.winfo_children():
            w.destroy()
            
        header = ctk.CTkFrame(self.history_frame, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(20, 10))
        
        ctk.CTkLabel(header, text="История скачиваний", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        
        self.history_search_var = ctk.StringVar()
        self.history_search_var.trace_add("write", lambda *_: self.refresh_history())
        search_entry = ctk.CTkEntry(header, textvariable=self.history_search_var,
                                    placeholder_text="Поиск в истории...", width=200, height=32,
                                    corner_radius=8, fg_color=SURFACE_DIM, border_width=0)
        search_entry.pack(side="right", padx=(0, 10))
        
        clear_btn = ctk.CTkButton(header, text="Очистить", width=100, command=self.clear_history,
                                  fg_color="#E11D48", hover_color="#BE123C")
        clear_btn.pack(side="right")
        
        self.history_scroll = ctk.CTkScrollableFrame(self.history_frame, fg_color=BG_DARK)
        self.history_scroll.pack(fill="both", expand=True, padx=40, pady=10)
        self.refresh_history()

    def clear_history(self) -> None:
        self.history_search_var.set("")
        if messagebox.askyesno("Очистить историю", "Удалить всю историю скачиваний?"):
            self.history_mgr.clear_history()
            self.refresh_history()

    def refresh_history(self) -> None:
        for w in self.history_scroll.winfo_children():
            w.destroy()
            
        downloads = self.history_mgr.get_downloads()
        query = self.history_search_var.get().strip().lower()
        if query:
            downloads = [d for d in downloads if query in d.get('title', '').lower()
                         or query in d.get('url', '').lower()
                         or query in d.get('format', '').lower()]
        
        if not downloads:
            msg = "Ничего не найдено" if query else "История пуста"
            ctk.CTkLabel(self.history_scroll, text=msg, text_color=TEXT_SECONDARY).pack(pady=40)
            return
            
        for d in downloads:
            card = ctk.CTkFrame(self.history_scroll, fg_color=CARD_BG, corner_radius=8, border_width=1, border_color=CARD_BORDER)
            card.pack(fill="x", pady=5, padx=10)
            card.grid_columnconfigure(1, weight=1)
            
            title_lbl = ctk.CTkLabel(card, text=d.get('title', 'Unknown')[:50], font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
            title_lbl.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 2), sticky="w")
            
            info_text = f"{d.get('date', '')}  |  Формат: {d.get('format', '')}"
            ctk.CTkLabel(card, text=info_text, font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY).grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")
            
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=0, column=2, rowspan=2, padx=10, pady=10)
            
            open_btn = ctk.CTkButton(btn_frame, text="Папка", width=80, height=28,
                                     fg_color=SECONDARY_BTN, hover_color=SECONDARY_BTN_HOVER,
                                     command=lambda path=d.get('path'): self.open_folder(path))
            open_btn.pack(side="left", padx=5)
            
            dl_btn = ctk.CTkButton(btn_frame, text="Скачать", width=80, height=28, 
                                   command=lambda url=d.get('url'): self.download_from_history(url))
            dl_btn.pack(side="left", padx=5)

    def download_from_history(self, url: str) -> None:
        self.select_frame_by_name("download")
        if '\n' in url:
            self.batch_mode_var.set(True)
            self._toggle_batch_mode()
            self.batch_entry.delete("1.0", "end")
            self.batch_entry.insert("1.0", url)
        else:
            self.url_entry.set(url)
        self.start_get_info()

    def open_folder(self, path: str) -> None:
        if not path or not os.path.isdir(path):
            self.show_toast(f"Папка не найдена:\n{path}")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.show_toast(f"Не удалось открыть папку:\n{e}")

    def build_settings_tab(self) -> None:
        title = ctk.CTkLabel(self.settings_frame, text="Настройки", font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(anchor="w", padx=40, pady=(30, 20))
        
        card = ctk.CTkFrame(self.settings_frame, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color=CARD_BORDER)
        card.pack(fill="x", padx=40, pady=10)
        
        self.meta_var = ctk.BooleanVar(value=self.history_mgr.get_setting("embed_metadata"))
        meta_cb = ctk.CTkCheckBox(card, text="Вшивать метаданные и обложки (MP3/Видео)", variable=self.meta_var, 
                                  command=self._save_settings, font=ctk.CTkFont(size=14))
        meta_cb.pack(anchor="w", padx=20, pady=20)
        
        theme_frame = ctk.CTkFrame(card, fg_color="transparent")
        theme_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(theme_frame, text="Тема оформления:", font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 15))
        
        self.theme_combo = ctk.CTkComboBox(theme_frame, values=["Dark", "Light", "System"], command=self._change_theme)
        theme = self.history_mgr.get_setting("theme")
        if theme:
            self.theme_combo.set(theme)
        self.theme_combo.pack(side="left")

        # C: предпочтительное качество
        qual_frame = ctk.CTkFrame(card, fg_color="transparent")
        qual_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(qual_frame, text="Предпочтительное качество:",
                     font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 15))
        qual_values = ["— (не задано)", "2160p", "1440p", "1080p", "720p", "480p", "360p", "Только аудио"]
        self.quality_pref_combo = ctk.CTkComboBox(qual_frame, values=qual_values,
                                                   width=160, state="readonly",
                                                   command=self._save_quality_pref)
        saved_q = self.history_mgr.get_setting("preferred_quality") or "— (не задано)"
        self.quality_pref_combo.set(saved_q)
        self.quality_pref_combo.pack(side="left")

        # D: Лимит скорости
        limit_frame = ctk.CTkFrame(card, fg_color="transparent")
        limit_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(limit_frame, text="Лимит скорости (МБ/с):",
                     font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 15))
        self.rate_limit_var = ctk.StringVar(value=str(self.history_mgr.get_setting("rate_limit") or 0))
        rate_entry = ctk.CTkEntry(limit_frame, textvariable=self.rate_limit_var, width=80)
        rate_entry.pack(side="left")
        rate_entry.bind("<KeyRelease>", lambda e: self._save_rate_limit())
        ctk.CTkLabel(limit_frame, text=" (0 = безлимит)", font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY).pack(side="left", padx=5)

        # G: Системные уведомления
        self.notif_var = ctk.BooleanVar(value=self.history_mgr.get_setting("notifications_enabled", True))
        notif_cb = ctk.CTkCheckBox(card, text="Системные уведомления по завершении (Windows)", variable=self.notif_var, 
                                   command=self._save_notif_settings, font=ctk.CTkFont(size=14))
        notif_cb.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Updater
        update_frame = ctk.CTkFrame(card, fg_color="transparent")
        update_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(update_frame, text="Обновление ядра:", font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 15))
        self.update_btn = ctk.CTkButton(update_frame, text="Обновить yt-dlp", command=self._update_ytdlp, fg_color=SECONDARY_BTN, hover_color=SECONDARY_BTN_HOVER, width=150)
        self.update_btn.pack(side="left")

    def _save_rate_limit(self) -> None:
        try:
            val = float(self.rate_limit_var.get())
            self.history_mgr.set_setting("rate_limit", val)
        except ValueError:
            pass

    def _save_notif_settings(self) -> None:
        self.history_mgr.set_setting("notifications_enabled", self.notif_var.get())

    def _update_ytdlp(self) -> None:
        self.update_btn.configure(state="disabled", text="Обновление...")
        self.show_toast("Началось обновление yt-dlp. Пожалуйста, подождите...")
        threading.Thread(target=self._run_ytdlp_update, daemon=True).start()

    def _run_ytdlp_update(self) -> None:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                self.after(0, lambda: self.show_toast("Ядро yt-dlp успешно обновлено!", "success"))
            else:
                self.after(0, lambda: self.show_toast("Ошибка при обновлении yt-dlp.", "error"))
        except subprocess.TimeoutExpired:
            self.after(0, lambda: self.show_toast("Ошибка: время обновления истекло (120с).", "error"))
        except Exception as exc:
            self.after(0, lambda exc=exc: self.show_toast(f"Ошибка: {exc}", "error"))
        finally:
            self.after(0, lambda: self.update_btn.configure(state="normal", text="Обновить yt-dlp"))

    def _save_settings(self):
        self.history_mgr.set_setting("embed_metadata", self.meta_var.get())

    def _save_quality_pref(self, choice: str) -> None:
        self.history_mgr.set_setting("preferred_quality", choice)

    def _change_theme(self, choice: str) -> None:
        self.history_mgr.set_setting("theme", choice)
        ctk.set_appearance_mode(choice)

    def _on_window_configure(self, event) -> None:
        if event.widget is self:
            if hasattr(self, '_debounce_save'):
                self.after_cancel(self._debounce_save)
            self._debounce_save = self.after(500, self._save_window_geometry)

    def _save_window_geometry(self) -> None:
        if self.state() == 'normal':
            self.history_mgr.set_setting("window_geometry", self.geometry())

    def _on_app_close(self) -> None:
        self.history_mgr.set_setting("theme", ctk.get_appearance_mode())
        self.history_mgr.set_setting("preferred_quality", self.format_combo.get())
        self.history_mgr.set_setting("notifications_enabled", self.notif_var.get())
        self._save_window_geometry()
        if self._is_downloading:
            self._cancel_event.set()
        self.destroy()

    def _on_browser_checkbox(self) -> None:
        if self.use_browser_cookies.get():
            self.cookies_entry.configure(state="disabled", text_color="gray")
            self.cookies_btn.configure(state="disabled")
        else:
            self.cookies_entry.configure(state="normal", text_color=TEXT_PRIMARY)
            self.cookies_btn.configure(state="normal")

    def show_supported_sites(self) -> None:
        SupportedSitesWindow(self)

    def paste_url(self) -> None:
        try:
            text = self.clipboard_get().strip()
            if self.batch_mode_var.get():
                self.batch_entry.delete("1.0", "end")
                self.batch_entry.insert("1.0", text)
            else:
                self.url_entry.set(text)
        except Exception:
            pass

    def browse_cookies(self) -> None:
        f = filedialog.askopenfilename(title="Выберите cookies.txt",
                                       filetypes=(("Text", "*.txt"), ("All", "*.*")))
        if f:
            self.use_browser_cookies.deselect()
            self._on_browser_checkbox()
            self.cookies_entry.delete(0, 'end')
            self.cookies_entry.insert(0, f)

    def browse_folder(self) -> None:
        d = filedialog.askdirectory(title="Папка сохранения")
        if d:
            self.folder_entry.delete(0, 'end')
            self.folder_entry.insert(0, d)

    def set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def load_image_from_url(self, url: str) -> Optional[ctk.CTkImage]:
        MAX_SIZE = 10 * 1024 * 1024
        try:
            with requests.get(url, timeout=8, stream=True) as r:
                r.raise_for_status()
                cl = r.headers.get('Content-Length')
                if cl and int(cl) > MAX_SIZE:
                    return None
                chunks = []
                total = 0
                for chunk in r.iter_content(8192):
                    total += len(chunk)
                    if total > MAX_SIZE:
                        return None
                    chunks.append(chunk)
                data = b''.join(chunks)
                img = Image.open(io.BytesIO(data))
                w, h = img.size
                if h <= 0:
                    return None
                new_w = 220
                new_h = int(new_w / (w / h))
                return ctk.CTkImage(light_image=img, dark_image=img, size=(new_w, new_h))
        except Exception:
            return None

    # ─── PLAYLIST UI ───

    def _show_search_window(self, info: dict) -> None:
        SearchWindow(self, info)

    def _build_playlist_card(self, info: dict) -> None:
        """Строит карточку плейлиста с подробной информацией."""
        # Очищаем старое содержимое
        for widget in self.playlist_card.winfo_children():
            widget.destroy()

        videos = info.get('videos', [])
        count = info.get('video_count', len(videos))
        total_dur_sec = info.get('total_duration_sec', 0)

        # ── Заголовок плейлиста ──
        header_frame = ctk.CTkFrame(self.playlist_card, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=16, pady=(14, 4), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # Бейдж "Плейлист"
        badge = ctk.CTkLabel(header_frame, text="ПЛЕЙЛИСТ",
                             font=ctk.CTkFont(size=11, weight="bold"),
                             text_color="white", fg_color=PLAYLIST_BADGE,
                             corner_radius=6, width=80, height=24)
        badge.grid(row=0, column=0, padx=(0, 10), sticky="w")

        if total_dur_sec:
            hours = total_dur_sec // 3600
            mins = (total_dur_sec % 3600) // 60
            if hours:
                dur_text = f"{hours}ч {mins}мин"
            else:
                dur_text = f"{mins} мин"
        else:
            dur_text = "—"

        stats_text = f"{count} видео  •  {dur_text}"
        stats_label = ctk.CTkLabel(header_frame, text=stats_text,
                                   font=ctk.CTkFont(size=13, weight="bold"),
                                   text_color=TEXT_PRIMARY)
        stats_label.grid(row=0, column=1, sticky="w")

        show_btn = ctk.CTkButton(header_frame, text=f"Показать все {count} видео",
                                 font=ctk.CTkFont(size=12),
                                 fg_color=SECONDARY_BTN, hover_color=SECONDARY_BTN_HOVER,
                                 width=160, height=28, corner_radius=6,
                                 command=lambda: self._show_playlist_window(info))
        show_btn.grid(row=0, column=2, padx=(10, 0), sticky="e")

        # ── Список видео (превью — первые 5) ──
        list_frame = ctk.CTkFrame(self.playlist_card, fg_color="transparent")
        list_frame.grid(row=1, column=0, padx=12, pady=(6, 4), sticky="ew")
        list_frame.grid_columnconfigure(1, weight=1)

        preview_count = min(5, len(videos))
        for i, video in enumerate(videos[:preview_count]):
            row_bg = CARD_BG_ALT if i % 2 == 0 else CARD_BG
            row_frame = ctk.CTkFrame(list_frame, fg_color=row_bg, corner_radius=8, height=36)
            row_frame.grid(row=i, column=0, columnspan=2, sticky="ew", pady=2, padx=4)
            row_frame.grid_columnconfigure(1, weight=1)
            row_frame.grid_propagate(False)

            # Номер
            idx_label = ctk.CTkLabel(row_frame, text=f"{video['index']:>2}.",
                                     font=ctk.CTkFont(size=12, weight="bold"),
                                     text_color=ACCENT_COLOR, width=32)
            idx_label.grid(row=0, column=0, padx=(10, 4), pady=6)

            # Название (обрезанное)
            title_text = video.get('title', '—')
            if len(title_text) > 55:
                title_text = title_text[:52] + "..."
            title_lbl = ctk.CTkLabel(row_frame, text=title_text,
                                     font=ctk.CTkFont(size=12),
                                     text_color=TEXT_PRIMARY, anchor="w")
            title_lbl.grid(row=0, column=1, padx=4, pady=6, sticky="w")

            # Длительность
            dur = video.get('duration', '')
            if dur:
                dur_lbl = ctk.CTkLabel(row_frame, text=f"⏱ {dur}",
                                       font=ctk.CTkFont(size=11),
                                       text_color=TEXT_SECONDARY, width=70)
                dur_lbl.grid(row=0, column=2, padx=(4, 10), pady=6)

        # Если видео больше 5 — показываем "ещё N видео"
        if count > preview_count:
            remaining = count - preview_count
            more_label = ctk.CTkLabel(list_frame,
                                      text=f"... и ещё {remaining} видео →",
                                      font=ctk.CTkFont(size=12, slant="italic"),
                                      text_color=TEXT_SECONDARY, cursor="hand2")
            more_label.grid(row=preview_count, column=0, columnspan=2, pady=(4, 2), padx=16, sticky="w")
            more_label.bind("<Button-1>", lambda e: self._show_playlist_window(info))

        # ── Нижняя полоса со сводкой ══
        summary_frame = ctk.CTkFrame(self.playlist_card, fg_color=SURFACE_DIM, corner_radius=8)
        summary_frame.grid(row=2, column=0, padx=12, pady=(6, 12), sticky="ew")
        summary_frame.grid_columnconfigure(0, weight=1)
        summary_frame.grid_columnconfigure(1, weight=1)
        summary_frame.grid_columnconfigure(2, weight=1)

        # Количество
        ctk.CTkLabel(summary_frame, text=f"{count}",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT_PRIMARY).grid(row=0, column=0, padx=16, pady=(10, 2))
        ctk.CTkLabel(summary_frame, text="видео",
                     font=ctk.CTkFont(size=11),
                     text_color=TEXT_SECONDARY).grid(row=1, column=0, padx=16, pady=(0, 10))

        ctk.CTkLabel(summary_frame, text=dur_text,
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT_PRIMARY).grid(row=0, column=1, padx=16, pady=(10, 2))
        ctk.CTkLabel(summary_frame, text="общая длительность",
                     font=ctk.CTkFont(size=11),
                     text_color=TEXT_SECONDARY).grid(row=1, column=1, padx=16, pady=(0, 10))

        uploader = info.get('uploader', '') or '—'
        ctk.CTkLabel(summary_frame, text=uploader[:20],
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT_PRIMARY).grid(row=0, column=2, padx=16, pady=(10, 2))
        ctk.CTkLabel(summary_frame, text="автор",
                     font=ctk.CTkFont(size=11),
                     text_color=TEXT_SECONDARY).grid(row=1, column=2, padx=16, pady=(0, 10))

        self.playlist_card.grid()

    def _show_playlist_window(self, info: dict) -> None:
        PlaylistWindow(self, info)

    # ─── GET INFO ───

    def start_get_info(self) -> None:
        if self.batch_mode_var.get():
            urls_text = self.batch_entry.get("1.0", "end-1c")
            urls = [u.strip() for u in urls_text.splitlines() if _is_valid_url(u.strip())]
            if not urls:
                self.show_toast("Введите хотя бы одну корректную ссылку!")
                return
            
            info = {
                'status': 'success',
                'type': 'batch',
                'urls': urls,
                'video_count': len(urls),
                'title': f'Пакетная загрузка ({len(urls)} ссылок)',
                'formats': ['2160p (4K)', '1440p (2K)', '1080p (Full HD)', '720p (HD)', '480p', '360p', 'Только аудио (MP3)'],
            }
            self.info_btn.configure(state="disabled")
            self.download_btn.configure(state="disabled")
            self.set_status("Инициализация пакета...")
            self.progress_bar.set(0)
            self.after(500, self._info_fetched, info)
            return

        url = self.url_entry.get().strip()
        if not url:
            self.show_toast("Введите ссылку или поисковый запрос!")
            return

        is_search = False
        search_query_url = url
        if not url.startswith(('http://', 'https://')):
            is_search = True
            search_query_url = f"ytsearch10:{url}"
            self.url_entry.set("")
        elif _is_valid_url(url):
            self.history_mgr.add_url(url)
            self.url_entry.configure(values=self.history_mgr.get_urls())
        else:
            self.show_toast("Некорректная ссылка!")
            return

        cookies = self.cookies_entry.get().strip()
        browser = None
        if self.use_browser_cookies.get():
            browser = self.browser_combo.get()
            cookies = ""  # Игнорируем файл, если используется браузер

        self.info_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self.set_status("Получение информации...")
        self.progress_bar.set(0)

        # Скрываем плейлист-карточку
        self.playlist_card.grid_remove()

        threading.Thread(target=self._get_info_thread, args=(search_query_url, cookies, browser, is_search), daemon=True).start()

    def _get_info_thread(self, url: str, cookies: str, browser: Optional[str], is_search: bool = False) -> None:
        info = self.downloader.fetch_info(url, cookies if cookies else None, browser)
        if is_search and info.get('status') == 'success':
            info['is_search'] = True
        self.after(0, self._info_fetched, info)

    def _info_fetched(self, info: dict) -> None:
        self.info_btn.configure(state="normal")

        if info.get('status') == 'error':
            self.show_toast(info.get('message', 'Неизвестная ошибка'))
            self.set_status("Ошибка получения информации.")
            return

        self.fetched_info = info
        title = info.get('title', '—')
        formats = info.get('formats', ['—'])
        thumb_url = info.get('thumbnail')
        is_search = info.get('is_search', False)
        if is_search:
            self.set_status("Поиск завершён! Выберите видео.")
            self._show_search_window(info)
            return

        is_playlist = info.get('type') == 'playlist'
        is_batch = info.get('type') == 'batch'

                # ── Обновляем превью-карточку ──
        if is_playlist or is_batch:
            count = info.get('video_count', 0)
            self.video_title_label.configure(text=title)
            duration_text = f"{count} видео"
            if is_playlist:
                duration_text += f"  •  {info.get('total_duration', '—')}"
            self.duration_label.configure(text=duration_text)

            if is_playlist:
                self._build_playlist_card(info)
            else:
                self.playlist_card.grid_remove()

            self.download_btn.configure(text=f"Скачать все {count} видео")
        else:
            duration = info.get('duration', '')
            self.video_title_label.configure(text=title)
            self.duration_label.configure(text=duration if duration else "")
            self.playlist_card.grid_remove()
            self.download_btn.configure(text="Скачать")

        if formats:
            self.format_combo.configure(values=formats)
            # C: пробуем выбрать предпочтительное качество
            pref = self.history_mgr.get_setting("preferred_quality") or ""
            selected = formats[0]  # по умолчанию — лучшее доступное
            if pref and pref != "— (не задано)":
                if "аудио" in pref.lower():
                    audio_fmt = next((f for f in formats if "аудио" in f.lower()), None)
                    if audio_fmt:
                        selected = audio_fmt
                else:
                    res_key = pref.replace("p", "").strip()  # "1080p" → "1080"
                    match = next((f for f in formats if f.startswith(res_key + "p")), None)
                    if match:
                        selected = match
            self.format_combo.set(selected)
            self.download_btn.configure(state="normal")

        # Предупреждение о блокировке видеоформатов YouTube
        if info.get('no_video_warning'):
            messagebox.showwarning(
                "YouTube ограничил доступ",
                "YouTube заблокировал видеоформаты (бот-защита).\n\n"
                "Доступно только аудио (MP3).\n\n"
                "Чтобы скачать видео:\n"
                "1. Закройте Chrome полностью\n"
                "2. Поставьте галочку «Cookies из браузера»\n"
                "3. Или экспортируйте cookies.txt и укажите файл\n\n"
                "Аудио можно скачать прямо сейчас!"
            )

        # ── Обновляем доступные языки субтитров ──
        subtitle_langs = info.get('subtitle_langs')
        self._update_subs_avail_label(subtitle_langs)

        if thumb_url:
            self.set_status("Загрузка превью...")
            threading.Thread(target=self._load_thumb, args=(thumb_url,), daemon=True).start()
        else:
            self.set_status("Готово! Выберите качество и нажмите «Скачать».")

    def _load_thumb(self, url: str) -> None:
        img = self.load_image_from_url(url)
        self.after(0, self._set_thumb, img)

    def _set_thumb(self, img: Optional[ctk.CTkImage]) -> None:
        if img:
            self._thumb_image = img
            self.thumb_label.configure(image=img, text="")
        else:
            self.thumb_label.configure(text="Превью\nнедоступно")
        self.set_status("Готово! Выберите качество и нажмите «Скачать».")

    # ─── DOWNLOAD ───

    def start_download(self) -> None:
        if self.batch_mode_var.get():
            urls_text = self.batch_entry.get("1.0", "end-1c")
            url = [u.strip() for u in urls_text.splitlines() if u.strip().startswith(('http://', 'https://')) and _is_valid_url(u.strip())]
        else:
            url = self.url_entry.get().strip()
            if url and not _is_valid_url(url):
                self.show_toast("Некорректная ссылка!")
                return
        cookies = self.cookies_entry.get().strip()
        fmt = self.format_combo.get()
        out_dir = self.folder_entry.get().strip()
        browser = None
        if self.use_browser_cookies.get():
            browser = self.browser_combo.get()
            cookies = ""  # Игнорируем файл, если используется браузер

        # Fix #9: проверяем, что формат валидный (не заглушка «—»)
        if not fmt or fmt == "—":
            messagebox.showerror(
                "Формат не выбран",
                "Сначала нажмите «Получить информацию» и дождитесь загрузки данных о видео."
            )
            return

        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except Exception as e:
                self.show_toast(f"Не удалось создать папку:\n{e}")
                return

        audio_fmt = self.audio_format_combo.get()
        use_sponsorblock = getattr(self, "sponsorblock_var", ctk.BooleanVar(value=False)).get()
        
        trim_start = None
        trim_end = None
        if getattr(self, "trim_var", ctk.BooleanVar(value=False)).get():
            trim_start = self.trim_start_entry.get().strip()
            trim_end = self.trim_end_entry.get().strip()

        # B: Если уже качаем, ставим в очередь
        download_task = {
            'url': url,
            'fmt': fmt,
            'out_dir': out_dir,
            'cookies': cookies,
            'browser': browser,
            'fetched_info': copy.deepcopy(self.fetched_info) if self.fetched_info else None,
            'audio_fmt': audio_fmt,
            'use_sponsorblock': use_sponsorblock,
            'trim_start': trim_start,
            'trim_end': trim_end
        }

        if self._is_downloading:
            self._download_queue.append(download_task)
            self._update_queue_label()
            self.set_status(f"Добавлено в очередь! (Позиция: {len(self._download_queue)})")
            return

        self._start_next_download(download_task)

    def _update_queue_label(self) -> None:
        q_len = len(self._download_queue)
        if q_len > 0:
            self.queue_label.configure(text=f"В очереди: {q_len}")
        else:
            self.queue_label.configure(text="")

    def _start_next_download(self, task: dict) -> None:
        self._is_downloading = True
        self._update_queue_label()

        url = task['url']
        fmt = task['fmt']
        out_dir = task['out_dir']
        cookies = task['cookies']
        browser = task['browser']
        fetched_info_copy = task['fetched_info']

        # A: готовим событие отмены, переключаем кнопки
        self._cancel_event.clear()
        self.download_btn.grid_remove()
        self.cancel_btn.grid()
        self.info_btn.configure(state="disabled")
        self.progress_bar.set(0)

        is_playlist = fetched_info_copy and fetched_info_copy.get('type') == 'playlist'
        if is_playlist:
            count = fetched_info_copy.get('video_count', 0)
            self.set_status(f"Начало скачивания плейлиста ({count} видео)...")
        else:
            self.set_status("Начало скачивания...")

        # Читаем все tkinter-переменные здесь, в главном потоке (thread-safe)
        embed_meta = self.history_mgr.get_setting("embed_metadata")
        rate_limit = self.history_mgr.get_setting("rate_limit") or 0
        dl_subs = self.subs_var.get()
        lang_str = self.subs_lang_combo.get().strip()
        sub_langs = [lang.strip() for lang in lang_str.split(',') if lang.strip()] if lang_str else ['ru', 'en']
        subs_mode = self.subs_mode_combo.get()
        embed_subs = "Вшить" in subs_mode
        youtube_style = "Стиль YouTube" in subs_mode
        auto_subs = self.auto_subs_var.get()
        if youtube_style:
            sub_fmt = "ass"
        elif embed_subs:
            sub_fmt = "srt"
        elif "vtt" in subs_mode:
            sub_fmt = "vtt"
        elif "ass" in subs_mode:
            sub_fmt = "ass"
        elif "json3" in subs_mode:
            sub_fmt = "json3"
        else:
            sub_fmt = "srt"

        # В _download_finished нам понадобятся данные текущей задачи
        self._current_task = task
        
        audio_fmt = task.get('audio_fmt', 'MP3')
        use_sponsorblock = task.get('use_sponsorblock', False)
        trim_start = task.get('trim_start')
        trim_end = task.get('trim_end')

        threading.Thread(
            target=self._download_thread,
            args=(url, fmt, out_dir, cookies if cookies else None, browser,
                  fetched_info_copy, embed_meta, dl_subs, sub_langs, sub_fmt,
                  auto_subs, embed_subs, youtube_style, rate_limit,
                  audio_fmt, use_sponsorblock, trim_start, trim_end),
            daemon=True
        ).start()

    # A: отмена скачивания
    def cancel_download(self) -> None:
        self._cancel_event.set()
        self.cancel_btn.configure(state="disabled", text="Отмена...")
        self.set_status("Отмена загрузки...")

    def _download_thread(
        self, url, fmt, out_dir, cookies, browser, fetched_info,
        embed_meta, dl_subs, sub_langs, sub_fmt,
        auto_subs, embed_subs, youtube_style, rate_limit,
        audio_fmt, use_sponsorblock, trim_start, trim_end,
    ) -> None:
        def progress_cb(percent, text):
            queue_len = len(self._download_queue)
            suffix = f" | +{queue_len} в очереди" if queue_len else ""
            self.after(0, self.progress_bar.set, percent)
            self.after(0, self.set_status, f"{percent*100:.0f}%  {text}")
            self.after(0, self.title, f"Video Downloader Pro — {percent*100:.0f}%{suffix}")

        def done_cb(errors=0, err_msgs=None):
            if fetched_info and fetched_info.get('type') == 'playlist':
                playlist_title = fetched_info.get('title', 'Playlist')
                safe = re.sub(r'[\\/*?:"<>|]', "_", playlist_title).strip()
                if out_dir:
                    self._current_task['out_dir'] = os.path.join(out_dir, safe)
            self.after(0, lambda: self._download_finished(errors, err_msgs))

        def err_cb(msg):
            # A: отличаем отмену от настоящей ошибки
            if msg == "__CANCELLED__":
                self.after(0, self._download_cancelled)
            else:
                self.after(0, self._download_error, msg)

        def playlist_item_cb(current, total, title):
            short_title = title[:40] + "..." if len(title) > 40 else title
            queue_len = len(self._download_queue)
            suffix = f" | +{queue_len} в очереди" if queue_len else ""
            self.after(0, self.set_status, f"[{current}/{total}] {short_title}")
            self.after(0, self.title, f"Video Downloader Pro — [{current}/{total}]{suffix}")

        try:
            self.downloader.download(
                url, fmt, out_dir, cookies, browser,
                progress_cb, done_cb, err_cb, playlist_item_cb,
                fetched_info, embed_meta,
                download_subtitles=dl_subs,
                subtitle_langs=sub_langs,
                subtitle_format=sub_fmt,
                auto_subtitles=auto_subs,
                embed_subtitles=embed_subs,
                youtube_style=youtube_style,
                cancel_event=self._cancel_event,  # A: передаём событие отмены
                rate_limit=rate_limit,
                audio_format=audio_fmt,
                sponsorblock=use_sponsorblock,
                trim_start=trim_start,
                trim_end=trim_end
            )
        except Exception as e:
            err_cb(str(e))

    def _restore_download_btn(self) -> None:
        self.cancel_btn.grid_remove()
        self.cancel_btn.configure(state="normal", text="Отменить загрузку")
        self.download_btn.grid()
        self.download_btn.configure(state="normal")
        self.info_btn.configure(state="normal")
        # H: убираем прогресс из заголовка
        self.title("Video Downloader Pro")

    def _download_finished(self, errors: int = 0, err_msgs: Optional[list] = None) -> None:
        self.progress_bar.set(1.0)
        task = getattr(self, '_current_task', None)
        folder = task['out_dir'] if task else self.folder_entry.get()
        fetched_info = task['fetched_info'] if task else self.fetched_info

        title = fetched_info.get('title', 'Unknown') if fetched_info else 'Unknown'
        url = task['url'] if task else self.url_entry.get().strip()
        if isinstance(url, list):
            url = '\n'.join(url)
        fmt = task['fmt'] if task else self.format_combo.get()

        self.history_mgr.add_download(title, url, folder, fmt)
        self.refresh_history()

        is_playlist = fetched_info and fetched_info.get('type') == 'playlist'

        notif_enabled = self.history_mgr.get_setting("notifications_enabled", True)
        def send_toast(msg_title, msg_body):
            if notif_enabled:
                try:
                    import win11toast
                    win11toast.toast(msg_title, msg_body, app_id="Video Downloader Pro")
                except Exception:
                    pass

        if is_playlist:
            count = fetched_info.get('video_count', 0)
            if errors > 0:
                self.set_status(f"Плейлист скачан с ошибками ({errors} видео пропущено)!")
                send_toast("Загрузка с ошибками", f"Плейлист скачан, {errors} видео пропущено.")
                detail = ""
                if err_msgs:
                    detail = "\n\nПример ошибки:\n" + "\n".join(err_msgs[:2])
                if not self._download_queue:
                    messagebox.showwarning(
                        "Загрузка завершена с ошибками",
                        f"Плейлист скачан, но {errors} из {count} видео не удалось загрузить."
                        f"\n\nОстальные видео сохранены в:\n{folder}{detail}"
                    )
            else:
                self.set_status(f"Плейлист ({count} видео) скачан!")
                send_toast("Плейлист загружен", f"{title} успешно скачан.")
                # Спрашиваем открыть папку, только если очередь пуста
                if not self._download_queue and messagebox.askyesno("Готово!",
                                       f"Плейлист ({count} видео) успешно скачан!\n\n"
                                       f"Папка: {folder}\n\nОткрыть папку?"):
                    self.open_folder(folder)
        else:
            self.set_status("Скачивание завершено!")
            send_toast("Видео загружено", f"{title} успешно скачано.")
            if not self._download_queue and messagebox.askyesno("Готово!",
                                   f"Файл успешно сохранён!\n\nПапка: {folder}\n\nОткрыть папку?"):
                self.open_folder(folder)

        self._check_next_in_queue()

    def _check_next_in_queue(self) -> None:
        if self._download_queue:
            next_task = self._download_queue.pop(0)
            self.after(500, self._start_next_download, next_task)
        else:
            self._is_downloading = False
            self._restore_download_btn()

    def _download_cancelled(self) -> None:
        self._download_queue.clear()
        self._update_queue_label()
        self._is_downloading = False
        self.progress_bar.set(0)
        self._restore_download_btn()
        self.set_status("Загрузка отменена.")

    def _download_error(self, err_msg: str) -> None:
        self.set_status("Ошибка!")
        retry = messagebox.askretrycancel("Ошибка загрузки", f"{err_msg}\n\nПовторить попытку?")
        if retry:
            task = getattr(self, '_current_task', None)
            if task:
                self.after(500, self._start_next_download, task)
                return
        self._check_next_in_queue()


if __name__ == "__main__":
    app = App()
    app.mainloop()
