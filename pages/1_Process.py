"""
Process Episodes Page
Simplified interface for transcribing and summarizing episodes
"""

import streamlit as st
import os
from p3.database import P3Database
from p3.transcriber_xai import AudioTranscriber
from p3.cleaner_xai import TranscriptCleaner

st.set_page_config(page_title="Process Episodes", page_icon="⚙️", layout="wide")

st.title("⚙️ Process Episodes")
st.markdown("**Step 2**: Transcribe and summarize your downloaded episodes")

# Check API key
api_key = os.getenv("XAI_API_KEY")
if not api_key:
    st.error("⚠️ XAI_API_KEY not found. Please set it in your environment variables.")
    st.stop()

# Initialize
db = P3Database()

# Get episode counts
downloaded = db.get_episodes_by_status('downloaded')
transcribed = db.get_episodes_by_status('transcribed')
processed = db.get_episodes_by_status('processed')

# Status overview
st.markdown("### 📊 Processing Status")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📥 Ready to Transcribe", len(downloaded), help="Downloaded episodes waiting for transcription")
with col2:
    st.metric("🎯 Ready to Summarize", len(transcribed), help="Transcribed episodes waiting for summarization")
with col3:
    st.metric("✅ Fully Processed", len(processed), help="Episodes with transcripts and summaries")

st.markdown("---")

# Main processing interface
if len(downloaded) == 0 and len(transcribed) == 0:
    st.info("ℹ️ No episodes to process. Download some episodes first!")
    if st.button("📥 Go to Download →", type="primary"):
        st.switch_page("pages/0_Download.py")
    st.stop()

# Simple one-button processing
st.markdown("### 🚀 Process All Episodes")

st.info("""
This will:
1. **Transcribe** all downloaded episodes (converts audio to text)
2. **Summarize** all transcribed episodes (extracts insights with AI)

Processing time: ~1-2 minutes per episode
""")

if st.button("⚙️ Process All Episodes Now", type="primary", use_container_width=True):
    total_processed = 0
    
    # Step 1: Transcribe downloaded episodes
    if len(downloaded) > 0:
        st.markdown("### 🎯 Step 1: Transcription")
        progress_bar = st.progress(0)
        
        transcriber = AudioTranscriber(db, api_key=api_key)
        
        for idx, episode in enumerate(downloaded):
            with st.spinner(f"🎯 Transcribing: {episode['title'][:50]}..."):
                try:
                    success = transcriber.transcribe_episode(episode['id'])
                    if success:
                        st.success(f"✅ Transcribed: {episode['title'][:50]}...")
                        total_processed += 1
                    else:
                        st.error(f"❌ Failed: {episode['title'][:50]}...")
                except Exception as e:
                    st.error(f"❌ Failed: {episode['title'][:50]}... - {str(e)}")
            
            progress_bar.progress((idx + 1) / len(downloaded))
        
        st.success(f"🎉 Transcription complete! Processed {total_processed} episodes")
        
        # Refresh transcribed list
        transcribed = db.get_episodes_by_status('transcribed')
    
    # Step 2: Summarize transcribed episodes
    if len(transcribed) > 0:
        st.markdown("### 🧠 Step 2: Summarization")
        progress_bar = st.progress(0)
        
        cleaner = TranscriptCleaner(db, api_key=api_key)
        summarized_count = 0
        
        for idx, episode in enumerate(transcribed):
            with st.spinner(f"🧠 Summarizing: {episode['title'][:50]}..."):
                try:
                    summary = cleaner.generate_summary(episode['id'])
                    if summary:
                        st.success(f"✅ Summarized: {episode['title'][:50]}...")
                        summarized_count += 1
                    else:
                        st.error(f"❌ Failed: {episode['title'][:50]}...")
                except Exception as e:
                    st.error(f"❌ Failed: {episode['title'][:50]}... - {str(e)}")
            
            progress_bar.progress((idx + 1) / len(transcribed))
        
        st.success(f"🎉 Summarization complete! Processed {summarized_count} episodes")
    
    # Show next step
    st.markdown("---")
    st.markdown("### ✅ Processing Complete!")
    st.success(f"🎉 Successfully processed {total_processed} episodes!")
    
    if st.button("📊 View Results →", type="primary"):
        st.switch_page("pages/2_View_Data.py")

# Advanced: Individual processing
with st.expander("🔧 Advanced: Process Individual Episodes"):
    st.markdown("### Transcribe Specific Episodes")
    
    if len(downloaded) > 0:
        selected_download = st.selectbox(
            "Select episode to transcribe",
            options=[(e['id'], f"{e['title'][:60]}...") for e in downloaded],
            format_func=lambda x: x[1]
        )
        
        if st.button("🎯 Transcribe Selected", key="transcribe_one"):
            with st.spinner("Transcribing..."):
                try:
                    transcriber = AudioTranscriber(db, api_key=api_key)
                    success = transcriber.transcribe_episode(selected_download[0])
                    if success:
                        st.success("✅ Transcription complete!")
                        st.rerun()
                    else:
                        st.error("❌ Transcription failed")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    else:
        st.info("No episodes ready for transcription")
    
    st.markdown("---")
    st.markdown("### Summarize Specific Episodes")
    
    if len(transcribed) > 0:
        selected_transcribed = st.selectbox(
            "Select episode to summarize",
            options=[(e['id'], f"{e['title'][:60]}...") for e in transcribed],
            format_func=lambda x: x[1]
        )
        
        if st.button("🧠 Summarize Selected", key="summarize_one"):
            with st.spinner("Summarizing..."):
                try:
                    cleaner = TranscriptCleaner(db, api_key=api_key)
                    summary = cleaner.generate_summary(selected_transcribed[0])
                    if summary:
                        st.success("✅ Summarization complete!")
                        st.rerun()
                    else:
                        st.error("❌ Summarization failed")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    else:
        st.info("No episodes ready for summarization")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Process Episodes")
    st.markdown("---")
    
    st.markdown("### 💡 Processing Info")
    st.markdown("""
    **Transcription:**
    - Uses XAI Whisper API
    - ~1-2 min per hour of audio
    - Converts speech to text
    
    **Summarization:**
    - Uses XAI Grok API
    - ~10-30 seconds per episode
    - Extracts topics, themes, quotes
    - Identifies companies mentioned
    """)
    
    st.markdown("---")
    
    st.markdown("### 📊 Current Status")
    st.metric("Ready to Transcribe", len(downloaded))
    st.metric("Ready to Summarize", len(transcribed))
    st.metric("Fully Processed", len(processed))

# Cleanup
db.close()
