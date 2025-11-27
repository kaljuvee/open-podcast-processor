"""
Test database module functionality
"""

import json
import os
from pathlib import Path
from datetime import datetime
from p3.database import P3Database


def test_database():
    """Test database initialization and basic operations"""
    results = {
        "test_name": "database_test",
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }
    
    # Use test database
    test_db_path = "data/test_p3.duckdb"
    
    try:
        # Test 1: Database initialization
        test_result = {
            "name": "database_initialization",
            "status": "pending",
            "message": ""
        }
        
        try:
            db = P3Database(db_path=test_db_path)
            test_result["status"] = "passed"
            test_result["message"] = "Database initialized successfully"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to initialize database: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 2: Add podcast
        test_result = {
            "name": "add_podcast",
            "status": "pending",
            "message": ""
        }
        
        try:
            podcast_id = db.add_podcast(
                title="Test Podcast",
                rss_url="https://example.com/feed.xml",
                category="tech"
            )
            test_result["status"] = "passed"
            test_result["message"] = f"Podcast added with ID: {podcast_id}"
            test_result["podcast_id"] = podcast_id
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to add podcast: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 3: Get podcast by URL
        test_result = {
            "name": "get_podcast_by_url",
            "status": "pending",
            "message": ""
        }
        
        try:
            podcast = db.get_podcast_by_url("https://example.com/feed.xml")
            if podcast and podcast['title'] == "Test Podcast":
                test_result["status"] = "passed"
                test_result["message"] = "Podcast retrieved successfully"
                test_result["podcast_data"] = podcast
            else:
                test_result["status"] = "failed"
                test_result["message"] = "Podcast not found or data mismatch"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to get podcast: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 4: Add episode
        test_result = {
            "name": "add_episode",
            "status": "pending",
            "message": ""
        }
        
        try:
            episode_id = db.add_episode(
                podcast_id=1,
                title="Test Episode",
                date=datetime.now(),
                url="https://example.com/episode1.mp3",
                file_path="/tmp/test.mp3"
            )
            test_result["status"] = "passed"
            test_result["message"] = f"Episode added with ID: {episode_id}"
            test_result["episode_id"] = episode_id
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to add episode: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 5: Check episode exists
        test_result = {
            "name": "episode_exists",
            "status": "pending",
            "message": ""
        }
        
        try:
            exists = db.episode_exists("https://example.com/episode1.mp3")
            if exists:
                test_result["status"] = "passed"
                test_result["message"] = "Episode existence check works"
            else:
                test_result["status"] = "failed"
                test_result["message"] = "Episode should exist but doesn't"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to check episode: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 6: Update episode status
        test_result = {
            "name": "update_episode_status",
            "status": "pending",
            "message": ""
        }
        
        try:
            db.update_episode_status(1, 'transcribed')
            episodes = db.get_episodes_by_status('transcribed')
            if len(episodes) > 0:
                test_result["status"] = "passed"
                test_result["message"] = "Episode status updated successfully"
            else:
                test_result["status"] = "failed"
                test_result["message"] = "Status update failed"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to update status: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Cleanup
        db.close()
        
        # Calculate summary
        total_tests = len(results["tests"])
        passed_tests = sum(1 for t in results["tests"] if t["status"] == "passed")
        failed_tests = sum(1 for t in results["tests"] if t["status"] == "failed")
        
        results["summary"] = {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
        }
        
    except Exception as e:
        results["error"] = str(e)
    
    # Save results
    output_dir = Path("test-results")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "database_test.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Database test results saved to {output_file}")
    print(f"Summary: {results.get('summary', {})}")
    
    return results


if __name__ == "__main__":
    test_database()
