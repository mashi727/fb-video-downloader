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

### With yt-dlp Support (Recommended)

```bash
pip install -e ".[ytdlp]"
```

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

# Direct execution without installation
python fb_downloader_cli.py <Facebook_Video_URL> [output_filename]
```

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

The package features smart filename generation:

1. **AI-Powered** (with claude -p): Automatically generates concise, meaningful filenames
2. **Smart Fallback**: Uses local summarization algorithm when claude is unavailable
3. **Safety**: Sanitizes filenames to be filesystem-safe across all platforms

Example outputs:
- Video titled "Amazing sunset at Mount Fuji" → `20240101_富士山_夕焼け.mp4`
- Video from user "TechNews" → `20240101_TechNews_latest_update.mp4`
- Video without metadata → `20240101_fb_video_123456.mp4`

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