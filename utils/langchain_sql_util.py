"""
LangChain SQL utility for querying podcast transcripts and answering questions.
Uses text-to-SQL to find relevant podcasts, then answers questions using Groq LLM.
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import text, inspect
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.postgres_db import PostgresDB
from utils.config import (
    get_groq_api_key,
    get_groq_model,
    get_groq_temperature,
    get_groq_max_tokens,
    get_db_url,
    get_db_schema
)


class PodcastSQLAssistant:
    """AI Assistant that uses SQL to find relevant podcasts and answers questions."""
    
    def __init__(self, db: PostgresDB = None, api_key: str = None, model: str = None):
        """
        Initialize the SQL assistant.
        
        Args:
            db: PostgresDB instance (creates new if not provided)
            api_key: Groq API key (defaults to environment)
            model: Groq model to use (defaults to GROQ_MODEL from .env)
        """
        self.db = db or PostgresDB()
        self.api_key = api_key or get_groq_api_key()
        self.model = model or get_groq_model()
        self.temperature = get_groq_temperature()
        self.max_tokens = get_groq_max_tokens()
        
        # Initialize Groq LLM
        self.llm = ChatGroq(
            model_name=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            groq_api_key=self.api_key
        )
        
        # Initialize SQL chain
        self._init_sql_chain()
    
    def _init_sql_chain(self):
        """Initialize SQL generation chain for text-to-SQL queries."""
        schema = self.db.schema
        schema_prefix = f"{schema}." if schema != 'public' else ""
        
        # Create prompt for SQL generation
        sql_prompt = f"""You are a PostgreSQL expert. Given a question, write a SQL query to find relevant podcast episodes.

Use the following table structure:
- Table: {schema_prefix}podcasts
- Columns: id, title, description, podcast_feed_name, podcast_category, published_at, transcript (JSONB), summary (JSONB), status

Important:
1. For transcript searches, use JSONB operators: transcript->>'text' ILIKE '%keyword%'
2. For summary searches, use: summary->>'summary' ILIKE '%keyword%' OR summary->'key_topics'::text ILIKE '%keyword%'
3. Always filter for episodes with transcripts: transcript IS NOT NULL AND transcript->>'text' IS NOT NULL
4. Return columns: id, title, podcast_feed_name, transcript, summary
5. Limit results to top 10 most relevant episodes

Question: {{question}}

SQL Query:"""
        
        self.sql_prompt_template = ChatPromptTemplate.from_template(sql_prompt)
        self.sql_chain = self.sql_prompt_template | self.llm | StrOutputParser()
    
    def _chunk_text(self, text: str, max_chunk_size: int = 100000) -> List[str]:
        """
        Chunk text into smaller pieces if too large.
        
        Args:
            text: Text to chunk
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        # Try to split on sentences/paragraphs
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def find_relevant_podcasts(self, question: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Use text-to-SQL to find relevant podcast episodes.
        
        Args:
            question: User's question
            limit: Maximum number of episodes to return
            
        Returns:
            List of episode dictionaries with id, title, transcript, etc.
        """
        try:
            # Generate SQL query
            sql_query = self.sql_chain.invoke({"question": question})
            
            # Clean up SQL query (remove markdown code blocks if present)
            sql_query = sql_query.strip()
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.startswith("```"):
                sql_query = sql_query[3:]
            sql_query = sql_query.strip()
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3].strip()
            
            # Execute query
            schema_prefix = f"{self.db.schema}." if self.db.schema != 'public' else ""
            
            # Ensure schema is set
            with self.db.engine.connect() as conn:
                if self.db.schema != 'public':
                    conn.execute(text(f"SET search_path TO {self.db.schema}, public"))
                
                result = conn.execute(text(sql_query))
                rows = result.fetchall()
                
                # Convert to dictionaries
                episodes = []
                for row in rows[:limit]:
                    episode_dict = {
                        'id': row[0] if len(row) > 0 else None,
                        'title': row[1] if len(row) > 1 else 'Unknown',
                        'podcast_feed_name': row[2] if len(row) > 2 else 'Unknown',
                        'transcript': row[3] if len(row) > 3 else None,
                        'summary': row[4] if len(row) > 4 else None
                    }
                    
                    # Parse JSONB fields
                    if episode_dict['transcript'] and isinstance(episode_dict['transcript'], str):
                        try:
                            episode_dict['transcript'] = json.loads(episode_dict['transcript'])
                        except:
                            pass
                    
                    if episode_dict['summary'] and isinstance(episode_dict['summary'], str):
                        try:
                            episode_dict['summary'] = json.loads(episode_dict['summary'])
                        except:
                            pass
                    
                    episodes.append(episode_dict)
                
                return episodes
        
        except Exception as e:
            # Fallback: simple keyword search
            print(f"SQL query failed, using fallback search: {e}")
            return self._fallback_search(question, limit)
    
    def _fallback_search(self, question: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fallback search using simple keyword matching."""
        keywords = question.lower().split()
        
        with self.db.engine.connect() as conn:
            schema_prefix = f"{self.db.schema}." if self.db.schema != 'public' else ""
            
            if self.db.schema != 'public':
                conn.execute(text(f"SET search_path TO {self.db.schema}, public"))
            
            # Build query with keyword matching
            conditions = []
            for keyword in keywords:
                conditions.append(f"(transcript->>'text' ILIKE '%{keyword}%' OR summary->>'summary' ILIKE '%{keyword}%')")
            
            where_clause = " OR ".join(conditions)
            
            query = text(f"""
                SELECT id, title, podcast_feed_name, transcript, summary
                FROM {schema_prefix}podcasts
                WHERE transcript IS NOT NULL 
                  AND transcript->>'text' IS NOT NULL
                  AND ({where_clause})
                ORDER BY published_at DESC
                LIMIT {limit}
            """)
            
            result = conn.execute(query)
            rows = result.fetchall()
            
            episodes = []
            for row in rows:
                episode_dict = {
                    'id': row[0],
                    'title': row[1],
                    'podcast_feed_name': row[2],
                    'transcript': row[3],
                    'summary': row[4]
                }
                
                # Parse JSONB
                if episode_dict['transcript'] and isinstance(episode_dict['transcript'], str):
                    try:
                        episode_dict['transcript'] = json.loads(episode_dict['transcript'])
                    except:
                        pass
                
                if episode_dict['summary'] and isinstance(episode_dict['summary'], str):
                    try:
                        episode_dict['summary'] = json.loads(episode_dict['summary'])
                    except:
                        pass
                
                episodes.append(episode_dict)
            
            return episodes
    
    def answer_question(self, question: str, episodes: List[Dict[str, Any]] = None, max_context_chars: int = 100000) -> Dict[str, Any]:
        """
        Answer a question using relevant podcast transcripts.
        
        Args:
            question: User's question
            episodes: List of relevant episodes (if None, will search for them)
            max_context_chars: Maximum characters to include in context
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Find relevant episodes if not provided
        if episodes is None:
            episodes = self.find_relevant_podcasts(question, limit=5)
        
        if not episodes:
            return {
                'answer': "I couldn't find any relevant podcast episodes to answer your question. Please try rephrasing or check if transcripts are available.",
                'sources': [],
                'episodes_used': 0,
                'error': None
            }
        
        # Extract transcripts
        transcripts_text = []
        sources = []
        
        for episode in episodes:
            transcript = episode.get('transcript')
            if not transcript:
                continue
            
            # Extract text from transcript JSONB
            if isinstance(transcript, dict):
                text_content = transcript.get('text', '')
            elif isinstance(transcript, str):
                try:
                    transcript_dict = json.loads(transcript)
                    text_content = transcript_dict.get('text', '') if isinstance(transcript_dict, dict) else ''
                except:
                    text_content = transcript
            else:
                text_content = str(transcript)
            
            if text_content:
                transcripts_text.append({
                    'text': text_content,
                    'title': episode.get('title', 'Unknown'),
                    'feed': episode.get('podcast_feed_name', 'Unknown'),
                    'id': episode.get('id')
                })
                sources.append({
                    'title': episode.get('title', 'Unknown'),
                    'feed': episode.get('podcast_feed_name', 'Unknown'),
                    'id': episode.get('id')
                })
        
        if not transcripts_text:
            return {
                'answer': "I found relevant episodes but couldn't extract transcript text. Please ensure episodes are transcribed.",
                'sources': sources,
                'episodes_used': len(sources),
                'error': 'No transcript text available'
            }
        
        # Combine transcripts, chunk if needed
        combined_text = "\n\n---\n\n".join([
            f"[Episode: {t['title']}]\n{t['text']}"
            for t in transcripts_text
        ])
        
        # Chunk if too large
        chunks = self._chunk_text(combined_text, max_chunk_size=max_context_chars)
        
        # Answer using first chunk (or iterate if needed)
        context = chunks[0] if chunks else combined_text[:max_context_chars]
        
        # Create prompt for answering
        answer_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI assistant that answers questions based on podcast transcripts.
Use the provided transcript excerpts to answer the user's question accurately.
Cite specific episodes when referencing information.
If the answer isn't in the transcripts, say so clearly."""),
            ("user", """Question: {question}

Transcript excerpts from relevant podcast episodes:
{context}

Please provide a comprehensive answer based on the transcripts above. Cite specific episodes when possible.""")
        ])
        
        try:
            chain = answer_prompt | self.llm | StrOutputParser()
            answer = chain.invoke({
                "question": question,
                "context": context
            })
            
            return {
                'answer': answer,
                'sources': sources,
                'episodes_used': len(sources),
                'context_length': len(context),
                'error': None
            }
        
        except Exception as e:
            return {
                'answer': f"I encountered an error while generating an answer: {str(e)}",
                'sources': sources,
                'episodes_used': len(sources),
                'error': str(e)
            }
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Complete query pipeline: find relevant podcasts and answer question.
        
        Args:
            question: User's question
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Find relevant episodes
        episodes = self.find_relevant_podcasts(question, limit=5)
        
        # Answer question
        result = self.answer_question(question, episodes=episodes)
        
        return result

