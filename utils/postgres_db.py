"""
PostgreSQL database utility for storing processed podcast data.
Uses SQLAlchemy ORM for database interactions.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import create_engine, text, inspect, Column, Integer, String, Text, BigInteger, DateTime, JSON
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB

from utils.config import get_db_url, get_db_schema

# Create base class for declarative models
Base = declarative_base()


class Podcast(Base):
    """SQLAlchemy ORM model for podcasts table."""
    __tablename__ = 'podcasts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    feed_url = Column(String(1000))
    episode_url = Column(String(1000))
    published_at = Column(DateTime)
    duration_seconds = Column(Integer)
    audio_file_path = Column(String(1000))
    file_size_bytes = Column(BigInteger)
    status = Column(String(50), default='downloaded')
    processed_at = Column(DateTime)
    transcript = Column(JSONB)
    summary = Column(JSONB)
    podcast_feed_name = Column(String(255))
    podcast_category = Column(String(100))
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))


class PostgresDB:
    """PostgreSQL database interface for podcast storage."""
    
    def __init__(self, db_url: str = None, schema: str = None):
        """
        Initialize PostgreSQL connection.
        
        Args:
            db_url: Database URL (defaults to DB_URL from .env)
            schema: Schema name (defaults to DB_SCHEMA from .env or 'public')
        """
        self.db_url = db_url or get_db_url()
        self.schema = schema or get_db_schema()
        self.engine = create_engine(self.db_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._ensure_schema()
        
        # Set schema for models if not public
        if self.schema != 'public':
            Podcast.__table__.schema = self.schema
    
    def _ensure_schema(self):
        """Ensure the schema exists."""
        try:
            with self.engine.connect() as conn:
                if self.schema != 'public':
                    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema}"))
                    conn.commit()
        except Exception as e:
            print(f"Warning: Could not ensure schema exists: {e}")
    
    def execute_sql_file(self, sql_file_path: str):
        """
        Execute SQL file to create schema.
        Uses psycopg2 directly to handle dollar-quoted strings properly.
        Sets the search_path to use the correct schema.
        
        Args:
            sql_file_path: Path to SQL file
        """
        from pathlib import Path
        import psycopg2
        from urllib.parse import urlparse
        
        sql_path = Path(sql_file_path)
        if not sql_path.exists():
            raise FileNotFoundError(f"SQL file not found: {sql_file_path}")
        
        with open(sql_path, 'r') as f:
            sql_content = f.read()
        
        # Replace schema placeholder if needed
        if '{schema}' in sql_content:
            sql_content = sql_content.replace('{schema}', self.schema)
        
        try:
            # Parse database URL and use psycopg2 directly for better SQL file handling
            parsed = urlparse(self.db_url)
            conn_params = {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path[1:] if parsed.path else None,
                'user': parsed.username,
                'password': parsed.password
            }
            
            # Remove None values
            conn_params = {k: v for k, v in conn_params.items() if v is not None}
            
            # Use psycopg2 directly which handles dollar-quoted strings properly
            with psycopg2.connect(**conn_params) as conn:
                conn.autocommit = False
                cursor = conn.cursor()
                
                # Set search_path to use the correct schema
                if self.schema != 'public':
                    cursor.execute(f"SET search_path TO {self.schema}, public")
                
                # Execute SQL statements one by one to handle errors better
                # Split by semicolon but preserve dollar-quoted strings
                statements = []
                current_statement = ""
                in_dollar_quote = False
                dollar_tag = None
                
                i = 0
                while i < len(sql_content):
                    char = sql_content[i]
                    
                    # Check for dollar-quoted strings (e.g., $$...$$ or $tag$...$tag$)
                    if char == '$' and not in_dollar_quote:
                        # Look ahead to find the closing tag
                        j = i + 1
                        tag_start = i
                        while j < len(sql_content) and sql_content[j] not in [' ', '\n', '\t', '$']:
                            j += 1
                        if j < len(sql_content) and sql_content[j] == '$':
                            dollar_tag = sql_content[tag_start:j+1]
                            in_dollar_quote = True
                            current_statement += sql_content[i:j+1]
                            i = j + 1
                            continue
                    elif in_dollar_quote and sql_content[i:i+len(dollar_tag)] == dollar_tag:
                        current_statement += dollar_tag
                        i += len(dollar_tag)
                        in_dollar_quote = False
                        dollar_tag = None
                        continue
                    
                    if not in_dollar_quote and char == ';':
                        stmt = current_statement.strip()
                        if stmt and not stmt.startswith('--'):
                            statements.append(stmt)
                        current_statement = ""
                    else:
                        current_statement += char
                    i += 1
                
                # Add final statement if any
                if current_statement.strip() and not current_statement.strip().startswith('--'):
                    statements.append(current_statement.strip())
                
                # Execute each statement
                for stmt in statements:
                    if stmt.strip():
                        try:
                            cursor.execute(stmt)
                        except Exception as e:
                            # Some errors are expected (e.g., table already exists)
                            error_msg = str(e)
                            if 'already exists' not in error_msg.lower() and 'duplicate' not in error_msg.lower():
                                print(f"Warning: Error executing statement: {error_msg[:100]}")
                                print(f"Statement: {stmt[:200]}...")
                
                conn.commit()
                cursor.close()
        except Exception as e:
            print(f"Warning: Error executing SQL file: {e}")
            print("Schema may already exist or some statements may have failed")
            # Don't raise - allow the test to continue
    
    def save_podcast(
        self,
        title: str,
        description: str = None,
        feed_url: str = None,
        episode_url: str = None,
        published_at: datetime = None,
        duration_seconds: int = None,
        audio_file_path: str = None,
        file_size_bytes: int = None,
        status: str = 'downloaded',
        transcript: Dict[str, Any] = None,
        summary: Dict[str, Any] = None,
        podcast_feed_name: str = None,
        podcast_category: str = None
    ) -> int:
        """
        Save or update a podcast episode using SQLAlchemy ORM.
        
        Args:
            title: Episode title
            description: Episode description
            feed_url: RSS feed URL
            episode_url: Episode URL
            published_at: Publication timestamp
            duration_seconds: Duration in seconds
            audio_file_path: Path to audio file
            file_size_bytes: File size in bytes
            status: Processing status
            transcript: Transcript data (will be stored as JSONB)
            summary: Summary data (will be stored as JSONB)
            podcast_feed_name: Name of the podcast feed
            podcast_category: Category of the podcast
            
        Returns:
            int: Podcast ID
        """
        session = self.SessionLocal()
        try:
            # Check if podcast already exists (by episode_url)
            existing = None
            if episode_url:
                existing = session.query(Podcast).filter(Podcast.episode_url == episode_url).first()
            
            if existing:
                # Update existing podcast
                if title is not None:
                    existing.title = title
                if description is not None:
                    existing.description = description
                if duration_seconds is not None:
                    existing.duration_seconds = duration_seconds
                if audio_file_path is not None:
                    existing.audio_file_path = audio_file_path
                if file_size_bytes is not None:
                    existing.file_size_bytes = file_size_bytes
                if status is not None:
                    existing.status = status
                if transcript is not None:
                    existing.transcript = transcript
                if summary is not None:
                    existing.summary = summary
                if status == 'processed' and existing.processed_at is None:
                    existing.processed_at = datetime.now()
                
                session.commit()
                return existing.id
            else:
                # Insert new podcast
                new_podcast = Podcast(
                    title=title,
                    description=description,
                    feed_url=feed_url,
                    episode_url=episode_url,
                    published_at=published_at,
                    duration_seconds=duration_seconds,
                    audio_file_path=audio_file_path,
                    file_size_bytes=file_size_bytes,
                    status=status,
                    transcript=transcript,
                    summary=summary,
                    podcast_feed_name=podcast_feed_name,
                    podcast_category=podcast_category
                )
                session.add(new_podcast)
                session.commit()
                session.refresh(new_podcast)
                return new_podcast.id
        finally:
            session.close()
    
    def update_podcast(
        self,
        podcast_id: int,
        title: str = None,
        description: str = None,
        duration_seconds: int = None,
        audio_file_path: str = None,
        file_size_bytes: int = None,
        status: str = None,
        transcript: Dict[str, Any] = None,
        summary: Dict[str, Any] = None,
        processed_at: datetime = None
    ):
        """
        Update an existing podcast using SQLAlchemy ORM.
        
        Args:
            podcast_id: Podcast ID
            title: Episode title
            description: Episode description
            duration_seconds: Duration in seconds
            audio_file_path: Path to audio file
            file_size_bytes: File size in bytes
            status: Processing status
            transcript: Transcript data
            summary: Summary data
            processed_at: Processing timestamp
        """
        session = self.SessionLocal()
        try:
            podcast = session.query(Podcast).filter(Podcast.id == podcast_id).first()
            if not podcast:
                print(f"⚠️  Warning: Podcast {podcast_id} not found for update")
                return
            
            if title is not None:
                podcast.title = title
            if description is not None:
                podcast.description = description
            if duration_seconds is not None:
                podcast.duration_seconds = duration_seconds
            if audio_file_path is not None:
                podcast.audio_file_path = audio_file_path
            if file_size_bytes is not None:
                podcast.file_size_bytes = file_size_bytes
            if status is not None:
                podcast.status = status
            if transcript is not None:
                podcast.transcript = transcript
            if summary is not None:
                podcast.summary = summary
            if processed_at is not None:
                podcast.processed_at = processed_at
            elif status == 'processed' and podcast.processed_at is None:
                podcast.processed_at = datetime.now()
            
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"❌ Error updating podcast {podcast_id}: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            session.close()
    
    def get_podcast_by_id(self, podcast_id: int) -> Optional[Dict[str, Any]]:
        """Get podcast by ID using SQLAlchemy ORM."""
        session = self.SessionLocal()
        try:
            podcast = session.query(Podcast).filter(Podcast.id == podcast_id).first()
            if podcast:
                return self._podcast_to_dict(podcast)
            return None
        finally:
            session.close()
    
    def get_podcast_by_url(self, episode_url: str) -> Optional[Dict[str, Any]]:
        """Get podcast by episode URL using SQLAlchemy ORM."""
        session = self.SessionLocal()
        try:
            podcast = session.query(Podcast).filter(Podcast.episode_url == episode_url).first()
            if podcast:
                return self._podcast_to_dict(podcast)
            return None
        finally:
            session.close()
    
    def _podcast_to_dict(self, podcast: Podcast) -> Dict[str, Any]:
        """Convert SQLAlchemy Podcast object to dictionary."""
        return {
            'id': podcast.id,
            'title': podcast.title,
            'description': podcast.description,
            'feed_url': podcast.feed_url,
            'episode_url': podcast.episode_url,
            'published_at': podcast.published_at,
            'duration_seconds': podcast.duration_seconds,
            'audio_file_path': podcast.audio_file_path,
            'file_size_bytes': podcast.file_size_bytes,
            'status': podcast.status,
            'processed_at': podcast.processed_at,
            'transcript': podcast.transcript,
            'summary': podcast.summary,
            'podcast_feed_name': podcast.podcast_feed_name,
            'podcast_category': podcast.podcast_category,
            'created_at': podcast.created_at,
            'updated_at': podcast.updated_at
        }
    
    def get_all_podcasts(self, status: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get all podcasts, optionally filtered by status using SQLAlchemy ORM.
        
        Args:
            status: Filter by status (optional)
            limit: Maximum number of results
            
        Returns:
            List of podcast dictionaries
        """
        session = self.SessionLocal()
        try:
            query = session.query(Podcast)
            
            if status:
                query = query.filter(Podcast.status == status)
            
            query = query.order_by(
                Podcast.published_at.desc().nullslast(),
                Podcast.created_at.desc()
            )
            
            if limit:
                query = query.limit(limit)
            
            podcasts = query.all()
            return [self._podcast_to_dict(p) for p in podcasts]
        finally:
            session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get podcast statistics."""
        view_name = f"{self.schema}.podcast_stats" if self.schema != 'public' else "podcast_stats"
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {view_name}"))
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return {}
    
    def get_podcast_by_feed_url(self, feed_url: str) -> Optional[Dict[str, Any]]:
        """Get podcast by feed URL (RSS URL)."""
        session = self.SessionLocal()
        try:
            podcast = session.query(Podcast).filter(Podcast.feed_url == feed_url).first()
            if podcast:
                return self._podcast_to_dict(podcast)
            return None
        finally:
            session.close()
    
    def episode_exists(self, episode_url: str) -> bool:
        """Check if episode already exists by episode URL."""
        session = self.SessionLocal()
        try:
            podcast = session.query(Podcast).filter(Podcast.episode_url == episode_url).first()
            return podcast is not None
        finally:
            session.close()
    
    def get_episodes_by_status(self, status: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get episodes by status (compatibility method).
        
        Args:
            status: Status filter
            limit: Maximum number of results
            
        Returns:
            List of episode dictionaries
        """
        return self.get_all_podcasts(status=status, limit=limit)
    
    def get_episode_by_id(self, episode_id: int) -> Optional[Dict[str, Any]]:
        """Get episode by ID (alias for get_podcast_by_id)."""
        return self.get_podcast_by_id(episode_id)
    
    def get_transcripts_for_episode(self, episode_id: int) -> List[Dict[str, Any]]:
        """
        Get transcript segments for an episode.
        Extracts segments from JSONB transcript field.
        
        Args:
            episode_id: Episode ID
            
        Returns:
            List of transcript segment dictionaries
        """
        episode = self.get_podcast_by_id(episode_id)
        if not episode or not episode.get('transcript'):
            return []
        
        transcript = episode['transcript']
        if isinstance(transcript, dict):
            segments = transcript.get('segments', [])
            # Convert to expected format
            result = []
            for seg in segments:
                result.append({
                    'id': None,  # Not stored separately in PostgreSQL
                    'episode_id': episode_id,
                    'speaker': seg.get('speaker'),
                    'timestamp_start': seg.get('start'),
                    'timestamp_end': seg.get('end'),
                    'text': seg.get('text', ''),
                    'confidence': seg.get('confidence', 1.0),
                    'created_at': None
                })
            return result
        return []
    
    def add_transcript_segments(self, episode_id: int, segments: List[Dict[str, Any]]):
        """
        Add transcript segments to an episode.
        Updates the transcript JSONB field.
        
        Args:
            episode_id: Episode ID
            segments: List of segment dictionaries
        """
        episode = self.get_podcast_by_id(episode_id)
        if not episode:
            print(f"⚠️  Warning: Episode {episode_id} not found in database")
            return
        
        # Prepare transcript data
        full_text = " ".join(seg.get('text', '') for seg in segments)
        transcript_data = {
            'segments': segments,
            'text': full_text,
            'language': 'en',  # Default, could be detected
            'provider': 'groq',
            'chunked': False
        }
        
        # Update episode with transcript
        try:
            self.update_podcast(
                podcast_id=episode_id,
                status='transcribed',
                transcript=transcript_data
            )
            print(f"   ✅ Transcript saved: {len(segments)} segments, {len(full_text):,} characters")
        except Exception as e:
            print(f"   ❌ Error saving transcript: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def add_summary(self, episode_id: int, key_topics: List[str], themes: List[str],
                   quotes: List[str], startups: List[str], full_summary: str,
                   digest_date: datetime = None):
        """
        Add summary to an episode.
        Updates the summary JSONB field.
        
        Args:
            episode_id: Episode ID
            key_topics: List of key topics
            themes: List of themes
            quotes: List of quotes
            startups: List of startups/companies
            full_summary: Full summary text
            digest_date: Digest date (optional)
        """
        summary_data = {
            'key_topics': key_topics,
            'themes': themes,
            'quotes': quotes,
            'startups': startups,
            'summary': full_summary
        }
        
        # Update episode with summary
        self.update_podcast(
            podcast_id=episode_id,
            status='processed',
            summary=summary_data,
            processed_at=digest_date or datetime.now()
        )
    
    def update_episode_status(self, episode_id: int, status: str):
        """Update episode status (alias for update_podcast)."""
        self.update_podcast(podcast_id=episode_id, status=status)
    
    def get_or_create_user(self, email: str, name: str = None) -> int:
        """
        Get or create a user by email.
        
        Args:
            email: User email
            name: User name (optional)
            
        Returns:
            int: User ID
        """
        session = self.SessionLocal()
        try:
            from sqlalchemy import text
            # Check if user exists
            result = session.execute(text(
                f"SELECT id FROM {self.schema}.users WHERE email = :email"
            ), {"email": email})
            user = result.fetchone()
            
            if user:
                return user[0]
            
            # Create new user
            result = session.execute(text(f"""
                INSERT INTO {self.schema}.users (email, name)
                VALUES (:email, :name)
                RETURNING id
            """), {"email": email, "name": name})
            user_id = result.fetchone()[0]
            session.commit()
            return user_id
        finally:
            session.close()
    
    def create_or_get_feed(self, name: str, url: str, category: str = None) -> int:
        """
        Create or get a feed by URL.
        
        Args:
            name: Feed name
            url: Feed URL
            category: Feed category
            
        Returns:
            int: Feed ID
        """
        session = self.SessionLocal()
        try:
            from sqlalchemy import text
            # Check if feed exists
            result = session.execute(text(
                f"SELECT id FROM {self.schema}.feeds WHERE url = :url"
            ), {"url": url})
            feed = result.fetchone()
            
            if feed:
                # Update name and category if provided
                if name or category:
                    session.execute(text(f"""
                        UPDATE {self.schema}.feeds
                        SET name = COALESCE(:name, name),
                            category = COALESCE(:category, category),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """), {"id": feed[0], "name": name, "category": category})
                    session.commit()
                return feed[0]
            
            # Create new feed
            result = session.execute(text(f"""
                INSERT INTO {self.schema}.feeds (name, url, category)
                VALUES (:name, :url, :category)
                RETURNING id
            """), {"name": name, "url": url, "category": category})
            feed_id = result.fetchone()[0]
            session.commit()
            return feed_id
        finally:
            session.close()
    
    def associate_feed_with_user(self, feed_id: int, user_id: int):
        """
        Associate a feed with a user (many-to-many).
        
        Args:
            feed_id: Feed ID
            user_id: User ID
        """
        session = self.SessionLocal()
        try:
            from sqlalchemy import text
            # Check if association exists
            result = session.execute(text(f"""
                SELECT id FROM {self.schema}.feed_user
                WHERE feed_id = :feed_id AND user_id = :user_id
            """), {"feed_id": feed_id, "user_id": user_id})
            
            if result.fetchone():
                return  # Already associated
            
            # Create association
            session.execute(text(f"""
                INSERT INTO {self.schema}.feed_user (feed_id, user_id)
                VALUES (:feed_id, :user_id)
            """), {"feed_id": feed_id, "user_id": user_id})
            session.commit()
        finally:
            session.close()
    
    def get_user_feeds(self, user_id: int = None, user_email: str = None) -> List[Dict[str, Any]]:
        """
        Get feeds for a user.
        
        Args:
            user_id: User ID (optional)
            user_email: User email (optional, used if user_id not provided)
            
        Returns:
            List of feed dictionaries
        """
        session = self.SessionLocal()
        try:
            from sqlalchemy import text
            
            if user_id is None and user_email:
                user = session.execute(text(
                    f"SELECT id FROM {self.schema}.users WHERE email = :email"
                ), {"email": user_email}).fetchone()
                if user:
                    user_id = user[0]
                else:
                    return []
            
            if user_id is None:
                return []
            
            result = session.execute(text(f"""
                SELECT f.id, f.name, f.url, f.category, f.enabled, f.created_at
                FROM {self.schema}.feeds f
                INNER JOIN {self.schema}.feed_user fu ON f.id = fu.feed_id
                WHERE fu.user_id = :user_id AND f.enabled = TRUE
                ORDER BY f.name
            """), {"user_id": user_id})
            
            feeds = []
            for row in result:
                feeds.append({
                    'id': row[0],
                    'name': row[1],
                    'url': row[2],
                    'category': row[3],
                    'enabled': row[4],
                    'created_at': row[5]
                })
            return feeds
        finally:
            session.close()
    
    def add_feed(self, name: str, url: str, category: str = None, user_id: int = None, user_email: str = None) -> int:
        """
        Add a new feed and associate with user.
        
        Args:
            name: Feed name
            url: Feed URL
            category: Feed category
            user_id: User ID (optional)
            user_email: User email (optional)
            
        Returns:
            int: Feed ID
        """
        feed_id = self.create_or_get_feed(name, url, category)
        
        if user_id is None and user_email:
            user_id = self.get_or_create_user(user_email)
        
        if user_id:
            self.associate_feed_with_user(feed_id, user_id)
        
        return feed_id
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()

