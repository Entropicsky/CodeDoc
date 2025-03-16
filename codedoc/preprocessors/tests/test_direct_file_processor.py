"""
Tests for the DirectFileProcessor class.
"""

import os
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from codedoc.preprocessors.direct_file_processor import DirectFileProcessor
from codedoc.preprocessors.metadata_generator import MetadataGenerator
from codedoc.integrations.openai_vector import OpenAIVectorClient


@pytest.fixture
def setup_processor():
    # Create temp directory for output
    temp_dir = tempfile.mkdtemp()
    
    # Mock dependencies
    metadata_generator = MagicMock(spec=MetadataGenerator)
    metadata_generator.generate_metadata.return_value = {
        "filename": "test.py",
        "language": "python",
        "content_type": "code",
        "lines_of_code": 10,
    }
    
    vector_client = MagicMock(spec=OpenAIVectorClient)
    vector_client.upload_file.return_value = MagicMock(
        id="file-123",
        bytes=1000,
        created_at=1234567890,
    )
    
    vector_client.create_vector_store.return_value = MagicMock(
        id="vs-123",
        name="test-vector-store",
    )
    
    vector_client.check_vector_store_status.return_value = (True, "ready")
    
    # Create processor
    processor = DirectFileProcessor(
        output_dir=temp_dir,
        metadata_generator=metadata_generator,
        vector_client=vector_client,
    )
    
    # Create a test file
    test_file = os.path.join(temp_dir, "test.py")
    with open(test_file, "w") as f:
        f.write("def test_function():\n    return 'Hello, World!'")
    
    return {
        "processor": processor,
        "temp_dir": temp_dir,
        "test_file": test_file,
        "metadata_generator": metadata_generator,
        "vector_client": vector_client,
    }


def test_init(setup_processor):
    """Test the initialization of the DirectFileProcessor."""
    processor = setup_processor["processor"]
    temp_dir = setup_processor["temp_dir"]
    
    # Check output directories
    assert processor.output_dir == Path(temp_dir)
    assert processor.metadata_dir == Path(temp_dir) / "metadata"
    
    # Check dependencies
    assert processor.metadata_generator is not None
    assert processor.vector_client is not None
    
    # Check stats initialization
    assert processor.stats == {
        "files_processed": 0,
        "files_uploaded": 0,
        "total_content_size": 0,
        "failed_files": 0,
    }


def test_process_file(setup_processor):
    """Test processing a single file."""
    processor = setup_processor["processor"]
    test_file = setup_processor["test_file"]
    vector_client = setup_processor["vector_client"]
    
    # Process the file
    result = processor.process_file(
        file_path=test_file,
        file_id="test_id",
        purpose="assistants",
    )
    
    # Check the result
    assert result["file_id"] == "test_id"
    assert result["file_path"] == test_file
    assert result["status"] == "success"
    assert result["openai_file_id"] == "file-123"
    
    # Check that the metadata generator was called
    metadata_generator = setup_processor["metadata_generator"]
    metadata_generator.generate_metadata.assert_called_once()
    
    # Check that the vector client was called
    vector_client.upload_file.assert_called_once_with(
        file_path=test_file,
        purpose="assistants",
        prefix="[test_id] "
    )
    
    # Check that stats were updated
    assert processor.stats["files_processed"] == 1
    assert processor.stats["files_uploaded"] == 1
    assert processor.stats["total_content_size"] > 0


def test_process_file_with_custom_metadata(setup_processor):
    """Test processing a file with custom metadata."""
    processor = setup_processor["processor"]
    test_file = setup_processor["test_file"]
    
    custom_metadata = {
        "author": "Test Author",
        "version": "1.0.0",
    }
    
    # Process the file with custom metadata
    result = processor.process_file(
        file_path=test_file,
        file_id="test_id",
        purpose="assistants",
        custom_metadata=custom_metadata,
    )
    
    # Check that the metadata was updated with custom values
    metadata_file = processor.metadata_dir / "test_id_metadata.json"
    with open(metadata_file, "r") as f:
        metadata = json.load(f)
    
    assert metadata["author"] == "Test Author"
    assert metadata["version"] == "1.0.0"
    assert metadata["file_id"] == "test_id"


def test_create_vector_store(setup_processor):
    """Test creating a vector store."""
    processor = setup_processor["processor"]
    vector_client = setup_processor["vector_client"]
    
    # Create a vector store
    result = processor.create_vector_store(
        name="test-store",
        file_ids=["file-123", "file-456"],
        chunking_strategy={"type": "auto"},
    )
    
    # Check the result
    assert result["status"] == "success"
    assert result["vector_store_id"] == "vs-123"
    assert result["name"] == "test-store"
    assert result["file_count"] == 2
    
    # Check that the vector client was called correctly
    vector_client.create_vector_store.assert_called_once_with(
        name="test-store",
        file_ids=["file-123", "file-456"],
        chunking_strategy={"type": "auto"},
        metadata=None,
    )
    
    vector_client.check_vector_store_status.assert_called_once_with(
        vector_store_id="vs-123",
        max_checks=20,
        check_interval=3,
    )


def test_process_directory(setup_processor):
    """Test processing a directory of files."""
    processor = setup_processor["processor"]
    temp_dir = setup_processor["temp_dir"]
    vector_client = setup_processor["vector_client"]
    
    # Create a few more test files
    for i in range(3):
        test_file = os.path.join(temp_dir, f"test{i}.py")
        with open(test_file, "w") as f:
            f.write(f"def test_function_{i}():\n    return 'Hello, World {i}!'")
    
    # Process the directory
    result = processor.process_directory(
        input_dir=temp_dir,
        file_patterns=["*.py"],
        recursive=False,
        purpose="assistants",
    )
    
    # Check the results
    assert len(result["success"]) == 4  # 3 new files + 1 original test file
    assert len(result["failed"]) == 0
    assert len(result["skipped"]) == 0
    
    # Check that stats were updated
    assert processor.stats["files_processed"] == 4
    assert processor.stats["files_uploaded"] == 4
    
    # Check the summary
    summary = result["summary"]
    assert summary["total_files"] == 4
    assert summary["successful_files"] == 4
    assert summary["failed_files"] == 0
    assert len(summary["uploaded_file_ids"]) == 4


def test_process_file_failure(setup_processor):
    """Test handling a file processing failure."""
    processor = setup_processor["processor"]
    test_file = setup_processor["test_file"]
    vector_client = setup_processor["vector_client"]
    
    # Make the vector client return None to simulate upload failure
    vector_client.upload_file.return_value = None
    
    # Process the file
    result = processor.process_file(
        file_path=test_file,
        file_id="test_id",
        purpose="assistants",
    )
    
    # Check the result indicates failure
    assert result["status"] == "failed"
    assert result["reason"] == "upload failed"
    
    # Check that stats were updated correctly
    assert processor.stats["files_processed"] == 0
    assert processor.stats["files_uploaded"] == 0
    assert processor.stats["failed_files"] == 1


def teardown_module(module):
    """Clean up temporary files and directories after tests."""
    # This will be run after all tests in this module
    import shutil
    
    # Find all temp directories created by tempfile.mkdtemp()
    temp_root = tempfile.gettempdir()
    for item in os.listdir(temp_root):
        if item.startswith("tmp"):
            try:
                path = os.path.join(temp_root, item)
                if os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception:
                pass 