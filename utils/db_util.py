"""
Database utilities for Open Podcast Processor.
Provides functions to test, query, and verify the DuckDB database.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from utils.database import P3Database


def verify_schema(db: P3Database) -> Dict[str, bool]:
    """
    Verify that all required tables exist in the database.
    
    Args:
        db: Database instance
        
    Returns:
        Dictionary mapping table names to existence status
    """
    required_tables = ['podcasts', 'episodes', 'transcripts', 'summaries']
    schema_status = {}
    
    for table in required_tables:
        try:
            # Try to query the table - if it exists, this will succeed
            db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            schema_status[table] = True
        except Exception:
            schema_status[table] = False
    
    return schema_status


def get_database_stats(db: P3Database) -> Dict[str, Any]:
    """
    Get statistics about the database contents.
    
    Args:
        db: Database instance
        
    Returns:
        Dictionary with database statistics
    """
    stats = {
        'podcasts': 0,
        'episodes': 0,
        'episodes_by_status': {},
        'transcripts': 0,
        'summaries': 0,
        'database_path': str(db.db_path),
        'database_size_mb': 0
    }
    
    try:
        # Count podcasts
        result = db.conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()
        stats['podcasts'] = result[0] if result else 0
        
        # Count episodes
        result = db.conn.execute("SELECT COUNT(*) FROM episodes").fetchone()
        stats['episodes'] = result[0] if result else 0
        
        # Count episodes by status
        result = db.conn.execute("""
            SELECT status, COUNT(*) 
            FROM episodes 
            GROUP BY status
        """).fetchall()
        stats['episodes_by_status'] = {row[0]: row[1] for row in result}
        
        # Count transcripts
        result = db.conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()
        stats['transcripts'] = result[0] if result else 0
        
        # Count summaries
        result = db.conn.execute("SELECT COUNT(*) FROM summaries").fetchone()
        stats['summaries'] = result[0] if result else 0
        
        # Database file size
        if db.db_path.exists():
            stats['database_size_mb'] = round(db.db_path.stat().st_size / (1024 * 1024), 2)
        
    except Exception as e:
        stats['error'] = str(e)
    
    return stats


def query_podcasts(db: P3Database, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Query podcasts from the database.
    
    Args:
        db: Database instance
        limit: Maximum number of podcasts to return
        
    Returns:
        List of podcast dictionaries
    """
    try:
        results = db.conn.execute("""
            SELECT id, title, rss_url, category, created_at 
            FROM podcasts 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,)).fetchall()
        
        podcasts = []
        for row in results:
            podcasts.append({
                'id': row[0],
                'title': row[1],
                'rss_url': row[2],
                'category': row[3],
                'created_at': row[4]
            })
        return podcasts
    except Exception as e:
        return []


def query_episodes(db: P3Database, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Query episodes from the database.
    
    Args:
        db: Database instance
        status: Filter by status (downloaded, transcribed, processed)
        limit: Maximum number of episodes to return
        
    Returns:
        List of episode dictionaries with podcast info
    """
    try:
        if status:
            results = db.conn.execute("""
                SELECT e.id, e.podcast_id, e.title, e.date, e.url, e.file_path, 
                       e.duration_seconds, e.status, e.created_at, p.title as podcast_title
                FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE e.status = ?
                ORDER BY e.date DESC
                LIMIT ?
            """, (status, limit)).fetchall()
        else:
            results = db.conn.execute("""
                SELECT e.id, e.podcast_id, e.title, e.date, e.url, e.file_path,
                       e.duration_seconds, e.status, e.created_at, p.title as podcast_title
                FROM episodes e
                JOIN podcasts p ON e.podcast_id = p.id
                ORDER BY e.date DESC
                LIMIT ?
            """, (limit,)).fetchall()
        
        episodes = []
        for row in results:
            episodes.append({
                'id': row[0],
                'podcast_id': row[1],
                'title': row[2],
                'date': row[3],
                'url': row[4],
                'file_path': row[5],
                'duration_seconds': row[6],
                'status': row[7],
                'created_at': row[8],
                'podcast_title': row[9]
            })
        return episodes
    except Exception as e:
        return []


def query_transcripts(db: P3Database, episode_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Query transcripts from the database.
    
    Args:
        db: Database instance
        episode_id: Filter by episode ID
        limit: Maximum number of transcript segments to return
        
    Returns:
        List of transcript segment dictionaries
    """
    try:
        if episode_id:
            results = db.conn.execute("""
                SELECT id, episode_id, speaker, timestamp_start, timestamp_end, text, confidence, created_at
                FROM transcripts
                WHERE episode_id = ?
                ORDER BY timestamp_start
                LIMIT ?
            """, (episode_id, limit)).fetchall()
        else:
            results = db.conn.execute("""
                SELECT id, episode_id, speaker, timestamp_start, timestamp_end, text, confidence, created_at
                FROM transcripts
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
        
        transcripts = []
        for row in results:
            transcripts.append({
                'id': row[0],
                'episode_id': row[1],
                'speaker': row[2],
                'timestamp_start': row[3],
                'timestamp_end': row[4],
                'text': row[5],
                'confidence': row[6],
                'created_at': row[7]
            })
        return transcripts
    except Exception as e:
        return []


def query_summaries(db: P3Database, episode_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Query summaries from the database.
    
    Args:
        db: Database instance
        episode_id: Filter by episode ID
        limit: Maximum number of summaries to return
        
    Returns:
        List of summary dictionaries
    """
    try:
        if episode_id:
            results = db.conn.execute("""
                SELECT s.id, s.episode_id, s.key_topics, s.themes, s.quotes, s.startups,
                       s.digest_date, s.full_summary, s.created_at,
                       e.title as episode_title, p.title as podcast_title
                FROM summaries s
                JOIN episodes e ON s.episode_id = e.id
                JOIN podcasts p ON e.podcast_id = p.id
                WHERE s.episode_id = ?
                ORDER BY s.digest_date DESC
                LIMIT ?
            """, (episode_id, limit)).fetchall()
        else:
            results = db.conn.execute("""
                SELECT s.id, s.episode_id, s.key_topics, s.themes, s.quotes, s.startups,
                       s.digest_date, s.full_summary, s.created_at,
                       e.title as episode_title, p.title as podcast_title
                FROM summaries s
                JOIN episodes e ON s.episode_id = e.id
                JOIN podcasts p ON e.podcast_id = p.id
                ORDER BY s.digest_date DESC
                LIMIT ?
            """, (limit,)).fetchall()
        
        summaries = []
        for row in results:
            summaries.append({
                'id': row[0],
                'episode_id': row[1],
                'key_topics': json.loads(row[2]) if row[2] else [],
                'themes': json.loads(row[3]) if row[3] else [],
                'quotes': json.loads(row[4]) if row[4] else [],
                'startups': json.loads(row[5]) if row[5] else [],
                'digest_date': row[6],
                'full_summary': row[7],
                'created_at': row[8],
                'episode_title': row[9],
                'podcast_title': row[10]
            })
        return summaries
    except Exception as e:
        return []


def test_database_operations(db: P3Database) -> Dict[str, Any]:
    """
    Test basic database operations: create, read, update.
    
    Args:
        db: Database instance
        
    Returns:
        Dictionary with test results
    """
    test_results = {
        'schema_verification': {},
        'create_test': {},
        'read_test': {},
        'stats': {}
    }
    
    # Test 1: Verify schema
    test_results['schema_verification'] = verify_schema(db)
    
    # Test 2: Create test podcast
    try:
        # Use unique URL to avoid conflicts
        import time
        test_url = f"https://test.example.com/feed_{int(time.time())}.xml"
        test_podcast_id = db.add_podcast(
            title="Test Podcast",
            rss_url=test_url,
            category="test"
        )
        test_results['create_test']['podcast_created'] = True
        test_results['create_test']['podcast_id'] = test_podcast_id
        
        # Test 3: Read back the podcast
        podcast = db.get_podcast_by_url(test_url)
        if podcast and podcast['id'] == test_podcast_id:
            test_results['read_test']['podcast_read'] = True
            test_results['read_test']['podcast_data'] = podcast
        else:
            test_results['read_test']['podcast_read'] = False
        
        # Test 4: Create test episode
        test_episode_id = db.add_episode(
            podcast_id=test_podcast_id,
            title="Test Episode",
            date=datetime.now(),
            url="https://test.example.com/episode1.mp3",
            file_path="/tmp/test.mp3"
        )
        test_results['create_test']['episode_created'] = True
        test_results['create_test']['episode_id'] = test_episode_id
        
        # Test 5: Read episodes
        episodes = query_episodes(db, limit=5)
        test_results['read_test']['episodes_read'] = len(episodes) > 0
        test_results['read_test']['episode_count'] = len(episodes)
        
        # Test 6: Update episode status
        db.update_episode_status(test_episode_id, 'transcribed')
        updated_episodes = db.get_episodes_by_status('transcribed')
        test_results['read_test']['status_update_works'] = len(updated_episodes) > 0
        
    except Exception as e:
        test_results['create_test']['error'] = str(e)
        test_results['read_test']['error'] = str(e)
    
    # Test 7: Get stats
    test_results['stats'] = get_database_stats(db)
    
    return test_results

