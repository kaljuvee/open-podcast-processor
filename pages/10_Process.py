"""
Process Episodes Page
Simplified interface for transcribing and summarizing episodes
"""

import streamlit as st
from utils.database import P3Database
from utils.config import get_api_key
from utils.processing import process_all_episodes, transcribe_episode, summarize_episode

st.set_page_config(page_title="Process Episodes", page_icon="⚙️", layout="wide")

st.title("⚙️ Process Episodes")
st.markdown("**Step 2**: Transcribe and summarize your downloaded episodes")

# Check API key
try:
    api_key = get_api_key()
except ValueError as e:
    st.error(f"⚠️ {str(e)}")
    st.code("echo 'XAI_API_KEY=your-key-here' > .env")
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

# Check ffmpeg availability for audio processing
from utils.audio import check_ffmpeg_installed
ffmpeg_available, ffmpeg_info = check_ffmpeg_installed()

if not ffmpeg_available:
    st.warning("⚠️ **ffmpeg not found** - Audio normalization may be skipped during download.")
    st.caption("ffmpeg is optional but recommended for better transcription quality.")
else:
    st.success(f"✅ **ffmpeg available** - Audio normalization enabled")
    if ffmpeg_info:
        st.caption(f"Version: {ffmpeg_info[:50]}...")

st.markdown("---")

if st.button("⚙️ Process All Episodes Now", type="primary", use_container_width=True):
    # Create progress indicators
    overall_progress = st.progress(0)
    status_text = st.empty()
    results_container = st.container()
    
    try:
        # Step 1: Transcription
        status_text.info("🎙️ Step 1/2: Transcribing episodes...")
        overall_progress.progress(0.1)
        
        # Get episodes to transcribe
        episodes_to_transcribe = db.get_episodes_by_status('downloaded')
        total_to_transcribe = len(episodes_to_transcribe)
        
        transcribed_count = 0
        transcription_errors = 0
        
        if total_to_transcribe > 0:
            transcription_progress = st.progress(0)
            transcription_status = st.empty()
            
            for idx, episode in enumerate(episodes_to_transcribe):
                episode_title = episode['title'][:50] + "..." if len(episode['title']) > 50 else episode['title']
                transcription_status.info(f"Transcribing {idx + 1}/{total_to_transcribe}: {episode_title}")
                transcription_progress.progress((idx + 1) / total_to_transcribe)
                
                success, error = transcribe_episode(episode['id'], db)
                if success:
                    transcribed_count += 1
                else:
                    transcription_errors += 1
                    st.warning(f"⚠️ Failed: {episode_title} - {error}")
            
            transcription_progress.progress(1.0)
            transcription_status.success(f"✅ Transcribed {transcribed_count}/{total_to_transcribe} episodes")
        else:
            st.info("ℹ️ No episodes to transcribe")
        
        overall_progress.progress(0.5)
        
        # Step 2: Summarization
        status_text.info("🧠 Step 2/2: Summarizing episodes...")
        
        # Get episodes to summarize
        episodes_to_summarize = db.get_episodes_by_status('transcribed')
        total_to_summarize = len(episodes_to_summarize)
        
        summarized_count = 0
        summarization_errors = 0
        
        if total_to_summarize > 0:
            summarization_progress = st.progress(0)
            summarization_status = st.empty()
            
            for idx, episode in enumerate(episodes_to_summarize):
                episode_title = episode['title'][:50] + "..." if len(episode['title']) > 50 else episode['title']
                summarization_status.info(f"Summarizing {idx + 1}/{total_to_summarize}: {episode_title}")
                summarization_progress.progress((idx + 1) / total_to_summarize)
                
                success, error, summary = summarize_episode(episode['id'], db)
                if success:
                    summarized_count += 1
                else:
                    summarization_errors += 1
                    st.warning(f"⚠️ Failed: {episode_title} - {error}")
            
            summarization_progress.progress(1.0)
            summarization_status.success(f"✅ Summarized {summarized_count}/{total_to_summarize} episodes")
        else:
            st.info("ℹ️ No episodes to summarize")
        
        overall_progress.progress(1.0)
        status_text.success("✅ Processing complete!")
        
        # Display results
        with results_container:
            st.markdown("### 📊 Processing Results")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("✅ Transcribed", transcribed_count, delta=f"{transcription_errors} errors" if transcription_errors > 0 else None)
            with col2:
                st.metric("✅ Summarized", summarized_count, delta=f"{summarization_errors} errors" if summarization_errors > 0 else None)
            with col3:
                total_errors = transcription_errors + summarization_errors
                st.metric("⚠️ Errors", total_errors)
            
            # Refresh lists
            downloaded = db.get_episodes_by_status('downloaded')
            transcribed = db.get_episodes_by_status('transcribed')
            processed = db.get_episodes_by_status('processed')
            
            # Show next step
            st.markdown("---")
            st.markdown("### ✅ Processing Complete!")
            total_processed = transcribed_count + summarized_count
            st.success(f"🎉 Successfully processed {total_processed} episodes!")
            
            if st.button("📊 View Results →", type="primary", key="view_results"):
                st.switch_page("pages/2_View_Data.py")
    
    except Exception as e:
        overall_progress.progress(1.0)
        status_text.error("❌ Processing failed")
        st.error(f"❌ Processing failed: {str(e)}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())

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
            episode_id = selected_download[0]
            episode_title = selected_download[1]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.info(f"🎙️ Transcribing: {episode_title}...")
            progress_bar.progress(0.3)
            
            success, error = transcribe_episode(episode_id, db)
            
            progress_bar.progress(1.0)
            
            if success:
                status_text.success("✅ Transcription complete!")
                st.success(f"✅ Successfully transcribed: {episode_title}")
                st.rerun()
            else:
                status_text.error("❌ Transcription failed")
                st.error(f"❌ Transcription failed: {error}")
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
            episode_id = selected_transcribed[0]
            episode_title = selected_transcribed[1]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.info(f"🧠 Summarizing: {episode_title}...")
            progress_bar.progress(0.3)
            
            success, error, summary = summarize_episode(episode_id, db)
            
            progress_bar.progress(1.0)
            
            if success:
                status_text.success("✅ Summarization complete!")
                st.success(f"✅ Successfully summarized: {episode_title}")
                if summary:
                    with st.expander("View Summary"):
                        st.json(summary)
                st.rerun()
            else:
                status_text.error("❌ Summarization failed")
                st.error(f"❌ Summarization failed: {error}")
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
