"""
Processing Page
Transcribe and summarize podcast episodes using XAI API
"""

import streamlit as st
import os
from p3.database import P3Database
from p3.transcriber_xai import AudioTranscriber
from p3.cleaner_xai import TranscriptCleaner

st.set_page_config(page_title="Processing", page_icon="⚙️", layout="wide")

st.title("⚙️ Episode Processing")

# Check API key
api_key = os.getenv("XAI_API_KEY")
if not api_key:
    st.error("⚠️ XAI_API_KEY not found in environment variables. Please set it to use this feature.")
    st.stop()

# Initialize database
db = P3Database()

# Tabs for different operations
tab1, tab2, tab3 = st.tabs(["🎯 Transcribe", "🧠 Summarize", "📊 Status"])

with tab1:
    st.subheader("Transcribe Episodes with XAI")
    
    # Get episodes ready for transcription
    downloaded_episodes = db.get_episodes_by_status('downloaded')
    
    if downloaded_episodes:
        st.info(f"Found {len(downloaded_episodes)} episodes ready for transcription")
        
        # Show episodes in expandable sections
        for episode in downloaded_episodes[:10]:  # Show first 10
            with st.expander(f"🎙️ {episode['title']}"):
                st.write(f"**Podcast:** {episode['podcast_title']}")
                st.write(f"**Date:** {episode['date']}")
                st.write(f"**File:** {episode['file_path']}")
                
                if st.button(f"Transcribe", key=f"transcribe_{episode['id']}"):
                    with st.spinner(f"Transcribing {episode['title']}..."):
                        try:
                            transcriber = AudioTranscriber(db, api_key=api_key)
                            success = transcriber.transcribe_episode(episode['id'])
                            
                            if success:
                                st.success("✅ Transcription complete!")
                            else:
                                st.error("❌ Transcription failed")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        st.markdown("---")
        
        # Batch transcribe
        if st.button("🚀 Transcribe All Downloaded Episodes", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            transcriber = AudioTranscriber(db, api_key=api_key)
            
            total = len(downloaded_episodes)
            success_count = 0
            
            for idx, episode in enumerate(downloaded_episodes):
                status_text.text(f"Transcribing: {episode['title']}...")
                
                try:
                    if transcriber.transcribe_episode(episode['id']):
                        success_count += 1
                        st.success(f"✅ {episode['title']}")
                except Exception as e:
                    st.error(f"❌ {episode['title']}: {str(e)}")
                
                progress_bar.progress((idx + 1) / total)
            
            status_text.text("Transcription complete!")
            st.success(f"🎉 Successfully transcribed {success_count}/{total} episodes")
    else:
        st.info("No episodes ready for transcription. Download episodes first from the RSS Feeds page.")

with tab2:
    st.subheader("Summarize Transcribed Episodes with XAI")
    
    # Get episodes ready for summarization
    transcribed_episodes = db.get_episodes_by_status('transcribed')
    
    if transcribed_episodes:
        st.info(f"Found {len(transcribed_episodes)} episodes ready for summarization")
        
        # Show episodes in expandable sections
        for episode in transcribed_episodes[:10]:  # Show first 10
            with st.expander(f"🎙️ {episode['title']}"):
                st.write(f"**Podcast:** {episode['podcast_title']}")
                st.write(f"**Date:** {episode['date']}")
                
                # Show transcript preview
                segments = db.get_transcripts_for_episode(episode['id'])
                if segments:
                    transcript_preview = " ".join([s['text'] for s in segments[:3]])
                    st.text_area("Transcript Preview", transcript_preview[:500] + "...", height=100)
                
                if st.button(f"Summarize", key=f"summarize_{episode['id']}"):
                    with st.spinner(f"Summarizing {episode['title']}..."):
                        try:
                            cleaner = TranscriptCleaner(db, api_key=api_key)
                            summary = cleaner.generate_summary(episode['id'])
                            
                            if summary:
                                st.success("✅ Summary generated!")
                                st.json(summary)
                            else:
                                st.error("❌ Summarization failed")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        st.markdown("---")
        
        # Batch summarize
        if st.button("🚀 Summarize All Transcribed Episodes", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            cleaner = TranscriptCleaner(db, api_key=api_key)
            
            total = len(transcribed_episodes)
            success_count = 0
            
            for idx, episode in enumerate(transcribed_episodes):
                status_text.text(f"Summarizing: {episode['title']}...")
                
                try:
                    if cleaner.generate_summary(episode['id']):
                        success_count += 1
                        st.success(f"✅ {episode['title']}")
                except Exception as e:
                    st.error(f"❌ {episode['title']}: {str(e)}")
                
                progress_bar.progress((idx + 1) / total)
            
            status_text.text("Summarization complete!")
            st.success(f"🎉 Successfully summarized {success_count}/{total} episodes")
    else:
        st.info("No episodes ready for summarization. Transcribe episodes first.")

with tab3:
    st.subheader("Processing Status Overview")
    
    # Get counts by status
    downloaded = db.get_episodes_by_status('downloaded')
    transcribed = db.get_episodes_by_status('transcribed')
    processed = db.get_episodes_by_status('processed')
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📥 Downloaded", len(downloaded), help="Episodes downloaded but not transcribed")
    with col2:
        st.metric("🎯 Transcribed", len(transcribed), help="Episodes transcribed but not summarized")
    with col3:
        st.metric("✅ Processed", len(processed), help="Episodes fully processed")
    
    # Show pipeline visualization
    st.markdown("### 📊 Processing Pipeline")
    
    total = len(downloaded) + len(transcribed) + len(processed)
    
    if total > 0:
        downloaded_pct = (len(downloaded) / total) * 100
        transcribed_pct = (len(transcribed) / total) * 100
        processed_pct = (len(processed) / total) * 100
        
        st.markdown(f"""
        **Pipeline Progress:**
        - 📥 Downloaded: {len(downloaded)} ({downloaded_pct:.1f}%)
        - 🎯 Transcribed: {len(transcribed)} ({transcribed_pct:.1f}%)
        - ✅ Processed: {len(processed)} ({processed_pct:.1f}%)
        """)
        
        # Progress bars
        st.progress(downloaded_pct / 100, text=f"Downloaded: {downloaded_pct:.1f}%")
        st.progress(transcribed_pct / 100, text=f"Transcribed: {transcribed_pct:.1f}%")
        st.progress(processed_pct / 100, text=f"Processed: {processed_pct:.1f}%")
    else:
        st.info("No episodes in the pipeline yet. Start by downloading episodes from RSS feeds.")

# Cleanup
db.close()

# Sidebar info
with st.sidebar:
    st.markdown("### ⚙️ Processing")
    st.markdown("""
    **Pipeline Steps:**
    1. **Transcribe** - Convert audio to text using XAI Whisper
    2. **Summarize** - Extract insights using XAI Grok
    
    **XAI Models:**
    - Transcription: Whisper-1
    - Summarization: Grok-beta
    
    **Processing Time:**
    - Transcription: ~1-2 min per hour of audio
    - Summarization: ~10-30 seconds per episode
    """)
