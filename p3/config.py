"""
Configuration utility for loading environment variables.
Supports both .env files (local development) and Streamlit secrets (cloud deployment).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

def get_api_key() -> str:
    """
    Get XAI API key from environment or Streamlit secrets.
    
    Returns:
        str: XAI API key
        
    Raises:
        ValueError: If API key is not found
    """
    # Try Streamlit secrets first (for cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'XAI_API_KEY' in st.secrets:
            return st.secrets['XAI_API_KEY']
    except (ImportError, FileNotFoundError, KeyError):
        pass
    
    # Fall back to environment variable (for local development)
    api_key = os.getenv('XAI_API_KEY')
    
    if not api_key:
        raise ValueError(
            "XAI_API_KEY not found. Please set it in:\n"
            "  - Local: .env file or environment variable\n"
            "  - Streamlit Cloud: App settings → Secrets"
        )
    
    return api_key
