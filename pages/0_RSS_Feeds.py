"""
RSS Feeds Management Page
Configure and manage podcast RSS feeds
"""

import streamlit as st
import yaml
from pathlib import Path
from p3.database import P3Database
from p3.downloader import PodcastDownloader

st.set_page_config(page_title="RSS Feeds", page_icon="📡", layout="wide")

st.title("📡 RSS Feed Management")

# Initialize database
db = P3Database()

# Tabs for different operations
tab1, tab2, tab3 = st.tabs(["📋 View Feeds", "➕ Add Feed", "📥 Download Episodes"])

with tab1:
    st.subheader("Configured Podcast Feeds")
    
    config_file = Path("config/feeds.yaml")
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        feeds = config.get('feeds', [])
        
        if feeds:
            for idx, feed in enumerate(feeds):
                with st.expander(f"🎙️ {feed.get('name', 'Unknown')}"):
                    st.write(f"**URL:** {feed.get('url', 'N/A')}")
                    st.write(f"**Category:** {feed.get('category', 'N/A')}")
                    
                    # Check if feed exists in database
                    db_feed = db.get_podcast_by_url(feed['url'])
                    if db_feed:
                        st.success(f"✅ Feed registered in database (ID: {db_feed['id']})")
                    else:
                        st.info("ℹ️ Feed not yet in database. Download episodes to register.")
        else:
            st.info("No feeds configured yet. Add feeds in the 'Add Feed' tab.")
    else:
        st.warning("⚠️ No feeds.yaml file found. Creating default configuration...")
        
        # Create default config
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

with tab2:
    st.subheader("Add New Podcast Feed")
    
    with st.form("add_feed_form"):
        feed_name = st.text_input("Podcast Name", placeholder="e.g., Tech Talks Daily")
        feed_url = st.text_input("RSS Feed URL", placeholder="https://example.com/feed.xml")
        feed_category = st.selectbox("Category", ["tech", "business", "science", "news", "entertainment", "education", "other"])
        
        submitted = st.form_submit_button("Add Feed")
        
        if submitted:
            if not feed_name or not feed_url:
                st.error("Please provide both name and URL")
            else:
                # Load existing config
                config_file = Path("config/feeds.yaml")
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Check if feed already exists
                existing_urls = [f['url'] for f in config.get('feeds', [])]
                if feed_url in existing_urls:
                    st.error("This feed URL already exists!")
                else:
                    # Add new feed
                    new_feed = {
                        'name': feed_name,
                        'url': feed_url,
                        'category': feed_category
                    }
                    config['feeds'].append(new_feed)
                    
                    # Save config
                    with open(config_file, 'w') as f:
                        yaml.dump(config, f, default_flow_style=False)
                    
                    st.success(f"✅ Added feed: {feed_name}")
                    st.rerun()

with tab3:
    st.subheader("Download Episodes from Feeds")
    
    config_file = Path("config/feeds.yaml")
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        feeds = config.get('feeds', [])
        settings = config.get('settings', {})
        
        if feeds:
            max_episodes = st.slider(
                "Max episodes per feed",
                min_value=1,
                max_value=20,
                value=settings.get('max_episodes_per_feed', 5)
            )
            
            download_dir = st.text_input(
                "Download directory",
                value=settings.get('download_dir', 'data/audio')
            )
            
            if st.button("📥 Download Episodes", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                downloader = PodcastDownloader(db, download_dir=download_dir)
                
                total_feeds = len(feeds)
                total_downloaded = 0
                
                for idx, feed in enumerate(feeds):
                    status_text.text(f"Processing: {feed['name']}...")
                    
                    try:
                        count = downloader.download_from_feed(
                            feed['url'],
                            feed['name'],
                            feed.get('category', 'general'),
                            max_episodes=max_episodes
                        )
                        total_downloaded += count
                        st.success(f"✅ {feed['name']}: Downloaded {count} episodes")
                    except Exception as e:
                        st.error(f"❌ {feed['name']}: {str(e)}")
                    
                    progress_bar.progress((idx + 1) / total_feeds)
                
                status_text.text("Download complete!")
                st.success(f"🎉 Downloaded {total_downloaded} total episodes")
        else:
            st.info("No feeds configured. Add feeds in the 'Add Feed' tab first.")
    else:
        st.error("No feeds.yaml found. Please configure feeds first.")

# Cleanup
db.close()

# Sidebar info
with st.sidebar:
    st.markdown("### 📡 RSS Feed Management")
    st.markdown("""
    **Features:**
    - View configured feeds
    - Add new podcast feeds
    - Download episodes from feeds
    - Automatic database registration
    
    **Supported Formats:**
    - RSS 2.0
    - Atom feeds
    - iTunes podcast feeds
    """)
