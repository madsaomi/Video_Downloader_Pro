import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List


class HistoryManager:
    def __init__(self) -> None:
        app_data = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')),
            'VideoDownloaderPro',
        )
        os.makedirs(app_data, exist_ok=True)

        self.history_file: str = os.path.join(app_data, 'history.json')
        self.settings_file: str = os.path.join(app_data, 'settings.json')

        old_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        if os.path.isdir(old_data):
            for fname in ('history.json', 'settings.json'):
                old_file = os.path.join(old_data, fname)
                new_file = os.path.join(app_data, fname)
                if os.path.isfile(old_file) and not os.path.isfile(new_file):
                    try:
                        shutil.copy2(old_file, new_file)
                    except Exception:
                        pass

        self.url_history: List[str] = []
        self.downloads: List[dict] = []
        self.settings: Dict[str, Any] = {}
        self.load_data()

    def load_data(self) -> None:
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

        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except Exception:
                self.settings = self._default_settings()
        else:
            self.settings = self._default_settings()

    def _default_settings(self) -> Dict[str, Any]:
        return {
            "embed_metadata": True,
            "theme": "Dark",
            "preferred_quality": "— (не задано)",
            "rate_limit": 0,
            "notifications_enabled": True,
        }

    def save_history(self) -> None:
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump({
                'url_history': self.url_history,
                'downloads': self.downloads,
            }, f, ensure_ascii=False, indent=4)

    def save_settings(self) -> None:
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def add_url(self, url: str) -> None:
        url = url.strip()
        if not url:
            return
        if url in self.url_history:
            self.url_history.remove(url)
        self.url_history.insert(0, url)
        self.url_history = self.url_history[:50]
        self.save_history()

    def get_urls(self) -> List[str]:
        return self.url_history

    def add_download(self, title: str, url: str, file_path: str, format_str: str) -> None:
        download_record = {
            "title": title,
            "url": url,
            "path": file_path,
            "format": format_str,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.downloads.insert(0, download_record)
        self.downloads = self.downloads[:100]
        self.save_history()

    def get_downloads(self) -> List[dict]:
        return self.downloads

    def clear_history(self) -> None:
        self.downloads = []
        self.url_history = []
        self.save_history()

    def get_setting(self, key: str, default: Any = None) -> Any:
        if default is not None:
            return self.settings.get(key, default)
        return self.settings.get(key, self._default_settings().get(key))

    def set_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.save_settings()
