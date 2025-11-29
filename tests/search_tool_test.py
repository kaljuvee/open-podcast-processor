#!/usr/bin/env python3
"""
Test Tavily search + Groq LLM utility for finding podcast RSS feeds.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.search_langraph_util import search_podcast_rss_feed, get_tavily_api_key


def test_tavily_api_key():
    """Test 1: Check if Tavily API key is configured."""
    print("\n" + "="*70)
    print("TEST 1: Tavily API Key Configuration")
    print("="*70)
    
    try:
        api_key = get_tavily_api_key()
        if api_key:
            print(f"✅ Tavily API key loaded successfully")
            print(f"   Key: {api_key[:10]}...{api_key[-4:]}")
            return True
        else:
            print("❌ Tavily API key is empty")
            return False
    except ValueError as e:
        print(f"❌ Tavily API key not found: {e}")
        print("\nTo fix:")
        print("  echo 'TAVILY_API_KEY=your-key-here' >> .env")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_groq_api_key():
    """Test 2: Check if Groq API key is configured."""
    print("\n" + "="*70)
    print("TEST 2: Groq API Key Configuration")
    print("="*70)
    
    try:
        from utils.config import get_groq_api_key
        api_key = get_groq_api_key()
        if api_key:
            print(f"✅ Groq API key loaded successfully")
            print(f"   Key: {api_key[:10]}...{api_key[-4:]}")
            return True
        else:
            print("❌ Groq API key is empty")
            return False
    except ValueError as e:
        print(f"❌ Groq API key not found: {e}")
        print("\nTo fix:")
        print("  echo 'GROQ_API_KEY=your-key-here' >> .env")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_known_podcast(podcast_name: str = "The Tim Ferriss Show"):
    """Test 3: Search for a well-known podcast."""
    print("\n" + "="*70)
    print(f"TEST 3: Search for Known Podcast - '{podcast_name}'")
    print("="*70)
    
    try:
        print(f"\n[3.1] Searching for: {podcast_name}")
        print("-" * 70)
        
        result = search_podcast_rss_feed(podcast_name)
        
        print(f"\n[3.2] Search Results:")
        print("-" * 70)
        print(f"Podcast Name: {result.get('podcast_name', 'N/A')}")
        print(f"RSS Feed: {result.get('rss_feed', 'N/A')}")
        print(f"Description: {result.get('description', 'N/A')[:100]}..." if result.get('description') else "N/A")
        print(f"Confidence: {result.get('confidence', 0.0):.0%}")
        print(f"Error: {result.get('error', 'None')}")
        
        if result.get('error'):
            print(f"\n❌ Search failed: {result['error']}")
            return False
        
        if not result.get('rss_feed'):
            print(f"\n⚠️  No RSS feed found")
            return False
        
        # Validate RSS feed URL
        rss_feed = result['rss_feed']
        if not (rss_feed.startswith('http://') or rss_feed.startswith('https://')):
            print(f"\n❌ Invalid RSS feed URL: {rss_feed}")
            return False
        
        # Check confidence
        confidence = result.get('confidence', 0.0)
        if confidence < 0.3:
            print(f"\n⚠️  Low confidence ({confidence:.0%}), but RSS feed found")
        else:
            print(f"\n✅ High confidence ({confidence:.0%})")
        
        # Validate RSS feed by parsing it
        print(f"\n[3.3] Validating RSS feed...")
        try:
            import feedparser
            parsed = feedparser.parse(rss_feed)
            
            if parsed.bozo:
                print(f"⚠️  RSS feed may have issues: {parsed.bozo_exception}")
            else:
                feed_title = parsed.feed.get('title', 'Unknown')
                print(f"✅ RSS feed is valid")
                print(f"   Feed Title: {feed_title}")
                print(f"   Entries: {len(parsed.entries)}")
        
        except Exception as e:
            print(f"⚠️  Could not validate RSS feed: {e}")
        
        print("\n✅ TEST 3 PASSED: Search completed successfully")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_multiple_podcasts():
    """Test 4: Search for multiple podcasts."""
    print("\n" + "="*70)
    print("TEST 4: Search for Multiple Podcasts")
    print("="*70)
    
    test_podcasts = [
        "Lex Fridman Podcast",
        "The Joe Rogan Experience",
        "How I Built This"
    ]
    
    results = []
    
    for podcast_name in test_podcasts:
        print(f"\n[4.1] Searching for: {podcast_name}")
        print("-" * 70)
        
        try:
            result = search_podcast_rss_feed(podcast_name)
            
            if result.get('rss_feed'):
                print(f"✅ Found: {result.get('rss_feed')}")
                print(f"   Confidence: {result.get('confidence', 0.0):.0%}")
                results.append({
                    'name': podcast_name,
                    'found': True,
                    'rss_feed': result.get('rss_feed'),
                    'confidence': result.get('confidence', 0.0)
                })
            else:
                print(f"⚠️  Not found: {result.get('error', 'Unknown error')}")
                results.append({
                    'name': podcast_name,
                    'found': False,
                    'error': result.get('error')
                })
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'name': podcast_name,
                'found': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("SEARCH SUMMARY")
    print("=" * 70)
    
    found_count = sum(1 for r in results if r.get('found'))
    print(f"\nFound: {found_count}/{len(test_podcasts)} podcasts")
    
    for result in results:
        if result.get('found'):
            print(f"  ✅ {result['name']}: {result.get('rss_feed', 'N/A')[:60]}... ({result.get('confidence', 0.0):.0%})")
        else:
            print(f"  ❌ {result['name']}: {result.get('error', 'Not found')}")
    
    if found_count >= len(test_podcasts) * 0.5:  # At least 50% success
        print("\n✅ TEST 4 PASSED: Multiple searches completed")
        return True
    else:
        print("\n⚠️  TEST 4 PARTIAL: Some searches failed")
        return False


def test_search_response_structure():
    """Test 5: Validate search response structure."""
    print("\n" + "="*70)
    print("TEST 5: Validate Response Structure")
    print("="*70)
    
    try:
        result = search_podcast_rss_feed("Test Podcast")
        
        # Check required fields
        required_fields = ['rss_feed', 'podcast_name', 'confidence', 'search_results', 'error']
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            print(f"❌ Missing fields: {missing_fields}")
            return False
        
        # Validate field types
        if result['rss_feed'] is not None and not isinstance(result['rss_feed'], str):
            print(f"❌ rss_feed should be string or None, got {type(result['rss_feed'])}")
            return False
        
        if not isinstance(result['podcast_name'], str):
            print(f"❌ podcast_name should be string, got {type(result['podcast_name'])}")
            return False
        
        if not isinstance(result['confidence'], (int, float)):
            print(f"❌ confidence should be number, got {type(result['confidence'])}")
            return False
        
        if not isinstance(result['search_results'], list):
            print(f"❌ search_results should be list, got {type(result['search_results'])}")
            return False
        
        if result['error'] is not None and not isinstance(result['error'], str):
            print(f"❌ error should be string or None, got {type(result['error'])}")
            return False
        
        print("✅ All fields present and correctly typed")
        print(f"   RSS Feed: {result['rss_feed'] is not None}")
        print(f"   Podcast Name: {result['podcast_name']}")
        print(f"   Confidence: {result['confidence']}")
        print(f"   Search Results: {len(result['search_results'])}")
        print(f"   Error: {result['error']}")
        
        print("\n✅ TEST 5 PASSED: Response structure is valid")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all search tool tests."""
    print("\n" + "="*70)
    print("TAVILY + GROQ SEARCH TOOL TEST")
    print("Testing: Podcast RSS Feed Search")
    print("="*70)
    
    results = {}
    
    # Test 1: Tavily API key
    results['tavily_key'] = test_tavily_api_key()
    if not results['tavily_key']:
        print("\n⚠️  Tavily API key not configured, some tests will fail")
    
    # Test 2: Groq API key
    results['groq_key'] = test_groq_api_key()
    if not results['groq_key']:
        print("\n⚠️  Groq API key not configured, tests will fail")
        return results
    
    # Test 3: Search known podcast
    if results['tavily_key'] and results['groq_key']:
        results['known_podcast'] = test_search_known_podcast("The Tim Ferriss Show")
        
        # Test 4: Search multiple podcasts
        results['multiple_podcasts'] = test_search_multiple_podcasts()
    
    # Test 5: Response structure (always run)
    results['response_structure'] = test_search_response_structure()
    
    # Final summary
    print("\n" + "="*70)
    print("🎉 SEARCH TOOL TEST COMPLETED!")
    print("="*70)
    
    print(f"\nTest Results:")
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}: {test_name}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n✅ All tests passed!")
    else:
        print("\n⚠️  Some tests failed or were skipped")
    
    return results


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

