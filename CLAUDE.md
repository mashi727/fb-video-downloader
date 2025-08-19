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
   - **Fallback mechanism**: Tries FacebookVideoDownloader first, then suggests/uses yt-dlp as fallback

3. **Key Features**
   - **Intelligent Filename Generation** (`src/fb_downloader/utils/filename.py`):
     - Integrates with `claude -p` command for AI-powered Japanese filename generation
     - Falls back to local summarization if claude is unavailable
     - Handles both Japanese and English content appropriately
   - **URL Validation** (`src/fb_downloader/utils/validator.py`): Validates and cleans Facebook URLs
   - **Progress Tracking** (`src/fb_downloader/utils/progress.py`): Visual download progress with speed calculation

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