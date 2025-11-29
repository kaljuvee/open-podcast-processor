"""Audio transcription using Groq Whisper Large V3 Turbo with LangChain and chunking support."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
import time
from datetime import timedelta

from utils.postgres_db import PostgresDB
from utils.config import get_groq_api_key, get_groq_whisper_model
from utils.audio_chunking import chunk_audio_file, cleanup_chunks, get_audio_size_mb, get_audio_duration, MAX_CHUNK_SIZE_MB


class AudioTranscriber:
    def __init__(self, db: PostgresDB, api_key: str = None):
        """
        Initialize Groq transcriber with Whisper Large V3 Turbo.
        
        Args:
            db: Database instance
            api_key: Groq API key (defaults to environment)
        """
        self.db = db
        self.api_key = api_key or get_groq_api_key()
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = get_groq_whisper_model()

    def transcribe_audio_chunk(self, audio_path: Path, offset_seconds: float = 0.0, chunk_info: str = "") -> Optional[Dict[str, Any]]:
        """
        Transcribe a single audio chunk using Groq Whisper API.
        
        Args:
            audio_path: Path to audio chunk file
            offset_seconds: Time offset to add to timestamps (for chunking)
            chunk_info: Optional info string for progress display
            
        Returns:
            Dictionary with transcription results
        """
        try:
            file_size_mb = get_audio_size_mb(audio_path)
            duration = get_audio_duration(audio_path)
            
            # Check file size (Groq Whisper supports up to 100MB)
            if file_size_mb > 100:
                print(f"⚠️  Warning: Chunk {audio_path.name} is {file_size_mb:.1f}MB, exceeds 100MB limit")
                print(f"     This chunk will be skipped. Consider reducing chunk duration.")
                return None
            
            # Warn if chunk is very large (but still under limit)
            if file_size_mb > 80:
                print(f"⚠️  Warning: Chunk {audio_path.name} is {file_size_mb:.1f}MB, close to 100MB limit")
            
            # Estimate processing time
            # Groq Whisper processes at roughly 1-2x realtime (faster than realtime)
            # Conservative estimate: 0.5x realtime (2x faster)
            estimated_seconds = (duration or (file_size_mb * 60)) * 0.5 if duration else file_size_mb * 30
            
            print(f"  📤 Uploading chunk {chunk_info} ({file_size_mb:.1f}MB", end="")
            if duration:
                print(f", {int(duration//60)}m{int(duration%60)}s", end="")
            print(f")...")
            print(f"     ⏱️  Estimated processing time: ~{int(estimated_seconds)}s")
            
            start_time = time.time()
            
            # Use Groq Whisper API
            url = f"{self.base_url}/audio/transcriptions"
            
            upload_start = time.time()
            with open(audio_path, 'rb') as audio_file:
                files = {
                    'file': (audio_path.name, audio_file, 'audio/mpeg')
                }
                data = {
                    'model': self.model,
                    'response_format': 'verbose_json',
                    'timestamp_granularities[]': 'segment'
                }
                headers = {
                    'Authorization': f'Bearer {self.api_key}'
                }
                
                print(f"     🔄 Sending request to Groq API...")
                response = requests.post(url, files=files, data=data, headers=headers, timeout=600)
                upload_time = time.time() - upload_start
                
                print(f"     ✅ Upload complete ({upload_time:.1f}s)")
                print(f"     ⏳ Processing with {self.model}...")
                
                response.raise_for_status()
                result = response.json()
            
            processing_time = time.time() - start_time
            segments_count = len(result.get('segments', []))
            
            print(f"     ✅ Transcription complete! ({processing_time:.1f}s, {segments_count} segments)")
            if duration:
                speed_factor = duration / processing_time if processing_time > 0 else 0
                print(f"     ⚡ Processing speed: {speed_factor:.1f}x realtime")
            
            # Convert Groq response to our format with offset
            segments = []
            if 'segments' in result and result['segments']:
                for segment in result['segments']:
                    segments.append({
                        'start': segment.get('start', 0) + offset_seconds,
                        'end': segment.get('end', 0) + offset_seconds,
                        'text': segment.get('text', '').strip(),
                        'speaker': None,
                        'confidence': 1.0
                    })
            else:
                # Fallback if no segments
                text = result.get('text', '')
                segments.append({
                    'start': offset_seconds,
                    'end': offset_seconds,
                    'text': text,
                    'speaker': None,
                    'confidence': 1.0
                })
            
            return {
                'segments': segments,
                'language': result.get('language', 'en'),
                'text': result.get('text', ''),
                'provider': 'groq'
            }
            
        except Exception as e:
            print(f"Groq transcription failed for chunk {audio_path.name}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None

    def transcribe_audio(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio using Groq Whisper with automatic chunking for large files.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with transcription results
        """
        audio_path_obj = Path(audio_path)
        
        if not audio_path_obj.exists():
            print(f"❌ Audio file not found: {audio_path}")
            return None
        
        # Get file info
        file_size_mb = get_audio_size_mb(audio_path_obj)
        duration = get_audio_duration(audio_path_obj)
        
        print(f"\n📊 Audio File Analysis:")
        print(f"   File: {audio_path_obj.name}")
        print(f"   Size: {file_size_mb:.2f} MB")
        if duration:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            print(f"   Duration: {minutes}m{seconds}s ({duration:.1f}s)")
        else:
            print(f"   Duration: Unknown (estimating from size)")
            estimated_duration = file_size_mb * 60  # Rough estimate: 1MB per minute
            print(f"   Estimated: ~{int(estimated_duration//60)}m{int(estimated_duration%60)}s")
        
        # Chunk the audio if needed
        print(f"\n🔪 Checking if chunking is needed...")
        chunks = chunk_audio_file(audio_path_obj)
        
        if not chunks:
            print("❌ Failed to create audio chunks")
            return None
        
        total_chunks = len(chunks)
        needs_chunking = total_chunks > 1 or (total_chunks == 1 and chunks[0][0] != audio_path_obj)
        
        if needs_chunking:
            print(f"   ✅ File will be split into {total_chunks} chunk(s)")
            for idx, (chunk_path, start_time, end_time) in enumerate(chunks):
                chunk_duration = end_time - start_time
                chunk_size = get_audio_size_mb(chunk_path)
                print(f"      Chunk {idx + 1}: {int(start_time//60)}m{int(start_time%60)}s - {int(end_time//60)}m{int(end_time%60)}s ({chunk_size:.1f}MB)")
        else:
            print(f"   ✅ File is small enough, processing as single chunk")
        
        # If single chunk (original file), transcribe directly
        if len(chunks) == 1 and chunks[0][0] == audio_path_obj:
            print(f"\n🎙️  Starting transcription (single chunk)...")
            return self.transcribe_audio_chunk(audio_path_obj, offset_seconds=0.0, chunk_info="1/1")
        
        # Transcribe each chunk
        print(f"\n🎙️  Starting transcription ({total_chunks} chunk(s))...")
        all_segments = []
        all_text_parts = []
        language = 'en'
        total_start_time = time.time()
        
        try:
            for idx, (chunk_path, start_time, end_time) in enumerate(chunks):
                chunk_num = idx + 1
                chunk_info = f"{chunk_num}/{total_chunks}"
                
                print(f"\n📦 Processing chunk {chunk_info}:")
                print(f"   Time range: {int(start_time//60)}m{int(start_time%60)}s - {int(end_time//60)}m{int(end_time%60)}s")
                
                chunk_result = self.transcribe_audio_chunk(chunk_path, offset_seconds=start_time, chunk_info=chunk_info)
                
                if chunk_result:
                    all_segments.extend(chunk_result['segments'])
                    all_text_parts.append(chunk_result['text'])
                    if chunk_result.get('language'):
                        language = chunk_result['language']
                    print(f"   ✅ Chunk {chunk_num} completed")
                else:
                    print(f"   ❌ Chunk {chunk_num} transcription failed")
            
            # Cleanup temporary chunks
            print(f"\n🧹 Cleaning up temporary chunk files...")
            cleanup_chunks(chunks)
            
            if not all_segments:
                print("❌ No segments transcribed from any chunk")
                return None
            
            # Merge results
            print(f"\n🔗 Merging transcription results...")
            full_text = " ".join(all_text_parts)
            total_time = time.time() - total_start_time
            
            print(f"\n✅ Transcription Complete!")
            print(f"   Total time: {int(total_time//60)}m{int(total_time%60)}s ({total_time:.1f}s)")
            print(f"   Segments: {len(all_segments)}")
            print(f"   Text length: {len(full_text):,} characters")
            if duration:
                speed_factor = duration / total_time if total_time > 0 else 0
                print(f"   Overall speed: {speed_factor:.1f}x realtime")
            
            return {
                'segments': all_segments,
                'language': language,
                'text': full_text,
                'provider': 'groq',
                'chunked': len(chunks) > 1
            }
            
        except Exception as e:
            print(f"❌ Error during chunked transcription: {e}")
            import traceback
            traceback.print_exc()
            # Cleanup on error
            cleanup_chunks(chunks)
            return None

    def transcribe_episode(self, episode_id: int) -> bool:
        """Transcribe a single episode and store results."""
        episode_start_time = time.time()
        
        # Get episode by ID (works for any status)
        episode = self.db.get_episode_by_id(episode_id)
        
        if not episode:
            print(f"❌ Episode {episode_id} not found")
            return False
        
        # Check if already transcribed
        if episode.get('status') == 'transcribed' or episode.get('status') == 'processed':
            print(f"ℹ️  Episode {episode_id} already transcribed (status: {episode.get('status')})")
            return False

        # Get file path (PostgreSQL uses audio_file_path)
        file_path = episode.get('audio_file_path') or episode.get('file_path')
        if not file_path or not Path(file_path).exists():
            print(f"❌ Audio file not found: {file_path}")
            return False

        print(f"\n{'='*70}")
        print(f"🎙️  TRANSCRIBING EPISODE")
        print(f"{'='*70}")
        print(f"Episode ID: {episode_id}")
        print(f"Title: {episode['title']}")
        print(f"File: {file_path}")
        print(f"{'='*70}\n")
        
        result = self.transcribe_audio(file_path)
        
        if not result:
            print(f"\n❌ Transcription failed for episode {episode_id}")
            return False

        # Store transcript segments in PostgreSQL
        print(f"\n💾 Saving transcript to PostgreSQL...")
        self.db.add_transcript_segments(episode_id, result['segments'])
        
        # Update episode status
        self.db.update_episode_status(episode_id, 'transcribed')
        
        total_time = time.time() - episode_start_time
        print(f"\n{'='*70}")
        print(f"✅ EPISODE TRANSCRIBED SUCCESSFULLY")
        print(f"{'='*70}")
        print(f"Episode: {episode['title']}")
        print(f"Total processing time: {int(total_time//60)}m{int(total_time%60)}s")
        print(f"Segments saved: {len(result['segments'])}")
        print(f"{'='*70}\n")
        
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

