"""
Open Podcast Processor - Streamlit Home Page
Automated podcast processing with XAI API
"""

import streamlit as st
import os
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Open Podcast Processor",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🎙️ Open Podcast Processor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated podcast processing with XAI API</div>', unsafe_allow_html=True)

# Check API key
api_key = os.getenv("XAI_API_KEY")
if not api_key:
    st.error("⚠️ XAI_API_KEY not found in environment variables. Please set it to use the application.")
    st.info("You can set it by running: `export XAI_API_KEY=your_api_key_here`")
else:
    st.success("✅ XAI API Key configured")

# Main content
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🚀 Key Features")
    st.markdown("""
    <div class="feature-box">
    <ul>
        <li><b>🎧 Smart RSS Feed Management</b> - Monitor and download podcast episodes</li>
        <li><b>🚀 XAI-Powered Transcription</b> - Fast and accurate speech-to-text</li>
        <li><b>🧠 AI Summarization</b> - Extract topics, themes, quotes, and companies</li>
        <li><b>💾 DuckDB Storage</b> - Efficient data storage and querying</li>
        <li><b>📊 Interactive Viewing</b> - Browse and explore processed content</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("### 📊 Pipeline Overview")
    st.markdown("""
    <div class="feature-box">
    <b>Processing Pipeline:</b>
    <ol>
        <li>📥 <b>RSS Feed</b> → Download episodes from configured feeds</li>
        <li>🎵 <b>Audio Processing</b> → ffmpeg normalization</li>
        <li>🎯 <b>XAI Transcription</b> → Convert speech to text</li>
        <li>🧠 <b>XAI Summarization</b> → Extract structured insights</li>
        <li>💾 <b>DuckDB Storage</b> → Store and query results</li>
        <li>📄 <b>Export/View</b> → Access via Streamlit interface</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)

# Quick stats
st.markdown("### 📈 Quick Stats")

# Initialize database to get stats
try:
    from p3.database import P3Database
    db = P3Database()
    
    # Get episode counts by status
    downloaded = len(db.get_episodes_by_status('downloaded'))
    transcribed = len(db.get_episodes_by_status('transcribed'))
    processed = len(db.get_episodes_by_status('processed'))
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📥 Downloaded", downloaded)
    with col2:
        st.metric("🎯 Transcribed", transcribed)
    with col3:
        st.metric("✅ Processed", processed)
    with col4:
        total = downloaded + transcribed + processed
        st.metric("📊 Total Episodes", total)
    
    db.close()
except Exception as e:
    st.info("💡 No database found yet. Start by configuring RSS feeds and downloading episodes!")

# Getting Started
st.markdown("### 🎯 Getting Started")
st.markdown("""
1. **Configure Feeds** - Go to the RSS Feeds page to add podcast feeds
2. **Download Episodes** - Fetch episodes from your configured feeds
3. **Process Audio** - Transcribe and summarize episodes using XAI
4. **View Results** - Browse processed content and export digests
""")

# Sidebar
with st.sidebar:
    st.markdown("### 📚 Navigation")
    st.markdown("""
    - **🏠 Home** - Overview and stats
    - **📡 RSS Feeds** - Manage podcast feeds
    - **⚙️ Processing** - Transcribe and summarize
    - **📊 View Data** - Browse processed content
    """)
    
    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("""
    **Open Podcast Processor** is an automated podcast processing system that uses XAI API 
    for transcription and summarization.
    
    Built with:
    - Streamlit
    - XAI API (Whisper + Grok)
    - DuckDB
    - FFmpeg
    """)
    
    st.markdown("---")
    st.markdown("### 🙏 Acknowledgements")
    st.markdown("""
    Inspired by [Parakeet Podcast Processor](https://github.com/haasonsaas/parakeet-podcast-processor) 
    and the innovative work of [Tomasz Tunguz](https://tomtunguz.com).
    """)
