"""
Test XAI API integration for transcription and summarization
"""

import json
import os
from pathlib import Path
from datetime import datetime
from p3.database import P3Database


def test_xai_integration():
    """Test XAI API integration"""
    results = {
        "test_name": "xai_integration_test",
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }
    
    # Test 1: Check XAI API key
    test_result = {
        "name": "xai_api_key_check",
        "status": "pending",
        "message": ""
    }
    
    api_key = os.getenv("XAI_API_KEY")
    if api_key:
        test_result["status"] = "passed"
        test_result["message"] = "XAI_API_KEY found in environment"
        test_result["key_prefix"] = api_key[:10] + "..." if len(api_key) > 10 else "***"
    else:
        test_result["status"] = "failed"
        test_result["message"] = "XAI_API_KEY not found in environment"
    
    results["tests"].append(test_result)
    
    # Test 2: Initialize transcriber
    test_result = {
        "name": "transcriber_initialization",
        "status": "pending",
        "message": ""
    }
    
    try:
        from p3.transcriber_xai import AudioTranscriber
        
        test_db_path = "data/test_p3.duckdb"
        db = P3Database(db_path=test_db_path)
        
        if api_key:
            transcriber = AudioTranscriber(db, api_key=api_key)
            test_result["status"] = "passed"
            test_result["message"] = "XAI transcriber initialized successfully"
        else:
            test_result["status"] = "skipped"
            test_result["message"] = "Skipped due to missing API key"
        
        db.close()
    except Exception as e:
        test_result["status"] = "failed"
        test_result["message"] = f"Failed to initialize transcriber: {str(e)}"
    
    results["tests"].append(test_result)
    
    # Test 3: Initialize cleaner
    test_result = {
        "name": "cleaner_initialization",
        "status": "pending",
        "message": ""
    }
    
    try:
        from p3.cleaner_xai import TranscriptCleaner
        
        test_db_path = "data/test_p3.duckdb"
        db = P3Database(db_path=test_db_path)
        
        if api_key:
            cleaner = TranscriptCleaner(db, api_key=api_key)
            test_result["status"] = "passed"
            test_result["message"] = "XAI cleaner initialized successfully"
        else:
            test_result["status"] = "skipped"
            test_result["message"] = "Skipped due to missing API key"
        
        db.close()
    except Exception as e:
        test_result["status"] = "failed"
        test_result["message"] = f"Failed to initialize cleaner: {str(e)}"
    
    results["tests"].append(test_result)
    
    # Test 4: Test OpenAI client configuration
    test_result = {
        "name": "openai_client_configuration",
        "status": "pending",
        "message": ""
    }
    
    try:
        from openai import OpenAI
        
        if api_key:
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1"
            )
            test_result["status"] = "passed"
            test_result["message"] = "OpenAI client configured with XAI base URL"
            test_result["base_url"] = "https://api.x.ai/v1"
        else:
            test_result["status"] = "skipped"
            test_result["message"] = "Skipped due to missing API key"
    except Exception as e:
        test_result["status"] = "failed"
        test_result["message"] = f"Failed to configure OpenAI client: {str(e)}"
    
    results["tests"].append(test_result)
    
    # Test 5: Test basic extraction fallback
    test_result = {
        "name": "basic_extraction_fallback",
        "status": "pending",
        "message": ""
    }
    
    try:
        from p3.cleaner_xai import TranscriptCleaner
        
        test_db_path = "data/test_p3.duckdb"
        db = P3Database(db_path=test_db_path)
        
        if api_key:
            cleaner = TranscriptCleaner(db, api_key=api_key)
            
            # Test basic extraction
            test_text = "This is a test transcript about artificial intelligence and machine learning technologies from OpenAI and Google."
            extraction = cleaner._basic_extraction(test_text)
            
            if extraction and 'key_topics' in extraction:
                test_result["status"] = "passed"
                test_result["message"] = "Basic extraction fallback works"
                test_result["extracted_topics"] = extraction['key_topics'][:3]
            else:
                test_result["status"] = "failed"
                test_result["message"] = "Basic extraction failed"
        else:
            test_result["status"] = "skipped"
            test_result["message"] = "Skipped due to missing API key"
        
        db.close()
    except Exception as e:
        test_result["status"] = "failed"
        test_result["message"] = f"Failed basic extraction: {str(e)}"
    
    results["tests"].append(test_result)
    
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
    
    # Save results
    output_dir = Path("test-results")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "xai_integration_test.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"XAI integration test results saved to {output_file}")
    print(f"Summary: {results.get('summary', {})}")
    
    return results


if __name__ == "__main__":
    test_xai_integration()
