#!/usr/bin/env python3
"""
🌐 STEP 3: Serve Corpus
HTTP server that serves corpus websites with proper CSS/asset dependency handling.
Enables the backend to make requests to local/simulated domains.
"""

import os
import logging
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Optional
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CorpusHTTPHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler with CORS and asset dependency support."""
    
    def do_GET(self) -> None:
        """Handle GET requests."""
        # TODO: Implement custom GET handling
        # - Map requests to corpus files
        # - Handle CSS/JS/image dependencies
        # - Add CORS headers if needed
        pass
    
    def do_HEAD(self) -> None:
        """Handle HEAD requests."""
        # TODO: Implement custom HEAD handling
        pass
    
    def send_cors_headers(self) -> None:
        """Add CORS headers to response."""
        # TODO: Add CORS headers
        pass
    
    def log_message(self, format_str: str, *args) -> None:
        """Override logging to use standard logger."""
        logger.debug(format_str % args)


class CorpusServer:
    """HTTP server for serving corpus."""
    
    def __init__(self, corpus_path: str, host: str = 'localhost', port: int = 8000):
        """
        Initialize corpus server.
        
        Args:
            corpus_path: Path to corpus directory
            host: Host to bind to (default: localhost)
            port: Port to listen on (default: 8000)
        """
        self.corpus_path = Path(corpus_path)
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """Start the HTTP server."""
        logger.info(f"Starting corpus server on {self.host}:{self.port}")
        logger.info(f"Serving from: {self.corpus_path}")
        
        # TODO: Implement server startup
        # - Create HTTPServer with CorpusHTTPHandler
        # - Change to corpus_path directory
        # - Start in background thread
        pass
    
    def stop(self) -> None:
        """Stop the HTTP server."""
        logger.info("Stopping corpus server")
        # TODO: Implement server shutdown
        pass
    
    def run_forever(self) -> None:
        """Run the server in the main thread."""
        # TODO: Implement blocking server run
        pass


def main():
    """Main entry point."""
    base_dir = os.path.dirname(__file__)
    corpus_dir = os.path.join(base_dir, 'corpus')
    
    server = CorpusServer(corpus_dir, host='0.0.0.0', port=8000)
    
    try:
        logger.info("🌐 Corpus HTTP Server")
        logger.info("Starting server (Press Ctrl+C to stop)")
        server.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
        server.stop()
    finally:
        logger.info("✅ Server stopped")


if __name__ == "__main__":
    main()
