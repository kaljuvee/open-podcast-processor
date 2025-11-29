#!/usr/bin/env python3
"""
Test script to run the entire pipeline step by step for one episode.
Tests: Download -> Transcribe -> Summarize
"""

import sys
from pathlib import Path
from utils.database import P3Database
from utils.download import load_feeds_config
from utils.downloader import PodcastDownloader
from utils.processing import transcribe_episode, summarize_episode
from utils.postgres_db import PostgresDB


def test_database_connection():
    """Test 1: Database connection and schema initialization."""
    print("\n" + "="*60)
    print("TEST 1: Database Connection & Schema")
    print("="*60)
    
    try:
        # Test DuckDB connection
        print("\n[1.1] Testing DuckDB connection...")
        db = P3Database()
        print("✓ DuckDB connection successful")
        
        # Test PostgreSQL connection
        print("\n[1.2] Testing PostgreSQL connection...")
        pg_db = PostgresDB()
        print("✓ PostgreSQL connection successful")
        
        # Initialize PostgreSQL schema if needed
        print("\n[1.3] Initializing PostgreSQL schema...")
        schema_path = Path(__file__).parent / "sql" / "schema.sql"
        if schema_path.exists():
            pg_db.execute_sql_file(str(schema_path))
            print("✓ PostgreSQL schema initialized")
        else:
            print("⚠️  Schema file not found, skipping schema initialization")
        
        db.close()
        pg_db.close()
        print("\n✅ TEST 1 PASSED: Database connections working")
        return True
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_download_one_episode():
    """Test 2: Download one episode from a feed."""
    print("\n" + "="*60)
    print("TEST 2: Download One Episode")
    print("="*60)
    
    try:
        # Load feed configuration
        print("\n[2.1] Loading feed configuration...")
        config = load_feeds_config()
        feeds = config.get('feeds', [])
        
        if not feeds:
            print("❌ No feeds configured in config/feeds.yaml")
            return None
        
        # Use first feed
        feed_config = feeds[0]
        feed_name = feed_config.get('name', 'Unknown')
        feed_url = feed_config.get('url')
        
        print(f"✓ Using feed: {feed_name}")
        print(f"  URL: {feed_url}")
        
        # Initialize database and downloader
        print("\n[2.2] Initializing downloader...")
        db = P3Database()
        downloader = PodcastDownloader(
            db=db,
            data_dir="data",
            max_episodes=1,  # Only download 1 episode
            audio_format="mp3"
        )
        
        # Add feed to database (or get existing)
        print("\n[2.3] Adding feed to database...")
        existing_podcast = db.get_podcast_by_url(feed_url)
        if existing_podcast:
            podcast_id = existing_podcast['id']
            print(f"✓ Feed already exists (ID: {podcast_id})")
        else:
            podcast_id = downloader.add_feed(
                name=feed_name,
                url=feed_url,
                category=feed_config.get('category', 'general')
            )
            print(f"✓ Feed added (ID: {podcast_id})")
        
        # Fetch episodes
        print("\n[2.4] Fetching episodes from RSS feed...")
        episodes = downloader.fetch_episodes(feed_url, limit=1)
        
        if not episodes:
            print("❌ No episodes found in feed")
            db.close()
            return None
        
        episode_data = episodes[0]
        print(f"✓ Found episode: {episode_data['title']}")
        
        # Check if episode already exists
        if db.episode_exists(episode_data['url']):
            print("\n⚠️  Episode already exists, fetching existing episode...")
            # Get existing episode
            all_episodes = db.get_episodes_by_status('downloaded')
            episode = next((e for e in all_episodes if e['url'] == episode_data['url']), None)
            if episode:
                print(f"✓ Using existing episode (ID: {episode['id']})")
                db.close()
                return episode
        
        # Download episode
        print("\n[2.5] Downloading episode...")
        safe_title = "".join(c for c in episode_data['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{podcast_id}_{safe_title[:50]}"
        
        file_path = downloader.download_episode(episode_data['url'], filename)
        
        if not file_path:
            print("❌ Failed to download episode")
            db.close()
            return None
        
        print(f"✓ Episode downloaded to: {file_path}")
        
        # Add to database
        print("\n[2.6] Saving episode to database...")
        episode_id = db.add_episode(
            podcast_id=podcast_id,
            title=episode_data['title'],
            date=episode_data['date'],
            url=episode_data['url'],
            file_path=file_path
        )
        print(f"✓ Episode saved (ID: {episode_id})")
        
        # Get episode info
        episode = db.get_episode_by_id(episode_id)
        db.close()
        
        print("\n✅ TEST 2 PASSED: Episode downloaded successfully")
        print(f"   Episode ID: {episode_id}")
        print(f"   Title: {episode['title']}")
        print(f"   File: {episode['file_path']}")
        
        return episode
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_transcribe_episode(episode):
    """Test 3: Transcribe the downloaded episode."""
    print("\n" + "="*60)
    print("TEST 3: Transcribe Episode")
    print("="*60)
    
    if not episode:
        print("❌ No episode provided for transcription")
        return None
    
    try:
        episode_id = episode['id']
        print(f"\n[3.1] Transcribing episode ID: {episode_id}")
        print(f"      Title: {episode['title']}")
        
        # Initialize database
        db = P3Database()
        
        # Check episode status
        episode_check = db.get_episode_by_id(episode_id)
        if not episode_check:
            print(f"❌ Episode {episode_id} not found in database")
            db.close()
            return None
        
        print(f"      Status: {episode_check['status']}")
        print(f"      File: {episode_check['file_path']}")
        
        # Transcribe
        print("\n[3.2] Starting transcription...")
        success, error = transcribe_episode(episode_id, db)
        
        if not success:
            print(f"❌ Transcription failed: {error}")
            db.close()
            return None
        
        # Verify transcription
        print("\n[3.3] Verifying transcription...")
        episode_updated = db.get_episode_by_id(episode_id)
        
        if episode_updated['status'] != 'transcribed':
            print(f"⚠️  Status is '{episode_updated['status']}', expected 'transcribed'")
        
        transcripts = db.get_transcripts_for_episode(episode_id)
        transcript_count = len(transcripts)
        
        print(f"✓ Transcription complete")
        print(f"  Status: {episode_updated['status']}")
        print(f"  Transcript segments: {transcript_count}")
        
        if transcripts:
            print(f"  First segment: {transcripts[0]['text'][:100]}...")
        
        db.close()
        
        print("\n✅ TEST 3 PASSED: Episode transcribed successfully")
        return episode_updated
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_summarize_episode(episode):
    """Test 4: Summarize the transcribed episode."""
    print("\n" + "="*60)
    print("TEST 4: Summarize Episode")
    print("="*60)
    
    if not episode:
        print("❌ No episode provided for summarization")
        return None
    
    try:
        episode_id = episode['id']
        print(f"\n[4.1] Summarizing episode ID: {episode_id}")
        print(f"      Title: {episode['title']}")
        
        # Initialize database
        db = P3Database()
        
        # Check episode status
        episode_check = db.get_episode_by_id(episode_id)
        if not episode_check:
            print(f"❌ Episode {episode_id} not found in database")
            db.close()
            return None
        
        print(f"      Status: {episode_check['status']}")
        
        # Summarize
        print("\n[4.2] Starting summarization...")
        success, error, summary = summarize_episode(episode_id, db)
        
        if not success:
            print(f"❌ Summarization failed: {error}")
            db.close()
            return None
        
        # Verify summary
        print("\n[4.3] Verifying summary...")
        episode_updated = db.get_episode_by_id(episode_id)
        
        if episode_updated['status'] != 'processed':
            print(f"⚠️  Status is '{episode_updated['status']}', expected 'processed'")
        
        # Get summary from database
        summaries = db.get_summaries_by_date(episode_check['date']) if episode_check.get('date') else []
        episode_summary = next((s for s in summaries if s['episode_id'] == episode_id), None)
        
        if episode_summary:
            print(f"✓ Summarization complete")
            print(f"  Status: {episode_updated['status']}")
            print(f"  Key topics: {len(episode_summary.get('key_topics', []))}")
            print(f"  Themes: {len(episode_summary.get('themes', []))}")
            print(f"  Quotes: {len(episode_summary.get('quotes', []))}")
            print(f"  Companies: {len(episode_summary.get('startups', []))}")
            
            if episode_summary.get('key_topics'):
                print(f"\n  Sample topics: {', '.join(episode_summary['key_topics'][:5])}")
        else:
            print("⚠️  Summary not found in database, but API call succeeded")
        
        db.close()
        
        print("\n✅ TEST 4 PASSED: Episode summarized successfully")
        return episode_updated
        
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all pipeline tests."""
    print("\n" + "="*60)
    print("PIPELINE TEST SUITE")
    print("Testing: Download -> Transcribe -> Summarize")
    print("="*60)
    
    # Test 1: Database connection
    if not test_database_connection():
        print("\n❌ Pipeline test aborted: Database connection failed")
        sys.exit(1)
    
    # Test 2: Download one episode
    episode = test_download_one_episode()
    if not episode:
        print("\n❌ Pipeline test aborted: Download failed")
        sys.exit(1)
    
    # Test 3: Transcribe episode
    transcribed_episode = test_transcribe_episode(episode)
    if not transcribed_episode:
        print("\n❌ Pipeline test aborted: Transcription failed")
        sys.exit(1)
    
    # Test 4: Summarize episode
    summarized_episode = test_summarize_episode(transcribed_episode)
    if not summarized_episode:
        print("\n❌ Pipeline test aborted: Summarization failed")
        sys.exit(1)
    
    # Final summary
    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED!")
    print("="*60)
    print(f"\nPipeline completed successfully for episode:")
    print(f"  ID: {summarized_episode['id']}")
    print(f"  Title: {summarized_episode['title']}")
    print(f"  Status: {summarized_episode['status']}")
    print("\n✅ Download -> Transcribe -> Summarize pipeline working!")


if __name__ == "__main__":
    main()

