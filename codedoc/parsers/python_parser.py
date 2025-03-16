#!/usr/bin/env python3
"""
Python AST-based parser for the CodeDoc framework.

This module provides a parser implementation that uses Python's built-in
Abstract Syntax Tree (AST) to extract detailed information from Python files,
including functions, classes, methods, docstrings, and relationships between
entities.
"""

import ast
import inspect
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from ..core.base_parser import BaseParser
from ..core.entities import (
    Argument, ClassEntity, Entity, FunctionEntity, ImportEntity, 
    ModuleEntity, Property, TypeInfo, VariableEntity
)
from ..core.parser_config import ParserConfig
from ..utils.docstring_parser import parse_docstring

# Configure logger
logger = logging.getLogger(__name__)


class PythonParser(BaseParser):
    """
    Parser for Python code using the built-in AST module.
    
    This parser extracts detailed information from Python files, including:
    - Module docstrings and imports
    - Classes, inheritance, and class attributes
    - Methods, properties, and class/static methods
    - Functions, arguments, and return values
    - Type annotations and docstrings
    - Relationships between entities
    
    The parser uses Python's built-in AST module to build a structured
    representation of the code, which is then converted to CodeDoc entities.
    """
    
    LANGUAGE = "python"
    FILE_EXTENSIONS = [".py"]
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize the Python parser.
        
        Args:
            config: Parser configuration options
        """
        super().__init__(config or ParserConfig())
        self._current_module: Optional[ModuleEntity] = None
        self._current_class: Optional[ClassEntity] = None
        self._imported_names: Dict[str, str] = {}
        self._module_path: Optional[Path] = None
    
    def parse_file(self, file_path: Union[str, Path]) -> ModuleEntity:
        """
        Parse a Python file and extract all entities.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            ModuleEntity containing all extracted information
            
        Raises:
            ValueError: If the file cannot be parsed
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")
            
        logger.debug(f"Parsing Python file: {file_path}")
        self._module_path = file_path
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            module_ast = ast.parse(source_code, filename=str(file_path))
            return self._parse_module(module_ast, file_path)
            
        except SyntaxError as e:
            logger.error(f"Syntax error in file {file_path}: {e}")
            raise ValueError(f"Syntax error in file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            raise ValueError(f"Error parsing file {file_path}: {e}")
    
    def _parse_module(self, module_ast: ast.Module, file_path: Path) -> ModuleEntity:
        """
        Parse a module AST node and create a ModuleEntity.
        
        Args:
            module_ast: AST node for the module
            file_path: Path to the module file
            
        Returns:
            ModuleEntity with all extracted information
        """
        module_name = file_path.stem
        module_docstring = ast.get_docstring(module_ast) or ""
        
        # Create module entity
        self._current_module = ModuleEntity(
            name=module_name,
            docstring=module_docstring,
            file_path=str(file_path),
            line_start=1,
            line_end=len(module_ast.body) + 1 if module_ast.body else 1,
        )
        
        # Reset state for this module
        self._imported_names = {}
        
        # Parse all nodes in the module
        for node in module_ast.body:
            self._parse_node(node)
        
        return self._current_module
    
    def _parse_node(self, node: ast.AST) -> Optional[Entity]:
        """
        Parse an AST node and dispatch to the appropriate handler.
        
        Args:
            node: AST node to parse
            
        Returns:
            Parsed entity or None
        """
        if isinstance(node, ast.FunctionDef):
            return self._parse_function(node)
        elif isinstance(node, ast.ClassDef):
            return self._parse_class(node)
        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            return self._parse_import(node)
        elif isinstance(node, ast.Assign):
            return self._parse_assignment(node)
        elif isinstance(node, ast.AnnAssign):
            return self._parse_annotated_assignment(node)
        # Add more node types as needed
        
        return None
    
    def _parse_function(self, node: ast.FunctionDef) -> FunctionEntity:
        """
        Parse a function definition and create a FunctionEntity.
        
        Args:
            node: AST node for the function
            
        Returns:
            FunctionEntity with all extracted information
        """
        name = node.name
        docstring = ast.get_docstring(node) or ""
        is_method = self._current_class is not None
        is_property = any(isinstance(d, ast.Name) and d.id == 'property' 
                          for d in node.decorator_list)
        is_static = any(isinstance(d, ast.Name) and d.id == 'staticmethod' 
                        for d in node.decorator_list)
        is_class_method = any(isinstance(d, ast.Name) and d.id == 'classmethod' 
                              for d in node.decorator_list)
        
        # Get function arguments
        arguments = self._parse_arguments(node.args)
        
        # Get return type annotation
        return_type = self._parse_type_annotation(node.returns) if hasattr(node, 'returns') and node.returns else None
        
        # Parse docstring to extract more information
        docstring_info = parse_docstring(docstring)
        
        # Create function entity
        function_entity = FunctionEntity(
            name=name,
            docstring=docstring,
            arguments=arguments,
            return_type=return_type,
            is_method=is_method,
            is_property=is_property,
            is_static=is_static,
            is_class_method=is_class_method,
            parent_entity_id=self._current_class.id if self._current_class else self._current_module.id,
            line_start=node.lineno,
            line_end=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            docstring_sections=docstring_info,
        )
        
        # Add decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                function_entity.decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                function_entity.decorators.append(f"{self._get_attribute_name(decorator)}")
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    function_entity.decorators.append(f"{decorator.func.id}(...)")
                elif isinstance(decorator.func, ast.Attribute):
                    function_entity.decorators.append(f"{self._get_attribute_name(decorator.func)}(...)")
        
        # Add to parent
        if self._current_class:
            self._current_class.methods.append(function_entity)
        else:
            self._current_module.functions.append(function_entity)
        
        return function_entity
    
    def _parse_class(self, node: ast.ClassDef) -> ClassEntity:
        """
        Parse a class definition and create a ClassEntity.
        
        Args:
            node: AST node for the class
            
        Returns:
            ClassEntity with all extracted information
        """
        name = node.name
        docstring = ast.get_docstring(node) or ""
        
        # Get base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(self._get_attribute_name(base))
            # Add more complex base class handling if needed
        
        # Parse docstring to extract more information
        docstring_info = parse_docstring(docstring)
        
        # Create class entity
        class_entity = ClassEntity(
            name=name,
            docstring=docstring,
            base_classes=base_classes,
            parent_entity_id=self._current_module.id,
            line_start=node.lineno,
            line_end=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            docstring_sections=docstring_info,
        )
        
        # Add decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                class_entity.decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                class_entity.decorators.append(f"{self._get_attribute_name(decorator)}")
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    class_entity.decorators.append(f"{decorator.func.id}(...)")
                elif isinstance(decorator.func, ast.Attribute):
                    class_entity.decorators.append(f"{self._get_attribute_name(decorator.func)}(...)")
        
        # Save previous class and set current class
        previous_class = self._current_class
        self._current_class = class_entity
        
        # Parse class body
        for child_node in node.body:
            if isinstance(child_node, ast.Assign):
                # Handle class variables
                self._parse_assignment(child_node, is_class_var=True)
            elif isinstance(child_node, ast.AnnAssign):
                # Handle annotated class variables
                self._parse_annotated_assignment(child_node, is_class_var=True)
            else:
                # Parse other nodes
                self._parse_node(child_node)
        
        # Restore previous class
        self._current_class = previous_class
        
        # Add to module
        self._current_module.classes.append(class_entity)
        
        return class_entity
    
    def _parse_import(self, node: Union[ast.Import, ast.ImportFrom]) -> ImportEntity:
        """
        Parse an import statement and create an ImportEntity.
        
        Args:
            node: AST node for the import
            
        Returns:
            ImportEntity with all extracted information
        """
        if isinstance(node, ast.Import):
            # Handle regular imports: import module, import module as alias
            module_names = []
            for name in node.names:
                module_name = name.name
                alias = name.asname or module_name
                module_names.append(f"{module_name}{' as ' + alias if alias != module_name else ''}")
                
                # Track imported names
                self._imported_names[alias] = module_name
                
            import_entity = ImportEntity(
                module_name=", ".join(module_names),
                is_from=False,
                parent_entity_id=self._current_module.id,
                line_start=node.lineno,
                line_end=node.lineno,
            )
            
        else:  # ast.ImportFrom
            # Handle from imports: from module import name, from module import name as alias
            if node.module is None:
                # Handle relative imports: from . import name
                module_name = "."
            else:
                # Handle normal from imports: from module import name
                module_name = node.module
                
            # Add level dots for relative imports
            if node.level > 0:
                module_name = "." * node.level + module_name
                
            # Get imported names
            imported_names = []
            for name in node.names:
                imported_name = name.name
                alias = name.asname or imported_name
                imported_names.append(f"{imported_name}{' as ' + alias if alias != imported_name else ''}")
                
                # Track imported names
                if imported_name == "*":
                    # Can't track specific names with wildcard imports
                    pass
                else:
                    self._imported_names[alias] = f"{module_name}.{imported_name}"
                    
            import_entity = ImportEntity(
                module_name=module_name,
                imported_names=imported_names,
                is_from=True,
                parent_entity_id=self._current_module.id,
                line_start=node.lineno,
                line_end=node.lineno,
            )
            
        # Add to module
        self._current_module.imports.append(import_entity)
        
        return import_entity
    
    def _parse_assignment(self, node: ast.Assign, is_class_var: bool = False) -> Optional[VariableEntity]:
        """
        Parse an assignment statement and create a VariableEntity.
        
        Args:
            node: AST node for the assignment
            is_class_var: Whether this is a class variable
            
        Returns:
            VariableEntity with all extracted information or None
        """
        # Skip function-local variables if not configured to include them
        if not self.config.include_local_variables and not is_class_var and self._current_class:
            return None
            
        # Get the variable names from targets
        variable_names = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                variable_names.append(target.id)
            elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                # Handle tuple unpacking: a, b = 1, 2
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        variable_names.append(elt.id)
            # Add more complex target handling if needed
        
        if not variable_names:
            return None
            
        # Get value information (simplified)
        value_info = self._get_value_info(node.value)
        
        # Create variable entities
        result = None
        for name in variable_names:
            # Skip private variables if not configured to include them
            if not self.config.include_private_members and name.startswith("_"):
                continue
                
            variable_entity = VariableEntity(
                name=name,
                docstring="",  # Assignments don't have docstrings
                value=value_info,
                is_class_var=is_class_var,
                parent_entity_id=self._current_class.id if self._current_class else self._current_module.id,
                line_start=node.lineno,
                line_end=node.lineno,
            )
            
            # Add to parent
            if is_class_var and self._current_class:
                self._current_class.class_variables.append(variable_entity)
            else:
                self._current_module.variables.append(variable_entity)
                
            result = variable_entity
            
        return result
    
    def _parse_annotated_assignment(self, node: ast.AnnAssign, is_class_var: bool = False) -> Optional[VariableEntity]:
        """
        Parse an annotated assignment statement and create a VariableEntity.
        
        Args:
            node: AST node for the annotated assignment
            is_class_var: Whether this is a class variable
            
        Returns:
            VariableEntity with all extracted information or None
        """
        # Skip function-local variables if not configured to include them
        if not self.config.include_local_variables and not is_class_var and self._current_class:
            return None
            
        # Get the variable name
        if not isinstance(node.target, ast.Name):
            return None
            
        name = node.target.id
        
        # Skip private variables if not configured to include them
        if not self.config.include_private_members and name.startswith("_"):
            return None
            
        # Get type annotation
        type_info = self._parse_type_annotation(node.annotation)
        
        # Get value information (simplified)
        value_info = self._get_value_info(node.value) if node.value else None
        
        # Create variable entity
        variable_entity = VariableEntity(
            name=name,
            docstring="",  # Assignments don't have docstrings
            value=value_info,
            type_annotation=type_info,
            is_class_var=is_class_var,
            parent_entity_id=self._current_class.id if self._current_class else self._current_module.id,
            line_start=node.lineno,
            line_end=node.lineno,
        )
        
        # Add to parent
        if is_class_var and self._current_class:
            self._current_class.class_variables.append(variable_entity)
        else:
            self._current_module.variables.append(variable_entity)
            
        return variable_entity
    
    def _parse_arguments(self, args_node: ast.arguments) -> List[Argument]:
        """
        Parse function arguments and create Argument objects.
        
        Args:
            args_node: AST node for the arguments
            
        Returns:
            List of Argument objects
        """
        arguments = []
        
        # Handle positional-only arguments (Python 3.8+)
        if hasattr(args_node, 'posonlyargs'):
            for i, arg in enumerate(args_node.posonlyargs):
                name = arg.arg
                type_annotation = self._parse_type_annotation(arg.annotation) if arg.annotation else None
                default = None  # Default values are handled separately
                arguments.append(Argument(
                    name=name,
                    type_annotation=type_annotation,
                    default_value=default,
                    is_positional_only=True,
                    is_keyword_only=False,
                    is_variadic=False,
                ))
                
        # Handle regular positional arguments
        for i, arg in enumerate(args_node.args):
            name = arg.arg
            type_annotation = self._parse_type_annotation(arg.annotation) if arg.annotation else None
            default = None  # Default values are handled separately
            
            # Skip 'self' or 'cls' for methods
            if i == 0 and self._current_class and name in ('self', 'cls'):
                continue
                
            arguments.append(Argument(
                name=name,
                type_annotation=type_annotation,
                default_value=default,
                is_positional_only=False,
                is_keyword_only=False,
                is_variadic=False,
            ))
            
        # Handle keyword-only arguments
        for arg in args_node.kwonlyargs:
            name = arg.arg
            type_annotation = self._parse_type_annotation(arg.annotation) if arg.annotation else None
            default = None  # Default values are handled separately
            arguments.append(Argument(
                name=name,
                type_annotation=type_annotation,
                default_value=default,
                is_positional_only=False,
                is_keyword_only=True,
                is_variadic=False,
            ))
            
        # Handle variadic positional arguments (*args)
        if args_node.vararg:
            name = args_node.vararg.arg
            type_annotation = self._parse_type_annotation(args_node.vararg.annotation) if args_node.vararg.annotation else None
            arguments.append(Argument(
                name=name,
                type_annotation=type_annotation,
                default_value=None,
                is_positional_only=False,
                is_keyword_only=False,
                is_variadic=True,
                is_variadic_positional=True,
            ))
            
        # Handle variadic keyword arguments (**kwargs)
        if args_node.kwarg:
            name = args_node.kwarg.arg
            type_annotation = self._parse_type_annotation(args_node.kwarg.annotation) if args_node.kwarg.annotation else None
            arguments.append(Argument(
                name=name,
                type_annotation=type_annotation,
                default_value=None,
                is_positional_only=False,
                is_keyword_only=False,
                is_variadic=True,
                is_variadic_keyword=True,
            ))
            
        # Add default values
        # Note: Default values for positional args are stored in defaults, 
        # while defaults for keyword-only args are stored in kw_defaults
        
        # Handle positional arg defaults
        pos_defaults_offset = len(args_node.args) - len(args_node.defaults)
        for i, default in enumerate(args_node.defaults):
            arg_idx = i + pos_defaults_offset
            if arg_idx < len(arguments):
                arguments[arg_idx].default_value = self._get_value_info(default)
                
        # Handle keyword-only arg defaults
        for i, (arg, default) in enumerate(zip(args_node.kwonlyargs, args_node.kw_defaults)):
            if default and i < len(arguments) - len(args_node.args):
                kw_idx = len(args_node.args) + i
                if kw_idx < len(arguments):
                    arguments[kw_idx].default_value = self._get_value_info(default)
                    
        return arguments
    
    def _parse_type_annotation(self, node: Optional[ast.AST]) -> Optional[TypeInfo]:
        """
        Parse a type annotation AST node.
        
        Args:
            node: AST node for the type annotation
            
        Returns:
            TypeInfo object with the parsed type information or None
        """
        if node is None:
            return None
            
        if isinstance(node, ast.Name):
            # Simple type: int, str, etc.
            return TypeInfo(name=node.id)
            
        elif isinstance(node, ast.Attribute):
            # Dotted type: module.Type
            return TypeInfo(name=self._get_attribute_name(node))
            
        elif isinstance(node, ast.Subscript):
            # Generic type: List[str], Dict[str, int], etc.
            if isinstance(node.value, ast.Name):
                container_type = node.value.id
            elif isinstance(node.value, ast.Attribute):
                container_type = self._get_attribute_name(node.value)
            else:
                container_type = "Unknown"
                
            # Get the type arguments (changed in Python 3.9)
            type_args = []
            if hasattr(node, 'slice') and isinstance(node.slice, ast.Index):
                # Python 3.8 and earlier
                if isinstance(node.slice.value, ast.Tuple):
                    # Multiple type args: Dict[str, int]
                    for elt in node.slice.value.elts:
                        arg_type = self._parse_type_annotation(elt)
                        if arg_type:
                            type_args.append(arg_type)
                else:
                    # Single type arg: List[str]
                    arg_type = self._parse_type_annotation(node.slice.value)
                    if arg_type:
                        type_args.append(arg_type)
            elif hasattr(node, 'slice') and isinstance(node.slice, ast.Tuple):
                # Python 3.9+, multiple type args: Dict[str, int]
                for elt in node.slice.elts:
                    arg_type = self._parse_type_annotation(elt)
                    if arg_type:
                        type_args.append(arg_type)
            else:
                # Python 3.9+, single type arg: List[str]
                arg_type = self._parse_type_annotation(node.slice)
                if arg_type:
                    type_args.append(arg_type)
                    
            return TypeInfo(
                name=container_type,
                is_container=True,
                container_types=type_args,
            )
            
        elif isinstance(node, ast.Constant) and node.value is None:
            # Handle None type
            return TypeInfo(name="None")
            
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Union type (old style): str | int
            left_type = self._parse_type_annotation(node.left)
            right_type = self._parse_type_annotation(node.right)
            return TypeInfo(
                name="Union",
                is_container=True,
                container_types=[t for t in [left_type, right_type] if t is not None],
            )
            
        # Add more type annotation handling as needed
        
        # Fall back to string representation
        return TypeInfo(name=ast.unparse(node) if hasattr(ast, 'unparse') else "Unknown")
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """
        Get the full name of an attribute node (e.g., module.submodule.name).
        
        Args:
            node: AST attribute node
            
        Returns:
            Full attribute name
        """
        parts = []
        current = node
        
        # Build the name from right to left
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
            
        if isinstance(current, ast.Name):
            parts.append(current.id)
            
        # Reverse and join the parts
        return ".".join(reversed(parts))
    
    def _get_value_info(self, node: ast.AST) -> str:
        """
        Get a string representation of a value AST node.
        
        Args:
            node: AST node for a value
            
        Returns:
            String representation of the value
        """
        if isinstance(node, ast.Constant):
            if node.value is None:
                return "None"
            elif isinstance(node.value, str):
                # For long strings, truncate
                if len(node.value) > 50:
                    return f'"{node.value[:47]}..."'
                return repr(node.value)
            else:
                return str(node.value)
                
        elif isinstance(node, ast.List):
            return "[...]"
            
        elif isinstance(node, ast.Dict):
            return "{...}"
            
        elif isinstance(node, ast.Tuple):
            return "(...)"
            
        elif isinstance(node, ast.Set):
            return "{...}"
            
        elif isinstance(node, ast.Name):
            return node.id
            
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f"{node.func.id}(...)"
            elif isinstance(node.func, ast.Attribute):
                return f"{self._get_attribute_name(node.func)}(...)"
            else:
                return "(...)"
                
        # Add more value type handling as needed
        
        # Fall back to a generic string
        try:
            if hasattr(ast, 'unparse'):
                # Python 3.9+ has ast.unparse
                return ast.unparse(node)
            else:
                # Fallback for earlier versions
                return f"<{type(node).__name__}>"
        except Exception:
            return f"<{type(node).__name__}>"

    def parse_module_dependencies(self, module_entity: ModuleEntity) -> None:
        """
        Parse dependencies for a module from its import statements.

        Args:
            module_entity: The module entity to parse dependencies for
        """
        # Implementation remains the same
        pass

    def parse_directory(self, dir_path: Union[str, Path]) -> List[Entity]:
        """
        Parse all Python files in a directory and its subdirectories.
        
        Args:
            dir_path: Path to the directory to parse
            
        Returns:
            List of entities parsed from all files
        """
        dir_path = Path(dir_path)
        if not dir_path.exists():
            raise ValueError(f"Directory does not exist: {dir_path}")
            
        entities = []
        
        # Walk through the directory and parse each Python file
        for root, _, files in os.walk(dir_path):
            for file in files:
                if not file.endswith(tuple(self.FILE_EXTENSIONS)):
                    continue
                    
                file_path = Path(root) / file
                
                try:
                    logger.info(f"Parsing file: {file_path}")
                    module = self.parse_file(file_path)
                    
                    # Add module entity
                    entities.append(module)
                    
                    # Add class entities
                    entities.extend(module.classes)
                    
                    # Add function entities
                    entities.extend(module.functions)
                    
                    # Add variable entities
                    entities.extend(module.variables)
                    
                except Exception as e:
                    logger.error(f"Error parsing file {file_path}: {str(e)}")
        
        logger.info(f"Parsed {len(entities)} entities from directory: {dir_path}")
        return entities


# Register the parser with the parser registry
def register_parser():
    """Register the Python parser in the parser registry."""
    from ..core.parser_registry import ParserRegistry
    ParserRegistry.register(PythonParser) 