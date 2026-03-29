import os
import sys
import yt_dlp
import traceback

# Стратегии клиентов YouTube — пробуем по очереди, пока не получим видеоформаты
YOUTUBE_CLIENT_STRATEGIES = [
    {'player_client': ['ios', 'mweb']},
    {'player_client': ['web_creator', 'mweb']},
    {'player_client': ['android', 'web']},
    {'player_client': ['tv_embedded']},
    {'player_client': ['default']},
]


class VideoDownloader:
    def __init__(self):
        # Определяем путь к папке приложения
        self.app_dir = os.path.dirname(os.path.abspath(__file__))

        # Добавляем app_dir в PATH, чтобы yt-dlp нашёл ffmpeg.exe и deno.exe
        if self.app_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = self.app_dir + os.pathsep + os.environ.get('PATH', '')

        # Проверяем наличие ffmpeg
        ffmpeg_path = os.path.join(self.app_dir, 'ffmpeg.exe')
        self.ffmpeg_location = self.app_dir if os.path.isfile(ffmpeg_path) else None

        # Запоминаем последнюю рабочую стратегию
        self._working_strategy_idx = 0

    def _base_opts(self, cookies_file=None, strategy_idx=0):
        """Базовые опции, общие для всех операций."""
        strategy = YOUTUBE_CLIENT_STRATEGIES[strategy_idx % len(YOUTUBE_CLIENT_STRATEGIES)]

        opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'extractor_args': {'youtube': strategy},
            'http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
            'socket_timeout': 30,
        }
        if self.ffmpeg_location:
            opts['ffmpeg_location'] = self.ffmpeg_location
        if cookies_file and os.path.isfile(cookies_file):
            opts['cookiefile'] = cookies_file
        return opts

    def _handle_error(self, err_str):
        """Централизованная обработка типичных ошибок yt-dlp."""
        if 'Could not copy Chrome cookie database' in err_str:
            return (
                '⛔ Ошибка доступа к Chrome Cookies.\n\n'
                'Причина: Браузер Chrome сейчас запущен и блокирует доступ к своим данным.\n\n'
                'Решение:\n'
                '1. ПОЛНОСТЬЮ ЗАКРОЙТЕ CHROME и попробуйте снова.\n'
                '2. Или используйте файл cookies.txt (кнопка "Обзор").'
            )

        if 'Failed to decrypt with DPAPI' in err_str:
            return (
                '⛔ Ошибка расшифровки cookies браузера.\n\n'
                'Windows заблокировал доступ к зашифрованным cookies.\n\n'
                'Решение:\n'
                '1. Используйте файл cookies.txt (экспортируйте расширением для браузера).\n'
                '2. Попробуйте другой браузер (Firefox работает лучше).'
            )

        if 'Sign in to confirm' in err_str or 'bot' in err_str.lower():
            return (
                '🛑 YouTube заблокировал запрос (защита от ботов).\n\n'
                'Решения:\n'
                '1. Экспортируйте cookies.txt из браузера и укажите файл.\n'
                '2. Попробуйте закрыть Chrome и использовать "Cookies из браузера".\n'
                '3. Подождите 5-10 минут — бан по IP обычно временный.'
            )

        if 'Requested format is not available' in err_str or 'No video formats found' in err_str:
            return (
                '⚠️ Запрошенный формат недоступен.\n\n'
                'YouTube ограничивает доступ к видеоформатам без авторизации.\n\n'
                'Решение:\n'
                '1. Экспортируйте cookies.txt и укажите в приложении.\n'
                '2. Или выберите "Только аудио (MP3)" — аудио обычно доступно.'
            )

        return err_str

    def _is_youtube(self, url):
        """Проверяет, является ли URL ссылкой на YouTube."""
        yt_domains = ['youtube.com', 'youtu.be', 'youtube-nocookie.com', 'm.youtube.com']
        return any(d in url.lower() for d in yt_domains)

    def _extract_video_resolutions(self, formats):
        """Извлекает доступные видео-разрешения из списка форматов."""
        available_resolutions = set()
        for f in formats:
            vcodec = f.get('vcodec', 'none')
            height = f.get('height')
            format_note = (f.get('format_note', '') or '').lower()

            if vcodec in ('none', None):
                continue
            if 'storyboard' in format_note or 'images' in str(vcodec):
                continue
            if height and isinstance(height, int) and height >= 144:
                available_resolutions.add(height)

        return sorted(list(available_resolutions), reverse=True)

    def _format_duration(self, seconds):
        """Форматирует секунды в читаемую строку."""
        if not seconds:
            return ""
        seconds = int(seconds)
        hours, remainder = divmod(seconds, 3600)
        mins, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"

    def _resolutions_to_labels(self, resolutions):
        """Превращает список разрешений в красивые лейблы для UI."""
        labels = []
        for res in resolutions:
            if res >= 2160:
                labels.append(f"{res}p (4K)")
            elif res >= 1440:
                labels.append(f"{res}p (2K)")
            elif res >= 1080:
                labels.append(f"{res}p (Full HD)")
            elif res >= 720:
                labels.append(f"{res}p (HD)")
            else:
                labels.append(f"{res}p")
        labels.append("🎵 Только аудио (MP3)")
        return labels if len(labels) > 1 else ["🎵 Только аудио (MP3)"]

    def _try_extract_with_strategies(self, url, cookies_file, browser_cookies, extra_opts=None):
        """Пробует извлечь информацию используя разные YouTube-стратегии."""
        is_yt = self._is_youtube(url)
        strategies_to_try = len(YOUTUBE_CLIENT_STRATEGIES) if is_yt else 1

        best_info = None
        best_resolutions = []

        for attempt in range(strategies_to_try):
            idx = (self._working_strategy_idx + attempt) % len(YOUTUBE_CLIENT_STRATEGIES)
            ydl_opts = self._base_opts(cookies_file, strategy_idx=idx)
            ydl_opts['skip_download'] = True
            ydl_opts['ignore_no_formats_error'] = True
            ydl_opts['extract_flat'] = 'in_playlist'  # Быстрое получение только списка для плейлистов

            if extra_opts:
                ydl_opts.update(extra_opts)

            if browser_cookies:
                ydl_opts['cookiesfrombrowser'] = (browser_cookies,)

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=False)

                    if info_dict is None:
                        continue

                    # Для плейлистов — не пробуем стратегии, берём как есть
                    if info_dict.get('_type') == 'playlist' or 'entries' in info_dict:
                        self._working_strategy_idx = idx
                        return info_dict

                    formats = info_dict.get('formats', [])
                    resolutions = self._extract_video_resolutions(formats)

                    if resolutions:
                        self._working_strategy_idx = idx
                        return info_dict

                    if best_info is None:
                        best_info = info_dict

            except Exception:
                continue

        return best_info

    def fetch_info(self, url, cookies_file=None, browser_cookies=None):
        """
        Извлекает информацию о видео/плейлисте по URL.
        Автоматически определяет тип (одно видео или плейлист).
        """
        info_dict = self._try_extract_with_strategies(url, cookies_file, browser_cookies)

        if info_dict is None:
            return {
                'status': 'error',
                'message': 'Не удалось получить информацию. Ссылка недействительна или видео удалено.'
            }

        # ═══ ПЛЕЙЛИСТ ═══
        if info_dict.get('_type') == 'playlist' or 'entries' in info_dict:
            return self._process_playlist_info(info_dict)

        # ═══ ОДНО ВИДЕО ═══
        return self._process_single_info(info_dict)

    def _process_single_info(self, info_dict):
        """Обрабатывает информацию одного видео."""
        title = info_dict.get('title', 'Без названия')
        duration = info_dict.get('duration', 0)
        thumbnail_url = info_dict.get('thumbnail')
        uploader = info_dict.get('uploader', '')

        formats = info_dict.get('formats', [])
        resolutions = self._extract_video_resolutions(formats)
        format_options = self._resolutions_to_labels(resolutions)

        is_yt = self._is_youtube(info_dict.get('webpage_url', ''))

        return {
            'status': 'success',
            'type': 'video',
            'title': title,
            'uploader': uploader,
            'duration': self._format_duration(duration),
            'thumbnail': thumbnail_url,
            'formats': format_options,
            'no_video_warning': len(resolutions) == 0 and is_yt,
        }

    def _process_playlist_info(self, info_dict):
        """Обрабатывает информацию о плейлисте."""
        entries_raw = info_dict.get('entries', [])

        # Материализуем генератор entries (yt-dlp возвращает генератор)
        entries = []
        for entry in entries_raw:
            if entry is not None:
                entries.append(entry)

        playlist_title = info_dict.get('title', 'Без названия')
        playlist_uploader = info_dict.get('uploader', info_dict.get('channel', ''))
        thumbnail_url = info_dict.get('thumbnails', [{}])[-1].get('url') if info_dict.get('thumbnails') else None

        # Собираем информацию о каждом видео
        video_list = []
        total_duration = 0
        all_resolutions = set()

        for i, entry in enumerate(entries):
            duration = entry.get('duration', 0) or 0
            total_duration += duration

            # Достаём разрешения из форматов
            formats = entry.get('formats', [])
            resolutions = self._extract_video_resolutions(formats)
            all_resolutions.update(resolutions)

            entry_title = entry.get('title', f'Видео {i + 1}')
            entry_thumb = entry.get('thumbnail') or entry.get('thumbnails', [{}])[-1].get('url') if entry.get('thumbnails') else None

            video_list.append({
                'index': i + 1,
                'title': entry_title,
                'duration': self._format_duration(duration),
                'duration_sec': duration,
                'thumbnail': entry_thumb,
                'uploader': entry.get('uploader', ''),
            })

        # Если нет thumbnail у плейлиста — берём от первого видео
        if not thumbnail_url and video_list:
            thumbnail_url = video_list[0].get('thumbnail')

        if not all_resolutions:
            # При extract_flat форматы отсутствуют, даем стандартные опции
            sorted_resolutions = [1080, 720, 480, 360]
        else:
            sorted_resolutions = sorted(list(all_resolutions), reverse=True)
            
        format_options = self._resolutions_to_labels(sorted_resolutions)

        is_yt = self._is_youtube(info_dict.get('webpage_url', '') or '')

        return {
            'status': 'success',
            'type': 'playlist',
            'title': playlist_title,
            'uploader': playlist_uploader,
            'video_count': len(video_list),
            'videos': video_list,
            'total_duration': self._format_duration(total_duration),
            'total_duration_sec': total_duration,
            'thumbnail': thumbnail_url,
            'formats': format_options,
            'no_video_warning': len(sorted_resolutions) == 0 and is_yt,
        }

    def download(self, url, format_selection, output_path, cookies_file=None,
                 browser_cookies=None, progress_callback=None,
                 finished_callback=None, error_callback=None,
                 playlist_item_callback=None):
        """
        Запускает скачивание выбранного формата.
        playlist_item_callback(current, total, title) — вызывается при начале каждого видео в плейлисте.
        """
        ydl_opts = self._base_opts(cookies_file, strategy_idx=self._working_strategy_idx)
        ydl_opts['outtmpl'] = os.path.join(output_path, '%(title)s.%(ext)s')
        # Для плейлистов — создаём подпапку
        ydl_opts['outtmpl'] = os.path.join(output_path, '%(playlist_title,)s', '%(title)s.%(ext)s')
        # Если не плейлист, шаблон %(playlist_title,)s будет пустым — файлы в корне
        ydl_opts['ignoreerrors'] = True  # Пропускать ошибки отдельных видео в плейлисте

        if browser_cookies:
            ydl_opts['cookiesfrombrowser'] = (browser_cookies,)

        # Счётчик для плейлистов
        playlist_state = {'current': 0, 'total': 0}

        if progress_callback:
            def hooks(d):
                if d['status'] == 'downloading':
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)

                    percent = downloaded / total if total > 0 else 0.0

                    # Для плейлистов — считаем общий прогресс
                    if playlist_state['total'] > 0:
                        base = (playlist_state['current'] - 1) / playlist_state['total']
                        item_share = 1.0 / playlist_state['total']
                        percent = base + percent * item_share

                    speed_mb = speed / 1024 / 1024 if speed else 0
                    prefix = ""
                    if playlist_state['total'] > 0:
                        prefix = f"[{playlist_state['current']}/{playlist_state['total']}] "
                    info_text = f"{prefix}⬇ {speed_mb:.1f} МБ/с  |  Осталось: {eta}с"
                    progress_callback(percent, info_text)
                elif d['status'] == 'finished':
                    if playlist_state['total'] > 0:
                        p = playlist_state['current'] / playlist_state['total']
                        progress_callback(p, f"[{playlist_state['current']}/{playlist_state['total']}] ⏳ Обработка...")
                    else:
                        progress_callback(1.0, "⏳ Обработка...")
            ydl_opts['progress_hooks'] = [hooks]

        # Postprocessor hook для отслеживания начала новых видео в плейлисте
        class PlaylistTracker(yt_dlp.postprocessor.PostProcessor):
            def run(self, info):
                idx = info.get('playlist_index') or info.get('playlist_autonumber')
                count = info.get('n_entries') or info.get('playlist_count', 0)
                title = info.get('title', '')
                if idx and count:
                    playlist_state['current'] = idx
                    playlist_state['total'] = count
                    if playlist_item_callback:
                        playlist_item_callback(idx, count, title)
                return [], info

        is_audio = "аудио" in format_selection.lower() or "audio" in format_selection.lower()

        if is_audio:
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        else:
            res_val = format_selection.split('p')[0].strip()
            ydl_opts['format'] = (
                f"bestvideo[height<={res_val}]+bestaudio/"
                f"bestvideo[height<={res_val}]+bestaudio[ext=m4a]/"
                f"best[height<={res_val}]/"
                f"bestvideo+bestaudio/best"
            )
            ydl_opts['merge_output_format'] = 'mp4'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.add_post_processor(PlaylistTracker())
                ydl.download([url])
            if finished_callback:
                finished_callback()
        except Exception as e:
            msg = self._handle_error(str(e))
            if error_callback:
                error_callback(msg)
