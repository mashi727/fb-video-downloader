"""
Filename generation utility
"""

import os
import re
import sys
import unicodedata
import subprocess
import logging
from datetime import datetime
from typing import Optional

from ..core.models import VideoInfo

logger = logging.getLogger(__name__)

# Emoji blocks preserved in filenames (see _sanitize_filename)
EMOJI_RANGES = (
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f900-\U0001f9ff"  # supplemental symbols (🥬 is here)
    "\U0001fa70-\U0001faff"  # symbols extended-A
    "\U00002600-\U000026ff"  # miscellaneous symbols
    "\U00002700-\U000027bf"  # dingbats (✨)
)


class FileNameGenerator:
    """Filename generation class"""

    MAX_FILENAME_LENGTH = 100  # Maximum filename length (considering byte length)
    IDEAL_LENGTH = 50  # Ideal length for Japanese filenames
    CLAUDE_TIMEOUT = 30  # `claude -p` needs ~5s; 10s was tight enough to always lose
    USE_CLAUDE: bool = True  # Set False to stay offline and deterministic

    # Brackets a Japanese post uses to declare its subject. 「」 is excluded on
    # purpose: it is ordinary quotation, and matching it yields quoted sentences
    # ("入試", "秘密") rather than titles.
    TITLE_BRACKETS = (("『", "』"), ("【", "】"))

    # Bracketed lines that head a section instead of naming the video
    SECTION_PREFIXES = (
        "材料",
        "作り方",
        "手順",
        "レシピ",
        "ポイント",
        "保存",
        "調味料",
        "分量",
        "下準備",
        "コツ",
        "作り置き",
        "注意",
        "道具",
        "栄養",
        "トッピング",
        "アレンジ",
        "免責",
        "お知らせ",
        "宣伝",
        "広告",
        "recipe",
    )

    # Titles the platform generates when a post has none of its own
    PLACEHOLDER_TITLE_PATTERNS = (
        r"^video by\b",
        r"^post by\b",
        r"^reels?$",
        r"^動画$",
        r"の動画$",
        r"^facebook$",
        r"^instagram$",
        r"^watch$",
    )

    # Phrases that mark a line as follow/save boilerplate rather than content
    BOILERPLATE_MARKERS = (
        "フォロー",
        "保存",
        "いいね",
        "コメント",
        "プロフィール",
        "DM",
        "リンク",
        "こちら",
    )

    @classmethod
    def generate(
        cls, video_info: Optional[VideoInfo] = None, date_str: Optional[str] = None
    ) -> str:
        """Generate filename based on video information.

        `date_str` overrides today's date, so files downloaded earlier keep the
        day they were fetched when they are renamed.
        """
        if not video_info:
            # If no video info, use timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"fb_video_{timestamp}.mp4"

        # Date
        date_str = date_str or datetime.now().strftime("%Y%m%d")

        # Main content summary
        content_summary = cls._create_content_summary(video_info)

        if content_summary:
            # The subject of the video is the name; the account name is not
            # part of it (「20260817_焼きシーザーサラダ🥬」).
            filename = f"{date_str}_{content_summary}"
        elif video_info.uploader:
            # Nothing describes the content: fall back to who posted it
            filename = f"{date_str}_{cls._sanitize_filename(video_info.uploader)[:20]}"
        elif video_info.video_id:
            filename = f"{date_str}_fb_video_{video_info.video_id[:8]}"
        else:
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{date_str}_fb_video_{timestamp}"

        # Adjust length
        if len(filename) > cls.MAX_FILENAME_LENGTH:
            # Truncate and add ID
            base = filename[: cls.MAX_FILENAME_LENGTH - 10]
            id_suffix = (
                video_info.video_id[:6] if video_info.video_id else datetime.now().strftime("%H%M")
            )
            filename = f"{base}_{id_suffix}"

        return f"{filename}.mp4"

    @classmethod
    def _create_content_summary(cls, video_info: VideoInfo) -> str:
        """Derive a name that says what the video is about.

        The post body is the only place that describes the content: on
        Instagram and Facebook the title field is a placeholder ("Video by
        xxx", "…の動画"), so it is consulted last.
        """
        body = (video_info.description or "").strip()
        title = (video_info.title or "").strip()

        # 1. The author's own declared title, e.g. a line reading 『焼きシーザーサラダ🥬』
        declared = cls._extract_declared_title(body) if body else ""
        if declared:
            logger.debug(f"Title declared in post body: {declared}")
            return cls._sanitize_filename(declared)

        # 2. Ask claude to name the subject of the post
        summarized = cls._summarize_with_claude(body or title, max_length=cls.IDEAL_LENGTH)
        if summarized:
            return cls._sanitize_filename(summarized)

        # 3. The platform title, when it actually says something
        if title and not cls._is_placeholder_title(title, video_info.uploader):
            return cls._sanitize_filename(title)

        # 4. Local fallback: first line of the body that is not boilerplate
        meaningful = cls._first_meaningful_line(body) if body else ""
        if meaningful:
            return cls._summarize_text(meaningful, target_length=40)

        return cls._summarize_text(title, target_length=40) if title else ""

    @classmethod
    def _extract_declared_title(cls, body: str) -> str:
        """Return a title the post states on a line of its own, if any.

        Requiring the brackets to span the whole line is what separates a
        declared title from emphasis inside a sentence.
        """
        for raw_line in body.splitlines():
            line = raw_line.strip()
            for open_char, close_char in cls.TITLE_BRACKETS:
                match = re.fullmatch(
                    re.escape(open_char) + r"(.{1,25})" + re.escape(close_char), line
                )
                if not match:
                    continue

                candidate = match.group(1).strip()
                core = re.sub(r"[^\w一-龥ぁ-んァ-ヶー]", "", candidate)
                if len(core) < 2:
                    # Decorations such as 『❤️』
                    continue
                if any(core.startswith(prefix) for prefix in cls.SECTION_PREFIXES):
                    continue
                return candidate

        return ""

    @classmethod
    def _is_placeholder_title(cls, title: str, uploader: Optional[str] = None) -> bool:
        """Whether the title is the platform's filler rather than a real one"""
        text = title.strip().lower()
        if uploader and text == uploader.strip().lower():
            return True
        return any(re.search(p, text, re.IGNORECASE) for p in cls.PLACEHOLDER_TITLE_PATTERNS)

    @classmethod
    def _first_meaningful_line(cls, body: str) -> str:
        """First line that carries content rather than follow/save prompts"""
        for raw_line in body.splitlines():
            # Posts decorate their pointer lines: "他のレシピ▷@eri.gohan_"
            line = raw_line.strip().strip("▷▶◀◁→←⇒⏩☝︎♡＞>・.")
            line = line.strip()
            if len(line) < 4:
                continue
            # An account handle or link anywhere means it is a pointer line
            if "@" in line or "http" in line or line.startswith("#"):
                continue
            if any(marker in line for marker in cls.BOILERPLATE_MARKERS):
                continue
            return line
        return ""

    @classmethod
    def _summarize_with_claude(cls, text: str, max_length: int = 50) -> Optional[str]:
        """Ask claude for the subject of the post, to be used as the filename"""
        if not text.strip() or not cls.USE_CLAUDE:
            return None

        try:
            prompt = (
                "次はSNSの動画投稿の本文です。この動画の主題を表すタイトルを1つだけ出力してください。\n"
                "要件:\n"
                "- 料理名・トレーニング名など、投稿の主題そのものの名称にする\n"
                "- 本文中に『』や【】でタイトルが明示されていれば、絵文字も含めそのまま使う\n"
                "- 自己紹介・フォロー誘導・ハッシュタグ・材料や手順は無視する\n"
                f"- 日本語で{max_length // 2}文字以内。句読点・説明・引用符を付けない\n"
                "- タイトルのみを1行で出力し、他には何も書かない\n\n"
                f"本文:\n{text[:1500]}\n"
            )

            # FBDL_CLAUDE_BIN covers installs that are not on PATH
            claude_bin = os.environ.get("FBDL_CLAUDE_BIN", "claude")

            result = subprocess.run(
                [claude_bin, "-p"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=cls.CLAUDE_TIMEOUT,
                check=False,
            )

            if result.returncode != 0:
                logger.info(f"claude -p failed (exit {result.returncode}); using local naming")
                if result.stderr:
                    logger.debug(f"stderr: {result.stderr}")
                return None

            # Take the last non-empty line: any preamble comes before it
            lines = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            if not lines:
                return None

            summary = lines[-1].strip("\"'`「」『』")
            summary = summary.replace(".mp4", "").replace(".MP4", "")

            # A sentence means it answered with prose instead of a title
            if not summary or len(summary) > max_length or "。" in summary:
                logger.debug(f"Rejected claude output: {summary!r}")
                return None

            # stderr keeps this out of reports that parse stdout
            print(f"📝 Using claude -p for filename: {summary}", file=sys.stderr)
            return summary

        except FileNotFoundError:
            logger.debug("claude command not found in PATH")
        except subprocess.TimeoutExpired:
            logger.info(f"claude -p timed out after {cls.CLAUDE_TIMEOUT}s; using local naming")
        except Exception as e:
            logger.debug(f"Error using claude -p: {e}")

        return None

    @classmethod
    def _summarize_text(cls, text: str, target_length: int = 40) -> str:
        """Summarize text meaningfully (fallback method)"""
        # Sanitize
        text = cls._sanitize_filename(text)

        # Check for Japanese characters
        has_japanese = any(ord(char) > 0x3000 for char in text)

        if has_japanese:
            # For Japanese: consider particles
            parts = re.split(r"[。、！？\s]+", text)
            summary = parts[0] if parts else text

            # Truncate if too long
            if len(summary) > target_length:
                summary = summary[:target_length]
                # Remove trailing particles
                particles = "をにがのでとはも"
                while summary and summary[-1] in particles:
                    summary = summary[:-1]
        else:
            # For English: keep important words
            stop_words = {
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
                "from",
                "as",
                "is",
                "was",
                "are",
                "were",
                "be",
                "have",
                "has",
                "had",
                "do",
                "does",
                "did",
                "will",
                "would",
                "could",
                "should",
                "may",
                "might",
                "can",
                "this",
                "that",
                "these",
                "those",
            }

            # Split into words
            words = text.split("_")

            # Select important words
            important_words = []
            current_length = 0

            for word in words:
                if word.lower() not in stop_words or len(important_words) == 0:
                    if current_length + len(word) + len(important_words) <= target_length:
                        important_words.append(word)
                        current_length += len(word)
                    else:
                        break

            summary = "_".join(important_words) if important_words else text[:target_length]

        return summary

    @staticmethod
    def _sanitize_filename(text: str) -> str:
        """Convert to string usable as filename (only - and _ allowed as symbols)"""
        # Unicode normalization
        text = unicodedata.normalize("NFKC", text)

        # Zero-width joiners and variation selectors leave invisible debris
        text = text.replace("‍", "").replace("️", "")

        # First, replace spaces and common separators with underscore
        text = re.sub(r"[\s,;:：、。！？・]+", "_", text)

        # Keep alphanumerics (including Japanese), hyphen, underscore and
        # emoji: the author's own title carries them (『焼きシーザーサラダ🥬』)
        # and the user names the file by that string.
        text = re.sub(rf"[^\w\-ー－{EMOJI_RANGES}]", "", text, flags=re.UNICODE)

        # Full-width hyphen becomes half-width. The katakana prolonged sound
        # mark (ー) is a letter, not punctuation — converting it mangles words
        # like シーザーサラダ into シ-ザ-サラダ.
        text = text.replace("－", "-")

        # Collapse consecutive underscores or hyphens
        text = re.sub(r"_+", "_", text)
        text = re.sub(r"-+", "-", text)
        text = re.sub(r"(-_|_-)+", "_", text)  # Mix of - and _ becomes _

        # Remove leading/trailing underscores and hyphens
        text = text.strip("_-")

        # If empty string after sanitization
        if not text:
            return ""

        return text
