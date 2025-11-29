"""
Download Episodes Page
Smart interface for finding and downloading podcast episodes
"""

import streamlit as st
from pathlib import Path
import feedparser

from utils.postgres_db import PostgresDB
from utils.search_langraph_util import search_podcast_rss_feed
from utils.downloader import PodcastDownloader

st.set_page_config(page_title="Download Episodes", page_icon="📥", layout="wide")

st.title("📥 Download Podcast Episodes")
st.markdown("**Step 1**: Search for podcasts and download episodes")

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

# Add Feed Section - Smart Search
st.markdown("### 🔍 Add New Podcast Feed")

# Tabs for search vs manual entry
tab1, tab2 = st.tabs(["🔍 Search by Name (AI)", "📋 Manual Entry (Plan B)"])

with tab1:
    st.markdown("**Search for podcasts by name using AI**")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        podcast_search = st.text_input(
            "Podcast Name",
            placeholder="e.g., 'The Tim Ferriss Show' or 'Lex Fridman Podcast'",
            key="podcast_search",
            label_visibility="collapsed"
        )
    with col2:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    # Check API keys
    try:
        from utils.config import get_groq_api_key
        groq_key = get_groq_api_key()
        tavily_available = True
        try:
            from utils.search_langraph_util import get_tavily_api_key
            tavily_key = get_tavily_api_key()
        except ValueError:
            tavily_available = False
    except ValueError:
        st.error("⚠️ GROQ_API_KEY not found. Please set it in your .env file")
        st.stop()
    
    if not tavily_available:
        st.warning("⚠️ TAVILY_API_KEY not found. Please set it in your .env file for search functionality.")
        st.code("echo 'TAVILY_API_KEY=your-key-here' >> .env")
    
    # Search results
    if search_button and podcast_search:
        if not tavily_available:
            st.error("Cannot search: TAVILY_API_KEY not configured")
        else:
            with st.spinner(f"🔍 Searching for '{podcast_search}'..."):
                search_result = search_podcast_rss_feed(podcast_search)
                
                if search_result.get('error'):
                    st.error(f"❌ Search failed: {search_result['error']}")
                elif search_result.get('rss_feed'):
                    st.session_state['search_result'] = search_result
                    st.success("✅ Found podcast!")
    
    # Display search result and confirmation
    if 'search_result' in st.session_state:
        result = st.session_state['search_result']
        
        st.markdown("---")
        st.markdown("### 📻 Found Podcast")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**{result.get('podcast_name', 'Unknown')}**")
            if result.get('description'):
                st.caption(result['description'])
            st.markdown(f"**RSS Feed:** `{result.get('rss_feed')}`")
            
            confidence = result.get('confidence', 0.0)
            if confidence >= 0.7:
                st.success(f"✅ High confidence ({confidence:.0%})")
            elif confidence >= 0.4:
                st.warning(f"⚠️ Medium confidence ({confidence:.0%})")
            else:
                st.error(f"❌ Low confidence ({confidence:.0%})")
        
        with col2:
            st.metric("Confidence", f"{confidence:.0%}")
        
        # Category selection
        feed_category = st.selectbox(
            "Category",
            ["trading", "business", "venture", "product", "saas", "ai", "investing", "general"],
            key="search_feed_category",
            index=7
        )
        
        # Confirm and add feed
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm & Add Feed", type="primary", use_container_width=True):
                try:
                    # Validate RSS feed
                    parsed = feedparser.parse(result['rss_feed'])
                    if parsed.bozo:
                        st.error("⚠️ Invalid RSS feed. Please check the URL.")
                    else:
                        feed_name = parsed.feed.get('title', result.get('podcast_name', 'Unknown'))
                        
                        # Add feed to database
                        feed_id = db.add_feed(
                            name=feed_name,
                            url=result['rss_feed'],
                            category=feed_category,
                            user_id=user_id
                        )
                        
                        st.success(f"✅ Added feed: {feed_name}")
                        
                        # Option to download immediately
                        download_immediately = st.checkbox(
                            "Download episodes now",
                            value=True,
                            key="download_after_add"
                        )
                        
                        if download_immediately:
                            st.session_state['feed_to_download'] = {
                                'id': feed_id,
                                'name': feed_name,
                                'url': result['rss_feed'],
                                'category': feed_category
                            }
                        
                        # Clear search result
                        del st.session_state['search_result']
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to add feed: {e}")
        
        with col2:
            if st.button("🔄 Search Again", use_container_width=True):
                del st.session_state['search_result']
                st.rerun()
        
        # Show search results details
        with st.expander("🔍 Search Details", expanded=False):
            if result.get('search_results'):
                st.write("**Search Results Used:**")
                for i, sr in enumerate(result['search_results'][:3], 1):
                    st.write(f"{i}. [{sr.get('title', 'N/A')}]({sr.get('url', '#')})")
                    st.caption(sr.get('content', '')[:200] + "...")

with tab2:
    st.markdown("**Manually paste an RSS feed URL**")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        feed_url = st.text_input(
            "RSS Feed URL",
            placeholder="https://example.com/feed/podcast",
            key="manual_feed_url",
            label_visibility="collapsed"
        )
    with col2:
        feed_category = st.selectbox(
            "Category",
            ["trading", "business", "venture", "product", "saas", "ai", "investing", "general"],
            key="manual_feed_category",
            index=7
        )
    
    if st.button("➕ Add Feed", type="primary", use_container_width=True):
        if feed_url:
            try:
                # Try to fetch feed to get name
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
                    
                    # Option to download immediately
                    download_immediately = st.checkbox(
                        "Download episodes now",
                        value=True,
                        key="download_after_add_manual"
                    )
                    
                    if download_immediately:
                        st.session_state['feed_to_download'] = {
                            'id': feed_id,
                            'name': feed_name,
                            'url': feed_url,
                            'category': feed_category
                        }
                    
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to add feed: {e}")
        else:
            st.warning("Please enter a feed URL")

st.divider()

# Download Section
if not feeds:
    st.warning("⚠️ No feeds configured yet.")
    st.info("Add feeds using the search or manual entry above to get started")
else:
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

# Auto-download if feed was just added
if 'feed_to_download' in st.session_state:
    feed_info = st.session_state['feed_to_download']
    st.info(f"📥 Auto-downloading episodes from: {feed_info['name']}")
    
    # Auto-select this feed
    feed_display_name = f"{feed_info['name']} ({feed_info['category']})"
    if feed_display_name not in selected_feeds:
        selected_feeds.append(feed_display_name)
    
    # Auto-trigger download
    st.session_state['auto_download'] = True
    del st.session_state['feed_to_download']

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
    download_triggered = st.button("📥 Download Episodes Now", type="primary", use_container_width=True)
    
    # Auto-download trigger
    if st.session_state.get('auto_download', False):
        download_triggered = True
        st.session_state['auto_download'] = False
    
    if download_triggered:
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
                selected_feed_configs.append({
                    'name': feed['name'],
                    'url': feed['url'],
                    'category': feed.get('category', 'general')
                })
        
        total_feeds = len(selected_feed_configs)
        
        with status_container:
            try:
                status_text.info(f"🔄 Starting download of {total_feeds} feed(s)...")
                
                results = {
                    'total_downloaded': 0,
                    'feed_results': {}
                }
                
                feed_progress_container = st.container()
                
                for idx, feed_config in enumerate(selected_feed_configs):
                    feed_name = feed_config['name']
                    progress = idx / total_feeds
                    overall_progress.progress(progress)
                    status_text.info(f"📥 Processing feed {idx + 1}/{total_feeds}: {feed_name}...")
                    
                    with feed_progress_container:
                        with st.spinner(f"Downloading from {feed_name}..."):
                            downloader = PodcastDownloader(
                                db=db,
                                data_dir="data",
                                max_episodes=max_episodes
                            )
                            
                            feed_id = downloader.add_feed(
                                name=feed_config['name'],
                                url=feed_config['url'],
                                category=feed_config.get('category', 'general')
                            )
                            
                            count = downloader.process_feed(feed_config['url'])
                    
                    results['feed_results'][feed_name] = count
                    results['total_downloaded'] += count
                    
                    if count > 0:
                        st.success(f"✅ {feed_name}: Downloaded {count} new episode(s)")
                    else:
                        st.info(f"ℹ️ {feed_name}: No new episodes (may already exist)")
                
                overall_progress.progress(1.0)
                status_text.success(f"✅ Download complete!")
                
                st.success(f"🎉 **Total**: {results['total_downloaded']} episodes downloaded")
                
                st.markdown("---")
                st.markdown("### 📊 Download Summary")
                for feed_name, count in results['feed_results'].items():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{feed_name}**")
                    with col2:
                        st.metric("Episodes", count)
                
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
    - **Search by name** to find podcasts automatically
    - Use **manual entry** if you have the RSS URL
    - Start with 3-5 episodes per feed
    - Download takes ~30 seconds per episode
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
