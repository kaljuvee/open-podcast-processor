#!/usr/bin/env python3
"""
Process all downloaded episodes that aren't yet in the database.
Scans audio directory, compares with database, and processes missing episodes.
Tests: Find Downloads -> Add to DB -> Transcribe -> Summarize
"""

import sys
import time
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.postgres_db import PostgresDB
from utils.processing import transcribe_episode, summarize_episode
from utils.transcriber_groq import AudioTranscriber
from utils.cleaner_groq import TranscriptCleaner
from utils.config import get_groq_api_key


def test_database_connection():
    """Test 1: Database connection and schema initialization."""
    print("\n" + "="*70)
    print("TEST 1: Database Connection & Schema")
    print("="*70)
    
    try:
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


def find_downloaded_audio_files(data_dir: str = "data/audio") -> list:
    """Find all audio files in the data directory."""
    audio_dir = Path(data_dir)
    
    if not audio_dir.exists():
        print(f"⚠️  Audio directory not found: {audio_dir}")
        return []
    
    # Supported audio formats
    audio_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
    
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(audio_dir.glob(f"*{ext}"))
        # Also check subdirectories
        audio_files.extend(audio_dir.rglob(f"*{ext}"))
    
    # Filter out temp files
    audio_files = [f for f in audio_files if 'temp' not in str(f) and '_downloaded.tmp' not in str(f)]
    
    return sorted(audio_files)


def get_episodes_in_database(db: PostgresDB) -> dict:
    """Get all episodes from database, indexed by audio file path."""
    episodes = db.get_all_podcasts(status=None, limit=10000)
    
    # Create mapping of file path -> episode
    episode_map = {}
    for ep in episodes:
        file_path = ep.get('audio_file_path')
        if file_path:
            # Normalize path
            normalized_path = str(Path(file_path).resolve())
            episode_map[normalized_path] = ep
    
    return episode_map


def extract_metadata_from_filename(filename: str) -> dict:
    """Try to extract metadata from filename pattern."""
    # Common patterns:
    # - "24_310  Dr Efrat Levy - Fingerprinting the Big Player_20251129_140434.wav"
    # - "podcast-name-episode-title.wav"
    
    metadata = {
        'title': filename,
        'feed_name': 'Unknown',
        'category': 'general'
    }
    
    # Try to extract title (remove extension, date suffixes, etc.)
    base_name = Path(filename).stem
    
    # Remove date patterns like _20251129_140434
    import re
    base_name = re.sub(r'_\d{8}_\d{6}$', '', base_name)
    base_name = re.sub(r'_\d{8}$', '', base_name)
    
    # Clean up underscores and numbers at start
    base_name = re.sub(r'^\d+_?\d*_?', '', base_name)
    
    metadata['title'] = base_name.replace('_', ' ').replace('-', ' ').strip()
    
    return metadata


def test_find_missing_episodes():
    """Test 2: Find downloaded audio files not in database."""
    print("\n" + "="*70)
    print("TEST 2: Find Missing Episodes")
    print("="*70)
    
    try:
        db = PostgresDB()
        
        print("\n[2.1] Scanning audio directory for downloaded files...")
        audio_files = find_downloaded_audio_files()
        
        if not audio_files:
            print("⚠️  No audio files found in data/audio directory")
            db.close()
            return []
        
        print(f"✓ Found {len(audio_files)} audio file(s)")
        
        print("\n[2.2] Loading episodes from database...")
        episode_map = get_episodes_in_database(db)
        print(f"✓ Found {len(episode_map)} episode(s) in database")
        
        print("\n[2.3] Comparing files with database...")
        missing_files = []
        
        for audio_file in audio_files:
            normalized_path = str(audio_file.resolve())
            
            if normalized_path not in episode_map:
                # File not in database
                file_size = audio_file.stat().st_size
                file_size_mb = file_size / (1024 * 1024)
                
                metadata = extract_metadata_from_filename(audio_file.name)
                
                missing_files.append({
                    'file_path': normalized_path,
                    'filename': audio_file.name,
                    'file_size_bytes': file_size,
                    'file_size_mb': file_size_mb,
                    'title': metadata['title'],
                    'feed_name': metadata['feed_name'],
                    'category': metadata['category']
                })
        
        print(f"✓ Found {len(missing_files)} file(s) not in database")
        
        if missing_files:
            print("\n" + "=" * 70)
            print("MISSING EPISODES")
            print("=" * 70)
            for i, item in enumerate(missing_files, 1):
                print(f"\n{i}. {item['filename']}")
                print(f"   Title: {item['title'][:70]}...")
                print(f"   Size: {item['file_size_mb']:.2f} MB")
                print(f"   Path: {item['file_path']}")
        
        db.close()
        print("\n✅ TEST 2 PASSED: Missing episodes identified")
        return missing_files
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_add_missing_to_database(missing_files: list):
    """Test 3: Add missing episodes to database."""
    print("\n" + "="*70)
    print("TEST 3: Add Missing Episodes to Database")
    print("="*70)
    
    if not missing_files:
        print("⚠️  No missing files to add")
        return []
    
    try:
        db = PostgresDB()
        
        print(f"\n[3.1] Adding {len(missing_files)} episode(s) to database...")
        
        added_episodes = []
        
        for idx, item in enumerate(missing_files, 1):
            print(f"\n[{idx}/{len(missing_files)}] Adding: {item['filename']}")
            print("-" * 70)
            
            try:
                # Add episode to database
                episode_id = db.save_podcast(
                    title=item['title'],
                    description=None,
                    feed_url=None,  # Unknown feed URL
                    episode_url=None,  # Unknown episode URL
                    published_at=None,
                    duration_seconds=None,
                    audio_file_path=item['file_path'],
                    file_size_bytes=item['file_size_bytes'],
                    status='downloaded',
                    transcript=None,
                    summary=None,
                    podcast_feed_name=item['feed_name'],
                    podcast_category=item['category']
                )
                
                print(f"✓ Added to database (ID: {episode_id})")
                
                # Get the episode back
                episode = db.get_episode_by_id(episode_id)
                added_episodes.append(episode)
                
            except Exception as e:
                print(f"✗ Failed to add: {e}")
                import traceback
                traceback.print_exc()
        
        db.close()
        
        print(f"\n✅ TEST 3 PASSED: Added {len(added_episodes)} episode(s) to database")
        return added_episodes
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_process_episodes(episodes: list):
    """Test 4: Process episodes (transcribe and summarize)."""
    print("\n" + "="*70)
    print("TEST 4: Process Episodes (Transcribe & Summarize)")
    print("="*70)
    
    if not episodes:
        print("⚠️  No episodes to process")
        return {}
    
    try:
        db = PostgresDB()
        api_key = get_groq_api_key()
        
        results = {
            'total_processed': 0,
            'total_transcribed': 0,
            'total_summarized': 0,
            'total_skipped': 0,
            'total_failed': 0,
            'episode_results': []
        }
        
        print(f"\n[4.1] Processing {len(episodes)} episode(s)...")
        print("=" * 70)
        
        for idx, episode in enumerate(episodes, 1):
            episode_id = episode['id']
            episode_title = episode.get('title', 'Unknown')[:70]
            file_path = episode.get('audio_file_path')
            
            print(f"\n[{idx}/{len(episodes)}] PROCESSING EPISODE")
            print(f"Episode ID: {episode_id}")
            print(f"Title: {episode_title}")
            print(f"File: {file_path}")
            print("-" * 70)
            
            episode_result = {
                'episode_id': episode_id,
                'title': episode_title,
                'transcription_status': 'pending',
                'summarization_status': 'pending',
                'error': None
            }
            
            # Check current status
            episode_check = db.get_episode_by_id(episode_id)
            transcript = episode_check.get('transcript') if episode_check else None
            summary = episode_check.get('summary') if episode_check else None
            
            has_transcript = False
            if transcript:
                if isinstance(transcript, dict):
                    transcript_text = transcript.get('text', '')
                    segments = transcript.get('segments', [])
                    if transcript_text or (segments and len(segments) > 0):
                        has_transcript = True
                elif isinstance(transcript, str):
                    try:
                        transcript_dict = json.loads(transcript)
                        if isinstance(transcript_dict, dict):
                            transcript_text = transcript_dict.get('text', '')
                            segments = transcript_dict.get('segments', [])
                            if transcript_text or (segments and len(segments) > 0):
                                has_transcript = True
                    except:
                        pass
            
            has_summary = False
            if summary:
                if isinstance(summary, dict):
                    summary_text = summary.get('summary', '')
                    key_topics = summary.get('key_topics', [])
                    if summary_text or key_topics:
                        has_summary = True
                elif isinstance(summary, str):
                    try:
                        summary_dict = json.loads(summary)
                        if isinstance(summary_dict, dict):
                            summary_text = summary_dict.get('summary', '')
                            key_topics = summary_dict.get('key_topics', [])
                            if summary_text or key_topics:
                                has_summary = True
                    except:
                        pass
            
            # Step 1: Transcribe if needed
            if not has_transcript:
                print(f"\n[4.2.{idx}] Transcribing episode...")
                transcription_start = time.time()
                
                try:
                    success, error = transcribe_episode(episode_id, db)
                    transcription_time = time.time() - transcription_start
                    
                    if success:
                        results['total_transcribed'] += 1
                        episode_result['transcription_status'] = 'success'
                        episode_result['transcription_time'] = transcription_time
                        
                        # Get transcript info
                        episode_updated = db.get_episode_by_id(episode_id)
                        transcript = episode_updated.get('transcript')
                        if transcript and isinstance(transcript, dict):
                            segments = transcript.get('segments', [])
                            text_length = len(transcript.get('text', ''))
                            print(f"✓ Transcribed in {transcription_time:.1f}s ({len(segments)} segments, {text_length:,} chars)")
                        else:
                            print(f"✓ Transcribed in {transcription_time:.1f}s")
                    else:
                        results['total_failed'] += 1
                        episode_result['transcription_status'] = 'failed'
                        episode_result['error'] = error
                        print(f"✗ Transcription failed: {error}")
                except Exception as e:
                    results['total_failed'] += 1
                    episode_result['transcription_status'] = 'failed'
                    episode_result['error'] = str(e)
                    print(f"✗ Transcription error: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"⏭️  Skipping transcription (already transcribed)")
                results['total_skipped'] += 1
                episode_result['transcription_status'] = 'skipped'
            
            # Step 2: Summarize if needed (refresh episode after transcription)
            episode_updated = db.get_episode_by_id(episode_id)
            summary = episode_updated.get('summary') if episode_updated else None
            
            has_summary = False
            if summary:
                if isinstance(summary, dict):
                    summary_text = summary.get('summary', '')
                    key_topics = summary.get('key_topics', [])
                    if summary_text or key_topics:
                        has_summary = True
            
            if not has_summary:
                # Check if we have transcript now
                transcript = episode_updated.get('transcript') if episode_updated else None
                has_transcript_now = False
                if transcript:
                    if isinstance(transcript, dict):
                        transcript_text = transcript.get('text', '')
                        segments = transcript.get('segments', [])
                        if transcript_text or (segments and len(segments) > 0):
                            has_transcript_now = True
                
                if has_transcript_now:
                    print(f"\n[4.3.{idx}] Summarizing episode...")
                    summarization_start = time.time()
                    
                    try:
                        success, error, summary_data = summarize_episode(episode_id, db)
                        summarization_time = time.time() - summarization_start
                        
                        if success:
                            results['total_summarized'] += 1
                            episode_result['summarization_status'] = 'success'
                            episode_result['summarization_time'] = summarization_time
                            
                            if summary_data:
                                key_topics = summary_data.get('key_topics', [])
                                themes = summary_data.get('themes', [])
                                print(f"✓ Summarized in {summarization_time:.1f}s ({len(key_topics)} topics, {len(themes)} themes)")
                            else:
                                print(f"✓ Summarized in {summarization_time:.1f}s")
                        else:
                            results['total_failed'] += 1
                            episode_result['summarization_status'] = 'failed'
                            if not episode_result['error']:
                                episode_result['error'] = error
                            print(f"✗ Summarization failed: {error}")
                    except Exception as e:
                        results['total_failed'] += 1
                        episode_result['summarization_status'] = 'failed'
                        if not episode_result['error']:
                            episode_result['error'] = str(e)
                        print(f"✗ Summarization error: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"⏭️  Skipping summarization (no transcript available)")
                    episode_result['summarization_status'] = 'skipped'
            else:
                print(f"⏭️  Skipping summarization (already summarized)")
                results['total_skipped'] += 1
                episode_result['summarization_status'] = 'skipped'
            
            if episode_result['transcription_status'] in ['success', 'skipped'] and \
               episode_result['summarization_status'] in ['success', 'skipped']:
                results['total_processed'] += 1
            
            results['episode_results'].append(episode_result)
        
        db.close()
        
        # Summary
        print("\n" + "=" * 70)
        print("PROCESSING SUMMARY")
        print("=" * 70)
        print(f"\nTotal episodes processed: {len(episodes)}")
        print(f"✅ Successfully transcribed: {results['total_transcribed']}")
        print(f"✅ Successfully summarized: {results['total_summarized']}")
        print(f"⏭️  Skipped (already done): {results['total_skipped']}")
        print(f"❌ Failed: {results['total_failed']}")
        print(f"✅ Fully processed: {results['total_processed']}")
        
        if results['episode_results']:
            print("\nEpisode Results:")
            for result in results['episode_results']:
                status_icon = "✅" if result['transcription_status'] == 'success' and result['summarization_status'] == 'success' else \
                              "⏭️" if result['transcription_status'] == 'skipped' and result['summarization_status'] == 'skipped' else \
                              "❌"
                print(f"  {status_icon} {result['title'][:60]}... "
                      f"(Transcribe: {result['transcription_status']}, "
                      f"Summarize: {result['summarization_status']})")
                if result.get('error'):
                    print(f"     Error: {result['error']}")
        
        print("\n✅ TEST 4 PASSED: Processing completed")
        return results
        
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {}


def main():
    """Run complete process for all downloaded episodes."""
    print("\n" + "="*70)
    print("PROCESS ALL DOWNLOADS TEST")
    print("Testing: Find Downloads -> Add to DB -> Transcribe -> Summarize")
    print("="*70)
    
    results = {
        'test_name': 'process_all_downloads',
        'timestamp': datetime.now().isoformat(),
        'database': 'PostgreSQL'
    }
    
    try:
        # Test 1: Database connection
        if not test_database_connection():
            print("\n❌ Pipeline test aborted: Database connection failed")
            results['error'] = 'Database connection failed'
            return results
        
        # Test 2: Find missing episodes
        missing_files = test_find_missing_episodes()
        results['missing_files_count'] = len(missing_files)
        
        if not missing_files:
            print("\n✅ All downloaded files are already in the database")
            print("   Checking for episodes needing processing...")
            
            # Get episodes that need processing
            db = PostgresDB()
            all_episodes = db.get_all_podcasts(status=None, limit=1000)
            
            needs_processing = []
            for ep in all_episodes:
                file_path = ep.get('audio_file_path')
                if file_path and Path(file_path).exists():
                    transcript = ep.get('transcript')
                    summary = ep.get('summary')
                    
                    has_transcript = False
                    if transcript:
                        if isinstance(transcript, dict):
                            if transcript.get('text') or transcript.get('segments'):
                                has_transcript = True
                    
                    has_summary = False
                    if summary:
                        if isinstance(summary, dict):
                            if summary.get('summary') or summary.get('key_topics'):
                                has_summary = True
                    
                    if not has_transcript or (has_transcript and not has_summary):
                        needs_processing.append(ep)
            
            db.close()
            
            if needs_processing:
                print(f"   Found {len(needs_processing)} episode(s) needing processing")
                process_results = test_process_episodes(needs_processing)
                results['processing'] = process_results
            else:
                print("   ✅ All episodes are fully processed")
                results['processing'] = {'total_processed': 0, 'message': 'All episodes already processed'}
            
            return results
        
        # Test 3: Add missing episodes to database
        added_episodes = test_add_missing_to_database(missing_files)
        results['added_episodes_count'] = len(added_episodes)
        
        if not added_episodes:
            print("\n⚠️  No episodes were added to database")
            results['error'] = 'Failed to add episodes to database'
            return results
        
        # Test 4: Process episodes
        process_results = test_process_episodes(added_episodes)
        results['processing'] = process_results
        
        # Final summary
        print("\n" + "="*70)
        print("🎉 PROCESS ALL DOWNLOADS TEST COMPLETED!")
        print("="*70)
        
        print(f"\nSummary:")
        print(f"  📁 Found: {len(missing_files)} downloaded file(s)")
        print(f"  💾 Added to DB: {len(added_episodes)} episode(s)")
        print(f"  🎙️  Transcribed: {process_results.get('total_transcribed', 0)} episode(s)")
        print(f"  ✅ Summarized: {process_results.get('total_summarized', 0)} episode(s)")
        print(f"  ⏭️  Skipped: {process_results.get('total_skipped', 0)} episode(s)")
        print(f"  ❌ Failed: {process_results.get('total_failed', 0)} episode(s)")
        print(f"  ✅ Fully Processed: {process_results.get('total_processed', 0)} episode(s)")
        
        # Save results
        output_dir = Path("test-results")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"process_all_downloads_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")
        print("\n✅ Process all downloads working!")
        
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

