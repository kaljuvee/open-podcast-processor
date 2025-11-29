"""
Open Podcast Processor - Home Page
Streamlit application for automated podcast processing with XAI API
"""

import streamlit as st
from utils.postgres_db import PostgresDB
from utils.config import get_api_key

st.set_page_config(
    page_title="Open Podcast Processor",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .big-number {
        font-size: 48px;
        font-weight: bold;
        color: #1f77b4;
    }
    .workflow-step {
        padding: 20px;
        border-radius: 10px;
        background-color: #f0f2f6;
        margin: 10px 0;
    }
    .step-number {
        font-size: 32px;
        font-weight: bold;
        color: #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🎙️ Open Podcast Processor")
st.markdown("**Automated podcast processing with XAI API**")

# Check API key
try:
    api_key = get_api_key()
    st.success("✅ XAI API Key configured")
except ValueError as e:
    st.error(f"⚠️ {str(e)}")
    st.code("echo 'XAI_API_KEY=your-key-here' > .env")
    st.stop()

# Initialize database
try:
    db = PostgresDB()
except Exception as e:
    st.error(f"Failed to connect to PostgreSQL: {e}")
    st.info("Please ensure DB_URL is set in your .env file")
    st.stop()

# Get statistics
try:
    stats = db.get_stats()
    downloaded_count = stats.get('downloaded_count', 0)
    transcribed_count = stats.get('transcribed_count', 0)
    processed_count = stats.get('processed_count', 0)
    total_episodes = stats.get('total_podcasts', 0)
except Exception as e:
    st.warning(f"Could not load statistics: {e}")
    downloaded_count = transcribed_count = processed_count = total_episodes = 0

# Quick Stats at the top
st.markdown("### 📊 Quick Stats")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📥 Downloaded", downloaded_count, help="Episodes downloaded but not transcribed")
with col2:
    st.metric("🎯 Transcribed", transcribed_count, help="Episodes transcribed but not summarized")
with col3:
    st.metric("✅ Processed", processed_count, help="Episodes fully processed")
with col4:
    st.metric("📊 Total", total_episodes, help="All episodes in database")

st.markdown("---")

# Workflow Guide
st.markdown("## 🚀 Getting Started - 3 Easy Steps")

# Step 1: Download
st.markdown("""
<div class="workflow-step">
    <span class="step-number">1️⃣</span> <strong>Download Episodes</strong>
    <p>Go to <strong>📥 Download</strong> page → Select feeds → Click "Download Episodes"</p>
</div>
""", unsafe_allow_html=True)

if downloaded_count > 0:
    st.info(f"✅ You have {downloaded_count} episodes ready to transcribe!")
    if st.button("🎯 Go to Process Episodes →", type="primary"):
        st.switch_page("pages/1_Process.py")
else:
    st.warning("⚠️ No episodes downloaded yet. Start by downloading some episodes!")
    if st.button("📥 Go to Download →", type="primary"):
        st.switch_page("pages/2_Download.py")

# Step 2: Process
st.markdown("""
<div class="workflow-step">
    <span class="step-number">2️⃣</span> <strong>Process Episodes</strong>
    <p>Go to <strong>⚙️ Process</strong> page → Click "Process All" to transcribe and summarize</p>
</div>
""", unsafe_allow_html=True)

if transcribed_count > 0:
    st.info(f"✅ You have {transcribed_count} episodes ready to summarize!")

# Step 3: View Results
st.markdown("""
<div class="workflow-step">
    <span class="step-number">3️⃣</span> <strong>View Results</strong>
    <p>Go to <strong>📊 View Data</strong> page → Browse summaries, transcripts, and export data</p>
</div>
""", unsafe_allow_html=True)

if processed_count > 0:
    st.success(f"✅ You have {processed_count} fully processed episodes!")
    if st.button("📊 View Results →"):
        st.switch_page("pages/0_Podcasts.py")

st.markdown("---")

# Pipeline Overview
st.markdown("### 🔄 Processing Pipeline")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Pipeline Steps:**
    1. 📥 **Download** → Fetch episodes from RSS feeds
    2. 🎯 **Transcribe** → Convert audio to text (XAI/Groq Whisper)
    3. 🧠 **Summarize** → Extract insights (XAI/Groq)
    4. 💾 **Store** → Save to PostgreSQL
    5. 📄 **View** → Browse transcripts and summaries
    """)

with col2:
    st.markdown("""
    **Features:**
    - 🎧 Smart RSS feed management
    - 🚀 AI-powered transcription
    - 🧠 AI summarization with topics & quotes
    - 💾 PostgreSQL storage
    - 📊 Interactive data viewing
    """)

# Progress visualization
if total_episodes > 0:
    st.markdown("### 📈 Processing Progress")
    
    downloaded_pct = (downloaded_count / total_episodes) * 100 if total_episodes > 0 else 0
    transcribed_pct = (transcribed_count / total_episodes) * 100 if total_episodes > 0 else 0
    processed_pct = (processed_count / total_episodes) * 100 if total_episodes > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.progress(downloaded_pct / 100)
        st.caption(f"Downloaded: {downloaded_pct:.0f}%")
    
    with col2:
        st.progress(transcribed_pct / 100)
        st.caption(f"Transcribed: {transcribed_pct:.0f}%")
    
    with col3:
        st.progress(processed_pct / 100)
        st.caption(f"Processed: {processed_pct:.0f}%")

# Cleanup
db.close()

# Sidebar
with st.sidebar:
    st.markdown("### 🎙️ Open Podcast Processor")
    st.markdown("---")
    
    st.markdown("### 📚 Quick Links")
    st.page_link("pages/0_Podcasts.py", label="🎙️ Podcasts", icon="🎙️")
    st.page_link("pages/1_Process.py", label="⚙️ Process Episodes", icon="⚙️")
    st.page_link("pages/2_Download.py", label="📥 Download Episodes", icon="📥")
    
    st.markdown("---")
    
    st.markdown("### ℹ️ About")
    st.markdown("""
    **Open Podcast Processor** automates podcast processing using AI APIs.
    
    Built with:
    - Streamlit
    - XAI/Groq APIs (Whisper + LLM)
    - PostgreSQL
    - FFmpeg
    """)
    
    st.markdown("---")
    
    st.markdown("### 🙏 Acknowledgements")
    st.markdown("""
    Inspired by:
    - [Parakeet Podcast Processor](https://github.com/haasonsaas/parakeet-podcast-processor)
    - [Tomasz Tunguz](https://tomtunguz.com/)
    """)
