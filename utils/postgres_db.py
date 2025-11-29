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
                
                # Execute the entire SQL file - psycopg2 handles it properly
                cursor.execute(sql_content)
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
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()

