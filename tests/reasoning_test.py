"""
Test Groq reasoning models via LangChain.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import get_groq_api_key, get_groq_model
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


def test_reasoning():
    """Test Groq reasoning models with LangChain."""
    print("=" * 60)
    print("Groq Reasoning Models Test")
    print("=" * 60)
    print()
    
    results = {
        'test_name': 'reasoning_test',
        'timestamp': datetime.now().isoformat(),
        'tests': []
    }
    
    # Test 1: Check API key and model config
    test_result = {
        'name': 'config_check',
        'status': 'pending',
        'message': ''
    }
    
    try:
        api_key = get_groq_api_key()
        model = get_groq_model()
        
        test_result['status'] = 'passed'
        test_result['message'] = 'Configuration loaded successfully'
        test_result['model'] = model
        test_result['api_key_length'] = len(api_key) if api_key else 0
        print(f"✓ Using model: {model}")
    except Exception as e:
        test_result['status'] = 'failed'
        test_result['message'] = f'Failed to load configuration: {str(e)}'
    
    results['tests'].append(test_result)
    
    # Test 2: Initialize LangChain ChatGroq
    test_result = {
        'name': 'langchain_initialization',
        'status': 'pending',
        'message': ''
    }
    
    try:
        api_key = get_groq_api_key()
        model = get_groq_model()
        
        llm = ChatGroq(
            model_name=model,
            temperature=0.7,
            groq_api_key=api_key
        )
        
        test_result['status'] = 'passed'
        test_result['message'] = 'LangChain ChatGroq initialized successfully'
        test_result['model'] = model
    except Exception as e:
        test_result['status'] = 'failed'
        test_result['message'] = f'Failed to initialize ChatGroq: {str(e)}'
        import traceback
        test_result['error'] = traceback.format_exc()
    
    results['tests'].append(test_result)
    
    # Test 3: Simple reasoning test
    test_result = {
        'name': 'simple_reasoning',
        'status': 'pending',
        'message': ''
    }
    
    try:
        api_key = get_groq_api_key()
        model = get_groq_model()
        
        llm = ChatGroq(
            model_name=model,
            temperature=0.7,
            groq_api_key=api_key
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Answer concisely."),
            ("user", "What is 2+2? Answer in one word.")
        ])
        
        chain = prompt | llm
        response = chain.invoke({})
        
        answer = response.content.strip()
        
        if "4" in answer:
            test_result['status'] = 'passed'
            test_result['message'] = 'Simple reasoning test passed'
            test_result['response'] = answer
            print(f"✓ Reasoning test: {answer}")
        else:
            test_result['status'] = 'warning'
            test_result['message'] = f'Unexpected response: {answer}'
            test_result['response'] = answer
    except Exception as e:
        test_result['status'] = 'failed'
        test_result['message'] = f'Reasoning test failed: {str(e)}'
        import traceback
        test_result['error'] = traceback.format_exc()
    
    results['tests'].append(test_result)
    
    # Test 4: JSON output parsing test (like the example)
    test_result = {
        'name': 'json_output_parsing',
        'status': 'pending',
        'message': ''
    }
    
    try:
        api_key = get_groq_api_key()
        model = get_groq_model()
        
        llm = ChatGroq(
            model_name=model,
            temperature=0.7,
            groq_api_key=api_key
        )
        
        parser = JsonOutputParser(
            pydantic_object={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "number"},
                    "features": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["name", "price", "features"]
            }
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract product details into JSON with this structure:
{{
  "name": "product name here",
  "price": number_here_without_currency_symbol,
  "features": ["feature1", "feature2", "feature3"]
}}"""),
            ("user", "{input}")
        ])
        
        chain = prompt | llm | parser
        
        description = """The Kees Van Der Westen Speedster is a high-end, single-group espresso machine priced at $6,500. 
        It features PID temperature control, E61 group head, and commercial-grade build quality."""
        
        result = chain.invoke({"input": description})
        
        if isinstance(result, dict) and 'name' in result and 'price' in result:
            test_result['status'] = 'passed'
            test_result['message'] = 'JSON output parsing test passed'
            test_result['result'] = result
            print(f"✓ JSON parsing test: {json.dumps(result, indent=2)}")
        else:
            test_result['status'] = 'failed'
            test_result['message'] = 'JSON parsing returned unexpected format'
            test_result['result'] = result
    except Exception as e:
        test_result['status'] = 'failed'
        test_result['message'] = f'JSON parsing test failed: {str(e)}'
        import traceback
        test_result['error'] = traceback.format_exc()
    
    results['tests'].append(test_result)
    
    # Test 5: Context window test (large prompt)
    test_result = {
        'name': 'context_window_test',
        'status': 'pending',
        'message': ''
    }
    
    try:
        api_key = get_groq_api_key()
        model = get_groq_model()
        
        llm = ChatGroq(
            model_name=model,
            temperature=0.3,
            groq_api_key=api_key
        )
        
        # Create a large prompt to test context window
        large_text = " ".join([f"Topic {i}: This is a test topic about technology and innovation." for i in range(100)])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarize the main themes from these topics."),
            ("user", "{input}")
        ])
        
        chain = prompt | llm
        response = chain.invoke({"input": large_text})
        
        if response.content and len(response.content) > 10:
            test_result['status'] = 'passed'
            test_result['message'] = 'Context window test passed'
            test_result['response_length'] = len(response.content)
            print(f"✓ Context window test: Generated {len(response.content)} chars")
        else:
            test_result['status'] = 'failed'
            test_result['message'] = 'Context window test returned empty response'
    except Exception as e:
        test_result['status'] = 'failed'
        test_result['message'] = f'Context window test failed: {str(e)}'
        import traceback
        test_result['error'] = traceback.format_exc()
    
    results['tests'].append(test_result)
    
    # Calculate summary
    total_tests = len(results['tests'])
    passed_tests = sum(1 for t in results['tests'] if t['status'] == 'passed')
    failed_tests = sum(1 for t in results['tests'] if t['status'] == 'failed')
    skipped_tests = sum(1 for t in results['tests'] if t['status'] == 'skipped')
    warning_tests = sum(1 for t in results['tests'] if t['status'] == 'warning')
    
    results['summary'] = {
        'total': total_tests,
        'passed': passed_tests,
        'failed': failed_tests,
        'skipped': skipped_tests,
        'warnings': warning_tests,
        'success_rate': f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
    }
    
    # Save results
    output_dir = Path("test-results")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"reasoning_test_{timestamp}.json"
    
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
    print(f"Warnings: {warning_tests}")
    print(f"Success Rate: {results['summary']['success_rate']}")
    print(f"\nResults saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    test_reasoning()

