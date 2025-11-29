"""
Streamlit logger utility to capture print statements and display in Streamlit.
"""

import sys
from io import StringIO
from contextlib import contextmanager
from typing import List, Optional
import streamlit as st
import html


class StreamlitLogger:
    """Capture stdout/stderr and display in Streamlit."""
    
    def __init__(self, container=None):
        self.container = container
        self.logs: List[str] = []
        self.original_stdout = None
        self.original_stderr = None
        self.string_io = None
    
    def start(self):
        """Start capturing output."""
        self.logs = []
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.string_io = StringIO()
        sys.stdout = self.string_io
        sys.stderr = self.string_io
    
    def stop(self):
        """Stop capturing and return logs."""
        if self.original_stdout:
            sys.stdout = self.original_stdout
        if self.original_stderr:
            sys.stderr = self.original_stderr
        
        if self.string_io:
            output = self.string_io.getvalue()
            self.string_io.close()
            if output:
                # Split into lines and add to logs
                lines = output.strip().split('\n')
                self.logs.extend([line for line in lines if line.strip()])
        
        return self.logs
    
    def display(self, max_lines: int = 200):
        """Display logs in Streamlit container."""
        if not self.logs:
            return
        
        display_logs = self.logs[-max_lines:] if len(self.logs) > max_lines else self.logs
        
        if self.container:
            with self.container:
                # Escape HTML and create scrollable log display
                log_text = '\n'.join(display_logs)
                escaped_text = html.escape(log_text)
                
                # Create a scrollable code block with dark theme
                st.markdown(
                    f'<div style="background-color: #1e1e1e; color: #d4d4d4; padding: 1rem; '
                    f'border-radius: 0.5rem; max-height: 500px; overflow-y: auto; '
                    f'font-family: "Courier New", monospace; font-size: 0.85em; '
                    f'border: 1px solid #3e3e3e;">'
                    f'<pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;">{escaped_text}</pre>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                # Show log count
                if len(self.logs) > max_lines:
                    st.caption(f"📋 Showing last {len(display_logs)} of {len(self.logs)} log lines")
                else:
                    st.caption(f"📋 {len(self.logs)} log lines")
        else:
            log_text = '\n'.join(display_logs)
            st.code(log_text, language=None)


@contextmanager
def capture_output(container=None, display: bool = True, max_lines: int = 200, auto_update: bool = False):
    """
    Context manager to capture print statements and display in Streamlit.
    
    Args:
        container: Streamlit container to display logs in
        display: Whether to display logs
        max_lines: Maximum number of lines to display
        auto_update: Whether to update display in real-time (not recommended for Streamlit)
    
    Usage:
        with capture_output(st.container(), display=True):
            print("This will be captured and shown in Streamlit")
    """
    logger = StreamlitLogger(container)
    logger.start()
    
    try:
        yield logger
    finally:
        logs = logger.stop()
        if display and logs:
            # Final display after all output is captured
            logger.display(max_lines=max_lines)

