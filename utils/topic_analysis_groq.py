"""
Topic analysis utility using Groq via LangChain to discover common topics across episodes.
Results are cached in the database to avoid re-running expensive analysis.
Uses PostgreSQL (PostgresDB) for storage.
"""

import json
from typing import List, Dict, Optional, Any, Union
from collections import Counter, defaultdict
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from utils.postgres_db import PostgresDB
from utils.config import get_groq_api_key, get_groq_model, get_groq_topic_temperature, get_groq_max_tokens

# Optional sklearn import for K-Means
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def analyze_topics_with_groq(
    summaries: List[Dict[str, Any]],
    num_topics: int = 10
) -> List[Dict[str, Any]]:
    """
    Use Groq to analyze and cluster topics from episode summaries.
    
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
    
    # Use Groq to cluster and refine topics
    try:
        api_key = get_groq_api_key()
        model = get_groq_model()
        
        # Initialize LangChain ChatGroq
        llm = ChatGroq(
            model_name=model,
            temperature=get_groq_topic_temperature(),
            max_tokens=get_groq_max_tokens(),
            groq_api_key=api_key
        )
        
        # Set up JSON parser
        parser = JsonOutputParser(
            pydantic_object={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "related_keywords": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "description": {"type": "string"}
                    },
                    "required": ["topic", "related_keywords", "description"]
                }
            }
        )
        
        # Create prompt for topic clustering
        topics_list = "\n".join([f"- {topic} (appears {count} times)" 
                                for topic, count in topic_counts.most_common(30)])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a topic analysis expert. Return only valid JSON."),
            ("user", f"""Analyze these podcast episode topics and identify the {num_topics} most important and distinct topics.
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

Return ONLY valid JSON, no other text.""")
        ])
        
        # Create chain
        chain = prompt | llm | parser
        
        # Invoke chain
        clustered_topics = chain.invoke({})
        
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
        print(f"Groq topic analysis failed: {e}, using frequency-based fallback")
        import traceback
        traceback.print_exc()
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


def analyze_topics_from_transcripts_with_groq(
    transcript_texts: List[str],
    podcast_ids: List[int],
    feed_names: List[str],
    num_topics: int = 10,
    max_chars: int = 100000,
    api_key: str = None,
    model: str = None
) -> List[Dict[str, Any]]:
    """
    Use Groq LLM to analyze and cluster topics directly from transcript texts.
    
    Args:
        transcript_texts: List of transcript texts
        podcast_ids: List of podcast IDs corresponding to texts
        feed_names: List of feed names corresponding to texts
        num_topics: Number of topics to discover
        max_chars: Maximum characters per request
        api_key: Groq API key (defaults to environment)
        model: Groq model name (defaults to environment)
        
    Returns:
        List of topic dictionaries with topic, description, key_phrases, etc.
    """
    if not transcript_texts or not podcast_ids:
        return []
    
    api_key = api_key or get_groq_api_key()
    model = model or get_groq_model()
    
    # Initialize LangChain ChatGroq
    llm = ChatGroq(
        model_name=model,
        temperature=get_groq_topic_temperature(),
        max_tokens=get_groq_max_tokens(),
        groq_api_key=api_key
    )
    
    # Set up JSON parser
    parser = JsonOutputParser(
        pydantic_object={
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "description": {"type": "string"},
                    "key_phrases": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "related_themes": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["topic", "description", "key_phrases", "related_themes"]
            }
        }
    )
    
    # Prepare transcript summaries for analysis
    transcript_summaries = []
    for i, text in enumerate(transcript_texts):
        if len(text) > max_chars:
            summary = text[:max_chars] + "... [truncated]"
        else:
            summary = text
        
        word_count = len(text.split())
        transcript_summaries.append(
            f"Podcast {podcast_ids[i]} ({feed_names[i]}): {summary[:500]}... "
            f"[{word_count} words total]"
        )
    
    # Combine all summaries
    combined_text = "\n\n".join(transcript_summaries)
    
    # Truncate if still too long
    if len(combined_text) > max_chars:
        combined_text = combined_text[:max_chars] + "... [truncated]"
    
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at analyzing podcast content and identifying themes and topics.
Analyze the provided podcast transcripts and identify distinct topics and themes.
Group similar content together and provide clear, meaningful topic names.
Return only valid JSON."""),
        ("user", f"""Analyze these podcast transcripts and identify the {num_topics} most important and distinct topics/themes.

Transcripts:
{combined_text}

Return a JSON array with {num_topics} topics, each with:
- "topic": Clear, concise topic name (2-4 words)
- "description": Brief description of what this topic covers (1-2 sentences)
- "key_phrases": List of 5-10 key phrases/terms that characterize this topic
- "related_themes": List of 2-4 broader themes this topic relates to

Focus on:
- Distinct, non-overlapping topics
- Meaningful themes that span multiple podcasts
- Important concepts, discussions, or subjects

Format:
[
  {{
    "topic": "Topic Name",
    "description": "What this topic covers",
    "key_phrases": ["phrase1", "phrase2", ...],
    "related_themes": ["theme1", "theme2", ...]
  }}
]

Return ONLY valid JSON, no other text.""")
    ])
    
    # Create chain
    chain = prompt | llm | parser
    
    # Invoke chain
    topics = chain.invoke({})
    
    # Map topics back to podcasts by analyzing which podcasts mention key phrases
    result_topics = []
    for topic_data in topics:
        topic_name = topic_data.get('topic', '')
        key_phrases = topic_data.get('key_phrases', [])
        
        # Find podcasts that mention these phrases
        matching_podcast_ids = []
        matching_feeds = set()
        
        for i, text in enumerate(transcript_texts):
            text_lower = text.lower()
            # Check if any key phrase appears in this transcript
            matches = sum(1 for phrase in key_phrases if phrase.lower() in text_lower)
            if matches >= 1:  # At least one phrase match
                matching_podcast_ids.append(podcast_ids[i])
                matching_feeds.add(feed_names[i])
        
        result_topics.append({
            'topic': topic_name,
            'description': topic_data.get('description', ''),
            'key_phrases': key_phrases,
            'related_themes': topic_data.get('related_themes', []),
            'podcast_count': len(matching_podcast_ids),
            'podcast_ids': matching_podcast_ids,
            'feeds': list(matching_feeds)
        })
    
    # Sort by podcast count
    result_topics.sort(key=lambda x: x['podcast_count'], reverse=True)
    
    return result_topics


def analyze_topics_with_kmeans(
    transcript_texts: List[str],
    podcast_ids: List[int],
    feed_names: List[str],
    num_topics: int
) -> List[Dict[str, Any]]:
    """
    Use K-Means clustering on TF-IDF vectors to find topics.
    
    Args:
        transcript_texts: List of transcript texts
        podcast_ids: List of podcast IDs
        feed_names: List of feed names
        num_topics: Number of clusters
        
    Returns:
        List of topic dictionaries
    """
    if not SKLEARN_AVAILABLE:
        raise ImportError("scikit-learn is required for K-Means clustering")
    
    # Vectorize
    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95
    )
    
    tfidf_matrix = vectorizer.fit_transform(transcript_texts)
    feature_names = vectorizer.get_feature_names_out()
    
    # Cluster
    clusterer = KMeans(n_clusters=num_topics, random_state=42, n_init=10)
    cluster_labels = clusterer.fit_predict(tfidf_matrix)
    
    # Extract topics
    topics = []
    for label in range(num_topics):
        cluster_mask = cluster_labels == label
        cluster_docs = tfidf_matrix[cluster_mask]
        
        if cluster_docs.shape[0] == 0:
            continue
        
        mean_scores = np.asarray(cluster_docs.mean(axis=0)).flatten()
        top_indices = mean_scores.argsort()[-10:][::-1]
        top_terms = [feature_names[i] for i in top_indices]
        
        cluster_podcast_ids = [podcast_ids[i] for i in range(len(podcast_ids)) if cluster_mask[i]]
        cluster_feeds = [feed_names[i] for i in range(len(feed_names)) if cluster_mask[i]]
        
        topics.append({
            'topic': ', '.join(top_terms[:3]),
            'description': f"Cluster based on terms: {', '.join(top_terms[:5])}",
            'key_phrases': top_terms[:10],
            'related_themes': [],
            'podcast_count': len(cluster_podcast_ids),
            'podcast_ids': cluster_podcast_ids,
            'feeds': list(set(cluster_feeds))
        })
    
    topics.sort(key=lambda x: x['podcast_count'], reverse=True)
    return topics


def load_transcripts_from_postgres(
    db: PostgresDB,
    feed_filter: str = "All",
    min_words: int = 100,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Load transcripts from PostgreSQL database.
    
    Args:
        db: PostgresDB instance
        feed_filter: Filter by feed name ("All" for all feeds)
        min_words: Minimum word count to include
        limit: Maximum number of podcasts to load
        
    Returns:
        List of transcript dictionaries with id, title, feed_name, text, etc.
    """
    podcasts = db.get_all_podcasts(status=None, limit=limit)
    
    # Filter by feed if specified
    if feed_filter != "All":
        podcasts = [p for p in podcasts if p.get('podcast_feed_name') == feed_filter]
    
    # Extract transcripts
    transcript_data = []
    for podcast in podcasts:
        transcript = podcast.get('transcript')
        if not transcript:
            continue
        
        # Handle JSONB field
        if isinstance(transcript, str):
            try:
                transcript = json.loads(transcript)
            except:
                continue
        elif not isinstance(transcript, dict):
            continue
        
        # Extract text
        text = transcript.get('text', '')
        if not text:
            # Try to construct from segments
            segments = transcript.get('segments', [])
            if segments:
                text = ' '.join([
                    seg.get('text', '') 
                    for seg in segments 
                    if isinstance(seg, dict)
                ])
        
        # Filter by minimum length
        word_count = len(text.split())
        if word_count < min_words:
            continue
        
        transcript_data.append({
            'id': podcast['id'],
            'title': podcast.get('title', 'Untitled'),
            'feed_name': podcast.get('podcast_feed_name', 'Unknown'),
            'category': podcast.get('podcast_category', 'general'),
            'published_at': podcast.get('published_at'),
            'text': text,
            'word_count': word_count,
            'segments': transcript.get('segments', [])
        })
    
    return transcript_data


def analyze_podcast_topics_from_postgres(
    db: PostgresDB,
    feed_filter: str = "All",
    min_words: int = 100,
    num_topics: int = 10,
    method: str = "llm",
    max_chars: int = 100000,
    per_feed: bool = False
) -> Union[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """
    Analyze topics from PostgreSQL database transcripts.
    
    Args:
        db: PostgresDB instance
        feed_filter: Filter by feed name
        min_words: Minimum transcript length
        num_topics: Number of topics to discover
        method: "llm" or "kmeans"
        max_chars: Max characters per LLM request
        per_feed: If True, analyze per feed; if False, aggregate all
        
    Returns:
        Dictionary with topics and metadata (or dict of feed results if per_feed=True)
    """
    # Load transcripts
    transcript_data = load_transcripts_from_postgres(db, feed_filter, min_words)
    
    if not transcript_data:
        return {} if per_feed else {'topics': [], 'total_podcasts': 0, 'transcript_data': []}
    
    if per_feed:
        # Group by feed
        feed_groups = defaultdict(list)
        for item in transcript_data:
            feed_groups[item['feed_name']].append(item)
        
        results = {}
        
        for feed_name, items in feed_groups.items():
            if len(items) < 2:
                continue  # Need at least 2 podcasts for clustering
            
            texts = [item['text'] for item in items]
            podcast_ids = [item['id'] for item in items]
            feed_names = [item['feed_name'] for item in items]
            
            try:
                if method == "llm":
                    topics = analyze_topics_from_transcripts_with_groq(
                        texts, podcast_ids, feed_names, num_topics, max_chars
                    )
                elif method == "kmeans":
                    topics = analyze_topics_with_kmeans(texts, podcast_ids, feed_names, num_topics)
                else:
                    continue
                
                results[feed_name] = {
                    'topics': topics,
                    'total_podcasts': len(items)
                }
            except Exception as e:
                print(f"Error analyzing {feed_name}: {e}")
                continue
        
        return results
    else:
        # Aggregate all podcasts
        texts = [item['text'] for item in transcript_data]
        podcast_ids = [item['id'] for item in transcript_data]
        feed_names = [item['feed_name'] for item in transcript_data]
        
        if method == "llm":
            topics = analyze_topics_from_transcripts_with_groq(
                texts, podcast_ids, feed_names, num_topics, max_chars
            )
        elif method == "kmeans":
            topics = analyze_topics_with_kmeans(texts, podcast_ids, feed_names, num_topics)
        else:
            raise ValueError(f"Unknown method: {method}. Use 'llm' or 'kmeans'")
        
        return {
            'topics': topics,
            'total_podcasts': len(transcript_data),
            'transcript_data': transcript_data
        }


def analyze_podcast_topics(
    podcast_id: Optional[int],
    db: PostgresDB,
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
    topics = analyze_topics_with_groq(summaries, num_topics)
    
    # Cache results
    db.save_topic_analysis(podcast_id, analysis_type, topics)
    
    return topics

