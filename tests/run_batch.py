"""
Batch download and processing test script for demo.
Downloads 1 episode from each feed and transcribes them.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import P3Database
from utils.batch_download import batch_download_one_per_feed
from utils.batch_process import batch_transcribe_downloaded, batch_summarize_transcribed, batch_process_all


def run_batch_demo(skip_download=False, process_all_downloaded=False):
    """
    Run batch download, MP3 conversion, transcription, and summarization demo.
    
    Args:
        skip_download: If True, skip download step and process existing downloaded episodes
        process_all_downloaded: If True, process ALL downloaded episodes (not just from batch download)
    """
    print("=" * 60)
    print("Open Podcast Processor - Batch Pipeline Demo")
    print("=" * 60)
    print()
    print("Using Groq Whisper Large V3 Turbo for transcription")
    print("Using Groq models via LangChain for summarization")
    print()
    
    # Use demo database
    demo_db_path = "db/demo.duckdb"
    db = P3Database(db_path=demo_db_path)
    
    results = {
        'test_name': 'batch_demo',
        'timestamp': datetime.now().isoformat(),
        'database_path': demo_db_path
    }
    
    try:
        if not skip_download:
            print("Step 1: Batch Download (1 episode per feed, converting to MP3)")
            print("-" * 60)
            download_results = batch_download_one_per_feed(
                db=db, 
                data_dir="data/demo",
                audio_format="mp3"  # Convert to MP3
            )
            results['download'] = download_results
            episode_ids = [ep['id'] for ep in download_results.get('episodes', [])]
        else:
            print("Step 1: Skipping download, processing existing episodes")
            print("-" * 60)
            # Get already downloaded episodes
            downloaded_episodes = db.get_episodes_by_status('downloaded')
            episode_ids = [ep['id'] for ep in downloaded_episodes]
            results['download'] = {
                'total_downloaded': len(episode_ids),
                'message': 'Using existing downloaded episodes',
                'episodes': downloaded_episodes
            }
            print(f"Found {len(episode_ids)} downloaded episode(s) to process")
        
        # If process_all_downloaded is True, get ALL downloaded episodes regardless of batch
        if process_all_downloaded:
            print("\n⚠️  Processing ALL downloaded episodes (not just batch download)")
            all_downloaded = db.get_episodes_by_status('downloaded')
            episode_ids = [ep['id'] for ep in all_downloaded]
            print(f"Total episodes to process: {len(episode_ids)}")
        
        print()
        print("Step 2: Batch Transcription")
        print("-" * 60)
        
        if episode_ids:
            transcription_results = batch_transcribe_downloaded(
                db=db,
                episode_ids=episode_ids
            )
            results['transcription'] = transcription_results
            
            print()
            print("Step 3: Batch Summarization")
            print("-" * 60)
            
            # Get successfully transcribed episode IDs
            transcribed_episode_ids = [
                r['episode_id'] for r in transcription_results.get('episode_results', [])
                if r.get('status') == 'transcribed'
            ]
            
            if transcribed_episode_ids:
                summarization_results = batch_summarize_transcribed(
                    db=db,
                    episode_ids=transcribed_episode_ids
                )
                results['summarization'] = summarization_results
            else:
                print("⚠️  No episodes transcribed, skipping summarization")
                results['summarization'] = {
                    'message': 'No episodes to summarize',
                    'total_summarized': 0,
                    'total_failed': 0
                }
        else:
            print("⚠️  No episodes downloaded, skipping transcription and summarization")
            results['transcription'] = {
                'message': 'No episodes to transcribe',
                'total_transcribed': 0,
                'total_failed': 0
            }
            results['summarization'] = {
                'message': 'No episodes to summarize',
                'total_summarized': 0,
                'total_failed': 0
            }
        
        print()
        print("=" * 60)
        print("Demo Summary")
        print("=" * 60)
        print(f"Downloaded/Found: {results['download'].get('total_downloaded', 0)} episode(s)")
        print(f"Transcribed: {results['transcription'].get('total_transcribed', 0)} episode(s)")
        print(f"Summarized: {results['summarization'].get('total_summarized', 0)} episode(s)")
        print(f"Failed: {results['transcription'].get('total_failed', 0) + results['summarization'].get('total_failed', 0)} episode(s)")
        
        # Show pipeline status
        print()
        print("=" * 60)
        print("Pipeline Status")
        print("=" * 60)
        downloaded_count = len(db.get_episodes_by_status('downloaded'))
        transcribed_count = len(db.get_episodes_by_status('transcribed'))
        processed_count = len(db.get_episodes_by_status('processed'))
        
        print(f"📥 Downloaded: {downloaded_count}")
        print(f"🎙️  Transcribed: {transcribed_count}")
        print(f"✅ Processed (with summaries): {processed_count}")
        
        # Save results
        output_dir = Path("test-results")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"batch_demo_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        results['error'] = str(e)
        return results
        
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    # Check if --skip-download flag is passed
    skip_download = "--skip-download" in sys.argv or "-s" in sys.argv
    # Check if --all flag is passed to process all downloaded episodes
    process_all = "--all" in sys.argv or "-a" in sys.argv
    run_batch_demo(skip_download=skip_download, process_all_downloaded=process_all)

