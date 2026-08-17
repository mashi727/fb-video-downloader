# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation
```bash
# Install in development mode with all dependencies
pip install -e ".[dev,ytdlp]"

# Install only core dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Using installed command
fbdl <Facebook_Video_URL> [output_filename]

# Direct execution without installation
python fb_downloader_cli.py <Facebook_Video_URL> [output_filename]

# From Python
python -c "from fb_downloader import Application; Application().run(['fbdl', 'URL'])"
```

### Testing
```bash
# Run all tests with coverage
python -m pytest tests/ -v --cov=fb_downloader --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_filename.py -v
```

### Code Quality
```bash
# Format code with Black
black src/ tests/ --line-length 100

# Check code style with Flake8
flake8 src/ tests/ --max-line-length=100

# Type checking with MyPy
mypy src/fb_downloader
```

## Architecture Overview

### Core Components

The application follows a modular architecture with clear separation of concerns:

1. **Entry Points**
   - `fbdl` command (via setuptools entry_points)
   - `fb_downloader_cli.py` (direct execution)
   - Main orchestration in `src/fb_downloader/core/application.py`

2. **Download Pipeline**
   - **Extractors** (`src/fb_downloader/extractors/`): Extract video metadata and URLs from Facebook pages
   - **Downloaders** (`src/fb_downloader/downloaders/`): Handle actual video downloading with progress tracking
   - **Fallback mechanism**: Tries yt-dlp first (it carries the browser session), then
     falls back to the built-in FacebookVideoDownloader for legacy public pages
   - **Attempt escalation** (`downloaders/ytdlp.py`): each URL is retried across
     (cookies × TLS impersonation). Facebook returns no video data unless the request
     carries both a logged-in session and a browser-like TLS fingerprint (curl_cffi),
     which is why `curl_cffi` is a hard requirement for Facebook reels.
   - **Quality**: format selection is `bv*+ba/b` capped via `format_sort: ["res:1080"]`.
     A `height<=1080` filter must not be used — it rejects vertical 1080x1920 reels.

3. **Key Features**
   - **Intelligent Filename Generation** (`src/fb_downloader/utils/filename.py`):
     - Names are `YYYYMMDD_<subject of the video>`; the account name is not part of it
     - The **post body** is the source of truth. On Instagram/Facebook the title
       field is a placeholder ("Video by xxx", "…の動画"), so it is consulted last
     - Resolution order: (1) a title the author declares on its own line in
       `『』`/`【】`, kept verbatim including emoji; (2) `claude -p` asked for the
       subject of the post (~5s, `CLAUDE_TIMEOUT=30` — 10s always lost the race);
       (3) the platform title when it is not a placeholder; (4) local summarization
     - `_sanitize_filename` keeps emoji (`EMOJI_RANGES`) and must NOT convert the
       katakana prolonged sound mark `ー` — doing so mangles シーザー into シ-ザ-
   - **URL Validation** (`src/fb_downloader/utils/validator.py`): Validates and cleans Facebook URLs
   - **Progress Tracking** (`src/fb_downloader/utils/progress.py`): Visual download progress with speed calculation

### Maintenance Tools

`src/fb_downloader/tools/rename.py` (`fbdl-rename`) re-applies the current naming
scheme to files already on disk, reading each video's subject from the `.txt`
saved beside it. Renaming is the default action — `-n` previews. It keeps the
existing `YYYYMMDD_` prefix (the original download date), moves the video/`.txt`/
`_yt.srt` as a set, and only touches names starting with `YYYYMMDD_` so unrelated
collections with same-named `.txt` files are not rewritten. Each run writes
`.fbdl-rename-undo.json` first, which `--undo` replays in reverse.

### Configuration

Configuration is managed via `config/settings.yaml` with the following structure:
- `download`: Chunk size, timeout, retry settings
- `headers`: User-Agent for HTTP requests
- `logging`: Log level and format
- `output`: Default directory and filename length limits

### Package Structure

The package uses `src/` layout with namespace package `fb_downloader`:
- All source code under `src/fb_downloader/`
- Configuration files in `config/` (included via package_data)
- Entry point defined in `setup.py` and `pyproject.toml`

### Dependencies

Core dependencies:
- `requests`: HTTP requests for video downloading
- `PyYAML`: Configuration file parsing

Optional:
- `yt-dlp`: Enhanced video extraction fallback

Development:
- `pytest`: Testing framework
- `black`: Code formatting
- `flake8`: Style checking
- `mypy`: Type checking