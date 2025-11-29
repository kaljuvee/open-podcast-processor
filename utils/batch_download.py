"""
Batch download utility for demo purposes.
Downloads 1 episode from each feed in config/feeds.yaml.
Uses PostgreSQL and skips already downloaded episodes.
"""

from typing import Dict, List, Optional
from pathlib import Path
from utils.postgres_db import PostgresDB
from utils.downloader import PodcastDownloader
from utils.download import load_feeds_config


def batch_download_one_per_feed(
    db: Optional[PostgresDB] = None,
    data_dir: str = "data",
    config_path: Optional[Path] = None,
    audio_format: str = "mp3"
) -> Dict[str, any]:
    """
    Download 1 episode from each feed configured in feeds.yaml.
    
    Args:
        db: Database instance (creates new if not provided)
        data_dir: Directory for storing downloaded files
        config_path: Path to feeds.yaml (defaults to config/feeds.yaml)
        
    Returns:
        Dictionary with download results: {
            'total_downloaded': int,
            'feed_results': Dict[str, Dict]  # feed_name -> {count: int, episode: Dict}
            'episodes': List[Dict]  # List of downloaded episode info
        }
    """
    if db is None:
        db = PostgresDB()
        should_close = True
    else:
        should_close = False
    
    results = {
        'total_downloaded': 0,
        'feed_results': {},
        'episodes': []
    }
    
    try:
        # Load feed configuration
        config = load_feeds_config(config_path)
        feeds = config.get('feeds', [])
        
        if not feeds:
            results['error'] = "No feeds configured in config/feeds.yaml"
            return results
        
        # Initialize downloader with max_episodes=1 per feed
        downloader = PodcastDownloader(
            db=db,
            data_dir=data_dir,
            max_episodes=1,  # Only 1 episode per feed for demo
            audio_format=audio_format
        )
        
        print(f"📥 Batch downloading 1 episode from each of {len(feeds)} feeds...")
        
        for feed_config in feeds:
            feed_name = feed_config.get('name', 'Unknown')
            feed_url = feed_config.get('url')
            category = feed_config.get('category', 'general')
            
            if not feed_url:
                print(f"⚠️  Skipping {feed_name}: No URL provided")
                results['feed_results'][feed_name] = {
                    'count': 0,
                    'error': 'No URL provided'
                }
                continue
            
            try:
                print(f"  Processing: {feed_name}")
                
                # Add feed to database if needed
                podcast_id = downloader.add_feed(feed_name, feed_url, category)
                
                # Process feed and download 1 episode
                count = downloader.process_feed(feed_url)
                
                # Get the downloaded episode info for this podcast
                # Find episodes by feed_url (PostgreSQL doesn't have podcast_id)
                episodes = db.get_episodes_by_status('downloaded')
                feed_episodes = [
                    ep for ep in episodes 
                    if ep.get('feed_url') == feed_url
                ]
                
                episode_info = None
                if feed_episodes:
                    # Get the most recently created episode for this feed
                    latest_episode = feed_episodes[0]  # Already sorted by date DESC
                    episode_info = {
                        'id': latest_episode['id'],
                        'title': latest_episode['title'],
                        'url': latest_episode.get('episode_url') or latest_episode.get('url'),
                        'file_path': latest_episode.get('audio_file_path') or latest_episode.get('file_path'),
                        'podcast_name': feed_name,
                        'feed_url': feed_url
                    }
                    results['episodes'].append(episode_info)
                
                results['feed_results'][feed_name] = {
                    'count': count,
                    'episode': episode_info
                }
                results['total_downloaded'] += count
                
                if count > 0:
                    print(f"    ✓ Downloaded {count} episode(s) from {feed_name}")
                else:
                    print(f"    ⚠️  No new episodes from {feed_name} (may already exist)")
                    
            except Exception as e:
                print(f"    ✗ Error downloading from {feed_name}: {str(e)}")
                results['feed_results'][feed_name] = {
                    'count': 0,
                    'error': str(e)
                }
        
        print(f"\n✅ Batch download complete: {results['total_downloaded']} total episodes downloaded")
        
        return results
        
    finally:
        if should_close and db:
            db.close()

