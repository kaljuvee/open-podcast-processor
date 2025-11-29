"""
Process Episodes Page
Smart interface for transcribing and summarizing episodes
Automatically detects podcasts without transcripts
"""

import streamlit as st
import json
from pathlib import Path
from utils.postgres_db import PostgresDB
from utils.config import get_groq_api_key
from utils.processing import transcribe_episode, summarize_episode

st.set_page_config(page_title="Process Episodes", page_icon="⚙️", layout="wide")

st.title("⚙️ Process Episodes")
st.markdown("**Step 2**: Transcribe and summarize your downloaded episodes")

# Check API key
try:
    api_key = get_groq_api_key()
except ValueError as e:
    st.error(f"⚠️ {str(e)}")
    st.code("echo 'GROQ_API_KEY=your-key-here' > .env")
    st.stop()

# Initialize PostgreSQL database
try:
    db = PostgresDB()
except Exception as e:
    st.error(f"Failed to connect to PostgreSQL: {e}")
    st.info("Please ensure DB_URL is set in your .env file")
    st.stop()

# Smart detection: Find podcasts without transcripts
def get_podcasts_needing_transcription():
    """Get podcasts that need transcription (downloaded but no transcript)."""
    all_podcasts = db.get_all_podcasts(status=None, limit=1000)
    
    needs_transcription = []
    for podcast in all_podcasts:
        # Check if status is 'downloaded' or if transcript is missing/invalid
        status = podcast.get('status', 'unknown')
        transcript = podcast.get('transcript')
        
        # Check if transcript exists and has content
        has_transcript = False
        if transcript:
            if isinstance(transcript, dict):
                transcript_text = transcript.get('text', '')
                segments = transcript.get('segments', [])
                if transcript_text or (segments and len(segments) > 0):
                    has_transcript = True
            elif isinstance(transcript, str):
                try:
                    transcript_dict = json.loads(transcript)
                    if isinstance(transcript_dict, dict):
                        transcript_text = transcript_dict.get('text', '')
                        segments = transcript_dict.get('segments', [])
                        if transcript_text or (segments and len(segments) > 0):
                            has_transcript = True
                except:
                    pass
        
        # Need transcription if: status is downloaded OR no valid transcript
        if status == 'downloaded' or (status != 'failed' and not has_transcript):
            # Check if audio file exists
            audio_file = podcast.get('audio_file_path')
            if audio_file:
                try:
                    if Path(audio_file).exists():
                        needs_transcription.append(podcast)
                except:
                    # If path is invalid, skip
                    pass
    
    return needs_transcription

def get_podcasts_needing_summarization():
    """Get podcasts that need summarization (transcribed but no summary)."""
    all_podcasts = db.get_all_podcasts(status=None, limit=1000)
    
    needs_summarization = []
    for podcast in all_podcasts:
        transcript = podcast.get('transcript')
        summary = podcast.get('summary')
        
        # Check if transcript exists
        has_transcript = False
        if transcript:
            if isinstance(transcript, dict):
                transcript_text = transcript.get('text', '')
                segments = transcript.get('segments', [])
                if transcript_text or (segments and len(segments) > 0):
                    has_transcript = True
            elif isinstance(transcript, str):
                try:
                    transcript_dict = json.loads(transcript)
                    if isinstance(transcript_dict, dict):
                        transcript_text = transcript_dict.get('text', '')
                        segments = transcript_dict.get('segments', [])
                        if transcript_text or (segments and len(segments) > 0):
                            has_transcript = True
                except:
                    pass
        
        # Check if summary exists
        has_summary = False
        if summary:
            if isinstance(summary, dict):
                summary_text = summary.get('summary', '')
                key_topics = summary.get('key_topics', [])
                if summary_text or key_topics:
                    has_summary = True
            elif isinstance(summary, str):
                try:
                    summary_dict = json.loads(summary)
                    if isinstance(summary_dict, dict):
                        summary_text = summary_dict.get('summary', '')
                        key_topics = summary_dict.get('key_topics', [])
                        if summary_text or key_topics:
                            has_summary = True
                except:
                    pass
        
        # Need summarization if: has transcript but no summary
        if has_transcript and not has_summary:
            needs_summarization.append(podcast)
    
    return needs_summarization

# Get podcasts needing processing
podcasts_needing_transcription = get_podcasts_needing_transcription()
podcasts_needing_summarization = get_podcasts_needing_summarization()

# Status overview
st.markdown("### 📊 Processing Status")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📥 Need Transcription", len(podcasts_needing_transcription), 
              help="Downloaded episodes without transcripts")
with col2:
    st.metric("🎯 Need Summarization", len(podcasts_needing_summarization),
              help="Transcribed episodes without summaries")
with col3:
    processed = db.get_all_podcasts(status='processed', limit=1000)
    st.metric("✅ Fully Processed", len(processed),
              help="Episodes with transcripts and summaries")

st.markdown("---")

# Main processing interface
if len(podcasts_needing_transcription) == 0 and len(podcasts_needing_summarization) == 0:
    st.success("✅ All episodes are processed!")
    st.info("All downloaded episodes have transcripts and summaries.")
    if st.button("📥 Download More Episodes →", type="primary"):
        st.switch_page("pages/11_Download.py")
    st.stop()

# Smart processing
st.markdown("### 🚀 Process Episodes")

if len(podcasts_needing_transcription) > 0:
    st.info(f"📥 Found {len(podcasts_needing_transcription)} episode(s) that need transcription")
    
    # Show list of episodes needing transcription
    with st.expander(f"📋 Episodes Needing Transcription ({len(podcasts_needing_transcription)})", expanded=False):
        for pod in podcasts_needing_transcription[:10]:  # Show first 10
            st.write(f"- {pod.get('title', 'Unknown')[:70]}...")
        if len(podcasts_needing_transcription) > 10:
            st.caption(f"... and {len(podcasts_needing_transcription) - 10} more")

if len(podcasts_needing_summarization) > 0:
    st.info(f"🎯 Found {len(podcasts_needing_summarization)} episode(s) that need summarization")
    
    # Show list of episodes needing summarization
    with st.expander(f"📋 Episodes Needing Summarization ({len(podcasts_needing_summarization)})", expanded=False):
        for pod in podcasts_needing_summarization[:10]:  # Show first 10
            st.write(f"- {pod.get('title', 'Unknown')[:70]}...")
        if len(podcasts_needing_summarization) > 10:
            st.caption(f"... and {len(podcasts_needing_summarization) - 10} more")

st.info("""
This will:
1. **Transcribe** all episodes without transcripts (converts audio to text)
2. **Summarize** all transcribed episodes without summaries (extracts insights with AI)

Processing time: ~1-2 minutes per episode
""")

# Check ffmpeg availability
from utils.audio import check_ffmpeg_installed
ffmpeg_available, ffmpeg_info = check_ffmpeg_installed()

if not ffmpeg_available:
    st.warning("⚠️ **ffmpeg not found** - Audio normalization may be skipped.")
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
        
        total_to_transcribe = len(podcasts_needing_transcription)
        transcribed_count = 0
        transcription_errors = 0
        
        if total_to_transcribe > 0:
            transcription_progress = st.progress(0)
            transcription_status = st.empty()
            
            for idx, episode in enumerate(podcasts_needing_transcription):
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
        
        # Refresh list after transcription
        podcasts_needing_summarization = get_podcasts_needing_summarization()
        
        # Step 2: Summarization
        status_text.info("🧠 Step 2/2: Summarizing episodes...")
        
        total_to_summarize = len(podcasts_needing_summarization)
        summarized_count = 0
        summarization_errors = 0
        
        if total_to_summarize > 0:
            summarization_progress = st.progress(0)
            summarization_status = st.empty()
            
            for idx, episode in enumerate(podcasts_needing_summarization):
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
                st.metric("✅ Transcribed", transcribed_count, 
                         delta=f"{transcription_errors} errors" if transcription_errors > 0 else None)
            with col2:
                st.metric("✅ Summarized", summarized_count,
                         delta=f"{summarization_errors} errors" if summarization_errors > 0 else None)
            with col3:
                total_errors = transcription_errors + summarization_errors
                st.metric("⚠️ Errors", total_errors)
            
            # Show next step
            st.markdown("---")
            st.markdown("### ✅ Processing Complete!")
            total_processed = transcribed_count + summarized_count
            st.success(f"🎉 Successfully processed {total_processed} episodes!")
            
            if st.button("📊 View Results →", type="primary", key="view_results"):
                st.switch_page("pages/0_Podcasts.py")
    
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
    
    if len(podcasts_needing_transcription) > 0:
        selected_download = st.selectbox(
            "Select episode to transcribe",
            options=[(e['id'], f"{e['title'][:60]}...") for e in podcasts_needing_transcription],
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
    
    if len(podcasts_needing_summarization) > 0:
        selected_transcribed = st.selectbox(
            "Select episode to summarize",
            options=[(e['id'], f"{e['title'][:60]}...") for e in podcasts_needing_summarization],
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
    - Uses Groq Whisper API
    - ~1-2 min per hour of audio
    - Converts speech to text
    
    **Summarization:**
    - Uses Groq LLM API
    - ~10-30 seconds per episode
    - Extracts topics, themes, quotes
    - Identifies companies mentioned
    """)
    
    st.markdown("---")
    
    st.markdown("### 📊 Current Status")
    st.metric("Need Transcription", len(podcasts_needing_transcription))
    st.metric("Need Summarization", len(podcasts_needing_summarization))
    st.metric("Fully Processed", len(processed))

# Cleanup
db.close()
