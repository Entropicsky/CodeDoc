"""
Output formatter for standardizing content for vector stores.

This module provides functionality for formatting and standardizing
content for consistent vectorization and storage.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable

logger = logging.getLogger(__name__)


class OutputFormatter:
    """
    Formats and standardizes content for vector store upload.
    """
    
    def __init__(self, 
                 output_dir: Union[str, Path],
                 metadata_defaults: Optional[Dict[str, Any]] = None):
        """
        Initialize the output formatter.
        
        Args:
            output_dir: Directory where formatted files will be saved
            metadata_defaults: Default metadata to include with all items
        """
        self.output_dir = Path(output_dir)
        self.metadata_defaults = metadata_defaults or {}
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output formatter initialized with output directory: {self.output_dir}")
    
    def format_for_vector_store(self, 
                           content: str,
                           metadata: Dict[str, Any],
                           format_type: str = "openai",
                           chunk_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format content and metadata for vector store compatibility.
        
        Args:
            content: The content text to format
            metadata: Metadata associated with the content
            format_type: Target format ("openai", "pinecone", etc.)
            chunk_id: Optional unique identifier for the chunk
            
        Returns:
            Dictionary with formatted content and metadata
        """
        # Clean and sanitize content
        content = self._clean_content(content)
        
        # Combine with default metadata
        combined_metadata = {**self.metadata_defaults, **metadata}
        
        # Format based on target system
        if format_type.lower() == "openai":
            return self._format_for_openai(content, combined_metadata, chunk_id)
        elif format_type.lower() == "pinecone":
            return self._format_for_pinecone(content, combined_metadata, chunk_id)
        else:
            # Default format
            return {
                "content": content,
                "metadata": combined_metadata,
                "id": chunk_id
            }
    
    def format_batch(self, 
                items: List[Dict[str, Any]],
                format_type: str = "openai",
                output_file: Optional[Union[str, Path]] = None) -> Union[List[Dict[str, Any]], str]:
        """
        Format a batch of items for vector store upload.
        
        Args:
            items: List of items with content and metadata
            format_type: Target format type
            output_file: Optional file path to write the formatted batch
            
        Returns:
            Formatted items list, or path to output file if output_file is provided
        """
        formatted_items = []
        
        for item in items:
            content = item.get("content", "")
            metadata = item.get("metadata", {})
            chunk_id = item.get("id")
            
            formatted_item = self.format_for_vector_store(
                content=content,
                metadata=metadata,
                format_type=format_type,
                chunk_id=chunk_id
            )
            
            formatted_items.append(formatted_item)
        
        # Write to file if output path is provided
        if output_file:
            output_path = self.output_dir / output_file if not os.path.isabs(output_file) else Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type.lower() == "openai":
                with open(output_path, 'w', encoding='utf-8') as f:
                    for item in formatted_items:
                        json.dump(item, f, ensure_ascii=False)
                        f.write('\n')
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(formatted_items, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Formatted batch saved to {output_path}")
            return str(output_path)
        
        return formatted_items
    
    def _clean_content(self, content: str) -> str:
        """
        Clean and sanitize content for vectorization.
        
        Args:
            content: Raw content text
            
        Returns:
            Cleaned content text
        """
        # Remove null bytes and other problematic characters
        content = content.replace('\x00', '')
        
        # Normalize whitespace
        content = ' '.join(content.split())
        
        # Trim to reasonable length if needed
        if len(content) > 100000:  # Arbitrary large limit
            logger.warning(f"Content exceeds 100,000 characters, truncating")
            content = content[:100000] + "... [truncated]"
        
        return content
    
    def _format_for_openai(self, 
                      content: str, 
                      metadata: Dict[str, Any],
                      chunk_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format for OpenAI vector store compatibility.
        
        Args:
            content: Content text
            metadata: Metadata dictionary
            chunk_id: Optional chunk identifier
            
        Returns:
            Formatted dictionary for OpenAI
        """
        # Format according to OpenAI vector store expectations
        formatted = {
            "text": content,
            "metadata": metadata
        }
        
        # Add ID if provided
        if chunk_id:
            formatted["metadata"]["chunk_id"] = chunk_id
        
        return formatted
    
    def _format_for_pinecone(self, 
                        content: str, 
                        metadata: Dict[str, Any],
                        chunk_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format for Pinecone vector store compatibility.
        
        Args:
            content: Content text
            metadata: Metadata dictionary
            chunk_id: Optional chunk identifier
            
        Returns:
            Formatted dictionary for Pinecone
        """
        # Format according to Pinecone expectations
        formatted = {
            "id": chunk_id or metadata.get("id", f"chunk_{hash(content) % 10000000}"),
            "metadata": {
                **metadata,
                "text": content[:1000]  # Include preview in metadata
            },
            "text": content
        }
        
        return formatted 