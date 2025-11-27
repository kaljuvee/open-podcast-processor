# Deployment Guide

This guide covers deploying the Open Podcast Processor to Streamlit Cloud.

## 🚀 Quick Deploy to Streamlit Cloud

### Prerequisites

- GitHub account
- Streamlit Cloud account (free at [streamlit.io](https://streamlit.io))
- XAI API key from [x.ai](https://x.ai)

### Step 1: Fork or Push Repository

1. **Option A - Fork**: Fork this repository to your GitHub account
2. **Option B - Push**: Push your local repository to GitHub

### Step 2: Connect to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your repository: `your-username/open-podcast-processor`
4. Set main file path: `Home.py`
5. Click "Advanced settings"

### Step 3: Configure Secrets

In the "Secrets" section, add:

```toml
XAI_API_KEY = "your-actual-xai-api-key-here"
```

### Step 4: Deploy

Click "Deploy!" and wait for the app to build and start.

## 📋 Configuration Files

The repository includes these deployment files:

### `packages.txt`
System packages required for deployment:
```
ffmpeg
```

### `.streamlit/config.toml`
Streamlit configuration:
```toml
[server]
maxUploadSize = 500
enableXsrfProtection = false
headless = true

[browser]
gatherUsageStats = false
```

### `requirements.txt`
Python dependencies (automatically installed)

## ⚙️ Environment Variables

### Local Development

Create a `.env` file:
```bash
XAI_API_KEY=your-xai-api-key-here
```

### Streamlit Cloud

Add secrets in app settings → Secrets:
```toml
XAI_API_KEY = "your-xai-api-key-here"
```

## 🔧 How It Works

The application uses a unified configuration system:

1. **Local Development**: Loads from `.env` file using `python-dotenv`
2. **Streamlit Cloud**: Loads from Streamlit secrets
3. **Fallback**: Uses environment variables

See `p3/config.py` for implementation details.

## ⚠️ Limitations on Streamlit Cloud

### Storage Limits
- **Ephemeral storage**: ~1GB temporary storage
- **Persistence**: Files may be deleted on app restart
- **Recommendation**: Download 1-2 episodes at a time

### Processing Limits
- **Timeout**: Long operations may timeout
- **Memory**: Limited RAM for processing
- **Recommendation**: Process episodes in small batches

### Solutions for Production

1. **Use Cloud Storage**
   - Store audio files in S3, Google Cloud Storage, or Azure Blob
   - Only keep temporary files locally

2. **Add Cleanup**
   - Delete audio files after transcription
   - Implement automatic cleanup of old files

3. **Use Background Workers**
   - For large-scale processing, use Celery or similar
   - Consider dedicated processing servers

## 🎯 Recommended Settings for Cloud

### For Streamlit Cloud deployment:

1. **Episodes per feed**: 1-2 (instead of 3-5)
2. **Cleanup**: Enable automatic file deletion
3. **Monitoring**: Watch storage usage in app logs

### Update `config/feeds.yaml`:

```yaml
settings:
  max_episodes_per_feed: 2  # Reduced for cloud
  cleanup_old_files: true
  cleanup_days: 1  # Clean up after 1 day
```

## 📊 Monitoring

### Check App Logs

In Streamlit Cloud:
1. Go to your app
2. Click "Manage app" (bottom right)
3. View logs for errors and warnings

### Monitor Storage

Check storage usage:
```python
import os
import shutil

# In your Streamlit app
total, used, free = shutil.disk_usage("/")
st.write(f"Free space: {free // (2**30)} GB")
```

## 🐛 Troubleshooting

### "XAI_API_KEY not found"

**Solution**: Add API key to Streamlit Cloud secrets:
1. Go to app settings
2. Click "Secrets"
3. Add: `XAI_API_KEY = "your-key"`

### "No space left on device"

**Solution**: 
1. Reduce episodes per feed to 1
2. Enable cleanup in settings
3. Delete old audio files manually

### "ffmpeg not found"

**Solution**: Ensure `packages.txt` exists with:
```
ffmpeg
```

### App crashes during download

**Solution**:
1. Download fewer episodes
2. Check internet connectivity
3. Verify RSS feed URLs are accessible

## 🔐 Security Best Practices

1. **Never commit secrets**
   - `.env` is in `.gitignore`
   - Use Streamlit secrets for deployment

2. **Rotate API keys**
   - Regenerate keys periodically
   - Update in Streamlit Cloud secrets

3. **Monitor usage**
   - Track API usage on XAI dashboard
   - Set up alerts for unusual activity

## 📚 Additional Resources

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
- [XAI API Documentation](https://docs.x.ai)

## 🆘 Support

For deployment issues:
1. Check [Streamlit Community Forum](https://discuss.streamlit.io)
2. Review [GitHub Issues](https://github.com/kaljuvee/open-podcast-processor/issues)
3. Contact Streamlit support for platform issues

---

**Last Updated**: November 27, 2025
