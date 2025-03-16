"""
Tests for processing the rally-here codebase.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json

from codedoc.pipeline import Pipeline
from codedoc.llm.openai_client import OpenAIClient
from codedoc.enhancers.code_analyzer import CodeAnalyzer
from codedoc.enhancers.file_enhancer import FileEnhancer


class TestRallyHereProcessing:
    """Integration tests for processing the rally-here codebase."""

    def test_enhancement_and_analysis(self, tmp_path):
        """Test file enhancement and code analysis with mocked dependencies."""
        # Create a test file in a temp directory
        test_file_dir = tmp_path / "test_input"
        test_file_dir.mkdir(parents=True)
        test_file = test_file_dir / "test_file.py"
        test_file.write_text("def test_function():\n    pass")
        
        # Create mock responses
        mock_llm_response = MagicMock()
        mock_llm_response.content = "Enhanced code with documentation."
        mock_llm_response.usage = {"total_tokens": 100}
        
        # Mock file enhancer results
        mock_enhanced_result = {
            "stats": {
                "files_processed": 1,
                "files_enhanced": 1,
                "total_tokens": 100
            },
            "enhanced_files": ["test_file.py"],
            "failed_files": []
        }
        
        # Mock code analyzer results
        mock_analyzer_result = {
            "stats": {
                "files_analyzed": 1,
                "patterns_identified": 2,
                "complexity_analyses": 1,
                "total_tokens_used": 200
            },
            "analysis_results": [
                {
                    "file": str(test_file),
                    "results": {
                        "patterns": "test_patterns.md",
                        "complexity": "test_complexity.md"
                    }
                }
            ]
        }
        
        # Set up our mocks
        with patch.object(OpenAIClient, 'generate_with_system_prompt', return_value=mock_llm_response), \
             patch.object(FileEnhancer, 'enhance_directory', return_value=mock_enhanced_result), \
             patch.object(CodeAnalyzer, 'analyze_directory', return_value=mock_analyzer_result):
            
            # Create the pipeline
            pipeline = Pipeline(
                output_dir=tmp_path / "output",
                openai_api_key="test_key"
            )
            
            # Test enhance_codebase directly
            enhance_result = pipeline.enhance_codebase(
                input_dir=test_file_dir,
                max_files=1
            )
            
            # Verify enhancement results
            assert enhance_result["enhanced_files"] == 1
            assert enhance_result["total_files"] == 1
            assert enhance_result["failed_files"] == 0
            
            # Test analyze_codebase directly
            analyze_result = pipeline.analyze_codebase(
                input_dir=test_file_dir,
                max_files=1
            )
            
            # Verify analysis results
            assert analyze_result["stats"]["files_analyzed"] == 1
            assert analyze_result["stats"]["patterns_identified"] == 2
            assert analyze_result["stats"]["complexity_analyses"] == 1
            
            # Verify output directories were created
            output_dir = tmp_path / "output"
            assert (output_dir / "enhanced-codebase").exists()
            assert (output_dir / "metadata").exists()
            
            # Log detailed results for debugging
            print(f"Enhancement result: {json.dumps(enhance_result, default=str, indent=2)}")
            print(f"Analysis result: {json.dumps(analyze_result, default=str, indent=2)}")
            
            # Verify that our mocks were called
            assert FileEnhancer.enhance_directory.called
            assert CodeAnalyzer.analyze_directory.called 