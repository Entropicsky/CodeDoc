"""
Tests for the output formatter module.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path

from codedoc.preprocessors.output_formatter import OutputFormatter


class TestOutputFormatter:
    """Tests for the OutputFormatter class."""
    
    def test_init(self, temp_dir):
        """Test initialization."""
        # Initialize with defaults
        formatter = OutputFormatter(output_dir=temp_dir)
        
        # Verify initialization
        assert formatter.output_dir == Path(temp_dir)
        assert formatter.metadata_defaults == {}
        
        # Initialize with custom metadata defaults
        custom_defaults = {"source": "test", "priority": "high"}
        formatter = OutputFormatter(
            output_dir=temp_dir,
            metadata_defaults=custom_defaults
        )
        
        # Verify custom defaults
        assert formatter.metadata_defaults == custom_defaults
    
    def test_clean_content(self, temp_dir):
        """Test content cleaning functionality."""
        formatter = OutputFormatter(output_dir=temp_dir)
        
        # Test with null bytes
        content_with_nulls = "Hello\x00World"
        cleaned = formatter._clean_content(content_with_nulls)
        assert cleaned == "Hello World"
        
        # Test with excessive whitespace
        content_with_spaces = "  Hello  \n  World  "
        cleaned = formatter._clean_content(content_with_spaces)
        assert cleaned == "Hello World"
        
        # Test with very long content
        long_content = "x" * 110000
        cleaned = formatter._clean_content(long_content)
        assert len(cleaned) <= 100015  # Account for truncation message
        assert "... [truncated]" in cleaned
    
    def test_format_for_openai(self, temp_dir):
        """Test formatting for OpenAI vector store."""
        formatter = OutputFormatter(output_dir=temp_dir)
        
        # Test with basic content and metadata
        content = "This is a test document."
        metadata = {"file_type": "text", "language": "English"}
        
        # Format for OpenAI
        formatted = formatter._format_for_openai(content, metadata)
        
        # Verify format
        assert formatted["text"] == content
        assert formatted["metadata"] == metadata
        
        # Test with chunk ID
        formatted = formatter._format_for_openai(content, metadata, chunk_id="123")
        assert formatted["metadata"]["chunk_id"] == "123"
    
    def test_format_for_pinecone(self, temp_dir):
        """Test formatting for Pinecone vector store."""
        formatter = OutputFormatter(output_dir=temp_dir)
        
        # Test with basic content and metadata
        content = "This is a test document."
        metadata = {"file_type": "text", "language": "English"}
        
        # Format for Pinecone
        formatted = formatter._format_for_pinecone(content, metadata)
        
        # Verify format
        assert "id" in formatted
        assert formatted["text"] == content
        assert formatted["metadata"]["file_type"] == "text"
        assert formatted["metadata"]["language"] == "English"
        assert formatted["metadata"]["text"] == content  # Preview in metadata
        
        # Test with provided ID
        formatted = formatter._format_for_pinecone(content, metadata, chunk_id="chunk123")
        assert formatted["id"] == "chunk123"
    
    def test_format_for_vector_store_openai(self, temp_dir):
        """Test formatting for OpenAI vector store."""
        formatter = OutputFormatter(
            output_dir=temp_dir,
            metadata_defaults={"source": "test_suite"}
        )
        
        # Format content for OpenAI
        content = "Sample content"
        metadata = {"file_type": "markdown"}
        
        formatted = formatter.format_for_vector_store(
            content=content,
            metadata=metadata,
            format_type="openai"
        )
        
        # Verify format
        assert formatted["text"] == content
        assert formatted["metadata"]["file_type"] == "markdown"
        assert formatted["metadata"]["source"] == "test_suite"  # Default metadata included
    
    def test_format_for_vector_store_pinecone(self, temp_dir):
        """Test formatting for Pinecone vector store."""
        formatter = OutputFormatter(
            output_dir=temp_dir,
            metadata_defaults={"source": "test_suite"}
        )
        
        # Format content for Pinecone
        content = "Sample content"
        metadata = {"file_type": "markdown"}
        
        formatted = formatter.format_for_vector_store(
            content=content,
            metadata=metadata,
            format_type="pinecone"
        )
        
        # Verify format
        assert formatted["text"] == content
        assert formatted["metadata"]["file_type"] == "markdown"
        assert formatted["metadata"]["source"] == "test_suite"  # Default metadata included
        assert "id" in formatted
    
    def test_format_for_vector_store_unknown(self, temp_dir):
        """Test formatting for unknown vector store type."""
        formatter = OutputFormatter(output_dir=temp_dir)
        
        # Format content for unknown type
        content = "Sample content"
        metadata = {"file_type": "markdown"}
        
        formatted = formatter.format_for_vector_store(
            content=content,
            metadata=metadata,
            format_type="unknown"
        )
        
        # Verify fallback format
        assert formatted["content"] == content
        assert formatted["metadata"] == metadata
        assert formatted["id"] is None
    
    def test_format_batch_memory(self, temp_dir):
        """Test batch formatting in memory (without file output)."""
        formatter = OutputFormatter(output_dir=temp_dir)
        
        # Create batch items
        items = [
            {"content": "Item 1", "metadata": {"index": 1}},
            {"content": "Item 2", "metadata": {"index": 2}},
            {"content": "Item 3", "metadata": {"index": 3}}
        ]
        
        # Format batch for OpenAI
        formatted = formatter.format_batch(
            items=items,
            format_type="openai"
        )
        
        # Verify batch formatting
        assert len(formatted) == 3
        assert formatted[0]["text"] == "Item 1"
        assert formatted[1]["text"] == "Item 2"
        assert formatted[2]["text"] == "Item 3"
        assert formatted[0]["metadata"]["index"] == 1
        assert formatted[1]["metadata"]["index"] == 2
        assert formatted[2]["metadata"]["index"] == 3
    
    def test_format_batch_file_openai(self, temp_dir):
        """Test batch formatting with file output for OpenAI."""
        formatter = OutputFormatter(output_dir=temp_dir)
        
        # Create batch items
        items = [
            {"content": "Item 1", "metadata": {"index": 1}},
            {"content": "Item 2", "metadata": {"index": 2}}
        ]
        
        # Format batch for OpenAI with file output
        output_file = "openai_batch.jsonl"
        result = formatter.format_batch(
            items=items,
            format_type="openai",
            output_file=output_file
        )
        
        # Verify file was created
        output_path = temp_dir / output_file
        assert output_path.exists()
        assert result == str(output_path)
        
        # Verify file contents
        with open(output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 2
            
            # Parse each line as JSON
            item1 = json.loads(lines[0])
            item2 = json.loads(lines[1])
            
            assert item1["text"] == "Item 1"
            assert item2["text"] == "Item 2"
            assert item1["metadata"]["index"] == 1
            assert item2["metadata"]["index"] == 2
    
    def test_format_batch_file_other(self, temp_dir):
        """Test batch formatting with file output for non-OpenAI format."""
        formatter = OutputFormatter(output_dir=temp_dir)
        
        # Create batch items
        items = [
            {"content": "Item 1", "metadata": {"index": 1}},
            {"content": "Item 2", "metadata": {"index": 2}}
        ]
        
        # Format batch for Pinecone with file output
        output_file = "pinecone_batch.json"
        result = formatter.format_batch(
            items=items,
            format_type="pinecone",
            output_file=output_file
        )
        
        # Verify file was created
        output_path = temp_dir / output_file
        assert output_path.exists()
        assert result == str(output_path)
        
        # Verify file contents (should be a JSON array)
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert isinstance(data, list)
            assert len(data) == 2
            
            assert data[0]["text"] == "Item 1"
            assert data[1]["text"] == "Item 2"
            assert data[0]["metadata"]["index"] == 1
            assert data[1]["metadata"]["index"] == 2 