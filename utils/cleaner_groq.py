"""LLM-based transcript cleaning and summarization using Groq via LangChain."""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from utils.database import P3Database
from utils.config import get_groq_api_key, get_groq_model, get_groq_temperature, get_groq_max_tokens


class TranscriptCleaner:
    def __init__(self, db: P3Database, api_key: str = None, model: str = None):
        """
        Initialize Groq cleaner with LangChain.
        
        Args:
            db: Database instance
            api_key: Groq API key (defaults to environment)
            model: Groq model to use (defaults to GROQ_MODEL from .env or llama-3.3-70b-versatile)
        """
        self.db = db
        self.api_key = api_key or get_groq_api_key()
        self.model = model or get_groq_model()
        self.temperature = get_groq_temperature()
        self.max_tokens = get_groq_max_tokens()
        
        # Initialize LangChain ChatGroq
        self.llm = ChatGroq(
            model_name=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            groq_api_key=self.api_key
        )
        
        # Set up JSON parser for structured output
        self.parser = JsonOutputParser(
            pydantic_object={
                "type": "object",
                "properties": {
                    "key_topics": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "themes": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "quotes": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "startups": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "summary": {"type": "string"}
                },
                "required": ["key_topics", "themes", "quotes", "startups", "summary"]
            }
        )
        
        # Set up prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at analyzing podcast content. 
Extract structured information from the transcript and return valid JSON only.

Return JSON with this structure:
{{
  "key_topics": ["topic1", "topic2", ...],
  "themes": ["theme1", "theme2", ...],
  "quotes": ["notable quote 1", "notable quote 2", ...],
  "startups": ["company1", "company2", ...],
  "summary": "Brief 2-3 sentence summary"
}}

Guidelines:
- key_topics: Main subjects discussed (3-5 topics)
- themes: Broader themes or patterns (2-4 themes)
- quotes: Memorable, insightful quotes (2-3 max)
- startups: Any companies, startups, or brands mentioned
- summary: Concise overview of the episode

Return ONLY valid JSON, no other text."""),
            ("user", "Transcript:\n{transcript}")
        ])

    def generate_summary(self, episode_id: int) -> Optional[Dict[str, Any]]:
        """Generate structured summary of an episode."""
        # Get transcript segments
        segments = self.db.get_transcripts_for_episode(episode_id)
        full_text = "\n".join(segment['text'] for segment in segments)
        
        if not full_text.strip():
            return None
        
        # Generate structured summary using Groq
        summary_data = self._generate_structured_summary(full_text)
        
        if summary_data:
            # Store in database
            self.db.add_summary(
                episode_id=episode_id,
                key_topics=summary_data.get('key_topics', []),
                themes=summary_data.get('themes', []),
                quotes=summary_data.get('quotes', []),
                startups=summary_data.get('startups', []),
                full_summary=summary_data.get('summary', ''),
                digest_date=datetime.now()
            )
            
            # Update episode status
            self.db.update_episode_status(episode_id, 'processed')
        
        return summary_data

    def _generate_structured_summary(self, text: str) -> Optional[Dict[str, Any]]:
        """Generate structured summary using Groq via LangChain."""
        try:
            # Truncate text if too long (keep within context window)
            # llama-3.3-70b-versatile has 131k tokens, roughly 100k words
            max_chars = 500000  # ~100k words
            if len(text) > max_chars:
                print(f"Warning: Transcript too long ({len(text)} chars), truncating to {max_chars}")
                text = text[:max_chars] + "... [truncated]"
            
            # Create chain: prompt -> llm -> parser
            chain = self.prompt | self.llm | self.parser
            
            # Invoke chain
            result = chain.invoke({"transcript": text})
            
            return result
            
        except Exception as e:
            print(f"Groq summarization failed: {e}")
            import traceback
            traceback.print_exc()
            return self._basic_extraction(text)

    def _basic_extraction(self, text: str) -> Dict[str, Any]:
        """Basic keyword extraction as fallback."""
        words = text.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 4 and word.isalpha():
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get most frequent words as topics
        key_topics = [word for word, freq in 
                     sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]]
        
        # Simple company extraction
        potential_companies = []
        for word in text.split():
            if any(word.lower().endswith(suffix) for suffix in ['inc', 'corp', 'llc', 'labs']):
                potential_companies.append(word)
        
        return {
            "key_topics": key_topics,
            "themes": ["general discussion"],
            "quotes": [],
            "startups": list(set(potential_companies)),
            "summary": "Podcast episode discussion covering various topics."
        }

    def process_all_transcribed(self) -> int:
        """Process all episodes with 'transcribed' status."""
        episodes = self.db.get_episodes_by_status('transcribed')
        processed_count = 0
        
        for episode in episodes:
            print(f"Processing summary for: {episode['title']}")
            if self.generate_summary(episode['id']):
                processed_count += 1
                print(f"✓ Processed: {episode['title']}")
            else:
                print(f"✗ Failed to process: {episode['title']}")
        
        return processed_count

