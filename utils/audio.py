"""
Audio processing utilities.
Checks for ffmpeg and provides audio processing functions.
"""

import subprocess
from pathlib import Path
from typing import Optional, Tuple


def check_ffmpeg_installed() -> Tuple[bool, Optional[str]]:
    """
    Check if ffmpeg is installed and available.
    
    Returns:
        Tuple of (is_installed: bool, version: Optional[str])
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Extract version from first line
            version_line = result.stdout.split('\n')[0]
            return True, version_line
        return False, None
    except FileNotFoundError:
        return False, None
    except Exception as e:
        return False, str(e)


def normalize_audio(input_path: Path, output_path: Path, sample_rate: int = 16000) -> bool:
    """
    Normalize audio file using ffmpeg.
    Works in Streamlit subprocess mode.
    
    Args:
        input_path: Path to input audio file
        output_path: Path to output audio file
        sample_rate: Target sample rate (default: 16000 for Whisper)
        
    Returns:
        True if successful, False otherwise
    """
    if not check_ffmpeg_installed()[0]:
        return False
    
    try:
        cmd = [
            'ffmpeg', '-y',  # overwrite existing files
            '-i', str(input_path),
            '-ar', str(sample_rate),  # sample rate
            '-ac', '1',  # mono
            '-c:a', 'pcm_s16le',  # PCM 16-bit little-endian
            '-af', 'loudnorm',  # normalize audio levels
            str(output_path)
        ]
        
        # Works in Streamlit subprocess mode - uses system ffmpeg
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=600  # 10 minute timeout for large files
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False

