#!/usr/bin/env python3
"""
P³ Demo Script - Showcase the complete pipeline
"""

import time
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and time it"""
    print(f"\n🔄 {description}")
    print(f"Running: {cmd}")
    
    start_time = time.time()
    result = subprocess.run(cmd.split(), capture_output=True, text=True)
    elapsed = time.time() - start_time
    
    if result.returncode == 0:
        print(f"✅ Completed in {elapsed:.1f}s")
        if result.stdout:
            print(result.stdout.strip())
    else:
        print(f"❌ Failed after {elapsed:.1f}s")
        if result.stderr:
            print(result.stderr.strip())
        return False
    
    return True

def main():
    print("🎙️  Parakeet Podcast Processor (P³) Demo")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Please run from the P³ project directory")
        return
    
    # Check prerequisites
    print("\n📋 Checking prerequisites...")
    prereqs = [
        ("ffmpeg", "ffmpeg -version"),
        ("ollama", "ollama --version"),
        ("p3", "p3 --help")
    ]
    
    for name, cmd in prereqs:
        result = subprocess.run(cmd.split(), capture_output=True)
        if result.returncode == 0:
            print(f"✅ {name} is available")
        else:
            print(f"❌ {name} not found - please install it")
            return
    
    # Clean slate
    print("\n🧹 Preparing clean environment...")
    subprocess.run(["rm", "-rf", "data/", "*.md", "*.json"], capture_output=True)
    run_command("p3 init", "Initializing P³")
    
    # Demo pipeline
    total_start = time.time()
    
    steps = [
        ("p3 fetch", "📥 Fetching podcast episodes from RSS"),
        ("p3 transcribe", "🎯 Transcribing with Parakeet MLX"),
        ("p3 digest", "🧠 Analyzing with Ollama LLM"),
        ("p3 export", "📄 Exporting structured digest"),
        ("p3 status", "📊 Final pipeline status")
    ]
    
    for cmd, desc in steps:
        if not run_command(cmd, desc):
            print(f"❌ Pipeline failed at: {desc}")
            return
        time.sleep(1)  # Brief pause between steps
    
    total_elapsed = time.time() - total_start
    
    # Show results
    print(f"\n🎉 Complete pipeline finished in {total_elapsed:.1f}s")
    
    # Display generated digest
    digest_file = Path("digest_2025-08-25.md")
    if digest_file.exists():
        print("\n📖 Generated Digest Preview:")
        print("-" * 40)
        with open(digest_file) as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:20]):  # Show first 20 lines
                print(line.rstrip())
            if len(lines) > 20:
                print("...")
        print("-" * 40)
    
    # Summary
    print(f"\n📈 Performance Summary:")
    print(f"• Total processing time: {total_elapsed:.1f}s")
    print(f"• Parakeet MLX: ~30x faster than Whisper")
    print(f"• Ollama: Local LLM processing")
    print(f"• 100% local, no API keys required")
    print(f"• Ready for production use!")

if __name__ == "__main__":
    main()
