"""
Batch processing utility for demo purposes.
Transcribes all downloaded episodes (focus on transcription for demo).
Uses PostgreSQL and skips already completed steps.
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
from utils.postgres_db import PostgresDB
from utils.processing import transcribe_episode, summarize_episode
from utils.transcriber_groq import AudioTranscriber
from utils.cleaner_groq import TranscriptCleaner
from utils.config import get_groq_api_key


def batch_transcribe_downloaded(
    db: Optional[PostgresDB] = None,
    episode_ids: Optional[List[int]] = None
) -> Dict[str, any]:
    """
    Transcribe all downloaded episodes (or specific episode IDs).
    Skips episodes that are already transcribed or processed.
    
    Args:
        db: Database instance (creates new if not provided)
        episode_ids: Optional list of specific episode IDs to transcribe.
                     If None, transcribes all episodes with 'downloaded' status.
        
    Returns:
        Dictionary with processing results: {
            'total_transcribed': int,
            'total_skipped': int,
            'total_failed': int,
            'episode_results': List[Dict]  # List of {episode_id, title, status, error}
        }
    """
    if db is None:
        db = PostgresDB()
        should_close = True
    else:
        should_close = False
    
    results = {
        'total_transcribed': 0,
        'total_skipped': 0,
        'total_failed': 0,
        'episode_results': []
    }
    
    try:
        # Get episodes to process
        if episode_ids:
            episodes_to_process = []
            for ep_id in episode_ids:
                episode = db.get_episode_by_id(ep_id)
                if episode:
                    # Check if already transcribed or processed
                    if episode.get('status') == 'transcribed' or episode.get('status') == 'processed':
                        print(f"    ⏭️  Skipping episode {ep_id}: already transcribed (status: {episode.get('status')})")
                        results['total_skipped'] += 1
                        continue
                    # Check if file exists
                    file_path = episode.get('audio_file_path') or episode.get('file_path')
                    if not file_path or not Path(file_path).exists():
                        print(f"    ⚠️  Skipping episode {ep_id}: file not found ({file_path})")
                        results['total_skipped'] += 1
                        continue
                    # Only process if status is 'downloaded'
                    if episode.get('status') == 'downloaded':
                        episodes_to_process.append(episode)
                    else:
                        print(f"    ⚠️  Skipping episode {ep_id}: status is '{episode.get('status')}' (not 'downloaded')")
                        results['total_skipped'] += 1
        else:
            all_downloaded = db.get_episodes_by_status('downloaded')
            episodes_to_process = []
            for episode in all_downloaded:
                # Check if file exists
                file_path = episode.get('audio_file_path') or episode.get('file_path')
                if file_path and Path(file_path).exists():
                    episodes_to_process.append(episode)
                else:
                    print(f"    ⚠️  Skipping episode {episode['id']}: file not found")
                    results['total_skipped'] += 1
        
        if not episodes_to_process:
            results['message'] = "No downloaded episodes to transcribe"
            return results
        
        print(f"🎙️  Batch transcribing {len(episodes_to_process)} episode(s)...")
        
        # Initialize transcriber once
        try:
            api_key = get_groq_api_key()
            transcriber = AudioTranscriber(db, api_key=api_key)
        except Exception as e:
            results['error'] = f"Failed to initialize transcriber: {str(e)}"
            return results
        
        # Process each episode
        for episode in episodes_to_process:
            episode_id = episode['id']
            episode_title = episode.get('title', f'Episode {episode_id}')
            
            print(f"  Transcribing: {episode_title[:60]}...")
            
            try:
                success, error = transcribe_episode(episode_id, db)
                
                if success:
                    results['total_transcribed'] += 1
                    results['episode_results'].append({
                        'episode_id': episode_id,
                        'title': episode_title,
                        'status': 'transcribed',
                        'error': None
                    })
                    print(f"    ✓ Transcribed: {episode_title[:60]}")
                else:
                    results['total_failed'] += 1
                    results['episode_results'].append({
                        'episode_id': episode_id,
                        'title': episode_title,
                        'status': 'failed',
                        'error': error or 'Unknown error'
                    })
                    print(f"    ✗ Failed: {episode_title[:60]} - {error}")
                    
            except Exception as e:
                results['total_failed'] += 1
                results['episode_results'].append({
                    'episode_id': episode_id,
                    'title': episode_title,
                    'status': 'failed',
                    'error': str(e)
                })
                print(f"    ✗ Error: {episode_title[:60]} - {str(e)}")
        
        print(f"\n✅ Batch transcription complete:")
        print(f"   Transcribed: {results['total_transcribed']}")
        print(f"   Skipped: {results['total_skipped']}")
        print(f"   Failed: {results['total_failed']}")
        
        return results
        
    finally:
        if should_close and db:
            db.close()


def batch_summarize_transcribed(
    db: Optional[PostgresDB] = None,
    episode_ids: Optional[List[int]] = None
) -> Dict[str, any]:
    """
    Summarize all transcribed episodes (or specific episode IDs).
    Skips episodes that are already processed.
    
    Args:
        db: Database instance (creates new if not provided)
        episode_ids: Optional list of specific episode IDs to summarize.
                     If None, summarizes all episodes with 'transcribed' status.
        
    Returns:
        Dictionary with processing results: {
            'total_summarized': int,
            'total_skipped': int,
            'total_failed': int,
            'episode_results': List[Dict]  # List of {episode_id, title, status, error}
        }
    """
    if db is None:
        db = PostgresDB()
        should_close = True
    else:
        should_close = False
    
    results = {
        'total_summarized': 0,
        'total_skipped': 0,
        'total_failed': 0,
        'episode_results': []
    }
    
    try:
        # Get episodes to process
        if episode_ids:
            episodes_to_process = []
            for ep_id in episode_ids:
                episode = db.get_episode_by_id(ep_id)
                if episode:
                    # Check if already processed
                    if episode.get('status') == 'processed':
                        if episode.get('summary'):
                            print(f"    ⏭️  Skipping episode {ep_id}: already processed")
                            results['total_skipped'] += 1
                            continue
                    # Only process if status is 'transcribed' or 'processed' (but no summary)
                    if episode.get('status') == 'transcribed' or (episode.get('status') == 'processed' and not episode.get('summary')):
                        episodes_to_process.append(episode)
                    else:
                        print(f"    ⚠️  Skipping episode {ep_id}: status is '{episode.get('status')}' (not 'transcribed')")
                        results['total_skipped'] += 1
        else:
            all_transcribed = db.get_episodes_by_status('transcribed')
            episodes_to_process = []
            for episode in all_transcribed:
                episodes_to_process.append(episode)
            # Also check for processed episodes without summaries
            all_processed = db.get_episodes_by_status('processed')
            for episode in all_processed:
                if not episode.get('summary'):
                    episodes_to_process.append(episode)
        
        if not episodes_to_process:
            results['message'] = "No transcribed episodes to summarize"
            return results
        
        print(f"🧠 Batch summarizing {len(episodes_to_process)} episode(s)...")
        
        # Process each episode
        for episode in episodes_to_process:
            episode_id = episode['id']
            episode_title = episode.get('title', f'Episode {episode_id}')
            
            # Double-check if already processed (race condition check)
            episode_check = db.get_episode_by_id(episode_id)
            if episode_check.get('status') == 'processed' and episode_check.get('summary'):
                print(f"    ⏭️  Skipping episode {episode_id}: already processed")
                results['total_skipped'] += 1
                continue
            
            print(f"  Summarizing: {episode_title[:60]}...")
            
            try:
                success, error, summary = summarize_episode(episode_id, db)
                
                if success:
                    results['total_summarized'] += 1
                    results['episode_results'].append({
                        'episode_id': episode_id,
                        'title': episode_title,
                        'status': 'summarized',
                        'error': None,
                        'summary': summary
                    })
                    print(f"    ✓ Summarized: {episode_title[:60]}")
                else:
                    results['total_failed'] += 1
                    results['episode_results'].append({
                        'episode_id': episode_id,
                        'title': episode_title,
                        'status': 'failed',
                        'error': error or 'Unknown error'
                    })
                    print(f"    ✗ Failed: {episode_title[:60]} - {error}")
                    
            except Exception as e:
                results['total_failed'] += 1
                results['episode_results'].append({
                    'episode_id': episode_id,
                    'title': episode_title,
                    'status': 'failed',
                    'error': str(e)
                })
                print(f"    ✗ Error: {episode_title[:60]} - {str(e)}")
        
        print(f"\n✅ Batch summarization complete:")
        print(f"   Summarized: {results['total_summarized']}")
        print(f"   Skipped: {results['total_skipped']}")
        print(f"   Failed: {results['total_failed']}")
        
        return results
        
    finally:
        if should_close and db:
            db.close()


def batch_process_all(
    db: Optional[PostgresDB] = None,
    audio_format: str = "mp3"
) -> Dict[str, any]:
    """
    Full pipeline: download 1 episode per feed, convert to MP3, transcribe, and summarize.
    Skips steps that are already complete.
    
    Args:
        db: Database instance (creates new if not provided)
        audio_format: Audio format for download ('mp3' or 'wav')
        
    Returns:
        Combined results from download, transcription, and summarization
    """
    from utils.batch_download import batch_download_one_per_feed
    
    if db is None:
        db = PostgresDB()
        should_close = True
    else:
        should_close = False
    
    try:
        # Step 1: Download (with MP3 conversion)
        download_results = batch_download_one_per_feed(db=db, audio_format=audio_format)
        
        # Step 2: Transcribe (will skip already transcribed episodes)
        episode_ids = [ep['id'] for ep in download_results.get('episodes', [])]
        transcription_results = batch_transcribe_downloaded(db=db, episode_ids=episode_ids)
        
        # Step 3: Summarize transcribed episodes (will skip already processed episodes)
        # Get all transcribed episodes, not just from this batch
        transcribed_episodes = db.get_episodes_by_status('transcribed')
        transcribed_episode_ids = [ep['id'] for ep in transcribed_episodes]
        summarization_results = batch_summarize_transcribed(db=db, episode_ids=transcribed_episode_ids)
        
        return {
            'download': download_results,
            'transcription': transcription_results,
            'summarization': summarization_results,
            'summary': {
                'downloaded': download_results.get('total_downloaded', 0),
                'transcribed': transcription_results.get('total_transcribed', 0),
                'summarized': summarization_results.get('total_summarized', 0),
                'skipped_transcription': transcription_results.get('total_skipped', 0),
                'skipped_summarization': summarization_results.get('total_skipped', 0),
                'failed': transcription_results.get('total_failed', 0) + summarization_results.get('total_failed', 0)
            }
        }
        
    finally:
        if should_close and db:
            db.close()

