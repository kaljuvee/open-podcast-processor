"""
Test Groq Whisper Large V3 Turbo speech-to-text transcription.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import P3Database
from utils.config import get_groq_api_key
from utils.transcriber_groq import AudioTranscriber


def test_stt():
    """Test Groq Whisper Large V3 Turbo transcription."""
    print("=" * 60)
    print("Groq Whisper Large V3 Turbo - Speech-to-Text Test")
    print("=" * 60)
    print()
    
    results = {
        'test_name': 'stt_test',
        'timestamp': datetime.now().isoformat(),
        'tests': []
    }
    
    # Test 1: Check API key
    test_result = {
        'name': 'api_key_check',
        'status': 'pending',
        'message': ''
    }
    
    try:
        api_key = get_groq_api_key()
        if api_key:
            test_result['status'] = 'passed'
            test_result['message'] = 'Groq API key loaded successfully'
        else:
            test_result['status'] = 'failed'
            test_result['message'] = 'Groq API key not found'
    except Exception as e:
        test_result['status'] = 'failed'
        test_result['message'] = f'Failed to load API key: {str(e)}'
    
    results['tests'].append(test_result)
    
    # Test 2: Initialize transcriber
    test_result = {
        'name': 'transcriber_initialization',
        'status': 'pending',
        'message': ''
    }
    
    try:
        db = P3Database(db_path="db/test_stt.duckdb")
        transcriber = AudioTranscriber(db)
        test_result['status'] = 'passed'
        test_result['message'] = 'Transcriber initialized successfully'
        test_result['model'] = transcriber.model
        db.close()
    except Exception as e:
        test_result['status'] = 'failed'
        test_result['message'] = f'Failed to initialize transcriber: {str(e)}'
    
    results['tests'].append(test_result)
    
    # Test 3: Test with actual audio file (if available)
    test_result = {
        'name': 'transcription_test',
        'status': 'pending',
        'message': ''
    }
    
    try:
        db = P3Database(db_path="db/test_stt.duckdb")
        transcriber = AudioTranscriber(db)
        
        # Look for downloaded episodes
        episodes = db.get_episodes_by_status('downloaded')
        
        if episodes:
            test_episode = episodes[0]
            audio_path = Path(test_episode.get('file_path', ''))
            
            if audio_path.exists():
                print(f"Testing transcription with: {test_episode['title']}")
                print(f"Audio file: {audio_path} ({audio_path.stat().st_size / (1024*1024):.1f}MB)")
                
                result = transcriber.transcribe_audio(str(audio_path))
                
                if result:
                    test_result['status'] = 'passed'
                    test_result['message'] = f'Successfully transcribed audio file'
                    test_result['segments_count'] = len(result.get('segments', []))
                    test_result['text_length'] = len(result.get('text', ''))
                    test_result['language'] = result.get('language', 'unknown')
                    test_result['chunked'] = result.get('chunked', False)
                    print(f"✓ Transcription successful: {test_result['segments_count']} segments, {test_result['text_length']} chars")
                else:
                    test_result['status'] = 'failed'
                    test_result['message'] = 'Transcription returned None'
            else:
                test_result['status'] = 'skipped'
                test_result['message'] = f'Audio file not found: {audio_path}'
        else:
            test_result['status'] = 'skipped'
            test_result['message'] = 'No downloaded episodes available for testing'
        
        db.close()
    except Exception as e:
        test_result['status'] = 'failed'
        test_result['message'] = f'Transcription test failed: {str(e)}'
        import traceback
        test_result['error'] = traceback.format_exc()
    
    results['tests'].append(test_result)
    
    # Calculate summary
    total_tests = len(results['tests'])
    passed_tests = sum(1 for t in results['tests'] if t['status'] == 'passed')
    failed_tests = sum(1 for t in results['tests'] if t['status'] == 'failed')
    skipped_tests = sum(1 for t in results['tests'] if t['status'] == 'skipped')
    
    results['summary'] = {
        'total': total_tests,
        'passed': passed_tests,
        'failed': failed_tests,
        'skipped': skipped_tests,
        'success_rate': f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
    }
    
    # Save results
    output_dir = Path("test-results")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"stt_test_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Total: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Skipped: {skipped_tests}")
    print(f"Success Rate: {results['summary']['success_rate']}")
    print(f"\nResults saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    test_stt()

