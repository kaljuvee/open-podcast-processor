"""
Download Episodes Page
Simple interface for downloading podcast episodes from RSS feeds
"""

import streamlit as st
from pathlib import Path
from utils.postgres_db import PostgresDB
from utils.download import download_feeds

st.set_page_config(page_title="Download Episodes", page_icon="📥", layout="wide")

st.title("📥 Download Podcast Episodes")
st.markdown("**Step 1**: Add feeds and download episodes to get started")

# Initialize database
try:
    db = PostgresDB()
except Exception as e:
    st.error(f"Failed to connect to PostgreSQL: {e}")
    st.info("Please ensure DB_URL is set in your .env file")
    st.stop()

# Default user
DEFAULT_USER_EMAIL = "kaljuvee@gmail.com"
user_id = db.get_or_create_user(DEFAULT_USER_EMAIL, name="Default User")

# Load feeds from database
feeds = db.get_user_feeds(user_id=user_id)

# Add Feed Section
with st.expander("➕ Add New Feed", expanded=len(feeds) == 0):
    st.markdown("**Paste an RSS feed URL to add it:**")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        feed_url = st.text_input(
            "RSS Feed URL",
            placeholder="https://example.com/feed/podcast",
            key="new_feed_url",
            label_visibility="collapsed"
        )
    with col2:
        feed_category = st.selectbox(
            "Category",
            ["trading", "business", "venture", "product", "saas", "ai", "investing", "general"],
            key="new_feed_category"
        )
    
    if st.button("➕ Add Feed", type="primary"):
        if feed_url:
            try:
                # Try to fetch feed to get name
                import feedparser
                parsed = feedparser.parse(feed_url)
                
                if parsed.bozo:
                    st.warning("⚠️ Could not parse feed. Please check the URL.")
                else:
                    feed_name = parsed.feed.get('title', feed_url.split('/')[-1])
                    
                    # Add feed to database
                    feed_id = db.add_feed(
                        name=feed_name,
                        url=feed_url,
                        category=feed_category,
                        user_id=user_id
                    )
                    
                    st.success(f"✅ Added feed: {feed_name}")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to add feed: {e}")
        else:
            st.warning("Please enter a feed URL")

if not feeds:
    st.warning("⚠️ No feeds configured yet.")
    st.info("Add feeds using the form above to get started")
else:
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
        value=5,
        help="Number of latest episodes to download from each feed"
    )

with col2:
    selected_feeds = st.multiselect(
        "Select feeds to download",
        options=[f"{feed['name']} ({feed.get('category', 'general')})" for feed in feeds],
        default=[f"{feed['name']} ({feed.get('category', 'general')})" for feed in feeds[:min(3, len(feeds))]],
        help="Select which feeds you want to download episodes from"
    )

# Show selected feeds
if selected_feeds:
    st.markdown(f"**Selected**: {len(selected_feeds)} feed(s)")
    
    # Check ffmpeg availability
    from utils.audio import check_ffmpeg_installed
    ffmpeg_available, ffmpeg_info = check_ffmpeg_installed()
    
    if not ffmpeg_available:
        st.warning("⚠️ **ffmpeg not found** - Audio normalization will be skipped. Install ffmpeg for best results.")
        st.code("sudo apt-get install ffmpeg  # Ubuntu/Debian\nbrew install ffmpeg  # macOS")
    else:
        st.success(f"✅ **ffmpeg available** - Audio will be normalized")
        if ffmpeg_info:
            st.caption(f"Version: {ffmpeg_info[:50]}...")
    
    st.markdown("---")
    
    # Download button
    if st.button("📥 Download Episodes Now", type="primary", use_container_width=True):
        # Create progress indicators
        overall_progress = st.progress(0)
        status_container = st.container()
        status_text = st.empty()
        
        # Extract feed configs for selected feeds
        selected_feed_configs = []
        
        for selected_feed in selected_feeds:
            feed_name = selected_feed.split(' (')[0]
            feed = next((f for f in feeds if f['name'] == feed_name), None)
            if feed:
                # Convert database feed to config format
                selected_feed_configs.append({
                    'name': feed['name'],
                    'url': feed['url'],
                    'category': feed.get('category', 'general')
                })
        
        total_feeds = len(selected_feed_configs)
        
        with status_container:
            try:
                status_text.info(f"🔄 Starting download of {total_feeds} feed(s)...")
                
                # Process feeds one by one with progress updates
                results = {
                    'total_downloaded': 0,
                    'feed_results': {}
                }
                
                # Create feed progress container
                feed_progress_container = st.container()
                
                for idx, feed_config in enumerate(selected_feed_configs):
                    feed_name = feed_config['name']
                    progress = idx / total_feeds
                    overall_progress.progress(progress)
                    status_text.info(f"📥 Processing feed {idx + 1}/{total_feeds}: {feed_name}...")
                    
                    # Show spinner for this feed
                    with feed_progress_container:
                        with st.spinner(f"Downloading from {feed_name}..."):
                            # Use PodcastDownloader with PostgreSQL
                            from utils.downloader import PodcastDownloader
                            
                            # Ensure feed exists in database
                            downloader = PodcastDownloader(db=db, data_dir="data", max_episodes=max_episodes)
                            feed_id = downloader.add_feed(
                                name=feed_config['name'],
                                url=feed_config['url'],
                                category=feed_config.get('category', 'general')
                            )
                            
                            # Process feed and download episodes
                            count = downloader.process_feed(feed_config['url'])
                            
                            # Convert to expected format
                            feed_results = {
                                'total_downloaded': count,
                                'feed_results': {feed_config['name']: count}
                            }
                    
                    count = feed_results['total_downloaded']
                    results['feed_results'][feed_name] = count
                    results['total_downloaded'] += count
                    
                    if count > 0:
                        st.success(f"✅ {feed_name}: Downloaded {count} new episode(s)")
                    else:
                        st.info(f"ℹ️ {feed_name}: No new episodes (may already exist)")
                
                # Complete
                overall_progress.progress(1.0)
                status_text.success(f"✅ Download complete!")
                
                st.success(f"🎉 **Total**: {results['total_downloaded']} episodes downloaded")
                
                # Display summary
                st.markdown("---")
                st.markdown("### 📊 Download Summary")
                for feed_name, count in results['feed_results'].items():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{feed_name}**")
                    with col2:
                        st.metric("Episodes", count)
                
                # Show next step
                st.markdown("---")
                st.markdown("### ✅ Next Step: Process Episodes")
                st.info(f"You now have {results['total_downloaded']} episodes ready to process!")
                
                if st.button("⚙️ Go to Process →", type="primary", key="goto_process"):
                    st.switch_page("pages/10_Process.py")
                    
            except Exception as e:
                overall_progress.progress(1.0)
                status_text.error("❌ Download failed")
                st.error(f"❌ Download failed: {str(e)}")
                import traceback
                with st.expander("Error details"):
                    st.code(traceback.format_exc())
else:
    st.warning("⚠️ Please select at least one feed to download")

# Show feed list
st.markdown("---")
st.markdown("### 📋 Configured Feeds")

for feed in feeds:
    with st.expander(f"🎙️ {feed.get('name', 'Unknown')} - {feed.get('category', 'N/A')}"):
        st.write(f"**URL:** {feed.get('url', 'N/A')}")
        
        # Check if feed has episodes
        feed_episodes = [p for p in db.get_all_podcasts() if p.get('feed_url') == feed['url']]
        if feed_episodes:
            st.success(f"✅ {len(feed_episodes)} episode(s) downloaded")
        else:
            st.info("ℹ️ No episodes downloaded yet")

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
        stats = db.get_stats()
        st.metric("Downloaded", stats.get('downloaded_count', 0))
        st.metric("Transcribed", stats.get('transcribed_count', 0))
        st.metric("Processed", stats.get('processed_count', 0))
    except:
        st.metric("Downloaded", 0)
        st.metric("Transcribed", 0)
        st.metric("Processed", 0)

# Cleanup
db.close()
