"""
Tests for the OpenAI vector store client.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from codedoc.vectorstore.openai_vectorstore import OpenAIVectorStore


class TestOpenAIVectorStore:
    """Tests for the OpenAIVectorStore class."""
    
    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        with patch('openai.OpenAI') as mock_openai:
            store = OpenAIVectorStore(api_key="test_api_key")
            
            # Verify OpenAI client was initialized with the API key
            mock_openai.assert_called_once_with(api_key="test_api_key")
    
    def test_init_with_env_var(self):
        """Test initialization with API key from environment variable."""
        with patch('openai.OpenAI') as mock_openai, \
             patch.dict(os.environ, {"OPENAI_API_KEY": "env_api_key"}):
            
            store = OpenAIVectorStore()
            
            # Verify OpenAI client was initialized with the environment API key
            mock_openai.assert_called_once_with(api_key="env_api_key")
    
    def test_init_with_organization(self):
        """Test initialization with organization ID."""
        with patch('openai.OpenAI') as mock_openai:
            store = OpenAIVectorStore(
                api_key="test_api_key",
                organization="test-org"
            )
            
            # Verify OpenAI client was initialized with organization
            mock_openai.assert_called_once_with(api_key="test_api_key", organization="test-org")
    
    def test_list_files(self):
        """Test listing files in the vector store."""
        with patch('openai.OpenAI') as mock_openai:
            # Set up mock response
            mock_files_response = [
                {"id": "file-1", "purpose": "assistants", "status": "processed"},
                {"id": "file-2", "purpose": "assistants", "status": "processing"}
            ]
            
            # Set up the mock client
            mock_client = MagicMock()
            mock_client.files.list.return_value.data = mock_files_response
            mock_openai.return_value = mock_client
            
            # Initialize the store and call the method
            store = OpenAIVectorStore(api_key="test_api_key")
            files = store.list_files()
            
            # Verify the response
            assert len(files) == 2
            assert files[0]["id"] == "file-1"
            assert files[1]["id"] == "file-2"
            
            # Verify the API call
            mock_client.files.list.assert_called_once()
    
    def test_upload_file(self, temp_dir):
        """Test uploading a file to the vector store."""
        with patch('openai.OpenAI') as mock_openai:
            # Create a sample file
            file_path = temp_dir / "test.jsonl"
            with open(file_path, 'w') as f:
                f.write('{"text": "Sample text", "metadata": {"key": "value"}}\n')
            
            # Set up mock response
            mock_file_response = {"id": "file-123", "purpose": "assistants", "status": "uploaded"}
            
            # Set up the mock client
            mock_client = MagicMock()
            mock_client.files.create.return_value = mock_file_response
            mock_openai.return_value = mock_client
            
            # Initialize the store and call the method
            store = OpenAIVectorStore(api_key="test_api_key")
            result = store.upload_file(file_path)
            
            # Verify the response
            assert result["id"] == "file-123"
            assert result["status"] == "uploaded"
            
            # Verify the API call
            mock_client.files.create.assert_called_once()
            call_kwargs = mock_client.files.create.call_args.kwargs
            assert call_kwargs["purpose"] == "assistants"
            # Can't easily check the file parameter as it's a file-like object
    
    def test_upload_batch(self, temp_dir):
        """Test uploading a batch file to the vector store."""
        with patch('openai.OpenAI') as mock_openai, \
             patch('codedoc.vectorstore.openai_vectorstore.tqdm') as mock_tqdm:
            
            # Create a sample batch file with multiple lines
            batch_file = temp_dir / "batch.jsonl"
            with open(batch_file, 'w') as f:
                for i in range(5):
                    f.write(f'{{"text": "Sample text {i}", "metadata": {{"index": {i}}}}}\n')
            
            # Set up mock response for file upload
            mock_file_response = {"id": "file-batch", "purpose": "assistants", "status": "uploaded"}
            
            # Set up the mock client
            mock_client = MagicMock()
            mock_client.files.create.return_value = mock_file_response
            mock_openai.return_value = mock_client
            
            # Set up mock progress bar
            mock_progress_bar = MagicMock()
            mock_tqdm.return_value = mock_progress_bar
            
            # Initialize the store and call the method
            store = OpenAIVectorStore(api_key="test_api_key")
            result = store.upload_batch(batch_file, batch_size=2)  # Batch size of 2 with 5 lines = 3 batches
            
            # Verify the response
            assert len(result["files"]) == 3  # Should create 3 files (2+2+1 lines)
            assert result["total_batches"] == 3
            assert result["total_lines"] == 5
            
            # Verify the API call was made 3 times
            assert mock_client.files.create.call_count == 3
            
            # Verify progress bar was updated
            assert mock_progress_bar.update.call_count >= 3
    
    def test_delete_file(self):
        """Test deleting a file from the vector store."""
        with patch('openai.OpenAI') as mock_openai:
            # Set up the mock client
            mock_client = MagicMock()
            mock_client.files.delete.return_value = {"id": "file-123", "deleted": True}
            mock_openai.return_value = mock_client
            
            # Initialize the store and call the method
            store = OpenAIVectorStore(api_key="test_api_key")
            result = store.delete_file("file-123")
            
            # Verify the response
            assert result is True
            
            # Verify the API call
            mock_client.files.delete.assert_called_once_with("file-123")
    
    def test_get_file_info(self):
        """Test getting file information from the vector store."""
        with patch('openai.OpenAI') as mock_openai:
            # Set up mock response
            mock_file_response = {
                "id": "file-123", 
                "purpose": "assistants", 
                "status": "processed",
                "filename": "test.jsonl",
                "created_at": 1641234567
            }
            
            # Set up the mock client
            mock_client = MagicMock()
            mock_client.files.retrieve.return_value = mock_file_response
            mock_openai.return_value = mock_client
            
            # Initialize the store and call the method
            store = OpenAIVectorStore(api_key="test_api_key")
            result = store.get_file_info("file-123")
            
            # Verify the response
            assert result["id"] == "file-123"
            assert result["status"] == "processed"
            assert result["filename"] == "test.jsonl"
            
            # Verify the API call
            mock_client.files.retrieve.assert_called_once_with("file-123")
    
    def test_wait_for_file_processing(self):
        """Test waiting for file processing completion."""
        with patch('openai.OpenAI') as mock_openai, \
             patch('time.sleep') as mock_sleep:
            
            # Set up mock responses for sequential calls
            mock_responses = [
                {"id": "file-123", "status": "processing"},
                {"id": "file-123", "status": "processing"},
                {"id": "file-123", "status": "processed"}
            ]
            
            # Set up the mock client to return different responses on each call
            mock_client = MagicMock()
            mock_client.files.retrieve.side_effect = mock_responses
            mock_openai.return_value = mock_client
            
            # Initialize the store and call the method
            store = OpenAIVectorStore(api_key="test_api_key")
            result = store.wait_for_file_processing("file-123", polling_interval=1)
            
            # Verify the response
            assert result["id"] == "file-123"
            assert result["status"] == "processed"
            
            # Verify the API calls
            assert mock_client.files.retrieve.call_count == 3
            mock_sleep.assert_has_calls([call(1), call(1)])
    
    def test_search_vector_store(self):
        """Test searching the vector store."""
        with patch('openai.OpenAI') as mock_openai:
            # Set up mock response
            mock_search_response = {
                "object": "list",
                "data": [
                    {
                        "object": "assistants_search_result",
                        "score": 0.95,
                        "document": {
                            "text": "Sample text 1",
                            "metadata": {"file_path": "file1.py", "language": "python"}
                        }
                    },
                    {
                        "object": "assistants_search_result",
                        "score": 0.85,
                        "document": {
                            "text": "Sample text 2",
                            "metadata": {"file_path": "file2.py", "language": "python"}
                        }
                    }
                ]
            }
            
            # Set up the mock client
            mock_client = MagicMock()
            mock_client.embeddings.create.return_value.data = [{"embedding": [0.1, 0.2, 0.3]}]
            mock_client.vector_stores.file_search.return_value = mock_search_response
            mock_openai.return_value = mock_client
            
            # Initialize the store and call the method
            store = OpenAIVectorStore(api_key="test_api_key")
            results = store.search_vector_store(
                query="test query",
                file_ids=["file-123"],
                max_results=2,
                metadata_filter={"language": "python"}
            )
            
            # Verify the response
            assert len(results) == 2
            assert results[0]["content"] == "Sample text 1"
            assert results[0]["score"] == 0.95
            assert results[0]["metadata"]["file_path"] == "file1.py"
            
            # Verify the API calls
            mock_client.embeddings.create.assert_called_once()
            mock_client.vector_stores.file_search.assert_called_once()
            
            # Verify search parameters
            call_kwargs = mock_client.vector_stores.file_search.call_args.kwargs
            assert call_kwargs["file_ids"] == ["file-123"]
            assert call_kwargs["max_results"] == 2
            assert "metadata_filter" in call_kwargs 
    
    def test_search_with_no_results(self):
        """Test searching with no results returned."""
        with patch('openai.OpenAI') as mock_openai:
            # Set up mock response with empty data
            mock_search_response = {
                "object": "list",
                "data": []
            }
            
            # Set up the mock client
            mock_client = MagicMock()
            mock_client.embeddings.create.return_value.data = [{"embedding": [0.1, 0.2, 0.3]}]
            mock_client.vector_stores.file_search.return_value = mock_search_response
            mock_openai.return_value = mock_client
            
            # Initialize the store and call the method
            store = OpenAIVectorStore(api_key="test_api_key")
            results = store.search_vector_store(query="test query", file_ids=["file-123"])
            
            # Verify empty results
            assert len(results) == 0 