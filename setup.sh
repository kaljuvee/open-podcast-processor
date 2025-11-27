#!/bin/bash

# Open Podcast Processor Setup Script
# This script sets up the environment and runs the application

set -e

echo "🎙️  Open Podcast Processor Setup"
echo "================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3.11 --version 2>&1 || python3 --version 2>&1)
echo "✓ Found: $python_version"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv venv || python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found"
    echo ""
    echo "Please create a .env file with your XAI API key:"
    echo "  cp .env.example .env"
    echo "  # Edit .env and add your XAI_API_KEY"
    echo ""
    read -p "Do you have an XAI API key? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your XAI API key: " api_key
        echo "XAI_API_KEY=$api_key" > .env
        echo "✓ .env file created"
    else
        echo "Get your API key from: https://x.ai"
        echo "Then run: echo 'XAI_API_KEY=your-key-here' > .env"
        exit 1
    fi
else
    echo "✓ .env file exists"
fi
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p data/audio
mkdir -p test-results
mkdir -p exports
echo "✓ Directories created"
echo ""

# Run tests
echo "Running tests..."
export PYTHONPATH=$(pwd):$PYTHONPATH
source .env
python tests/run_all_tests.py
echo ""

# Success message
echo "================================"
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  source venv/bin/activate"
echo "  source .env"
echo "  streamlit run Home.py"
echo ""
echo "Then open: http://localhost:8501"
echo "================================"
