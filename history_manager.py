import json
import os
from datetime import datetime

class HistoryManager:
    def __init__(self):
        # Определение пути для данных
        if not os.path.exists('data'):
            os.makedirs('data')
        
        self.history_file = os.path.join('data', 'history.json')
        self.settings_file = os.path.join('data', 'settings.json')
        
        self.load_data()

    def load_data(self):
        # Загрузка истории
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.url_history = data.get('url_history', [])
                    self.downloads = data.get('downloads', [])
            except Exception:
                self.url_history = []
                self.downloads = []
        else:
            self.url_history = []
            self.downloads = []
            
        # Загрузка настроек
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except Exception:
                self.settings = self._default_settings()
        else:
            self.settings = self._default_settings()

    def _default_settings(self):
        return {
            "embed_metadata": True,
            "theme": "Dark",
            "default_quality": "—"
        }

    def save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump({
                'url_history': self.url_history,
                'downloads': self.downloads
            }, f, ensure_ascii=False, indent=4)

    def save_settings(self):
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)
            
    # --- Работа с URL ---
    def add_url(self, url):
        url = url.strip()
        if not url: return
        # Избегаем дубликатов, сдвигая в начало
        if url in self.url_history:
            self.url_history.remove(url)
        self.url_history.insert(0, url)
        # Ограничиваем историю 50 ссылками
        self.url_history = self.url_history[:50]
        self.save_history()

    def get_urls(self):
        return self.url_history

    # --- Работа с загрузками ---
    def add_download(self, title, url, file_path, format_str):
        download_record = {
            "title": title,
            "url": url,
            "path": file_path,
            "format": format_str,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.downloads.insert(0, download_record)
        # Ограничиваем историю 100 файлами
        self.downloads = self.downloads[:100]
        self.save_history()

    def get_downloads(self):
        return self.downloads

    def clear_history(self):
        self.downloads = []
        self.url_history = []
        self.save_history()

    # --- Работа с настройками ---
    def get_setting(self, key):
        return self.settings.get(key, self._default_settings().get(key))

    def set_setting(self, key, value):
        self.settings[key] = value
        self.save_settings()
