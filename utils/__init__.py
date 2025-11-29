"""
Utility functions and classes for Open Podcast Processor.
All functionality consolidated from p3/ directory.
"""

# Core classes
from .database import P3Database
from .downloader import PodcastDownloader
from .transcriber_groq import AudioTranscriber
from .cleaner_groq import TranscriptCleaner
from .config import get_groq_api_key, get_groq_model, get_api_key  # Backward compatibility

# Utility functions
from .processing import process_all_episodes, transcribe_episode, summarize_episode
from .download import download_feeds, load_feeds_config
from .db_util import (
    verify_schema,
    get_database_stats,
    query_podcasts,
    query_episodes,
    query_transcripts,
    query_summaries,
    test_database_operations
)
from .audio import check_ffmpeg_installed, normalize_audio
from .batch_download import batch_download_one_per_feed
from .batch_process import batch_transcribe_downloaded, batch_summarize_transcribed, batch_process_all
from .topic_analysis_groq import analyze_podcast_topics

__version__ = "0.1.0"

__all__ = [
    # Core classes
    'P3Database',
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
    # Database utilities
    'verify_schema',
    'get_database_stats',
    'query_podcasts',
    'query_episodes',
    'query_transcripts',
    'query_summaries',
    'test_database_operations',
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
