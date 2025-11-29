#!/usr/bin/env python3
"""
Sync transcribed episodes from DuckDB to PostgreSQL.
Useful for migrating existing transcripts.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import P3Database
from utils.postgres_db import PostgresDB


def sync_transcribed_to_postgres():
    """Sync all transcribed episodes from DuckDB to PostgreSQL."""
    print("=" * 70)
    print("SYNC TRANSCRIBED EPISODES TO POSTGRESQL")
    print("=" * 70)
    
    # Initialize databases
    print("\n[1] Initializing databases...")
    duckdb = P3Database()
    pg_db = PostgresDB()
    print("✅ Databases initialized")
    
    # Get transcribed episodes from DuckDB
    print("\n[2] Finding transcribed episodes in DuckDB...")
    transcribed_episodes = duckdb.get_episodes_by_status('transcribed')
    
    if not transcribed_episodes:
        print("⚠️  No transcribed episodes found in DuckDB")
        duckdb.close()
        pg_db.close()
        return
    
    print(f"✅ Found {len(transcribed_episodes)} transcribed episode(s)\n")
    
    # Sync each episode
    print("=" * 70)
    print("SYNCING EPISODES")
    print("=" * 70)
    
    synced_count = 0
    skipped_count = 0
    error_count = 0
    
    for idx, episode in enumerate(transcribed_episodes, 1):
        episode_id = episode['id']
        episode_title = episode['title']
        
        print(f"\n[{idx}/{len(transcribed_episodes)}] Episode ID: {episode_id}")
        print(f"Title: {episode_title[:70]}...")
        
        try:
            # Get transcript from DuckDB
            transcripts = duckdb.get_transcripts_for_episode(episode_id)
            
            if not transcripts:
                print(f"  ⚠️  No transcript segments found, skipping")
                skipped_count += 1
                continue
            
            # Get podcast info
            podcast_info = None
            if episode.get('podcast_id'):
                try:
                    podcasts = duckdb.conn.execute(
                        "SELECT title, rss_url, category FROM podcasts WHERE id = ?",
                        (episode['podcast_id'],)
                    ).fetchone()
                    if podcasts:
                        podcast_info = {
                            'name': podcasts[0],
                            'url': podcasts[1],
                            'category': podcasts[2]
                        }
                except:
                    pass
            
            if not podcast_info and episode.get('podcast_title'):
                podcast_info = {
                    'name': episode.get('podcast_title'),
                    'url': None,
                    'category': None
                }
            
            # Calculate file size
            file_size_bytes = None
            if episode.get('file_path'):
                audio_path = Path(episode['file_path'])
                if audio_path.exists():
                    file_size_bytes = audio_path.stat().st_size
            
            # Prepare transcript data
            full_text = "\n".join(t.get('text', '') for t in transcripts)
            transcript_data = {
                'segments': transcripts,
                'text': full_text,
                'language': 'en',  # Default, could be extracted if available
                'provider': 'groq',
                'chunked': False
            }
            
            # Save to PostgreSQL
            pg_episode_id = pg_db.save_podcast(
                title=episode['title'],
                description=None,
                feed_url=podcast_info['url'] if podcast_info else None,
                episode_url=episode.get('url'),
                published_at=episode.get('date'),
                duration_seconds=episode.get('duration_seconds'),
                audio_file_path=episode.get('file_path'),
                file_size_bytes=file_size_bytes,
                status='transcribed',
                transcript=transcript_data,
                summary=None,
                podcast_feed_name=podcast_info['name'] if podcast_info else None,
                podcast_category=podcast_info['category'] if podcast_info else None
            )
            
            print(f"  ✅ Synced to PostgreSQL (ID: {pg_episode_id})")
            print(f"     Transcript: {len(transcripts)} segments, {len(full_text):,} chars")
            synced_count += 1
            
        except Exception as e:
            print(f"  ❌ Error syncing: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("SYNC SUMMARY")
    print("=" * 70)
    print(f"Total episodes: {len(transcribed_episodes)}")
    print(f"✅ Synced: {synced_count}")
    print(f"⚠️  Skipped: {skipped_count}")
    print(f"❌ Errors: {error_count}")
    
    # Verify in PostgreSQL
    print("\n" + "=" * 70)
    print("VERIFYING POSTGRESQL")
    print("=" * 70)
    pg_podcasts = pg_db.get_all_podcasts(status='transcribed')
    print(f"\nFound {len(pg_podcasts)} transcribed episodes in PostgreSQL:\n")
    
    for p in pg_podcasts:
        print(f"ID: {p['id']} - {p['title'][:60]}...")
        if p.get('transcript'):
            if isinstance(p['transcript'], dict):
                segments = p['transcript'].get('segments', [])
                text_len = len(p['transcript'].get('text', ''))
                print(f"  ✅ Transcript: {len(segments)} segments, {text_len:,} chars")
            else:
                print(f"  ⚠️  Transcript: Present but not dict")
        else:
            print(f"  ❌ Transcript: None")
        print()
    
    duckdb.close()
    pg_db.close()
    
    print("=" * 70)
    if synced_count > 0:
        print("✅ Sync completed successfully!")
    else:
        print("⚠️  No episodes were synced")
    print("=" * 70)


if __name__ == "__main__":
    try:
        sync_transcribed_to_postgres()
    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

