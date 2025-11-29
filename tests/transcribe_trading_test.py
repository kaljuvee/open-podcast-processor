#!/usr/bin/env python3
"""
Test script to transcribe downloaded episodes from trading podcasts.
This is the most difficult step, so we test it carefully with progress tracking.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.postgres_db import PostgresDB
from utils.processing import transcribe_episode
from utils.transcriber_groq import AudioTranscriber
from utils.config import get_groq_api_key


def test_transcribe_downloaded_episodes():
    """Transcribe all downloaded episodes, prioritizing trading podcasts."""
    print("=" * 70)
    print("TRANSCRIPTION TEST: Trading Podcast Episodes")
    print("=" * 70)
    
    # Initialize database
    print("\n[1] Initializing database...")
    db = PostgresDB()
    print("✅ PostgreSQL database initialized")
    
    # Get downloaded episodes
    print("\n[2] Finding downloaded episodes...")
    downloaded_episodes = db.get_episodes_by_status('downloaded')
    
    if not downloaded_episodes:
        print("⚠️  No episodes with 'downloaded' status found")
        print("\n   To download episodes first, run:")
        print("   python tests/test_download_trading.py")
        db.close()
        return False
    
    print(f"✅ Found {len(downloaded_episodes)} episode(s) ready for transcription\n")
    
    # Show episodes to be transcribed
    print("=" * 70)
    print("EPISODES TO TRANSCRIBE")
    print("=" * 70)
    for i, ep in enumerate(downloaded_episodes, 1):
        # PostgreSQL uses audio_file_path, DuckDB uses file_path
        file_path = ep.get('audio_file_path') or ep.get('file_path')
        file_exists = Path(file_path).exists() if file_path else False
        file_status = "✅" if file_exists else "❌ MISSING"
        print(f"\n{i}. Episode ID: {ep['id']}")
        print(f"   Title: {ep['title'][:70]}...")
        print(f"   Podcast: {ep.get('podcast_feed_name') or ep.get('podcast_title', 'Unknown')}")
        print(f"   File: {file_path or 'N/A'} {file_status}")
        if ep.get('duration_seconds'):
            minutes = ep['duration_seconds'] // 60
            seconds = ep['duration_seconds'] % 60
            print(f"   Duration: {minutes}m{seconds}s")
    
    # Filter out episodes with missing files
    valid_episodes = []
    for ep in downloaded_episodes:
        file_path = ep.get('audio_file_path') or ep.get('file_path')
        if file_path and Path(file_path).exists():
            valid_episodes.append(ep)
    
    if not valid_episodes:
        print("\n❌ No episodes with valid audio files found")
        print("   Please download episodes first")
        db.close()
        return False
    
    missing_count = len(downloaded_episodes) - len(valid_episodes)
    if missing_count > 0:
        print(f"\n⚠️  {missing_count} episode(s) have missing files and will be skipped")
    
    print(f"\n✅ {len(valid_episodes)} episode(s) ready for transcription")
    
    # Confirm before proceeding
    print("\n" + "=" * 70)
    print("READY TO START TRANSCRIPTION")
    print("=" * 70)
    print(f"\nThis will transcribe {len(valid_episodes)} episode(s) using Groq Whisper API.")
    print("Transcription is the most time-consuming step.")
    print("\nEstimated time:")
    total_duration = sum(ep.get('duration_seconds', 0) or 0 for ep in valid_episodes)
    if total_duration > 0:
        # Groq processes at ~0.5x realtime (2x faster), so estimate is conservative
        estimated_minutes = (total_duration / 60) * 0.5
        print(f"  Total audio: {total_duration//60}m{total_duration%60}s")
        print(f"  Estimated processing: ~{int(estimated_minutes)} minutes")
    else:
        print("  (Duration unknown, estimating from file sizes)")
    
    print("\nPress Ctrl+C to cancel, or Enter to continue...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n⚠️  Transcription cancelled by user")
        db.close()
        return False
    
    # Transcribe each episode
    print("\n" + "=" * 70)
    print("STARTING TRANSCRIPTION")
    print("=" * 70)
    
    results = {
        'total_transcribed': 0,
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
            # Transcribe using the processing utility (which handles errors)
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
                    print(f"\nSample transcript:")
                    print(f"  [{int(transcripts[0].get('timestamp_start', 0))}s] {transcripts[0].get('text', '')[:100]}...")
                
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
    
    # Final summary
    print("\n" + "=" * 70)
    print("TRANSCRIPTION SUMMARY")
    print("=" * 70)
    print(f"\nTotal episodes processed: {len(valid_episodes)}")
    print(f"✅ Successfully transcribed: {results['total_transcribed']}")
    print(f"❌ Failed: {results['total_failed']}")
    
    if results['episode_results']:
        print("\nEpisode Results:")
        for result in results['episode_results']:
            status_icon = "✅" if result['status'] == 'success' else "❌"
            print(f"  {status_icon} {result['title'][:60]}...")
            if result['status'] == 'success':
                print(f"     Segments: {result.get('segments', 0)}")
            else:
                print(f"     Error: {result.get('error', 'Unknown')}")
    
    # Show transcribed episodes ready for summarization
    print("\n" + "=" * 70)
    print("EPISODES READY FOR SUMMARIZATION")
    print("=" * 70)
    transcribed_episodes = db.get_episodes_by_status('transcribed')
    
    if transcribed_episodes:
        print(f"\nFound {len(transcribed_episodes)} episode(s) with status 'transcribed':\n")
        for ep in transcribed_episodes[:10]:  # Show first 10
            transcripts = db.get_transcripts_for_episode(ep['id'])
            print(f"  ID: {ep['id']} - {ep['title'][:60]}...")
            print(f"      Segments: {len(transcripts)}")
            print()
    else:
        print("\n⚠️  No episodes with 'transcribed' status found")
    
    db.close()
    
    print("=" * 70)
    if results['total_transcribed'] > 0:
        print("✅ Transcription test completed successfully!")
        print(f"   {results['total_transcribed']} episode(s) ready for summarization")
    else:
        print("⚠️  Transcription test completed with no successful transcriptions")
    print("=" * 70)
    
    return results['total_transcribed'] > 0


if __name__ == "__main__":
    try:
        success = test_transcribe_downloaded_episodes()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Transcription test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Transcription test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

