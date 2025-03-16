#!/usr/bin/env python3
"""
Test suite for the Markdown documentation generator.

This module contains tests for the Markdown documentation generator, verifying
that it correctly generates Markdown documentation from parsed code entities.
"""

import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Union

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from codedoc.core.entities import (
    Argument, ClassEntity, Entity, FunctionEntity, ImportEntity, 
    ModuleEntity, TypeInfo, VariableEntity
)
from codedoc.core.parser_config import ParserConfig
from codedoc.parsers.python_parser import PythonParser
from codedoc.exporters import GeneratorConfig
from codedoc.exporters.markdown_generator import MarkdownGenerator
from codedoc.tests.utils import (
    create_temp_file, create_temp_module, create_temp_project,
    compare_parsed_entities, cleanup_temp_files
)


class TestMarkdownGenerator(unittest.TestCase):
    """Test case for the Markdown documentation generator."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Initialize parser with configuration to include private members
        parser_config = ParserConfig(include_private_members=True)
        self.parser = PythonParser(parser_config)
        self.generator = MarkdownGenerator(GeneratorConfig())
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "python"
        self.temp_files = []  # Track temp files for cleanup
        self.output_dir = Path(__file__).parent / "output" / "markdown"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def tearDown(self):
        """Clean up test fixtures."""
        cleanup_temp_files(self.temp_files)
        
        # Clean up generated documentation
        if self.output_dir.exists():
            for file in self.output_dir.glob("**/*"):
                if file.is_file():
                    file.unlink()
    
    def test_generate_module_documentation(self):
        """Test generating documentation for a module."""
        # Create a simple Python module with minimal features
        code = '''#!/usr/bin/env python3
"""
A simple test module.

This module contains basic Python constructs for testing.
"""

import sys
import os
from typing import List, Dict

# A simple variable
DEBUG = True

def hello_world():
    """Print a hello world message."""
    print("Hello, World!")
    
def add(a: int, b: int) -> int:
    """
    Add two numbers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The sum of a and b
    """
    return a + b
'''
        
        # Create a temporary file
        file_path = create_temp_file(code, extension=".py")
        self.temp_files.append(file_path)
        
        # Parse the file
        module_entity = self.parser.parse_file(file_path)
        
        # Generate documentation
        doc_path = self.generator.generate_documentation(module_entity, self.output_dir)
        
        # Check that the documentation file was created
        self.assertTrue(doc_path.exists())
        
        # Read the documentation content
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify basic content
        self.assertIn(f"# Module `{module_entity.name}`", content)
        self.assertIn("A simple test module", content)
        self.assertIn("## Imports", content)
        self.assertIn("## Variables", content)
        self.assertIn("## Functions", content)
        self.assertIn("hello_world", content)
        self.assertIn("add", content)
    
    def test_generate_class_documentation(self):
        """Test generating documentation for a class."""
        # Create a Python module with a class definition
        code = '''
"""Module with a class definition."""

class BaseClass:
    """A base class."""
    
    def __init__(self, name: str):
        """Initialize with a name."""
        self.name = name
        
    def get_name(self) -> str:
        """Get the name."""
        return self.name

class ChildClass(BaseClass):
    """A child class that inherits from BaseClass."""
    
    def __init__(self, name: str, value: int = 0):
        """
        Initialize with name and value.
        
        Args:
            name: The name
            value: The value (default: 0)
        """
        super().__init__(name)
        self.value = value
        
    @property
    def total(self) -> int:
        """Get the total value."""
        return self.value
        
    @classmethod
    def create(cls, name: str) -> 'ChildClass':
        """Create a new instance."""
        return cls(name)
        
    @staticmethod
    def helper() -> None:
        """A helper method."""
        print("Helper")
'''
        
        # Create a temporary file
        file_path = create_temp_file(code, extension=".py")
        self.temp_files.append(file_path)
        
        # Parse the file
        module_entity = self.parser.parse_file(file_path)
        
        # Generate documentation for the module
        module_doc_path = self.generator.generate_documentation(module_entity, self.output_dir)
        
        # Get the ChildClass entity
        child_class = next(cls for cls in module_entity.classes if cls.name == "ChildClass")
        
        # Find the class documentation file
        child_class_doc_path = Path()
        for file in self.output_dir.glob("**/*"):
            if file.is_file() and file.stem == "ChildClass":
                child_class_doc_path = file
                break
        
        # Check that the class documentation file was found
        self.assertTrue(child_class_doc_path.exists())
        
        # Read the class documentation content
        with open(child_class_doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify basic content
        self.assertIn("# Class `ChildClass`", content)
        self.assertIn("A child class that inherits from BaseClass", content)
        self.assertIn("**Inherits from:** `BaseClass`", content)
        self.assertIn("## Constructor", content)
        self.assertIn("## Properties", content)
        self.assertIn("## Class Methods", content)
        self.assertIn("## Static Methods", content)
        self.assertIn("`total`", content)
        self.assertIn("`create`", content)
        self.assertIn("`helper`", content)
    
    def test_generate_function_documentation(self):
        """Test generating documentation for a function."""
        # Create a Python module with a function
        code = '''
"""Module with a function."""

def process_data(
    data: list[dict[str, any]], 
    max_items: int = 100, 
    verbose: bool = False
) -> tuple[list, int]:
    """
    Process a list of data items.
    
    Args:
        data: The data to process
        max_items: Maximum number of items to process
        verbose: Whether to print verbose output
        
    Returns:
        A tuple containing:
        - The processed data
        - The number of items processed
        
    Raises:
        ValueError: If data is empty
        TypeError: If data is not a list
    """
    if not data:
        raise ValueError("Data cannot be empty")
        
    if not isinstance(data, list):
        raise TypeError("Data must be a list")
        
    result = []
    for i, item in enumerate(data):
        if i >= max_items:
            break
            
        if verbose:
            print(f"Processing item {i}")
            
        result.append(item)
        
    return result, len(result)
'''
        
        # Create a temporary file
        file_path = create_temp_file(code, extension=".py")
        self.temp_files.append(file_path)
        
        # Parse the file
        module_entity = self.parser.parse_file(file_path)
        
        # Generate documentation for the module
        module_doc_path = self.generator.generate_documentation(module_entity, self.output_dir)
        
        # Get the process_data function entity
        function = module_entity.functions[0]
        
        # Find the function documentation file
        function_doc_path = Path()
        for file in self.output_dir.glob("**/*"):
            if file.is_file() and file.stem == "process_data":
                function_doc_path = file
                break
        
        # Check that the function documentation file was found
        self.assertTrue(function_doc_path.exists())
        
        # Read the function documentation content
        with open(function_doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify basic content
        self.assertIn("# Function `process_data`", content)
        self.assertIn("Process a list of data items", content)
        self.assertIn("## Signature", content)
        self.assertIn("## Parameters", content)
        self.assertIn("### `data`", content)
        self.assertIn("### `max_items`", content)
        self.assertIn("### `verbose`", content)
        self.assertIn("## Returns", content)
        self.assertIn("## Raises", content)
        self.assertIn("### `ValueError`", content)
        self.assertIn("### `TypeError`", content)
    
    def test_generate_index(self):
        """Test generating an index page."""
        # Create a simple Python module
        code = '''
"""Test module for index generation."""

def func1():
    """Function 1."""
    pass
    
def func2():
    """Function 2."""
    pass
    
class Class1:
    """Class 1."""
    pass
    
class Class2:
    """Class 2."""
    pass
'''
        
        # Create a temporary file
        file_path = create_temp_file(code, extension=".py")
        self.temp_files.append(file_path)
        
        # Parse the file
        module_entity = self.parser.parse_file(file_path)
        
        # Generate documentation for all entities first
        self.generator.generate_documentation(module_entity, self.output_dir)
        
        # Generate documentation for classes and functions separately
        for cls in module_entity.classes:
            self.generator.generate_documentation(cls, self.output_dir)
        
        for func in module_entity.functions:
            self.generator.generate_documentation(func, self.output_dir)
        
        # Generate index
        index_path = self.generator.generate_index([module_entity], self.output_dir, "Test API")
        
        # Check that the index file was created
        self.assertTrue(index_path.exists())
        
        # Read the index content
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify basic content
        self.assertIn("# Test API", content)
        self.assertIn("## Table of Contents", content)
        self.assertIn("### Modules", content)
        self.assertIn("### Classes", content)
        self.assertIn("### Functions", content)
        self.assertIn(module_entity.name, content)
    
    def test_generate_documentation_with_config(self):
        """Test generating documentation with various configuration options."""
        # Create a simple Python module
        code = '''
"""Test module for configuration options."""

# Private variable
_PRIVATE_VAR = "private"
# Public variable
PUBLIC_VAR = "public"

def _private_func():
    """A private function."""
    pass
    
def public_func(a: int, b: str = "default") -> bool:
    """A public function."""
    return True
    
class _PrivateClass:
    """A private class."""
    pass
    
class PublicClass:
    """A public class."""
    
    def __init__(self):
        """Initialize."""
        self._private_attr = 1
        self.public_attr = 2
        
    def _private_method(self):
        """A private method."""
        pass
        
    def public_method(self):
        """A public method."""
        pass
'''
        
        # Create a temporary file
        file_path = create_temp_file(code, extension=".py")
        self.temp_files.append(file_path)
        
        # Parse the file
        module_entity = self.parser.parse_file(file_path)
        
        # Verify that the module has the expected variables
        var_names = [var.name for var in module_entity.variables]
        self.assertIn("_PRIVATE_VAR", var_names)
        self.assertIn("PUBLIC_VAR", var_names)
        
        # Test with private members excluded
        config1 = GeneratorConfig(include_private=False)
        generator1 = MarkdownGenerator(config1)
        
        # Create separate output directory for this test
        output_dir1 = self.output_dir / "no_private"
        output_dir1.mkdir(exist_ok=True)
        
        # Generate documentation
        doc_path1 = generator1.generate_documentation(module_entity, output_dir1)
        
        # Read the documentation content
        with open(doc_path1, "r", encoding="utf-8") as f:
            content1 = f.read()
        
        # Verify that private members are excluded
        self.assertNotIn("_PRIVATE_VAR", content1)
        self.assertNotIn("_private_func", content1)
        self.assertNotIn("_PrivateClass", content1)
        self.assertIn("PUBLIC_VAR", content1)
        self.assertIn("public_func", content1)
        self.assertIn("PublicClass", content1)
        
        # Test with private members included
        config2 = GeneratorConfig(include_private=True)
        generator2 = MarkdownGenerator(config2)
        
        # Create separate output directory for this test
        output_dir2 = self.output_dir / "with_private"
        output_dir2.mkdir(exist_ok=True)
        
        # Generate documentation
        doc_path2 = generator2.generate_documentation(module_entity, output_dir2)
        
        # Read the documentation content
        with open(doc_path2, "r", encoding="utf-8") as f:
            content2 = f.read()
        
        # Verify that private members are included
        self.assertIn("_PRIVATE_VAR", content2)
        self.assertIn("_private_func", content2)
        self.assertIn("_PrivateClass", content2)
        self.assertIn("PUBLIC_VAR", content2)
        self.assertIn("public_func", content2)
        self.assertIn("PublicClass", content2)
    
    def test_generate_sample_documentation(self):
        """Test generating documentation for the sample Python file."""
        sample_path = self.fixtures_dir / "sample.py"
        
        # Make sure the sample file exists
        self.assertTrue(sample_path.exists(), f"Sample file not found: {sample_path}")
        
        # Parse the file
        module_entity = self.parser.parse_file(sample_path)
        
        # Generate documentation
        doc_path = self.generator.generate_documentation(module_entity, self.output_dir)
        
        # Generate index
        index_path = self.generator.generate_index([module_entity], self.output_dir, "Sample API")
        
        # Check that the documentation files were created
        self.assertTrue(doc_path.exists())
        self.assertTrue(index_path.exists())
        
        # Read the documentation content
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify that key elements from the sample are included
        self.assertIn("Sample Python module for testing the parser", content)
        self.assertIn("calculate_sum", content)
        self.assertIn("process_data", content)
        self.assertIn("Item", content)
        self.assertIn("SpecialItem", content)
        self.assertIn("Configuration", content)
        self.assertIn("BaseProcessor", content)
        self.assertIn("complex_function", content)


if __name__ == "__main__":
    unittest.main() 