# Manual Pipeline Execution Guide

This guide shows you how to run each part of the podcast processing pipeline manually, step by step.

## Prerequisites

1. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Set up environment variables** (in `.env` file):
   ```bash
   GROQ_API_KEY=your-api-key-here
   DB_URL=postgresql://user:password@localhost:5432/dbname
   DB_SCHEMA=public  # optional, defaults to 'public'
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Pipeline Overview

The pipeline consists of 4 main steps:
1. **Download** - Fetch episode from RSS feed and save audio file
2. **Transcribe** - Convert audio to text using Groq Whisper API
3. **Summarize** - Extract insights using Groq LLM API
4. **View** - Browse processed episodes in Streamlit UI

---

## Step 1: Download One Episode

### Option A: Using Python Script

Create a file `download_one.py`:

```python
#!/usr/bin/env python3
"""Download one episode from a feed."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.database import P3Database
from utils.download import load_feeds_config
from utils.downloader import PodcastDownloader

# Load feed configuration
config = load_feeds_config()
feeds = config.get('feeds', [])

if not feeds:
    print("No feeds configured!")
    sys.exit(1)

# Use first feed
feed_config = feeds[0]
feed_name = feed_config.get('name', 'Unknown')
feed_url = feed_config.get('url')

print(f"Using feed: {feed_name}")
print(f"URL: {feed_url}")

# Initialize database and downloader
db = P3Database()
downloader = PodcastDownloader(
    db=db,
    data_dir="data",
    max_episodes=1,  # Only download 1 episode
    audio_format="mp3"  # or "wav"
)

# Add feed to database (or get existing)
existing_podcast = db.get_podcast_by_url(feed_url)
if existing_podcast:
    podcast_id = existing_podcast['id']
    print(f"Feed already exists (ID: {podcast_id})")
else:
    podcast_id = downloader.add_feed(
        name=feed_name,
        url=feed_url,
        category=feed_config.get('category', 'general')
    )
    print(f"Feed added (ID: {podcast_id})")

# Fetch episodes from RSS feed
episodes = downloader.fetch_episodes(feed_url, limit=1)

if not episodes:
    print("No episodes found in feed")
    db.close()
    sys.exit(1)

episode_data = episodes[0]
print(f"Found episode: {episode_data['title']}")

# Check if episode already exists
if db.episode_exists(episode_data['url']):
    print("Episode already exists, skipping download")
    all_episodes = db.get_episodes_by_status('downloaded')
    episode = next((e for e in all_episodes if e['url'] == episode_data['url']), None)
    if episode:
        print(f"Using existing episode (ID: {episode['id']})")
        db.close()
        sys.exit(0)

# Download episode
from datetime import datetime
safe_title = "".join(c for c in episode_data['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
filename = f"{podcast_id}_{safe_title[:50]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

file_path = downloader.download_episode(episode_data['url'], filename)

if not file_path:
    print("Failed to download episode")
    db.close()
    sys.exit(1)

print(f"Episode downloaded to: {file_path}")

# Add to database
episode_id = db.add_episode(
    podcast_id=podcast_id,
    title=episode_data['title'],
    date=episode_data['date'],
    url=episode_data['url'],
    file_path=file_path
)

print(f"Episode saved (ID: {episode_id})")
episode = db.get_episode_by_id(episode_id)
print(f"Title: {episode['title']}")
print(f"File: {episode['file_path']}")
print(f"Status: {episode['status']}")

db.close()
```

Run it:
```bash
python download_one.py
```

### Option B: Using Python REPL

```python
# Start Python REPL
python

# Import modules
from utils.database import P3Database
from utils.download import load_feeds_config
from utils.downloader import PodcastDownloader

# Load config
config = load_feeds_config()
feed_config = config['feeds'][0]  # Use first feed

# Initialize
db = P3Database()
downloader = PodcastDownloader(db=db, max_episodes=1, audio_format="mp3")

# Add feed
podcast_id = downloader.add_feed(
    name=feed_config['name'],
    url=feed_config['url'],
    category=feed_config.get('category', 'general')
)

# Fetch and download
episodes = downloader.fetch_episodes(feed_config['url'], limit=1)
episode_data = episodes[0]

# Download
from datetime import datetime
filename = f"{podcast_id}_{episode_data['title'][:50]}"
file_path = downloader.download_episode(episode_data['url'], filename)

# Save to database
episode_id = db.add_episode(
    podcast_id=podcast_id,
    title=episode_data['title'],
    date=episode_data['date'],
    url=episode_data['url'],
    file_path=file_path
)

# Check status
episode = db.get_episode_by_id(episode_id)
print(f"Episode ID: {episode_id}, Status: {episode['status']}")

db.close()
```

---

## Step 2: Transcribe Downloaded Episode

### Option A: Using Python Script

Create `transcribe_one.py`:

```python
#!/usr/bin/env python3
"""Transcribe one downloaded episode."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.database import P3Database
from utils.processing import transcribe_episode

# Get episode ID (from previous step or database)
episode_id = int(sys.argv[1]) if len(sys.argv) > 1 else None

if not episode_id:
    print("Usage: python transcribe_one.py <episode_id>")
    print("\nOr get episodes by status:")
    db = P3Database()
    downloaded = db.get_episodes_by_status('downloaded')
    if downloaded:
        print("\nAvailable episodes:")
        for ep in downloaded:
            print(f"  ID: {ep['id']} - {ep['title'][:60]}")
    db.close()
    sys.exit(1)

# Initialize database
db = P3Database()

# Get episode info
episode = db.get_episode_by_id(episode_id)
if not episode:
    print(f"Episode {episode_id} not found")
    db.close()
    sys.exit(1)

print(f"Transcribing episode ID: {episode_id}")
print(f"Title: {episode['title']}")
print(f"Status: {episode['status']}")
print(f"File: {episode['file_path']}")

# Transcribe
print("\nStarting transcription...")
success, error = transcribe_episode(episode_id, db)

if not success:
    print(f"❌ Transcription failed: {error}")
    db.close()
    sys.exit(1)

# Verify
episode_updated = db.get_episode_by_id(episode_id)
transcripts = db.get_transcripts_for_episode(episode_id)

print(f"\n✅ Transcription complete!")
print(f"Status: {episode_updated['status']}")
print(f"Transcript segments: {len(transcripts)}")

if transcripts:
    print(f"\nFirst segment:")
    print(f"  [{transcripts[0]['timestamp_start']}s - {transcripts[0]['timestamp_end']}s]")
    print(f"  {transcripts[0]['text'][:200]}...")

db.close()
```

Run it:
```bash
# If you know the episode ID
python transcribe_one.py 1

# Or list available episodes first
python transcribe_one.py
```

### Option B: Using Python REPL

```python
from utils.database import P3Database
from utils.processing import transcribe_episode

# Get episode ID
db = P3Database()
downloaded = db.get_episodes_by_status('downloaded')
if downloaded:
    episode_id = downloaded[0]['id']
    print(f"Transcribing episode ID: {episode_id}")
    
    # Transcribe
    success, error = transcribe_episode(episode_id, db)
    
    if success:
        episode = db.get_episode_by_id(episode_id)
        transcripts = db.get_transcripts_for_episode(episode_id)
        print(f"✅ Transcribed! Status: {episode['status']}, Segments: {len(transcripts)}")
    else:
        print(f"❌ Failed: {error}")

db.close()
```

---

## Step 3: Summarize Transcribed Episode

### Option A: Using Python Script

Create `summarize_one.py`:

```python
#!/usr/bin/env python3
"""Summarize one transcribed episode."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.database import P3Database
from utils.processing import summarize_episode

# Get episode ID
episode_id = int(sys.argv[1]) if len(sys.argv) > 1 else None

if not episode_id:
    print("Usage: python summarize_one.py <episode_id>")
    print("\nOr get transcribed episodes:")
    db = P3Database()
    transcribed = db.get_episodes_by_status('transcribed')
    if transcribed:
        print("\nAvailable episodes:")
        for ep in transcribed:
            print(f"  ID: {ep['id']} - {ep['title'][:60]}")
    db.close()
    sys.exit(1)

# Initialize database
db = P3Database()

# Get episode info
episode = db.get_episode_by_id(episode_id)
if not episode:
    print(f"Episode {episode_id} not found")
    db.close()
    sys.exit(1)

print(f"Summarizing episode ID: {episode_id}")
print(f"Title: {episode['title']}")
print(f"Status: {episode['status']}")

# Summarize
print("\nStarting summarization...")
success, error, summary = summarize_episode(episode_id, db)

if not success:
    print(f"❌ Summarization failed: {error}")
    db.close()
    sys.exit(1)

# Verify
episode_updated = db.get_episode_by_id(episode_id)
summaries = db.get_summaries_by_date(episode['date']) if episode.get('date') else []
episode_summary = next((s for s in summaries if s['episode_id'] == episode_id), None)

print(f"\n✅ Summarization complete!")
print(f"Status: {episode_updated['status']}")

if episode_summary:
    print(f"\nKey Topics ({len(episode_summary.get('key_topics', []))}):")
    for topic in episode_summary.get('key_topics', [])[:10]:
        print(f"  - {topic}")
    
    print(f"\nThemes ({len(episode_summary.get('themes', []))}):")
    for theme in episode_summary.get('themes', [])[:5]:
        print(f"  - {theme}")
    
    print(f"\nCompanies ({len(episode_summary.get('startups', []))}):")
    for company in episode_summary.get('startups', [])[:5]:
        print(f"  - {company}")
    
    if episode_summary.get('full_summary'):
        print(f"\nSummary preview:")
        print(episode_summary['full_summary'][:300] + "...")

db.close()
```

Run it:
```bash
python summarize_one.py 1
```

### Option B: Using Python REPL

```python
from utils.database import P3Database
from utils.processing import summarize_episode

# Get episode ID
db = P3Database()
transcribed = db.get_episodes_by_status('transcribed')
if transcribed:
    episode_id = transcribed[0]['id']
    print(f"Summarizing episode ID: {episode_id}")
    
    # Summarize
    success, error, summary = summarize_episode(episode_id, db)
    
    if success:
        episode = db.get_episode_by_id(episode_id)
        print(f"✅ Summarized! Status: {episode['status']}")
        if summary:
            print(f"Key topics: {summary.get('key_topics', [])[:5]}")
    else:
        print(f"❌ Failed: {error}")

db.close()
```

---

## Step 4: View Processed Episodes

### Using Streamlit UI

```bash
streamlit run Home.py
```

Then navigate to:
- **Podcasts** page - View all processed episodes
- **Download** page - Download new episodes
- **Process** page - Transcribe and summarize episodes

### Using Python Script

Create `view_episodes.py`:

```python
#!/usr/bin/env python3
"""View processed episodes."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.database import P3Database

db = P3Database()

# Get all processed episodes
processed = db.get_episodes_by_status('processed')

print(f"\nFound {len(processed)} processed episodes:\n")

for ep in processed:
    print(f"ID: {ep['id']}")
    print(f"Title: {ep['title']}")
    print(f"Podcast: {ep.get('podcast_title', 'Unknown')}")
    print(f"Date: {ep.get('date', 'Unknown')}")
    
    # Get summary
    summaries = db.get_summaries_by_date(ep['date']) if ep.get('date') else []
    summary = next((s for s in summaries if s['episode_id'] == ep['id']), None)
    
    if summary:
        print(f"Topics: {', '.join(summary.get('key_topics', [])[:5])}")
    
    print("-" * 60)

db.close()
```

---

## Quick Reference: Complete Pipeline

Run all steps in sequence:

```python
from utils.database import P3Database
from utils.download import load_feeds_config
from utils.downloader import PodcastDownloader
from utils.processing import transcribe_episode, summarize_episode

# 1. Download
db = P3Database()
config = load_feeds_config()
feed = config['feeds'][0]
downloader = PodcastDownloader(db=db, max_episodes=1, audio_format="mp3")
podcast_id = downloader.add_feed(feed['name'], feed['url'], feed.get('category'))
episodes = downloader.fetch_episodes(feed['url'], limit=1)
file_path = downloader.download_episode(episodes[0]['url'], "test")
episode_id = db.add_episode(podcast_id, episodes[0]['title'], episodes[0]['date'], episodes[0]['url'], file_path)

# 2. Transcribe
success, error = transcribe_episode(episode_id, db)
print(f"Transcribed: {success}")

# 3. Summarize
success, error, summary = summarize_episode(episode_id, db)
print(f"Summarized: {success}")

# 4. View
episode = db.get_episode_by_id(episode_id)
print(f"Final status: {episode['status']}")

db.close()
```

---

## Troubleshooting

### Episode already exists
If you see "Episode already exists", you can:
- Use the existing episode ID
- Or delete it from the database first

### Transcription fails
- Check that `GROQ_API_KEY` is set
- Verify audio file exists and is readable
- Check audio format (should be mp3 or wav)

### Summarization fails
- Ensure episode is transcribed first (status = 'transcribed')
- Check API key and rate limits
- Verify transcript exists in database

### Database errors
- Ensure DuckDB file is writable: `chmod 666 db/opp.duckdb`
- Check PostgreSQL connection string in `.env`
- Verify schema is initialized: `python -c "from utils.postgres_db import PostgresDB; db = PostgresDB(); db.execute_sql_file('sql/schema.sql')"`

