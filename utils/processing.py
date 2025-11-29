"""
Processing utilities for transcribing and summarizing episodes.
Extracted from Streamlit pages.
"""

from typing import Dict, List, Optional, Tuple
from utils.postgres_db import PostgresDB
from utils.transcriber_groq import AudioTranscriber
from utils.cleaner_groq import TranscriptCleaner
from utils.config import get_groq_api_key


def transcribe_episode(episode_id: int, db: PostgresDB) -> Tuple[bool, Optional[str]]:
    """
    Transcribe a single episode.
    
    Args:
        episode_id: ID of the episode to transcribe
        db: Database instance
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        api_key = get_groq_api_key()
        transcriber = AudioTranscriber(db, api_key=api_key)
        success = transcriber.transcribe_episode(episode_id)
        
        if success:
            return True, None
        else:
            return False, "Transcription failed"
    except Exception as e:
        return False, str(e)


def summarize_episode(episode_id: int, db: PostgresDB) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Summarize a single episode.
    
    Args:
        episode_id: ID of the episode to summarize
        db: Database instance
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str], summary: Optional[Dict])
    """
    try:
        api_key = get_groq_api_key()
        cleaner = TranscriptCleaner(db, api_key=api_key)
        summary = cleaner.generate_summary(episode_id)
        
        if summary:
            return True, None, summary
        else:
            return False, "Summarization failed", None
    except Exception as e:
        return False, str(e), None


def process_all_episodes(db: PostgresDB) -> Dict[str, int]:
    """
    Process all pending episodes (transcribe downloaded, summarize transcribed).
    
    Args:
        db: Database instance
        
    Returns:
        Dictionary with counts: {
            'transcribed': int,
            'summarized': int,
            'errors': int
        }
    """
    results = {
        'transcribed': 0,
        'summarized': 0,
        'errors': 0
    }
    
    api_key = get_groq_api_key()
    
    # Step 1: Transcribe downloaded episodes
    downloaded = db.get_episodes_by_status('downloaded')
    if downloaded:
        transcriber = AudioTranscriber(db, api_key=api_key)
        for episode in downloaded:
            try:
                if transcriber.transcribe_episode(episode['id']):
                    results['transcribed'] += 1
                else:
                    results['errors'] += 1
            except Exception:
                results['errors'] += 1
    
    # Step 2: Summarize transcribed episodes
    transcribed = db.get_episodes_by_status('transcribed')
    if transcribed:
        cleaner = TranscriptCleaner(db, api_key=api_key)
        for episode in transcribed:
            try:
                summary = cleaner.generate_summary(episode['id'])
                if summary:
                    results['summarized'] += 1
                else:
                    results['errors'] += 1
            except Exception:
                results['errors'] += 1
    
    return results

