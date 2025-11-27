# Open Podcast Processor

**Automated podcast processing with XAI API**

Transform podcast episodes into searchable, structured knowledge using AI-powered transcription and summarization.

## 🎯 Overview

Open Podcast Processor is a Streamlit-based application that automates the entire podcast processing pipeline from RSS feed monitoring to AI-powered summarization. Built on the foundation of the [Parakeet Podcast Processor](https://github.com/haasonsaas/parakeet-podcast-processor), this version replaces local MLX models with XAI's cloud API for faster, more scalable processing.

## ✨ Features

### 🎧 Smart RSS Feed Management
- Monitor multiple podcast feeds simultaneously
- Automatic episode discovery and download
- Configurable episode limits per feed
- Support for RSS 2.0, Atom, and iTunes podcast formats

### 🚀 XAI-Powered Transcription
- Fast and accurate speech-to-text using XAI Whisper API
- Automatic audio normalization with ffmpeg
- Batch processing capabilities
- Progress tracking and error handling

### 🧠 AI Summarization
- Extract key topics, themes, and quotes
- Identify mentioned companies and startups
- Generate structured summaries with XAI Grok
- Fallback extraction for reliability

### 💾 DuckDB Storage
- Efficient columnar storage for podcast data
- Fast querying and filtering
- Support for large-scale datasets
- Export capabilities (JSON, CSV, TXT)

### 📊 Interactive Viewing
- Browse summaries with expandable content
- Read full transcripts with segmentation
- View episode metadata and analytics
- Timeline and distribution visualizations

## 🏗️ Architecture

### Pipeline Flow

```
📡 RSS Feed → 📥 Download → 🎵 ffmpeg → 🎯 XAI Transcription → 🧠 XAI Summarization → 💾 DuckDB → 📊 Streamlit UI
```

### Technology Stack

- **Frontend**: Streamlit
- **AI Processing**: XAI API (Whisper + Grok)
- **Database**: DuckDB
- **Audio Processing**: ffmpeg
- **RSS Parsing**: feedparser
- **Language**: Python 3.11+

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- ffmpeg installed on your system
- XAI API key ([get one here](https://x.ai))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/kaljuvee/open-podcast-processor.git
   cd open-podcast-processor
   ```

2. **Create virtual environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   export XAI_API_KEY="your-xai-api-key-here"
   ```

5. **Run the application**
   ```bash
   streamlit run Home.py
   ```

6. **Open in browser**
   ```
   http://localhost:8501
   ```

## 📖 Usage Guide

### 1. Configure RSS Feeds

Navigate to the **RSS Feeds** page and:
- View pre-configured feeds in `config/feeds.yaml`
- Add new podcast feeds using the "Add Feed" tab
- Download episodes using the "Download Episodes" tab

### 2. Process Episodes

Go to the **Processing** page to:
- **Transcribe**: Convert audio to text using XAI Whisper
- **Summarize**: Extract structured insights using XAI Grok
- Monitor processing status and progress

### 3. View Results

Explore processed content in the **View Data** page:
- **Summaries**: Browse AI-generated summaries with topics, themes, and quotes
- **Transcripts**: Read full transcripts with timestamps
- **Episodes**: View all episodes with filtering options
- **Analytics**: Explore statistics and visualizations

### 4. Export Data

Export processed content in multiple formats:
- JSON for summaries
- TXT for transcripts
- CSV for episode lists

## 🧪 Testing

The project includes a comprehensive test suite:

```bash
# Run all tests
python tests/run_all_tests.py

# Run individual test modules
python tests/test_database.py
python tests/test_downloader.py
python tests/test_xai_integration.py
```

Test results are saved to `test-results/*.json` for review.

## 📁 Project Structure

```
open-podcast-processor/
├── Home.py                    # Main Streamlit app
├── pages/                     # Streamlit pages
│   ├── 0_RSS_Feeds.py        # RSS feed management
│   ├── 1_Processing.py       # Transcription & summarization
│   └── 2_View_Data.py        # Data viewing & export
├── p3/                        # Core modules
│   ├── database.py           # DuckDB operations
│   ├── downloader.py         # RSS feed & download
│   ├── transcriber_xai.py    # XAI transcription
│   └── cleaner_xai.py        # XAI summarization
├── tests/                     # Test suite
│   ├── test_database.py
│   ├── test_downloader.py
│   ├── test_xai_integration.py
│   └── run_all_tests.py
├── config/                    # Configuration
│   └── feeds.yaml            # RSS feed definitions
├── data/                      # Data storage
│   ├── audio/                # Downloaded episodes
│   └── p3.duckdb             # Database file
├── test-results/              # Test outputs
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🔧 Configuration

### RSS Feeds

Edit `config/feeds.yaml` to configure podcast feeds:

```yaml
feeds:
  - name: "Tech Podcast"
    url: "https://example.com/feed.xml"
    category: "tech"
  - name: "Business Show"
    url: "https://example.com/business.xml"
    category: "business"

settings:
  max_episodes_per_feed: 5
  download_dir: "data/audio"
```

### Environment Variables

- `XAI_API_KEY`: Your XAI API key (required)

## 🎨 XAI Models Used

- **Transcription**: `whisper-1` - High-quality speech-to-text
- **Summarization**: `grok-beta` - Advanced language understanding

## 📊 Database Schema

### Tables

- **podcasts**: Podcast metadata (title, URL, category)
- **episodes**: Episode information (title, date, duration, status)
- **transcripts**: Timestamped transcript segments
- **summaries**: Structured summaries with topics, themes, quotes

### Episode Status Flow

```
downloaded → transcribed → processed
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgements

This project builds upon and is inspired by:

### [Parakeet Podcast Processor](https://github.com/haasonsaas/parakeet-podcast-processor)

**Created by [haasonsaas](https://github.com/haasonsaas)**

The original Parakeet Podcast Processor (P³) pioneered the automated podcast processing pipeline using Apple Silicon optimization and local LLMs. This project adapts their innovative architecture to use cloud-based XAI APIs, making it accessible to users without Apple Silicon hardware while maintaining the core processing philosophy.

**Key innovations from Parakeet P³:**
- Efficient podcast RSS feed monitoring and download
- Structured summarization with topic, theme, and quote extraction
- Company/startup mention detection for business intelligence
- DuckDB integration for fast analytical queries
- Markdown and JSON export formats

### [Tomasz Tunguz](https://tomtunguz.com/)

**Founder of Theory Ventures**

Tomasz Tunguz pioneered many of the techniques for automated podcast analysis in venture capital, as described in his "How I AI" interview. His innovative approaches influenced both the original Parakeet project and this adaptation.

**Tunguz's contributions to podcast processing:**
- AP English teacher grading system for iterative AI writing
- Multi-feed podcast processing for investment research
- Company extraction for CRM integration
- Investment thesis generation from podcast insights
- Social media content generation from summaries

---

### Special Thanks

- **XAI Team** - For providing powerful API access to Whisper and Grok models
- **Streamlit Team** - For an excellent framework for building data applications
- **DuckDB Team** - For a fast, embeddable analytical database
- **Open Source Community** - For the amazing tools that made this project possible

---

## 📚 Additional Documentation

All additional documentation is in the `docs/` directory:

- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - 5-minute setup guide
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** - Version history and updates
- **[docs/TEST_REPORT.md](docs/TEST_REPORT.md)** - Comprehensive test results
- **[docs/README_ORIGINAL.md](docs/README_ORIGINAL.md)** - Original Parakeet README
- **[docs/AGENT.md](docs/AGENT.md)** - Development notes

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on [GitHub](https://github.com/kaljuvee/open-podcast-processor/issues)
- Check existing issues for solutions

## 🔮 Future Enhancements

- [ ] Speaker diarization (identify different speakers)
- [ ] Multi-language support
- [ ] Automatic topic clustering
- [ ] Integration with podcast players
- [ ] Real-time processing for live streams
- [ ] Advanced search and filtering
- [ ] Custom summarization templates
- [ ] API endpoints for programmatic access

## 📈 Performance

- **Transcription**: ~1-2 minutes per hour of audio
- **Summarization**: ~10-30 seconds per episode
- **Database**: Handles 10,000+ episodes efficiently
- **UI**: Responsive for datasets with 1,000+ processed episodes

## 🔒 Privacy & Security

- All processing happens via XAI's secure API
- API keys stored as environment variables (never committed)
- Local database storage (no cloud data storage)
- Audio files stored locally and can be deleted after processing

---

**Built with ❤️ using Streamlit and XAI**

*Inspired by the innovative work of haasonsaas and Tomasz Tunguz*
