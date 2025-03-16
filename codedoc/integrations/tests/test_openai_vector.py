"""
Tests for the OpenAI Vector integration.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import tempfile
import openai

from codedoc.integrations.openai_vector import OpenAIVectorClient


class TestOpenAIVectorClient(unittest.TestCase):
    """Tests for OpenAI Vector client integration."""
    
    def setUp(self):
        """Set up test environment."""
        # Set up mock environment variables
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        os.environ["OPENAI_ORG_ID"] = "test-org-id"
        
        # Create test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = os.path.join(self.temp_dir.name, "test_file.txt")
        with open(self.test_file_path, "w") as f:
            f.write("Test content")
        
        # Create mock OpenAI client
        self.mock_client = MagicMock()
        
        # Set up mock structures
        self.mock_files_list = MagicMock()
        self.mock_files_create = MagicMock()
        self.mock_files_delete = MagicMock()
        
        self.mock_beta = MagicMock()
        self.mock_vector_stores = MagicMock()
        self.mock_vector_stores_create = MagicMock()
        self.mock_vector_stores_retrieve = MagicMock()
        self.mock_vector_stores_search = MagicMock()
        
        # Connect mock structures
        self.mock_client.files = MagicMock()
        self.mock_client.files.list = self.mock_files_list
        self.mock_client.files.create = self.mock_files_create
        self.mock_client.files.delete = self.mock_files_delete
        
        self.mock_client.beta = self.mock_beta
        self.mock_beta.vector_stores = self.mock_vector_stores
        self.mock_vector_stores.create = self.mock_vector_stores_create
        self.mock_vector_stores.retrieve = self.mock_vector_stores_retrieve
        self.mock_vector_stores.search = self.mock_vector_stores_search
        
        # Create client using our mock
        self.client = OpenAIVectorClient(client_class=lambda **kwargs: self.mock_client)
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("OPENAI_ORG_ID", None)
    
    def test_init(self):
        """Test client initialization."""
        # Test with environment variables
        client = OpenAIVectorClient(client_class=lambda **kwargs: self.mock_client)
        
        # Test with explicit parameters
        client = OpenAIVectorClient(
            api_key="custom-api-key",
            organization="custom-org-id",
            timeout=60,
            client_class=lambda **kwargs: self.mock_client
        )
    
    def test_upload_file(self):
        """Test uploading a file."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.id = "file-123"
        self.mock_files_create.return_value = mock_response
        
        # Test valid upload
        result = self.client.upload_file(self.test_file_path, purpose="assistants")
        self.assertEqual(result.id, "file-123")
        self.mock_files_create.assert_called_once()
        
        # Reset mock
        self.mock_files_create.reset_mock()
        
        # Test invalid purpose
        with self.assertRaises(ValueError):
            self.client.upload_file(self.test_file_path, purpose="invalid")
        
        # Test API error
        self.mock_files_create.side_effect = Exception("API Error")
        with self.assertRaises(Exception):
            self.client.upload_file(self.test_file_path, purpose="assistants")
    
    def test_upload_directory(self):
        """Test uploading a directory."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.id = "file-123"
        mock_response.bytes = 100
        mock_response.created_at = 12345
        self.mock_files_create.return_value = mock_response
        
        # Create additional test file
        second_file_path = os.path.join(self.temp_dir.name, "second_file.txt")
        with open(second_file_path, "w") as f:
            f.write("More test content")
        
        # Count files in directory for accurate assertion
        import glob
        files_count = len(glob.glob(os.path.join(self.temp_dir.name, "*.txt")))
        
        # Test directory upload
        results = self.client.upload_directory(self.temp_dir.name, purpose="assistants")
        
        # Check the structure of the results
        self.assertIn("stats", results)
        self.assertIn("uploaded_files", results)
        self.assertEqual(results["stats"]["files_uploaded"], files_count)
        self.assertEqual(len(results["uploaded_files"]), files_count)
        self.assertEqual(self.mock_files_create.call_count, files_count)
        
        # Test with file pattern
        self.mock_files_create.reset_mock()
        results = self.client.upload_directory(
            self.temp_dir.name, 
            purpose="assistants",
            file_patterns=["second*"]
        )
        self.assertEqual(results["stats"]["files_uploaded"], 1)
        self.assertEqual(len(results["uploaded_files"]), 1)
        self.assertEqual(self.mock_files_create.call_count, 1)
    
    def test_list_files(self):
        """Test listing files."""
        # Set up mock response
        mock_data = [
            {"id": "file-1", "purpose": "assistants"},
            {"id": "file-2", "purpose": "fine-tune"}
        ]
        mock_response = MagicMock()
        mock_response.data = mock_data
        self.mock_files_list.return_value = mock_response
        
        # Test listing all files
        result = self.client.list_files()
        self.assertEqual(len(result), 2)
        self.mock_files_list.assert_called_once_with(limit=100, purpose=None)
        
        # Test listing files with purpose
        self.mock_files_list.reset_mock()
        result = self.client.list_files(purpose="assistants")
        self.assertEqual(len(result), 2)  # Mocked result doesn't filter
        self.mock_files_list.assert_called_once_with(limit=100, purpose="assistants")
    
    def test_delete_file(self):
        """Test deleting a file."""
        # Set up mock response for successful deletion
        mock_response = MagicMock()
        mock_response.deleted = True
        self.mock_files_delete.return_value = mock_response
        
        # Test successful deletion
        result = self.client.delete_file("file-123")
        self.assertTrue(result)
        self.mock_files_delete.assert_called_once_with("file-123")
        
        # Reset mock for API error test
        self.mock_files_delete.reset_mock()
        
        # Set up API error without raising exception in the test
        # This simulates the client catching the exception
        self.mock_files_delete.side_effect = openai.OpenAIError("API Error")
        
        # The client should handle the exception and return False
        result = self.client.delete_file("file-123")
        self.assertFalse(result)
    
    def test_create_vector_store(self):
        """Test creating a vector store."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.id = "vs-123"
        self.mock_vector_stores_create.return_value = mock_response
        
        # Test with file ids
        result = self.client.create_vector_store(
            "test-store",
            file_ids=["file-1", "file-2"]
        )
        self.assertEqual(result.id, "vs-123")
        self.mock_vector_stores_create.assert_called_once()
        
        # Test with file ids and params
        self.mock_vector_stores_create.reset_mock()
        result = self.client.create_vector_store(
            "test-store",
            file_ids=["file-1", "file-2"],
            chunking_strategy={"type": "semantic"}
        )
        self.assertEqual(result.id, "vs-123")
        self.mock_vector_stores_create.assert_called_once()
        
        # Test API error
        self.mock_vector_stores_create.side_effect = Exception("API Error")
        with self.assertRaises(Exception):
            self.client.create_vector_store(
                "test-store",
                file_ids=["file-1", "file-2"]
            )
    
    @patch('time.sleep', return_value=None)  # Patch sleep to speed up test
    def test_check_vector_store_status(self, mock_sleep):
        """Test checking vector store status."""
        # Set up mock response for completed store
        mock_completed_response = MagicMock()
        mock_completed_response.file_counts = {
            "in_progress": 0,
            "completed": 2,
            "failed": 0,
            "cancelled": 0,
            "total": 2
        }
        self.mock_vector_stores_retrieve.return_value = mock_completed_response
        
        # Test completed vector store
        is_ready, status = self.client.check_vector_store_status("vs-123", max_checks=1)
        self.assertTrue(is_ready)
        self.assertEqual(status, mock_completed_response.file_counts)
        
        # Reset mock for in-progress test
        self.mock_vector_stores_retrieve.reset_mock()
        
        # Set up mock response for in-progress store
        mock_in_progress_response = MagicMock()
        mock_in_progress_response.file_counts = {
            "in_progress": 1,
            "completed": 1,
            "failed": 0,
            "cancelled": 0,
            "total": 2
        }
        self.mock_vector_stores_retrieve.return_value = mock_in_progress_response
        
        # For in-progress store, the method will return False, None because max_checks=1
        is_ready, status = self.client.check_vector_store_status("vs-123", max_checks=1)
        self.assertFalse(is_ready)
        # With max_checks=1, we don't get a status back for in-progress stores
        
        # Reset mock for API error test
        self.mock_vector_stores_retrieve.reset_mock()
        
        # Set up API error that will be caught by the client
        self.mock_vector_stores_retrieve.side_effect = openai.OpenAIError("API Error")
        
        # The client should handle the exception and return (False, None)
        is_ready, status = self.client.check_vector_store_status("vs-123", max_checks=1)
        self.assertFalse(is_ready)
        self.assertIsNone(status)
    
    def test_search_vector_store(self):
        """Test searching vector store."""
        # Set up mock response for successful search
        mock_item = MagicMock()
        mock_item.file_id = "file-1"
        mock_item.filename = "test.txt"
        mock_item.score = 0.95
        mock_content_item = MagicMock()
        mock_content_item.text = "Test result"
        mock_item.content = [mock_content_item]
        mock_response = MagicMock()
        mock_response.data = [mock_item]
        mock_response.has_more = False
        self.mock_vector_stores_search.return_value = mock_response
        
        # Test basic search
        result = self.client.search_vector_store("vs-123", "test query")
        self.assertEqual(result["query"], "test query")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["file_id"], "file-1")
        
        # Verify the parameters used in the search call
        call_kwargs = self.mock_vector_stores_search.call_args[1]
        self.assertEqual(call_kwargs["vector_store_id"], "vs-123")
        
        # The implementation uses max_num_results internally to match OpenAI's API parameter
        # even though the method parameter is named max_results
        expected_search_args = {"query": "test query", "max_num_results": 10}
        for key, value in expected_search_args.items():
            self.assertEqual(call_kwargs.get(key), value)
        
        # Test search with filters
        self.mock_vector_stores_search.reset_mock()
        self.mock_vector_stores_search.return_value = mock_response
        result = self.client.search_vector_store(
            "vs-123",
            "test query",
            filters={"type": "document"}
        )
        self.assertEqual(len(result["results"]), 1)
        
        # Verify filters were included in the search call
        call_kwargs = self.mock_vector_stores_search.call_args[1]
        self.assertEqual(call_kwargs.get("filters"), {"type": "document"})
        
        # Reset mock for API error test
        self.mock_vector_stores_search.reset_mock()
        
        # Set up API error that will be caught by the client
        self.mock_vector_stores_search.side_effect = openai.OpenAIError("API Error")
        
        # The client should handle the exception and return a result with error info
        result = self.client.search_vector_store("vs-123", "test query")
        self.assertEqual(result["query"], "test query")
        self.assertEqual(len(result["results"]), 0)
        self.assertEqual(result["error"], "API Error")


if __name__ == "__main__":
    unittest.main() 