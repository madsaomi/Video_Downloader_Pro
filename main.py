import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import io
import requests
from PIL import Image
from downloader import VideoDownloader

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

ACCENT_COLOR = "#7C3AED"
ACCENT_HOVER = "#6D28D9"
SUCCESS_COLOR = "#10B981"
SUCCESS_HOVER = "#059669"
BG_DARK = "#0F0F14"
CARD_BG = "#1A1A24"
CARD_BORDER = "#2A2A3A"
TEXT_PRIMARY = "#F1F1F6"
TEXT_SECONDARY = "#9CA3AF"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🎬 Video Downloader Pro")
        self.geometry("780x820")
        self.minsize(650, 700)
        self.configure(fg_color=BG_DARK)
        self.downloader = VideoDownloader()
        self.fetched_info = None
        self._thumb_image = None  # prevent GC

        # --- Grid ---
        self.grid_columnconfigure(0, weight=1)

        # ═══ HEADER ═══
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(24, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="🎬  Video Downloader Pro",
            font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w")

        subtitle_frame = ctk.CTkFrame(header, fg_color="transparent")
        subtitle_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))

        ctk.CTkLabel(
            subtitle_frame, text="YouTube • TikTok • Instagram • VK и еще",
            font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY
        ).pack(side="left")

        sites_btn = ctk.CTkButton(
            subtitle_frame, text="1000+ сайтов", font=ctk.CTkFont(size=13, underline=True),
            text_color=ACCENT_COLOR, fg_color="transparent", hover_color=BG_DARK,
            width=0, height=0, command=self.show_supported_sites
        )
        sites_btn.pack(side="left", padx=(5, 0))

        # ═══ URL CARD ═══
        url_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color=CARD_BORDER)
        url_card.grid(row=1, column=0, padx=24, pady=8, sticky="ew")
        url_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(url_card, text="🔗  Ссылка на видео", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT_PRIMARY).grid(row=0, column=0, columnspan=3, padx=16, pady=(14, 6), sticky="w")

        self.url_entry = ctk.CTkEntry(url_card, placeholder_text="Вставьте ссылку...",
                                      height=40, font=ctk.CTkFont(size=14), corner_radius=8)
        self.url_entry.grid(row=1, column=0, columnspan=2, padx=(16, 8), pady=(0, 14), sticky="ew")

        self.paste_btn = ctk.CTkButton(url_card, text="📋 Вставить", command=self.paste_url,
                                       width=110, height=40, corner_radius=8,
                                       fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER)
        self.paste_btn.grid(row=1, column=2, padx=(0, 16), pady=(0, 14))

        # ═══ COOKIES CARD ═══
        cookies_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color=CARD_BORDER)
        cookies_card.grid(row=2, column=0, padx=24, pady=8, sticky="ew")
        cookies_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cookies_card, text="🍪  Cookies (опционально — для 18+ и закрытых видео)",
                     font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY
                     ).grid(row=0, column=0, columnspan=3, padx=16, pady=(12, 6), sticky="w")

        self.cookies_entry = ctk.CTkEntry(cookies_card, placeholder_text="Путь к файлу cookies.txt",
                                          height=36, corner_radius=8)
        self.cookies_entry.grid(row=1, column=0, columnspan=2, padx=(16, 8), pady=(0, 12), sticky="ew")

        self.cookies_btn = ctk.CTkButton(cookies_card, text="📂 Обзор", command=self.browse_cookies,
                                         width=100, height=36, corner_radius=8,
                                         fg_color="#374151", hover_color="#4B5563")
        self.cookies_btn.grid(row=1, column=2, padx=(0, 16), pady=(0, 6))

        # Browser cookies option
        browser_frame = ctk.CTkFrame(cookies_card, fg_color="transparent")
        browser_frame.grid(row=2, column=0, columnspan=3, padx=16, pady=(0, 12), sticky="w")

        self.use_browser_cookies = ctk.CTkCheckBox(browser_frame,
            text="Использовать cookies из браузера (рекомендуется для YouTube)",
            font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY,
            checkbox_width=20, checkbox_height=20, corner_radius=4)
        self.use_browser_cookies.pack(side="left", padx=(0, 10))

        self.browser_combo = ctk.CTkComboBox(browser_frame,
            values=["chrome", "edge", "firefox", "opera", "brave"],
            width=110, height=28, corner_radius=6, font=ctk.CTkFont(size=12))
        self.browser_combo.set("chrome")
        self.browser_combo.pack(side="left")

        # ═══ GET INFO BUTTON ═══
        self.info_btn = ctk.CTkButton(self, text="🔍  Получить информацию", command=self.start_get_info,
                                      height=44, corner_radius=10, font=ctk.CTkFont(size=15, weight="bold"),
                                      fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER)
        self.info_btn.grid(row=3, column=0, padx=24, pady=12, sticky="ew")

        # ═══ PREVIEW CARD ═══
        self.preview_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12,
                                         border_width=1, border_color=CARD_BORDER)
        self.preview_card.grid(row=4, column=0, padx=24, pady=8, sticky="ew")
        self.preview_card.grid_columnconfigure(1, weight=1)

        self.thumb_label = ctk.CTkLabel(self.preview_card, text="  Превью  \n  появится  \n  здесь  ",
                                        width=220, height=124, corner_radius=8,
                                        fg_color="#252535", text_color=TEXT_SECONDARY,
                                        font=ctk.CTkFont(size=12))
        self.thumb_label.grid(row=0, column=0, rowspan=3, padx=14, pady=14)

        self.video_title_label = ctk.CTkLabel(self.preview_card, text="Название: —",
                                              wraplength=380, justify="left",
                                              font=ctk.CTkFont(size=14, weight="bold"),
                                              text_color=TEXT_PRIMARY)
        self.video_title_label.grid(row=0, column=1, padx=10, pady=(14, 4), sticky="nw")

        self.duration_label = ctk.CTkLabel(self.preview_card, text="",
                                           font=ctk.CTkFont(size=12), text_color=TEXT_SECONDARY)
        self.duration_label.grid(row=1, column=1, padx=10, pady=0, sticky="nw")

        # Format selection row
        fmt_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        fmt_frame.grid(row=2, column=1, padx=10, pady=(4, 14), sticky="sw")

        ctk.CTkLabel(fmt_frame, text="Качество:", font=ctk.CTkFont(size=13),
                     text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 8))

        self.format_combo = ctk.CTkComboBox(fmt_frame, values=["—"], width=220,
                                            height=32, corner_radius=8, state="readonly",
                                            font=ctk.CTkFont(size=13))
        self.format_combo.pack(side="left")

        # ═══ OUTPUT FOLDER ═══
        folder_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12,
                                   border_width=1, border_color=CARD_BORDER)
        folder_card.grid(row=5, column=0, padx=24, pady=8, sticky="ew")
        folder_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(folder_card, text="📁  Папка сохранения",
                     font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY
                     ).grid(row=0, column=0, columnspan=3, padx=16, pady=(12, 6), sticky="w")

        self.folder_entry = ctk.CTkEntry(folder_card, height=36, corner_radius=8)
        self.folder_entry.grid(row=1, column=0, columnspan=2, padx=(16, 8), pady=(0, 12), sticky="ew")

        default_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.folder_entry.insert(0, default_dir)

        self.folder_btn = ctk.CTkButton(folder_card, text="📂 Изменить", command=self.browse_folder,
                                        width=100, height=36, corner_radius=8,
                                        fg_color="#374151", hover_color="#4B5563")
        self.folder_btn.grid(row=1, column=2, padx=(0, 16), pady=(0, 12))

        # ═══ DOWNLOAD BUTTON ═══
        self.download_btn = ctk.CTkButton(self, text="⬇️  Скачать", command=self.start_download,
                                          height=48, corner_radius=10,
                                          font=ctk.CTkFont(size=16, weight="bold"),
                                          fg_color=SUCCESS_COLOR, hover_color=SUCCESS_HOVER)
        self.download_btn.grid(row=6, column=0, padx=24, pady=14, sticky="ew")
        self.download_btn.configure(state="disabled")

        # ═══ PROGRESS ═══
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=7, column=0, padx=24, pady=(4, 20), sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(progress_frame, text="⏳ Ожидание...",
                                         font=ctk.CTkFont(size=13), text_color=TEXT_SECONDARY)
        self.status_label.grid(row=0, column=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=10, corner_radius=5,
                                                progress_color=ACCENT_COLOR)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.progress_bar.set(0)

    # ─── ACTIONS ───

    def show_supported_sites(self):
        sites_window = ctk.CTkToplevel(self)
        sites_window.title("1500+ Поддерживаемых платформ")
        sites_window.geometry("500x650")
        sites_window.resizable(False, False)
        sites_window.attributes('-topmost', True)

        sites_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 650) // 2
        sites_window.geometry(f"+{x}+{y}")

        title_lbl = ctk.CTkLabel(sites_window, text="🌐 Поддерживаемые сайты", font=ctk.CTkFont(size=18, weight="bold"))
        title_lbl.pack(pady=(20, 5))

        desc_lbl = ctk.CTkLabel(sites_window, text="Без учета 18+ сайтов (они скрыты фильтром)", text_color="gray")
        desc_lbl.pack(pady=(0, 10))

        textbox = ctk.CTkTextbox(sites_window, width=460, height=480, font=ctk.CTkFont(size=13), corner_radius=8)
        textbox.pack(padx=20, pady=5, fill="both", expand=True)
        
        # Динамически получаем все экстракторы из yt-dlp
        import yt_dlp.extractor
        extractors = yt_dlp.extractor.gen_extractors()
        
        adult_keywords = ['porn', 'xnxx', 'xvideos', 'tube8', 'hentai', 'spank', 'cam', 'sex', 'bitch', 'boob', 'nude', 'strip', 'erotic', 'adult']
        
        clean_sites = set()
        for e in extractors:
            # 1. Фильтр по встроенному флагу age_limit
            if getattr(e, 'age_limit', 0) == 18:
                continue
            
            # 2. Фильтр по названию
            name = e.IE_NAME.lower()
            if any(k in name for k in adult_keywords):
                continue
                
            # Используем описание если есть, иначе имя
            site_name = getattr(e, 'IE_DESC', None)
            if not site_name:
                site_name = e.IE_NAME.split(':')[0].capitalize()
                
            clean_sites.add(site_name)

        # Сортируем (без учета регистра) и убираем пустышки
        sorted_sites = sorted([str(s).strip() for s in clean_sites if s and str(s).strip() and not str(s).startswith('Generic')], key=lambda x: x.lower())

        text_content = "⭐ ТОП ПОПУЛЯРНЫХ:\n"
        text_content += "  • YouTube (Видео, Shorts, Плейлисты)\n"
        text_content += "  • TikTok, Instagram, ВКонтакте\n"
        text_content += "  • Twitter (X), Facebook, Reddit\n"
        text_content += "  • Twitch, Telegram, SoundCloud\n\n"
        text_content += f"─── ПОЛНЫЙ КАТАЛОГ ({len(sorted_sites)} САЙТОВ) ───\n"
        
        current_letter = ""
        for site in sorted_sites:
            first_char = site[0].upper()
            # Если не буква латиницы/кириллицы (например, цифра)
            if not first_char.isalpha():
                first_char = "# (Цифры и символы)"
            
            if first_char != current_letter:
                current_letter = first_char
                text_content += f"\n[ {current_letter} ] {'—'*25}\n"
                
            text_content += f"  • {site}\n"

        textbox.insert("0.0", text_content)
        textbox.configure(state="disabled")

        close_btn = ctk.CTkButton(sites_window, text="Отлично!", command=sites_window.destroy, width=150)
        close_btn.pack(pady=15)

    def paste_url(self):
        try:
            text = self.clipboard_get()
            self.url_entry.delete(0, 'end')
            self.url_entry.insert(0, text.strip())
        except Exception:
            pass

    def browse_cookies(self):
        f = filedialog.askopenfilename(title="Выберите cookies.txt",
                                       filetypes=(("Text", "*.txt"), ("All", "*.*")))
        if f:
            self.cookies_entry.delete(0, 'end')
            self.cookies_entry.insert(0, f)

    def browse_folder(self):
        d = filedialog.askdirectory(title="Папка сохранения")
        if d:
            self.folder_entry.delete(0, 'end')
            self.folder_entry.insert(0, d)

    def set_status(self, text):
        self.status_label.configure(text=text)

    def load_image_from_url(self, url):
        try:
            r = requests.get(url, timeout=8)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content))
            w, h = img.size
            new_w = 220
            new_h = int(new_w / (w / h))
            return ctk.CTkImage(light_image=img, dark_image=img, size=(new_w, new_h))
        except Exception:
            return None

    # ─── GET INFO ───

    def start_get_info(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Ошибка", "Введите ссылку на видео!")
            return
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("Ошибка", "Ссылка должна начинаться с http:// или https://")
            return

        cookies = self.cookies_entry.get().strip()
        browser = None
        if self.use_browser_cookies.get():
            browser = self.browser_combo.get()

        self.info_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self.set_status("🔄 Получение информации...")
        self.progress_bar.set(0)

        threading.Thread(target=self._get_info_thread, args=(url, cookies, browser), daemon=True).start()

    def _get_info_thread(self, url, cookies, browser):
        info = self.downloader.fetch_info(url, cookies if cookies else None, browser)
        self.after(0, self._info_fetched, info)

    def _info_fetched(self, info):
        self.info_btn.configure(state="normal")

        if info.get('status') == 'error':
            messagebox.showerror("Ошибка", info.get('message', 'Неизвестная ошибка'))
            self.set_status("❌ Ошибка получения информации.")
            return

        self.fetched_info = info
        title = info.get('title', '—')
        formats = info.get('formats', ['—'])
        thumb_url = info.get('thumbnail')
        duration = info.get('duration', '')

        self.video_title_label.configure(text=title)
        self.duration_label.configure(text=f"⏱ {duration}" if duration else "")

        if formats:
            self.format_combo.configure(values=formats)
            self.format_combo.set(formats[0])
            self.download_btn.configure(state="normal")

        if thumb_url:
            self.set_status("🖼 Загрузка превью...")
            # Load thumbnail in thread
            threading.Thread(target=self._load_thumb, args=(thumb_url,), daemon=True).start()
        else:
            self.set_status("✅ Готово! Выберите качество и нажмите «Скачать».")

    def _load_thumb(self, url):
        img = self.load_image_from_url(url)
        self.after(0, self._set_thumb, img)

    def _set_thumb(self, img):
        if img:
            self._thumb_image = img  # prevent garbage collection
            self.thumb_label.configure(image=img, text="")
        else:
            self.thumb_label.configure(text="Превью\nнедоступно")
        self.set_status("✅ Готово! Выберите качество и нажмите «Скачать».")

    # ─── DOWNLOAD ───

    def start_download(self):
        url = self.url_entry.get().strip()
        cookies = self.cookies_entry.get().strip()
        fmt = self.format_combo.get()
        out_dir = self.folder_entry.get().strip()
        browser = None
        if self.use_browser_cookies.get():
            browser = self.browser_combo.get()

        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать папку:\n{e}")
                return

        self.download_btn.configure(state="disabled")
        self.info_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.set_status("⬇️ Начало скачивания...")

        threading.Thread(target=self._download_thread,
                         args=(url, fmt, out_dir, cookies if cookies else None, browser),
                         daemon=True).start()

    def _download_thread(self, url, fmt, out_dir, cookies, browser):
        def progress_cb(percent, text):
            self.after(0, self.progress_bar.set, percent)
            self.after(0, self.set_status, f"⬇️ {percent*100:.0f}%  {text}")

        def done_cb():
            self.after(0, self._download_finished)

        def err_cb(msg):
            self.after(0, self._download_error, msg)

        try:
            self.downloader.download(url, fmt, out_dir, cookies, browser, progress_cb, done_cb, err_cb)
        except Exception as e:
            err_cb(str(e))

    def _download_finished(self):
        self.progress_bar.set(1.0)
        self.set_status("✅ Скачивание завершено!")
        self.download_btn.configure(state="normal")
        self.info_btn.configure(state="normal")
        folder = self.folder_entry.get()
        messagebox.showinfo("Готово! 🎉", f"Файл успешно сохранён в:\n{folder}")

    def _download_error(self, err_msg):
        self.set_status("❌ Ошибка!")
        self.download_btn.configure(state="normal")
        self.info_btn.configure(state="normal")
        
        # downloader.py now handles detailed error explanations.
        # We just show them in the popup.
        messagebox.showerror("Ошибка загрузки", err_msg)


if __name__ == "__main__":
    app = App()
    app.mainloop()
