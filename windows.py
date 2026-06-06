import customtkinter as ctk
import threading
from typing import TYPE_CHECKING, List, Tuple

from ui_components import (
    ACCENT_COLOR, ACCENT_HOVER, TEXT_PRIMARY, TEXT_SECONDARY,
    CARD_BG, CARD_BG_ALT, SECONDARY_BTN,
    SECONDARY_BTN_HOVER, SURFACE_DIM,
    show_context_menu,
)

if TYPE_CHECKING:
    from app import App


class SearchWindow(ctk.CTkToplevel):
    def __init__(self, parent_app: "App", info: dict) -> None:
        super().__init__(parent_app)
        self.parent_app = parent_app
        self._search_ctk_images: List = []
        self._search_thumb_labels: List[Tuple] = []
        self._search_closed: bool = False

        videos = info.get("videos", [])
        count = len(videos)

        self.title(f"Результаты поиска ({count})")
        self.geometry("750x600")
        self.attributes("-topmost", True)
        self.update_idletasks()
        x = parent_app.winfo_x() + max(0, parent_app.winfo_width() - 750) // 2
        y = parent_app.winfo_y() + max(0, parent_app.winfo_height() - 600) // 2
        self.geometry(f"+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        ctk.CTkLabel(
            self, text="Результаты поиска YouTube",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_PRIMARY,
        ).pack(pady=(16, 8))

        scroll_frame = ctk.CTkScrollableFrame(self, fg_color=CARD_BG, corner_radius=10)
        scroll_frame.pack(padx=16, pady=8, fill="both", expand=True)
        scroll_frame.grid_columnconfigure(0, weight=1)

        for i, video in enumerate(videos):
            row_bg = CARD_BG_ALT if i % 2 == 0 else CARD_BG
            row_frame = ctk.CTkFrame(scroll_frame, fg_color=row_bg, corner_radius=6)
            row_frame.grid(row=i, column=0, sticky="ew", pady=2, padx=4)
            row_frame.grid_columnconfigure(1, weight=1)

            thumb_lbl = ctk.CTkLabel(row_frame, text="", width=80, height=45, fg_color=SURFACE_DIM, corner_radius=4)
            thumb_lbl.grid(row=0, column=0, padx=10, pady=8)

            thumb_url = video.get("thumbnail")
            if thumb_url:
                self._search_thumb_labels.append((thumb_lbl, thumb_url))

            title_text = video.get("title", "—")
            info_text = f"{video.get('uploader', '—')}  |  {video.get('duration', '—')}"

            text_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            text_frame.grid(row=0, column=1, sticky="w", padx=10, pady=8)
            ctk.CTkLabel(
                text_frame, text=title_text,
                font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_PRIMARY,
                anchor="w", wraplength=400,
            ).pack(anchor="w")
            ctk.CTkLabel(
                text_frame, text=info_text,
                font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY, anchor="w",
            ).pack(anchor="w")

            btn = ctk.CTkButton(
                row_frame, text="Выбрать", width=90,
                fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER,
                command=lambda u=video.get("url"): self._select_result(u),
            )
            btn.grid(row=0, column=2, padx=10, pady=8)

        ctk.CTkButton(
            self, text="Закрыть", width=120,
            fg_color=SECONDARY_BTN, hover_color=SECONDARY_BTN_HOVER,
            command=self._on_close,
        ).pack(pady=12)

        threading.Thread(target=self._load_thumbs, daemon=True).start()

    def _on_close(self) -> None:
        self._search_closed = True
        self._search_ctk_images.clear()
        self.destroy()

    def _load_thumbs(self) -> None:
        for lbl, url in self._search_thumb_labels:
            if getattr(self, '_search_closed', False):
                return
            try:
                img = self.parent_app.load_image_from_url(url)
                if img:
                    self._search_ctk_images.append(img)
                    self.after(0, lambda ll=lbl, ii=img: ll.configure(image=ii, text="") if ll.winfo_exists() else None)
            except Exception:
                pass

    def _select_result(self, url: str) -> None:
        self.parent_app.url_entry.set(url)
        self._on_close()
        self.parent_app.start_get_info()


class PlaylistWindow(ctk.CTkToplevel):
    def __init__(self, parent_app: "App", info: dict) -> None:
        super().__init__(parent_app)
        self.parent_app = parent_app

        videos = info.get("videos", [])
        count = info.get("video_count", len(videos))

        self.title(f"Плейлист: {info.get('title', 'Без названия')}")
        self.geometry("650x600")
        self.attributes("-topmost", True)
        self.update_idletasks()
        x = parent_app.winfo_x() + max(0, parent_app.winfo_width() - 650) // 2
        y = parent_app.winfo_y() + max(0, parent_app.winfo_height() - 600) // 2
        self.geometry(f"+{x}+{y}")

        header_text = f"{info.get('title', 'Плейлист')}  ({count} видео)"
        ctk.CTkLabel(
            self, text=header_text,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_PRIMARY, wraplength=600,
        ).pack(padx=20, pady=(16, 4))

        total_dur = info.get("total_duration", "")
        if total_dur:
            ctk.CTkLabel(
                self,
                text=f"Общая длительность: {total_dur}  •  Автор: {info.get('uploader', '—')}",
                font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
            ).pack(padx=20, pady=(0, 8))

        scroll_frame = ctk.CTkScrollableFrame(self, fg_color=CARD_BG, corner_radius=10, height=420)
        scroll_frame.pack(padx=16, pady=8, fill="both", expand=True)
        scroll_frame.grid_columnconfigure(1, weight=1)

        if not videos:
            ctk.CTkLabel(scroll_frame, text="Нет видео для отображения",
                         font=ctk.CTkFont(size=14), text_color=TEXT_SECONDARY).pack(pady=40)
        else:
            for i, video in enumerate(videos):
                row_bg = CARD_BG_ALT if i % 2 == 0 else CARD_BG
                row_frame = ctk.CTkFrame(scroll_frame, fg_color=row_bg, corner_radius=6, height=42)
                row_frame.grid(row=i, column=0, columnspan=3, sticky="ew", pady=1, padx=4)
                row_frame.grid_columnconfigure(1, weight=1)
                row_frame.grid_propagate(False)

                idx_color = ACCENT_COLOR if i < 3 else TEXT_SECONDARY
                ctk.CTkLabel(
                    row_frame, text=f"{video['index']:>3}.",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=idx_color, width=40,
                ).grid(row=0, column=0, padx=(10, 6), pady=8)

                title_text = video.get("title", "—")
                if len(title_text) > 60:
                    title_text = title_text[:57] + "..."
                ctk.CTkLabel(
                    row_frame, text=title_text,
                    font=ctk.CTkFont(size=12), text_color=TEXT_PRIMARY, anchor="w",
                ).grid(row=0, column=1, padx=4, pady=8, sticky="w")

                uploader = video.get("uploader", "")
                if uploader:
                    if len(uploader) > 15:
                        uploader = uploader[:12] + "..."
                    ctk.CTkLabel(
                        row_frame, text=uploader,
                        font=ctk.CTkFont(size=11), text_color=TEXT_SECONDARY, width=100,
                    ).grid(row=0, column=2, padx=4, pady=8)

                dur = video.get("duration", "")
                if dur:
                    ctk.CTkLabel(
                        row_frame, text=dur,
                        font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY, width=60,
                    ).grid(row=0, column=3, padx=(4, 12), pady=8)

        ctk.CTkButton(self, text="Закрыть", width=120, command=self.destroy).pack(pady=12)


class SupportedSitesWindow(ctk.CTkToplevel):
    def __init__(self, parent_app: "App") -> None:
        super().__init__(parent_app)
        self.parent_app = parent_app

        self.title("1500+ Поддерживаемых платформ")
        self.geometry("500x650")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.update_idletasks()
        x = parent_app.winfo_x() + max(0, parent_app.winfo_width() - 500) // 2
        y = parent_app.winfo_y() + max(0, parent_app.winfo_height() - 650) // 2
        self.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            self, text="Поддерживаемые сайты",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self, text="Загрузка списка сайтов...",
            text_color="gray",
        ).pack(pady=(0, 10))

        textbox = ctk.CTkTextbox(self, width=460, height=480, font=ctk.CTkFont(size=13), corner_radius=8)
        textbox.pack(padx=20, pady=5, fill="both", expand=True)

        self.after(100, self._load_sites_in_thread, textbox)

        ctk.CTkButton(self, text="Отлично!", command=self.destroy, width=150).pack(pady=15)

    def _load_sites_in_thread(self, textbox: ctk.CTkTextbox) -> None:
        def load() -> None:
            import yt_dlp.extractor
            extractors = yt_dlp.extractor.gen_extractors()

            adult_keywords = [
                "porn", "xnxx", "xvideos", "tube8", "hentai", "spank",
                "cam", "sex", "bitch", "boob", "nude", "strip", "erotic", "adult",
            ]

            clean_sites = set()
            for e in extractors:
                if getattr(e, "age_limit", 0) == 18:
                    continue
                name = e.IE_NAME.lower()
                if any(k in name for k in adult_keywords):
                    continue
                site_name = getattr(e, "IE_DESC", None)
                if not site_name:
                    site_name = e.IE_NAME.split(":")[0].capitalize()
                clean_sites.add(site_name)

            sorted_sites = sorted(
                [
                    str(s).strip()
                    for s in clean_sites
                    if s and str(s).strip() and not str(s).startswith("Generic")
                ],
                key=lambda x: x.lower(),
            )

            text_content = "ТОП ПОПУЛЯРНЫХ:\n"
            text_content += "  * YouTube (Видео, Shorts, Плейлисты)\n"
            text_content += "  * TikTok, Instagram, VK\n"
            text_content += "  * Twitter (X), Facebook, Reddit\n"
            text_content += "  * Twitch, Telegram, SoundCloud\n\n"
            text_content += f"--- ПОЛНЫЙ КАТАЛОГ ({len(sorted_sites)} САЙТОВ) ---\n"

            current_letter = ""
            for site in sorted_sites:
                first_char = site[0].upper()
                if not first_char.isalpha():
                    first_char = "#"
                if first_char != current_letter:
                    current_letter = first_char
                    text_content += f"\n[{current_letter}]\n"
                text_content += f"  * {site}\n"

            self.after(0, lambda t=textbox: self._display_sites(t, text_content) if t.winfo_exists() else None)

        threading.Thread(target=load, daemon=True).start()

    def _display_sites(self, textbox: ctk.CTkTextbox, text_content: str) -> None:
        textbox.delete("0.0", "end")
        textbox.insert("0.0", text_content)
        textbox.configure(state="disabled")
        textbox._textbox.bind("<Button-3>", show_context_menu)
