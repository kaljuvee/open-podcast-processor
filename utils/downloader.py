"""Podcast episode downloader and RSS feed processor."""

import os
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
import feedparser
# from pydub import AudioSegment  # Disabled due to Python 3.13 compatibility
import subprocess
import re

from utils.postgres_db import PostgresDB


def create_slug(text: str, max_length: int = 100) -> str:
    """
    Create a URL-friendly slug from text.
    
    Args:
        text: Text to convert to slug
        max_length: Maximum length of slug
        
    Returns:
        Slug string
    """
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove all non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    # Replace multiple hyphens with single hyphen
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')
    return slug


class PodcastDownloader:
    def __init__(self, db: PostgresDB, data_dir: str = "data", 
                 max_episodes: int = 10, audio_format: str = "wav"):
        self.db = db
        self.data_dir = Path(data_dir)
        self.audio_dir = self.data_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.max_episodes = max_episodes
        self.audio_format = audio_format

    def add_feed(self, name: str, url: str, category: str = None) -> int:
        """Add a new podcast feed to the database."""
        # Check if feed already exists by looking for any episode with this feed_url
        existing = self.db.get_podcast_by_feed_url(url)
        if existing:
            return existing["id"]
        # Create a placeholder entry to track the feed
        # We use a special episode_url pattern to identify feed entries
        feed_episode_url = f"__feed__:{url}"
        existing_feed = self.db.get_podcast_by_url(feed_episode_url)
        if existing_feed:
            return existing_feed["id"]
        
        # Create new feed entry
        podcast_id = self.db.save_podcast(
            title=f"Feed: {name}",
            feed_url=url,
            episode_url=feed_episode_url,  # Special marker for feed entries
            podcast_feed_name=name,
            podcast_category=category,
            status='downloaded'
        )
        return podcast_id

    def fetch_episodes(self, rss_url: str, limit: int = None) -> List[Dict]:
        """Fetch episode metadata from RSS feed."""
        if limit is None:
            limit = self.max_episodes

        try:
            feed = feedparser.parse(rss_url)
            episodes = []
            
            for entry in feed.entries[:limit]:
                # Find audio enclosure
                audio_url = None
                for enclosure in entry.get('enclosures', []):
                    if enclosure.type and 'audio' in enclosure.type:
                        audio_url = enclosure.href
                        break
                
                if not audio_url:
                    continue

                # Parse publication date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

                episodes.append({
                    'title': entry.get('title', 'Unknown Title'),
                    'url': audio_url,
                    'date': pub_date,
                    'description': entry.get('description', ''),
                    'guid': entry.get('id', audio_url)
                })
            
            return episodes
            
        except Exception as e:
            print(f"Error fetching RSS feed {rss_url}: {e}")
            return []

    def download_episode(self, episode_url: str, filename: str) -> Optional[str]:
        """Download and normalize audio episode."""
        import time
        
        try:
            # Check if output file already exists
            output_path = self.audio_dir / f"{filename}.{self.audio_format}"
            if output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"  ℹ️  File already exists: {output_path.name}")
                print(f"     Size: {file_size_mb:.2f} MB")
                print(f"     Skipping download")
                return str(output_path)
            
            download_start = time.time()
            
            # Download audio file
            print(f"  📥 Downloading audio from URL...")
            print(f"     URL: {episode_url[:80]}...")
            
            response = requests.get(episode_url, stream=True, timeout=300)
            response.raise_for_status()
            
            # Get content length if available
            content_length = response.headers.get('Content-Length')
            total_size = int(content_length) if content_length else None
            
            if total_size:
                total_size_mb = total_size / (1024 * 1024)
                print(f"     File size: {total_size_mb:.2f} MB")
            
            # Save to temporary file with slug-based name
            print(f"     Saving to temporary file...")
            # Create slug from filename for temp file
            slug = create_slug(filename)
            temp_dir = self.audio_dir / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = temp_dir / f"{slug}_downloaded.tmp"
            
            downloaded_bytes = 0
            with open(tmp_path, 'wb') as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    if total_size:
                        progress = (downloaded_bytes / total_size) * 100
                        if downloaded_bytes % (1024 * 1024) == 0:  # Print every MB
                            print(f"     Progress: {progress:.1f}% ({downloaded_bytes / (1024*1024):.1f} MB)", end='\r')
            
            print(f"     Temp file: {tmp_path.name}")
            
            download_time = time.time() - download_start
            print(f"\n     ✅ Download complete ({download_time:.1f}s)")
            if total_size:
                speed_mbps = (total_size / (1024 * 1024)) / download_time if download_time > 0 else 0
                print(f"     ⚡ Download speed: {speed_mbps:.2f} MB/s")

            # Convert and normalize with ffmpeg
            # output_path already defined above, but check again in case it was created
            if output_path.exists():
                print(f"\n  ℹ️  Output file already exists, skipping processing")
                return str(output_path)
            
            print(f"\n  🎵 Processing audio with ffmpeg...")
            print(f"     Input: {tmp_path}")
            print(f"     Output: {output_path}")
            print(f"     Format: {self.audio_format}")
            print(f"     Settings: 16kHz, mono, normalized")
            
            # Use ffmpeg for reliable audio processing and normalization
            cmd = [
                'ffmpeg', '-y',  # overwrite existing files
                '-i', tmp_path,
                '-ar', '16000',  # 16kHz sample rate for Whisper
                '-ac', '1',      # mono
                '-c:a', 'pcm_s16le' if self.audio_format == 'wav' else 'libmp3lame',
                '-af', 'loudnorm',  # normalize audio levels
                '-loglevel', 'info',  # Show progress info
                str(output_path)
            ]
            
            ffmpeg_start = time.time()
            
            # Run ffmpeg with timeout - show output for progress
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=600  # 10 minute timeout for large files
            )
            
            ffmpeg_time = time.time() - ffmpeg_start
            
            if result.returncode != 0:
                print(f"     ⚠️  FFmpeg error (exit code {result.returncode}):")
                print(f"     {result.stderr[:500]}")
                print(f"     Trying fallback conversion...")
                # Fallback to simpler conversion
                return self._fallback_conversion(tmp_path, output_path)
            
            # Show ffmpeg output for diagnostics
            if result.stdout:
                # Extract useful info from ffmpeg output
                lines = result.stdout.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['duration', 'bitrate', 'size', 'time=']):
                        print(f"     {line.strip()}")
            
            print(f"     ✅ Audio processing complete ({ffmpeg_time:.1f}s)")
            
            # Get output file size
            if output_path.exists():
                output_size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"     Output size: {output_size_mb:.2f} MB")
            
            # Keep temp file for debugging (no cleanup)
            print(f"     ℹ️  Temp file kept: {tmp_path}")
            
            total_time = time.time() - download_start
            print(f"\n  ✅ Download and processing complete!")
            print(f"     Total time: {int(total_time//60)}m{int(total_time%60)}s ({total_time:.1f}s)")
            
            return str(output_path)
            
        except Exception as e:
            print(f"  ❌ Error downloading {episode_url}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _fallback_conversion(self, input_path: str, output_path: Path) -> str:
        """Fallback audio conversion using ffmpeg directly."""
        try:
            # Use ffmpeg without pydub as fallback
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-ar', '16000', '-ac', '1',
                str(output_path)
            ]
            # Run ffmpeg with timeout - works in Streamlit subprocess mode
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                # Keep temp file for debugging (no cleanup)
                print(f"     ℹ️  Temp file kept: {input_path}")
                return str(output_path)
            else:
                print(f"Fallback conversion failed: {result.stderr}")
                print(f"     ℹ️  Temp file kept: {input_path}")
                return None
            
        except Exception as e:
            print(f"Fallback conversion failed: {e}")
            print(f"     ℹ️  Temp file kept: {input_path}")
            return None

    def process_feed(self, rss_url: str) -> int:
        """Process a single RSS feed and download new episodes."""
        # Get feed info (stored as podcast with feed_url)
        podcast = self.db.get_podcast_by_feed_url(rss_url)
        if not podcast:
            print(f"Podcast feed not found for URL: {rss_url}")
            return 0

        episodes = self.fetch_episodes(rss_url)
        downloaded_count = 0
        
        # Get feed name and category from podcast
        feed_name = podcast.get('podcast_feed_name') or podcast.get('title', 'Unknown')
        feed_category = podcast.get('podcast_category', 'general')
        
        for ep_data in episodes:
            # Skip if episode already exists
            if self.db.episode_exists(ep_data['url']):
                continue
                
            print(f"Downloading: {ep_data['title']}")
            
            # Generate safe filename
            safe_title = "".join(c for c in ep_data['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{podcast['id']}_{safe_title[:50]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Download episode
            file_path = self.download_episode(ep_data['url'], filename)
            if file_path:
                # Calculate file size
                file_size_bytes = None
                if Path(file_path).exists():
                    file_size_bytes = Path(file_path).stat().st_size
                
                # Add to PostgreSQL database
                episode_id = self.db.save_podcast(
                    title=ep_data['title'],
                    description=ep_data.get('description'),
                    feed_url=rss_url,
                    episode_url=ep_data['url'],
                    published_at=ep_data['date'],
                    duration_seconds=None,  # Will be calculated later if needed
                    audio_file_path=file_path,
                    file_size_bytes=file_size_bytes,
                    status='downloaded',
                    transcript=None,
                    summary=None,
                    podcast_feed_name=feed_name,
                    podcast_category=feed_category
                )
                downloaded_count += 1
                print(f"✓ Downloaded: {ep_data['title']} (ID: {episode_id})")
            else:
                print(f"✗ Failed to download: {ep_data['title']}")
        
        return downloaded_count

    def fetch_all_feeds(self, feeds_config: List[Dict]) -> Dict[str, int]:
        """Process all configured RSS feeds."""
        results = {}
        
        for feed_config in feeds_config:
            name = feed_config['name']
            url = feed_config['url']
            category = feed_config.get('category')
            
            print(f"Processing feed: {name}")
            
            # Ensure podcast exists in database
            self.add_feed(name, url, category)
            
            # Process episodes
            count = self.process_feed(url)
            results[name] = count
            
            print(f"Downloaded {count} new episodes from {name}")
        
        return results
