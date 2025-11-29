"""
Download Episodes Page
Simple interface for downloading podcast episodes from RSS feeds
"""

import streamlit as st
from pathlib import Path
from utils.database import P3Database
from utils.download import load_feeds_config, download_feeds

st.set_page_config(page_title="Download Episodes", page_icon="📥", layout="wide")

st.title("📥 Download Podcast Episodes")
st.markdown("**Step 1**: Select feeds and download episodes to get started")

# Initialize database
db = P3Database()

# Load configuration using utility function
config = load_feeds_config()

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
                selected_feed_configs.append(feed)
        
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
                            # Download from this feed
                            feed_results = download_feeds(
                                feed_configs=[feed_config],
                                max_episodes=max_episodes,
                                db=db,
                                data_dir="data"
                            )
                    
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
                    st.switch_page("pages/1_Process.py")
                    
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
