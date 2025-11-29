"""
Utility functions and classes for Open Podcast Processor.
All functionality consolidated from p3/ directory.
"""

# Core classes
# Note: P3Database (DuckDB) removed - use PostgresDB instead
from .downloader import PodcastDownloader
from .transcriber_groq import AudioTranscriber
from .cleaner_groq import TranscriptCleaner
from .config import get_groq_api_key, get_groq_model, get_api_key  # Backward compatibility

# Utility functions
from .processing import process_all_episodes, transcribe_episode, summarize_episode
from .download import download_feeds, load_feeds_config
# Note: db_util functions removed - they depend on DuckDB P3Database
from .audio import check_ffmpeg_installed, normalize_audio
from .batch_download import batch_download_one_per_feed
from .batch_process import batch_transcribe_downloaded, batch_summarize_transcribed, batch_process_all
from .topic_analysis_groq import analyze_podcast_topics

__version__ = "0.1.0"

__all__ = [
    # Core classes
    'PodcastDownloader',
    'AudioTranscriber',
    'TranscriptCleaner',
    'get_api_key',  # Backward compatibility alias
    'get_groq_api_key',
    'get_groq_model',
    # Processing utilities
    'process_all_episodes',
    'transcribe_episode',
    'summarize_episode',
    # Download utilities
    'download_feeds',
    'load_feeds_config',
    # Audio utilities
    'check_ffmpeg_installed',
    'normalize_audio',
    # Batch utilities
    'batch_download_one_per_feed',
    'batch_transcribe_downloaded',
    'batch_summarize_transcribed',
    'batch_process_all',
    # Topic analysis
    'analyze_podcast_topics'
]
