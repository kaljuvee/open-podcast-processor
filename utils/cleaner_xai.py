"""LLM-based transcript cleaning and summarization using XAI API with LangChain."""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from utils.database import P3Database
from utils.config import get_api_key, get_grok_model


class TranscriptCleaner:
    def __init__(self, db: P3Database, api_key: str = None, model: str = None):
        """
        Initialize XAI cleaner with LangChain.
        
        Args:
            db: Database instance
            api_key: XAI API key (defaults to environment/secrets)
            model: XAI model to use (defaults to GROK_MODEL from .env or grok-2-1212)
        """
        self.db = db
        self.api_key = api_key or get_api_key()
        self.model = model or get_grok_model()
        
        # Initialize LangChain ChatOpenAI with XAI
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url="https://api.x.ai/v1",
            temperature=0.2,
            max_tokens=4000
        )

    def generate_summary(self, episode_id: int) -> Optional[Dict[str, Any]]:
        """Generate structured summary of an episode."""
        # Get transcript segments
        segments = self.db.get_transcripts_for_episode(episode_id)
        full_text = "\n".join(segment['text'] for segment in segments)
        
        if not full_text.strip():
            return None
        
        # Generate structured summary using XAI
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
        """Generate structured summary using XAI."""
        prompt = """Analyze this podcast transcript and extract structured information in JSON format:

{
  "key_topics": ["topic1", "topic2", ...],
  "themes": ["theme1", "theme2", ...],  
  "quotes": ["notable quote 1", "notable quote 2", ...],
  "startups": ["company1", "company2", ...],
  "summary": "Brief 2-3 sentence summary"
}

Guidelines:
- key_topics: Main subjects discussed (3-5 topics)
- themes: Broader themes or patterns (2-4 themes)  
- quotes: Memorable, insightful quotes (2-3 max)
- startups: Any companies, startups, or brands mentioned
- summary: Concise overview of the episode

Transcript:
""" + text

        try:
            # Use LangChain for XAI API access
            messages = [
                SystemMessage(content="You are an expert at analyzing podcast content. Return valid JSON only."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Extract JSON from response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            
            return None
            
        except Exception as e:
            print(f"XAI summarization failed: {e}")
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
