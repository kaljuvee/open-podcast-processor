#!/usr/bin/env python3
"""
Test script to download episodes from the first 5 trading podcasts.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.postgres_db import PostgresDB
from utils.download import load_feeds_config
from utils.downloader import PodcastDownloader


def test_download_first_5_feeds():
    """Download 1 episode from each of the first 5 feeds."""
    print("=" * 70)
    print("DOWNLOAD TEST: First 5 Trading Podcasts")
    print("=" * 70)
    
    # Load feed configuration
    print("\n[1] Loading feed configuration...")
    config = load_feeds_config()
    feeds = config.get('feeds', [])
    
    if len(feeds) < 5:
        print(f"❌ Not enough feeds configured. Found {len(feeds)}, need at least 5")
        return False
    
    # Get first 5 feeds
    first_5_feeds = feeds[:5]
    
    print(f"✅ Found {len(feeds)} total feeds")
    print(f"📥 Will download from first {len(first_5_feeds)} feeds:\n")
    
    for i, feed in enumerate(first_5_feeds, 1):
        print(f"  {i}. {feed['name']} ({feed.get('category', 'N/A')})")
        print(f"     URL: {feed['url']}")
    
    # Initialize database and downloader
    print("\n[2] Initializing database and downloader...")
    db = PostgresDB()
    downloader = PodcastDownloader(
        db=db,
        data_dir="data",
        max_episodes=1,  # Only 1 episode per feed for testing
        audio_format="mp3"  # Use mp3 for faster processing
    )
    
    print("✅ PostgreSQL database and downloader initialized")
    
    # Process each feed
    print("\n[3] Downloading episodes...")
    print("=" * 70)
    
    results = {
        'total_downloaded': 0,
        'feed_results': {}
    }
    
    for idx, feed_config in enumerate(first_5_feeds, 1):
        feed_name = feed_config['name']
        feed_url = feed_config['url']
        feed_category = feed_config.get('category', 'general')
        
        print(f"\n[{idx}/5] Processing: {feed_name}")
        print("-" * 70)
        
        try:
            # Add feed to database (or get existing)
            existing_podcast = db.get_podcast_by_feed_url(feed_url)
            if existing_podcast:
                podcast_id = existing_podcast['id']
                print(f"  ✓ Feed already exists (ID: {podcast_id})")
            else:
                podcast_id = downloader.add_feed(
                    name=feed_name,
                    url=feed_url,
                    category=feed_category
                )
                print(f"  ✓ Feed added (ID: {podcast_id})")
            
            # Fetch episodes
            print(f"  📡 Fetching episodes from RSS feed...")
            episodes = downloader.fetch_episodes(feed_url, limit=1)
            
            if not episodes:
                print(f"  ⚠️  No episodes found in feed")
                results['feed_results'][feed_name] = {'downloaded': 0, 'error': 'No episodes found'}
                continue
            
            episode_data = episodes[0]
            print(f"  ✓ Found episode: {episode_data['title'][:70]}...")
            
            # Check if episode already exists in database
            if db.episode_exists(episode_data['url']):
                print(f"  ℹ️  Episode already exists in database, checking file...")
                all_episodes = db.get_episodes_by_status('downloaded')
                episode = next((e for e in all_episodes if e.get('episode_url') == episode_data['url']), None)
                if episode:
                    # Check if file actually exists on disk
                    file_path = episode.get('audio_file_path') or episode.get('file_path')
                    if file_path and Path(file_path).exists():
                        print(f"  ✓ Using existing episode (ID: {episode['id']})")
                        print(f"     File: {file_path}")
                        results['feed_results'][feed_name] = {'downloaded': 0, 'episode_id': episode['id'], 'existing': True}
                    else:
                        print(f"  ⚠️  Episode in DB but file missing, will re-download")
                        # Continue to download below
                    if file_path and Path(file_path).exists():
                        continue
                else:
                    print(f"  ⚠️  Episode marked as existing but not found, will download")
                    # Continue to download below
            
            # Download episode
            print(f"  📥 Downloading episode...")
            from datetime import datetime
            safe_title = "".join(c for c in episode_data['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{podcast_id}_{safe_title[:50]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            file_path = downloader.download_episode(episode_data['url'], filename)
            
            if not file_path:
                print(f"  ❌ Failed to download episode")
                results['feed_results'][feed_name] = {'downloaded': 0, 'error': 'Download failed'}
                continue
            
            print(f"  ✓ Episode downloaded: {file_path}")
            
            # Add to database using PostgreSQL save_podcast method
            print(f"  💾 Saving to PostgreSQL...")
            # Calculate file size
            file_size_bytes = None
            if Path(file_path).exists():
                file_size_bytes = Path(file_path).stat().st_size
            
            episode_id = db.save_podcast(
                title=episode_data['title'],
                description=episode_data.get('description'),
                feed_url=feed_url,
                episode_url=episode_data['url'],
                published_at=episode_data['date'],
                audio_file_path=file_path,
                file_size_bytes=file_size_bytes,
                status='downloaded',
                podcast_feed_name=feed_name,
                podcast_category=feed_category
            )
            
            print(f"  ✅ Episode saved (ID: {episode_id})")
            results['feed_results'][feed_name] = {'downloaded': 1, 'episode_id': episode_id}
            results['total_downloaded'] += 1
            
        except Exception as e:
            print(f"  ❌ Error processing feed: {e}")
            import traceback
            traceback.print_exc()
            results['feed_results'][feed_name] = {'downloaded': 0, 'error': str(e)}
    
    # Summary
    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    print(f"\nTotal episodes downloaded: {results['total_downloaded']}")
    print("\nFeed Results:")
    for feed_name, feed_result in results['feed_results'].items():
        if feed_result.get('downloaded', 0) > 0:
            print(f"  ✅ {feed_name}: Downloaded episode ID {feed_result.get('episode_id')}")
        elif feed_result.get('existing'):
            print(f"  ℹ️  {feed_name}: Using existing episode ID {feed_result.get('episode_id')}")
        else:
            print(f"  ⚠️  {feed_name}: {feed_result.get('error', 'Unknown error')}")
    
    # Show downloaded episodes ready for transcription
    print("\n" + "=" * 70)
    print("EPISODES READY FOR TRANSCRIPTION")
    print("=" * 70)
    downloaded_episodes = db.get_episodes_by_status('downloaded')
    
    if downloaded_episodes:
        print(f"\nFound {len(downloaded_episodes)} episode(s) with status 'downloaded':\n")
        for ep in downloaded_episodes[:10]:  # Show first 10
            print(f"  ID: {ep['id']} - {ep['title'][:60]}...")
            print(f"      Podcast: {ep.get('podcast_title', 'Unknown')}")
            print(f"      File: {ep.get('file_path', 'N/A')}")
            print()
    else:
        print("\n⚠️  No episodes with 'downloaded' status found")
    
    db.close()
    
    print("=" * 70)
    if results['total_downloaded'] > 0:
        print("✅ Download test completed successfully!")
        print(f"   Ready to transcribe {len(downloaded_episodes)} episode(s)")
    else:
        print("ℹ️  Download test completed (no new episodes downloaded)")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    try:
        test_download_first_5_feeds()
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Download test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

