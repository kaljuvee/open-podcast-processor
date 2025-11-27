"""
Download Episodes Page
Simple interface for downloading podcast episodes from RSS feeds
"""

import streamlit as st
import yaml
from pathlib import Path
from p3.database import P3Database
from p3.downloader import PodcastDownloader

st.set_page_config(page_title="Download Episodes", page_icon="📥", layout="wide")

st.title("📥 Download Podcast Episodes")
st.markdown("**Step 1**: Select feeds and download episodes to get started")

# Initialize database
db = P3Database()

# Load configuration
config_file = Path("config/feeds.yaml")

if not config_file.exists():
    st.error("⚠️ No feeds.yaml file found. Creating default configuration...")
    config_file.parent.mkdir(parents=True, exist_ok=True)
    default_config = {
        'feeds': [],
        'settings': {
            'max_episodes_per_feed': 5,
            'download_dir': 'data/audio'
        }
    }
    with open(config_file, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)
    st.success("✅ Created default feeds.yaml")
    st.rerun()

with open(config_file, 'r') as f:
    config = yaml.safe_load(f)

feeds = config.get('feeds', [])
settings = config.get('settings', {})

if not feeds:
    st.warning("⚠️ No feeds configured yet.")
    st.info("Add feeds to config/feeds.yaml to get started")
    st.stop()

# Main download interface
st.markdown("### 🎙️ Available Podcast Feeds")
st.info(f"Found {len(feeds)} configured feeds")

# Settings
col1, col2 = st.columns(2)

with col1:
    max_episodes = st.number_input(
        "Episodes per feed",
        min_value=1,
        max_value=20,
        value=settings.get('max_episodes_per_feed', 5),
        help="Number of latest episodes to download from each feed"
    )

with col2:
    selected_feeds = st.multiselect(
        "Select feeds to download",
        options=[f"{feed['name']} ({feed.get('category', 'general')})" for feed in feeds],
        default=[f"{feed['name']} ({feed.get('category', 'general')})" for feed in feeds[:3]],
        help="Select which feeds you want to download episodes from"
    )

# Show selected feeds
if selected_feeds:
    st.markdown(f"**Selected**: {len(selected_feeds)} feed(s)")
    
    # Download button
    if st.button("📥 Download Episodes Now", type="primary", use_container_width=True):
        # Create progress indicators
        progress_bar = st.progress(0)
        status_container = st.container()
        
        downloader = PodcastDownloader(db, data_dir="data")
        
        total_feeds = len(selected_feeds)
        total_downloaded = 0
        
        with status_container:
            for idx, selected_feed in enumerate(selected_feeds):
                # Find the feed config
                feed_name = selected_feed.split(' (')[0]
                feed = next((f for f in feeds if f['name'] == feed_name), None)
                
                if not feed:
                    continue
                
                with st.spinner(f"📥 Downloading from {feed['name']}..."):
                    try:
                        # Add feed to database
                        podcast_id = downloader.add_feed(
                            feed['name'],
                            feed['url'],
                            feed.get('category', 'general')
                        )
                        
                        # Process feed and download episodes
                        count = downloader.process_feed(feed['url'])
                        total_downloaded += count
                        st.success(f"✅ {feed['name']}: Downloaded {count} episodes")
                    except Exception as e:
                        st.error(f"❌ {feed['name']}: {str(e)}")
                        import traceback
                        st.error(traceback.format_exc())
                
                progress_bar.progress((idx + 1) / total_feeds)
        
        st.success(f"🎉 Download complete! Total: {total_downloaded} episodes")
        
        # Show next step
        st.markdown("---")
        st.markdown("### ✅ Next Step: Process Episodes")
        st.info(f"You now have {total_downloaded} episodes ready to process!")
        
        if st.button("⚙️ Go to Process →", type="primary"):
            st.switch_page("pages/1_Process.py")
else:
    st.warning("⚠️ Please select at least one feed to download")

# Show feed list
st.markdown("---")
st.markdown("### 📋 Configured Feeds")

for feed in feeds:
    with st.expander(f"🎙️ {feed.get('name', 'Unknown')} - {feed.get('category', 'N/A')}"):
        st.write(f"**URL:** {feed.get('url', 'N/A')}")
        
        # Check if feed exists in database
        db_feed = db.get_podcast_by_url(feed['url'])
        if db_feed:
            st.success(f"✅ Registered in database (ID: {db_feed['id']})")
        else:
            st.info("ℹ️ Not yet in database. Download episodes to register.")

# Sidebar
with st.sidebar:
    st.markdown("### 📥 Download Episodes")
    st.markdown("---")
    
    st.markdown("### 💡 Tips")
    st.markdown("""
    - Start with 3-5 episodes per feed
    - Select feeds you're interested in
    - Download takes ~30 seconds per episode
    - Episodes are saved to `data/audio/`
    """)
    
    st.markdown("---")
    
    st.markdown("### 📊 Current Status")
    try:
        downloaded_count = len(db.get_episodes_by_status('downloaded'))
        transcribed_count = len(db.get_episodes_by_status('transcribed'))
        processed_count = len(db.get_episodes_by_status('processed'))
        
        st.metric("Downloaded", downloaded_count)
        st.metric("Transcribed", transcribed_count)
        st.metric("Processed", processed_count)
    except:
        st.metric("Downloaded", 0)
        st.metric("Transcribed", 0)
        st.metric("Processed", 0)

# Cleanup
db.close()
