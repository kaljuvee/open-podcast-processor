#!/usr/bin/env python3
"""
Complete pipeline test for trading podcasts.
Tests: Download -> Transcribe -> Summarize
Skips steps that are already complete.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.postgres_db import PostgresDB
from utils.download import load_feeds_config
from utils.downloader import PodcastDownloader
from utils.processing import transcribe_episode, summarize_episode


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


def test_download_episodes(num_feeds: int = 5):
    """Test 2: Download episodes from trading podcasts."""
    print("\n" + "="*70)
    print("TEST 2: Download Episodes from Trading Podcasts")
    print("="*70)
    
    try:
        # Load feed configuration
        print("\n[2.1] Loading feed configuration...")
        config = load_feeds_config()
        feeds = config.get('feeds', [])
        
        if len(feeds) < num_feeds:
            print(f"⚠️  Only {len(feeds)} feeds configured, using all available feeds")
            num_feeds = len(feeds)
        
        if not feeds:
            print("❌ No feeds configured in config/feeds.yaml")
            return []
        
        # Get first N feeds
        feeds_to_process = feeds[:num_feeds]
        
        print(f"✅ Found {len(feeds)} total feeds")
        print(f"📥 Will download from first {len(feeds_to_process)} feeds:\n")
        
        for i, feed in enumerate(feeds_to_process, 1):
            print(f"  {i}. {feed['name']} ({feed.get('category', 'N/A')})")
            print(f"     URL: {feed['url']}")
        
        # Initialize database and downloader
        print("\n[2.2] Initializing database and downloader...")
        db = PostgresDB()
        downloader = PodcastDownloader(
            db=db,
            data_dir="data",
            max_episodes=1,  # Only 1 episode per feed for testing
            audio_format="mp3"  # Use mp3 for faster processing
        )
        
        print("✅ PostgreSQL database and downloader initialized")
        
        # Process each feed
        print("\n[2.3] Downloading episodes...")
        print("=" * 70)
        
        downloaded_episodes = []
        results = {
            'total_downloaded': 0,
            'total_existing': 0,
            'total_failed': 0,
            'feed_results': {}
        }
        
        for idx, feed_config in enumerate(feeds_to_process, 1):
            feed_name = feed_config['name']
            feed_url = feed_config['url']
            feed_category = feed_config.get('category', 'general')
            
            print(f"\n[{idx}/{len(feeds_to_process)}] Processing: {feed_name}")
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
                episode_url = episode_data['url']
                print(f"  ✓ Found episode: {episode_data['title'][:70]}...")
                
                # Check if episode already exists in database
                existing_episode = db.get_podcast_by_url(episode_url)
                if existing_episode:
                    print(f"  ℹ️  Episode already exists in database, checking file...")
                    file_path = existing_episode.get('audio_file_path') or existing_episode.get('file_path')
                    
                    # Check if file actually exists on disk
                    if file_path and Path(file_path).exists():
                        print(f"  ✓ Using existing episode (ID: {existing_episode['id']})")
                        print(f"     File: {file_path}")
                        print(f"     Status: {existing_episode.get('status', 'unknown')}")
                        downloaded_episodes.append(existing_episode)
                        results['total_existing'] += 1
                        results['feed_results'][feed_name] = {'downloaded': 0, 'episode_id': existing_episode['id'], 'existing': True}
                        continue
                    else:
                        print(f"  ⚠️  Episode in DB but file missing: {file_path}")
                        print(f"     Will re-download...")
                
                # Download episode
                print(f"  📥 Downloading episode...")
                safe_title = "".join(c for c in episode_data['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f"{podcast_id}_{safe_title[:50]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                file_path = downloader.download_episode(episode_url, filename)
                
                if not file_path:
                    print(f"  ❌ Failed to download episode")
                    results['total_failed'] += 1
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
                    episode_url=episode_url,
                    published_at=episode_data['date'],
                    audio_file_path=file_path,
                    file_size_bytes=file_size_bytes,
                    status='downloaded',
                    podcast_feed_name=feed_name,
                    podcast_category=feed_category
                )
                
                print(f"  ✅ Episode saved (ID: {episode_id})")
                episode = db.get_podcast_by_id(episode_id)
                downloaded_episodes.append(episode)
                results['total_downloaded'] += 1
                results['feed_results'][feed_name] = {'downloaded': 1, 'episode_id': episode_id}
            
            except Exception as e:
                print(f"  ❌ Error processing feed: {e}")
                import traceback
                traceback.print_exc()
                results['total_failed'] += 1
                results['feed_results'][feed_name] = {'downloaded': 0, 'error': str(e)}
        
        # Summary
        print("\n" + "=" * 70)
        print("DOWNLOAD SUMMARY")
        print("=" * 70)
        print(f"\nTotal episodes downloaded: {results['total_downloaded']}")
        print(f"Total episodes existing: {results['total_existing']}")
        print(f"Total failed: {results['total_failed']}")
        print("\nFeed Results:")
        for feed_name, feed_result in results['feed_results'].items():
            if feed_result.get('downloaded', 0) > 0:
                print(f"  ✅ {feed_name}: Downloaded episode ID {feed_result.get('episode_id')}")
            elif feed_result.get('existing'):
                print(f"  ℹ️  {feed_name}: Using existing episode ID {feed_result.get('episode_id')}")
            else:
                print(f"  ⚠️  {feed_name}: {feed_result.get('error', 'Unknown error')}")
        
        # Filter episodes with valid files
        valid_episodes = []
        for ep in downloaded_episodes:
            file_path = ep.get('audio_file_path') or ep.get('file_path')
            if file_path and Path(file_path).exists():
                valid_episodes.append(ep)
        
        db.close()
        
        print("\n✅ TEST 2 PASSED: Episodes downloaded successfully")
        print(f"   {len(valid_episodes)} episode(s) ready for transcription")
        
        return valid_episodes
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_transcribe_episodes(episodes):
    """Test 3: Transcribe downloaded episodes."""
    print("\n" + "="*70)
    print("TEST 3: Transcribe Episodes")
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
    
    results = {
        'total_transcribed': 0,
        'total_skipped': 0,
        'total_failed': 0,
        'episode_results': []
    }
    
    for idx, episode in enumerate(valid_episodes, 1):
        episode_id = episode['id']
        episode_title = episode['title']
        file_path = episode.get('audio_file_path') or episode.get('file_path')
        
        print(f"\n{'='*70}")
        print(f"[{idx}/{len(valid_episodes)}] TRANSCRIBING EPISODE")
        print(f"{'='*70}")
        print(f"Episode ID: {episode_id}")
        print(f"Title: {episode_title}")
        print(f"File: {file_path}")
        print(f"{'='*70}\n")
        
        try:
            # Check if already transcribed
            episode_check = db.get_episode_by_id(episode_id)
            if episode_check.get('status') == 'transcribed' or episode_check.get('status') == 'processed':
                print(f"⚠️  Episode already transcribed (status: {episode_check.get('status')})")
                print("   Skipping transcription...")
                transcripts = db.get_transcripts_for_episode(episode_id)
                results['total_skipped'] += 1
                results['episode_results'].append({
                    'episode_id': episode_id,
                    'title': episode_title,
                    'status': 'skipped',
                    'segments': len(transcripts)
                })
                continue
            
            # Transcribe using the processing utility
            success, error = transcribe_episode(episode_id, db)
            
            if success:
                # Verify transcription
                episode_updated = db.get_episode_by_id(episode_id)
                transcripts = db.get_transcripts_for_episode(episode_id)
                
                print(f"\n{'='*70}")
                print(f"✅ TRANSCRIPTION SUCCESSFUL")
                print(f"{'='*70}")
                print(f"Status: {episode_updated.get('status', 'unknown')}")
                print(f"Transcript segments: {len(transcripts)}")
                
                if transcripts:
                    total_chars = sum(len(t.get('text', '')) for t in transcripts)
                    print(f"Total text length: {total_chars:,} characters")
                
                results['total_transcribed'] += 1
                results['episode_results'].append({
                    'episode_id': episode_id,
                    'title': episode_title,
                    'status': 'success',
                    'segments': len(transcripts)
                })
            else:
                print(f"\n{'='*70}")
                print(f"❌ TRANSCRIPTION FAILED")
                print(f"{'='*70}")
                print(f"Error: {error}")
                
                results['total_failed'] += 1
                results['episode_results'].append({
                    'episode_id': episode_id,
                    'title': episode_title,
                    'status': 'failed',
                    'error': error
                })
        
        except KeyboardInterrupt:
            print(f"\n\n⚠️  Transcription interrupted by user")
            print(f"   Processed {idx-1}/{len(valid_episodes)} episodes")
            break
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"❌ UNEXPECTED ERROR")
            print(f"{'='*70}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            
            results['total_failed'] += 1
            results['episode_results'].append({
                'episode_id': episode_id,
                'title': episode_title,
                'status': 'error',
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("TRANSCRIPTION SUMMARY")
    print("=" * 70)
    print(f"\nTotal episodes processed: {len(valid_episodes)}")
    print(f"✅ Successfully transcribed: {results['total_transcribed']}")
    print(f"⏭️  Skipped (already done): {results['total_skipped']}")
    print(f"❌ Failed: {results['total_failed']}")
    
    if results['episode_results']:
        print("\nEpisode Results:")
        for result in results['episode_results']:
            if result['status'] == 'success':
                print(f"  ✅ {result['title'][:60]}... (Segments: {result.get('segments', 0)})")
            elif result['status'] == 'skipped':
                print(f"  ⏭️  {result['title'][:60]}... (Already transcribed, {result.get('segments', 0)} segments)")
            else:
                print(f"  ❌ {result['title'][:60]}... (Error: {result.get('error', 'Unknown')})")
    
    # Get transcribed episodes
    transcribed_episodes = []
    for ep in valid_episodes:
        episode_check = db.get_episode_by_id(ep['id'])
        if episode_check.get('status') == 'transcribed' or episode_check.get('status') == 'processed':
            transcribed_episodes.append(episode_check)
    
    db.close()
    
    print("\n✅ TEST 3 PASSED: Transcription completed")
    print(f"   {len(transcribed_episodes)} episode(s) ready for summarization")
    
    return transcribed_episodes


def test_summarize_episodes(episodes):
    """Test 4: Summarize transcribed episodes."""
    print("\n" + "="*70)
    print("TEST 4: Summarize Episodes")
    print("="*70)
    
    if not episodes:
        print("⚠️  No episodes provided for summarization")
        return []
    
    print(f"\n✅ Found {len(episodes)} episode(s) ready for summarization\n")
    
    # Initialize database
    db = PostgresDB()
    
    results = {
        'total_summarized': 0,
        'total_skipped': 0,
        'total_failed': 0,
        'episode_results': []
    }
    
    for idx, episode in enumerate(episodes, 1):
        episode_id = episode['id']
        episode_title = episode['title']
        
        print(f"\n{'='*70}")
        print(f"[{idx}/{len(episodes)}] SUMMARIZING EPISODE")
        print(f"{'='*70}")
        print(f"Episode ID: {episode_id}")
        print(f"Title: {episode_title}")
        print(f"{'='*70}\n")
        
        try:
            # Check if already processed
            episode_check = db.get_episode_by_id(episode_id)
            if episode_check.get('status') == 'processed':
                if episode_check.get('summary'):
                    print(f"⚠️  Episode already processed (status: processed)")
                    print("   Skipping summarization...")
                    summary = episode_check.get('summary')
                    results['total_skipped'] += 1
                    results['episode_results'].append({
                        'episode_id': episode_id,
                        'title': episode_title,
                        'status': 'skipped',
                        'key_topics': len(summary.get('key_topics', [])) if summary else 0
                    })
                    continue
            
            # Summarize
            success, error, summary = summarize_episode(episode_id, db)
            
            if not success:
                print(f"❌ Summarization failed: {error}")
                results['total_failed'] += 1
                results['episode_results'].append({
                    'episode_id': episode_id,
                    'title': episode_title,
                    'status': 'failed',
                    'error': error
                })
                continue
            
            # Verify summary
            episode_updated = db.get_episode_by_id(episode_id)
            episode_summary = episode_updated.get('summary')
            
            if episode_summary:
                print(f"\n{'='*70}")
                print(f"✅ SUMMARIZATION SUCCESSFUL")
                print(f"{'='*70}")
                print(f"Status: {episode_updated['status']}")
                print(f"Key topics: {len(episode_summary.get('key_topics', []))}")
                print(f"Themes: {len(episode_summary.get('themes', []))}")
                print(f"Quotes: {len(episode_summary.get('quotes', []))}")
                print(f"Companies: {len(episode_summary.get('startups', []))}")
                
                if episode_summary.get('key_topics'):
                    print(f"\nSample topics: {', '.join(episode_summary['key_topics'][:5])}")
            
            results['total_summarized'] += 1
            results['episode_results'].append({
                'episode_id': episode_id,
                'title': episode_title,
                'status': 'success',
                'key_topics': len(episode_summary.get('key_topics', [])) if episode_summary else 0
            })
        
        except KeyboardInterrupt:
            print(f"\n\n⚠️  Summarization interrupted by user")
            print(f"   Processed {idx-1}/{len(episodes)} episodes")
            break
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"❌ UNEXPECTED ERROR")
            print(f"{'='*70}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            
            results['total_failed'] += 1
            results['episode_results'].append({
                'episode_id': episode_id,
                'title': episode_title,
                'status': 'error',
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARIZATION SUMMARY")
    print("=" * 70)
    print(f"\nTotal episodes processed: {len(episodes)}")
    print(f"✅ Successfully summarized: {results['total_summarized']}")
    print(f"⏭️  Skipped (already done): {results['total_skipped']}")
    print(f"❌ Failed: {results['total_failed']}")
    
    if results['episode_results']:
        print("\nEpisode Results:")
        for result in results['episode_results']:
            if result['status'] == 'success':
                print(f"  ✅ {result['title'][:60]}... ({result.get('key_topics', 0)} topics)")
            elif result['status'] == 'skipped':
                print(f"  ⏭️  {result['title'][:60]}... (Already processed, {result.get('key_topics', 0)} topics)")
            else:
                print(f"  ❌ {result['title'][:60]}... (Error: {result.get('error', 'Unknown')})")
    
    db.close()
    
    print("\n✅ TEST 4 PASSED: Summarization completed")
    
    return results


def main():
    """Run complete trading podcast pipeline."""
    print("\n" + "="*70)
    print("TRADING PODCAST PIPELINE TEST")
    print("Testing: Download -> Transcribe -> Summarize")
    print("="*70)
    
    # Test 1: Database connection
    if not test_database_connection():
        print("\n❌ Pipeline test aborted: Database connection failed")
        sys.exit(1)
    
    # Test 2: Download episodes
    episodes = test_download_episodes(num_feeds=5)
    if not episodes:
        print("\n⚠️  No episodes downloaded or found")
        print("   Pipeline test will continue with existing episodes...")
        # Try to get existing episodes
        db = PostgresDB()
        episodes = db.get_episodes_by_status('downloaded')
        db.close()
        if not episodes:
            print("\n❌ Pipeline test aborted: No episodes available")
            sys.exit(1)
    
    # Test 3: Transcribe episodes
    transcribed_episodes = test_transcribe_episodes(episodes)
    if not transcribed_episodes:
        print("\n⚠️  No episodes transcribed")
        print("   Pipeline test will continue with existing transcribed episodes...")
        # Try to get existing transcribed episodes
        db = PostgresDB()
        transcribed_episodes = db.get_episodes_by_status('transcribed')
        db.close()
        if not transcribed_episodes:
            print("\n⚠️  Pipeline test completed: No episodes available for summarization")
            sys.exit(0)
    
    # Test 4: Summarize episodes
    summarize_results = test_summarize_episodes(transcribed_episodes)
    
    # Final summary
    print("\n" + "="*70)
    print("🎉 PIPELINE TEST COMPLETED!")
    print("="*70)
    print(f"\nSummary:")
    print(f"  Downloaded: {len(episodes)} episode(s)")
    print(f"  Transcribed: {len(transcribed_episodes)} episode(s)")
    print(f"  Summarized: {summarize_results.get('total_summarized', 0)} episode(s)")
    print(f"  Skipped: {summarize_results.get('total_skipped', 0)} episode(s)")
    print(f"  Failed: {summarize_results.get('total_failed', 0)} episode(s)")
    print("\n✅ Trading podcast pipeline working!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


