#!/usr/bin/env python3
"""
Parser service main entry point
Processes content with Polars and generates embeddings
"""

import sys
import logging
import re
from datetime import datetime
import polars as pl
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the sentence transformer model
model = SentenceTransformer("thenlper/gte-small")

def strip_tags(html_content: str) -> str:
    """Remove HTML tags from content"""
    # Simple HTML tag removal
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', html_content)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def process_content(html_content: str) -> dict:
    """Process HTML content and generate embeddings"""
    # Strip HTML tags
    text = strip_tags(html_content)
    
    if not text:
        logger.warning("Empty text after HTML stripping")
        text = "No content"
    
    # Generate embedding
    try:
        embedding = model.encode(text).tolist()
        logger.info(f"Generated embedding with {len(embedding)} dimensions")
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        # Fallback to zero vector
        embedding = [0.0] * 384  # gte-small has 384 dimensions
    
    return {
        "text": text,
        "embedding": embedding,
        "processed_at": datetime.utcnow().isoformat(),
        "text_length": len(text)
    }

def main():
    """Main parser service entry point"""
    logger.info("Starting parser service...")
    
    try:
        # Read HTML content from stdin
        html_content = sys.stdin.read()
        
        if not html_content:
            logger.error("No input content received")
            sys.exit(1)
        
        logger.info(f"Processing {len(html_content)} characters of HTML content")
        
        # Process the content
        processed_data = process_content(html_content)
        
        # Create Polars DataFrame
        df = pl.DataFrame([processed_data])
        
        # Write to stdout as Arrow IPC stream
        df.write_ipc_stream(sys.stdout.buffer)
        
        logger.info("Successfully processed content and wrote Arrow IPC stream")
        
    except Exception as e:
        logger.error(f"Parser failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()