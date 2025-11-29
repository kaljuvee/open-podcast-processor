#!/usr/bin/env python3
"""
Migration script to move feeds from feeds.yaml to PostgreSQL database.
Creates default user kaljuvee@gmail.com and associates all feeds with that user.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.postgres_db import PostgresDB
from utils.download import load_feeds_config
import yaml

def migrate_feeds():
    """Migrate feeds from YAML to database."""
    print("=" * 70)
    print("Migrating feeds from feeds.yaml to PostgreSQL database")
    print("=" * 70)
    
    # Initialize database
    try:
        db = PostgresDB()
        print("✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False
    
    # Load feeds from YAML
    config_path = Path(__file__).parent.parent / "config" / "feeds.yaml"
    if not config_path.exists():
        print(f"❌ feeds.yaml not found at {config_path}")
        return False
    
    try:
        feeds_config = load_feeds_config(str(config_path))
        feeds = feeds_config.get('feeds', [])
        print(f"✓ Loaded {len(feeds)} feeds from YAML")
    except Exception as e:
        print(f"❌ Failed to load feeds.yaml: {e}")
        return False
    
    # Create or get default user
    default_email = "kaljuvee@gmail.com"
    user_id = db.get_or_create_user(default_email, name="Default User")
    print(f"✓ User: {default_email} (ID: {user_id})")
    
    # Migrate feeds
    migrated_count = 0
    skipped_count = 0
    
    for feed in feeds:
        name = feed.get('name', '')
        url = feed.get('url', '')
        category = feed.get('category', 'general')
        
        if not name or not url:
            print(f"⚠️  Skipping feed with missing name or URL: {feed}")
            skipped_count += 1
            continue
        
        try:
            # Create or get feed
            feed_id = db.create_or_get_feed(name, url, category)
            
            # Associate with user
            db.associate_feed_with_user(feed_id, user_id)
            
            print(f"  ✓ {name} -> {url[:60]}...")
            migrated_count += 1
        except Exception as e:
            print(f"  ❌ Failed to migrate {name}: {e}")
            skipped_count += 1
    
    print("\n" + "=" * 70)
    print(f"Migration complete!")
    print(f"  Migrated: {migrated_count}")
    print(f"  Skipped: {skipped_count}")
    print("=" * 70)
    
    db.close()
    return True

if __name__ == "__main__":
    success = migrate_feeds()
    sys.exit(0 if success else 1)

