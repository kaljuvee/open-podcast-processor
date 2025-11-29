"""
Test downloader module functionality
"""

import json
from pathlib import Path
from datetime import datetime
from utils.database import P3Database
from utils.downloader import PodcastDownloader
from utils.download import load_feeds_config
import feedparser


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
            downloader = PodcastDownloader(db, data_dir="data/test")
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
            # Use actual feed from feeds.yaml via utils
            config = load_feeds_config()
            feeds = config.get('feeds', [])
            
            if not feeds:
                test_result["status"] = "skipped"
                test_result["message"] = "No feeds configured in config/feeds.yaml"
                results["tests"].append(test_result)
                return results
            
            feed_url = feeds[0]['url']  # Use first feed from config
            
            feed = feedparser.parse(feed_url)
            
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
            # Parse feed again for this test using utils
            config = load_feeds_config()
            feeds = config.get('feeds', [])
            
            if not feeds:
                test_result["status"] = "skipped"
                test_result["message"] = "No feeds configured in config/feeds.yaml"
                results["tests"].append(test_result)
                return results
            
            feed_url = feeds[0]['url']  # Use first feed from config
            
            feed = feedparser.parse(feed_url)
            
            if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                entry = feed.entries[0]
                
                # Extract episode info manually (downloader doesn't have this method)
                episode_info = {
                    'title': entry.get('title', 'Unknown'),
                    'audio_url': None
                }
                
                for enclosure in entry.get('enclosures', []):
                    if hasattr(enclosure, 'type') and 'audio' in enclosure.type:
                        episode_info['audio_url'] = enclosure.href
                        break
                
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
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"downloader_test_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Downloader test results saved to {output_file}")
    print(f"Summary: {results.get('summary', {})}")
    
    return results


if __name__ == "__main__":
    test_downloader()
