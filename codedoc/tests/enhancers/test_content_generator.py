"""
Tests for the content generator.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from codedoc.enhancers.content_generator import ContentGenerator
from codedoc.llm.base import LLMResponse


class TestContentGenerator:
    """Tests for the ContentGenerator class."""
    
    def test_init(self, temp_dir, mock_llm_client):
        """Test initialization with default values."""
        generator = ContentGenerator(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Verify output directory is created
        assert temp_dir.exists()
        
        # Verify default values
        assert generator.llm_client is mock_llm_client
        assert generator.model is None
        assert generator.temperature == 0.5
        assert generator.prompt_manager is not None
        
        # Verify stats are initialized
        assert generator.stats["faqs_generated"] == 0
        assert generator.stats["tutorials_generated"] == 0
        assert generator.stats["other_content_generated"] == 0
        assert generator.stats["total_tokens_used"] == 0
    
    def test_init_custom_values(self, temp_dir, mock_llm_client):
        """Test initialization with custom values."""
        mock_prompt_manager = MagicMock()
        
        generator = ContentGenerator(
            llm_client=mock_llm_client,
            output_dir=temp_dir,
            prompt_manager=mock_prompt_manager,
            model="gpt-4",
            temperature=0.7
        )
        
        # Verify custom values are used
        assert generator.prompt_manager is mock_prompt_manager
        assert generator.model == "gpt-4"
        assert generator.temperature == 0.7
    
    def test_generate_faq_string_content(self, temp_dir, mock_llm_client):
        """Test generating FAQ from string content."""
        # Set up mock LLM response
        mock_llm_client.generate_with_system_prompt.return_value = LLMResponse(
            content="Q: What is this?\nA: This is a test.",
            usage={"total_tokens": 50}
        )
        
        # Set up content generator
        generator = ContentGenerator(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Generate FAQ from string content
        content = "Sample content for FAQ generation."
        output_path = generator.generate_faq(content, output_filename="test_faq.md")
        
        # Verify output file is created
        assert output_path is not None
        output_file = Path(output_path)
        assert output_file.exists()
        
        # Verify file content
        with open(output_file, 'r') as f:
            content = f.read()
            assert "# Frequently Asked Questions" in content
            assert "Q: What is this?" in content
            assert "A: This is a test." in content
        
        # Verify stats are updated
        assert generator.stats["faqs_generated"] == 1
        assert generator.stats["total_tokens_used"] == 50
        
        # Verify LLM call
        mock_llm_client.generate_with_system_prompt.assert_called_once()
        system_prompt = mock_llm_client.generate_with_system_prompt.call_args.kwargs["system_prompt"]
        user_prompt = mock_llm_client.generate_with_system_prompt.call_args.kwargs["user_prompt"]
        assert "FAQ" in system_prompt
        assert "Sample content" in user_prompt
    
    def test_generate_faq_file_content(self, temp_dir, mock_llm_client, sample_py_file):
        """Test generating FAQ from file content."""
        # Set up mock LLM response
        mock_llm_client.generate_with_system_prompt.return_value = LLMResponse(
            content="Q: What does the sample class do?\nA: It stores and retrieves values.",
            usage={"total_tokens": 60}
        )
        
        # Set up content generator
        generator = ContentGenerator(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Generate FAQ from file
        output_path = generator.generate_faq(sample_py_file)
        
        # Verify output file is created with expected name pattern
        assert output_path is not None
        output_file = Path(output_path)
        assert output_file.exists()
        assert output_file.name == "sample_faq.md"  # Based on input filename
        
        # Verify LLM call includes file content
        user_prompt = mock_llm_client.generate_with_system_prompt.call_args.kwargs["user_prompt"]
        assert "SampleClass" in user_prompt  # Contains code from the file
        
        # Verify stats
        assert generator.stats["faqs_generated"] == 1
        assert generator.stats["total_tokens_used"] == 60
    
    def test_generate_tutorial(self, temp_dir, mock_llm_client, sample_py_file):
        """Test generating a tutorial."""
        # Set up mock LLM response
        mock_llm_client.generate_with_system_prompt.return_value = LLMResponse(
            content="# Introduction\nThis tutorial explains how to use the sample class.",
            usage={"total_tokens": 70}
        )
        
        # Set up content generator
        generator = ContentGenerator(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Generate tutorial
        tutorial_topic = "Using SampleClass"
        output_path = generator.generate_tutorial(
            content=sample_py_file,
            tutorial_topic=tutorial_topic,
            audience_level="beginner"
        )
        
        # Verify output file is created
        assert output_path is not None
        output_file = Path(output_path)
        assert output_file.exists()
        assert "using_sampleclass_tutorial.md" in output_path
        
        # Verify file content
        with open(output_file, 'r') as f:
            content = f.read()
            assert f"# {tutorial_topic}" in content
            assert "# Introduction" in content
            assert "This tutorial explains" in content
        
        # Verify LLM call parameters
        call_kwargs = mock_llm_client.generate_with_system_prompt.call_args.kwargs
        assert "beginner" in call_kwargs["user_prompt"]
        assert tutorial_topic in call_kwargs["user_prompt"]
        
        # Verify stats
        assert generator.stats["tutorials_generated"] == 1
        assert generator.stats["total_tokens_used"] == 70
    
    def test_generate_custom_content(self, temp_dir, mock_llm_client, sample_py_file):
        """Test generating custom content."""
        # Set up mock LLM response
        mock_llm_client.generate_with_system_prompt.return_value = LLMResponse(
            content="This is custom content based on the sample file.",
            usage={"total_tokens": 40}
        )
        
        # Set up content generator
        generator = ContentGenerator(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Define custom prompts
        system_prompt = "You are a technical writer creating code documentation."
        user_prompt = "Please summarize the following code:\n\n{content}"
        
        # Generate custom content
        output_path = generator.generate_custom_content(
            content=sample_py_file,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_filename="custom_doc.md"
        )
        
        # Verify output file is created
        assert output_path is not None
        output_file = Path(output_path)
        assert output_file.exists()
        assert output_file.name == "custom_doc.md"
        
        # Verify file content
        with open(output_file, 'r') as f:
            content = f.read()
            assert "This is custom content" in content
        
        # Verify LLM call parameters
        call_kwargs = mock_llm_client.generate_with_system_prompt.call_args.kwargs
        assert call_kwargs["system_prompt"] == system_prompt
        assert "Please summarize the following code" in call_kwargs["user_prompt"]
        
        # Verify stats
        assert generator.stats["other_content_generated"] == 1
        assert generator.stats["total_tokens_used"] == 40
    
    def test_generate_architecture_diagram(self, temp_dir, mock_llm_client, sample_py_file):
        """Test generating an architecture diagram."""
        # Set up mock LLM response with a Mermaid diagram
        mock_llm_client.generate_with_system_prompt.return_value = LLMResponse(
            content="""The architecture consists of a simple class structure.

```mermaid
classDiagram
    class SampleClass {
        +name: str
        +value: int
        +get_value()
        +set_value(new_value)
    }
    class sample_function {
        +process(items, filter_value)
    }
```
""",
            usage={"total_tokens": 80}
        )
        
        # Set up content generator
        generator = ContentGenerator(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Generate architecture diagram
        output_path = generator.generate_architecture_diagram(
            content=sample_py_file,
            diagram_type="class"
        )
        
        # Verify output file is created
        assert output_path is not None
        output_file = Path(output_path)
        assert output_file.exists()
        assert "sample_architecture.md" in output_path
        
        # Verify file content
        with open(output_file, 'r') as f:
            content = f.read()
            assert "# Architecture Diagram (class)" in content
            assert "```mermaid" in content
            assert "classDiagram" in content
            assert "SampleClass" in content
        
        # Verify LLM call parameters
        call_kwargs = mock_llm_client.generate_with_system_prompt.call_args.kwargs
        assert "class diagram" in call_kwargs["system_prompt"]
        assert "Mermaid format" in call_kwargs["user_prompt"]
        
        # Verify stats
        assert generator.stats["other_content_generated"] == 1
        assert generator.stats["total_tokens_used"] == 80
    
    def test_batch_generate(self, temp_dir, mock_llm_client):
        """Test batch generation of content."""
        # Create sample files
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        
        file1 = input_dir / "file1.py"
        file2 = input_dir / "file2.py"
        
        with open(file1, 'w') as f:
            f.write("def function1():\n    pass")
        
        with open(file2, 'w') as f:
            f.write("def function2():\n    pass")
        
        # Set up mock LLM responses for different calls
        responses = [
            LLMResponse(content="FAQ for file1", usage={"total_tokens": 10}),
            LLMResponse(content="FAQ for file2", usage={"total_tokens": 10}),
            LLMResponse(content="Tutorial for file1", usage={"total_tokens": 15})
        ]
        
        mock_llm_client.generate_with_system_prompt.side_effect = responses
        
        # Set up content generator
        generator = ContentGenerator(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Set up topics for tutorials
        topics = {
            str(file1): "Using function1"
        }
        
        # Batch generate content
        result = generator.batch_generate(
            input_files=[file1, file2],
            content_types=["faq", "tutorial"],
            topics=topics
        )
        
        # Verify result statistics
        assert result["stats"]["total_files_processed"] == 2
        assert result["stats"]["total_content_pieces"] > 0
        
        # Verify generated files list
        assert len(result["generated_files"]) == 2  # Both files should have generated content
        
        # Verify failed files list
        assert len(result["failed_files"]) == 0  # No failures expected
        
        # Verify internal stats
        assert generator.stats["faqs_generated"] == 2
        assert generator.stats["tutorials_generated"] > 0
        assert generator.stats["total_tokens_used"] > 0
    
    def test_error_handling(self, temp_dir, mock_llm_client):
        """Test error handling during content generation."""
        # Set up mock LLM client to raise an exception
        mock_llm_client.generate_with_system_prompt.side_effect = Exception("LLM error")
        
        # Set up content generator
        generator = ContentGenerator(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Generate FAQ with error
        output_path = generator.generate_faq("Sample content")
        
        # Verify error handling
        assert output_path is None
        
        # Verify stats remain unchanged
        assert generator.stats["faqs_generated"] == 0
        assert generator.stats["total_tokens_used"] == 0 