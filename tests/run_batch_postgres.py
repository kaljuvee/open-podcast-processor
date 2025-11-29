"""
Batch processing script that processes locally and saves to PostgreSQL.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import P3Database
from utils.postgres_db import PostgresDB
from utils.batch_download import batch_download_one_per_feed
from utils.batch_process_postgres import process_and_save_to_postgres, migrate_duckdb_to_postgres


def run_batch_postgres(skip_download=False, migrate_existing=False):
    """
    Run batch processing and save to PostgreSQL.
    
    Args:
        skip_download: If True, skip download and process existing episodes
        migrate_existing: If True, migrate existing DuckDB data to PostgreSQL first
    """
    print("=" * 60)
    print("Open Podcast Processor - Batch Processing to PostgreSQL")
    print("=" * 60)
    print()
    print("Using Groq Whisper Large V3 Turbo for transcription")
    print("Using Groq models via LangChain for summarization")
    print()
    
    # Initialize databases
    duckdb = P3Database(db_path="db/demo.duckdb")
    
    try:
        postgres = PostgresDB()
        print(f"✓ Connected to PostgreSQL (schema: {postgres.schema})")
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        print("Please ensure DB_URL is set in your .env file")
        return
    
    # Initialize schema if needed
    try:
        print("\nInitializing PostgreSQL schema...")
        sql_file = Path("sql/schema.sql")
        if sql_file.exists():
            postgres.execute_sql_file(str(sql_file))
            print("✓ Schema initialized")
        else:
            print("⚠️  SQL schema file not found, assuming schema exists")
    except Exception as e:
        print(f"⚠️  Schema initialization warning: {e}")
    
    results = {
        'test_name': 'batch_postgres',
        'timestamp': datetime.now().isoformat(),
        'duckdb_path': 'db/demo.duckdb'
    }
    
    try:
        # Migrate existing data if requested
        if migrate_existing:
            print("\n" + "=" * 60)
            print("Migrating existing DuckDB data to PostgreSQL")
            print("=" * 60)
            migrated_count = migrate_duckdb_to_postgres(duckdb, postgres)
            results['migrated'] = migrated_count
        
        # Step 1: Download (if not skipping)
        if not skip_download:
            print("\n" + "=" * 60)
            print("Step 1: Batch Download")
            print("=" * 60)
            download_results = batch_download_one_per_feed(
                db=duckdb,
                data_dir="data/demo",
                audio_format="mp3"
            )
            results['download'] = download_results
            episode_ids = [ep['id'] for ep in download_results.get('episodes', [])]
            print(f"Downloaded {len(episode_ids)} episode(s)")
        else:
            print("\n" + "=" * 60)
            print("Step 1: Using existing downloaded episodes")
            print("=" * 60)
            downloaded_episodes = duckdb.get_episodes_by_status('downloaded')
            episode_ids = [ep['id'] for ep in downloaded_episodes]
            print(f"Found {len(episode_ids)} downloaded episode(s)")
            results['download'] = {
                'total_downloaded': len(episode_ids),
                'message': 'Using existing episodes'
            }
        
        # Step 2: Process and save to PostgreSQL
        if episode_ids:
            print("\n" + "=" * 60)
            print("Step 2: Processing and Saving to PostgreSQL")
            print("=" * 60)
            
            processing_results = process_and_save_to_postgres(
                duckdb=duckdb,
                postgres=postgres,
                episode_ids=episode_ids
            )
            results['processing'] = processing_results
        else:
            print("\n⚠️  No episodes to process")
            results['processing'] = {
                'message': 'No episodes to process'
            }
        
        # Step 3: Verify saved podcasts
        print("\n" + "=" * 60)
        print("Step 3: Verification")
        print("=" * 60)
        
        all_podcasts = postgres.get_all_podcasts()
        stats = postgres.get_stats()
        
        print(f"✓ Total podcasts in PostgreSQL: {stats.get('total_podcasts', 0)}")
        print(f"✓ Processed: {stats.get('processed_count', 0)}")
        print(f"✓ Transcribed: {stats.get('transcribed_count', 0)}")
        print(f"✓ Unique feeds: {stats.get('unique_feeds', 0)}")
        
        results['verification'] = {
            'total_podcasts': stats.get('total_podcasts', 0),
            'processed': stats.get('processed_count', 0),
            'transcribed': stats.get('transcribed_count', 0),
            'unique_feeds': stats.get('unique_feeds', 0)
        }
        
        # Show recent podcasts
        print("\nRecent podcasts:")
        for podcast in all_podcasts[:6]:
            title = podcast.get('title', 'Untitled')[:60]
            status = podcast.get('status', 'unknown')
            has_transcript = bool(podcast.get('transcript'))
            has_summary = bool(podcast.get('summary'))
            print(f"  - {title} [{status}] {'📝' if has_transcript else ''} {'📊' if has_summary else ''}")
        
        print("\n" + "=" * 60)
        print("✅ Batch processing complete!")
        print("=" * 60)
        print("\nView podcasts in Streamlit: streamlit run pages/0_Podcasts.py")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        results['error'] = str(e)
    
    finally:
        duckdb.close()
        postgres.close()
        
        # Save results
        output_dir = Path("test-results")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"batch_postgres_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    import sys
    skip_download = "--skip-download" in sys.argv or "-s" in sys.argv
    migrate_existing = "--migrate" in sys.argv or "-m" in sys.argv
    run_batch_postgres(skip_download=skip_download, migrate_existing=migrate_existing)

