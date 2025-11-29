# Test Suite Documentation

This document provides a comprehensive guide for testing each component of the Open Podcast Processor pipeline in isolation.

## Overview

The test suite is organized to test each component of the pipeline independently:
1. **Database** - Database operations and schema
2. **Downloader** - RSS feed parsing and episode downloading
3. **Transcriber** - Audio transcription using Groq Whisper
4. **Cleaner/Summarizer** - Transcript cleaning and summarization using Groq LLM
5. **Full Pipeline** - End-to-end testing

## Test File Naming Convention

All test files end with `*test*` for easier autocomplete:
- `database_test.py` - Database operations
- `downloader_test.py` - Download functionality
- `ai_processing_test.py` - AI transcription and summarization
- `pipeline_test.py` - Full pipeline test
- `stt_test.py` - Speech-to-text (transcription) test
- `reasoning_test.py` - LLM reasoning test
- `utils_test.py` - Utility functions test
- `db_opp_test.py` - Main database (db/opp.duckdb) test
- `real_feed_test.py` - Real RSS feed integration test
- `full_pipeline_postgres_test.py` - Full pipeline with PostgreSQL
- `download_trading_test.py` - Trading podcast download test
- `transcribe_trading_test.py` - Trading podcast transcription test
- `run_all_tests_test.py` - Run all tests suite
- `run_batch_test.py` - Batch processing test
- `run_batch_postgres_test.py` - Batch processing with PostgreSQL test
- `sync_to_postgres_test.py` - DuckDB to PostgreSQL sync test

## Component-by-Component Testing

### 1. Database Tests

**File**: `database_test.py`

**Purpose**: Test database initialization, schema creation, and basic CRUD operations.

**What it tests**:
- Database initialization
- Podcast/episode creation
- Episode existence checks
- Status updates
- Query operations

**Run**:
```bash
python tests/database_test.py
```

**Expected Output**: JSON report in `test-results/database_test_*.json`

---

### 2. Downloader Tests

**File**: `downloader_test.py`

**Purpose**: Test RSS feed parsing and episode downloading functionality.

**What it tests**:
- Downloader initialization
- RSS feed parsing
- Episode metadata extraction
- Download directory creation
- File download (if episodes available)

**Prerequisites**:
- Valid RSS feed URLs in `config/feeds.yaml`
- Internet connection

**Run**:
```bash
python tests/downloader_test.py
```

**Expected Output**: JSON report in `test-results/downloader_test_*.json`

---

### 3. Speech-to-Text (STT) Tests

**File**: `stt_test.py`

**Purpose**: Test Groq Whisper Large V3 Turbo transcription.

**What it tests**:
- API key configuration
- Transcriber initialization
- Audio file transcription (if test audio available)
- Chunking for large files

**Prerequisites**:
- `GROQ_API_KEY` in `.env` file
- Test audio files in database (optional)

**Run**:
```bash
python tests/stt_test.py
```

**Expected Output**: JSON report in `test-results/stt_test_*.json`

---

### 4. Reasoning/LLM Tests

**File**: `reasoning_test.py`

**Purpose**: Test Groq LLM models for reasoning and JSON output parsing.

**What it tests**:
- API key and model configuration
- LangChain ChatGroq initialization
- Simple reasoning tasks
- JSON output parsing
- Context window handling

**Prerequisites**:
- `GROQ_API_KEY` in `.env` file
- `GROQ_MODEL` (optional, defaults to llama-3.3-70b-versatile)

**Run**:
```bash
python tests/reasoning_test.py
```

**Expected Output**: JSON report in `test-results/reasoning_test_*.json`

---

### 5. AI Processing Tests

**File**: `ai_processing_test.py`

**Purpose**: Test complete AI processing pipeline (transcription + summarization).

**What it tests**:
- ffmpeg installation check
- API key validation
- Feed loading
- Episode download (if needed)
- Transcription functionality
- Summarization functionality

**Prerequisites**:
- `GROQ_API_KEY` in `.env` file
- ffmpeg installed (optional, for audio processing)
- Valid feeds in `config/feeds.yaml`

**Run**:
```bash
python tests/ai_processing_test.py
```

**Expected Output**: JSON report in `test-results/ai_processing_test_*.json`

---

### 6. Pipeline Tests

**File**: `pipeline_test.py`

**Purpose**: Test the complete pipeline: Download → Transcribe → Summarize.

**What it tests**:
- Database connection (DuckDB and PostgreSQL)
- Schema initialization
- Episode download
- Transcription
- Summarization
- Status updates

**Prerequisites**:
- `GROQ_API_KEY` in `.env` file
- `DB_URL` for PostgreSQL (optional)
- Valid feeds in `config/feeds.yaml`

**Run**:
```bash
python tests/pipeline_test.py
```

**Expected Output**: Console output showing each step of the pipeline

---

### 7. Utils Tests

**File**: `utils_test.py`

**Purpose**: Test utility functions extracted from Streamlit pages.

**What it tests**:
- Feed configuration loading
- API key retrieval
- `process_all_episodes()` function
- `transcribe_episode()` function
- `summarize_episode()` function
- `download_feeds()` function

**Run**:
```bash
python tests/utils_test.py
```

**Expected Output**: JSON report in `test-results/utils_test_*.json`

---

### 8. Database OPP Tests

**File**: `db_opp_test.py`

**Purpose**: Test the main database (`db/opp.duckdb`) schema and operations.

**What it tests**:
- Database initialization
- Schema verification
- Database operations (CRUD)
- Statistics retrieval
- Podcast/episode queries
- Download integration

**Run**:
```bash
python tests/db_opp_test.py
```

**Expected Output**: JSON report in `test-results/db_opp_test_*.json`

---

### 9. Real Feed Tests

**File**: `real_feed_test.py`

**Purpose**: Test with actual RSS feeds from configuration.

**What it tests**:
- Feed configuration loading
- RSS feed parsing
- Episode metadata extraction
- Integration with downloader

**Prerequisites**:
- Valid feeds in `config/feeds.yaml`
- Internet connection

**Run**:
```bash
python tests/real_feed_test.py
```

---

### 10. Full Pipeline PostgreSQL Tests

**File**: `full_pipeline_postgres_test.py`

**Purpose**: Test complete pipeline using PostgreSQL database.

**What it tests**:
- PostgreSQL connection
- Schema initialization
- Episode download
- Transcription with Groq
- Summarization with Groq
- Data persistence in PostgreSQL

**Prerequisites**:
- `GROQ_API_KEY` in `.env` file
- `DB_URL` for PostgreSQL in `.env` file
- Valid feeds in `config/feeds.yaml`

**Run**:
```bash
python tests/full_pipeline_postgres_test.py
```

---

## Running All Tests

**File**: `run_all_tests_test.py`

Run all test suites and generate a consolidated report:

```bash
python tests/run_all_tests_test.py
```

**Expected Output**: 
- Console output for each test suite
- Consolidated JSON report in `test-results/all_tests_report_*.json`

---

## Batch Processing Tests

### Batch Download Test

**File**: `run_batch_test.py`

Test batch downloading from multiple feeds:

```bash
python tests/run_batch_test.py
```

### Batch Processing PostgreSQL Test

**File**: `run_batch_postgres_test.py`

Test batch processing with PostgreSQL:

```bash
python tests/run_batch_postgres_test.py
```

---

## Environment Setup

Before running tests, ensure your `.env` file is configured:

```bash
# Copy example file
cp .env.example .env

# Edit .env and add your API keys
GROQ_API_KEY=your-groq-api-key-here
DB_URL=postgresql://user:password@localhost:5432/podcast_db
```

See `.env.example` for all available configuration options.

---

## Test Results

All tests generate JSON reports in the `test-results/` directory with:
- Test name and timestamp
- Individual test results with status (passed/failed/skipped)
- Summary statistics
- Error messages (if any)

---

## Duplicate Work Prevention

The codebase includes checks to prevent duplicate work:

1. **Download**: 
   - Checks if episode URL already exists in database (`episode_exists()`)
   - Checks if audio file already exists on disk before downloading

2. **Transcription**:
   - Checks episode status before transcribing (`status == 'transcribed'` or `'processed'`)
   - Skips if already transcribed

3. **Summarization**:
   - Checks episode status before summarizing (`status == 'processed'`)
   - Checks if summary already exists in database
   - Returns existing summary if found

These checks ensure that re-running the pipeline won't duplicate expensive operations.

---

## Troubleshooting

### Tests fail with "API key not found"
- Ensure `.env` file exists and contains `GROQ_API_KEY`
- Check that `.env` is in the project root directory

### Tests fail with "Database connection error"
- For PostgreSQL tests, ensure `DB_URL` is correct in `.env`
- Check that PostgreSQL is running and accessible

### Tests skip with "No feeds configured"
- Add feeds to `config/feeds.yaml`
- Ensure feed URLs are valid and accessible

### Transcription tests fail
- Check that test audio files exist
- Verify `GROQ_API_KEY` is valid
- Check Groq API quota/limits

---

## Best Practices

1. **Test in isolation**: Each test file can be run independently
2. **Use test databases**: Tests use separate test databases to avoid affecting production data
3. **Check prerequisites**: Review test prerequisites before running
4. **Review test results**: Check JSON reports for detailed test outcomes
5. **Run specific tests**: Run individual test files for faster feedback during development

---

## Adding New Tests

When adding new tests:

1. Follow the naming convention: `*_test.py`
2. Include JSON report generation
3. Test one component at a time
4. Include prerequisites in docstring
5. Add to `run_all_tests_test.py` if it's a core component test

---

## Integration with CI/CD

Tests can be integrated into CI/CD pipelines:

```bash
# Run all tests and check exit code
python tests/run_all_tests_test.py
EXIT_CODE=$?

# Check if any tests failed
if [ $EXIT_CODE -ne 0 ]; then
    echo "Tests failed!"
    exit 1
fi
```


