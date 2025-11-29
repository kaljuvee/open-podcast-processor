"""
Topics Page
Visualize topics distribution across podcasts with a treemap
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
import json

from utils.postgres_db import PostgresDB

st.set_page_config(page_title="Topics", page_icon="🔍", layout="wide")

st.title("🔍 Topics Analysis")
st.markdown("Visualize topics distribution across podcasts with semantic clustering")

# Initialize PostgreSQL connection
try:
    db = PostgresDB()
    schema = db.schema
    if schema and schema != 'public':
        st.sidebar.info(f"📊 Using schema: `{schema}`")
except ValueError as e:
    st.error(f"Database configuration error: {e}")
    st.info("Please ensure DB_URL is set in your .env file")
    st.stop()
except Exception as e:
    st.error(f"Failed to connect to PostgreSQL: {e}")
    st.stop()

# Sidebar filters
with st.sidebar:
    st.header("📊 Filters")
    
    # Get unique feed names
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            schema_prefix = f"{db.schema}." if db.schema != 'public' else ""
            result = conn.execute(text(
                f"SELECT DISTINCT podcast_feed_name FROM {schema_prefix}podcasts "
                f"WHERE podcast_feed_name IS NOT NULL ORDER BY podcast_feed_name"
            ))
            unique_feeds = [row[0] for row in result.fetchall()]
    except Exception as e:
        unique_feeds = []
    
    feed_filter = st.selectbox(
        "Filter by Feed",
        ["All"] + unique_feeds,
        index=0
    )
    
    min_topic_frequency = st.number_input(
        "Min Topic Frequency",
        min_value=1,
        max_value=10,
        value=1,
        step=1,
        help="Only show topics that appear in at least this many podcasts"
    )

# Load podcasts with summaries
@st.cache_data(ttl=3600)
def load_topics_data(feed_filter: str = "All", min_frequency: int = 1):
    """Load topics from podcast summaries."""
    podcasts = db.get_all_podcasts(status=None, limit=1000)
    
    # Filter by feed if specified
    if feed_filter != "All":
        podcasts = [p for p in podcasts if p.get('podcast_feed_name') == feed_filter]
    
    # Extract topics
    topic_data = []
    topic_counter = Counter()
    
    for podcast in podcasts:
        summary = podcast.get('summary')
        if not summary:
            continue
        
        # Handle JSONB field
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except:
                continue
        elif not isinstance(summary, dict):
            continue
        
        topics = summary.get('key_topics', [])
        if not topics or not isinstance(topics, list):
            continue
        
        feed_name = podcast.get('podcast_feed_name', 'Unknown')
        podcast_title = podcast.get('title', 'Untitled')
        
        for topic in topics:
            if topic and isinstance(topic, str):
                topic_data.append({
                    'Topic': topic,
                    'Feed': feed_name,
                    'Podcast': podcast_title[:50],
                    'Podcast ID': podcast['id']
                })
                topic_counter[topic] += 1
    
    # Filter by minimum frequency
    if min_frequency > 1:
        topic_data = [
            t for t in topic_data 
            if topic_counter[t['Topic']] >= min_frequency
        ]
    
    return topic_data, topic_counter

# Load data
topic_data, topic_counter = load_topics_data(feed_filter, min_topic_frequency)

if not topic_data:
    st.warning("No topics found matching your criteria. Please process some episodes first.")
    st.info("Go to the Process page to generate summaries with topics.")
    st.stop()

st.success(f"✅ Loaded {len(topic_data)} topic occurrences from {len(set(t['Podcast ID'] for t in topic_data))} podcasts")

# Display statistics
col1, col2, col3, col4 = st.columns(4)
with col1:
    unique_podcasts = len(set(t['Podcast ID'] for t in topic_data))
    st.metric("Total Podcasts", unique_podcasts)
with col2:
    unique_topics = len(topic_counter)
    st.metric("Unique Topics", unique_topics)
with col3:
    total_occurrences = len(topic_data)
    st.metric("Total Occurrences", total_occurrences)
with col4:
    unique_feeds_count = len(set(t['Feed'] for t in topic_data))
    st.metric("Unique Feeds", unique_feeds_count)

st.divider()

# Prepare data for treemap
# Create hierarchical structure: Feed > Topic
treemap_data = []
for topic, frequency in topic_counter.most_common():
    # Get all occurrences of this topic
    topic_occurrences = [t for t in topic_data if t['Topic'] == topic]
    
    # Group by feed
    feed_groups = {}
    for occ in topic_occurrences:
        feed = occ['Feed']
        if feed not in feed_groups:
            feed_groups[feed] = []
        feed_groups[feed].append(occ)
    
    # Create treemap entries
    for feed, occurrences in feed_groups.items():
        treemap_data.append({
            'Feed': feed,
            'Topic': topic,
            'Frequency': len(occurrences),
            'Podcast Count': len(set(occ['Podcast ID'] for occ in occurrences)),
            'Path': f"{feed} > {topic}",
            'Parent': feed
        })
    
    # Also add aggregate entry for the topic across all feeds
    treemap_data.append({
        'Feed': 'All Feeds',
        'Topic': topic,
        'Frequency': frequency,
        'Podcast Count': len(set(occ['Podcast ID'] for occ in topic_occurrences)),
        'Path': f"All Topics > {topic}",
        'Parent': 'All Topics'
    })

treemap_df = pd.DataFrame(treemap_data)

# Create treemap visualization
st.subheader("📊 Topics Treemap")
st.markdown("**Size** = Topic frequency | **Color** = Number of podcasts mentioning the topic")

if len(treemap_df) > 0:
    # Create treemap with hierarchical structure
    fig = px.treemap(
        treemap_df,
        path=[px.Constant("All Topics"), 'Feed', 'Topic'],
        values='Frequency',
        color='Podcast Count',
        color_continuous_scale='Viridis',
        title="Topics Distribution (Size = Frequency, Color = Podcast Count)",
        hover_data=['Frequency', 'Podcast Count'],
        labels={
            'Frequency': 'Occurrences',
            'Podcast Count': 'Podcasts',
            'Topic': 'Topic Name',
            'Feed': 'Feed Name'
        }
    )
    
    fig.update_layout(
        height=700,
        margin=dict(t=50, l=25, r=25, b=25)
    )
    
    fig.update_traces(
        textinfo="label+value",
        textfont_size=12,
        hovertemplate='<b>%{label}</b><br>' +
                      'Frequency: %{value}<br>' +
                      'Podcasts: %{color}<br>' +
                      '<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show top topics table
    with st.expander("📋 Top Topics Table", expanded=False):
        # Aggregate by topic
        topic_summary = []
        for topic, frequency in topic_counter.most_common():
            topic_occurrences = [t for t in topic_data if t['Topic'] == topic]
            podcast_ids = set(t['Podcast ID'] for t in topic_occurrences)
            feeds = set(t['Feed'] for t in topic_occurrences)
            
            topic_summary.append({
                'Topic': topic,
                'Frequency': frequency,
                'Podcast Count': len(podcast_ids),
                'Feed Count': len(feeds),
                'Feeds': ', '.join(sorted(feeds)[:3]) + ('...' if len(feeds) > 3 else '')
            })
        
        summary_df = pd.DataFrame(topic_summary)
        summary_df = summary_df.sort_values('Frequency', ascending=False)
        
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No topics found matching your criteria")

# Close connection
db.close()
