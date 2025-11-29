"""
Topic analysis utility using XAI to discover common topics across episodes.
Results are cached in the database to avoid re-running expensive analysis.
"""

import json
from typing import List, Dict, Optional, Any
from collections import Counter
from utils.database import P3Database
from utils.config import get_api_key, get_grok_model
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


def analyze_topics_with_xai(
    summaries: List[Dict[str, Any]],
    num_topics: int = 10
) -> List[Dict[str, Any]]:
    """
    Use XAI to analyze and cluster topics from episode summaries.
    
    Args:
        summaries: List of summary dictionaries with key_topics, themes, etc.
        num_topics: Number of top topics to return
        
    Returns:
        List of topic dictionaries: [{
            'topic': str,
            'count': int,
            'episodes': List[int],
            'related_themes': List[str]
        }]
    """
    if not summaries:
        return []
    
    # Collect all topics and themes from summaries
    all_topics = []
    all_themes = []
    topic_to_episodes = {}
    
    for summary in summaries:
        episode_id = summary.get('episode_id')
        key_topics = summary.get('key_topics', [])
        themes = summary.get('themes', [])
        
        for topic in key_topics:
            all_topics.append(topic.lower().strip())
            if topic.lower().strip() not in topic_to_episodes:
                topic_to_episodes[topic.lower().strip()] = []
            topic_to_episodes[topic.lower().strip()].append(episode_id)
        
        all_themes.extend([t.lower().strip() for t in themes])
    
    if not all_topics:
        return []
    
    # Count topic frequencies
    topic_counts = Counter(all_topics)
    
    # Use XAI to cluster and refine topics
    try:
        api_key = get_api_key()
        model = get_grok_model()
        
        # Initialize LangChain ChatOpenAI with XAI
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://api.x.ai/v1",
            temperature=0.3,
            max_tokens=4000
        )
        
        # Create prompt for topic clustering
        topics_list = "\n".join([f"- {topic} (appears {count} times)" 
                                for topic, count in topic_counts.most_common(30)])
        
        prompt = f"""Analyze these podcast episode topics and identify the {num_topics} most important and distinct topics.
Group similar topics together and provide clear, concise topic names.

Topics from episodes:
{topics_list}

Return a JSON array with the top {num_topics} topics, each with:
- "topic": clear, concise topic name
- "related_keywords": list of related keywords/phrases that map to this topic
- "description": brief description of what this topic covers

Format:
[
  {{
    "topic": "Topic Name",
    "related_keywords": ["keyword1", "keyword2"],
    "description": "Brief description"
  }}
]

Return ONLY valid JSON, no other text."""

        messages = [
            SystemMessage(content="You are a topic analysis expert. Return only valid JSON."),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        # Parse JSON response
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        clustered_topics = json.loads(response_text)
        
        # Map clustered topics back to counts and episodes
        result_topics = []
        for cluster in clustered_topics:
            topic_name = cluster.get('topic', '')
            related_keywords = cluster.get('related_keywords', [])
            
            # Count episodes mentioning this topic or related keywords
            episode_ids = set()
            count = 0
            
            for keyword in [topic_name.lower()] + [k.lower() for k in related_keywords]:
                for original_topic, episodes in topic_to_episodes.items():
                    if keyword in original_topic or original_topic in keyword:
                        episode_ids.update(episodes)
                        count += topic_counts.get(original_topic, 0)
            
            # Find related themes
            related_themes = []
            for theme in set(all_themes):
                theme_lower = theme.lower()
                if any(kw.lower() in theme_lower or theme_lower in kw.lower() 
                       for kw in [topic_name] + related_keywords):
                    related_themes.append(theme)
            
            result_topics.append({
                'topic': topic_name,
                'count': count,
                'episodes': list(episode_ids),
                'related_themes': related_themes[:5],  # Top 5 related themes
                'description': cluster.get('description', '')
            })
        
        # Sort by count descending
        result_topics.sort(key=lambda x: x['count'], reverse=True)
        
        return result_topics[:num_topics]
        
    except Exception as e:
        # Fallback: return simple frequency-based topics
        print(f"XAI topic analysis failed: {e}, using frequency-based fallback")
        return [
            {
                'topic': topic,
                'count': count,
                'episodes': list(set(topic_to_episodes.get(topic.lower().strip(), []))),
                'related_themes': [],
                'description': ''
            }
            for topic, count in topic_counts.most_common(num_topics)
        ]


def analyze_podcast_topics(
    podcast_id: Optional[int],
    db: P3Database,
    num_topics: int = 10,
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Analyze topics for a specific podcast or all podcasts.
    Results are cached in the database.
    
    Args:
        podcast_id: Podcast ID (None for global analysis)
        db: Database instance
        num_topics: Number of topics to return
        use_cache: Whether to use cached results
        
    Returns:
        List of topic dictionaries
    """
    analysis_type = 'podcast' if podcast_id else 'global'
    
    # Check cache
    if use_cache:
        cached = db.get_topic_analysis(podcast_id, analysis_type)
        if cached:
            return cached
    
    # Get summaries
    if podcast_id:
        # Get episodes for this podcast
        episodes = db.get_episodes_by_status('processed')
        episodes = [e for e in episodes if e.get('podcast_id') == podcast_id]
        episode_ids = [e['id'] for e in episodes]
    else:
        # Get all processed episodes
        episodes = db.get_episodes_by_status('processed')
        episode_ids = [e['id'] for e in episodes]
    
    if not episode_ids:
        return []
    
    # Get summaries for these episodes - more efficient query
    summaries = []
    
    # Query all summaries at once
    from datetime import datetime, timedelta
    all_summaries = []
    # Check last 365 days
    for days_ago in range(365):
        check_date = datetime.now() - timedelta(days=days_ago)
        day_summaries = db.get_summaries_by_date(check_date)
        all_summaries.extend(day_summaries)
    
    # Create lookup dict
    summaries_by_episode = {s['episode_id']: s for s in all_summaries}
    
    for episode_id in episode_ids:
        summary = summaries_by_episode.get(episode_id)
        
        if summary:
            summaries.append({
                'episode_id': episode_id,
                'key_topics': summary.get('key_topics', []),
                'themes': summary.get('themes', []),
                'startups': summary.get('startups', [])
            })
        else:
            # Fallback: try to get transcript and extract basic info
            segments = db.get_transcripts_for_episode(episode_id)
            if segments:
                summaries.append({
                    'episode_id': episode_id,
                    'key_topics': [],
                    'themes': [],
                    'startups': []
                })
    
    if not summaries:
        return []
    
    # Analyze topics
    topics = analyze_topics_with_xai(summaries, num_topics)
    
    # Cache results
    db.save_topic_analysis(podcast_id, analysis_type, topics)
    
    return topics

