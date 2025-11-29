"""
Configuration utility for loading environment variables.
Uses python-dotenv to load from .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

def get_groq_api_key() -> str:
    """
    Get Groq API key from environment variables (loaded via python-dotenv).
    
    Returns:
        str: Groq API key
        
    Raises:
        ValueError: If API key is not found
    """
    api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. Please set it in:\n"
            "  - .env file: GROQ_API_KEY=your-key-here\n"
            "  - Environment variable: export GROQ_API_KEY='your-key-here'"
        )
    
    return api_key


def get_groq_model() -> str:
    """
    Get Groq model name from environment variables.
    Defaults to llama-3.3-70b-versatile (largest context window: 131k tokens).
    
    Returns:
        str: Groq model name (e.g., 'llama-3.3-70b-versatile', 'llama-3.1-8b-instant')
    """
    model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    return model


def get_groq_whisper_model() -> str:
    """
    Get Groq Whisper model name from environment variables.
    Defaults to whisper-large-v3-turbo.
    
    Returns:
        str: Whisper model name (e.g., 'whisper-large-v3-turbo', 'whisper-large-v3')
    """
    model = os.getenv('GROQ_WHISPER_MODEL', 'whisper-large-v3-turbo')
    return model


def get_groq_temperature() -> float:
    """
    Get Groq temperature for reasoning/summarization from environment variables.
    Defaults to 0.2.
    
    Returns:
        float: Temperature value (0.0 to 2.0)
    """
    temp_str = os.getenv('GROQ_TEMPERATURE', '0.2')
    try:
        return float(temp_str)
    except ValueError:
        return 0.2


def get_groq_topic_temperature() -> float:
    """
    Get Groq temperature for topic analysis from environment variables.
    Defaults to 0.3.
    
    Returns:
        float: Temperature value (0.0 to 2.0)
    """
    temp_str = os.getenv('GROQ_TOPIC_TEMPERATURE', '0.3')
    try:
        return float(temp_str)
    except ValueError:
        return 0.3


def get_groq_max_tokens() -> int:
    """
    Get Groq max_tokens for responses from environment variables.
    Defaults to 4000.
    
    Returns:
        int: Maximum tokens in response
    """
    tokens_str = os.getenv('GROQ_MAX_TOKENS', '4000')
    try:
        return int(tokens_str)
    except ValueError:
        return 4000


def get_db_url() -> str:
    """
    Get PostgreSQL database URL from environment variables.
    
    Returns:
        str: Database URL (e.g., 'postgresql://user:pass@localhost:5432/dbname')
        
    Raises:
        ValueError: If DB_URL is not found
    """
    db_url = os.getenv('DB_URL')
    
    if not db_url:
        raise ValueError(
            "DB_URL not found. Please set it in:\n"
            "  - .env file: DB_URL=postgresql://user:password@localhost:5432/dbname\n"
            "  - Environment variable: export DB_URL='postgresql://...'"
        )
    
    return db_url


def get_db_schema() -> str:
    """
    Get PostgreSQL database schema name from environment variables.
    Defaults to 'public'.
    
    Returns:
        str: Schema name
    """
    schema = os.getenv('DB_SCHEMA', 'public')
    return schema


# Backward compatibility aliases
def get_api_key() -> str:
    """Backward compatibility: returns Groq API key."""
    return get_groq_api_key()


def get_grok_model() -> str:
    """Backward compatibility: returns Groq model."""
    return get_groq_model()
