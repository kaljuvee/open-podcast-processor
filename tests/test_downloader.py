"""
Test downloader module functionality
"""

import json
from pathlib import Path
from datetime import datetime
from p3.database import P3Database
from p3.downloader import PodcastDownloader


def test_downloader():
    """Test podcast downloader functionality"""
    results = {
        "test_name": "downloader_test",
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }
    
    # Use test database
    test_db_path = "data/test_p3.duckdb"
    
    try:
        db = P3Database(db_path=test_db_path)
        
        # Test 1: Initialize downloader
        test_result = {
            "name": "downloader_initialization",
            "status": "pending",
            "message": ""
        }
        
        try:
            downloader = PodcastDownloader(db, download_dir="data/test_audio")
            test_result["status"] = "passed"
            test_result["message"] = "Downloader initialized successfully"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to initialize downloader: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 2: Parse RSS feed
        test_result = {
            "name": "parse_rss_feed",
            "status": "pending",
            "message": ""
        }
        
        try:
            # Use a real test RSS feed
            feed_url = "https://feeds.simplecast.com/54nAGcIl"  # The Changelog podcast
            feed = downloader.parse_feed(feed_url)
            
            if feed and hasattr(feed, 'entries'):
                test_result["status"] = "passed"
                test_result["message"] = f"RSS feed parsed successfully, found {len(feed.entries)} entries"
                test_result["entry_count"] = len(feed.entries)
            else:
                test_result["status"] = "failed"
                test_result["message"] = "Failed to parse RSS feed"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to parse feed: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 3: Extract episode info
        test_result = {
            "name": "extract_episode_info",
            "status": "pending",
            "message": ""
        }
        
        try:
            if feed and len(feed.entries) > 0:
                entry = feed.entries[0]
                episode_info = downloader.extract_episode_info(entry)
                
                if episode_info and 'title' in episode_info:
                    test_result["status"] = "passed"
                    test_result["message"] = f"Episode info extracted: {episode_info['title']}"
                    test_result["episode_info"] = {
                        "title": episode_info.get('title'),
                        "has_audio_url": bool(episode_info.get('audio_url'))
                    }
                else:
                    test_result["status"] = "failed"
                    test_result["message"] = "Failed to extract episode info"
            else:
                test_result["status"] = "skipped"
                test_result["message"] = "No feed entries available"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to extract episode info: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 4: Download directory creation
        test_result = {
            "name": "download_directory_creation",
            "status": "pending",
            "message": ""
        }
        
        try:
            download_dir = Path("data/test_audio")
            if download_dir.exists():
                test_result["status"] = "passed"
                test_result["message"] = f"Download directory exists: {download_dir}"
            else:
                download_dir.mkdir(parents=True, exist_ok=True)
                test_result["status"] = "passed"
                test_result["message"] = f"Download directory created: {download_dir}"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to create download directory: {str(e)}"
        
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
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
        }
        
    except Exception as e:
        results["error"] = str(e)
    
    # Save results
    output_dir = Path("test-results")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "downloader_test.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Downloader test results saved to {output_file}")
    print(f"Summary: {results.get('summary', {})}")
    
    return results


if __name__ == "__main__":
    test_downloader()
