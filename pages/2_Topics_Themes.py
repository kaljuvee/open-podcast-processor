"""
Topics & Themes Page
Visualize topics and themes counts per podcast with bubble charts
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter, defaultdict
import json

from utils.postgres_db import PostgresDB

st.set_page_config(page_title="Topics & Themes", page_icon="🔍", layout="wide")

st.title("🔍 Topics & Themes Analysis")
st.markdown("Visualize topics and themes distribution across podcasts")

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
    
    show_type = st.radio(
        "Show",
        ["Themes", "Topics", "Both"],
        index=2,
        help="Choose what to visualize"
    )

# Load podcasts with summaries
@st.cache_data(ttl=3600)
def load_podcasts_with_summaries(feed_filter: str = "All"):
    """Load podcasts with their summaries."""
    podcasts = db.get_all_podcasts(status=None, limit=1000)
    
    # Filter by feed if specified
    if feed_filter != "All":
        podcasts = [p for p in podcasts if p.get('podcast_feed_name') == feed_filter]
    
    # Extract summaries
    podcast_data = []
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
        
        themes = summary.get('themes', [])
        topics = summary.get('key_topics', [])
        
        if not themes and not topics:
            continue
        
        podcast_data.append({
            'id': podcast['id'],
            'title': podcast.get('title', 'Untitled'),
            'feed_name': podcast.get('podcast_feed_name', 'Unknown'),
            'category': podcast.get('podcast_category', 'general'),
            'published_at': podcast.get('published_at'),
            'themes': themes if isinstance(themes, list) else [],
            'topics': topics if isinstance(topics, list) else [],
            'theme_count': len(themes) if isinstance(themes, list) else 0,
            'topic_count': len(topics) if isinstance(topics, list) else 0
        })
    
    return podcast_data

# Load data
podcast_data = load_podcasts_with_summaries(feed_filter)

if not podcast_data:
    st.warning("No podcasts with summaries found. Please process some episodes first.")
    st.info("Go to the Process page to generate summaries with themes and topics.")
    st.stop()

st.success(f"✅ Loaded {len(podcast_data)} podcasts with summaries")

# Display statistics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Podcasts", len(podcast_data))
with col2:
    total_themes = sum(p['theme_count'] for p in podcast_data)
    st.metric("Total Themes", total_themes)
with col3:
    total_topics = sum(p['topic_count'] for p in podcast_data)
    st.metric("Total Topics", total_topics)
with col4:
    unique_feeds = len(set(p['feed_name'] for p in podcast_data))
    st.metric("Unique Feeds", unique_feeds)

st.divider()

# Prepare data for visualization
if show_type in ["Themes", "Both"]:
    st.subheader("🎨 Themes Distribution")
    
    # Collect all themes with podcast info
    theme_data = []
    for pod in podcast_data:
        for theme in pod['themes']:
            if theme:  # Skip empty themes
                theme_data.append({
                    'Podcast': pod['title'][:50],
                    'Podcast ID': pod['id'],
                    'Feed': pod['feed_name'],
                    'Theme': theme,
                    'Type': 'Theme'
                })
    
    if theme_data:
        theme_df = pd.DataFrame(theme_data)
        
        # Count themes per podcast
        theme_counts = theme_df.groupby(['Podcast', 'Feed']).size().reset_index(name='Count')
        theme_counts = theme_counts.sort_values('Count', ascending=False)
        
        # Bubble chart: Themes per Podcast
        fig1 = px.scatter(
            theme_counts,
            x='Podcast',
            y='Count',
            size='Count',
            color='Feed',
            title="Theme Counts per Podcast",
            labels={'Count': 'Number of Themes', 'Podcast': 'Podcast Title'},
            hover_data=['Feed'],
            size_max=30
        )
        fig1.update_layout(
            height=500,
            xaxis_tickangle=-45,
            xaxis={'categoryorder': 'total descending'}
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        # Bubble chart: Theme frequency across all podcasts
        theme_freq = theme_df.groupby('Theme').size().reset_index(name='Frequency')
        theme_freq = theme_freq.sort_values('Frequency', ascending=False).head(30)
        
        # Get podcast count per theme
        theme_podcast_count = theme_df.groupby('Theme')['Podcast'].nunique().reset_index(name='Podcast Count')
        theme_freq = theme_freq.merge(theme_podcast_count, on='Theme', how='left')
        
        fig2 = px.scatter(
            theme_freq,
            x='Theme',
            y='Frequency',
            size='Podcast Count',
            color='Frequency',
            title="Most Common Themes (Bubble size = Number of Podcasts)",
            labels={'Frequency': 'Total Occurrences', 'Theme': 'Theme Name'},
            hover_data=['Podcast Count'],
            color_continuous_scale='Viridis',
            size_max=30
        )
        fig2.update_layout(
            height=500,
            xaxis_tickangle=-45,
            xaxis={'categoryorder': 'total descending'}
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # Table: Themes per podcast
        with st.expander("📋 Themes per Podcast (Table)", expanded=False):
            st.dataframe(
                theme_counts[['Podcast', 'Feed', 'Count']],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No themes found in summaries")

if show_type in ["Topics", "Both"]:
    st.subheader("📚 Topics Distribution")
    
    # Collect all topics with podcast info
    topic_data = []
    for pod in podcast_data:
        for topic in pod['topics']:
            if topic:  # Skip empty topics
                topic_data.append({
                    'Podcast': pod['title'][:50],
                    'Podcast ID': pod['id'],
                    'Feed': pod['feed_name'],
                    'Topic': topic,
                    'Type': 'Topic'
                })
    
    if topic_data:
        topic_df = pd.DataFrame(topic_data)
        
        # Count topics per podcast
        topic_counts = topic_df.groupby(['Podcast', 'Feed']).size().reset_index(name='Count')
        topic_counts = topic_counts.sort_values('Count', ascending=False)
        
        # Bubble chart: Topics per Podcast
        fig3 = px.scatter(
            topic_counts,
            x='Podcast',
            y='Count',
            size='Count',
            color='Feed',
            title="Topic Counts per Podcast",
            labels={'Count': 'Number of Topics', 'Podcast': 'Podcast Title'},
            hover_data=['Feed'],
            size_max=30
        )
        fig3.update_layout(
            height=500,
            xaxis_tickangle=-45,
            xaxis={'categoryorder': 'total descending'}
        )
        st.plotly_chart(fig3, use_container_width=True)
        
        # Bubble chart: Topic frequency across all podcasts
        topic_freq = topic_df.groupby('Topic').size().reset_index(name='Frequency')
        topic_freq = topic_freq.sort_values('Frequency', ascending=False).head(30)
        
        # Get podcast count per topic
        topic_podcast_count = topic_df.groupby('Topic')['Podcast'].nunique().reset_index(name='Podcast Count')
        topic_freq = topic_freq.merge(topic_podcast_count, on='Topic', how='left')
        
        fig4 = px.scatter(
            topic_freq,
            x='Topic',
            y='Frequency',
            size='Podcast Count',
            color='Frequency',
            title="Most Common Topics (Bubble size = Number of Podcasts)",
            labels={'Frequency': 'Total Occurrences', 'Topic': 'Topic Name'},
            hover_data=['Podcast Count'],
            color_continuous_scale='Plasma',
            size_max=30
        )
        fig4.update_layout(
            height=500,
            xaxis_tickangle=-45,
            xaxis={'categoryorder': 'total descending'}
        )
        st.plotly_chart(fig4, use_container_width=True)
        
        # Table: Topics per podcast
        with st.expander("📋 Topics per Podcast (Table)", expanded=False):
            st.dataframe(
                topic_counts[['Podcast', 'Feed', 'Count']],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No topics found in summaries")

if show_type == "Both":
    st.subheader("🔗 Combined View")
    
    # Combined bubble chart: Podcast vs Theme/Topic counts
    combined_data = []
    for pod in podcast_data:
        combined_data.append({
            'Podcast': pod['title'][:50],
            'Feed': pod['feed_name'],
            'Themes': pod['theme_count'],
            'Topics': pod['topic_count'],
            'Total': pod['theme_count'] + pod['topic_count']
        })
    
    combined_df = pd.DataFrame(combined_data)
    
    # Bubble chart: Themes vs Topics per podcast
    fig5 = px.scatter(
        combined_df,
        x='Themes',
        y='Topics',
        size='Total',
        color='Feed',
        title="Themes vs Topics per Podcast (Bubble size = Total count)",
        labels={'Themes': 'Number of Themes', 'Topics': 'Number of Topics'},
        hover_data=['Podcast', 'Feed'],
        size_max=30
    )
    fig5.update_layout(height=500)
    st.plotly_chart(fig5, use_container_width=True)
    
    # Summary table
    with st.expander("📊 Summary Table", expanded=False):
        summary_df = combined_df[['Podcast', 'Feed', 'Themes', 'Topics', 'Total']].sort_values('Total', ascending=False)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

# Close connection
db.close()
