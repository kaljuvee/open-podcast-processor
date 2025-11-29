"""
Audio chunking utilities for handling large audio files.
Splits audio into smaller chunks to avoid API size limits.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional
from utils.audio import check_ffmpeg_installed


# Maximum file size for XAI Whisper API (approximately 25MB or ~25 minutes)
# We'll chunk files larger than 20MB to be safe
MAX_CHUNK_SIZE_MB = 20
MAX_CHUNK_DURATION_SECONDS = 20 * 60  # 20 minutes


def get_audio_duration(audio_path: Path) -> Optional[float]:
    """
    Get audio file duration in seconds using ffprobe.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Duration in seconds, or None if error
    """
    if not check_ffmpeg_installed()[0]:
        return None
    
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    
    return None


def get_audio_size_mb(audio_path: Path) -> float:
    """
    Get audio file size in MB.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Size in MB
    """
    if not audio_path.exists():
        return 0.0
    return audio_path.stat().st_size / (1024 * 1024)


def chunk_audio_file(
    audio_path: Path,
    chunk_duration: int = MAX_CHUNK_DURATION_SECONDS,
    overlap_seconds: int = 5
) -> List[Tuple[Path, float, float]]:
    """
    Split audio file into chunks using ffmpeg.
    
    Args:
        audio_path: Path to input audio file
        chunk_duration: Duration of each chunk in seconds
        overlap_seconds: Overlap between chunks in seconds (for context)
        
    Returns:
        List of tuples: [(chunk_path, start_time, end_time), ...]
    """
    if not check_ffmpeg_installed()[0]:
        return []
    
    # Check if chunking is needed
    file_size_mb = get_audio_size_mb(audio_path)
    duration = get_audio_duration(audio_path)
    
    # If file is small enough, return single chunk
    if file_size_mb < MAX_CHUNK_SIZE_MB and (duration is None or duration < MAX_CHUNK_DURATION_SECONDS):
        return [(audio_path, 0.0, duration or 0.0)]
    
    chunks = []
    temp_dir = tempfile.mkdtemp(prefix="audio_chunks_")
    
    try:
        if duration is None:
            # Fallback: estimate duration from file size (rough estimate)
            # Assume ~1MB per minute for compressed audio
            estimated_duration = file_size_mb * 60
            duration = estimated_duration
        
        start_time = 0.0
        chunk_index = 0
        
        while start_time < duration:
            end_time = min(start_time + chunk_duration, duration)
            
            # Create chunk filename
            chunk_path = Path(temp_dir) / f"chunk_{chunk_index:04d}.mp3"
            
            # Extract chunk using ffmpeg
            cmd = [
                'ffmpeg', '-y',
                '-i', str(audio_path),
                '-ss', str(start_time),
                '-t', str(end_time - start_time),
                '-acodec', 'copy',  # Copy codec to avoid re-encoding
                str(chunk_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0 and chunk_path.exists():
                chunks.append((chunk_path, start_time, end_time))
                chunk_index += 1
            else:
                print(f"Warning: Failed to create chunk at {start_time}s: {result.stderr}")
            
            # Move to next chunk with overlap
            start_time = end_time - overlap_seconds
            
            # Prevent infinite loop
            if start_time >= duration:
                break
        
        return chunks
        
    except Exception as e:
        print(f"Error chunking audio: {e}")
        # Cleanup on error
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        return []


def cleanup_chunks(chunks: List[Tuple[Path, float, float]]):
    """
    Clean up temporary chunk files.
    
    Args:
        chunks: List of chunk tuples from chunk_audio_file()
    """
    import shutil
    
    if not chunks:
        return
    
    # Get temp directory from first chunk
    temp_dir = chunks[0][0].parent
    
    try:
        # Delete all chunks
        for chunk_path, _, _ in chunks:
            if chunk_path.exists() and chunk_path != chunks[0][0]:  # Don't delete original
                chunk_path.unlink()
        
        # Remove temp directory if it's a temp dir
        if 'audio_chunks_' in str(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        print(f"Warning: Error cleaning up chunks: {e}")

