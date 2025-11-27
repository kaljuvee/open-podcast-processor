# Parakeet Podcast Processor (P³)

**Automated podcast processing with Apple Silicon optimization and local LLMs**

Transform podcasts into structured summaries using cutting-edge Apple Silicon ML acceleration.

> **Inspired by [Tomasz Tunguz](https://tomtunguz.com)**'s innovative podcast processing system described in his "How I AI" interview. This implementation builds on his pioneering work in automated podcast analysis for venture capital and business intelligence.

## ⚡ Key Features

- **🎧 Smart Audio Processing**: RSS feed monitoring + ffmpeg normalization
- **🚀 Lightning Fast Transcription**: Parakeet MLX (30x faster than Whisper on Apple Silicon)
- **🧠 Local LLM Analysis**: Ollama integration for structured summarization
- **✍️ AI Blog Generation**: Iterative writing with AP English teacher grading system
- **📱 Social Media Posts**: Auto-generate Twitter and LinkedIn content
- **💾 Efficient Storage**: DuckDB for fast queries and analysis
- **📊 Rich Outputs**: Markdown and JSON exports with topics, themes, quotes, and company mentions
- **🔒 100% Local**: No API keys required, complete privacy

## 🚦 Quick Start

```bash
# Prerequisites: macOS with Apple Silicon + ffmpeg + Ollama
brew install ffmpeg
# Install Ollama from https://ollama.com, then: ollama pull llama3.2

# Setup P³
python3 -m venv venv && source venv/bin/activate
pip install -e .
p3 init

# Configure feeds in config/feeds.yaml
# Then run the complete pipeline:
p3 fetch && p3 transcribe && p3 digest && p3 export

# Generate blog posts from digest (Tunguz's innovation):
p3 write --topic "AI's Impact on Software Development"

# Or run the demo script:
python demo.py
```

## ⚡ Performance

- **Audio Download**: ~30 seconds per episode
- **Parakeet Transcription**: 60 minutes audio → 1 second processing 
- **Ollama Analysis**: Full transcript → structured summary in ~10 seconds
- **Total Pipeline**: ~1 minute for complete podcast processing

## 🏗️ Architecture

```
RSS → ffmpeg → Parakeet MLX → Ollama → DuckDB → Export
```

**Optimized Stack:**
- **Audio**: ffmpeg normalization for consistent quality
- **Transcription**: Parakeet MLX (Apple Silicon optimized ASR)  
- **Analysis**: Ollama (local Llama3.2 for structured extraction)
- **Storage**: DuckDB (fast analytical queries)

## 📊 Output Example

**Generated Markdown Digest:**
```markdown
# Podcast Digest - 2025-08-25

## Test Podcast

### All About That Bass

**Summary:** The Roland TR-808 drum machine revolutionized hip-hop and electronic music...

**Key Topics:**
- Roland TR-808 drum machine  
- Hip-hop music evolution
- Electronic music production

**Notable Quotes:**
> "I really feel the 808 kick drum was one of the first things that started shattering the rules..."

**Companies Mentioned:**
- Roland Corporation
```

## 🛠️ Commands

- `p3 init` - Initialize directories and database
- `p3 fetch` - Download episodes from RSS feeds
- `p3 transcribe` - Convert audio to text with Parakeet MLX
- `p3 digest` - Generate structured summaries with Ollama
- `p3 export` - Export daily digests (markdown/JSON)
- `p3 write --topic "Your Topic"` - Generate blog posts with AP English grading
- `p3 status` - Show processing pipeline status

## 🔧 Configuration

Edit `config/feeds.yaml` to add your podcast feeds:

```yaml
feeds:
  - name: "Your Podcast"
    url: "https://example.com/feed.xml"
    category: "tech"

settings:
  max_episodes_per_feed: 5
  
  # Transcription (Apple Silicon optimized)
  parakeet_enabled: true
  parakeet_model: "mlx-community/parakeet-tdt-0.6b-v2"
  
  # LLM Processing (100% Local)
  llm_provider: "ollama"
  llm_model: "llama3.2:latest"
```

## 📂 Project Structure

```
p3/
├── p3/                    # Core package
│   ├── database.py        # DuckDB storage layer
│   ├── downloader.py      # RSS + audio download with ffmpeg
│   ├── transcriber.py     # Parakeet MLX + Whisper fallback
│   ├── cleaner.py         # Ollama LLM analysis
│   ├── exporter.py        # Markdown/JSON generation
│   └── cli.py             # Command-line interface
├── config/feeds.yaml      # Podcast feed configuration
├── data/                  # Audio files + DuckDB database
├── exports/               # Generated digests
├── digest_YYYY-MM-DD.md   # Generated markdown digests
└── digest_YYYY-MM-DD.json # Generated JSON digests
```

## 🚀 Why P³?

**Performance**: Parakeet MLX delivers 30x speed improvement over Whisper on Apple Silicon

**Privacy**: 100% local processing - your podcast data never leaves your machine

**Quality**: State-of-the-art ASR + structured LLM analysis produces rich, actionable summaries

**Efficiency**: Process hours of podcasts in minutes with optimized pipeline

Perfect for researchers, journalists, content creators, or anyone who needs to efficiently process large volumes of podcast content.

## 🙏 **Attribution**

This implementation is inspired by and builds upon the innovative work of **[Tomasz Tunguz](https://tomtunguz.com)**, founder of Theory Ventures, who pioneered many of these techniques for automated podcast analysis in venture capital. His "AP English teacher grading system" for iterative AI writing and multi-feed podcast processing approach formed the foundation for several features in this system.

**Key innovations from Tunguz's system:**
- ✍️ Blog post generation with AP English teacher grading (91/100 target)
- 🔄 Iterative writing improvement loops  
- 📱 Social media post generation
- 🏢 Company/startup extraction for CRM integration
- 📊 Investment thesis generation from podcast insights

*Source: Tomasz Tunguz interview on "How I AI" podcast*
