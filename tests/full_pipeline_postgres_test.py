#!/usr/bin/env python3
"""
Full pipeline test for one podcast episode using PostgreSQL only.
Tests: Download -> Transcribe -> Summarize
Verifies each step and ensures data is saved to PostgreSQL.
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.postgres_db import PostgresDB
from utils.download import load_feeds_config
from utils.downloader import PodcastDownloader
from utils.processing import transcribe_episode, summarize_episode
from utils.config import get_groq_api_key


def verify_postgres_episode(pg_db: PostgresDB, episode_url: str, step: str) -> dict:
    """Verify episode exists in PostgreSQL."""
    episode = pg_db.get_podcast_by_url(episode_url)
    if episode:
        print(f"  ✅ Found in PostgreSQL (ID: {episode['id']}, Status: {episode['status']})")
        return episode
    else:
        print(f"  ❌ Not found in PostgreSQL")
        return None


def test_full_pipeline():
    """Run full pipeline for first trading podcast."""
    print("=" * 70)
    print("FULL PIPELINE TEST: PostgreSQL Only")
    print("=" * 70)
    
    # Load feed configuration
    print("\n[STEP 0] Loading feed configuration...")
    config = load_feeds_config()
    feeds = config.get('feeds', [])
    
    if not feeds:
        print("❌ No feeds configured")
        return False
    
    # Get first trading podcast (should be at index 0)
    feed_config = feeds[0]
    feed_name = feed_config.get('name', 'Unknown')
    feed_url = feed_config.get('url')
    feed_category = feed_config.get('category', 'trading')
    
    print(f"✅ Using first feed: {feed_name}")
    print(f"   URL: {feed_url}")
    print(f"   Category: {feed_category}")
    
    # Initialize PostgreSQL database
    print("\n[STEP 1] Initializing PostgreSQL database...")
    pg_db = PostgresDB()
    print("✅ PostgreSQL database initialized")
    
    # Initialize downloader
    print("\n[STEP 2] Initializing downloader...")
    downloader = PodcastDownloader(
        db=pg_db,
        data_dir="data",
        max_episodes=1,
        audio_format="mp3"
    )
    print("✅ Downloader initialized")
    
    # ========================================================================
    # STEP 3: DOWNLOAD
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 3: DOWNLOAD EPISODE")
    print("=" * 70)
    
    # Add feed to PostgreSQL
    print(f"\n[3.1] Adding feed to PostgreSQL...")
    existing_podcast = pg_db.get_podcast_by_feed_url(feed_url)
    if existing_podcast:
        podcast_id = existing_podcast['id']
        print(f"  ✅ Feed already exists in PostgreSQL (ID: {podcast_id})")
    else:
        podcast_id = downloader.add_feed(feed_name, feed_url, feed_category)
        print(f"  ✅ Feed added to PostgreSQL (ID: {podcast_id})")
    
    # Fetch episodes
    print(f"\n[3.2] Fetching episodes from RSS feed...")
    episodes = downloader.fetch_episodes(feed_url, limit=1)
    
    if not episodes:
        print("  ❌ No episodes found in feed")
        pg_db.close()
        return False
    
    episode_data = episodes[0]
    episode_url = episode_data['url']
    print(f"  ✅ Found episode: {episode_data['title'][:70]}...")
    print(f"     URL: {episode_url[:80]}...")
    
    # Check if already downloaded
    print(f"\n[3.3] Checking if episode already downloaded...")
    if pg_db.episode_exists(episode_url):
        print(f"  ℹ️  Episode exists in PostgreSQL, checking file...")
        downloaded_episodes = pg_db.get_episodes_by_status('downloaded')
        episode = next((e for e in downloaded_episodes if e.get('episode_url') == episode_url), None)
        if episode and episode.get('audio_file_path') and Path(episode['audio_file_path']).exists():
            print(f"  ✅ Episode already downloaded")
            print(f"     File: {episode['audio_file_path']}")
            episode_id = episode['id']
            file_path = episode['audio_file_path']
        else:
            print(f"  ⚠️  Episode in DB but file missing, will download")
            episode_id = None
            file_path = None
    else:
        episode_id = None
        file_path = None
    
    # Download if needed
    if not file_path or not Path(file_path).exists():
        print(f"\n[3.4] Downloading episode...")
        from datetime import datetime
        safe_title = "".join(c for c in episode_data['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{podcast_id}_{safe_title[:50]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        file_path = downloader.download_episode(episode_data['url'], filename)
        
        if not file_path:
            print("  ❌ Download failed")
            duckdb.close()
            pg_db.close()
            return False
        
        print(f"  ✅ Download complete: {file_path}")
        
        # Save to PostgreSQL (already done in downloader.process_feed, but we'll do it here for clarity)
        print(f"\n[3.5] Saving to PostgreSQL...")
        # This is handled by downloader.process_feed, but we verify it here
        episode_id = None  # Will be set by save_podcast
    
    # Verify file exists and get info
    print(f"\n[3.6] Verifying downloaded file...")
    audio_path = Path(file_path)
    if audio_path.exists():
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        print(f"  ✅ File exists: {file_size_mb:.2f} MB")
        
        # Get duration using ffprobe if available
        duration_seconds = None
        try:
            import subprocess
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                duration_seconds = int(float(result.stdout.strip()))
                minutes = duration_seconds // 60
                seconds = duration_seconds % 60
                print(f"  ✅ Duration: {minutes}m{seconds}s ({duration_seconds}s)")
        except:
            print(f"  ⚠️  Could not get duration (ffprobe not available)")
    else:
        print(f"  ❌ File not found: {file_path}")
        pg_db.close()
        return False
    
    # Save to PostgreSQL
    print(f"\n[3.7] Saving to PostgreSQL...")
    try:
        pg_episode_id = pg_db.save_podcast(
            title=episode_data['title'],
            description=None,
            feed_url=feed_url,
            episode_url=episode_url,
            published_at=episode_data.get('date'),
            duration_seconds=duration_seconds,
            audio_file_path=file_path,
            file_size_bytes=audio_path.stat().st_size if audio_path.exists() else None,
            status='downloaded',
            transcript=None,
            summary=None,
            podcast_feed_name=feed_name,
            podcast_category=feed_category
        )
        print(f"  ✅ Saved to PostgreSQL (ID: {pg_episode_id})")
    except Exception as e:
        print(f"  ❌ Failed to save to PostgreSQL: {e}")
        import traceback
        traceback.print_exc()
        pg_db.close()
        return False
    
    # Verify in PostgreSQL
    print(f"\n[3.8] Verifying in PostgreSQL...")
    pg_episode = verify_postgres_episode(pg_db, episode_url, "download")
    if not pg_episode:
        print("  ❌ Episode not found in PostgreSQL after download")
        pg_db.close()
        return False
    
    episode_id = pg_episode['id']  # Use PostgreSQL ID
    
    print(f"\n✅ DOWNLOAD COMPLETE")
    print(f"   PostgreSQL Episode ID: {episode_id}")
    print(f"   File: {file_path}")
    print(f"   Size: {file_size_mb:.2f} MB")
    
    # ========================================================================
    # STEP 4: TRANSCRIBE
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 4: TRANSCRIBE EPISODE")
    print("=" * 70)
    
    print(f"\n[4.1] Starting transcription...")
    print(f"      Using PostgreSQL episode ID: {episode_id}")
    
    # Transcribe using PostgreSQL episode ID
    success, error = transcribe_episode(episode_id, pg_db)
    
    if not success:
        print(f"  ❌ Transcription failed: {error}")
        pg_db.close()
        return False
    
    print(f"  ✅ Transcription complete")
    
    # Verify in PostgreSQL
    print(f"\n[4.2] Verifying transcript in PostgreSQL...")
    pg_episode = pg_db.get_podcast_by_url(episode_url)
    
    if not pg_episode:
        print("  ❌ Episode not found in PostgreSQL")
        pg_db.close()
        return False
    
    if pg_episode['status'] != 'transcribed':
        print(f"  ⚠️  Status is '{pg_episode['status']}', expected 'transcribed'")
    
    if pg_episode.get('transcript'):
        transcript = pg_episode['transcript']
        if isinstance(transcript, dict):
            segments = transcript.get('segments', [])
            text = transcript.get('text', '')
            print(f"  ✅ Transcript found:")
            print(f"     Segments: {len(segments)}")
            print(f"     Text length: {len(text):,} characters")
            print(f"     Language: {transcript.get('language', 'unknown')}")
            
            if segments:
                sample = segments[0]
                print(f"     Sample: [{int(sample.get('start', 0))}s] {sample.get('text', '')[:80]}...")
        else:
            print(f"  ⚠️  Transcript exists but is not a dict (type: {type(transcript)})")
    else:
        print(f"  ❌ No transcript found in PostgreSQL")
        pg_db.close()
        return False
    
    print(f"\n✅ TRANSCRIPTION COMPLETE")
    print(f"   PostgreSQL Episode ID: {pg_episode['id']}")
    print(f"   Status: {pg_episode['status']}")
    print(f"   Transcript segments: {len(segments)}")
    
    # ========================================================================
    # STEP 5: SUMMARIZE
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 5: SUMMARIZE EPISODE")
    print("=" * 70)
    
    print(f"\n[5.1] Starting summarization...")
    print(f"      Using PostgreSQL episode ID: {episode_id}")
    
    # Summarize using PostgreSQL episode ID
    success, error, summary = summarize_episode(episode_id, pg_db)
    
    if not success:
        print(f"  ❌ Summarization failed: {error}")
        pg_db.close()
        return False
    
    print(f"  ✅ Summarization complete")
    
    # Verify in PostgreSQL
    print(f"\n[5.2] Verifying summary in PostgreSQL...")
    pg_episode = pg_db.get_podcast_by_url(episode_url)
    
    if not pg_episode:
        print("  ❌ Episode not found in PostgreSQL")
        pg_db.close()
        return False
    
    if pg_episode['status'] != 'processed':
        print(f"  ⚠️  Status is '{pg_episode['status']}', expected 'processed'")
    
    if pg_episode.get('summary'):
        summary_data = pg_episode['summary']
        if isinstance(summary_data, dict):
            print(f"  ✅ Summary found:")
            print(f"     Key topics: {len(summary_data.get('key_topics', []))}")
            print(f"     Themes: {len(summary_data.get('themes', []))}")
            print(f"     Quotes: {len(summary_data.get('quotes', []))}")
            print(f"     Companies: {len(summary_data.get('startups', []))}")
            
            if summary_data.get('key_topics'):
                print(f"     Topics: {', '.join(summary_data['key_topics'][:5])}")
            
            if summary_data.get('summary'):
                print(f"     Summary preview: {summary_data['summary'][:200]}...")
        else:
            print(f"  ⚠️  Summary exists but is not a dict (type: {type(summary_data)})")
    else:
        print(f"  ❌ No summary found in PostgreSQL")
        pg_db.close()
        return False
    
    print(f"\n✅ SUMMARIZATION COMPLETE")
    print(f"   PostgreSQL Episode ID: {pg_episode['id']}")
    print(f"   Status: {pg_episode['status']}")
    
    # ========================================================================
    # FINAL VERIFICATION
    # ========================================================================
    print("\n" + "=" * 70)
    print("FINAL VERIFICATION")
    print("=" * 70)
    
    print(f"\n[6.1] Final PostgreSQL check...")
    final_episode = pg_db.get_podcast_by_id(pg_episode['id'])
    
    if final_episode:
        print(f"  ✅ Episode found in PostgreSQL")
        print(f"     ID: {final_episode['id']}")
        print(f"     Title: {final_episode['title']}")
        print(f"     Status: {final_episode['status']}")
        print(f"     Podcast: {final_episode.get('podcast_feed_name', 'Unknown')}")
        print(f"     Category: {final_episode.get('podcast_category', 'Unknown')}")
        print(f"     File: {final_episode.get('audio_file_path', 'N/A')}")
        print(f"     Size: {final_episode.get('file_size_bytes', 0) / (1024*1024):.2f} MB" if final_episode.get('file_size_bytes') else "     Size: Unknown")
        print(f"     Duration: {final_episode.get('duration_seconds', 0) // 60}m{final_episode.get('duration_seconds', 0) % 60}s" if final_episode.get('duration_seconds') else "     Duration: Unknown")
        
        if final_episode.get('transcript'):
            transcript = final_episode['transcript']
            if isinstance(transcript, dict):
                print(f"     Transcript: ✅ ({len(transcript.get('segments', []))} segments)")
            else:
                print(f"     Transcript: ⚠️  (present but not dict)")
        else:
            print(f"     Transcript: ❌")
        
        if final_episode.get('summary'):
            summary = final_episode['summary']
            if isinstance(summary, dict):
                print(f"     Summary: ✅ ({len(summary.get('key_topics', []))} topics)")
            else:
                print(f"     Summary: ⚠️  (present but not dict)")
        else:
            print(f"     Summary: ❌")
        
        if final_episode.get('processed_at'):
            print(f"     Processed: {final_episode['processed_at']}")
    else:
        print(f"  ❌ Episode not found in PostgreSQL")
    
    duckdb.close()
    pg_db.close()
    
    print("\n" + "=" * 70)
    print("✅ FULL PIPELINE TEST COMPLETE")
    print("=" * 70)
    print(f"\nPipeline successfully completed for:")
    print(f"  Podcast: {feed_name}")
    print(f"  Episode: {episode_data['title']}")
    print(f"  PostgreSQL ID: {pg_episode['id']}")
    print(f"  Status: {pg_episode['status']}")
    print(f"\nAll data saved to PostgreSQL! ✅")
    
    return True


if __name__ == "__main__":
    try:
        success = test_full_pipeline()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

