"""
Search utility using Tavily search API with Groq LLM to find podcast RSS feeds.
Uses LangChain/LangGraph to combine search and LLM reasoning.
"""

import json
from typing import Dict, List, Optional, Any
import os

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults

from utils.config import (
    get_groq_api_key,
    get_groq_model,
    get_groq_temperature,
    get_groq_max_tokens
)


def get_tavily_api_key() -> str:
    """
    Get Tavily API key from environment variables.
    
    Returns:
        str: Tavily API key
        
    Raises:
        ValueError: If API key is not found
    """
    api_key = os.getenv('TAVILY_API_KEY')
    
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY not found. Please set it in:\n"
            "  - .env file: TAVILY_API_KEY=your-key-here\n"
            "  - Environment variable: export TAVILY_API_KEY='your-key-here'"
        )
    
    return api_key


def search_podcast_rss_feed(podcast_name: str) -> Dict[str, Any]:
    """
    Search for podcast RSS feed using Tavily search + Groq LLM.
    
    Args:
        podcast_name: Name of the podcast to search for
        
    Returns:
        Dictionary with:
        {
            'rss_feed': str or None,
            'podcast_name': str,
            'description': str or None,
            'confidence': float (0-1),
            'search_results': List[Dict],
            'error': str or None
        }
    """
    try:
        # Initialize Tavily search tool
        tavily_api_key = get_tavily_api_key()
        search_tool = TavilySearchResults(
            max_results=5,
            tavily_api_key=tavily_api_key
        )
        
        # Initialize Groq LLM
        groq_api_key = get_groq_api_key()
        model = get_groq_model()
        
        llm = ChatGroq(
            model_name=model,
            temperature=get_groq_temperature(),
            max_tokens=get_groq_max_tokens(),
            groq_api_key=groq_api_key
        )
        
        # Set up JSON parser
        parser = JsonOutputParser(
            pydantic_object={
                "type": "object",
                "properties": {
                    "rss_feed": {"type": "string"},
                    "podcast_name": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "number"}
                },
                "required": ["rss_feed", "podcast_name", "confidence"]
            }
        )
        
        # Step 1: Search for podcast information
        search_query = f"{podcast_name} podcast RSS feed"
        search_results = search_tool.invoke({"query": search_query})
        
        if not search_results:
            return {
                'rss_feed': None,
                'podcast_name': podcast_name,
                'description': None,
                'confidence': 0.0,
                'search_results': [],
                'error': 'No search results found'
            }
        
        # Step 2: Use LLM to extract RSS feed from search results
        search_results_text = "\n\n".join([
            f"Title: {r.get('title', 'N/A')}\n"
            f"URL: {r.get('url', 'N/A')}\n"
            f"Content: {r.get('content', '')[:500]}"
            for r in search_results[:5]
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at finding podcast RSS feeds.
Analyze the search results and extract the RSS feed URL for the requested podcast.
RSS feeds typically end in .rss, .xml, or contain '/feed' or '/rss' in the URL.
Return only valid JSON with fields: rss_feed, podcast_name, description, confidence."""),
            ("user", """Find the RSS feed URL for the podcast: "{podcast_name}"

Search Results:
{search_results_text}

Return a JSON object with these fields:
- rss_feed: The RSS feed URL (string or null if not found)
- podcast_name: The official name of the podcast (string)
- description: Brief description of the podcast (string)
- confidence: Your confidence level 0.0 to 1.0 (number)

Return ONLY valid JSON, no markdown, no code blocks, no other text.""")
        ])
        
        # Create chain
        chain = prompt | llm | parser
        
        # Invoke chain with formatted inputs
        result = chain.invoke({
            "podcast_name": podcast_name,
            "search_results_text": search_results_text
        })
        
        return {
            'rss_feed': result.get('rss_feed'),
            'podcast_name': result.get('podcast_name', podcast_name),
            'description': result.get('description'),
            'confidence': result.get('confidence', 0.0),
            'search_results': search_results[:5],
            'error': None
        }
        
    except ValueError as e:
        # API key missing
        return {
            'rss_feed': None,
            'podcast_name': podcast_name,
            'description': None,
            'confidence': 0.0,
            'search_results': [],
            'error': str(e)
        }
    except Exception as e:
        return {
            'rss_feed': None,
            'podcast_name': podcast_name,
            'description': None,
            'confidence': 0.0,
            'search_results': [],
            'error': f"Search failed: {str(e)}"
        }

