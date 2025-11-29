"""
Download utilities for fetching podcast episodes.
Extracted from Streamlit pages.
"""

from typing import List, Dict, Optional
from pathlib import Path
import yaml
from utils.downloader import PodcastDownloader
from utils.postgres_db import PostgresDB


def load_feeds_config(config_path: Optional[Path] = None) -> Dict:
    """
    Load feeds configuration from YAML file.
    
    Args:
        config_path: Path to feeds.yaml (defaults to config/feeds.yaml)
        
    Returns:
        Dictionary with 'feeds' and 'settings' keys
    """
    if config_path is None:
        config_path = Path("config/feeds.yaml")
    
    if not config_path.exists():
        # Create default config
        config_path.parent.mkdir(parents=True, exist_ok=True)
        default_config = {
            'feeds': [],
            'settings': {
                'max_episodes_per_feed': 5,
                'download_dir': 'data/audio'
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        return default_config
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def download_feeds(
    feed_configs: List[Dict],
    max_episodes: int = 5,
    db: Optional[PostgresDB] = None,
    data_dir: str = "data",
    audio_format: str = "wav"
) -> Dict[str, int]:
    """
    Download episodes from multiple feeds.
    This is a wrapper around PodcastDownloader.fetch_all_feeds() for convenience.
    
    Args:
        feed_configs: List of feed configuration dicts (with 'name', 'url', 'category')
        max_episodes: Maximum episodes per feed
        db: Database instance (creates new PostgreSQL if not provided)
        data_dir: Directory for storing downloaded files
        audio_format: Audio format (wav, mp3)
        
    Returns:
        Dictionary with download results: {
            'total_downloaded': int,
            'feed_results': Dict[str, int]  # feed_name -> count
        }
    """
    if db is None:
        db = PostgresDB()
        should_close = True
    else:
        should_close = False
    
    try:
        downloader = PodcastDownloader(
            db=db,
            data_dir=data_dir,
            max_episodes=max_episodes,
            audio_format=audio_format
        )
        
        # Use the core method from PodcastDownloader
        results_dict = downloader.fetch_all_feeds(feed_configs)
        
        # Convert to expected format
        results = {
            'total_downloaded': sum(results_dict.values()),
            'feed_results': results_dict
        }
        
        return results
    finally:
        if should_close and db:
            db.close()

