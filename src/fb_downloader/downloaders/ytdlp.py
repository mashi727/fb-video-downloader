"""
yt-dlp based downloader
"""

import atexit
import logging
import os
import platform
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse

from .base import BaseDownloader
from ..core.models import DownloadOptions, VideoInfo, VideoQuality
from ..extractors.post_text import PostTextExtractor
from ..utils.filename import FileNameGenerator

logger = logging.getLogger(__name__)

# Browser preference for cookie extraction, per platform.
# Linux puts Firefox first: Chromium-family cookies are encrypted with a key
# held in the GNOME keyring / KWallet, which is unavailable over SSH or on a
# headless box, while Firefox's cookies.sqlite is readable as-is.
COOKIE_BROWSERS: List[str] = ["chrome", "firefox", "edge"]
COOKIE_BROWSERS_BY_PLATFORM: Dict[str, List[str]] = {
    "Darwin": ["safari", "chrome", "firefox", "edge"],
    "Linux": ["firefox", "chrome", "chromium", "brave", "edge"],
}

# TLS fingerprint impersonation targets, best first (requires curl_cffi).
# Facebook serves its reel/watch payload only to clients whose TLS handshake
# looks like a real browser; a plain Python request gets "Cannot parse data".
IMPERSONATE_TARGETS: List[str] = ["chrome-136", "chrome-133", "chrome", "safari-18.4", "safari"]

# Sites that need impersonation on the *first* attempt, not as a fallback
IMPERSONATE_FIRST_DOMAINS: Tuple[str, ...] = (
    "facebook.com",
    "fb.watch",
    "fb.com",
    "instagram.com",
)

# Cookie that proves a logged-in session, by site keyword
SESSION_COOKIES: List[Tuple[Tuple[str, ...], str]] = [
    (("facebook", "fb.watch", "fb.com"), "c_user"),
    (("instagram",), "sessionid"),
]

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

# Age at which a yt-dlp install is old enough to be a plausible cause of failure
STALE_YTDLP_DAYS = 45


class _QuietLogger:
    """Routes yt-dlp's console output to debug level.

    Extraction failures are expected while escalating through strategies, so
    they are reported once, trimmed, instead of shouting on every attempt.
    """

    def debug(self, msg: str) -> None:
        logger.debug(msg)

    def info(self, msg: str) -> None:
        logger.debug(msg)

    def warning(self, msg: str) -> None:
        logger.debug(msg)

    def error(self, msg: str) -> None:
        logger.debug(msg)


class YtDlpDownloader(BaseDownloader):
    """Downloader using yt-dlp"""

    _ffmpeg_warned = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._available_browser: Optional[str] = None
        self._cookie_file: Optional[Path] = None
        self._cookies_resolved = False
        self._impersonate_target: Any = None
        self._impersonate_resolved = False
        self._forced_browser: Optional[str] = None

    # ------------------------------------------------------------------
    # Capability detection
    # ------------------------------------------------------------------

    def _browser_candidates(self) -> List[str]:
        """Browsers to probe for cookies, most likely to work first"""
        if self._forced_browser:
            return [self._forced_browser]
        return COOKIE_BROWSERS_BY_PLATFORM.get(platform.system(), COOKIE_BROWSERS).copy()

    @staticmethod
    def _session_cookie_name(url: str) -> Optional[str]:
        """Name of the cookie that proves a logged-in session for this URL"""
        host = urlparse(url).netloc.lower()
        for keywords, cookie in SESSION_COOKIES:
            if any(keyword in host for keyword in keywords):
                return cookie
        return None

    def _resolve_cookies(self, url: str) -> Optional[Path]:
        """Extract browser cookies once and cache them in a private temp file.

        A browser that actually holds a logged-in session for the target site
        wins: Facebook reels return no video data to anonymous clients.
        """
        if self._cookies_resolved:
            return self._cookie_file
        self._cookies_resolved = True

        if self._forced_browser == "none":
            logger.info("Cookies disabled by --browser none")
            return None

        try:
            from yt_dlp.cookies import extract_cookies_from_browser, YDLLogger
        except ImportError:
            return None

        wanted = self._session_cookie_name(url)
        fallback: Optional[Tuple[str, Any]] = None

        for browser in self._browser_candidates():
            try:
                jar = extract_cookies_from_browser(browser, logger=YDLLogger())
            except Exception as e:
                logger.debug(f"Cookie extraction failed for {browser}: {e}")
                continue

            if not len(jar):
                continue

            if wanted and not any(cookie.name == wanted for cookie in jar):
                logger.debug(f"{browser}: no logged-in session (missing '{wanted}')")
                if fallback is None:
                    fallback = (browser, jar)
                continue

            return self._store_cookies(browser, jar)

        if fallback:
            logger.warning(
                f"No logged-in session found in browser cookies; using {fallback[0]} anyway"
            )
            return self._store_cookies(*fallback)

        logger.info("No usable browser cookies found; continuing without cookies")
        return None

    def _store_cookies(self, browser: str, jar: Any) -> Optional[Path]:
        """Persist an extracted cookie jar so every retry reuses one extraction"""
        self._available_browser = browser
        logger.info(f"Using cookies from: {browser}")

        try:
            handle, name = tempfile.mkstemp(prefix="fbdl-cookies-", suffix=".txt")
            os.close(handle)
            path = Path(name)
            os.chmod(path, 0o600)
            jar.save(str(path))
        except Exception as e:
            # Fall back to letting yt-dlp re-extract per attempt
            logger.debug(f"Could not cache cookies to file: {e}")
            return None

        self._cookie_file = path
        atexit.register(self._cleanup_cookie_file)
        return path

    def _cleanup_cookie_file(self) -> None:
        """Remove the temporary cookie file (it holds live session tokens)"""
        if self._cookie_file:
            try:
                self._cookie_file.unlink(missing_ok=True)
            except OSError:
                pass
            self._cookie_file = None

    def _detect_impersonate_target(self) -> Any:
        """Return the best available TLS impersonation target, or None"""
        if self._impersonate_resolved:
            return self._impersonate_target
        self._impersonate_resolved = True

        try:
            import yt_dlp
            from yt_dlp.networking.impersonate import ImpersonateTarget
        except ImportError:
            return None

        for name in IMPERSONATE_TARGETS:
            try:
                target = ImpersonateTarget.from_str(name)
                # Constructing YoutubeDL raises if the target is unsupported
                with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "impersonate": target}):
                    pass
            except Exception:
                continue
            logger.debug(f"TLS impersonation available: {target}")
            self._impersonate_target = target
            return target

        logger.debug("No TLS impersonation target available (curl_cffi missing?)")
        return None

    @classmethod
    def _warn_if_ffmpeg_missing(cls) -> None:
        """Warn once per run: every mode relies on ffmpeg post-processing"""
        if cls._ffmpeg_warned or shutil.which("ffmpeg"):
            return
        cls._ffmpeg_warned = True
        logger.warning("ffmpeg not found: separate video/audio streams cannot be merged")
        logger.info("  Install it: sudo apt install ffmpeg  (macOS: brew install ffmpeg)")

    @staticmethod
    def _needs_impersonation(url: str) -> bool:
        """True for sites that block non-browser TLS fingerprints outright"""
        host = urlparse(url).netloc.lower()
        return any(host == d or host.endswith("." + d) for d in IMPERSONATE_FIRST_DOMAINS)

    def _get_base_opts(
        self, url: str = "", use_cookies: bool = True, impersonate: bool = False
    ) -> Dict[str, Any]:
        """Get base yt-dlp options for one attempt strategy"""
        opts: Dict[str, Any] = {"quiet": True, "no_warnings": True}

        target = self._detect_impersonate_target() if impersonate else None
        if target:
            # curl_cffi owns the header set: a hand-written User-Agent would
            # contradict the impersonated TLS fingerprint and defeat the point.
            opts["impersonate"] = target
        else:
            opts["http_headers"] = dict(DEFAULT_HEADERS)

        if use_cookies:
            cookie_file = self._resolve_cookies(url)
            if cookie_file:
                opts["cookiefile"] = str(cookie_file)
            elif self._available_browser:
                opts["cookiesfrombrowser"] = (self._available_browser,)

        return opts

    def _build_attempts(self, url: str) -> List[Tuple[bool, bool]]:
        """Ordered (use_cookies, impersonate) strategies to try for this URL"""
        has_cookies = self._resolve_cookies(url) is not None or self._available_browser is not None
        has_impersonate = self._detect_impersonate_target() is not None

        cookie_modes = [True, False] if has_cookies else [False]
        if not has_impersonate:
            impersonate_modes = [False]
        elif self._needs_impersonation(url):
            impersonate_modes = [True, False]
        else:
            # YouTube and friends work fine without it; keep it as a fallback
            impersonate_modes = [False, True]

        return [(cookies, imp) for cookies in cookie_modes for imp in impersonate_modes]

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

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
        self._forced_browser = options.cookie_browser
        self._warn_if_ffmpeg_missing()

        try:
            # Playlist URLs fan out into a numbered directory
            playlist = self._probe_playlist(url)
            if playlist:
                return self._download_playlist(playlist, options)

            return self._download_single(url, output_path, options)
        finally:
            self._cleanup_cookie_file()

    def _download_single(
        self, url: str, output_path: Optional[Path], options: DownloadOptions
    ) -> bool:
        """Download a single video, escalating through the attempt strategies"""
        attempts = self._build_attempts(url)
        last_error: Optional[Exception] = None

        for index, (use_cookies, impersonate) in enumerate(attempts, 1):
            label = self._describe_attempt(use_cookies, impersonate)
            logger.info(f"Attempt {index}/{len(attempts)}: {label}")
            try:
                if self._attempt_download(url, output_path, use_cookies, impersonate, options):
                    return True
            except Exception as e:
                last_error = e
                logger.warning(f"Failed ({label}): {self._first_line(e)}")

        self._log_failure_hints(last_error)
        return False

    @staticmethod
    def _describe_attempt(use_cookies: bool, impersonate: bool) -> str:
        """Human-readable name for an attempt strategy"""
        parts = []
        if use_cookies:
            parts.append("cookies")
        if impersonate:
            parts.append("TLS impersonation")
        return " + ".join(parts) if parts else "plain request"

    @staticmethod
    def _first_line(error: Exception) -> str:
        """Trim yt-dlp's boilerplate down to the part that matters"""
        text = str(error).split("\n")[0]
        text = re.sub(r";\s*please report this issue.*$", "", text, flags=re.IGNORECASE)
        return text.strip()

    @staticmethod
    def _ytdlp_age_days() -> Optional[int]:
        """Days since the installed yt-dlp was released, if parseable"""
        try:
            from yt_dlp.version import __version__

            match = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", __version__)
            if not match:
                return None
            year, month, day = (int(g) for g in match.groups())
            released = datetime(year, month, day)
        except Exception:
            return None
        return (datetime.now() - released).days

    def _log_failure_hints(self, error: Optional[Exception]) -> None:
        """Turn a dead end into actionable next steps"""
        message = self._first_line(error) if error else ""
        logger.error(f"All download strategies failed: {message}" if message else "Download failed")

        hints: List[str] = []
        if self._detect_impersonate_target() is None:
            hints.append(
                'Install TLS impersonation support: pip install "curl_cffi>=0.5.10" '
                "(Facebook blocks non-browser TLS fingerprints)"
            )
        if self._cookie_file is None and self._available_browser is None:
            hints.append(
                "Log in to the site in Safari or Chrome so fbdl can reuse the session "
                "(macOS: the terminal needs Full Disk Access to read Safari cookies)"
            )
        age = self._ytdlp_age_days()
        if age is not None and age > STALE_YTDLP_DAYS:
            hints.append(f"yt-dlp is {age} days old; update it: pip install -U --pre yt-dlp")

        for hint in hints:
            logger.info(f"  - {hint}")

    def _probe_playlist(self, url: str) -> Optional[Dict[str, Any]]:
        """Return flat playlist info if the URL is a playlist, else None"""
        # Only pay for a probe when the URL looks like a playlist
        if "list=" not in url and "/playlist" not in url:
            return None

        import yt_dlp

        for use_cookies, impersonate in self._build_attempts(url):
            try:
                opts = {
                    **self._get_base_opts(url, use_cookies, impersonate),
                    "quiet": True,
                    "logger": _QuietLogger(),
                    "extract_flat": "in_playlist",
                }
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                if info and info.get("_type") == "playlist":
                    return info
                return None
            except Exception as e:
                logger.debug(f"Playlist probe failed: {e}")

        return None

    def _download_playlist(self, playlist_info: Dict[str, Any], options: DownloadOptions) -> bool:
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
        impersonate: bool,
        options: DownloadOptions,
    ) -> bool:
        """Attempt to download with specified options"""
        import yt_dlp

        base_opts = self._get_base_opts(url, use_cookies, impersonate)

        # First, get video info
        info_opts = {**base_opts, "quiet": True, "logger": _QuietLogger()}
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            logger.info(f"Fetching video info: {url}")
            info = ydl.extract_info(url, download=False)
            if not info:
                raise RuntimeError("yt-dlp returned no video information")

            # Create VideoInfo
            video_info = self._create_video_info(info)

            # If yt-dlp didn't provide description, fetch it from the page
            if not video_info.description and info:
                # Use the original URL (not mobile webpage_url which often returns 400)
                description = self._fetch_post_text(url, ydl)
                if description:
                    video_info.description = description

            # Generate filename
            auto_named = output_path is None
            if output_path is None:
                filename = self._generate_filename(video_info)
                output_path = Path(filename)

            # Audio-only mode extracts to .m4a regardless of the source ext
            if options.audio_only:
                output_path = output_path.with_suffix(".m4a")

            # Auto-generated names collide across videos from the same
            # uploader; an explicit name from the user is left alone.
            if auto_named:
                output_path = self._ensure_unique_path(output_path)

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

            final_path = self._resolve_final_path(output_path, actual_filepath[0])
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
    def _resolve_final_path(output_path: Path, downloaded: Optional[str]) -> Path:
        """Pick the file that actually survived the download.

        When yt-dlp merges separate video and audio streams it deletes the
        per-format temporaries that the progress hook last reported, so the
        template path is the reliable answer whenever it exists.
        """
        if output_path.exists():
            return output_path
        if downloaded and Path(downloaded).exists():
            return Path(downloaded)
        return output_path

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
            # Best video + best audio, merged to mp4; fall back to the best
            # single file (/b) for sources that only offer combined streams.
            opts["format"] = "bv*+ba/b"
            # Cap quality by the *smaller* dimension: a height filter would
            # reject a 1080x1920 vertical reel while letting 4K through.
            opts["format_sort"] = ["res:1080"]
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
            info.get("description") or info.get("caption") or info.get("post_text") or None
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
