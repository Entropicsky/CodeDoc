"""
Tests for the main pipeline.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from codedoc.pipeline import Pipeline
from codedoc.preprocessors.chunker import ChunkingStrategy


class TestPipeline:
    """Tests for the main Pipeline class."""
    
    def test_init_default_values(self, temp_dir):
        """Test initialization with default values."""
        with patch('openai.OpenAI'):
            pipeline = Pipeline(output_dir=temp_dir)
            
            # Verify output directories are created
            assert (temp_dir / "enhanced-codebase").exists()
            assert (temp_dir / "supplementary-docs").exists()
            assert (temp_dir / "compiled").exists()
            assert (temp_dir / "metadata").exists()
            
            # Verify default components are created
            assert pipeline.llm_client is not None
            assert pipeline.file_enhancer is not None
            assert pipeline.content_generator is not None
            assert pipeline.code_analyzer is not None
            assert pipeline.file_processor is not None
            assert pipeline.vectorstore is not None
    
    def test_init_with_openai_client(self, temp_dir):
        """Test initialization with OpenAI client."""
        with patch('openai.OpenAI') as mock_openai, \
             patch('codedoc.llm.openai_client.OpenAIClient') as mock_openai_client:
            
            # Initialize pipeline with OpenAI
            pipeline = Pipeline(
                output_dir=temp_dir,
                llm_provider="openai",
                openai_api_key="test_key"
            )
            
            # Verify OpenAI client is created
            mock_openai_client.assert_called_once()
            assert mock_openai_client.call_args.kwargs["api_key"] == "test_key"
    
    def test_init_with_gemini_client(self, temp_dir):
        """Test initialization with Gemini client."""
        with patch('google.generativeai'), \
             patch('codedoc.llm.gemini_client.GeminiClient') as mock_gemini_client:
            
            # Initialize pipeline with Gemini
            pipeline = Pipeline(
                output_dir=temp_dir,
                llm_provider="gemini",
                gemini_api_key="test_gemini_key"
            )
            
            # Verify Gemini client is created
            mock_gemini_client.assert_called_once()
            assert mock_gemini_client.call_args.kwargs["api_key"] == "test_gemini_key"
    
    def test_enhance_codebase(self, temp_dir):
        """Test enhancing codebase."""
        with patch('openai.OpenAI'), \
             patch('codedoc.enhancers.file_enhancer.FileEnhancer') as mock_enhancer_class:
            
            # Set up mock file enhancer
            mock_enhancer = MagicMock()
            mock_enhancer.enhance_directory.return_value = {
                "enhanced_files": 5,
                "total_tokens_used": 1000
            }
            mock_enhancer_class.return_value = mock_enhancer
            
            # Initialize pipeline
            pipeline = Pipeline(output_dir=temp_dir)
            
            # Enhance codebase
            input_dir = temp_dir / "input"
            input_dir.mkdir()
            
            result = pipeline.enhance_codebase(
                input_dir=input_dir,
                file_patterns=["*.py", "*.js"],
                recursive=True
            )
            
            # Verify enhancer was called
            mock_enhancer.enhance_directory.assert_called_once()
            call_kwargs = mock_enhancer.enhance_directory.call_args.kwargs
            assert call_kwargs["input_dir"] == input_dir
            assert call_kwargs["file_patterns"] == ["*.py", "*.js"]
            assert call_kwargs["recursive"] is True
            
            # Verify result
            assert result["enhanced_files"] == 5
            assert result["total_tokens_used"] == 1000
    
    def test_analyze_codebase(self, temp_dir):
        """Test analyzing codebase."""
        with patch('openai.OpenAI'), \
             patch('codedoc.enhancers.code_analyzer.CodeAnalyzer') as mock_analyzer_class:
            
            # Set up mock code analyzer
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_directory.return_value = {
                "analyzed_files": 5,
                "total_tokens_used": 800,
                "findings": {}
            }
            mock_analyzer_class.return_value = mock_analyzer
            
            # Initialize pipeline
            pipeline = Pipeline(output_dir=temp_dir)
            
            # Analyze codebase
            input_dir = temp_dir / "input"
            input_dir.mkdir()
            
            result = pipeline.analyze_codebase(
                input_dir=input_dir,
                file_patterns=["*.py"],
                recursive=True
            )
            
            # Verify analyzer was called
            mock_analyzer.analyze_directory.assert_called_once()
            call_kwargs = mock_analyzer.analyze_directory.call_args.kwargs
            assert call_kwargs["input_dir"] == input_dir
            assert call_kwargs["file_patterns"] == ["*.py"]
            assert call_kwargs["recursive"] is True
            
            # Verify result
            assert result["analyzed_files"] == 5
            assert result["total_tokens_used"] == 800
            assert "findings" in result
    
    def test_generate_supplementary_content(self, temp_dir):
        """Test generating supplementary content."""
        with patch('openai.OpenAI'), \
             patch('codedoc.enhancers.content_generator.ContentGenerator') as mock_generator_class:
            
            # Set up mock content generator
            mock_generator = MagicMock()
            mock_generator.batch_generate.return_value = {
                "generated_files": [{"input_file": "file1.py", "outputs": []}],
                "failed_files": [],
                "stats": {
                    "total_files_processed": 1,
                    "total_content_pieces": 2
                }
            }
            mock_generator_class.return_value = mock_generator
            
            # Initialize pipeline
            pipeline = Pipeline(output_dir=temp_dir)
            
            # Generate supplementary content
            source_dir = temp_dir / "input"
            source_dir.mkdir()
            
            result = pipeline.generate_supplementary_content(
                source_dir=source_dir,
                project_name="Test Project",
                content_types=["faq", "tutorial"]
            )
            
            # Verify generator was called
            mock_generator.batch_generate.assert_called_once()
            
            # Verify result
            assert result["stats"]["total_files_processed"] == 1
            assert result["stats"]["total_content_pieces"] == 2
            assert len(result["generated_files"]) == 1
    
    def test_process_files_for_vectorization(self, temp_dir):
        """Test processing files for vectorization."""
        with patch('openai.OpenAI'), \
             patch('codedoc.preprocessors.file_processor.FileProcessor') as mock_processor_class:
            
            # Set up mock file processor
            mock_processor = MagicMock()
            
            # Set up mock return values for processor methods
            mock_processor.process_directory.return_value = {
                "summary": {
                    "files_processed": 5,
                    "chunks_created": 20
                },
                "results": {
                    "success": []
                }
            }
            
            mock_processor.create_openai_batch_file.return_value = {
                "batch_file": "batch.jsonl",
                "num_chunks": 20
            }
            
            mock_processor_class.return_value = mock_processor
            
            # Initialize pipeline
            pipeline = Pipeline(output_dir=temp_dir)
            
            # Set up directory structure
            (temp_dir / "enhanced-codebase").mkdir(exist_ok=True)
            (temp_dir / "original-codebase").mkdir(exist_ok=True)
            (temp_dir / "supplementary-docs").mkdir(exist_ok=True)
            
            # Process files for vectorization
            result = pipeline.process_files_for_vectorization(
                include_enhanced=True,
                include_original=True,
                include_supplementary=True
            )
            
            # Verify processor was called for each included directory
            assert mock_processor.process_directory.call_count == 3
            
            # Verify batch file was created
            mock_processor.create_openai_batch_file.assert_called_once()
            
            # Verify result
            assert "total_files_processed" in result
            assert "total_chunks_created" in result
            assert "batch_file" in result
    
    def test_upload_to_vector_store(self, temp_dir):
        """Test uploading to vector store."""
        with patch('openai.OpenAI'), \
             patch('codedoc.vectorstore.openai_vectorstore.OpenAIVectorStore') as mock_store_class:
            
            # Set up mock vector store
            mock_store = MagicMock()
            mock_store.upload_batch.return_value = {
                "total_lines": 20,
                "total_batches": 1,
                "files": [{"id": "file-123", "status": "processed"}]
            }
            mock_store_class.return_value = mock_store
            
            # Initialize pipeline
            pipeline = Pipeline(output_dir=temp_dir)
            
            # Create a batch file
            batch_file = temp_dir / "compiled" / "openai_batch.jsonl"
            batch_file.parent.mkdir(exist_ok=True)
            with open(batch_file, 'w') as f:
                for i in range(5):
                    f.write(f'{{"text": "Sample text {i}", "metadata": {{"index": {i}}}}}\n')
            
            # Upload to vector store
            result = pipeline.upload_to_vector_store(
                batch_file=batch_file,
                api_key="test_key"
            )
            
            # Verify vector store was called
            mock_store.upload_batch.assert_called_once_with(
                batch_file_path=batch_file,
                batch_size=100,
                progress_callback=None
            )
            
            # Verify result
            assert result["total_lines"] == 20
            assert result["total_batches"] == 1
            assert len(result["files"]) == 1
    
    def test_run_pipeline(self, temp_dir):
        """Test running the full pipeline."""
        with patch('openai.OpenAI'), \
             patch.object(Pipeline, 'enhance_codebase') as mock_enhance, \
             patch.object(Pipeline, 'analyze_codebase') as mock_analyze, \
             patch.object(Pipeline, 'generate_supplementary_content') as mock_generate, \
             patch.object(Pipeline, 'process_files_for_vectorization') as mock_process, \
             patch.object(Pipeline, 'upload_to_vector_store') as mock_upload:
            
            # Set up mock return values
            mock_enhance.return_value = {"enhanced_files": 5}
            mock_analyze.return_value = {"analyzed_files": 5}
            mock_generate.return_value = {"generated_files": 3}
            mock_process.return_value = {"total_files_processed": 10}
            mock_upload.return_value = {"files": 1}
            
            # Initialize pipeline
            pipeline = Pipeline(output_dir=temp_dir)
            
            # Create input directory
            input_dir = temp_dir / "input"
            input_dir.mkdir()
            
            # Run full pipeline
            result = pipeline.run_pipeline(
                input_dir=input_dir,
                project_name="Test Project"
            )
            
            # Verify all steps were called
            mock_enhance.assert_called_once()
            mock_analyze.assert_called_once()
            mock_generate.assert_called_once()
            mock_process.assert_called_once()
            mock_upload.assert_called_once()
            
            # Verify result contains all steps
            assert "enhance_result" in result
            assert "analyze_result" in result
            assert "supplementary_result" in result
            assert "process_result" in result
            assert "upload_result" in result
    
    def test_run_pipeline_with_skips(self, temp_dir):
        """Test running pipeline with skipped steps."""
        with patch('openai.OpenAI'), \
             patch.object(Pipeline, 'enhance_codebase') as mock_enhance, \
             patch.object(Pipeline, 'analyze_codebase') as mock_analyze, \
             patch.object(Pipeline, 'generate_supplementary_content') as mock_generate, \
             patch.object(Pipeline, 'process_files_for_vectorization') as mock_process, \
             patch.object(Pipeline, 'upload_to_vector_store') as mock_upload:
            
            # Initialize pipeline
            pipeline = Pipeline(output_dir=temp_dir)
            
            # Create input directory
            input_dir = temp_dir / "input"
            input_dir.mkdir()
            
            # Run pipeline with skips
            result = pipeline.run_pipeline(
                input_dir=input_dir,
                project_name="Test Project",
                skip_enhancement=True,
                skip_analysis=True,
                skip_supplementary=False,
                skip_processing=False,
                skip_upload=True
            )
            
            # Verify only non-skipped steps were called
            mock_enhance.assert_not_called()
            mock_analyze.assert_not_called()
            mock_generate.assert_called_once()
            mock_process.assert_called_once()
            mock_upload.assert_not_called()
            
            # Verify result contains only executed steps
            assert "enhance_result" not in result
            assert "analyze_result" not in result
            assert "supplementary_result" in result
            assert "process_result" in result
            assert "upload_result" not in result 