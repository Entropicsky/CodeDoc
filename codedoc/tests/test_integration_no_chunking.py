"""
Integration tests for the pipeline without custom chunking.
"""

import os
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from codedoc.pipeline import Pipeline
from codedoc.integrations.openai_vector import OpenAIVectorClient


class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for the pipeline with direct OpenAI upload."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        
        self.input_dir = self.base_dir / "input"
        self.input_dir.mkdir()
        
        self.output_dir = self.base_dir / "output"
        
        # Create some sample files for testing
        self.create_sample_files()
        
        # Mock OpenAI API responses
        self.setup_openai_mocks()
        
        # Initialize the pipeline with mocks
        self.pipeline = self.create_pipeline()
    
    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()
    
    def create_sample_files(self):
        """Create sample files for testing."""
        # Create a Python file
        py_dir = self.input_dir / "src"
        py_dir.mkdir(parents=True)
        
        with open(py_dir / "main.py", "w") as f:
            f.write("""
def main():
    print("Hello, world!")

if __name__ == "__main__":
    main()
""")
        
        # Create a Markdown file
        with open(self.input_dir / "README.md", "w") as f:
            f.write("""
# Test Project

This is a test project for integration testing.
""")
    
    def setup_openai_mocks(self):
        """Set up mocks for OpenAI API calls."""
        # Create patch for OpenAI client
        self.openai_client_patch = patch("codedoc.integrations.openai_vector.OpenAI")
        self.mock_openai = self.openai_client_patch.start()
        
        # Mock file upload response
        self.mock_file_response = MagicMock()
        self.mock_file_response.id = "file-123"
        self.mock_file_response.bytes = 1024
        self.mock_file_response.created_at = 1617976800
        
        # Mock files.create method
        self.mock_files = MagicMock()
        self.mock_files.create.return_value = self.mock_file_response
        
        # Mock vector store response
        self.mock_vs_response = MagicMock()
        self.mock_vs_response.id = "vs-123"
        
        # Mock vector_stores.create method
        self.mock_vector_stores = MagicMock()
        self.mock_vector_stores.create.return_value = self.mock_vs_response
        self.mock_vector_stores.retrieve.return_value = MagicMock(
            file_counts={"in_progress": 0, "completed": 2, "failed": 0, "total": 2}
        )
        
        # Mock beta property
        self.mock_beta = MagicMock()
        self.mock_beta.vector_stores = self.mock_vector_stores
        
        # Set up the OpenAI client instance
        self.mock_openai_instance = MagicMock()
        self.mock_openai_instance.files = self.mock_files
        self.mock_openai_instance.beta = self.mock_beta
        
        # Make the OpenAI constructor return our mock instance
        self.mock_openai.return_value = self.mock_openai_instance
        
        # Create a patch for DirectFileProcessor to monitor method calls
        self.processor_patch = patch("codedoc.preprocessors.direct_file_processor.DirectFileProcessor.process_file")
        self.mock_process_file = self.processor_patch.start()
        self.mock_process_file.return_value = {
            "status": "success",
            "file_id": "test_file",
            "openai_file_id": "file-123",
            "file_path": "test/file.py",
            "processing_time": 0.5,
            "size_bytes": 1024,
            "created_at": 1617976800
        }
    
    def create_pipeline(self):
        """Create a pipeline instance for testing."""
        return Pipeline(
            output_dir=self.output_dir,
            llm_provider="openai",
            openai_api_key="test-key",
            model="gpt-3.5-turbo",
            temperature=0.2
        )
    
    def test_pipeline_no_chunking(self):
        """Test the complete pipeline without chunking."""
        # Run a simplified pipeline that skips enhancement and analysis
        result = self.pipeline.run_pipeline(
            input_dir=self.input_dir,
            project_name="TestProject",
            skip_enhancement=True,
            skip_analysis=True,
            skip_supplementary=True,
            skip_processing=False,
            skip_upload=False,
            file_patterns=["*.py", "*.md"]
        )
        
        # Assert pipeline completed
        self.assertIsNotNone(result.get("processing"))
        self.assertIsNotNone(result.get("upload"))
        
        # Verify OpenAI interactions
        # Check that vector store was created without chunking parameters
        create_kwargs = self.mock_vector_stores.create.call_args.kwargs
        self.assertIn("chunking_strategy", create_kwargs)
        self.assertEqual(create_kwargs["chunking_strategy"], {"type": "auto"})
        
        # Check that the processor was called for the files
        self.assertTrue(self.mock_process_file.called)
    
    def test_pipeline_with_custom_chunking_strategy(self):
        """Test pipeline with a custom OpenAI chunking strategy."""
        # Create a vector store with a specific chunking strategy
        result = self.pipeline.upload_to_vector_store(
            file_ids=["file-123", "file-456"],
            name="TestProject",
            chunking_strategy={"type": "fixed_size", "size": 300, "overlap": 20},
            metadata={"project": "TestProject"}
        )
        
        # Check that the chunking strategy was passed to the API
        create_kwargs = self.mock_vector_stores.create.call_args.kwargs
        self.assertIn("chunking_strategy", create_kwargs)
        self.assertEqual(create_kwargs["chunking_strategy"]["type"], "fixed_size")
        self.assertEqual(create_kwargs["chunking_strategy"]["size"], 300)
        self.assertEqual(create_kwargs["chunking_strategy"]["overlap"], 20)
    
    def tearDown(self):
        """Clean up after each test."""
        # Stop all patches
        self.openai_client_patch.stop()
        self.processor_patch.stop()
        
        # Remove temporary directory
        self.temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main() 