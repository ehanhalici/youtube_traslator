from typing import Optional
import yt_dlp
import os

class SilentLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def silent_hook(d): 
    pass


def download_subtitle(video_url: str, lang: str) -> Optional[str]:
    subtitle_name = video_url.replace("/", '_')
    subtitle_name_orig_name = subtitle_name   +"."+lang+".json3"

    if os.path.exists(subtitle_name_orig_name):
        return subtitle_name_orig_name

    ydl_opts = {
        # '--write-auto-sub' -> Otomatik altyazıları yaz
        'writeautomaticsub': True,
        'subtitleslangs': [lang],
        'subtitlesformat': 'json3',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'outtmpl': subtitle_name,
        'logger': SilentLogger(),
        'progress_hooks': [silent_hook],
        'cookiesfrombrowser': ('firefox',),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True, )
        return subtitle_name_orig_name
    except yt_dlp.utils.DownloadError as e:
        print(f"İndirme hatası: {e}")
    except Exception as e:
        print(f"Genel bir hata oluştu: {e}")

    return None
