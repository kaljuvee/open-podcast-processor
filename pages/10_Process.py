"""
Process Episodes Page
Smart interface for transcribing and summarizing episodes
Automatically detects podcasts without transcripts
Combines transcription and summarization into one step with progress logging
"""

import streamlit as st
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from utils.postgres_db import PostgresDB
from utils.config import get_groq_api_key
from utils.processing import transcribe_episode, summarize_episode
from utils.streamlit_logger import capture_output

st.set_page_config(page_title="Process Episodes", page_icon="⚙️", layout="wide")

st.title("⚙️ Process Episodes")
st.markdown("**Step 2**: Transcribe and summarize your downloaded episodes in one step")

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
def get_podcasts_needing_processing():
    """Get podcasts that need processing (downloaded but not fully processed)."""
    all_podcasts = db.get_all_podcasts(status=None, limit=1000)
    
    needs_processing = []
    for podcast in all_podcasts:
        status = podcast.get('status', 'unknown')
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
                        transcript_text = transcript_dict.get('text', '') or transcript_dict.get('segments', [])
                        if transcript_text or (isinstance(transcript_dict, dict) and transcript_dict.get('segments')):
                            has_transcript = True
                except:
                    pass
        
        # Check if summary exists
        has_summary = False
        if summary:
            if isinstance(summary, dict):
                summary_text = summary.get('summary', '') if isinstance(summary, dict) else ''
                key_topics = summary.get('key_topics', []) if isinstance(summary, dict) else []
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
        
        # Need processing if: no transcript OR (has transcript but no summary)
        if not has_transcript or (has_transcript and not has_summary):
            # Check if audio file exists
            audio_file = podcast.get('audio_file_path')
            if audio_file:
                try:
                    if Path(audio_file).exists():
                        needs_processing.append({
                            'podcast': podcast,
                            'needs_transcription': not has_transcript,
                            'needs_summarization': has_transcript and not has_summary
                        })
                except:
                    pass
    
    return needs_processing

# Get podcasts needing processing
podcasts_needing_processing = get_podcasts_needing_processing()

# Status overview
st.markdown("### 📊 Processing Status")

col1, col2, col3 = st.columns(3)

with col1:
    needs_transcription = sum(1 for p in podcasts_needing_processing if p['needs_transcription'])
    st.metric("📥 Need Processing", len(podcasts_needing_processing), 
              help="Episodes needing transcription and/or summarization")
with col2:
    processed = db.get_all_podcasts(status='processed', limit=1000)
    st.metric("✅ Fully Processed", len(processed),
              help="Episodes with transcripts and summaries")
with col3:
    st.metric("🎯 Ready to process", needs_transcription,
              help="Episodes ready for processing")

st.markdown("---")

# Main processing interface
if len(podcasts_needing_processing) == 0:
    st.success("✅ All episodes are processed!")
    st.info("All downloaded episodes have transcripts and summaries.")
    if st.button("📥 Download More Episodes →", type="primary"):
        st.switch_page("pages/11_Download.py")
    st.stop()

# Smart processing
st.markdown("### 🚀 Process All Episodes (One Step)")

if len(podcasts_needing_processing) > 0:
    st.info(f"📥 Found {len(podcasts_needing_processing)} episode(s) that need processing")
    
    # Show list of episodes needing processing
    with st.expander(f"📋 Episodes Needing Processing ({len(podcasts_needing_processing)})", expanded=False):
        for p in podcasts_needing_processing[:10]:
            st.write(f"- {p['podcast'].get('title', 'Unknown')[:70]}...")
        if len(podcasts_needing_processing) > 10:
            st.caption(f"... and {len(podcasts_needing_processing) - 10} more")

st.info("""
This will process all episodes in one step:
1. **Transcribe** episodes without transcripts (converts audio to text)
2. **Summarize** transcribed episodes without summaries (extracts insights with AI)

Estimated time: ~2-3 minutes per episode
""")

# Check ffmpeg availability
from utils.audio import check_ffmpeg_installed
ffmpeg_available, ffmpeg_info = check_ffmpeg_installed()

if not ffmpeg_available:
    st.warning("⚠️ **ffmpeg not found** - Audio normalization may be skipped.")
    st.caption("ffmpeg is optional but recommended for better transcription quality.")
else:
    st.success(f"✅ **ffmpeg available** - Audio normalization enabled")

st.markdown("---")

if st.button("⚙️ Process All Episodes Now", type="primary", use_container_width=True):
    # Create progress indicators
    overall_progress = st.progress(0)
    status_text = st.empty()
    results_container = st.container()
    
    # Create debug log container
    debug_expander = st.expander("🔍 Debug Logs", expanded=True)
    debug_container = debug_expander.container()
    debug_container.info("📋 Processing episodes with progress logging...")
    
    try:
        # Combine transcription and summarization into one step
        status_text.info("🎙️ Processing all episodes in one step...")
        overall_progress.progress(0.1)
        
        total_to_process = len(podcasts_needing_processing)
        processed_count = 0
        transcription_count = 0
        summarization_count = 0
        errors = 0
        start_time = time.time()
        
        # Capture console output
        with capture_output(container=debug_container, display=True, max_lines=200):
            
            for idx, item in enumerate(podcasts_needing_processing):
                podcast = item['podcast']
                needs_transcription = item['needs_transcription']
                needs_summarization = item['needs_summarization']
                
                episode_id = podcast['id']
                episode_title = podcast['title'][:50] + "..." if len(podcast['title']) > 50 else podcast['title']
                
                # Calculate progress
                progress = (idx + 1) / total_to_process
                overall_progress.progress(progress)
                
                # Calculate estimated time remaining
                elapsed_time = time.time() - start_time
                if idx > 0:
                    avg_time_per_episode = elapsed_time / idx
                    remaining_episodes = total_to_process - idx
                    estimated_remaining = timedelta(seconds=int(avg_time_per_episode * remaining_episodes))
                    status_text.info(
                        f"🎙️ Processing {idx + 1}/{total_to_process}: {episode_title} "
                        f"(Estimated remaining: {estimated_remaining.total_seconds():.0f}s)"
                    )
                else:
                    status_text.info(f"🎙️ Processing {idx + 1}/{total_to_process}: {episode_title}")
                    print(f"  Processing episode {idx + 1}/{total_to_process}: {episode_title}")
                
                # Step 1: Transcribe if needed
                if needs_transcription:
                    print(f"\n[{idx + 1}/{total_to_process}] TRANSCRIBING: {episode_title}")
                    print(f"  Transcribing episode {idx + 1}/{total_to_process}: {episode_title}")
                    
                    transcription_start = time.time()
                    print(f"  🎙️ Transcribing episode {idx + 1}/{total_to_process}: {episode_title}...")
                    
                    success, error = transcribe_episode(episode_id, db)
                    transcription_time = time.time() - transcription_start
                    
                    if success:
                        transcription_count += 1
                        print(f"  ✅ Transcribed episode {idx + 1}/{total_to_process}: {episode_title} ({transcription_time:.1f}s)")
                    else:
                        errors += 1
                        print(f"  ❌ Transcription failed: {episode_title} - {error}")
                        st.warning(f"⚠️ Failed: {episode_title} - {error}")
                
                # Step 2: Summarize if needed (refresh list after transcription)
                if needs_summarization or (needs_transcription and success):
                    # Refresh podcast to get updated status
                    updated_podcast = db.get_episode_by_id(episode_id)
                    updated_summary = updated_podcast.get('summary') if updated_podcast else None
                    
                    if not updated_summary or (isinstance(updated_summary, dict) and not updated_summary.get('summary') and not updated_summary.get('key_topics')):
                        print(f"  🧠 Summarizing episode {idx + 1}/{total_to_process}: {episode_title}...")
                        
                        summarization_start = time.time()
                        success_summary, error_summary, summary = summarize_episode(episode_id, db)
                        summarization_time = time.time() - summarization_start
                        
                        if success_summary:
                            summarization_count += 1
                            print(f"  ✅ Summarized episode {idx + 1}/{total_to_process}: {episode_title} ({summarization_time:.1f}s)")
                        else:
                            errors += 1
                            print(f"  ❌ Summarization failed: {episode_title} - {error_summary}")
                            st.warning(f"⚠️ Failed: {episode_title} - {error_summary}")
                    else:
                        print(f"  ⏭️  Skipping summarization (already processed): {episode_title}")
                
                processed_count += 1
                
                # Update progress
                elapsed_total = time.time() - start_time
                if idx < total_to_process - 1:
                    avg_time = elapsed_total / (idx + 1)
                    remaining = total_to_process - idx - 1
                    eta = timedelta(seconds=int(avg_time * remaining))
                    status_text.success(f"✅ Processed {idx + 1}/{total_to_process}: {episode_title} (ETA: {eta.total_seconds():.0f}s remaining)")
        
        overall_progress.progress(1.0)
        total_time = time.time() - start_time
        
        # Display results
        with results_container:
            st.markdown("### 📊 Processing Results")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("✅ Processed", processed_count, 
                         delta=f"{total_time:.1f}s total" if total_time > 0 else None)
            with col2:
                st.metric("🎙️ Transcribed", transcription_count,
                         delta=f"{errors} errors" if errors > 0 else None)
            with col3:
                st.metric("🧠 Summarized", summarization_count,
                         delta=f"{errors} errors" if errors > 0 else None)
            with col4:
                st.metric("⚠️ Errors", errors)
            
            # Show next step
            st.markdown("---")
            st.markdown("### ✅ Processing Complete!")
            st.success(f"🎉 Successfully processed {processed_count} episodes in {total_time:.1f}s")
            
            if st.button("📊 View Results →", type="primary", key="view_results"):
                st.switch_page("pages/0_Podcasts.py")
    
    except Exception as e:
        overall_progress.progress(1.0)
        status_text.success("✅ Processing complete!")
        st.error(f"❌ Processing failed: {str(e)}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())

# Advanced: Individual processing
with st.expander("🔧 Advanced: Process Individual Episodes"):
    st.markdown("### Process Specific Episode")
    
    if len(podcasts_needing_processing) > 0:
        selected_episode = st.selectbox(
            "Select episode to process",
            options=[(p['podcast']['id'], f"{p['podcast']['title'][:60]}...") for p in podcasts_needing_processing],
            format_func=lambda x: x[1]
        )
        
        if st.button("🎯 Process Selected", key="process_one"):
            episode_id = selected_episode[0]
            episode_title = selected_episode[1]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            debug_expander = st.expander("🔍 Debug Logs", expanded=True)
            debug_container = debug_expander.container()
            
            with capture_output(container=debug_container, display=True, max_lines=200):
                status_text.info(f"🎙️ Processing: {episode_title}...")
                progress_bar.progress(0.3)
                
                # Transcribe
                transcription_start = time.time()
                print(f"🎙️ Transcribing episode: {episode_title}...")
                success, error = transcribe_episode(episode_id, db)
                transcription_time = time.time() - transcription_start
                
                progress_bar.progress(0.6)
                
                if success:
                    print(f"✅ Transcribed episode in {transcription_time:.1f}s")
                    # Summarize
                    summarization_start = time.time()
                    print(f"🧠 Summarizing episode: {episode_title}...")
                    success_summary, error_summary, summary = summarize_episode(episode_id, db)
                    summarization_time = time.time() - summarization_start
                    
                    progress_bar.progress(1.0)
                    
                    if success_summary:
                        status_text.success(f"✅ Processing complete! ({transcription_time + summarization_time:.1f}s total)")
                        st.success(f"✅ Successfully processed: {episode_title}")
                        print(f"✅ Summarized episode in {summarization_time:.1f}s")
                        if summary:
                            with st.expander("View Summary"):
                                st.json(summary)
                        st.rerun()
                    else:
                        status_text.error("❌ Summarization failed")
                        st.error(f"❌ Summarization failed: {error_summary}")
                else:
                    progress_bar.progress(1.0)
                    status_text.error("❌ Processing failed")
                    st.error(f"❌ Processing failed: {error}")
    else:
        st.info("No episodes ready for processing")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Process Episodes")
    st.markdown("---")
    
    st.markdown("### 💡 Processing Info")
    st.markdown("""
    **One-Step Processing:**
    - Transcribes episodes (Groq Whisper API)
    - Summarize episodes (Groq LLM API)
    - ~2-3 min per episode total
    - Extracts topics, themes, quotes
    - Identifies companies mentioned
    """)
    
    st.markdown("---")
    
    st.markdown("### 📊 Current Status")
    st.metric("Need Processing", len(podcasts_needing_processing))
    st.metric("Fully Processed", len(processed))

# Cleanup
db.close()
