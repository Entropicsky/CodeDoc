"""
Tests for the file processor.
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from codedoc.preprocessors.file_processor import FileProcessor
from codedoc.preprocessors.chunker import Chunker, ChunkingStrategy


class TestFileProcessor:
    """Tests for the FileProcessor class."""
    
    def test_init_default_values(self, temp_dir):
        """Test initialization with default values."""
        processor = FileProcessor(output_dir=temp_dir)
        
        # Verify output directories are created
        assert (temp_dir / "chunks").exists()
        assert (temp_dir / "metadata").exists()
        
        # Verify default chunker is created
        assert processor.chunker is not None
        assert isinstance(processor.chunker, Chunker)
        
        # Verify default metadata generator is created
        assert processor.metadata_generator is not None
    
    def test_init_custom_values(self, temp_dir):
        """Test initialization with custom components."""
        # Create mock objects
        mock_chunker = MagicMock()
        mock_metadata_generator = MagicMock()
        
        processor = FileProcessor(
            output_dir=temp_dir,
            chunker=mock_chunker,
            metadata_generator=mock_metadata_generator,
            chunk_strategy=ChunkingStrategy.PARAGRAPH,
            chunk_size=1000,
            chunk_overlap=100
        )
        
        # Verify custom objects are used
        assert processor.chunker is mock_chunker
        assert processor.metadata_generator is mock_metadata_generator
    
    def test_process_file(self, temp_dir, sample_py_file):
        """Test processing a single file."""
        # Initialize processor
        processor = FileProcessor(output_dir=temp_dir)
        
        # Process the file
        result = processor.process_file(sample_py_file)
        
        # Verify successful processing
        assert result["status"] == "success"
        assert result["file_path"] == str(sample_py_file)
        assert result["num_chunks"] > 0
        
        # Verify output files are created
        chunks_file = Path(result["chunks_file"])
        metadata_file = Path(result["metadata_file"])
        assert chunks_file.exists()
        assert metadata_file.exists()
        
        # Verify chunks file content
        with open(chunks_file, 'r') as f:
            chunks = json.load(f)
            assert isinstance(chunks, list)
            assert len(chunks) > 0
            assert "content" in chunks[0]
            assert "metadata" in chunks[0]
            
        # Verify metadata file content
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
            assert isinstance(metadata, dict)
            assert "file_path" in metadata
            assert "file_id" in metadata
    
    def test_process_file_with_custom_metadata(self, temp_dir, sample_py_file):
        """Test processing a file with custom metadata."""
        processor = FileProcessor(output_dir=temp_dir)
        
        # Custom metadata
        custom_metadata = {
            "project": "test-project",
            "author": "test-author",
            "version": "1.0.0"
        }
        
        # Process the file with custom metadata
        result = processor.process_file(sample_py_file, custom_metadata=custom_metadata)
        
        # Verify custom metadata is included
        metadata_file = Path(result["metadata_file"])
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
            assert metadata["project"] == "test-project"
            assert metadata["author"] == "test-author"
            assert metadata["version"] == "1.0.0"
    
    def test_process_file_with_custom_file_id(self, temp_dir, sample_py_file):
        """Test processing a file with custom file ID."""
        processor = FileProcessor(output_dir=temp_dir)
        
        # Process the file with custom file ID
        result = processor.process_file(sample_py_file, file_id="custom-id")
        
        # Verify custom file ID is used
        assert result["file_id"] == "custom-id"
        
        # Verify output files use the custom ID
        assert "custom-id_chunks.json" in result["chunks_file"]
        assert "custom-id_metadata.json" in result["metadata_file"]
    
    def test_process_empty_file(self, temp_dir):
        """Test processing an empty file."""
        # Create an empty file
        empty_file = temp_dir / "empty.py"
        with open(empty_file, 'w') as f:
            pass
        
        processor = FileProcessor(output_dir=temp_dir)
        
        # Process the empty file
        result = processor.process_file(empty_file)
        
        # Verify file is skipped
        assert result["status"] == "skipped"
        assert "empty file" in result["reason"]
    
    def test_process_directory(self, temp_dir):
        """Test processing a directory of files."""
        # Create a directory with multiple files
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        
        # Create Python files
        for i in range(3):
            file_path = input_dir / f"file{i}.py"
            with open(file_path, 'w') as f:
                f.write(f"# File {i}\ndef function{i}():\n    return {i}")
        
        # Create a non-Python file
        txt_file = input_dir / "readme.txt"
        with open(txt_file, 'w') as f:
            f.write("This is a readme file.")
        
        processor = FileProcessor(output_dir=temp_dir)
        
        # Process the directory with Python files only
        result = processor.process_directory(
            input_dir=input_dir,
            file_patterns=["*.py"],
            recursive=False
        )
        
        # Verify processing statistics
        assert result["summary"]["files_processed"] == 3
        assert result["summary"]["successful_files"] == 3
        assert len(result["results"]["success"]) == 3
        
        # Verify summary file is created
        summary_file = temp_dir / "processing_summary.json"
        assert summary_file.exists()
    
    def test_process_directory_with_exclusions(self, temp_dir):
        """Test processing a directory with exclusion patterns."""
        # Create a directory structure
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        
        # Create a subdirectory to exclude
        exclude_dir = input_dir / "exclude_me"
        exclude_dir.mkdir()
        
        # Create files in main directory
        for i in range(2):
            file_path = input_dir / f"file{i}.py"
            with open(file_path, 'w') as f:
                f.write(f"# File {i}")
        
        # Create files in excluded directory
        for i in range(2):
            file_path = exclude_dir / f"excluded{i}.py"
            with open(file_path, 'w') as f:
                f.write(f"# Excluded file {i}")
        
        processor = FileProcessor(output_dir=temp_dir)
        
        # Process the directory with exclusions
        result = processor.process_directory(
            input_dir=input_dir,
            file_patterns=["*.py"],
            recursive=True,
            exclude_dirs=["exclude_me"]
        )
        
        # Verify only non-excluded files are processed
        assert result["summary"]["files_processed"] == 2
        assert len(result["results"]["success"]) == 2
        
        # Verify excluded files are not in the results
        processed_paths = [r["file_path"] for r in result["results"]["success"]]
        for path in processed_paths:
            assert "exclude_me" not in path
    
    def test_create_openai_batch_file(self, temp_dir):
        """Test creating a batch file for OpenAI uploads."""
        processor = FileProcessor(output_dir=temp_dir)
        
        # Create sample chunk files
        chunks_dir = temp_dir / "chunks"
        
        # Create 3 chunk files with sample chunks
        for i in range(3):
            chunks = []
            for j in range(2):  # 2 chunks per file
                chunks.append({
                    "content": f"Sample content {i}-{j}",
                    "metadata": {
                        "file_path": f"file{i}.py",
                        "chunk_index": j,
                        "language": "python"
                    }
                })
            
            # Write chunks to file
            with open(chunks_dir / f"file{i}_chunks.json", 'w') as f:
                json.dump(chunks, f)
        
        # Create batch file
        batch_file = temp_dir / "batch.jsonl"
        result = processor.create_openai_batch_file(batch_file)
        
        # Verify batch file is created
        assert batch_file.exists()
        assert result["num_chunks"] == 6  # 3 files * 2 chunks
        
        # Verify batch file content
        chunks = []
        with open(batch_file, 'r') as f:
            for line in f:
                chunks.append(json.loads(line))
        
        assert len(chunks) == 6
        for chunk in chunks:
            assert "text" in chunk
            assert "metadata" in chunk
    
    def test_create_openai_batch_file_with_include_files(self, temp_dir):
        """Test creating a batch file with specific include files."""
        processor = FileProcessor(output_dir=temp_dir)
        
        # Create sample chunk files
        chunks_dir = temp_dir / "chunks"
        
        # Create 3 chunk files with sample chunks
        for i in range(3):
            chunks = []
            for j in range(2):  # 2 chunks per file
                chunks.append({
                    "content": f"Sample content {i}-{j}",
                    "metadata": {
                        "file_path": f"file{i}.py",
                        "chunk_index": j,
                        "language": "python"
                    }
                })
            
            # Write chunks to file
            with open(chunks_dir / f"file{i}_chunks.json", 'w') as f:
                json.dump(chunks, f)
        
        # Create batch file with only specific files
        batch_file = temp_dir / "batch.jsonl"
        include_files = [chunks_dir / "file0_chunks.json", chunks_dir / "file2_chunks.json"]
        
        result = processor.create_openai_batch_file(
            batch_file,
            include_files=include_files
        )
        
        # Verify batch file contains only chunks from included files
        assert result["num_chunks"] == 4  # 2 files * 2 chunks
        
        # Verify included files are in the result
        assert str(include_files[0]) in result["chunk_files"]
        assert str(include_files[1]) in result["chunk_files"]
        
        # Verify batch file content
        chunks = []
        with open(batch_file, 'r') as f:
            for line in f:
                chunks.append(json.loads(line))
        
        assert len(chunks) == 4 