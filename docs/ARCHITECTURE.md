# Architecture Overview

## Directory Structure Rationalization

### `utils/` - All Functionality Consolidated
All classes and utilities consolidated in utils/ directory:

- **`database.py`** - `P3Database` class
  - Database schema management
  - CRUD operations for podcasts, episodes, transcripts, summaries
  - No duplicate logic

- **`downloader.py`** - `PodcastDownloader` class
  - RSS feed parsing
  - Episode downloading
  - Audio normalization with ffmpeg
  - `fetch_all_feeds()` - processes multiple feeds
  - `process_feed()` - processes single feed

- **`transcriber_xai.py`** - `AudioTranscriber` class (XAI API)
  - Audio transcription using XAI Whisper API
  - `transcribe_episode()` - transcribe single episode
  - `transcribe_all_pending()` - transcribe all downloaded episodes

- **`cleaner_xai.py`** - `TranscriptCleaner` class (XAI API)
  - Transcript summarization using XAI Grok API
  - `generate_summary()` - summarize single episode
  - `process_all_transcribed()` - process all transcribed episodes

- **`config.py`** - Configuration utilities
  - `get_api_key()` - loads XAI_API_KEY via python-dotenv

- **`cli.py`** - Command-line interface
  - Uses `utils.download.load_feeds_config()` for config loading
  - Uses core classes directly

- **`download.py`** - Download utilities
  - `load_feeds_config()` - loads config from YAML (used by CLI and pages)
  - `download_feeds()` - wrapper around `PodcastDownloader.fetch_all_feeds()`
    - Handles DB lifecycle (creates/closes if needed)
    - Returns consistent format with `total_downloaded` key

- **`processing.py`** - Processing utilities
  - `transcribe_episode()` - wrapper around `AudioTranscriber.transcribe_episode()`
    - Handles API key loading
    - Returns (success, error) tuple for easier error handling
  - `summarize_episode()` - wrapper around `TranscriptCleaner.generate_summary()`
    - Handles API key loading
    - Returns (success, error, summary) tuple
  - `process_all_episodes()` - orchestrates transcription and summarization
    - Uses core class methods directly
    - Returns aggregated results

- **`db_util.py`** - Database utilities
  - Query functions: `query_podcasts()`, `query_episodes()`, etc.
  - Schema verification: `verify_schema()`
  - Statistics: `get_database_stats()`
  - Test utilities: `test_database_operations()`

- **`audio.py`** - Audio utilities
  - `check_ffmpeg_installed()` - checks if ffmpeg is available
  - `normalize_audio()` - audio normalization utility

## Design Principles

1. **Consolidated Structure**
   - All functionality in `utils/` directory
   - Core classes and utility functions in same location
   - No separation between "core" and "utils" - everything is utils

2. **No Duplication**
   - Utility functions wrap classes, don't duplicate logic
   - `download_feeds()` uses `PodcastDownloader.fetch_all_feeds()` internally
   - `process_all_episodes()` uses class methods directly

3. **Single Source of Truth**
   - Config loading: `utils.download.load_feeds_config()` (used by CLI and pages)
   - API key: `utils.config.get_api_key()` (used by all modules)
   - Database: `utils.database.P3Database` (used by all modules)

4. **Clear Responsibilities**
   - Classes handle their domain logic
   - Utility functions provide simplified interfaces for common operations
   - Pages/CLI use utilities for convenience, classes for advanced usage

## Usage Patterns

### Streamlit Pages
```python
from utils.download import load_feeds_config, download_feeds
from utils.processing import process_all_episodes

# Simple, clean interface
config = load_feeds_config()
results = download_feeds(feed_configs=feeds, db=db)
```

### CLI
```python
from utils.download import load_feeds_config
from utils.downloader import PodcastDownloader

# Uses utils for config and classes
config = load_feeds_config()
downloader = PodcastDownloader(db)
results = downloader.fetch_all_feeds(config['feeds'])
```

### Direct Class Usage
```python
from utils.downloader import PodcastDownloader
from utils.transcriber_xai import AudioTranscriber

# Full control, no wrappers
downloader = PodcastDownloader(db)
transcriber = AudioTranscriber(db, api_key=api_key)
```

