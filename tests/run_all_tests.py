"""
Run all tests and generate consolidated report
"""

import json
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_database import test_database
from tests.test_downloader import test_downloader
from tests.test_xai_integration import test_xai_integration


def run_all_tests():
    """Run all test suites and generate consolidated report"""
    print("=" * 60)
    print("Running Open Podcast Processor Test Suite")
    print("=" * 60)
    print()
    
    all_results = {
        "test_suite": "open_podcast_processor",
        "timestamp": datetime.now().isoformat(),
        "test_modules": []
    }
    
    # Run database tests
    print("Running database tests...")
    try:
        db_results = test_database()
        all_results["test_modules"].append(db_results)
        print(f"✓ Database tests completed")
    except Exception as e:
        print(f"✗ Database tests failed: {e}")
        all_results["test_modules"].append({
            "test_name": "database_test",
            "error": str(e)
        })
    
    print()
    
    # Run downloader tests
    print("Running downloader tests...")
    try:
        downloader_results = test_downloader()
        all_results["test_modules"].append(downloader_results)
        print(f"✓ Downloader tests completed")
    except Exception as e:
        print(f"✗ Downloader tests failed: {e}")
        all_results["test_modules"].append({
            "test_name": "downloader_test",
            "error": str(e)
        })
    
    print()
    
    # Run XAI integration tests
    print("Running XAI integration tests...")
    try:
        xai_results = test_xai_integration()
        all_results["test_modules"].append(xai_results)
        print(f"✓ XAI integration tests completed")
    except Exception as e:
        print(f"✗ XAI integration tests failed: {e}")
        all_results["test_modules"].append({
            "test_name": "xai_integration_test",
            "error": str(e)
        })
    
    print()
    print("=" * 60)
    
    # Calculate overall summary
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    
    for module in all_results["test_modules"]:
        if "summary" in module:
            summary = module["summary"]
            total_tests += summary.get("total", 0)
            total_passed += summary.get("passed", 0)
            total_failed += summary.get("failed", 0)
            total_skipped += summary.get("skipped", 0)
    
    all_results["overall_summary"] = {
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_skipped": total_skipped,
        "overall_success_rate": f"{(total_passed/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
    }
    
    # Print summary
    print("Overall Test Summary:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print(f"  Skipped: {total_skipped}")
    print(f"  Success Rate: {all_results['overall_summary']['overall_success_rate']}")
    print("=" * 60)
    
    # Save consolidated report
    output_dir = Path("test-results")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "all_tests_report.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\nConsolidated test report saved to {output_file}")
    
    return all_results


if __name__ == "__main__":
    run_all_tests()
