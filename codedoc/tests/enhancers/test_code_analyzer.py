"""
Tests for the code analyzer.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from codedoc.enhancers.code_analyzer import CodeAnalyzer
from codedoc.llm.base import LLMResponse


class TestCodeAnalyzer:
    """Tests for the CodeAnalyzer class."""
    
    def test_init(self, temp_dir):
        """Test initialization."""
        # Create mock LLM client
        mock_llm_client = MagicMock()
        
        # Initialize the analyzer
        analyzer = CodeAnalyzer(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Verify initialization
        assert analyzer.llm_client == mock_llm_client
        assert analyzer.output_dir == Path(temp_dir)
        assert analyzer.prompt_manager is not None
        assert analyzer.temperature == 0.3
    
    def test_analyze_patterns(self, temp_dir):
        """Test analyzing patterns in code."""
        # Create mock LLM client
        mock_llm_client = MagicMock()
        mock_response = MagicMock(spec=LLMResponse)
        mock_response.content = """
        # Pattern Analysis
        
        ## Design Patterns
        
        ### Factory Pattern
        - **Location**: Class `UserFactory` in lines 10-30
        - **Description**: Creates different types of user objects based on input
        - **Advantages**: Centralizes object creation logic
        
        ### Observer Pattern
        - **Location**: Class `EventManager` in lines 50-80
        - **Description**: Implements event-based communication
        - **Advantages**: Loose coupling between components
        """
        mock_llm_client.generate_with_system_prompt.return_value = mock_response
        
        # Create a sample Python file
        test_file = temp_dir / "sample.py"
        with open(test_file, "w") as f:
            f.write("""
class UserFactory:
    def create_user(self, user_type):
        if user_type == "admin":
            return AdminUser()
        elif user_type == "customer":
            return CustomerUser()
        else:
            return GuestUser()
            
class EventManager:
    def __init__(self):
        self.listeners = {}
        
    def subscribe(self, event_type, listener):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)
        
    def notify(self, event_type, data):
        if event_type in self.listeners:
            for listener in self.listeners[event_type]:
                listener(data)
            """)
        
        # Initialize the analyzer
        analyzer = CodeAnalyzer(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Analyze patterns
        result = analyzer.analyze_patterns(test_file)
        
        # Verify analysis
        assert result is not None
        assert "Pattern Analysis" in result
        assert "Factory Pattern" in result
        assert "Observer Pattern" in result
        
        # Verify correct LLM call
        mock_llm_client.generate_with_system_prompt.assert_called_once()
        system_prompt, user_prompt = mock_llm_client.generate_with_system_prompt.call_args.args
        assert "pattern" in system_prompt.lower()
        assert "sample.py" in user_prompt
    
    def test_analyze_complexity(self, temp_dir):
        """Test analyzing code complexity."""
        # Create mock LLM client
        mock_llm_client = MagicMock()
        mock_response = MagicMock(spec=LLMResponse)
        mock_response.content = """
        # Complexity Analysis
        
        ## Overall Complexity
        
        - **Cognitive Complexity**: Medium
        - **Cyclometric Complexity**: 5
        - **Time Complexity**: O(n) for most operations
        - **Space Complexity**: O(n) for event storage
        
        ## Complex Areas
        
        ### Method `process_events`
        - **Lines**: 25-40
        - **Complexity Factors**: Nested loops, conditional logic
        - **Suggestions**: Consider breaking down into smaller functions
        """
        mock_llm_client.generate_with_system_prompt.return_value = mock_response
        
        # Create a sample Python file
        test_file = temp_dir / "sample.py"
        with open(test_file, "w") as f:
            f.write("""
class EventProcessor:
    def __init__(self):
        self.events = []
        
    def add_event(self, event):
        self.events.append(event)
        
    def process_events(self, filters=None):
        results = []
        for event in self.events:
            if filters:
                match = True
                for key, value in filters.items():
                    if key not in event or event[key] != value:
                        match = False
                        break
                if match:
                    results.append(self.transform_event(event))
            else:
                results.append(self.transform_event(event))
        return results
        
    def transform_event(self, event):
        return {
            "id": event.get("id"),
            "type": event.get("type"),
            "timestamp": event.get("timestamp"),
            "processed": True
        }
            """)
        
        # Initialize the analyzer
        analyzer = CodeAnalyzer(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Analyze complexity
        result = analyzer.analyze_complexity(test_file)
        
        # Verify analysis
        assert result is not None
        assert "Complexity Analysis" in result
        assert "Cognitive Complexity" in result
        assert "Complex Areas" in result
        
        # Verify correct LLM call
        mock_llm_client.generate_with_system_prompt.assert_called_once()
        system_prompt, user_prompt = mock_llm_client.generate_with_system_prompt.call_args.args
        assert "complexity" in system_prompt.lower()
        assert "sample.py" in user_prompt
    
    def test_analyze_file(self, temp_dir):
        """Test analyzing a complete file."""
        # Create mock LLM client
        mock_llm_client = MagicMock()
        
        # Set up mock responses for different analyses
        mock_pattern_response = MagicMock(spec=LLMResponse)
        mock_pattern_response.content = "# Pattern Analysis\n\nFactory Pattern detected."
        
        mock_complexity_response = MagicMock(spec=LLMResponse)
        mock_complexity_response.content = "# Complexity Analysis\n\nMedium complexity."
        
        # Configure mock to return different responses based on prompt
        def mock_generate(system_prompt, user_prompt, **kwargs):
            if "pattern" in system_prompt.lower():
                return mock_pattern_response
            else:
                return mock_complexity_response
                
        mock_llm_client.generate_with_system_prompt.side_effect = mock_generate
        
        # Create a sample Python file
        test_file = temp_dir / "sample.py"
        with open(test_file, "w") as f:
            f.write("print('Hello, World!')")
        
        # Initialize the analyzer
        analyzer = CodeAnalyzer(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Analyze file with both analyses
        result = analyzer.analyze_file(
            file_path=test_file,
            analyses=["patterns", "complexity"]
        )
        
        # Verify analysis results
        assert result["file_path"] == str(test_file)
        assert result["analyses"]["patterns"] is not None
        assert result["analyses"]["complexity"] is not None
        assert "Pattern Analysis" in result["analyses"]["patterns"]
        assert "Complexity Analysis" in result["analyses"]["complexity"]
        
        # Verify output files were created
        patterns_file = temp_dir / "patterns" / "sample.py.md"
        complexity_file = temp_dir / "complexity" / "sample.py.md"
        assert patterns_file.exists()
        assert complexity_file.exists()
        
        # Verify LLM was called twice (once for each analysis)
        assert mock_llm_client.generate_with_system_prompt.call_count == 2
    
    def test_analyze_directory(self, temp_dir):
        """Test analyzing a directory of files."""
        # Create mock LLM client
        mock_llm_client = MagicMock()
        
        # Set up mock response
        mock_response = MagicMock(spec=LLMResponse)
        mock_response.content = "# Analysis\n\nSample analysis."
        mock_llm_client.generate_with_system_prompt.return_value = mock_response
        
        # Create sample directory structure with files
        sample_dir = temp_dir / "src"
        sample_dir.mkdir()
        
        # Create Python files
        (sample_dir / "file1.py").write_text("print('File 1')")
        (sample_dir / "file2.py").write_text("print('File 2')")
        
        # Create subdirectory with files
        sub_dir = sample_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.py").write_text("print('File 3')")
        
        # Initialize the analyzer
        analyzer = CodeAnalyzer(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Analyze directory
        result = analyzer.analyze_directory(
            input_dir=sample_dir,
            file_patterns=["*.py"],
            analyses=["patterns"],
            recursive=True
        )
        
        # Verify analysis results
        assert result["input_dir"] == str(sample_dir)
        assert result["file_count"] == 3
        assert len(result["analyzed_files"]) == 3
        assert result["success_count"] == 3
        assert result["failure_count"] == 0
        
        # Verify each file was analyzed
        analyzed_paths = [item["file_path"] for item in result["analyzed_files"]]
        assert str(sample_dir / "file1.py") in analyzed_paths
        assert str(sample_dir / "file2.py") in analyzed_paths
        assert str(sample_dir / "subdir" / "file3.py") in analyzed_paths
        
        # Verify LLM was called three times (once for each file)
        assert mock_llm_client.generate_with_system_prompt.call_count == 3
    
    def test_extract_patterns_from_text(self, temp_dir):
        """Test extracting pattern information from analysis text."""
        # Create mock LLM client
        mock_llm_client = MagicMock()
        
        # Initialize the analyzer
        analyzer = CodeAnalyzer(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Sample analysis text
        text = """
        # Pattern Analysis
        
        ## Design Patterns
        
        ### Factory Pattern
        - **Location**: Class `UserFactory` in lines 10-30
        - **Description**: Creates different types of user objects
        - **Advantages**: Centralized object creation
        
        ### Observer Pattern
        - **Location**: Class `EventManager` in lines 50-80
        - **Description**: Event-based communication
        """
        
        # Extract patterns
        patterns = analyzer._extract_patterns_from_text(text)
        
        # Verify extraction
        assert len(patterns) == 2
        assert patterns[0]["name"] == "Factory Pattern"
        assert "UserFactory" in patterns[0]["location"]
        assert patterns[1]["name"] == "Observer Pattern"
        assert "EventManager" in patterns[1]["location"]
    
    def test_extract_complexity_from_text(self, temp_dir):
        """Test extracting complexity information from analysis text."""
        # Create mock LLM client
        mock_llm_client = MagicMock()
        
        # Initialize the analyzer
        analyzer = CodeAnalyzer(
            llm_client=mock_llm_client,
            output_dir=temp_dir
        )
        
        # Sample analysis text
        text = """
        # Complexity Analysis
        
        ## Overall Complexity
        
        - **Cognitive Complexity**: Medium
        - **Cyclometric Complexity**: 5
        - **Time Complexity**: O(n)
        - **Space Complexity**: O(n)
        
        ## Complex Areas
        
        ### Method `process_events`
        - **Lines**: 25-40
        - **Complexity Factors**: Nested loops
        """
        
        # Extract complexity info
        complexity = analyzer._extract_complexity_from_text(text)
        
        # Verify extraction
        assert complexity["cognitive_complexity"] == "Medium"
        assert complexity["cyclometric_complexity"] == "5"
        assert complexity["time_complexity"] == "O(n)"
        assert complexity["space_complexity"] == "O(n)"
        assert len(complexity["complex_areas"]) == 1
        assert complexity["complex_areas"][0]["name"] == "Method `process_events`"
        assert complexity["complex_areas"][0]["lines"] == "25-40" 