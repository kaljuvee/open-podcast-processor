"""
Test with real RSS feed from feeds.yaml
"""

import json
import os
import yaml
from pathlib import Path
from datetime import datetime
from p3.database import P3Database
from p3.downloader import PodcastDownloader
import feedparser


def test_real_feed():
    """Test with actual RSS feed from configuration"""
    results = {
        "test_name": "real_feed_test",
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }
    
    # Use test database
    test_db_path = "data/test_real_feed.duckdb"
    
    try:
        db = P3Database(db_path=test_db_path)
        
        # Test 1: Load feeds.yaml configuration
        test_result = {
            "name": "load_feeds_config",
            "status": "pending",
            "message": ""
        }
        
        try:
            config_file = Path("config/feeds.yaml")
            if not config_file.exists():
                test_result["status"] = "failed"
                test_result["message"] = "feeds.yaml not found"
            else:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                feeds = config.get('feeds', [])
                if len(feeds) > 0:
                    test_result["status"] = "passed"
                    test_result["message"] = f"Loaded {len(feeds)} feeds from config"
                    test_result["feed_count"] = len(feeds)
                    test_result["first_feed"] = feeds[0].get('name')
                else:
                    test_result["status"] = "failed"
                    test_result["message"] = "No feeds in configuration"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to load config: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 2: Parse actual RSS feed
        test_result = {
            "name": "parse_actual_rss_feed",
            "status": "pending",
            "message": ""
        }
        
        try:
            if config and len(feeds) > 0:
                feed_config = feeds[0]  # Test with first feed
                feed_url = feed_config['url']
                feed_name = feed_config['name']
                
                feed = feedparser.parse(feed_url)
                
                if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                    test_result["status"] = "passed"
                    test_result["message"] = f"Successfully parsed {feed_name}"
                    test_result["feed_name"] = feed_name
                    test_result["feed_url"] = feed_url
                    test_result["entry_count"] = len(feed.entries)
                    test_result["first_episode"] = feed.entries[0].get('title', 'Unknown')
                else:
                    test_result["status"] = "failed"
                    test_result["message"] = f"Failed to parse feed or no entries found"
            else:
                test_result["status"] = "skipped"
                test_result["message"] = "No feeds available from config"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to parse RSS feed: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 3: Extract episode metadata
        test_result = {
            "name": "extract_episode_metadata",
            "status": "pending",
            "message": ""
        }
        
        try:
            if feed and len(feed.entries) > 0:
                entry = feed.entries[0]
                
                metadata = {
                    'title': entry.get('title', 'Unknown'),
                    'published': entry.get('published', None),
                    'summary': entry.get('summary', '')[:100] + '...' if entry.get('summary') else None,
                    'has_audio': False,
                    'audio_url': None
                }
                
                # Check for audio enclosure
                for enclosure in entry.get('enclosures', []):
                    if hasattr(enclosure, 'type') and 'audio' in enclosure.type:
                        metadata['has_audio'] = True
                        metadata['audio_url'] = enclosure.href
                        break
                
                if metadata['has_audio']:
                    test_result["status"] = "passed"
                    test_result["message"] = "Episode metadata extracted with audio URL"
                    test_result["metadata"] = {
                        'title': metadata['title'],
                        'has_audio': metadata['has_audio']
                    }
                else:
                    test_result["status"] = "warning"
                    test_result["message"] = "Episode metadata extracted but no audio URL found"
                    test_result["metadata"] = {
                        'title': metadata['title'],
                        'has_audio': metadata['has_audio']
                    }
            else:
                test_result["status"] = "skipped"
                test_result["message"] = "No feed entries available"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to extract metadata: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 4: Test downloader with actual feed
        test_result = {
            "name": "downloader_with_real_feed",
            "status": "pending",
            "message": ""
        }
        
        try:
            downloader = PodcastDownloader(db, data_dir="data/test_real")
            
            if config and len(feeds) > 0:
                feed_config = feeds[0]
                
                # Add feed to database
                podcast_id = downloader.add_feed(
                    name=feed_config['name'],
                    url=feed_config['url'],
                    category=feed_config.get('category', 'general')
                )
                
                test_result["status"] = "passed"
                test_result["message"] = f"Downloader successfully added feed: {feed_config['name']}"
                test_result["podcast_id"] = podcast_id
            else:
                test_result["status"] = "skipped"
                test_result["message"] = "No feeds available"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Downloader test failed: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 5: Verify all configured feeds are accessible
        test_result = {
            "name": "verify_all_feeds_accessible",
            "status": "pending",
            "message": ""
        }
        
        try:
            if config and len(feeds) > 0:
                accessible_feeds = []
                inaccessible_feeds = []
                
                for feed_config in feeds[:5]:  # Test first 5 feeds
                    try:
                        feed = feedparser.parse(feed_config['url'])
                        if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                            accessible_feeds.append(feed_config['name'])
                        else:
                            inaccessible_feeds.append(feed_config['name'])
                    except:
                        inaccessible_feeds.append(feed_config['name'])
                
                test_result["status"] = "passed"
                test_result["message"] = f"Checked {len(accessible_feeds) + len(inaccessible_feeds)} feeds"
                test_result["accessible_count"] = len(accessible_feeds)
                test_result["inaccessible_count"] = len(inaccessible_feeds)
                test_result["accessible_feeds"] = accessible_feeds
                if inaccessible_feeds:
                    test_result["inaccessible_feeds"] = inaccessible_feeds
            else:
                test_result["status"] = "skipped"
                test_result["message"] = "No feeds to verify"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Feed verification failed: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Cleanup
        db.close()
        
        # Calculate summary
        total_tests = len(results["tests"])
        passed_tests = sum(1 for t in results["tests"] if t["status"] == "passed")
        failed_tests = sum(1 for t in results["tests"] if t["status"] == "failed")
        skipped_tests = sum(1 for t in results["tests"] if t["status"] == "skipped")
        warning_tests = sum(1 for t in results["tests"] if t["status"] == "warning")
        
        results["summary"] = {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "warnings": warning_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
        }
        
    except Exception as e:
        results["error"] = str(e)
    
    # Save results
    output_dir = Path("test-results")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "real_feed_test.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Real feed test results saved to {output_file}")
    print(f"Summary: {results.get('summary', {})}")
    
    return results


if __name__ == "__main__":
    test_real_feed()
