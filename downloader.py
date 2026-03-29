import os
import sys
import yt_dlp
import traceback

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

    def _base_opts(self, cookies_file=None):
        """Базовые опции, общие для всех операций."""
        opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        if self.ffmpeg_location:
            opts['ffmpeg_location'] = self.ffmpeg_location
        if cookies_file and os.path.isfile(cookies_file):
            opts['cookiefile'] = cookies_file
        return opts

    def _handle_error(self, err_str):
        """Централизованная обработка типичных ошибок yt-dlp."""
        # Ошибка блокировки Chrome cookies
        if 'Could not copy Chrome cookie database' in err_str:
            return (
                '⛔ Ошибка доступа к Chrome Cookies.\n\n'
                'Причина: Браузер Chrome сейчас запущен и блокирует доступ к своим данным.\n\n'
                'Решение:\n'
                '1. ПОЛНОСТЬЮ ЗАКРОЙТЕ CHROME и попробуйте снова.\n'
                '2. Или используйте файл cookies.txt (кнопка "Обзор").'
            )
        
        # Ошибка 'Sign in to confirm'
        if 'Sign in to confirm' in err_str or 'bot' in err_str.lower():
            return (
                '🛑 YouTube заблокировал запрос (защита от ботов).\n\n'
                'Решения:\n'
                '1. Попробуйте закрыть Chrome и использовать "Cookies из браузера".\n'
                '2. Экспортируйте cookies.txt из браузера и укажите файл.\n'
                '3. Подождите 5-10 минут — бан по IP обычно временный.'
            )

        # Ошибка 'Requested format is not available'
        if 'Requested format is not available' in err_str or 'No video formats found' in err_str:
            return (
                '⚠️ Видеоформаты не найдены (доступно только аудио).\n\n'
                'Возможные причины:\n'
                '• YouTube заблокировал ваш IP запрос (бот-защита).\n'
                '• Видео защищено или имеет возрастное ограничение.\n\n'
                'Решение: Попробуйте использовать cookies или подождите 5-10 минут.'
            )

        return err_str

    def fetch_info(self, url, cookies_file=None, browser_cookies=None):
        """
        Извлекает информацию о видео по URL:
        название, ссылка на превью, список форматов.
        """
        ydl_opts = self._base_opts(cookies_file)
        ydl_opts['skip_download'] = True
        ydl_opts['ignore_no_formats_error'] = True 

        if browser_cookies:
            ydl_opts['cookiesfrombrowser'] = (browser_cookies,)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

                if info_dict is None:
                    return {
                        'status': 'error',
                        'message': 'Не удалось получить информацию. Ссылка недействительна или видео удалено.'
                    }

                title = info_dict.get('title', 'Без названия')
                duration = info_dict.get('duration', 0)
                thumbnail_url = info_dict.get('thumbnail')
                uploader = info_dict.get('uploader', '')

                # Извлекаем все форматы
                formats = info_dict.get('formats', [])

                # Фильтруем ТОЛЬКО настоящие видеоформаты
                available_resolutions = set()
                for f in formats:
                    vcodec = f.get('vcodec', 'none')
                    height = f.get('height')
                    format_note = (f.get('format_note', '') or '').lower()

                    # Пропускаем: аудио-only, картинки, сториборды
                    if vcodec in ('none', None):
                        continue
                    if 'storyboard' in format_note or 'images' in str(vcodec):
                        continue
                    if height and isinstance(height, int) and height >= 144:
                        available_resolutions.add(height)

                # Сортируем от большего к меньшему
                sorted_resolutions = sorted(list(available_resolutions), reverse=True)

                # Формируем список для UI
                format_options = []
                for res in sorted_resolutions:
                    if res >= 2160: label = f"{res}p (4K)"
                    elif res >= 1440: label = f"{res}p (2K)"
                    elif res >= 1080: label = f"{res}p (Full HD)"
                    elif res >= 720: label = f"{res}p (HD)"
                    else: label = f"{res}p"
                    format_options.append(label)

                format_options.append("🎵 Только аудио (MP3)")

                if not sorted_resolutions:
                    format_options = ["🎵 Только аудио (MP3)"]

                duration_str = ""
                if duration:
                    mins, secs = divmod(int(duration), 60)
                    hours, mins = divmod(mins, 60)
                    duration_str = f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{mins}:{secs:02d}"

                return {
                    'status': 'success',
                    'title': title,
                    'uploader': uploader,
                    'duration': duration_str,
                    'thumbnail': thumbnail_url,
                    'formats': format_options
                }

        except Exception as e:
            msg = self._handle_error(str(e))
            return {'status': 'error', 'message': msg}

    def download(self, url, format_selection, output_path, cookies_file=None,
                 browser_cookies=None, progress_callback=None,
                 finished_callback=None, error_callback=None):
        """
        Запускает скачивание выбранного формата.
        """
        ydl_opts = self._base_opts(cookies_file)
        ydl_opts['outtmpl'] = os.path.join(output_path, '%(title)s.%(ext)s')

        if browser_cookies:
            ydl_opts['cookiesfrombrowser'] = (browser_cookies,)

        if progress_callback:
            def hooks(d):
                if d['status'] == 'downloading':
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)

                    percent = downloaded / total if total > 0 else 0.0
                    speed_mb = speed / 1024 / 1024 if speed else 0
                    info_text = f"⬇ {speed_mb:.1f} МБ/с  |  Осталось: {eta}с"
                    progress_callback(percent, info_text)
                elif d['status'] == 'finished':
                    progress_callback(1.0, "⏳ Обработка...")
            ydl_opts['progress_hooks'] = [hooks]

        is_audio = "аудио" in format_selection.lower() or "audio" in format_selection.lower()

        if is_audio:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        else:
            # Магия yt-dlp: ищем лучшее видео до указанной высоты + лучшее аудио
            res_val = format_selection.split('p')[0].strip()
            ydl_opts['format'] = f"bestvideo[height<={res_val}]+bestaudio/best/best[height<={res_val}]/best"
            ydl_opts['merge_output_format'] = 'mp4'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if finished_callback: finished_callback()
        except Exception as e:
            msg = self._handle_error(str(e))
            if error_callback: error_callback(msg)
