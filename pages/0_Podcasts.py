"""
Podcasts Page
View processed podcasts with transcripts and statistics
"""

import streamlit as st
import json
from datetime import datetime

from utils.postgres_db import PostgresDB

st.set_page_config(page_title="Podcasts", page_icon="🎙️", layout="wide")

st.title("🎙️ Processed Podcasts")

# Initialize PostgreSQL connection
try:
    db = PostgresDB()
    # Test connection by getting schema info
    schema = db.schema
    if schema and schema != 'public':
        st.sidebar.info(f"📊 Using schema: `{schema}`")
except ValueError as e:
    st.error(f"Database configuration error: {e}")
    st.info("Please ensure DB_URL is set in your .env file")
    st.stop()
except Exception as e:
    st.error(f"Failed to connect to PostgreSQL: {e}")
    st.info("Please ensure:")
    st.info("1. DB_URL is set in your .env file")
    st.info("2. PostgreSQL is running and accessible")
    st.info("3. Database schema is initialized (run schema.sql)")
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
    # Get unique feed names efficiently
    try:
        # Query distinct feed names directly from database
        from sqlalchemy import text
        with db.engine.connect() as conn:
            schema_prefix = f"{db.schema}." if db.schema != 'public' else ""
            result = conn.execute(text(
                f"SELECT DISTINCT podcast_feed_name FROM {schema_prefix}podcasts "
                f"WHERE podcast_feed_name IS NOT NULL ORDER BY podcast_feed_name"
            ))
            unique_feeds = [row[0] for row in result.fetchall()]
    except Exception as e:
        # Fallback: get from limited podcast list
        st.warning(f"Could not fetch feed list: {e}")
        limited_pods = db.get_all_podcasts(limit=100)
        unique_feeds = sorted(set([p.get('podcast_feed_name') for p in limited_pods if p.get('podcast_feed_name')]))
    
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

# Filter to only show podcasts with transcripts
podcasts_with_transcripts = []
for p in podcasts:
    transcript = p.get('transcript')
    if transcript is not None:
        # Check if transcript has actual content
        if isinstance(transcript, dict):
            transcript_text = transcript.get('text', '')
            segments = transcript.get('segments', [])
            if transcript_text or (segments and len(segments) > 0):
                podcasts_with_transcripts.append(p)
        elif isinstance(transcript, str):
            try:
                transcript_dict = json.loads(transcript)
                transcript_text = transcript_dict.get('text', '') if isinstance(transcript_dict, dict) else ''
                segments = transcript_dict.get('segments', []) if isinstance(transcript_dict, dict) else []
                if transcript_text or (segments and len(segments) > 0):
                    podcasts_with_transcripts.append(p)
            except:
                # If it's a non-JSON string, consider it valid
                if transcript.strip():
                    podcasts_with_transcripts.append(p)

podcasts = podcasts_with_transcripts

if not podcasts:
    st.info("No podcasts with transcripts found. Run batch processing to transcribe episodes.")
    st.stop()

# Count podcasts with summaries
podcasts_with_summaries = sum(1 for p in podcasts if p.get('summary') is not None)

st.subheader(f"📋 Podcasts with Transcripts ({len(podcasts)} found)")
st.caption(f"📊 {podcasts_with_summaries} with summaries")

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
        
        # Summary (shown first)
        summary = podcast.get('summary')
        if summary:
            st.subheader("📊 Summary")
            
            # Handle JSONB field - it may already be a dict or a string
            if isinstance(summary, str):
                try:
                    summary = json.loads(summary)
                except (json.JSONDecodeError, TypeError):
                    st.warning("Could not parse summary data")
                    summary = {}
            elif not isinstance(summary, dict):
                summary = {}
            
            # Full summary text
            summary_text = summary.get('summary', '') if isinstance(summary, dict) else ''
            if summary_text:
                st.write(summary_text)
            
            # Key topics
            key_topics = summary.get('key_topics', []) if isinstance(summary, dict) else []
            if key_topics:
                st.write("**Key Topics:**")
                if isinstance(key_topics, list):
                    st.write(", ".join([f"`{topic}`" for topic in key_topics if topic]))
                else:
                    st.write(str(key_topics))
            
            # Themes
            themes = summary.get('themes', []) if isinstance(summary, dict) else []
            if themes:
                st.write("**Themes:**")
                if isinstance(themes, list):
                    st.write(", ".join([f"`{theme}`" for theme in themes if theme]))
                else:
                    st.write(str(themes))
            
            # Quotes
            quotes = summary.get('quotes', []) if isinstance(summary, dict) else []
            if quotes:
                st.write("**Notable Quotes:**")
                if isinstance(quotes, list):
                    for quote in quotes:
                        if quote:
                            st.write(f"> {quote}")
                else:
                    st.write(str(quotes))
            
            # Startups/Companies
            startups = summary.get('startups', []) if isinstance(summary, dict) else []
            if startups:
                st.write("**Companies Mentioned:**")
                if isinstance(startups, list):
                    st.write(", ".join([f"`{startup}`" for startup in startups if startup]))
                else:
                    st.write(str(startups))
        else:
            st.info("No summary available")
        
        st.divider()
        
        # Transcript (shown second)
        transcript = podcast.get('transcript')
        
        if transcript is not None:
            st.subheader("📝 Transcript")
            
            # Handle JSONB field - SQLAlchemy returns JSONB as dict when retrieved
            # But handle both dict and string cases for robustness
            if isinstance(transcript, str):
                try:
                    transcript = json.loads(transcript)
                except (json.JSONDecodeError, TypeError) as e:
                    st.error(f"Could not parse transcript JSON: {e}")
                    st.code(transcript[:500], language='text')
                    transcript = {}
            elif not isinstance(transcript, dict):
                st.warning(f"Unexpected transcript type: {type(transcript)}")
                st.code(str(transcript)[:500], language='text')
                transcript = {}
            
            # Extract text and segments from transcript dict
            # Expected structure: {'text': '...', 'segments': [...], 'language': 'en', ...}
            transcript_text = ''
            segments = []
            
            if isinstance(transcript, dict):
                transcript_text = transcript.get('text', '') or ''
                segments = transcript.get('segments', []) or []
                
                # If no text but we have segments, construct text from segments
                if not transcript_text and segments:
                    transcript_text = ' '.join([
                        seg.get('text', '') 
                        for seg in segments 
                        if isinstance(seg, dict) and seg.get('text')
                    ])
            
            if transcript_text:
                # Display transcript with word count
                word_count = len(transcript_text.split())
                st.caption(f"📊 {word_count:,} words | {len(transcript_text):,} characters")
                
                # Full transcript text area
                st.text_area(
                    "Full Transcript",
                    transcript_text,
                    height=200,
                    key=f"transcript_{podcast_id}",
                    disabled=True,
                    help="Complete transcript text"
                )
            
            if segments:
                st.write(f"**Segments:** {len(segments)}")
                
                # Segment visualization options
                view_mode = st.radio(
                    "View Mode",
                    ["Timeline", "List", "Search"],
                    key=f"view_mode_{podcast_id}",
                    horizontal=True
                )
                
                if view_mode == "Timeline":
                    # Timeline view with better formatting
                    with st.expander("📊 Timeline View", expanded=True):
                        segment_limit = st.slider(
                            "Show segments",
                            min_value=10,
                            max_value=min(len(segments), 100),
                            value=min(50, len(segments)),
                            key=f"timeline_limit_{podcast_id}"
                        )
                        
                        for i, segment in enumerate(segments[:segment_limit]):
                            start = segment.get('start', 0)
                            end = segment.get('end', 0)
                            text = segment.get('text', '').strip()
                            speaker = segment.get('speaker', '')
                            
                            # Format timestamp
                            def format_time(seconds):
                                hours = int(seconds // 3600)
                                minutes = int((seconds % 3600) // 60)
                                secs = int(seconds % 60)
                                if hours > 0:
                                    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
                                return f"{minutes:02d}:{secs:02d}"
                            
                            time_str = f"{format_time(start)} - {format_time(end)}"
                            
                            # Display segment with styling
                            if speaker:
                                st.markdown(f"**{speaker}** [{time_str}]")
                            else:
                                st.markdown(f"**[{time_str}]**")
                            st.markdown(f"<div style='margin-left: 20px; margin-bottom: 10px;'>{text}</div>", unsafe_allow_html=True)
                        
                        if len(segments) > segment_limit:
                            st.info(f"... and {len(segments) - segment_limit} more segments")
                
                elif view_mode == "List":
                    # Compact list view
                    with st.expander("📋 List View", expanded=True):
                        segment_limit = st.slider(
                            "Show segments",
                            min_value=10,
                            max_value=min(len(segments), 100),
                            value=min(50, len(segments)),
                            key=f"list_limit_{podcast_id}"
                        )
                        
                        for i, segment in enumerate(segments[:segment_limit]):
                            start = segment.get('start', 0)
                            end = segment.get('end', 0)
                            text = segment.get('text', '').strip()
                            speaker = segment.get('speaker', '')
                            
                            if speaker:
                                st.write(f"**{speaker}** [{int(start)}s-{int(end)}s]: {text}")
                            else:
                                st.write(f"[{int(start)}s-{int(end)}s]: {text}")
                        
                        if len(segments) > segment_limit:
                            st.info(f"... and {len(segments) - segment_limit} more segments")
                
                elif view_mode == "Search":
                    # Search functionality
                    search_term = st.text_input(
                        "Search transcript",
                        key=f"search_{podcast_id}",
                        placeholder="Enter search term..."
                    )
                    
                    if search_term:
                        matching_segments = [
                            seg for seg in segments
                            if search_term.lower() in seg.get('text', '').lower()
                        ]
                        
                        if matching_segments:
                            st.success(f"Found {len(matching_segments)} matching segments")
                            for segment in matching_segments:
                                start = segment.get('start', 0)
                                end = segment.get('end', 0)
                                text = segment.get('text', '').strip()
                                
                                # Highlight search term
                                highlighted_text = text.replace(
                                    search_term,
                                    f"**{search_term}**"
                                )
                                
                                st.write(f"[{int(start)}s-{int(end)}s]: {highlighted_text}")
                        else:
                            st.info("No matching segments found")
                    else:
                        st.info("Enter a search term to find segments")
        else:
            st.info("No transcript available")
        
        # Raw data (collapsible)
        with st.expander("🔧 Raw Data (JSON)", expanded=False):
            st.json(podcast)

# Close connection
db.close()
