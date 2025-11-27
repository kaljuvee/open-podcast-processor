"""Export functionality for P³ digests."""

import json
from datetime import date
from typing import Dict, List, Any


class DigestExporter:
    def __init__(self, db):
        self.db = db

    def export_markdown(self, summaries: List[Dict[str, Any]], target_date: date) -> str:
        """Export summaries as Markdown."""
        content = [f"# Podcast Digest - {target_date}\n"]
        
        if not summaries:
            content.append("No summaries available for this date.\n")
            return "\n".join(content)
        
        # Group by podcast
        by_podcast = {}
        for summary in summaries:
            podcast = summary['podcast_title']
            if podcast not in by_podcast:
                by_podcast[podcast] = []
            by_podcast[podcast].append(summary)
        
        for podcast_name, episodes in by_podcast.items():
            content.append(f"## {podcast_name}\n")
            
            for episode in episodes:
                content.append(f"### {episode['episode_title']}\n")
                
                if episode['full_summary']:
                    content.append(f"**Summary:** {episode['full_summary']}\n")
                
                if episode['key_topics']:
                    content.append("**Key Topics:**")
                    for topic in episode['key_topics']:
                        content.append(f"- {topic}")
                    content.append("")
                
                if episode['themes']:
                    content.append("**Themes:**")
                    for theme in episode['themes']:
                        content.append(f"- {theme}")
                    content.append("")
                
                if episode['quotes']:
                    content.append("**Notable Quotes:**")
                    for quote in episode['quotes']:
                        content.append(f"> {quote}")
                    content.append("")
                
                if episode['startups']:
                    content.append("**Companies/Startups Mentioned:**")
                    for startup in episode['startups']:
                        content.append(f"- {startup}")
                    content.append("")
                
                content.append("---\n")
        
        return "\n".join(content)

    def export_json(self, summaries: List[Dict[str, Any]], target_date: date) -> str:
        """Export summaries as JSON."""
        export_data = {
            "date": str(target_date),
            "total_episodes": len(summaries),
            "summaries": summaries
        }
        
        return json.dumps(export_data, indent=2, default=str)

    def export_email_html(self, summaries: List[Dict[str, Any]], target_date: date) -> str:
        """Export summaries as HTML for email."""
        html = f"""
        <html>
        <head>
            <title>Podcast Digest - {target_date}</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; }}
                h1, h2, h3 {{ color: #333; }}
                .podcast {{ margin-bottom: 2em; }}
                .episode {{ margin-bottom: 1.5em; padding: 1em; background: #f9f9f9; }}
                .summary {{ font-style: italic; margin-bottom: 1em; }}
                .topics, .themes, .startups {{ margin-bottom: 0.5em; }}
                .quote {{ background: #e8e8e8; padding: 0.5em; margin: 0.5em 0; }}
                ul {{ margin: 0.5em 0; }}
            </style>
        </head>
        <body>
            <h1>Podcast Digest - {target_date}</h1>
        """
        
        if not summaries:
            html += "<p>No summaries available for this date.</p>"
        else:
            # Group by podcast
            by_podcast = {}
            for summary in summaries:
                podcast = summary['podcast_title']
                if podcast not in by_podcast:
                    by_podcast[podcast] = []
                by_podcast[podcast].append(summary)
            
            for podcast_name, episodes in by_podcast.items():
                html += f'<div class="podcast"><h2>{podcast_name}</h2>'
                
                for episode in episodes:
                    html += f'<div class="episode"><h3>{episode["episode_title"]}</h3>'
                    
                    if episode['full_summary']:
                        html += f'<div class="summary"><strong>Summary:</strong> {episode["full_summary"]}</div>'
                    
                    if episode['key_topics']:
                        html += '<div class="topics"><strong>Key Topics:</strong><ul>'
                        for topic in episode['key_topics']:
                            html += f'<li>{topic}</li>'
                        html += '</ul></div>'
                    
                    if episode['themes']:
                        html += '<div class="themes"><strong>Themes:</strong><ul>'
                        for theme in episode['themes']:
                            html += f'<li>{theme}</li>'
                        html += '</ul></div>'
                    
                    if episode['quotes']:
                        html += '<div><strong>Notable Quotes:</strong>'
                        for quote in episode['quotes']:
                            html += f'<div class="quote">{quote}</div>'
                        html += '</div>'
                    
                    if episode['startups']:
                        html += '<div class="startups"><strong>Companies/Startups:</strong><ul>'
                        for startup in episode['startups']:
                            html += f'<li>{startup}</li>'
                        html += '</ul></div>'
                    
                    html += '</div>'  # episode
                
                html += '</div>'  # podcast
        
        html += """
        </body>
        </html>
        """
        
        return html
