"""
yt-dlp based downloader
"""

import logging
import platform
from pathlib import Path
from typing import Optional, Dict, Any, List

from .base import BaseDownloader
from ..core.models import DownloadOptions, VideoInfo, VideoQuality
from ..extractors.post_text import PostTextExtractor
from ..utils.filename import FileNameGenerator

logger = logging.getLogger(__name__)

# Browser preference for cookie extraction (in order)
COOKIE_BROWSERS: List[str] = ["chrome", "firefox", "safari", "edge"]


class YtDlpDownloader(BaseDownloader):
    """Downloader using yt-dlp"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._available_browser: Optional[str] = None

    def _detect_available_browser(self) -> Optional[str]:
        """Detect available browser for cookie extraction"""
        if self._available_browser is not None:
            return self._available_browser

        try:
            import yt_dlp.cookies
        except ImportError:
            return None

        # On macOS, Safari is often easiest due to fewer permission issues
        browsers = COOKIE_BROWSERS.copy()
        if platform.system() == "Darwin":
            browsers = ["safari", "chrome", "firefox", "edge"]

        for browser in browsers:
            try:
                # Try to check if browser cookies are accessible
                logger.debug(f"Checking cookie availability for: {browser}")
                self._available_browser = browser
                return browser
            except Exception:
                continue

        return None

    def _get_base_opts(self, use_cookies: bool = True) -> Dict[str, Any]:
        """Get base yt-dlp options with optional cookie support"""
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            # Modern headers to avoid blocks
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            },
        }

        if use_cookies:
            browser = self._detect_available_browser()
            if browser:
                opts["cookiesfrombrowser"] = (browser,)
                logger.info(f"Using cookies from: {browser}")

        return opts

    def download(
        self,
        url: str,
        output_path: Optional[Path] = None,
        options: Optional[DownloadOptions] = None,
    ) -> bool:
        """Download using yt-dlp"""
        try:
            import yt_dlp  # noqa: F401
        except ImportError:
            logger.error("yt-dlp is not installed")
            logger.info("To install: pip install yt-dlp")
            return False

        options = options or DownloadOptions()

        # Playlist URLs fan out into a numbered directory
        playlist = self._probe_playlist(url)
        if playlist:
            return self._download_playlist(playlist, options)

        return self._download_single(url, output_path, options)

    def _download_single(
        self, url: str, output_path: Optional[Path], options: DownloadOptions
    ) -> bool:
        """Download a single video, trying with cookies first, then without"""
        for use_cookies in [True, False]:
            try:
                result = self._attempt_download(url, output_path, use_cookies, options)
                if result:
                    return True
            except Exception as e:
                if use_cookies:
                    logger.warning(f"Download with cookies failed: {e}")
                    logger.info("Retrying without cookies...")
                else:
                    logger.error(f"yt-dlp error: {e}")
                    return False

        return False

    def _probe_playlist(self, url: str) -> Optional[Dict[str, Any]]:
        """Return flat playlist info if the URL is a playlist, else None"""
        # Only pay for a probe when the URL looks like a playlist
        if "list=" not in url and "/playlist" not in url:
            return None

        import yt_dlp

        for use_cookies in [True, False]:
            try:
                opts = {
                    **self._get_base_opts(use_cookies),
                    "quiet": True,
                    "extract_flat": "in_playlist",
                }
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                if info and info.get("_type") == "playlist":
                    return info
                return None
            except Exception as e:
                if use_cookies:
                    continue
                logger.debug(f"Playlist probe failed: {e}")

        return None

    def _download_playlist(
        self, playlist_info: Dict[str, Any], options: DownloadOptions
    ) -> bool:
        """Download every entry of a playlist into a numbered directory"""
        entries = [e for e in (playlist_info.get("entries") or []) if e]
        if not entries:
            logger.error("Playlist has no entries")
            return False

        title = playlist_info.get("title") or "playlist"
        dir_name = FileNameGenerator._sanitize_filename(title)[:60] or "playlist"
        playlist_dir = Path(dir_name)
        playlist_dir.mkdir(parents=True, exist_ok=True)

        total = len(entries)
        ext = "m4a" if options.audio_only else "mp4"
        logger.info(f"Playlist: {title} ({total} items)")
        logger.info(f"Output directory: {playlist_dir}/")

        success = 0
        for index, entry in enumerate(entries, 1):
            entry_url = entry.get("url")
            if entry_url and not entry_url.startswith("http"):
                entry_url = f"https://www.youtube.com/watch?v={entry_url}"
            if not entry_url and entry.get("id"):
                entry_url = f"https://www.youtube.com/watch?v={entry['id']}"

            entry_title = entry.get("title") or f"track_{index}"
            print("\n" + "=" * 50)
            print(f"[{index}/{total}] {entry_title}")
            print("=" * 50)

            if not entry_url:
                logger.warning(f"[{index}/{total}] Skipped (no URL)")
                continue

            safe_title = FileNameGenerator._sanitize_filename(entry_title) or f"track_{index}"
            out = playlist_dir / f"{index:02d}_{safe_title}.{ext}"

            try:
                if self._download_single(entry_url, out, options):
                    success += 1
                else:
                    logger.warning(f"[{index}/{total}] Failed")
            except Exception as e:
                # One bad entry must not abort the whole playlist
                logger.warning(f"[{index}/{total}] Failed ({e})")

        logger.info(f"Playlist complete: {success}/{total} succeeded")
        logger.info(f"Files saved in: {playlist_dir}/")
        return success > 0

    def _attempt_download(
        self,
        url: str,
        output_path: Optional[Path],
        use_cookies: bool,
        options: DownloadOptions,
    ) -> bool:
        """Attempt to download with specified options"""
        import yt_dlp

        base_opts = self._get_base_opts(use_cookies)

        # First, get video info
        info_opts = {**base_opts, "quiet": True}
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            logger.info(f"Fetching video info: {url}")
            info = ydl.extract_info(url, download=False)

            # Create VideoInfo
            video_info = self._create_video_info(info)

            # If yt-dlp didn't provide description, fetch it from the page
            if not video_info.description and info:
                # Use the original URL (not mobile webpage_url which often returns 400)
                description = self._fetch_post_text(url, ydl)
                if description:
                    video_info.description = description

            # Generate filename
            if output_path is None:
                filename = self._generate_filename(video_info)
                output_path = Path(filename)

            # Audio-only mode extracts to .m4a regardless of the source ext
            if options.audio_only:
                output_path = output_path.with_suffix(".m4a")

            # Track actual downloaded file path
            actual_filepath: List[Optional[str]] = [None]

            def progress_hook(d: Dict[str, Any]) -> None:
                self._progress_hook(d)
                if d["status"] == "finished":
                    actual_filepath[0] = d.get("filename")

            # Set download options
            ydl_opts = self._build_ydl_opts(base_opts, output_path, options, progress_hook)

            # Execute download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_dl:
                ydl_dl.download([url])

            # Subtitle-only mode produces no media file; just handle the .srt
            if options.srt_only:
                self._finalize_subtitle(output_path, options.sub_lang)
                self._save_description(output_path, video_info)
                return True

            # Use actual file path if available
            final_path = Path(actual_filepath[0]) if actual_filepath[0] else output_path
            logger.info(f"✓ Download complete: {final_path}")
            if final_path.exists():
                logger.info(f"  File size: {final_path.stat().st_size:,} bytes")

            # Rename downloaded subtitle to the *_yt.srt convention
            if options.subtitles:
                self._finalize_subtitle(output_path, options.sub_lang)

            # Save description as text file
            self._save_description(final_path, video_info)

            return True

    @staticmethod
    def _build_ydl_opts(
        base_opts: Dict[str, Any],
        output_path: Path,
        options: DownloadOptions,
        progress_hook: Any,
    ) -> Dict[str, Any]:
        """Build yt-dlp options for the requested download mode"""
        opts: Dict[str, Any] = {
            **base_opts,
            "outtmpl": str(output_path),
            "quiet": False,
            "no_warnings": False,
            "progress_hooks": [progress_hook],
        }

        if options.audio_only:
            # Best audio extracted to m4a
            opts["format"] = "ba/b"
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                    "preferredquality": "0",
                }
            ]
            return opts

        if options.srt_only:
            # Subtitles only, no media download
            opts["skip_download"] = True
        else:
            # Best video (capped at 1080p) + best audio, merged to mp4;
            # fall back to best single file (/b) for sources that only
            # offer combined streams.
            opts["format"] = "bv*[height<=1080]+ba/b"
            opts["merge_output_format"] = "mp4"
            # Allow yt-dlp to fetch the JS challenge solver (yt-dlp-ejs) that
            # YouTube now requires; harmless for Facebook/Instagram.
            opts["remote_components"] = ["ejs:github"]

        if options.subtitles or options.srt_only:
            # Auto-generated captions converted to SRT (matches ytdl workflow)
            opts["writeautomaticsub"] = True
            opts["subtitleslangs"] = [options.sub_lang]
            opts["subtitlesformat"] = "srt/best"
            opts.setdefault("postprocessors", []).append(
                {"key": "FFmpegSubtitlesConvertor", "format": "srt"}
            )

        return opts

    @staticmethod
    def _finalize_subtitle(output_path: Path, sub_lang: str) -> None:
        """Rename yt-dlp's '<base>.<lang>.srt' to the '<base>_yt.srt' convention"""
        sub_src = output_path.with_name(f"{output_path.stem}.{sub_lang}.srt")
        sub_dst = output_path.with_name(f"{output_path.stem}_yt.srt")
        if sub_src.exists():
            sub_src.replace(sub_dst)
            logger.info(f"✓ Subtitle saved: {sub_dst}")
        else:
            logger.warning("No subtitles found for this video")

    def _fetch_post_text(self, page_url: str, ydl: Any) -> Optional[str]:
        """Fetch the Facebook page and extract post body text using yt-dlp's session"""
        try:
            logger.info(f"Fetching post text from: {page_url}")

            # Use yt-dlp's urlopen which handles cookies and headers properly
            response = ydl.urlopen(page_url)
            html = response.read().decode("utf-8", errors="replace")

            if html:
                text = PostTextExtractor.extract(html)
                if text:
                    logger.info(f"Post text extracted ({len(text)} chars)")
                    return text
                else:
                    logger.info("No post text found on page")

        except Exception as e:
            logger.warning(f"Failed to fetch post text: {e}")

        return None

    @staticmethod
    def _create_video_info(info: Dict[str, Any]) -> VideoInfo:
        """Create VideoInfo from yt-dlp info"""
        # yt-dlp stores post body in different fields depending on the extractor
        description = (
            info.get("description")
            or info.get("caption")
            or info.get("post_text")
            or None
        )
        if description:
            logger.debug(f"yt-dlp description ({len(description)} chars): {description[:100]}...")

        return VideoInfo(
            url=info.get("url", ""),
            quality=VideoQuality.STANDARD,
            title=info.get("title"),
            uploader=info.get("uploader") or info.get("channel"),
            description=description,
            video_id=str(info.get("id", "")),
        )

    @staticmethod
    def _progress_hook(d: Dict[str, Any]) -> None:
        """Progress display hook"""
        if d["status"] == "downloading":
            print(f"\rProgress: {d.get('_percent_str', '')}", end="")
        elif d["status"] == "finished":
            print()  # New line
