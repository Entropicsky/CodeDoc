"""
Tests for the chunking strategies.
"""

import pytest
from pathlib import Path

from codedoc.preprocessors.chunker import Chunker, ChunkingStrategy, estimate_tokens


class TestChunker:
    """Tests for the Chunker class."""
    
    def test_init_default_values(self):
        """Test initialization with default values."""
        chunker = Chunker()
        
        assert chunker.strategy == ChunkingStrategy.FIXED_SIZE
        assert chunker.chunk_size == 1500
        assert chunker.chunk_overlap == 200
        assert chunker.max_chunks is None
    
    def test_init_custom_values(self):
        """Test initialization with custom values."""
        chunker = Chunker(
            strategy=ChunkingStrategy.PARAGRAPH,
            chunk_size=1000,
            chunk_overlap=100,
            max_chunks=10
        )
        
        assert chunker.strategy == ChunkingStrategy.PARAGRAPH
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 100
        assert chunker.max_chunks == 10
    
    def test_chunk_document_fixed_size(self):
        """Test chunking a document with fixed size strategy."""
        chunker = Chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=100,
            chunk_overlap=20
        )
        
        # Create a document with 250 characters
        content = "A" * 250
        
        # Chunk the document
        chunks = chunker.chunk_document(content)
        
        # Should produce 3 chunks with overlap: [0-100], [80-180], [160-250]
        assert len(chunks) == 3
        
        # Each chunk should have content and metadata
        for chunk in chunks:
            assert "content" in chunk
            assert "metadata" in chunk
            assert "chunk_index" in chunk["metadata"]
            assert "strategy" in chunk["metadata"]
            assert "total_chunks" in chunk["metadata"]
            
        # Verify chunk contents with overlap
        assert chunks[0]["content"] == "A" * 100
        assert chunks[1]["content"] == "A" * 100
        assert chunks[2]["content"] == "A" * 90  # Last chunk is shorter
        
        # Verify chunk indices
        assert chunks[0]["metadata"]["chunk_index"] == 0
        assert chunks[1]["metadata"]["chunk_index"] == 1
        assert chunks[2]["metadata"]["chunk_index"] == 2
    
    def test_chunk_document_paragraph(self):
        """Test chunking a document with paragraph strategy."""
        chunker = Chunker(
            strategy=ChunkingStrategy.PARAGRAPH,
            chunk_size=1000  # Large enough to keep paragraphs together
        )
        
        # Create a document with paragraphs
        content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        
        # Chunk the document
        chunks = chunker.chunk_document(content)
        
        # Should produce 3 chunks (one per paragraph)
        assert len(chunks) == 3
        
        # Verify chunk contents
        assert chunks[0]["content"] == "First paragraph."
        assert chunks[1]["content"] == "Second paragraph."
        assert chunks[2]["content"] == "Third paragraph."
    
    def test_chunk_document_with_metadata(self):
        """Test chunking a document with provided metadata."""
        chunker = Chunker(strategy=ChunkingStrategy.FIXED_SIZE)
        
        content = "Sample content"
        metadata = {
            "file_path": "test.py",
            "language": "python",
            "custom_field": "value"
        }
        
        # Chunk with metadata
        chunks = chunker.chunk_document(content, metadata)
        
        # Check that metadata is preserved in chunks
        assert chunks[0]["metadata"]["file_path"] == "test.py"
        assert chunks[0]["metadata"]["language"] == "python"
        assert chunks[0]["metadata"]["custom_field"] == "value"
    
    def test_chunk_document_with_file_path(self):
        """Test chunking a document with file path."""
        chunker = Chunker(strategy=ChunkingStrategy.FIXED_SIZE)
        
        content = "Sample content"
        file_path = Path("test.py")
        
        # Chunk with file path
        chunks = chunker.chunk_document(content, file_path=file_path)
        
        # Check that file path is used in metadata
        assert chunks[0]["metadata"]["file_path"] == str(file_path)
        assert chunks[0]["metadata"]["file_extension"] == ".py"
    
    def test_chunk_document_max_chunks(self):
        """Test limiting the number of chunks."""
        chunker = Chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=10,
            chunk_overlap=0,
            max_chunks=2
        )
        
        content = "A" * 50  # Should produce 5 chunks of size 10
        
        # Chunk with max_chunks=2
        chunks = chunker.chunk_document(content)
        
        # Should only return the first 2 chunks
        assert len(chunks) == 2
        assert chunks[0]["metadata"]["total_chunks"] == 5  # Total is still 5
        assert chunks[1]["metadata"]["chunk_index"] == 1
    
    def test_chunk_code_blocks(self):
        """Test chunking with code_block strategy."""
        chunker = Chunker(strategy=ChunkingStrategy.CODE_BLOCK)
        
        # Python code with functions and classes
        content = """
def function1():
    # Function 1
    pass

def function2():
    # Function 2
    pass

class TestClass:
    def method1(self):
        pass
        
    def method2(self):
        pass
"""
        # Set file extension to make it use Python-specific chunking
        chunks = chunker.chunk_document(content, file_path="test.py")
        
        # Should break into logical code blocks
        assert len(chunks) >= 3  # At least one chunk per function/class
        
        # Check content is preserved
        all_content = "".join(chunk["content"] for chunk in chunks)
        assert "function1" in all_content
        assert "function2" in all_content
        assert "TestClass" in all_content
        assert "method1" in all_content
        assert "method2" in all_content
    
    def test_chunk_semantic(self):
        """Test chunking with semantic strategy."""
        chunker = Chunker(strategy=ChunkingStrategy.SEMANTIC)
        
        # Markdown with headings
        content = """# Title

## Section 1
Content for section 1.

## Section 2
Content for section 2.

### Subsection 2.1
Subsection content.
"""
        chunks = chunker.chunk_document(content, file_path="test.md")
        
        # Should create chunks based on sections
        assert len(chunks) >= 3  # At least one per section
        
        # Verify sections are separated
        section_names = [
            "Title",
            "Section 1",
            "Section 2",
            "Subsection 2.1"
        ]
        
        # Check that at least one chunk contains each section name
        for name in section_names:
            assert any(name in chunk["content"] for chunk in chunks)


class TestEstimateTokens:
    """Tests for the estimate_tokens function."""
    
    @pytest.mark.parametrize("text,expected_range", [
        ("", (0, 10)),  # Empty string
        ("Hello world", (2, 4)),  # Short text
        ("A" * 1000, (250, 350)),  # Medium text
    ])
    def test_estimate_tokens(self, text, expected_range):
        """Test token estimation for different texts."""
        tokens = estimate_tokens(text)
        
        # Check that the estimate is within the expected range
        min_expected, max_expected = expected_range
        assert min_expected <= tokens <= max_expected 