"""
Integration test for the basic workflow.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from codedoc.llm.openai_client import OpenAIClient
from codedoc.enhancers.file_enhancer import FileEnhancer
from codedoc.preprocessors.chunker import Chunker, ChunkingStrategy
from codedoc.preprocessors.file_processor import FileProcessor
from codedoc.vectorstore.openai_vectorstore import OpenAIVectorStore


@pytest.mark.integration
class TestBasicWorkflow:
    """Integration test for the basic workflow."""
    
    @pytest.fixture
    def sample_codebase(self, temp_dir):
        """Create a sample codebase with multiple files."""
        # Create source directory
        src_dir = temp_dir / "src"
        src_dir.mkdir()
        
        # Create Python files
        with open(src_dir / "main.py", "w") as f:
            f.write("""
\"\"\"
Main module for the application.
\"\"\"

import os
import sys
from utils import format_string

def main():
    \"\"\"
    Main entry point for the application.
    \"\"\"
    print("Hello, world!")
    
    # Format a sample string
    formatted = format_string("test")
    print(formatted)
    
if __name__ == "__main__":
    main()
""")
        
        with open(src_dir / "utils.py", "w") as f:
            f.write("""
\"\"\"
Utility functions for the application.
\"\"\"

def format_string(s):
    \"\"\"
    Format a string by converting it to uppercase and adding exclamation.
    
    Args:
        s: The string to format
        
    Returns:
        Formatted string
    \"\"\"
    return s.upper() + "!"
""")
        
        # Return the directory containing the codebase
        return src_dir
    
    @patch("openai.OpenAI")
    def test_enhance_and_process_workflow(self, mock_openai, sample_codebase, temp_dir):
        """Test the basic workflow of enhancing files and processing them for vector storage."""
        # Set up mock LLM response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "# Enhanced documentation\n\nThis function does something important."
        mock_response.usage.total_tokens = 150
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Create output directories
        output_dir = temp_dir / "output"
        enhanced_dir = output_dir / "enhanced"
        processed_dir = output_dir / "processed"
        
        # Step 1: Initialize OpenAI client
        openai_client = OpenAIClient(api_key="test_api_key")
        
        # Step 2: Initialize and run file enhancer
        enhancer = FileEnhancer(
            llm_client=openai_client,
            output_dir=enhanced_dir,
            model="gpt-4"
        )
        
        # Enhance the files
        enhancement_result = enhancer.enhance_directory(
            input_dir=sample_codebase,
            file_patterns=["*.py"],
            recursive=False
        )
        
        # Verify enhancement result
        assert enhancement_result["enhanced_files"] == 2
        assert enhancement_result["total_tokens_used"] == 2 * 150  # 2 files * 150 tokens each
        
        # Verify enhanced files exist
        assert (enhanced_dir / "main.py").exists()
        assert (enhanced_dir / "utils.py").exists()
        
        # Step 3: Initialize and run file processor
        chunker = Chunker(
            strategy=ChunkingStrategy.CODE_BLOCK,
            chunk_size=1000,
            chunk_overlap=100
        )
        
        processor = FileProcessor(
            output_dir=processed_dir,
            chunker=chunker
        )
        
        # Process the enhanced files
        processing_result = processor.process_directory(
            input_dir=enhanced_dir,
            file_patterns=["*.py"],
            recursive=False
        )
        
        # Verify processing result
        assert processing_result["summary"]["files_processed"] == 2
        assert processing_result["summary"]["chunks_created"] > 0
        
        # Verify output files exist
        assert (processed_dir / "chunks").exists()
        assert (processed_dir / "metadata").exists()
        assert len(list((processed_dir / "chunks").glob("*.json"))) == 2
        
        # Step 4: Create batch file for vector store
        batch_file = processed_dir / "openai_batch.jsonl"
        batch_result = processor.create_openai_batch_file(batch_file)
        
        # Verify batch file creation
        assert batch_file.exists()
        assert batch_result["num_chunks"] > 0
        
        # Verify batch file format
        with open(batch_file, "r") as f:
            lines = f.readlines()
            assert len(lines) > 0
            
            # Check first line has expected format
            first_chunk = json.loads(lines[0])
            assert "text" in first_chunk
            assert "metadata" in first_chunk
            assert "file_path" in first_chunk["metadata"]
    
    @patch("openai.OpenAI")
    def test_process_and_search_workflow(self, mock_openai, sample_codebase, temp_dir):
        """Test the workflow of processing files and searching the vector store."""
        # Set up mock OpenAI client responses for embedding and search
        mock_client = MagicMock()
        
        # Mock embedding response
        mock_client.embeddings.create.return_value.data = [{"embedding": [0.1, 0.2, 0.3]}]
        
        # Mock search response
        mock_search_response = {
            "object": "list",
            "data": [
                {
                    "object": "assistants_search_result",
                    "score": 0.95,
                    "document": {
                        "text": "def format_string(s):\n    \"\"\"Format a string by converting it to uppercase.\"\"\"\n    return s.upper() + \"!\"",
                        "metadata": {"file_path": "utils.py", "language": "python"}
                    }
                }
            ]
        }
        mock_client.vector_stores.file_search.return_value = mock_search_response
        
        # Mock file upload response
        mock_client.files.create.return_value = {"id": "file-123", "purpose": "assistants", "status": "uploaded"}
        
        mock_openai.return_value = mock_client
        
        # Create output directories
        processed_dir = temp_dir / "processed"
        
        # Step 1: Initialize and run file processor directly on sample codebase
        chunker = Chunker(
            strategy=ChunkingStrategy.CODE_BLOCK,
            chunk_size=1000,
            chunk_overlap=100
        )
        
        processor = FileProcessor(
            output_dir=processed_dir,
            chunker=chunker
        )
        
        # Process the original files
        processor.process_directory(
            input_dir=sample_codebase,
            file_patterns=["*.py"],
            recursive=False
        )
        
        # Create batch file
        batch_file = processed_dir / "openai_batch.jsonl"
        processor.create_openai_batch_file(batch_file)
        
        # Step 2: Initialize vector store client
        vector_store = OpenAIVectorStore(api_key="test_api_key")
        
        # Step 3: Upload batch file
        upload_result = vector_store.upload_batch(batch_file)
        
        # Verify upload result
        assert "files" in upload_result
        assert len(upload_result["files"]) > 0
        
        # Step 4: Search vector store
        search_results = vector_store.search_vector_store(
            query="How to format a string?",
            file_ids=["file-123"]
        )
        
        # Verify search results
        assert len(search_results) == 1
        assert search_results[0]["content"].startswith("def format_string")
        assert search_results[0]["score"] == 0.95
        assert search_results[0]["metadata"]["file_path"] == "utils.py" 