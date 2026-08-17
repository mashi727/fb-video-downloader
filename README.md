# Facebook Video Downloader

A robust Python package for downloading videos from Facebook with intelligent filename generation and comprehensive error handling.

## 🌟 Features

- 🎥 Download videos from various Facebook URL formats (Watch, Reel, Share, etc.)
- 📺 Support for HD/SD quality videos with automatic quality detection
- 🤖 Intelligent filename generation with AI assistance (using claude -p)
- 🔄 Fallback to yt-dlp for enhanced compatibility
- 📈 Real-time progress tracking with download speed and ETA
- 🔒 Robust error handling with retry logic
- ⚙️ Environment variable configuration support
- 🧪 Comprehensive test coverage
- 📦 Modular and extensible architecture

## 💻 Installation

### Basic Installation

```bash
git clone https://github.com/yourusername/fb-video-downloader.git
cd fb-video-downloader
pip install -r requirements.txt
python setup.py install
```

### Development Installation

```bash
# Install with all development dependencies
pip install -e ".[dev,ytdlp]"
```

### With yt-dlp Support (Required for Facebook)

```bash
pip install -e ".[ytdlp]"
```

This pulls in `yt-dlp` **and** `curl_cffi`. Facebook only returns video data to
clients with a browser-like TLS fingerprint, so `curl_cffi` (TLS impersonation)
is required for reels and watch pages. Keep yt-dlp current:

```bash
pip install -U --pre yt-dlp
```

### Platform notes

Runs on macOS, Linux and Windows (Python 3.8+). `ffmpeg` must be on PATH — every
mode uses it to merge or convert streams.

**Ubuntu / Debian**

```bash
sudo apt install -y ffmpeg python3-venv python3-pip
python3 -m venv ~/.venvs/fbdl && source ~/.venvs/fbdl/bin/activate
pip install -e ".[ytdlp]"
```

Cookies are read from the browser installed on the machine. On Linux, Firefox is
tried first: Chrome/Chromium store their cookie key in the GNOME keyring or
KWallet, which is unreachable over SSH or on a headless server, while Firefox's
`cookies.sqlite` can be read directly. If the machine has no browser session
(server, container), export cookies elsewhere and place them where yt-dlp can
find them, or run fbdl on the desktop machine.

Filename generation calls the optional `claude` CLI; without it, fbdl falls back
to local summarization automatically.

## 🚀 Usage

### Command Line Interface

After installation, you can use the `fbdl` command:

```bash
# Basic usage
fbdl https://www.facebook.com/watch/?v=123456789

# With custom output filename
fbdl https://www.facebook.com/watch/?v=123456789 my_video.mp4

# Various URL formats supported
fbdl https://www.facebook.com/reel/123456789
fbdl https://www.facebook.com/share/v/VIDEO_ID/
fbdl https://www.facebook.com/username/videos/987654321

# Audio / subtitle modes
fbdl 'https://youtu.be/VIDEO_ID' -a           # audio only (m4a)
fbdl 'https://youtu.be/VIDEO_ID' --subs       # video + SRT subtitles
fbdl 'https://youtu.be/VIDEO_ID' -S           # subtitles only

# Choose where login cookies come from (default: auto-detect)
fbdl 'https://www.facebook.com/reel/123456789' --browser chrome
fbdl 'https://youtu.be/VIDEO_ID' --browser none

# Direct execution without installation
python fb_downloader_cli.py <Facebook_Video_URL> [output_filename]
```

### How a download is attempted

For each URL, fbdl escalates through up to four strategies and stops at the
first success:

1. browser cookies + TLS impersonation (what Facebook reels require)
2. browser cookies only
3. TLS impersonation only
4. plain request

Cookies are taken from the first browser that holds a live session for the
target site (`c_user` for Facebook, `sessionid` for Instagram), extracted once
per run into a private temporary file that is deleted on exit.

### Python API

```python
from fb_downloader.core.application import Application
from fb_downloader.core.models import DownloadConfig

# Create application instance with custom config
config = DownloadConfig(
    chunk_size=16384,
    timeout=60,
    max_retries=5
)
app = Application()

# Download video
result = app.run(['fbdl', 'https://www.facebook.com/watch/?v=123456789'])

# Using specific downloader
from fb_downloader.downloaders.facebook import FacebookVideoDownloader

downloader = FacebookVideoDownloader(config)
success = downloader.download('https://www.facebook.com/watch/?v=123456789')
```

## 🤖 Intelligent Filename Generation

Files are named `YYYYMMDD_<subject of the video>` — the date it was downloaded
plus what the video is actually about. The account name is not part of the name.

The subject comes from the **post body**, since Instagram and Facebook give every
video a placeholder title ("Video by xxx", "…の動画"). Resolution order:

1. **A title the author declared** on a line of its own in `『』` or `【】`, kept
   verbatim including emoji — `『焼きシーザーサラダ🥬』` → `20260817_焼きシーザーサラダ🥬.mp4`
2. **`claude -p`**, asked for the subject of the post while ignoring the
   self-introduction, follow prompts, ingredients and steps — a body describing
   a cold dandan noodle recipe → `20260817_ピリ辛冷やし坦々そうめん.mp4`
3. **The platform title**, when it is not a placeholder (YouTube, for instance)
4. **Local summarization**, when `claude` is unavailable — the first line of the
   body that is not follow/save boilerplate

The description is saved alongside as `.txt` with the same base name. When two
videos resolve to the same name, `_2`, `_3` … is appended rather than
overwriting.

### Renaming older downloads

`fbdl-rename` applies the same naming to files that are already on disk, reading
the subject from the `.txt` saved next to each video. One command covers the
current folder and everything below it:

```bash
fbdl-rename                              # rename here, recursively
fbdl-rename -n                           # preview, change nothing
fbdl-rename ~/Movies ~/Desktop           # rename the given trees
fbdl-rename --undo .fbdl-rename-undo.json
```

- The video, its `.txt` and its `_yt.srt` are renamed together
- The existing `YYYYMMDD_` prefix is kept — that is the day fbdl downloaded it,
  and it is not replaced with today's date
- Only files starting with `YYYYMMDD_` are touched, so unrelated video
  collections that happen to keep a same-named `.txt` are left alone (`--all`
  lifts this)
- Every run writes `.fbdl-rename-undo.json` before renaming, so `--undo` can put
  the old names back
- `--no-claude` stays offline and uses only titles the post declares in `『』`/`【】`

Set `FBDL_CLAUDE_BIN` if the `claude` CLI is installed somewhere not on `PATH`.

## 📁 Project Structure

```
fb-video-downloader/
├── src/
│   └── fb_downloader/
│       ├── core/           # Core application logic
│       ├── downloaders/    # Video downloader implementations
│       ├── extractors/     # Video URL extractors
│       └── utils/          # Utility modules
├── tests/                  # Test suite
├── config/                 # Configuration files
└── docs/                   # Documentation
```

## ⚙️ Configuration

### Environment Variables

Configure via environment variables:

```bash
export FBDL_CHUNK_SIZE=16384        # Download chunk size in bytes
export FBDL_TIMEOUT=60              # Request timeout in seconds
export FBDL_MAX_RETRIES=5           # Maximum retry attempts
export FBDL_LOG_LEVEL=DEBUG         # Logging level
export FBDL_OUTPUT_DIR=/downloads   # Default output directory
```

### Configuration File

Or modify `config/settings.yaml`:

```yaml
download:
  chunk_size: 16384
  timeout: 60
  max_retries: 5

headers:
  user_agent: "Mozilla/5.0..."

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

output:
  directory: "."
  max_filename_length: 100
```

## Requirements

- Python 3.7+
- requests
- PyYAML
- yt-dlp (optional, for enhanced compatibility)

## 🔧 Development

### Running Tests

```bash
# Run all tests
PYTHONPATH=src python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=fb_downloader --cov-report=term-missing
```

### Code Quality

```bash
# Format code
black src/ tests/ --line-length 100

# Check style
flake8 src/ tests/ --max-line-length=100

# Type checking
mypy src/fb_downloader
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Legal Notice

**Important:** This tool is for educational purposes only. Please ensure you comply with:

- Copyright laws in your jurisdiction
- Facebook's Terms of Service
- Content creators' rights

Only download videos that you own or have explicit permission to download.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔍 Error Handling

The package includes comprehensive error handling:

- `VideoNotFoundError`: Raised when video cannot be found
- `NetworkError`: Network-related issues with status codes
- `ExtractionError`: Video extraction failures
- `ValidationError`: URL validation errors

All errors include detailed messages and context for debugging.

## 📝 Troubleshooting

### Common Issues

1. **Video not found**: The video might be private or the URL format has changed
2. **Network errors**: Check your internet connection and proxy settings
3. **yt-dlp not installed**: Install with `pip install yt-dlp` for better compatibility
4. **Facebook: "Cannot parse data"**: Facebook needs both a logged-in session
   and a browser TLS fingerprint. Check, in order:
   - `pip install "curl_cffi>=0.5.10"` (TLS impersonation)
   - Log in to Facebook in Safari or Chrome; on macOS the terminal needs
     Full Disk Access to read Safari cookies
   - Force a specific browser with `--browser chrome`, or skip cookies with
     `--browser none`
   - `pip install -U --pre yt-dlp` (extractors break whenever Facebook ships
     a change)

### Debug Mode

Enable debug logging:

```bash
export FBDL_LOG_LEVEL=DEBUG
```

Or in Python:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/yourusername/fb-video-downloader/issues) page.

## Acknowledgments

- Uses yt-dlp for enhanced video extraction capabilities
- Inspired by various open-source video downloaders