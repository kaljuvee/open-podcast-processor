# Quick Start Guide

Get up and running with Open Podcast Processor in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- XAI API key ([get one here](https://x.ai))
- Internet connection

## Option 1: Automated Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/kaljuvee/open-podcast-processor.git
cd open-podcast-processor

# Run the setup script
./setup.sh

# Follow the prompts to enter your XAI API key
```

The setup script will:
- ✅ Create a virtual environment
- ✅ Install all dependencies
- ✅ Set up your API key
- ✅ Create necessary directories
- ✅ Run tests to verify everything works

## Option 2: Manual Setup

```bash
# Clone the repository
git clone https://github.com/kaljuvee/open-podcast-processor.git
cd open-podcast-processor

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
echo "XAI_API_KEY=your-xai-api-key-here" > .env

# Create directories
mkdir -p data/audio test-results exports

# Run tests (optional)
export PYTHONPATH=$(pwd):$PYTHONPATH
source .env
python tests/run_all_tests.py
```

## Start the Application

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Load environment variables
source .env

# Start Streamlit
streamlit run Home.py
```

The application will open in your browser at `http://localhost:8501`

## First Steps

### 1. Configure RSS Feeds

Navigate to **RSS Feeds** page:
- View the pre-configured feeds in `config/feeds.yaml`
- Add your own podcast feeds
- Click "Download Episodes" to fetch episodes

### 2. Process Episodes

Go to **Processing** page:
- **Transcribe** tab: Convert audio to text
- **Summarize** tab: Extract insights with AI
- Monitor progress in the **Status** tab

### 3. View Results

Explore **View Data** page:
- Browse AI-generated summaries
- Read full transcripts
- View episode metadata
- Export data in JSON, TXT, or CSV formats

## Troubleshooting

### "Module not found" error

Make sure you're in the virtual environment:
```bash
source venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### "XAI_API_KEY not found"

Set your API key:
```bash
export XAI_API_KEY="your-key-here"
# Or create a .env file:
echo "XAI_API_KEY=your-key-here" > .env
source .env
```

### No episodes downloading

Check your internet connection and verify the RSS feed URLs in `config/feeds.yaml` are accessible.

### Streamlit won't start

Make sure port 8501 is not in use:
```bash
# Use a different port
streamlit run Home.py --server.port 8502
```

## Next Steps

- **Customize Feeds**: Edit `config/feeds.yaml` to add your favorite podcasts
- **Batch Processing**: Use the batch buttons to process multiple episodes at once
- **Export Data**: Download summaries and transcripts for offline use
- **Explore Analytics**: Check the Analytics tab for insights

## Getting Help

- 📖 Read the full [README.md](README.md)
- 🧪 Check [TEST_REPORT.md](TEST_REPORT.md) for test results
- 🐛 Report issues on [GitHub](https://github.com/kaljuvee/open-podcast-processor/issues)

## Example Workflow

```bash
# 1. Start the app
streamlit run Home.py

# 2. In the browser:
#    - Go to RSS Feeds → Download Episodes (select 3-5 episodes)
#    - Go to Processing → Transcribe All
#    - Wait for transcription to complete
#    - Go to Processing → Summarize All
#    - Go to View Data → Summaries to see results

# 3. Export your data
#    - Click "Download as JSON" on any summary
#    - Or export all episodes as CSV from the Episodes tab
```

## Performance Tips

- Start with 3-5 episodes per feed to test
- Transcription takes ~1-2 minutes per hour of audio
- Summarization takes ~10-30 seconds per episode
- Use batch processing for efficiency

## What's Next?

Once you're comfortable with the basics:
- Add more podcast feeds
- Customize the summarization prompts (edit `utils/cleaner_xai.py`)
- Build custom analytics on the exported data
- Integrate with your own tools via the JSON exports

---

**Ready to process some podcasts? Let's go! 🚀**
