#!/usr/bin/env python3
"""
Helper script to find RSS feed URLs for podcasts.
Uses various methods to locate working RSS feeds.
"""

import sys
import requests
import feedparser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def find_rss_from_apple_id(apple_id: int) -> str:
    """Try to get RSS feed from Apple Podcasts ID."""
    try:
        url = f"https://itunes.apple.com/lookup?id={apple_id}&entity=podcast"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('resultCount', 0) > 0:
            result = data['results'][0]
            feed_url = result.get('feedUrl')
            if feed_url:
                return feed_url
    except Exception as e:
        print(f"Error fetching from iTunes API: {e}")
    return None


def test_rss_url(url: str) -> bool:
    """Test if an RSS URL is valid and has episodes."""
    try:
        parsed = feedparser.parse(url)
        if parsed.entries and len(parsed.entries) > 0:
            return True
    except:
        pass
    return False


def find_bloomberg_stock_movers():
    """Find RSS feed for Bloomberg Stock Movers."""
    print("🔍 Searching for Bloomberg Stock Movers RSS feed...")
    
    # Try Apple Podcasts ID
    feed_url = find_rss_from_apple_id(1736584894)
    if feed_url and test_rss_url(feed_url):
        print(f"✅ Found via Apple Podcasts: {feed_url}")
        return feed_url
    
    # Try common Bloomberg patterns
    patterns = [
        "https://feeds.bloomberg.fm/BLM1736584894",
        "https://feeds.bloomberg.fm/stock-movers",
        "https://www.bloomberg.com/feeds/podcasts/stock_movers.xml",
    ]
    
    for url in patterns:
        if test_rss_url(url):
            print(f"✅ Found: {url}")
            return url
    
    print("⚠️  Could not find working RSS feed")
    print("   Try visiting: https://podcasts.apple.com/us/podcast/stock-movers/id1736584894")
    print("   And look for RSS feed link on the podcast's website")
    return None


def find_marketing_school():
    """Find RSS feed for Marketing School."""
    print("🔍 Searching for Marketing School RSS feed...")
    
    # Try Apple Podcasts ID
    feed_url = find_rss_from_apple_id(1294710068)
    if feed_url and test_rss_url(feed_url):
        print(f"✅ Found via Apple Podcasts: {feed_url}")
        return feed_url
    
    # Try Libsyn patterns
    patterns = [
        "https://marketingschool.libsyn.com/rss",
        "https://feeds.libsyn.com/129471/rss",
        "https://www.marketingschool.io/feed/podcast",
        "https://neilpatel.com/podcast/feed/",
    ]
    
    for url in patterns:
        if test_rss_url(url):
            print(f"✅ Found: {url}")
            return url
    
    print("⚠️  Could not find working RSS feed")
    print("   Try visiting: https://podcasts.apple.com/us/podcast/marketing-school/id1294710068")
    print("   Or check: https://www.marketingschool.io/")
    return None


if __name__ == "__main__":
    print("=" * 60)
    print("RSS Feed Finder")
    print("=" * 60)
    print()
    
    bloomberg_rss = find_bloomberg_stock_movers()
    print()
    
    marketing_rss = find_marketing_school()
    print()
    
    if bloomberg_rss or marketing_rss:
        print("=" * 60)
        print("Update config/feeds.yaml with these URLs:")
        print("=" * 60)
        if bloomberg_rss:
            print(f'  - name: "Bloomberg Stock Movers"')
            print(f'    url: "{bloomberg_rss}"')
            print(f'    category: "finance"')
        if marketing_rss:
            print(f'  - name: "Marketing School"')
            print(f'    url: "{marketing_rss}"')
            print(f'    category: "marketing"')

