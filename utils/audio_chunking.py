"""
Audio chunking utilities for handling large audio files.
Splits audio into smaller chunks to avoid API size limits.
"""

import subprocess
import re
from pathlib import Path
from typing import List, Tuple, Optional
from utils.audio import check_ffmpeg_installed


def create_slug(text: str, max_length: int = 100) -> str:
    """
    Create a URL-friendly slug from text.
    
    Args:
        text: Text to convert to slug
        max_length: Maximum length of slug
        
    Returns:
        Slug string
    """
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove all non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    # Replace multiple hyphens with single hyphen
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')
    return slug


# Maximum file size for Groq Whisper API (supports up to 100MB)
# We'll chunk files larger than 80MB to be safe (leave margin for API)
MAX_CHUNK_SIZE_MB = 80
# For duration: if file is small (< 50MB), allow longer chunks (up to 60 minutes)
# If file is large, use shorter chunks to stay under size limit
MAX_CHUNK_DURATION_SECONDS_SMALL = 60 * 60  # 60 minutes for small files
MAX_CHUNK_DURATION_SECONDS_LARGE = 30 * 60  # 30 minutes for large files


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
    chunk_duration: int = None,
    overlap_seconds: int = 5
) -> List[Tuple[Path, float, float]]:
    """
    Split audio file into chunks using ffmpeg.
    Optimized for Groq API: supports up to 100MB files.
    
    Args:
        audio_path: Path to input audio file
        chunk_duration: Duration of each chunk in seconds (auto-determined if None)
        overlap_seconds: Overlap between chunks in seconds (for context)
        
    Returns:
        List of tuples: [(chunk_path, start_time, end_time), ...]
    """
    if not check_ffmpeg_installed()[0]:
        return []
    
    # Check if chunking is needed
    file_size_mb = get_audio_size_mb(audio_path)
    duration = get_audio_duration(audio_path)
    
    # Groq Whisper supports up to 100MB files
    # If file is under 80MB, process as single chunk regardless of duration
    # This handles compressed audio files that are small but long (like your 18MB, 105min file)
    if file_size_mb < MAX_CHUNK_SIZE_MB:
        if duration:
            print(f"   ✅ File is {file_size_mb:.1f}MB, {duration/60:.1f}min (under {MAX_CHUNK_SIZE_MB}MB limit)")
            print(f"      Processing as single chunk (Groq supports up to 100MB)")
        else:
            print(f"   ✅ File is {file_size_mb:.1f}MB (under {MAX_CHUNK_SIZE_MB}MB limit), processing as single chunk")
        return [(audio_path, 0.0, duration or 0.0)]
    
    # File is large (> 80MB), need to chunk by size
    # Determine chunk duration based on file size
    # Small files (< 50MB) can use longer chunks
    # Large files need shorter chunks to stay under size limit
    if chunk_duration is None:
        if file_size_mb < 50:
            chunk_duration = MAX_CHUNK_DURATION_SECONDS_SMALL
        else:
            chunk_duration = MAX_CHUNK_DURATION_SECONDS_LARGE
    
    print(f"   ⚠️  File is {file_size_mb:.1f}MB (over {MAX_CHUNK_SIZE_MB}MB limit), chunking required")
    
    chunks = []
    # Create slug-based temp directory next to the audio file
    audio_slug = create_slug(audio_path.stem)
    temp_dir = audio_path.parent / f"chunks_{audio_slug}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    print(f"   📁 Chunk directory: {temp_dir}")
    
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
        # Keep temp directory for debugging (no cleanup)
        print(f"   ℹ️  Temp directory kept: {temp_dir}")
        return []


def cleanup_chunks(chunks: List[Tuple[Path, float, float]]):
    """
    Clean up temporary chunk files.
    
    NOTE: Cleanup is disabled - chunks are kept for debugging.
    To enable cleanup later, uncomment the code below.
    
    Args:
        chunks: List of chunk tuples from chunk_audio_file()
    """
    # Cleanup disabled - keep chunks for debugging
    if chunks:
        temp_dir = chunks[0][0].parent
        print(f"   ℹ️  Chunks kept in: {temp_dir} (cleanup disabled)")
    return
    
    # Code below is disabled - uncomment to enable cleanup
    # import shutil
    # 
    # if not chunks:
    #     return
    # 
    # # Get temp directory from first chunk
    # temp_dir = chunks[0][0].parent
    # 
    # try:
    #     # Delete all chunks
    #     for chunk_path, _, _ in chunks:
    #         if chunk_path.exists() and chunk_path != chunks[0][0]:  # Don't delete original
    #             chunk_path.unlink()
    #     
    #     # Remove temp directory if it's a temp dir
    #     if 'chunks_' in str(temp_dir):
    #         shutil.rmtree(temp_dir, ignore_errors=True)
    # except Exception as e:
    #     print(f"Warning: Error cleaning up chunks: {e}")

