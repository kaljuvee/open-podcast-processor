"""
Open Podcast Processor - Home Page
Streamlit application for automated podcast processing with XAI API
"""

import streamlit as st
from utils.database import P3Database
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
db = P3Database()

# Get statistics
downloaded = db.get_episodes_by_status('downloaded')
transcribed = db.get_episodes_by_status('transcribed')
processed = db.get_episodes_by_status('processed')

total_episodes = len(downloaded) + len(transcribed) + len(processed)

# Quick Stats at the top
st.markdown("### 📊 Quick Stats")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📥 Downloaded", len(downloaded), help="Episodes downloaded but not transcribed")
with col2:
    st.metric("🎯 Transcribed", len(transcribed), help="Episodes transcribed but not summarized")
with col3:
    st.metric("✅ Processed", len(processed), help="Episodes fully processed")
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

if len(downloaded) > 0:
    st.info(f"✅ You have {len(downloaded)} episodes ready to transcribe!")
    if st.button("🎯 Go to Process Episodes →", type="primary"):
        st.switch_page("pages/1_Process.py")
else:
    st.warning("⚠️ No episodes downloaded yet. Start by downloading some episodes!")
    if st.button("📥 Go to Download →", type="primary"):
        st.switch_page("pages/0_Download.py")

# Step 2: Process
st.markdown("""
<div class="workflow-step">
    <span class="step-number">2️⃣</span> <strong>Process Episodes</strong>
    <p>Go to <strong>⚙️ Process</strong> page → Click "Process All" to transcribe and summarize</p>
</div>
""", unsafe_allow_html=True)

if len(transcribed) > 0:
    st.info(f"✅ You have {len(transcribed)} episodes ready to summarize!")

# Step 3: View Results
st.markdown("""
<div class="workflow-step">
    <span class="step-number">3️⃣</span> <strong>View Results</strong>
    <p>Go to <strong>📊 View Data</strong> page → Browse summaries, transcripts, and export data</p>
</div>
""", unsafe_allow_html=True)

if len(processed) > 0:
    st.success(f"✅ You have {len(processed)} fully processed episodes!")
    if st.button("📊 View Results →"):
        st.switch_page("pages/2_View_Data.py")

st.markdown("---")

# Pipeline Overview
st.markdown("### 🔄 Processing Pipeline")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Pipeline Steps:**
    1. 📥 **Download** → Fetch episodes from RSS feeds
    2. 🎯 **Transcribe** → Convert audio to text (XAI Whisper)
    3. 🧠 **Summarize** → Extract insights (XAI Grok)
    4. 💾 **Store** → Save to DuckDB
    5. 📄 **Export** → View and download results
    """)

with col2:
    st.markdown("""
    **Features:**
    - 🎧 Smart RSS feed management
    - 🚀 XAI-powered transcription
    - 🧠 AI summarization with topics & quotes
    - 💾 Efficient DuckDB storage
    - 📊 Interactive data viewing
    """)

# Progress visualization
if total_episodes > 0:
    st.markdown("### 📈 Processing Progress")
    
    downloaded_pct = (len(downloaded) / total_episodes) * 100
    transcribed_pct = (len(transcribed) / total_episodes) * 100
    processed_pct = (len(processed) / total_episodes) * 100
    
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
    st.page_link("pages/0_Download.py", label="📥 Download Episodes", icon="📥")
    st.page_link("pages/1_Process.py", label="⚙️ Process Episodes", icon="⚙️")
    st.page_link("pages/2_View_Data.py", label="📊 View Data", icon="📊")
    
    st.markdown("---")
    
    st.markdown("### ℹ️ About")
    st.markdown("""
    **Open Podcast Processor** automates podcast processing using XAI API.
    
    Built with:
    - Streamlit
    - XAI API (Whisper + Grok)
    - DuckDB
    - FFmpeg
    """)
    
    st.markdown("---")
    
    st.markdown("### 🙏 Acknowledgements")
    st.markdown("""
    Inspired by:
    - [Parakeet Podcast Processor](https://github.com/haasonsaas/parakeet-podcast-processor)
    - [Tomasz Tunguz](https://tomtunguz.com/)
    """)
