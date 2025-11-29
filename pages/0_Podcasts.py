"""
Podcasts Page
View processed podcasts with transcripts and statistics
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

from utils.postgres_db import PostgresDB
from utils.config import get_db_url, get_db_schema

st.set_page_config(page_title="Podcasts", page_icon="🎙️", layout="wide")

st.title("🎙️ Processed Podcasts")

# Initialize PostgreSQL connection
try:
    db = PostgresDB()
except Exception as e:
    st.error(f"Failed to connect to PostgreSQL: {e}")
    st.info("Please ensure DB_URL is set in your .env file")
    st.stop()

# Get statistics
try:
    stats = db.get_stats()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Podcasts", stats.get('total_podcasts', 0))
    with col2:
        st.metric("Downloaded", stats.get('downloaded_count', 0))
    with col3:
        st.metric("Transcribed", stats.get('transcribed_count', 0))
    with col4:
        st.metric("Processed", stats.get('processed_count', 0))
    with col5:
        st.metric("Failed", stats.get('failed_count', 0))
    
    if stats.get('unique_feeds', 0) > 0:
        st.info(f"📊 {stats.get('unique_feeds', 0)} unique feeds | "
                f"Avg duration: {stats.get('avg_duration_seconds', 0):.0f}s | "
                f"Total size: {stats.get('total_size_mb', 0):.1f} MB")
except Exception as e:
    st.warning(f"Could not load statistics: {e}")

st.divider()

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "downloaded", "transcribed", "processed", "failed"],
        index=0
    )
with col2:
    # Get unique feed names
    all_pods = db.get_all_podcasts()
    unique_feeds = sorted(set([p.get('podcast_feed_name') for p in all_pods if p.get('podcast_feed_name')]))
    feed_filter = st.selectbox(
        "Filter by Feed",
        ["All"] + unique_feeds,
        index=0
    )
with col3:
    limit = st.number_input("Limit results", min_value=10, max_value=1000, value=50, step=10)

# Get podcasts
status = None if status_filter == "All" else status_filter
all_podcasts = db.get_all_podcasts(status=status, limit=limit)

# Filter by feed if selected
if feed_filter != "All":
    podcasts = [p for p in all_podcasts if p.get('podcast_feed_name') == feed_filter]
else:
    podcasts = all_podcasts

if not podcasts:
    st.info("No podcasts found. Run batch processing to populate the database.")
    st.stop()

st.subheader(f"📋 Podcasts ({len(podcasts)} found)")

# Display podcasts in expanders
for podcast in podcasts:
    podcast_id = podcast['id']
    title = podcast.get('title', 'Untitled')
    status = podcast.get('status', 'unknown')
    published_at = podcast.get('published_at')
    processed_at = podcast.get('processed_at')
    feed_name = podcast.get('podcast_feed_name', 'Unknown')
    category = podcast.get('podcast_category', 'general')
    
    # Status badge color
    status_colors = {
        'downloaded': '🔵',
        'transcribed': '🟡',
        'processed': '🟢',
        'failed': '🔴'
    }
    status_icon = status_colors.get(status, '⚪')
    
    with st.expander(f"{status_icon} {title[:80]}", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Feed:** {feed_name}")
            st.write(f"**Category:** {category}")
            st.write(f"**Status:** {status}")
            
            if published_at:
                st.write(f"**Published:** {published_at.strftime('%Y-%m-%d %H:%M') if isinstance(published_at, datetime) else published_at}")
            if processed_at:
                st.write(f"**Processed:** {processed_at.strftime('%Y-%m-%d %H:%M') if isinstance(processed_at, datetime) else processed_at}")
            
            if podcast.get('duration_seconds'):
                duration_min = podcast['duration_seconds'] // 60
                duration_sec = podcast['duration_seconds'] % 60
                st.write(f"**Duration:** {duration_min}m {duration_sec}s")
            
            if podcast.get('file_size_bytes'):
                size_mb = podcast['file_size_bytes'] / (1024 * 1024)
                st.write(f"**File Size:** {size_mb:.1f} MB")
        
        with col2:
            if podcast.get('episode_url'):
                st.write(f"**URL:** [{podcast['episode_url'][:50]}...]({podcast['episode_url']})")
            if podcast.get('audio_file_path'):
                st.write(f"**Audio File:** `{podcast['audio_file_path']}`")
        
        # Transcript
        transcript = podcast.get('transcript')
        if transcript:
            st.subheader("📝 Transcript")
            
            if isinstance(transcript, str):
                transcript = json.loads(transcript)
            
            transcript_text = transcript.get('text', '')
            if transcript_text:
                st.text_area(
                    "Full Transcript",
                    transcript_text,
                    height=200,
                    key=f"transcript_{podcast_id}",
                    disabled=True
                )
            
            segments = transcript.get('segments', [])
            if segments:
                st.write(f"**Segments:** {len(segments)}")
                
                # Show first few segments
                with st.expander("View Segments", expanded=False):
                    for i, segment in enumerate(segments[:10]):  # Show first 10
                        start = segment.get('start', 0)
                        end = segment.get('end', 0)
                        text = segment.get('text', '')
                        st.write(f"**[{int(start)}s - {int(end)}s]** {text}")
                    if len(segments) > 10:
                        st.info(f"... and {len(segments) - 10} more segments")
        else:
            st.info("No transcript available")
        
        # Summary
        summary = podcast.get('summary')
        if summary:
            st.subheader("📊 Summary")
            
            if isinstance(summary, str):
                summary = json.loads(summary)
            
            # Full summary text
            summary_text = summary.get('summary', '')
            if summary_text:
                st.write(summary_text)
            
            # Key topics
            key_topics = summary.get('key_topics', [])
            if key_topics:
                st.write("**Key Topics:**")
                st.write(", ".join([f"`{topic}`" for topic in key_topics]))
            
            # Themes
            themes = summary.get('themes', [])
            if themes:
                st.write("**Themes:**")
                st.write(", ".join([f"`{theme}`" for theme in themes]))
            
            # Quotes
            quotes = summary.get('quotes', [])
            if quotes:
                st.write("**Notable Quotes:**")
                for quote in quotes:
                    st.write(f"> {quote}")
            
            # Startups/Companies
            startups = summary.get('startups', [])
            if startups:
                st.write("**Companies Mentioned:**")
                st.write(", ".join([f"`{startup}`" for startup in startups]))
        else:
            st.info("No summary available")
        
        # Raw data (collapsible)
        with st.expander("🔧 Raw Data (JSON)", expanded=False):
            st.json(podcast)

# Close connection
db.close()
