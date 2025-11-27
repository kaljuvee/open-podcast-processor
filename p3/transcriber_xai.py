"""Audio transcription using XAI API."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from openai import OpenAI

from .database import P3Database
from .config import get_api_key


class AudioTranscriber:
    def __init__(self, db: P3Database, api_key: str = None):
        """
        Initialize XAI transcriber.
        
        Args:
            db: Database instance
            api_key: XAI API key (defaults to environment/secrets)
        """
        self.db = db
        self.api_key = api_key or get_api_key()
        
        # Initialize OpenAI client with XAI base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )

    def transcribe_audio(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio using XAI API.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with transcription results
        """
        try:
            with open(audio_path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # Convert XAI response to our format
            segments = []
            if hasattr(response, 'segments') and response.segments:
                for segment in response.segments:
                    segments.append({
                        'start': segment.get('start', 0),
                        'end': segment.get('end', 0),
                        'text': segment.get('text', '').strip(),
                        'speaker': None,
                        'confidence': 1.0
                    })
            else:
                # Fallback if no segments
                segments.append({
                    'start': 0,
                    'end': 0,
                    'text': response.text,
                    'speaker': None,
                    'confidence': 1.0
                })
            
            return {
                'segments': segments,
                'language': getattr(response, 'language', 'en'),
                'text': response.text,
                'provider': 'xai'
            }
            
        except Exception as e:
            print(f"XAI transcription failed: {e}")
            return None

    def transcribe_episode(self, episode_id: int) -> bool:
        """Transcribe a single episode and store results."""
        episodes = self.db.get_episodes_by_status('downloaded')
        episode = next((ep for ep in episodes if ep['id'] == episode_id), None)
        
        if not episode:
            print(f"Episode {episode_id} not found or already processed")
            return False

        if not episode['file_path'] or not Path(episode['file_path']).exists():
            print(f"Audio file not found: {episode.get('file_path')}")
            return False

        print(f"Transcribing: {episode['title']}")
        
        result = self.transcribe_audio(episode['file_path'])
        
        if not result:
            return False

        # Store transcript segments in database
        self.db.add_transcript_segments(episode_id, result['segments'])
        
        # Update episode status
        self.db.update_episode_status(episode_id, 'transcribed')
        
        print(f"✓ Transcribed: {episode['title']}")
        return True

    def transcribe_all_pending(self) -> int:
        """Transcribe all episodes with 'downloaded' status."""
        episodes = self.db.get_episodes_by_status('downloaded')
        transcribed_count = 0
        
        for episode in episodes:
            if self.transcribe_episode(episode['id']):
                transcribed_count += 1
            
        return transcribed_count

    def get_full_transcript(self, episode_id: int) -> str:
        """Get the full transcript text for an episode."""
        segments = self.db.get_transcripts_for_episode(episode_id)
        return "\n".join(segment['text'] for segment in segments)
