"""Audio transcription using XAI API with LangChain and chunking support."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from utils.database import P3Database
from utils.config import get_api_key
from utils.audio_chunking import chunk_audio_file, cleanup_chunks, get_audio_size_mb, MAX_CHUNK_SIZE_MB


class AudioTranscriber:
    def __init__(self, db: P3Database, api_key: str = None):
        """
        Initialize XAI transcriber with LangChain.
        
        Args:
            db: Database instance
            api_key: XAI API key (defaults to environment/secrets)
        """
        self.db = db
        self.api_key = api_key or get_api_key()
        
        # Initialize OpenAI-compatible client for XAI (still needed for audio)
        from openai import OpenAI
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )

    def transcribe_audio_chunk(self, audio_path: Path, offset_seconds: float = 0.0) -> Optional[Dict[str, Any]]:
        """
        Transcribe a single audio chunk using XAI API.
        
        Args:
            audio_path: Path to audio chunk file
            offset_seconds: Time offset to add to timestamps (for chunking)
            
        Returns:
            Dictionary with transcription results
        """
        try:
            file_size_mb = get_audio_size_mb(audio_path)
            
            # Check file size
            if file_size_mb > MAX_CHUNK_SIZE_MB:
                print(f"Warning: Chunk {audio_path.name} is {file_size_mb:.1f}MB, may still be too large")
            
            with open(audio_path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # Convert XAI response to our format with offset
            segments = []
            if hasattr(response, 'segments') and response.segments:
                for segment in response.segments:
                    segments.append({
                        'start': segment.get('start', 0) + offset_seconds,
                        'end': segment.get('end', 0) + offset_seconds,
                        'text': segment.get('text', '').strip(),
                        'speaker': None,
                        'confidence': 1.0
                    })
            else:
                # Fallback if no segments
                segments.append({
                    'start': offset_seconds,
                    'end': offset_seconds,
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
            print(f"XAI transcription failed for chunk {audio_path.name}: {e}")
            return None

    def transcribe_audio(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio using XAI API with automatic chunking for large files.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with transcription results
        """
        audio_path_obj = Path(audio_path)
        
        if not audio_path_obj.exists():
            print(f"Audio file not found: {audio_path}")
            return None
        
        # Check if chunking is needed
        file_size_mb = get_audio_size_mb(audio_path_obj)
        
        # Chunk the audio if needed
        chunks = chunk_audio_file(audio_path_obj)
        
        if not chunks:
            print("Failed to create audio chunks")
            return None
        
        # If single chunk (original file), transcribe directly
        if len(chunks) == 1 and chunks[0][0] == audio_path_obj:
            return self.transcribe_audio_chunk(audio_path_obj, offset_seconds=0.0)
        
        # Transcribe each chunk
        print(f"Transcribing {len(chunks)} audio chunk(s)...")
        all_segments = []
        all_text_parts = []
        language = 'en'
        
        try:
            for idx, (chunk_path, start_time, end_time) in enumerate(chunks):
                print(f"  Processing chunk {idx + 1}/{len(chunks)} ({start_time:.0f}s - {end_time:.0f}s)...")
                
                chunk_result = self.transcribe_audio_chunk(chunk_path, offset_seconds=start_time)
                
                if chunk_result:
                    all_segments.extend(chunk_result['segments'])
                    all_text_parts.append(chunk_result['text'])
                    if chunk_result.get('language'):
                        language = chunk_result['language']
                else:
                    print(f"    ⚠️  Chunk {idx + 1} transcription failed")
            
            # Cleanup temporary chunks
            cleanup_chunks(chunks)
            
            if not all_segments:
                print("No segments transcribed from any chunk")
                return None
            
            # Merge results
            full_text = " ".join(all_text_parts)
            
            return {
                'segments': all_segments,
                'language': language,
                'text': full_text,
                'provider': 'xai',
                'chunked': len(chunks) > 1
            }
            
        except Exception as e:
            print(f"Error during chunked transcription: {e}")
            # Cleanup on error
            cleanup_chunks(chunks)
            return None

    def transcribe_episode(self, episode_id: int) -> bool:
        """Transcribe a single episode and store results."""
        # Get episode by ID (works for any status)
        episode = self.db.get_episode_by_id(episode_id)
        
        if not episode:
            print(f"Episode {episode_id} not found")
            return False
        
        # Check if already transcribed
        if episode.get('status') == 'transcribed' or episode.get('status') == 'processed':
            print(f"Episode {episode_id} already transcribed")
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
