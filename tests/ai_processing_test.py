"""
Test AI processing (transcription and summarization) with real data.
Tests transcriber and processor with actual episodes from config/feeds.yaml
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import P3Database
from utils.config import get_api_key
from utils.transcriber_xai import AudioTranscriber
from utils.cleaner_xai import TranscriptCleaner
from utils.download import load_feeds_config
from utils.audio import check_ffmpeg_installed
from utils.downloader import PodcastDownloader


def test_ai_processing():
    """Test AI processing with real data"""
    results = {
        "test_name": "ai_processing_test",
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }
    
    test_db_path = "data/test_ai_processing.duckdb"
    
    try:
        db = P3Database(db_path=test_db_path)
        
        # Test 1: Check ffmpeg installation
        test_result = {
            "name": "ffmpeg_check",
            "status": "pending",
            "message": ""
        }
        
        try:
            is_installed, version_info = check_ffmpeg_installed()
            if is_installed:
                test_result["status"] = "passed"
                test_result["message"] = "ffmpeg is installed"
                test_result["version_info"] = version_info[:50] if version_info else None
            else:
                test_result["status"] = "failed"
                test_result["message"] = "ffmpeg is not installed or not in PATH"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to check ffmpeg: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 2: Check API key
        test_result = {
            "name": "api_key_check",
            "status": "pending",
            "message": ""
        }
        
        try:
            api_key = get_api_key()
            test_result["status"] = "passed"
            test_result["message"] = "API key found"
        except ValueError as e:
            test_result["status"] = "skipped"
            test_result["message"] = f"API key not found: {str(e)}"
            api_key = None
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to get API key: {str(e)}"
            api_key = None
        
        results["tests"].append(test_result)
        
        if not api_key:
            results["error"] = "Cannot proceed without API key"
            db.close()
            return results
        
        # Test 3: Load feeds and get actual feed
        test_result = {
            "name": "load_actual_feeds",
            "status": "pending",
            "message": ""
        }
        
        try:
            config = load_feeds_config()
            feeds = config.get('feeds', [])
            
            if not feeds:
                test_result["status"] = "skipped"
                test_result["message"] = "No feeds configured in config/feeds.yaml"
            else:
                test_result["status"] = "passed"
                test_result["message"] = f"Loaded {len(feeds)} feeds from config"
                test_result["feed_count"] = len(feeds)
                test_result["first_feed"] = feeds[0].get('name')
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to load feeds: {str(e)}"
            feeds = []
        
        results["tests"].append(test_result)
        
        if not feeds:
            results["error"] = "Cannot proceed without feeds"
            db.close()
            return results
        
        # Test 4: Download a test episode (if possible)
        test_result = {
            "name": "download_test_episode",
            "status": "pending",
            "message": ""
        }
        
        episode_id = None
        try:
            downloader = PodcastDownloader(db, data_dir="data/test_audio", max_episodes=1)
            first_feed = feeds[0]
            
            # Add feed to database
            podcast_id = downloader.add_feed(
                first_feed['name'],
                first_feed['url'],
                first_feed.get('category', 'general')
            )
            
            # Try to download one episode
            count = downloader.process_feed(first_feed['url'])
            
            if count > 0:
                # Get the downloaded episode
                episodes = db.get_episodes_by_status('downloaded')
                if episodes:
                    episode_id = episodes[0]['id']
                    test_result["status"] = "passed"
                    test_result["message"] = f"Downloaded {count} episode(s) for testing"
                    test_result["episode_id"] = episode_id
                    test_result["episode_title"] = episodes[0]['title']
                else:
                    test_result["status"] = "skipped"
                    test_result["message"] = "No episodes downloaded"
            else:
                test_result["status"] = "skipped"
                test_result["message"] = "No new episodes to download (may already exist)"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to download episode: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 5: Test transcriber initialization and basic functionality
        test_result = {
            "name": "transcriber_functionality",
            "status": "pending",
            "message": ""
        }
        
        try:
            transcriber = AudioTranscriber(db, api_key=api_key)
            test_result["status"] = "passed"
            test_result["message"] = "Transcriber initialized successfully"
            
            # If we have an episode, try to transcribe it
            if episode_id:
                try:
                    success = transcriber.transcribe_episode(episode_id)
                    if success:
                        test_result["message"] += " - Successfully transcribed test episode"
                        test_result["transcription_success"] = True
                    else:
                        test_result["message"] += " - Transcription attempted but failed"
                        test_result["transcription_success"] = False
                except Exception as e:
                    test_result["message"] += f" - Transcription error: {str(e)[:50]}"
                    test_result["transcription_error"] = str(e)[:100]
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to initialize transcriber: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 6: Test processor/cleaner initialization and basic functionality
        test_result = {
            "name": "processor_functionality",
            "status": "pending",
            "message": ""
        }
        
        try:
            cleaner = TranscriptCleaner(db, api_key=api_key)
            test_result["status"] = "passed"
            test_result["message"] = "Processor initialized successfully"
            
            # Check if we have transcribed episodes
            transcribed = db.get_episodes_by_status('transcribed')
            if transcribed:
                episode_id_to_summarize = transcribed[0]['id']
                try:
                    summary = cleaner.generate_summary(episode_id_to_summarize)
                    if summary:
                        test_result["message"] += " - Successfully generated summary"
                        test_result["summary_success"] = True
                        test_result["summary_keys"] = list(summary.keys())
                    else:
                        test_result["message"] += " - Summary generation attempted but returned None"
                        test_result["summary_success"] = False
                except Exception as e:
                    test_result["message"] += f" - Summary error: {str(e)[:50]}"
                    test_result["summary_error"] = str(e)[:100]
            else:
                test_result["message"] += " - No transcribed episodes available for summarization"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to initialize processor: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Cleanup
        db.close()
        
        # Calculate summary
        total_tests = len(results["tests"])
        passed_tests = sum(1 for t in results["tests"] if t["status"] == "passed")
        failed_tests = sum(1 for t in results["tests"] if t["status"] == "failed")
        skipped_tests = sum(1 for t in results["tests"] if t["status"] == "skipped")
        
        results["summary"] = {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
        }
        
    except Exception as e:
        results["error"] = str(e)
    
    # Save results
    output_dir = Path("test-results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"ai_processing_test_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"AI processing test results saved to {output_file}")
    print(f"Summary: {results.get('summary', {})}")
    
    return results


if __name__ == "__main__":
    test_ai_processing()

