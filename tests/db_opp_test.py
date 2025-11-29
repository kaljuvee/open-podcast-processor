"""
Test db/opp.duckdb database schema and operations.
Verifies that the database is created correctly and basic operations work.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import P3Database
from utils.db_util import (
    verify_schema,
    get_database_stats,
    query_podcasts,
    query_episodes,
    query_transcripts,
    query_summaries,
    test_database_operations
)
from utils.download import load_feeds_config, download_feeds


def test_db_opp():
    """Test db/opp.duckdb database"""
    results = {
        "test_name": "db_opp_test",
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }
    
    db_path = "db/opp.duckdb"
    
    try:
        # Test 1: Database initialization
        test_result = {
            "name": "database_initialization",
            "status": "pending",
            "message": ""
        }
        
        try:
            db = P3Database(db_path=db_path)
            if db.db_path.exists():
                test_result["status"] = "passed"
                test_result["message"] = f"Database initialized at {db_path}"
                test_result["db_path"] = str(db.db_path)
            else:
                test_result["status"] = "failed"
                test_result["message"] = "Database file not created"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to initialize database: {str(e)}"
            db = None
        
        results["tests"].append(test_result)
        
        if not db:
            results["error"] = "Database initialization failed"
            return results
        
        # Test 2: Schema verification
        test_result = {
            "name": "schema_verification",
            "status": "pending",
            "message": ""
        }
        
        try:
            schema_status = verify_schema(db)
            all_tables_exist = all(schema_status.values())
            
            if all_tables_exist:
                test_result["status"] = "passed"
                test_result["message"] = "All required tables exist"
                test_result["tables"] = schema_status
            else:
                test_result["status"] = "failed"
                test_result["message"] = "Some tables are missing"
                test_result["tables"] = schema_status
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Schema verification failed: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 3: Database operations test
        test_result = {
            "name": "database_operations",
            "status": "pending",
            "message": ""
        }
        
        try:
            ops_results = test_database_operations(db)
            
            if ops_results.get('create_test', {}).get('podcast_created') and \
               ops_results.get('read_test', {}).get('podcast_read'):
                test_result["status"] = "passed"
                test_result["message"] = "Database operations work correctly"
                test_result["details"] = {
                    "podcast_created": ops_results['create_test'].get('podcast_created'),
                    "episode_created": ops_results['create_test'].get('episode_created'),
                    "podcast_read": ops_results['read_test'].get('podcast_read'),
                    "episodes_read": ops_results['read_test'].get('episodes_read'),
                    "status_update_works": ops_results['read_test'].get('status_update_works')
                }
            else:
                test_result["status"] = "failed"
                test_result["message"] = "Some database operations failed"
                test_result["details"] = ops_results
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Database operations test failed: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 4: Database stats
        test_result = {
            "name": "database_stats",
            "status": "pending",
            "message": ""
        }
        
        try:
            stats = get_database_stats(db)
            test_result["status"] = "passed"
            test_result["message"] = "Database statistics retrieved"
            test_result["stats"] = stats
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to get stats: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 5: Query podcasts
        test_result = {
            "name": "query_podcasts",
            "status": "pending",
            "message": ""
        }
        
        try:
            podcasts = query_podcasts(db, limit=10)
            test_result["status"] = "passed"
            test_result["message"] = f"Queried {len(podcasts)} podcasts"
            test_result["podcast_count"] = len(podcasts)
            if podcasts:
                test_result["sample_podcast"] = {
                    "id": podcasts[0].get('id'),
                    "title": podcasts[0].get('title')
                }
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to query podcasts: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 6: Query episodes
        test_result = {
            "name": "query_episodes",
            "status": "pending",
            "message": ""
        }
        
        try:
            episodes = query_episodes(db, limit=10)
            test_result["status"] = "passed"
            test_result["message"] = f"Queried {len(episodes)} episodes"
            test_result["episode_count"] = len(episodes)
            if episodes:
                test_result["sample_episode"] = {
                    "id": episodes[0].get('id'),
                    "title": episodes[0].get('title'),
                    "status": episodes[0].get('status')
                }
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Failed to query episodes: {str(e)}"
        
        results["tests"].append(test_result)
        
        # Test 7: Test download integration (if feeds available)
        test_result = {
            "name": "download_integration_test",
            "status": "pending",
            "message": ""
        }
        
        try:
            config = load_feeds_config()
            feeds = config.get('feeds', [])
            
            if feeds and len(feeds) > 0:
                # Try downloading from first feed (dry run - just test the function)
                # We'll use a very small limit to avoid downloading too much
                test_feed = feeds[0]
                test_result["status"] = "skipped"
                test_result["message"] = f"Feed available: {test_feed.get('name')} (skipping actual download)"
                test_result["feed_name"] = test_feed.get('name')
                test_result["feed_url"] = test_feed.get('url')
            else:
                test_result["status"] = "skipped"
                test_result["message"] = "No feeds configured for download test"
        except Exception as e:
            test_result["status"] = "failed"
            test_result["message"] = f"Download integration test failed: {str(e)}"
        
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
    output_file = output_dir / f"db_opp_test_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"DB OPP test results saved to {output_file}")
    print(f"Summary: {results.get('summary', {})}")
    
    return results


if __name__ == "__main__":
    test_db_opp()

