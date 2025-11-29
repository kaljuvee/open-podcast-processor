"""
AI Assistant Page
Chat interface for asking questions about podcast transcripts using SQL and LLM.
"""

import streamlit as st
from typing import Dict, List, Any
import json

from utils.postgres_db import PostgresDB
from utils.langchain_sql_util import PodcastSQLAssistant

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

st.title("🤖 AI Assistant")
st.markdown("Ask questions about podcast transcripts. I'll search the database and provide answers based on the content.")

# Initialize database connection
try:
    db = PostgresDB()
    schema = db.schema
    if schema and schema != 'public':
        st.sidebar.info(f"📊 Using schema: `{schema}`")
except ValueError as e:
    st.error(f"Database configuration error: {e}")
    st.info("Please ensure DB_URL is set in your .env file")
    st.stop()
except Exception as e:
    st.error(f"Failed to connect to PostgreSQL: {e}")
    st.stop()

# Initialize AI Assistant
@st.cache_resource
def get_assistant():
    """Get cached AI assistant instance."""
    try:
        return PodcastSQLAssistant(db=db)
    except Exception as e:
        st.error(f"Failed to initialize AI Assistant: {e}")
        st.info("Please ensure GROQ_API_KEY is set in your .env file")
        return None

assistant = get_assistant()

if assistant is None:
    st.stop()

# Sample questions
sample_questions = [
    "What are the main topics discussed about trading?",
    "Which episodes mention startups or venture capital?",
    "What insights are shared about AI and machine learning?",
    "What are the key themes in business strategy discussions?",
    "Which podcasts discuss product development or SaaS?",
    "What are the most interesting quotes about investing?"
]

# Initialize chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Sidebar with sample questions
with st.sidebar:
    st.header("💡 Sample Questions")
    st.markdown("Click a question below to get started:")
    
    # Two rows of buttons (3 per row)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📈 Trading", use_container_width=True, key="sample_1"):
            st.session_state.current_question = sample_questions[0]
            st.rerun()
    
    with col2:
        if st.button("🚀 Startups", use_container_width=True, key="sample_2"):
            st.session_state.current_question = sample_questions[1]
            st.rerun()
    
    with col3:
        if st.button("🤖 AI/ML", use_container_width=True, key="sample_3"):
            st.session_state.current_question = sample_questions[2]
            st.rerun()
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        if st.button("💼 Strategy", use_container_width=True, key="sample_4"):
            st.session_state.current_question = sample_questions[3]
            st.rerun()
    
    with col5:
        if st.button("📦 Product", use_container_width=True, key="sample_5"):
            st.session_state.current_question = sample_questions[4]
            st.rerun()
    
    with col6:
        if st.button("💰 Investing", use_container_width=True, key="sample_6"):
            st.session_state.current_question = sample_questions[5]
            st.rerun()
    
    st.divider()
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()
    
    # Statistics
    st.markdown("### 📊 Statistics")
    st.info(f"**Chat Messages:** {len(st.session_state.chat_history)}")

# Main chat interface
st.markdown("---")

# Display chat history
chat_container = st.container()

with chat_container:
    for i, message in enumerate(st.session_state.chat_history):
        role = message['role']
        content = message['content']
        
        if role == 'user':
            with st.chat_message("user"):
                st.write(content)
        elif role == 'assistant':
            with st.chat_message("assistant"):
                st.write(content['answer'])
                
                # Show sources if available
                if content.get('sources'):
                    with st.expander(f"📚 Sources ({len(content['sources'])} episodes)", expanded=False):
                        for source in content['sources']:
                            st.markdown(f"- **{source['title']}** ({source['feed']})")
                
                # Show metadata
                if content.get('episodes_used'):
                    st.caption(f"Based on {content['episodes_used']} episode(s)")

# Chat input
question = st.chat_input("Ask a question about podcast transcripts...")

# Handle sample question or new question
if 'current_question' in st.session_state:
    question = st.session_state.current_question
    del st.session_state.current_question

if question:
    # Add user message to history
    st.session_state.chat_history.append({
        'role': 'user',
        'content': question
    })
    
    # Show user message
    with st.chat_message("user"):
        st.write(question)
    
    # Generate answer
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching transcripts and generating answer..."):
            try:
                result = assistant.query(question)
                
                # Display answer
                st.write(result['answer'])
                
                # Show sources
                if result.get('sources'):
                    with st.expander(f"📚 Sources ({len(result['sources'])} episodes)", expanded=False):
                        for source in result['sources']:
                            st.markdown(f"- **{source['title']}** ({source['feed']})")
                
                # Show metadata
                metadata_text = f"Based on {result.get('episodes_used', 0)} episode(s)"
                if result.get('context_length'):
                    metadata_text += f" ({result['context_length']:,} chars)"
                st.caption(metadata_text)
                
                # Add assistant response to history
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': result
                })
                
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.error(error_msg)
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': {
                        'answer': error_msg,
                        'sources': [],
                        'episodes_used': 0,
                        'error': str(e)
                    }
                })
    
    st.rerun()

# Footer info
st.markdown("---")
st.info("💡 **Tip:** The AI searches podcast transcripts using SQL queries and provides answers based on the actual content. Make sure episodes are transcribed before asking questions.")

# Close database connection
db.close()

