"""
Test utils module functionality
Tests for processing and download utilities extracted from Streamlit pages
"""

import json
from pathlib import Path
from datetime import datetime
from utils.database import P3Database
from utils.processing import process_all_episodes, transcribe_episode, summarize_episode
from utils.download import load_feeds_config, download_feeds
from utils.config import get_api_key


def test_utils():
    """Test utils module functionality"""
    results = {
        "test_name": "utils_test",
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }
    
    # Use test database
    test_db_path = "data/test_utils.duckdb"
    
    try:
        db = P3Database(db_path=test_db_path)
        
        # Test 1: Load feeds config utility
        test_result = {
            "name": "load_feeds_config",
            "status": "pending",
            "message": ""
        }
        
        try:
            config = load_feeds_config()
            
            if config and 'feeds' in config and 'settings' in config:
                test_result["status"] = "passed"
                test_result["message"] = f"Successfully loaded config with {len(config.get('feeds', []))} feeds"
                test_result["feed_count"] = len(config.get('feeds', []))
                test_result["has_settings"] = 'settings' in config
            else:
                test_result["status"] = "failed"
                test_result["message"] = "Config loaded but missing expected keys"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to load config: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 2: Get API key from config
        test_result = {
            "name": "get_api_key_from_config",
            "status": "pending",
            "message": ""
        }
        
        try:
            api_key = get_api_key()
            if api_key:
                test_result["status"] = "passed"
                test_result["message"] = "API key retrieved successfully via config module"
                test_result["key_prefix"] = api_key[:10] + "..." if len(api_key) > 10 else "***"
            else:
                test_result["status"] = "failed"
                test_result["message"] = "API key is empty"
        except ValueError as e:
            test_result["status"] = "skipped"
            test_result["message"] = f"API key not configured: {str(e)}"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to get API key: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 3: Process all episodes (empty state)
        test_result = {
            "name": "process_all_episodes_empty",
            "status": "pending",
            "message": ""
        }
        
        try:
            # Process with empty database
            results_dict = process_all_episodes(db)
            
            if isinstance(results_dict, dict) and 'transcribed' in results_dict:
                test_result["status"] = "passed"
                test_result["message"] = "process_all_episodes works with empty database"
                test_result["results"] = results_dict
            else:
                test_result["status"] = "failed"
                test_result["message"] = "process_all_episodes returned unexpected format"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to process episodes: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 4: Transcribe episode (with invalid ID)
        test_result = {
            "name": "transcribe_episode_invalid_id",
            "status": "pending",
            "message": ""
        }
        
        try:
            # Try with non-existent episode ID
            success, error = transcribe_episode(99999, db)
            
            if not success and error:
                test_result["status"] = "passed"
                test_result["message"] = "transcribe_episode correctly handles invalid episode ID"
                test_result["error_message"] = error[:50] if error else None
            else:
                test_result["status"] = "warning"
                test_result["message"] = "transcribe_episode did not return expected error for invalid ID"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to test transcribe_episode: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 5: Summarize episode (with invalid ID)
        test_result = {
            "name": "summarize_episode_invalid_id",
            "status": "pending",
            "message": ""
        }
        
        try:
            # Try with non-existent episode ID
            success, error, summary = summarize_episode(99999, db)
            
            if not success:
                test_result["status"] = "passed"
                test_result["message"] = "summarize_episode correctly handles invalid episode ID"
                test_result["error_message"] = error[:50] if error else None
            else:
                test_result["status"] = "warning"
                test_result["message"] = "summarize_episode did not return expected error for invalid ID"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to test summarize_episode: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 6: Download feeds utility (with empty feed list)
        test_result = {
            "name": "download_feeds_empty_list",
            "status": "pending",
            "message": ""
        }
        
        try:
            results_dict = download_feeds(
                feed_configs=[],
                max_episodes=5,
                db=db,
                data_dir="data/test"
            )
            
            if isinstance(results_dict, dict) and 'total_downloaded' in results_dict:
                test_result["status"] = "passed"
                test_result["message"] = "download_feeds works with empty feed list"
                test_result["results"] = results_dict
            else:
                test_result["status"] = "failed"
                test_result["message"] = "download_feeds returned unexpected format"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to test download_feeds: {str(e)}"
        
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
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"utils_test_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Utils test results saved to {output_file}")
    print(f"Summary: {results.get('summary', {})}")
    
    return results


if __name__ == "__main__":
    test_utils()

