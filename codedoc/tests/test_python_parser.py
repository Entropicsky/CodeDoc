#!/usr/bin/env python3
"""
Test suite for the Python AST parser.

This module contains tests for the Python AST parser, verifying that it
correctly extracts information from Python code including functions, classes,
methods, docstrings, type annotations, and more.
"""

import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Union

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from codedoc.core.entities import (
    Argument, ClassEntity, FunctionEntity, ImportEntity, 
    ModuleEntity, TypeInfo, VariableEntity
)
from codedoc.core.parser_config import ParserConfig
from codedoc.parsers.python_parser import PythonParser
from codedoc.tests.utils import (
    create_temp_file, create_temp_module, create_temp_project,
    compare_parsed_entities, cleanup_temp_files
)


class TestPythonParser(unittest.TestCase):
    """Test case for the Python AST parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = PythonParser()
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "python"
        self.temp_files = []  # Track temp files for cleanup
        
    def tearDown(self):
        """Clean up test fixtures."""
        cleanup_temp_files(self.temp_files)
    
    def test_parse_simple_module(self):
        """Test parsing a simple Python module."""
        # Create a simple Python module with minimal features
        code = """#!/usr/bin/env python3
        \"\"\"
        A simple test module.
        
        This module contains basic Python constructs for testing.
        \"\"\"
        
        import sys
        import os
        from typing import List, Dict
        
        # A simple variable
        DEBUG = True
        
        def hello_world():
            \"\"\"Print a hello world message.\"\"\"
            print("Hello, World!")
            
        def add(a: int, b: int) -> int:
            \"\"\"
            Add two numbers.
            
            Args:
                a: First number
                b: Second number
                
            Returns:
                The sum of a and b
            \"\"\"
            return a + b
        """
        
        # Create a temporary file
        file_path = create_temp_file(code, suffix=".py")
        self.temp_files.append(file_path)
        
        # Parse the file
        module_entity = self.parser.parse_file(file_path)
        
        # Verify the module was parsed correctly
        self.assertEqual(module_entity.name, file_path.stem)
        self.assertIn("A simple test module", module_entity.docstring)
        
        # Verify imports
        self.assertEqual(len(module_entity.imports), 3)
        import_names = [imp.module_name for imp in module_entity.imports]
        self.assertIn("sys", import_names)
        self.assertIn("os", import_names)
        self.assertIn("typing", import_names)  # from typing import ...
        
        # Verify variables
        self.assertEqual(len(module_entity.variables), 1)
        self.assertEqual(module_entity.variables[0].name, "DEBUG")
        self.assertEqual(module_entity.variables[0].value, "True")
        
        # Verify functions
        self.assertEqual(len(module_entity.functions), 2)
        function_names = [func.name for func in module_entity.functions]
        self.assertIn("hello_world", function_names)
        self.assertIn("add", function_names)
        
        # Get the add function for detailed testing
        add_func = next(func for func in module_entity.functions if func.name == "add")
        self.assertEqual(len(add_func.arguments), 2)
        self.assertEqual(add_func.arguments[0].name, "a")
        self.assertEqual(add_func.arguments[0].type_annotation.name, "int")
        self.assertEqual(add_func.arguments[1].name, "b")
        self.assertEqual(add_func.arguments[1].type_annotation.name, "int")
        self.assertEqual(add_func.return_type.name, "int")
        
        # Verify docstring parsing
        self.assertIn("Add two numbers", add_func.docstring)
        self.assertIn("args", add_func.docstring_sections)
        args_section = add_func.docstring_sections["args"]
        self.assertEqual(len(args_section), 2)
        arg_names = [arg["name"] for arg in args_section]
        self.assertIn("a", arg_names)
        self.assertIn("b", arg_names)
    
    def test_parse_class(self):
        """Test parsing a Python class with methods and inheritance."""
        # Create a Python module with a class definition
        code = """
        \"\"\"Module with a class definition.\"\"\"
        
        class BaseClass:
            \"\"\"A base class.\"\"\"
            
            def __init__(self, name: str):
                \"\"\"Initialize with a name.\"\"\"
                self.name = name
                
            def get_name(self) -> str:
                \"\"\"Get the name.\"\"\"
                return self.name
        
        class ChildClass(BaseClass):
            \"\"\"A child class that inherits from BaseClass.\"\"\"
            
            def __init__(self, name: str, value: int = 0):
                \"\"\"
                Initialize with name and value.
                
                Args:
                    name: The name
                    value: The value (default: 0)
                \"\"\"
                super().__init__(name)
                self.value = value
                
            @property
            def total(self) -> int:
                \"\"\"Get the total value.\"\"\"
                return self.value
                
            @classmethod
            def create(cls, name: str) -> 'ChildClass':
                \"\"\"Create a new instance.\"\"\"
                return cls(name)
                
            @staticmethod
            def helper() -> None:
                \"\"\"A helper method.\"\"\"
                print("Helper")
        """
        
        # Create a temporary file
        file_path = create_temp_file(code, suffix=".py")
        self.temp_files.append(file_path)
        
        # Parse the file
        module_entity = self.parser.parse_file(file_path)
        
        # Verify the module was parsed correctly
        self.assertEqual(len(module_entity.classes), 2)
        
        # Get the classes for detailed testing
        base_class = next(cls for cls in module_entity.classes if cls.name == "BaseClass")
        child_class = next(cls for cls in module_entity.classes if cls.name == "ChildClass")
        
        # Verify base class
        self.assertEqual(base_class.name, "BaseClass")
        self.assertEqual(len(base_class.methods), 2)  # __init__ and get_name
        self.assertEqual(len(base_class.base_classes), 0)  # No inheritance
        
        # Verify child class
        self.assertEqual(child_class.name, "ChildClass")
        self.assertEqual(len(child_class.methods), 4)  # __init__, total, create, helper
        self.assertEqual(len(child_class.base_classes), 1)
        self.assertEqual(child_class.base_classes[0], "BaseClass")
        
        # Check method types
        init_method = next(m for m in child_class.methods if m.name == "__init__")
        total_prop = next(m for m in child_class.methods if m.name == "total")
        create_method = next(m for m in child_class.methods if m.name == "create")
        helper_method = next(m for m in child_class.methods if m.name == "helper")
        
        self.assertTrue(init_method.is_method)
        self.assertTrue(total_prop.is_property)
        self.assertTrue(create_method.is_class_method)
        self.assertTrue(helper_method.is_static)
        
        # Check arguments
        self.assertEqual(len(init_method.arguments), 2)  # name and value (not counting self)
        self.assertEqual(init_method.arguments[0].name, "name")
        self.assertEqual(init_method.arguments[1].name, "value")
        self.assertEqual(init_method.arguments[1].default_value, "0")
        
        # Check decorators
        self.assertEqual(len(total_prop.decorators), 1)
        self.assertEqual(total_prop.decorators[0], "property")
        self.assertEqual(len(create_method.decorators), 1)
        self.assertEqual(create_method.decorators[0], "classmethod")
        self.assertEqual(len(helper_method.decorators), 1)
        self.assertEqual(helper_method.decorators[0], "staticmethod")
    
    def test_parse_complex_types(self):
        """Test parsing complex type annotations."""
        # Create a Python module with complex type annotations
        code = """
        \"\"\"Module with complex type annotations.\"\"\"
        
        from typing import List, Dict, Tuple, Optional, Union, Any, Callable
        
        def process(
            items: List[Dict[str, Any]],
            callback: Optional[Callable[[str, int], bool]] = None,
            config: Dict[str, Union[str, int, bool]] = None
        ) -> Tuple[List[Any], int]:
            \"\"\"Process items with complex types.\"\"\"
            return [], 0
            
        class Container:
            \"\"\"A container class with complex types.\"\"\"
            
            def __init__(self):
                self.items: List[Dict[str, Any]] = []
                self.mapping: Dict[str, Tuple[int, str]] = {}
                
            def add(self, item: Any) -> None:
                \"\"\"Add an item.\"\"\"
                self.items.append({"value": item})
        """
        
        # Create a temporary file
        file_path = create_temp_file(code, suffix=".py")
        self.temp_files.append(file_path)
        
        # Parse the file
        module_entity = self.parser.parse_file(file_path)
        
        # Get the process function
        process_func = module_entity.functions[0]
        
        # Check parameter types
        items_param = process_func.arguments[0]
        self.assertEqual(items_param.name, "items")
        self.assertEqual(items_param.type_annotation.name, "List")
        self.assertTrue(items_param.type_annotation.is_container)
        self.assertEqual(len(items_param.type_annotation.container_types), 1)
        self.assertEqual(items_param.type_annotation.container_types[0].name, "Dict")
        
        callback_param = process_func.arguments[1]
        self.assertEqual(callback_param.name, "callback")
        self.assertEqual(callback_param.type_annotation.name, "Optional")
        
        # Check return type
        self.assertEqual(process_func.return_type.name, "Tuple")
        self.assertTrue(process_func.return_type.is_container)
        self.assertEqual(len(process_func.return_type.container_types), 2)
        self.assertEqual(process_func.return_type.container_types[0].name, "List")
        self.assertEqual(process_func.return_type.container_types[1].name, "int")
        
        # Get the Container class
        container_class = module_entity.classes[0]
        
        # Get the add method
        add_method = container_class.methods[1]  # __init__ is [0], add is [1]
        
        # Check parameter type
        item_param = add_method.arguments[0]
        self.assertEqual(item_param.name, "item")
        self.assertEqual(item_param.type_annotation.name, "Any")
        
        # Check return type
        self.assertEqual(add_method.return_type.name, "None")
    
    def test_parse_sample_file(self):
        """Test parsing the sample Python file in the fixtures directory."""
        sample_path = self.fixtures_dir / "sample.py"
        
        # Make sure the sample file exists
        self.assertTrue(sample_path.exists(), f"Sample file not found: {sample_path}")
        
        # Parse the file
        module_entity = self.parser.parse_file(sample_path)
        
        # Basic module verification
        self.assertEqual(module_entity.name, "sample")
        self.assertIn("Sample Python module for testing the parser", module_entity.docstring)
        
        # Verify imports
        import_modules = [imp.module_name for imp in module_entity.imports]
        self.assertIn("os", import_modules)
        self.assertIn("sys", import_modules)
        self.assertIn("typing", import_modules)
        
        # Verify module variables
        variables = {var.name: var for var in module_entity.variables}
        self.assertIn("DEBUG", variables)
        self.assertIn("MAX_ITEMS", variables)
        self.assertIn("VERSION", variables)
        
        # Verify functions
        functions = {func.name: func for func in module_entity.functions}
        self.assertIn("calculate_sum", functions)
        self.assertIn("process_data", functions)
        self.assertIn("complex_function", functions)
        
        # Check calculate_sum function
        calc_func = functions["calculate_sum"]
        self.assertEqual(len(calc_func.arguments), 2)
        self.assertEqual(calc_func.arguments[0].name, "a")
        self.assertEqual(calc_func.arguments[0].type_annotation.name, "int")
        self.assertEqual(calc_func.return_type.name, "int")
        
        # Verify classes
        classes = {cls.name: cls for cls in module_entity.classes}
        self.assertIn("Item", classes)
        self.assertIn("SpecialItem", classes)
        self.assertIn("Configuration", classes)
        self.assertIn("BaseProcessor", classes)
        self.assertIn("DefaultProcessor", classes)
        self.assertIn("SpecialProcessor", classes)
        
        # Check inheritance
        self.assertEqual(len(classes["SpecialItem"].base_classes), 1)
        self.assertEqual(classes["SpecialItem"].base_classes[0], "Item")
        
        self.assertEqual(len(classes["DefaultProcessor"].base_classes), 1)
        self.assertEqual(classes["DefaultProcessor"].base_classes[0], "BaseProcessor")
        
        # Check methods
        special_processor = classes["SpecialProcessor"]
        methods = {method.name: method for method in special_processor.methods}
        
        self.assertIn("__init__", methods)
        self.assertIn("name", methods)
        self.assertIn("get_version", methods)
        self.assertIn("from_config_file", methods)
        self.assertIn("process", methods)
        
        # Check method types
        self.assertTrue(methods["name"].is_property)
        self.assertTrue(methods["get_version"].is_static)
        self.assertTrue(methods["from_config_file"].is_class_method)
        
        # Check decorators
        self.assertIn("property", methods["name"].decorators)
        self.assertIn("staticmethod", methods["get_version"].decorators)
        self.assertIn("classmethod", methods["from_config_file"].decorators)
        
        # Check dataclass
        config_class = classes["Configuration"]
        self.assertIn("dataclass(...)", config_class.decorators)


if __name__ == "__main__":
    unittest.main() 