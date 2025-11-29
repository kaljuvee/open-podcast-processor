"""
Batch processing utility that saves results to PostgreSQL.
Processes locally and stores to PostgreSQL database.
"""

from typing import Dict, List, Optional
from pathlib import Path
from utils.database import P3Database
from utils.postgres_db import PostgresDB
from utils.processing import transcribe_episode, summarize_episode
from utils.transcriber_groq import AudioTranscriber
from utils.cleaner_groq import TranscriptCleaner
from utils.config import get_groq_api_key


def migrate_duckdb_to_postgres(duckdb: P3Database, postgres: PostgresDB):
    """
    Migrate podcasts from DuckDB to PostgreSQL.
    
    Args:
        duckdb: DuckDB instance
        postgres: PostgreSQL instance
    """
    print("Migrating podcasts from DuckDB to PostgreSQL...")
    
    # Get all episodes from DuckDB
    episodes = duckdb.get_episodes_by_status('downloaded')
    episodes.extend(duckdb.get_episodes_by_status('transcribed'))
    episodes.extend(duckdb.get_episodes_by_status('processed'))
    
    # Remove duplicates
    seen_ids = set()
    unique_episodes = []
    for ep in episodes:
        if ep['id'] not in seen_ids:
            seen_ids.add(ep['id'])
            unique_episodes.append(ep)
    
    print(f"Found {len(unique_episodes)} episodes to migrate")
    
    migrated_count = 0
    for episode in unique_episodes:
        try:
            # Get transcript if available
            transcript_data = None
            if episode.get('status') in ['transcribed', 'processed']:
                segments = duckdb.get_transcripts_for_episode(episode['id'])
                if segments:
                    transcript_data = {
                        'segments': segments,
                        'text': '\n'.join([s.get('text', '') for s in segments]),
                        'language': 'en'
                    }
            
            # Get summary if available
            summary_data = None
            if episode.get('status') == 'processed':
                summaries = duckdb.get_summaries_for_episode(episode['id'])
                if summaries:
                    summary = summaries[0]
                    summary_data = {
                        'key_topics': summary.get('key_topics', []),
                        'themes': summary.get('themes', []),
                        'quotes': summary.get('quotes', []),
                        'startups': summary.get('startups', []),
                        'summary': summary.get('full_summary', '')
                    }
            
            # Get podcast info
            podcast = duckdb.get_podcast_by_id(episode.get('podcast_id'))
            podcast_name = podcast.get('name') if podcast else None
            podcast_category = podcast.get('category') if podcast else None
            
            # Save to PostgreSQL
            podcast_id = postgres.save_podcast(
                title=episode.get('title', 'Untitled'),
                description=episode.get('description'),
                feed_url=episode.get('feed_url'),
                episode_url=episode.get('url'),
                published_at=episode.get('published_at'),
                duration_seconds=episode.get('duration_seconds'),
                audio_file_path=episode.get('file_path'),
                file_size_bytes=None,  # Could calculate from file if exists
                status=episode.get('status', 'downloaded'),
                transcript=transcript_data,
                summary=summary_data,
                podcast_feed_name=podcast_name,
                podcast_category=podcast_category
            )
            
            migrated_count += 1
            print(f"  ✓ Migrated: {episode.get('title', 'Untitled')[:60]}")
            
        except Exception as e:
            print(f"  ✗ Failed to migrate episode {episode.get('id')}: {e}")
    
    print(f"\n✅ Migration complete: {migrated_count}/{len(unique_episodes)} episodes migrated")
    return migrated_count


def process_and_save_to_postgres(
    duckdb: P3Database,
    postgres: PostgresDB,
    episode_ids: Optional[List[int]] = None
) -> Dict[str, any]:
    """
    Process episodes locally and save results to PostgreSQL.
    
    Args:
        duckdb: DuckDB instance (for local processing)
        postgres: PostgreSQL instance (for storage)
        episode_ids: Optional list of episode IDs to process
        
    Returns:
        Dictionary with processing results
    """
    results = {
        'transcribed': 0,
        'summarized': 0,
        'saved_to_postgres': 0,
        'errors': 0
    }
    
    # Get episodes to process
    if episode_ids:
        episodes_to_process = []
        for ep_id in episode_ids:
            episode = duckdb.get_episode_by_id(ep_id)
            if episode and episode.get('status') == 'downloaded':
                episodes_to_process.append(episode)
    else:
        episodes_to_process = duckdb.get_episodes_by_status('downloaded')
    
    if not episodes_to_process:
        print("No episodes to process")
        return results
    
    print(f"Processing {len(episodes_to_process)} episode(s) locally and saving to PostgreSQL...")
    
    api_key = get_groq_api_key()
    transcriber = AudioTranscriber(duckdb, api_key=api_key)
    cleaner = TranscriptCleaner(duckdb, api_key=api_key)
    
    for episode in episodes_to_process:
        episode_id = episode['id']
        episode_title = episode.get('title', f'Episode {episode_id}')
        
        try:
            # Step 1: Transcribe
            print(f"  Transcribing: {episode_title[:60]}...")
            success, error = transcribe_episode(episode_id, duckdb)
            
            if not success:
                print(f"    ✗ Transcription failed: {error}")
                results['errors'] += 1
                continue
            
            results['transcribed'] += 1
            
            # Get transcript
            segments = duckdb.get_transcripts_for_episode(episode_id)
            transcript_data = {
                'segments': segments,
                'text': '\n'.join([s.get('text', '') for s in segments]),
                'language': 'en'
            }
            
            # Step 2: Summarize
            print(f"  Summarizing: {episode_title[:60]}...")
            success, error, summary = summarize_episode(episode_id, duckdb)
            
            if not success:
                print(f"    ✗ Summarization failed: {error}")
                results['errors'] += 1
            else:
                results['summarized'] += 1
            
            # Step 3: Save to PostgreSQL
            print(f"  Saving to PostgreSQL: {episode_title[:60]}...")
            
            # Get podcast info
            podcast = duckdb.get_podcast_by_id(episode.get('podcast_id'))
            podcast_name = podcast.get('name') if podcast else None
            podcast_category = podcast.get('category') if podcast else None
            
            # Calculate file size if file exists
            file_size_bytes = None
            if episode.get('file_path'):
                audio_path = Path(episode['file_path'])
                if audio_path.exists():
                    file_size_bytes = audio_path.stat().st_size
            
            postgres_id = postgres.save_podcast(
                title=episode.get('title', 'Untitled'),
                description=episode.get('description'),
                feed_url=episode.get('feed_url'),
                episode_url=episode.get('url'),
                published_at=episode.get('published_at'),
                duration_seconds=episode.get('duration_seconds'),
                audio_file_path=episode.get('file_path'),
                file_size_bytes=file_size_bytes,
                status='processed' if summary else 'transcribed',
                transcript=transcript_data,
                summary=summary,
                podcast_feed_name=podcast_name,
                podcast_category=podcast_category
            )
            
            results['saved_to_postgres'] += 1
            print(f"    ✓ Saved to PostgreSQL (ID: {postgres_id})")
            
        except Exception as e:
            print(f"    ✗ Error processing episode {episode_id}: {e}")
            import traceback
            traceback.print_exc()
            results['errors'] += 1
    
    print(f"\n✅ Processing complete:")
    print(f"   Transcribed: {results['transcribed']}")
    print(f"   Summarized: {results['summarized']}")
    print(f"   Saved to PostgreSQL: {results['saved_to_postgres']}")
    print(f"   Errors: {results['errors']}")
    
    return results

