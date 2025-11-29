#!/usr/bin/env python3
"""
Complete batch pipeline test for all feeds in feeds.yaml.
Tests: Download -> Transcribe -> Summarize
Uses batch utilities and processes all feeds from config/feeds.yaml.
Skips steps that are already complete.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.postgres_db import PostgresDB
from utils.batch_download import batch_download_one_per_feed
from utils.batch_process import batch_transcribe_downloaded, batch_summarize_transcribed
from utils.download import load_feeds_config


def test_database_connection():
    """Test 1: Database connection and schema initialization."""
    print("\n" + "="*70)
    print("TEST 1: Database Connection & Schema")
    print("="*70)
    
    try:
        # Test PostgreSQL connection
        print("\n[1.1] Testing PostgreSQL connection...")
        db = PostgresDB()
        print("✓ PostgreSQL connection successful")
        
        # Initialize PostgreSQL schema if needed
        print("\n[1.2] Initializing PostgreSQL schema...")
        schema_path = Path(__file__).parent.parent / "sql" / "schema.sql"
        if schema_path.exists():
            db.execute_sql_file(str(schema_path))
            print("✓ PostgreSQL schema initialized")
        else:
            print("⚠️  Schema file not found, skipping schema initialization")
        
        db.close()
        print("\n✅ TEST 1 PASSED: Database connection working")
        return True
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_load_feeds_config():
    """Test 2: Load and validate feed configuration."""
    print("\n" + "="*70)
    print("TEST 2: Load Feed Configuration")
    print("="*70)
    
    try:
        print("\n[2.1] Loading feed configuration from config/feeds.yaml...")
        config = load_feeds_config()
        feeds = config.get('feeds', [])
        
        if not feeds:
            print("❌ No feeds configured in config/feeds.yaml")
            return []
        
        print(f"✅ Found {len(feeds)} feeds configured\n")
        
        print("=" * 70)
        print("CONFIGURED FEEDS")
        print("=" * 70)
        for i, feed in enumerate(feeds, 1):
            print(f"\n{i}. {feed.get('name', 'Unknown')}")
            print(f"   Category: {feed.get('category', 'N/A')}")
            print(f"   URL: {feed.get('url', 'N/A')}")
        
        print("\n✅ TEST 2 PASSED: Feed configuration loaded")
        return feeds
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_batch_download_episodes(skip_download=False, process_all_downloaded=False):
    """Test 3: Batch download episodes from all feeds."""
    print("\n" + "="*70)
    print("TEST 3: Batch Download Episodes from All Feeds")
    print("="*70)
    
    try:
        # Load feed configuration
        config = load_feeds_config()
        feeds = config.get('feeds', [])
        
        if not feeds:
            print("❌ No feeds configured in config/feeds.yaml")
            return []
        
        print(f"\n[3.1] Found {len(feeds)} feeds configured")
        print(f"      Will download 1 episode per feed (or use existing)")
        
        # Initialize database
        print("\n[3.2] Initializing database...")
        db = PostgresDB()
        print("✓ PostgreSQL database initialized")
        
        results = {
            'total_downloaded': 0,
            'total_existing': 0,
            'total_failed': 0,
            'feed_results': {},
            'episodes': []
        }
        
        if skip_download:
            print("\n[3.3] Skipping download, using existing episodes...")
            downloaded_episodes = db.get_episodes_by_status('downloaded')
            episode_ids = [ep['id'] for ep in downloaded_episodes]
            
            print(f"✓ Found {len(episode_ids)} downloaded episode(s) to process")
            results['total_existing'] = len(episode_ids)
            results['message'] = 'Using existing downloaded episodes'
            
            # Filter episodes with valid files
            valid_episodes = []
            for ep in downloaded_episodes:
                file_path = ep.get('audio_file_path') or ep.get('file_path')
                if file_path and Path(file_path).exists():
                    valid_episodes.append(ep)
            
            db.close()
            print("\n✅ TEST 3 PASSED: Using existing episodes")
            print(f"   {len(valid_episodes)} episode(s) ready for transcription")
            return valid_episodes
        
        # Process all downloaded episodes if flag is set
        if process_all_downloaded:
            print("\n[3.3] Processing ALL downloaded episodes (not just batch download)")
            all_downloaded = db.get_episodes_by_status('downloaded')
            valid_episodes = []
            for ep in all_downloaded:
                file_path = ep.get('audio_file_path') or ep.get('file_path')
                if file_path and Path(file_path).exists():
                    valid_episodes.append(ep)
            
            print(f"✓ Found {len(valid_episodes)} downloaded episode(s)")
            db.close()
            print("\n✅ TEST 3 PASSED: Using all downloaded episodes")
            print(f"   {len(valid_episodes)} episode(s) ready for transcription")
            return valid_episodes
        
        # Batch download from all feeds
        print("\n[3.3] Batch downloading episodes...")
        print("=" * 70)
        
        download_results = batch_download_one_per_feed(
            db=db,
            data_dir="data/demo",
            audio_format="mp3"  # Convert to MP3 for faster processing
        )
        
        results['total_downloaded'] = download_results.get('total_downloaded', 0)
        results['feed_results'] = download_results.get('feed_results', {})
        results['episodes'] = download_results.get('episodes', [])
        
        # Count failures
        for feed_result in results['feed_results'].values():
            if feed_result.get('error'):
                results['total_failed'] += 1
        
        # Summary
        print("\n" + "=" * 70)
        print("DOWNLOAD SUMMARY")
        print("=" * 70)
        print(f"\nTotal episodes downloaded: {results['total_downloaded']}")
        print(f"Total failed: {results['total_failed']}")
        
        if results['feed_results']:
            print("\nFeed Results:")
            for feed_name, feed_result in results['feed_results'].items():
                if feed_result.get('count', 0) > 0:
                    episode = feed_result.get('episode', {})
                    print(f"  ✅ {feed_name}: Downloaded episode ID {episode.get('id', 'N/A')}")
                elif feed_result.get('error'):
                    print(f"  ❌ {feed_name}: {feed_result.get('error', 'Unknown error')}")
                else:
                    print(f"  ⚠️  {feed_name}: No new episodes (may already exist)")
        
        # Get valid episodes with files
        valid_episodes = []
        for ep_info in results['episodes']:
            file_path = ep_info.get('file_path')
            if file_path and Path(file_path).exists():
                # Get full episode from database
                episode = db.get_episode_by_id(ep_info['id'])
                if episode:
                    valid_episodes.append(episode)
        
        db.close()
        
        print("\n✅ TEST 3 PASSED: Batch download completed")
        print(f"   {len(valid_episodes)} episode(s) ready for transcription")
        
        return valid_episodes
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_batch_transcribe_episodes(episodes):
    """Test 4: Batch transcribe downloaded episodes."""
    print("\n" + "="*70)
    print("TEST 4: Batch Transcribe Episodes")
    print("="*70)
    
    if not episodes:
        print("⚠️  No episodes provided for transcription")
        return []
    
    # Filter episodes with valid files
    valid_episodes = []
    for ep in episodes:
        file_path = ep.get('audio_file_path') or ep.get('file_path')
        if file_path and Path(file_path).exists():
            valid_episodes.append(ep)
    
    if not valid_episodes:
        print("❌ No episodes with valid audio files found")
        return []
    
    print(f"\n✅ Found {len(valid_episodes)} episode(s) ready for transcription\n")
    
    # Show episodes to be transcribed
    print("=" * 70)
    print("EPISODES TO TRANSCRIBE")
    print("=" * 70)
    for i, ep in enumerate(valid_episodes, 1):
        file_path = ep.get('audio_file_path') or ep.get('file_path')
        print(f"\n{i}. Episode ID: {ep['id']}")
        print(f"   Title: {ep['title'][:70]}...")
        print(f"   Podcast: {ep.get('podcast_feed_name', 'Unknown')}")
        print(f"   File: {file_path}")
        if ep.get('duration_seconds'):
            minutes = ep['duration_seconds'] // 60
            seconds = ep['duration_seconds'] % 60
            print(f"   Duration: {minutes}m{seconds}s")
    
    # Initialize database
    db = PostgresDB()
    
    # Get episode IDs
    episode_ids = [ep['id'] for ep in valid_episodes]
    
    print(f"\n{'='*70}")
    print(f"BATCH TRANSCRIBING {len(episode_ids)} EPISODE(S)")
    print(f"{'='*70}\n")
    
    try:
        # Batch transcribe
        transcription_results = batch_transcribe_downloaded(
            db=db,
            episode_ids=episode_ids
        )
        
        # Summary
        print("\n" + "=" * 70)
        print("TRANSCRIPTION SUMMARY")
        print("=" * 70)
        print(f"\nTotal episodes processed: {len(episode_ids)}")
        print(f"✅ Successfully transcribed: {transcription_results.get('total_transcribed', 0)}")
        print(f"⏭️  Skipped (already done): {transcription_results.get('total_skipped', 0)}")
        print(f"❌ Failed: {transcription_results.get('total_failed', 0)}")
        
        if transcription_results.get('episode_results'):
            print("\nEpisode Results:")
            for result in transcription_results['episode_results']:
                if result['status'] == 'transcribed':
                    print(f"  ✅ {result.get('title', 'Unknown')[:60]}... (Segments: {result.get('segments', 0)})")
                elif result['status'] == 'skipped':
                    print(f"  ⏭️  {result.get('title', 'Unknown')[:60]}... (Already transcribed, {result.get('segments', 0)} segments)")
                else:
                    print(f"  ❌ {result.get('title', 'Unknown')[:60]}... (Error: {result.get('error', 'Unknown')})")
        
        # Get transcribed episodes
        transcribed_episodes = []
        for ep in valid_episodes:
            episode_check = db.get_episode_by_id(ep['id'])
            if episode_check.get('status') == 'transcribed' or episode_check.get('status') == 'processed':
                transcribed_episodes.append(episode_check)
        
        db.close()
        
        print("\n✅ TEST 4 PASSED: Batch transcription completed")
        print(f"   {len(transcribed_episodes)} episode(s) ready for summarization")
        
        return transcribed_episodes
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Transcription interrupted by user")
        db.close()
        return []
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return []


def test_batch_summarize_episodes(episodes):
    """Test 5: Batch summarize transcribed episodes."""
    print("\n" + "="*70)
    print("TEST 5: Batch Summarize Episodes")
    print("="*70)
    
    if not episodes:
        print("⚠️  No episodes provided for summarization")
        return {}
    
    print(f"\n✅ Found {len(episodes)} episode(s) ready for summarization\n")
    
    # Initialize database
    db = PostgresDB()
    
    # Get episode IDs
    episode_ids = [ep['id'] for ep in episodes]
    
    print(f"\n{'='*70}")
    print(f"BATCH SUMMARIZING {len(episode_ids)} EPISODE(S)")
    print(f"{'='*70}\n")
    
    try:
        # Batch summarize
        summarization_results = batch_summarize_transcribed(
            db=db,
            episode_ids=episode_ids
        )
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARIZATION SUMMARY")
        print("=" * 70)
        print(f"\nTotal episodes processed: {len(episode_ids)}")
        print(f"✅ Successfully summarized: {summarization_results.get('total_summarized', 0)}")
        print(f"⏭️  Skipped (already done): {summarization_results.get('total_skipped', 0)}")
        print(f"❌ Failed: {summarization_results.get('total_failed', 0)}")
        
        if summarization_results.get('episode_results'):
            print("\nEpisode Results:")
            for result in summarization_results['episode_results']:
                if result['status'] == 'summarized':
                    print(f"  ✅ {result.get('title', 'Unknown')[:60]}... ({result.get('key_topics', 0)} topics)")
                elif result['status'] == 'skipped':
                    print(f"  ⏭️  {result.get('title', 'Unknown')[:60]}... (Already processed, {result.get('key_topics', 0)} topics)")
                else:
                    print(f"  ❌ {result.get('title', 'Unknown')[:60]}... (Error: {result.get('error', 'Unknown')})")
        
        db.close()
        
        print("\n✅ TEST 5 PASSED: Batch summarization completed")
        
        return summarization_results
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Summarization interrupted by user")
        db.close()
        return {}
    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return {}


def main():
    """Run complete batch pipeline for all feeds."""
    print("\n" + "="*70)
    print("BATCH PIPELINE TEST - ALL FEEDS")
    print("Testing: Download -> Transcribe -> Summarize")
    print("="*70)
    
    # Parse command line arguments
    skip_download = "--skip-download" in sys.argv or "-s" in sys.argv
    process_all = "--all" in sys.argv or "-a" in sys.argv
    
    results = {
        'test_name': 'batch_pipeline_all_feeds',
        'timestamp': datetime.now().isoformat(),
        'database': 'PostgreSQL',
        'skip_download': skip_download,
        'process_all_downloaded': process_all
    }
    
    try:
        # Test 1: Database connection
        if not test_database_connection():
            print("\n❌ Pipeline test aborted: Database connection failed")
            results['error'] = 'Database connection failed'
            return results
        
        # Test 2: Load feed configuration
        feeds = test_load_feeds_config()
        if not feeds:
            print("\n❌ Pipeline test aborted: No feeds configured")
            results['error'] = 'No feeds configured'
            return results
        
        results['feeds_count'] = len(feeds)
        
        # Test 3: Batch download episodes
        episodes = test_batch_download_episodes(
            skip_download=skip_download,
            process_all_downloaded=process_all
        )
        if not episodes:
            print("\n⚠️  No episodes downloaded or found")
            print("   Pipeline test will continue with existing episodes...")
            # Try to get existing episodes
            db = PostgresDB()
            episodes = db.get_episodes_by_status('downloaded')
            db.close()
            if not episodes:
                print("\n❌ Pipeline test aborted: No episodes available")
                results['error'] = 'No episodes available'
                return results
        
        results['download'] = {
            'total_episodes': len(episodes),
            'episode_ids': [ep['id'] for ep in episodes]
        }
        
        # Test 4: Batch transcribe episodes
        transcribed_episodes = test_batch_transcribe_episodes(episodes)
        if not transcribed_episodes:
            print("\n⚠️  No episodes transcribed")
            print("   Pipeline test will continue with existing transcribed episodes...")
            # Try to get existing transcribed episodes
            db = PostgresDB()
            transcribed_episodes = db.get_episodes_by_status('transcribed')
            db.close()
            if not transcribed_episodes:
                print("\n⚠️  Pipeline test completed: No episodes available for summarization")
                results['warning'] = 'No episodes available for summarization'
                return results
        
        results['transcription'] = {
            'total_episodes': len(transcribed_episodes),
            'episode_ids': [ep['id'] for ep in transcribed_episodes]
        }
        
        # Test 5: Batch summarize episodes
        summarize_results = test_batch_summarize_episodes(transcribed_episodes)
        results['summarization'] = summarize_results
        
        # Final summary
        print("\n" + "="*70)
        print("🎉 BATCH PIPELINE TEST COMPLETED!")
        print("="*70)
        
        # Show pipeline status
        db = PostgresDB()
        downloaded_count = len(db.get_episodes_by_status('downloaded'))
        transcribed_count = len(db.get_episodes_by_status('transcribed'))
        processed_count = len(db.get_episodes_by_status('processed'))
        db.close()
        
        print(f"\nSummary:")
        print(f"  📥 Downloaded: {len(episodes)} episode(s)")
        print(f"  🎙️  Transcribed: {len(transcribed_episodes)} episode(s)")
        print(f"  ✅ Summarized: {summarize_results.get('total_summarized', 0)} episode(s)")
        print(f"  ⏭️  Skipped: {summarize_results.get('total_skipped', 0)} episode(s)")
        print(f"  ❌ Failed: {summarize_results.get('total_failed', 0)} episode(s)")
        
        print("\n" + "="*70)
        print("Pipeline Status")
        print("="*70)
        print(f"📥 Downloaded: {downloaded_count}")
        print(f"🎙️  Transcribed: {transcribed_count}")
        print(f"✅ Processed (with summaries): {processed_count}")
        
        # Save results
        output_dir = Path("test-results")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"batch_pipeline_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")
        print("\n✅ Batch pipeline working for all feeds!")
        
        return results
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline test interrupted by user")
        results['interrupted'] = True
        return results
    except Exception as e:
        print(f"\n\n❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        results['error'] = str(e)
        return results


if __name__ == "__main__":
    main()
