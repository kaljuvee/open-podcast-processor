-- PostgreSQL schema for Open Podcast Processor
-- Stores processed podcast data with transcripts and summaries

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Podcasts table
CREATE TABLE IF NOT EXISTS podcasts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    feed_url VARCHAR(1000),
    episode_url VARCHAR(1000),
    published_at TIMESTAMP,
    duration_seconds INTEGER,
    audio_file_path VARCHAR(1000),
    file_size_bytes BIGINT,
    
    -- Processing status
    status VARCHAR(50) DEFAULT 'downloaded', -- downloaded, transcribed, processed, failed
    processed_at TIMESTAMP,
    
    -- Content (stored as JSONB for flexibility)
    transcript JSONB, -- {segments: [...], text: "...", language: "en"}
    summary JSONB, -- {key_topics: [...], themes: [...], quotes: [...], startups: [...], summary: "..."}
    
    -- Metadata
    podcast_feed_name VARCHAR(255),
    podcast_category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_podcasts_status ON podcasts(status);
CREATE INDEX IF NOT EXISTS idx_podcasts_processed_at ON podcasts(processed_at);
CREATE INDEX IF NOT EXISTS idx_podcasts_published_at ON podcasts(published_at);
CREATE INDEX IF NOT EXISTS idx_podcasts_feed_name ON podcasts(podcast_feed_name);
CREATE INDEX IF NOT EXISTS idx_podcasts_transcript_gin ON podcasts USING GIN(transcript);
CREATE INDEX IF NOT EXISTS idx_podcasts_summary_gin ON podcasts USING GIN(summary);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to auto-update updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_podcasts_updated_at BEFORE UPDATE ON podcasts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for podcast statistics
CREATE OR REPLACE VIEW podcast_stats AS
SELECT 
    COUNT(*) as total_podcasts,
    COUNT(*) FILTER (WHERE status = 'downloaded') as downloaded_count,
    COUNT(*) FILTER (WHERE status = 'transcribed') as transcribed_count,
    COUNT(*) FILTER (WHERE status = 'processed') as processed_count,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
    COUNT(DISTINCT podcast_feed_name) as unique_feeds,
    AVG(duration_seconds) as avg_duration_seconds,
    SUM(file_size_bytes) / 1024 / 1024 as total_size_mb
FROM podcasts;

