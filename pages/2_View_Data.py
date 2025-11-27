"""
View Data Page
Browse and explore processed podcast content
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from p3.database import P3Database

st.set_page_config(page_title="View Data", page_icon="📊", layout="wide")

st.title("📊 View Processed Content")

# Initialize database
db = P3Database()

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📋 Summaries", "📝 Transcripts", "🎙️ Episodes", "📈 Analytics"])

with tab1:
    st.subheader("Episode Summaries")
    
    # Get processed episodes
    processed_episodes = db.get_episodes_by_status('processed')
    
    if processed_episodes:
        st.info(f"Found {len(processed_episodes)} processed episodes")
        
        # Date filter
        date_range = st.date_input(
            "Filter by date range",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
            key="summary_date_filter"
        )
        
        # Get summaries for date range
        if len(date_range) == 2:
            start_date, end_date = date_range
            
            summaries = []
            for single_date in pd.date_range(start_date, end_date):
                day_summaries = db.get_summaries_by_date(single_date)
                summaries.extend(day_summaries)
            
            if summaries:
                st.success(f"Found {len(summaries)} summaries in date range")
                
                # Display summaries
                for summary in summaries:
                    with st.expander(f"🎙️ {summary['episode_title']} - {summary['podcast_title']}"):
                        st.markdown(f"**Date:** {summary['digest_date']}")
                        
                        # Summary
                        st.markdown("### 📝 Summary")
                        st.write(summary['full_summary'])
                        
                        # Key Topics
                        if summary['key_topics']:
                            st.markdown("### 🔑 Key Topics")
                            topics_str = ", ".join(summary['key_topics'])
                            st.write(topics_str)
                        
                        # Themes
                        if summary['themes']:
                            st.markdown("### 🎨 Themes")
                            themes_str = ", ".join(summary['themes'])
                            st.write(themes_str)
                        
                        # Quotes
                        if summary['quotes']:
                            st.markdown("### 💬 Notable Quotes")
                            for quote in summary['quotes']:
                                st.markdown(f"> {quote}")
                        
                        # Companies/Startups
                        if summary['startups']:
                            st.markdown("### 🏢 Companies Mentioned")
                            companies_str = ", ".join(summary['startups'])
                            st.write(companies_str)
                        
                        # Export button
                        export_data = {
                            'episode': summary['episode_title'],
                            'podcast': summary['podcast_title'],
                            'date': str(summary['digest_date']),
                            'summary': summary['full_summary'],
                            'key_topics': summary['key_topics'],
                            'themes': summary['themes'],
                            'quotes': summary['quotes'],
                            'startups': summary['startups']
                        }
                        
                        st.download_button(
                            label="📥 Download as JSON",
                            data=json.dumps(export_data, indent=2),
                            file_name=f"summary_{summary['episode_id']}.json",
                            mime="application/json",
                            key=f"download_{summary['id']}"
                        )
            else:
                st.info("No summaries found in the selected date range")
    else:
        st.info("No processed episodes yet. Process episodes from the Processing page.")

with tab2:
    st.subheader("Episode Transcripts")
    
    # Get transcribed or processed episodes
    transcribed = db.get_episodes_by_status('transcribed')
    processed = db.get_episodes_by_status('processed')
    all_transcribed = transcribed + processed
    
    if all_transcribed:
        st.info(f"Found {len(all_transcribed)} episodes with transcripts")
        
        # Episode selector
        episode_options = {f"{ep['title']} - {ep['podcast_title']}": ep['id'] for ep in all_transcribed}
        selected_episode = st.selectbox("Select Episode", list(episode_options.keys()))
        
        if selected_episode:
            episode_id = episode_options[selected_episode]
            
            # Get transcript segments
            segments = db.get_transcripts_for_episode(episode_id)
            
            if segments:
                st.success(f"Found {len(segments)} transcript segments")
                
                # Display options
                display_mode = st.radio("Display Mode", ["Full Text", "Segmented", "Table"])
                
                if display_mode == "Full Text":
                    full_text = "\n\n".join([seg['text'] for seg in segments])
                    st.text_area("Transcript", full_text, height=400)
                    
                    # Download button
                    st.download_button(
                        label="📥 Download Transcript",
                        data=full_text,
                        file_name=f"transcript_{episode_id}.txt",
                        mime="text/plain"
                    )
                
                elif display_mode == "Segmented":
                    for idx, seg in enumerate(segments):
                        with st.expander(f"Segment {idx + 1} ({seg['timestamp_start']:.2f}s - {seg['timestamp_end']:.2f}s)"):
                            st.write(seg['text'])
                
                else:  # Table
                    df = pd.DataFrame([
                        {
                            'Segment': idx + 1,
                            'Start (s)': seg['timestamp_start'],
                            'End (s)': seg['timestamp_end'],
                            'Text': seg['text'][:100] + "..." if len(seg['text']) > 100 else seg['text']
                        }
                        for idx, seg in enumerate(segments)
                    ])
                    st.dataframe(df, use_container_width=True)
            else:
                st.warning("No transcript segments found for this episode")
    else:
        st.info("No transcribed episodes yet. Transcribe episodes from the Processing page.")

with tab3:
    st.subheader("All Episodes")
    
    # Get all episodes
    all_statuses = ['downloaded', 'transcribed', 'processed']
    all_episodes = []
    
    for status in all_statuses:
        episodes = db.get_episodes_by_status(status)
        all_episodes.extend(episodes)
    
    if all_episodes:
        st.info(f"Total episodes: {len(all_episodes)}")
        
        # Create DataFrame
        df_data = []
        for ep in all_episodes:
            df_data.append({
                'ID': ep['id'],
                'Title': ep['title'],
                'Podcast': ep['podcast_title'],
                'Date': ep['date'],
                'Status': ep['status'],
                'Duration (s)': ep['duration_seconds'] or 'N/A'
            })
        
        df = pd.DataFrame(df_data)
        
        # Filters
        col1, col2 = st.columns(2)
        
        with col1:
            status_filter = st.multiselect(
                "Filter by Status",
                options=['downloaded', 'transcribed', 'processed'],
                default=['downloaded', 'transcribed', 'processed']
            )
        
        with col2:
            podcasts = df['Podcast'].unique().tolist()
            podcast_filter = st.multiselect(
                "Filter by Podcast",
                options=podcasts,
                default=podcasts
            )
        
        # Apply filters
        filtered_df = df[
            (df['Status'].isin(status_filter)) &
            (df['Podcast'].isin(podcast_filter))
        ]
        
        st.dataframe(filtered_df, use_container_width=True)
        
        # Export filtered data
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="episodes.csv",
            mime="text/csv"
        )
    else:
        st.info("No episodes in database. Download episodes from the RSS Feeds page.")

with tab4:
    st.subheader("Analytics Dashboard")
    
    # Get all episodes
    all_statuses = ['downloaded', 'transcribed', 'processed']
    all_episodes = []
    
    for status in all_statuses:
        episodes = db.get_episodes_by_status(status)
        all_episodes.extend(episodes)
    
    if all_episodes:
        # Status distribution
        st.markdown("### 📊 Status Distribution")
        
        status_counts = {}
        for status in all_statuses:
            status_counts[status] = len(db.get_episodes_by_status(status))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📥 Downloaded", status_counts['downloaded'])
        with col2:
            st.metric("🎯 Transcribed", status_counts['transcribed'])
        with col3:
            st.metric("✅ Processed", status_counts['processed'])
        
        # Podcast distribution
        st.markdown("### 🎙️ Episodes by Podcast")
        
        podcast_counts = {}
        for ep in all_episodes:
            podcast = ep['podcast_title']
            podcast_counts[podcast] = podcast_counts.get(podcast, 0) + 1
        
        df_podcasts = pd.DataFrame([
            {'Podcast': k, 'Episodes': v}
            for k, v in podcast_counts.items()
        ]).sort_values('Episodes', ascending=False)
        
        st.bar_chart(df_podcasts.set_index('Podcast'))
        
        # Timeline
        st.markdown("### 📅 Episodes Over Time")
        
        df_episodes = pd.DataFrame(all_episodes)
        if 'date' in df_episodes.columns:
            df_episodes['date'] = pd.to_datetime(df_episodes['date'])
            df_episodes['date_only'] = df_episodes['date'].dt.date
            
            timeline = df_episodes.groupby('date_only').size().reset_index(name='count')
            timeline.columns = ['Date', 'Episodes']
            
            st.line_chart(timeline.set_index('Date'))
    else:
        st.info("No data available for analytics. Download and process episodes first.")

# Cleanup
db.close()

# Sidebar info
with st.sidebar:
    st.markdown("### 📊 Data Views")
    st.markdown("""
    **Available Views:**
    - **Summaries** - Browse AI-generated summaries
    - **Transcripts** - Read full transcripts
    - **Episodes** - View all episodes
    - **Analytics** - Explore statistics
    
    **Export Options:**
    - JSON format for summaries
    - TXT format for transcripts
    - CSV format for episode lists
    """)
