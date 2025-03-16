#!/usr/bin/env python3
"""
Markdown documentation generator for CodeDoc.

This module provides a generator for exporting parsed code entities to Markdown
documentation format, which is widely used for developer documentation.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ..core.entities import (
    Argument, ClassEntity, Entity, FunctionEntity, ImportEntity,
    ModuleEntity, TypeInfo, VariableEntity
)
from .base_generator import BaseGenerator, GeneratorConfig

logger = logging.getLogger(__name__)


class MarkdownConfig(GeneratorConfig):
    """
    Configuration for the Markdown generator.
    """
    
    def __init__(
        self,
        include_private: bool = False,
        include_docstrings: bool = True,
        include_source: bool = False,
        include_inheritance: bool = True,
        include_references: bool = True,
        include_metadata: bool = True,
        include_toc: bool = True,
        entity_types: Optional[List[str]] = None
    ):
        """
        Initialize the Markdown configuration.
        
        Args:
            include_private: Whether to include private entities (starting with _)
            include_docstrings: Whether to include docstrings
            include_source: Whether to include source code
            include_inheritance: Whether to include inheritance information
            include_references: Whether to include references to other entities
            include_metadata: Whether to include metadata like file paths
            include_toc: Whether to include a table of contents
            entity_types: List of entity types to include (e.g. ["module", "class", "function"])
        """
        super().__init__(
            include_private=include_private,
            include_docstrings=include_docstrings,
            include_source=include_source,
            entity_types=entity_types or ["module", "class", "function", "variable"]
        )
        self.include_inheritance = include_inheritance
        self.include_references = include_references
        self.include_metadata = include_metadata
        self.include_toc = include_toc


class MarkdownGenerator(BaseGenerator):
    """
    Generator for Markdown documentation.
    
    This generator converts parsed code entities to Markdown documentation,
    which is a lightweight markup language widely used for developer
    documentation.
    """
    
    FORMAT = "markdown"
    FILE_EXTENSION = ".md"
    
    def __init__(self, config: Optional[MarkdownConfig] = None):
        """
        Initialize the Markdown generator.
        
        Args:
            config: Configuration for the generator
        """
        self.config = config or MarkdownConfig()
        self.processed_entities = set()
        
    def generate_documentation(
        self, 
        entity: Entity, 
        output_dir: Union[str, Path],
        relative_path: Optional[str] = None
    ) -> Path:
        """
        Generate Markdown documentation for an entity.
        
        Args:
            entity: The entity to generate documentation for
            output_dir: Directory where documentation should be saved
            relative_path: Optional relative path within output_dir
            
        Returns:
            Path to the generated documentation file
            
        Raises:
            ValueError: If documentation cannot be generated
        """
        output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Skip if we shouldn't include this entity
        if not self._should_include_entity(entity):
            return output_dir
        
        # Mark this entity as processed
        self.processed_entities.add(entity.id)
        
        # Generate markdown content based on entity type
        if isinstance(entity, ModuleEntity):
            content = self._generate_module_documentation(entity)
        elif isinstance(entity, ClassEntity):
            content = self._generate_class_documentation(entity)
        elif isinstance(entity, FunctionEntity):
            content = self._generate_function_documentation(entity)
        else:
            # Default handling for other entity types
            content = self._generate_generic_documentation(entity)
        
        # Get the output path for this entity
        output_path = self._get_output_path(entity, output_dir, relative_path)
        
        # Write the content to the file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Process child entities if this is a container
        if isinstance(entity, ModuleEntity):
            # Process classes and functions
            for class_entity in entity.classes:
                # Skip if we shouldn't include this entity
                if not self._should_include_entity(class_entity):
                    continue
                
                # Generate documentation for the class
                self.generate_documentation(
                    class_entity, 
                    output_dir, 
                    Path(output_path).parent.relative_to(output_dir)
                )
                
            # Only generate separate files for top-level functions
            for func_entity in entity.functions:
                # Skip if we shouldn't include this entity
                if not self._should_include_entity(func_entity):
                    continue
                
                # Generate documentation for the function
                self.generate_documentation(
                    func_entity, 
                    output_dir, 
                    Path(output_path).parent.relative_to(output_dir)
                )
        
        return output_path
    
    def generate_index(
        self,
        entities: List[Entity],
        output_dir: Union[str, Path],
        title: str = "API Documentation"
    ) -> Path:
        """
        Generate an index page for a list of entities.
        
        Args:
            entities: List of entities to include in the index
            output_dir: Directory where the index should be saved
            title: Title for the index page
            
        Returns:
            Path to the generated index file
        """
        output_dir_path = Path(output_dir) if isinstance(output_dir, str) else output_dir
        if not output_dir_path.exists():
            output_dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create index content
        content = f"# {title}\n\n"
        content += "## Table of Contents\n\n"
        
        # Add modules section
        modules = [entity for entity in entities if isinstance(entity, ModuleEntity)]
        
        if modules:
            content += "### Modules\n\n"
            for module in modules:
                module_path = self._get_relative_path(
                    self._get_output_path(module, output_dir_path),
                    output_dir_path / "index.md"
                )
                content += f"- [`{module.name}`]({module_path})\n"
            content += "\n"
        
        # Collect all classes
        all_classes = []
        
        # First collect classes from modules
        for module in modules:
            for cls in module.classes:
                # Skip private classes if not configured to include them
                if not self.config.include_private and cls.name.startswith("_"):
                    continue
                all_classes.append(cls)
        
        # Then add classes that were passed directly
        for entity in entities:
            if isinstance(entity, ClassEntity) and entity not in all_classes:
                # Skip private classes if not configured to include them
                if not self.config.include_private and entity.name.startswith("_"):
                    continue
                all_classes.append(entity)
        
        # Add classes section
        if all_classes:
            content += "### Classes\n\n"
            for cls in all_classes:
                cls_path = self._get_relative_path(
                    self._get_output_path(cls, output_dir_path),
                    output_dir_path / "index.md"
                )
                content += f"- [`{cls.name}`]({cls_path})\n"
            content += "\n"
        
        # Collect all functions (excluding methods)
        all_functions = []
        
        # First collect functions from modules
        for module in modules:
            for func in module.functions:
                # Skip methods
                if func.is_method:
                    continue
                # Skip private functions if not configured to include them
                if not self.config.include_private and func.name.startswith("_"):
                    continue
                all_functions.append(func)
        
        # Then add functions that were passed directly
        for entity in entities:
            if isinstance(entity, FunctionEntity) and not entity.is_method and entity not in all_functions:
                # Skip private functions if not configured to include them
                if not self.config.include_private and entity.name.startswith("_"):
                    continue
                all_functions.append(entity)
        
        # Add functions section
        if all_functions:
            content += "### Functions\n\n"
            for func in all_functions:
                func_path = self._get_relative_path(
                    self._get_output_path(func, output_dir_path),
                    output_dir_path / "index.md"
                )
                content += f"- [`{func.name}`]({func_path})\n"
            content += "\n"
        
        # Write index file
        index_path = output_dir_path / "index.md"
        with open(index_path, "w") as f:
            f.write(content)
            
        return index_path
    
    def _generate_module_documentation(self, module: ModuleEntity) -> str:
        """
        Generate documentation for a module.
        
        Args:
            module: The module entity to document
            
        Returns:
            Markdown documentation for the module
        """
        # Header with module name
        content = f"# Module `{module.name}`\n\n"
        
        # Add file path if available
        if module.file_path and self.config.include_metadata:
            content += f"**File:** `{module.file_path}`\n\n"
        
        # Add docstring if available
        if module.docstring:
            content += f"{module.docstring.strip()}\n\n"
        
        # Add imports section if there are imports
        if module.imports and self.config.include_references:
            content += "## Imports\n\n"
            content += "```python\n"
            for imp in module.imports:
                if imp.is_from:
                    imported_names = ", ".join(imp.imported_names or [])
                    content += f"from {imp.module_name} import {imported_names}\n"
                else:
                    content += f"import {imp.module_name}\n"
            content += "```\n\n"
        
        # Add variables section if there are variables
        filtered_variables = []
        for var in module.variables:
            # Include all variables if include_private is True
            if self.config.include_private or not var.name.startswith("_"):
                filtered_variables.append(var)
        
        if filtered_variables:
            content += "## Variables\n\n"
            for var in filtered_variables:
                type_str = f": `{var.type_annotation.name}`" if var.type_annotation else ""
                value_str = f" = `{var.value}`" if var.value else ""
                content += f"### `{var.name}`{type_str}{value_str}\n\n"
                if var.docstring:
                    content += f"{var.docstring.strip()}\n\n"
        
        # Add classes section
        filtered_classes = [c for c in module.classes if self._should_include_entity(c)]
        if filtered_classes:
            content += "## Classes\n\n"
            for cls in filtered_classes:
                # Class name with link to class documentation
                cls_path = self._get_relative_path(
                    self._get_output_path(cls, Path(module.file_path).parent if module.file_path else Path()),
                    self._get_output_path(module, Path(module.file_path).parent if module.file_path else Path())
                )
                content += f"### [`{cls.name}`]({cls_path})\n\n"
                
                # Add inheritance if available
                if cls.base_classes and self.config.include_inheritance:
                    base_classes_str = ", ".join([f"`{base}`" for base in cls.base_classes])
                    content += f"Inherits from: {base_classes_str}\n\n"
                
                # Add class summary
                if cls.docstring:
                    content += f"{self._get_summary(cls.docstring)}\n\n"
                
                # List methods
                filtered_methods = [m for m in cls.methods if self._should_include_entity(m)]
                if filtered_methods:
                    content += "#### Methods\n\n"
                    for method in filtered_methods:
                        method_str = self._format_function_signature(method)
                        content += f"- `{method_str}`\n"
                    content += "\n"
        
        # Add functions section
        filtered_functions = [f for f in module.functions if self._should_include_entity(f)]
        if filtered_functions:
            content += "## Functions\n\n"
            for func in filtered_functions:
                # Function name with link to function documentation
                func_path = self._get_relative_path(
                    self._get_output_path(func, Path(module.file_path).parent if module.file_path else Path()),
                    self._get_output_path(module, Path(module.file_path).parent if module.file_path else Path())
                )
                content += f"### [`{func.name}`]({func_path})\n\n"
                
                # Add function signature
                func_str = self._format_function_signature(func)
                content += f"```python\n{func_str}\n```\n\n"
                
                # Add function summary
                if func.docstring:
                    content += f"{self._get_summary(func.docstring)}\n\n"
        
        return content
    
    def _generate_class_documentation(self, cls: ClassEntity) -> str:
        """
        Generate documentation for a class.
        
        Args:
            cls: The class entity to document
            
        Returns:
            Markdown documentation for the class
        """
        # Header with class name
        content = f"# Class `{cls.name}`\n\n"
        
        # Add metadata if available
        if self.config.include_metadata:
            if cls.file_path:
                content += f"**File:** `{cls.file_path}`\n\n"
            if cls.line_start and cls.line_end:
                content += f"**Lines:** {cls.line_start}-{cls.line_end}\n\n"
        
        # Add inheritance if available
        if cls.base_classes and self.config.include_inheritance:
            base_classes_str = ", ".join([f"`{base}`" for base in cls.base_classes])
            content += f"**Inherits from:** {base_classes_str}\n\n"
        
        # Add decorators if available
        if cls.decorators:
            decorators_str = "\n".join([f"@{d}" for d in cls.decorators])
            content += f"**Decorators:**\n```python\n{decorators_str}\n```\n\n"
        
        # Add docstring if available
        if cls.docstring:
            content += f"{cls.docstring.strip()}\n\n"
        
        # Add class variables
        if cls.class_variables:
            content += "## Class Variables\n\n"
            for var in cls.class_variables:
                type_str = f": `{var.type_annotation.name}`" if var.type_annotation else ""
                value_str = f" = `{var.value}`" if var.value else ""
                content += f"### `{var.name}`{type_str}{value_str}\n\n"
                if var.docstring:
                    content += f"{var.docstring.strip()}\n\n"
        
        # Add methods section
        if cls.methods:
            # Group methods by type
            init_methods = [m for m in cls.methods if m.name == "__init__"]
            properties = [m for m in cls.methods if m.is_property]
            class_methods = [m for m in cls.methods if m.is_class_method]
            static_methods = [m for m in cls.methods if m.is_static]
            regular_methods = [
                m for m in cls.methods 
                if not m.is_property and not m.is_class_method and not m.is_static and m.name != "__init__"
            ]
            
            # Constructor
            if init_methods:
                content += "## Constructor\n\n"
                for method in init_methods:
                    content += self._format_method_documentation(method)
            
            # Properties
            if properties:
                content += "## Properties\n\n"
                for method in properties:
                    content += self._format_method_documentation(method)
            
            # Class methods
            if class_methods:
                content += "## Class Methods\n\n"
                for method in class_methods:
                    content += self._format_method_documentation(method)
            
            # Static methods
            if static_methods:
                content += "## Static Methods\n\n"
                for method in static_methods:
                    content += self._format_method_documentation(method)
            
            # Instance methods
            if regular_methods:
                content += "## Methods\n\n"
                for method in regular_methods:
                    content += self._format_method_documentation(method)
        
        return content
    
    def _generate_function_documentation(self, func: FunctionEntity) -> str:
        """
        Generate documentation for a function.
        
        Args:
            func: The function entity to document
            
        Returns:
            Markdown documentation for the function
        """
        # Header with function name
        content = f"# {'Method' if func.is_method else 'Function'} `{func.name}`\n\n"
        
        # Add metadata if available
        if self.config.include_metadata:
            if func.file_path:
                content += f"**File:** `{func.file_path}`\n\n"
            if func.line_start and func.line_end:
                content += f"**Lines:** {func.line_start}-{func.line_end}\n\n"
        
        # Add special method types
        method_types = []
        if func.is_property:
            method_types.append("Property")
        if func.is_class_method:
            method_types.append("Class Method")
        if func.is_static:
            method_types.append("Static Method")
        
        if method_types:
            content += f"**Type:** {', '.join(method_types)}\n\n"
        
        # Add decorators if available
        if func.decorators:
            decorators_str = "\n".join([f"@{d}" for d in func.decorators])
            content += f"**Decorators:**\n```python\n{decorators_str}\n```\n\n"
        
        # Add function signature
        func_str = self._format_function_signature(func)
        content += f"## Signature\n\n```python\n{func_str}\n```\n\n"
        
        # Add docstring if available
        if func.docstring:
            content += f"## Description\n\n{func.docstring.strip()}\n\n"
        
        # Add parameters section if there are arguments
        if func.arguments and self.config.include_types:
            content += "## Parameters\n\n"
            
            # Check if we have parameter descriptions in the docstring
            has_param_docs = False
            param_docs = {}
            if "args" in func.docstring_sections:
                has_param_docs = True
                # Create a mapping of parameter name to description
                for param in func.docstring_sections["args"]:
                    if "name" in param:
                        param_docs[param["name"]] = param.get("description", "")
            
            # Add each parameter
            for arg in func.arguments:
                # Skip self parameter for methods
                if func.is_method and arg.name == "self":
                    continue
                
                # Skip cls parameter for class methods
                if func.is_class_method and arg.name == "cls":
                    continue
                
                # Parameter name and type
                param_type = f": `{arg.type_annotation.name}`" if arg.type_annotation else ""
                default_value = f" = `{arg.default_value}`" if arg.default_value else ""
                
                # Format special parameter types
                param_prefix = ""
                if arg.is_variadic_positional:
                    param_prefix = "*"
                elif arg.is_variadic_keyword:
                    param_prefix = "**"
                
                content += f"### `{param_prefix}{arg.name}`{param_type}{default_value}\n\n"
                
                # Add parameter description if available
                if has_param_docs and arg.name in param_docs:
                    content += f"{param_docs[arg.name]}\n\n"
        
        # Add return type section if available
        if func.return_type and self.config.include_types:
            content += "## Returns\n\n"
            content += f"`{self._format_type(func.return_type)}`\n\n"
            
            # Add return description if available
            if "returns" in func.docstring_sections:
                for ret in func.docstring_sections["returns"]:
                    if "description" in ret:
                        content += f"{ret['description']}\n\n"
        
        # Add exceptions/raises section if available
        if "raises" in func.docstring_sections:
            content += "## Raises\n\n"
            for exc in func.docstring_sections["raises"]:
                exc_name = exc.get("name", "Exception")
                exc_desc = exc.get("description", "")
                content += f"### `{exc_name}`\n\n{exc_desc}\n\n"
        
        # Add examples section if available
        if "examples" in func.docstring_sections and self.config.include_examples:
            content += "## Examples\n\n"
            for example in func.docstring_sections["examples"]:
                if isinstance(example, dict) and "description" in example:
                    content += f"{example['description']}\n\n"
                else:
                    content += f"{example}\n\n"
        
        return content
    
    def _generate_generic_documentation(self, entity: Entity) -> str:
        """
        Generate documentation for a generic entity.
        
        Args:
            entity: The entity to document
            
        Returns:
            Markdown documentation for the entity
        """
        # Header with entity name and type
        entity_type = entity.__class__.__name__.replace("Entity", "")
        content = f"# {entity_type} `{entity.name}`\n\n"
        
        # Add metadata if available
        if self.config.include_metadata:
            if entity.file_path:
                content += f"**File:** `{entity.file_path}`\n\n"
            if entity.line_start and entity.line_end:
                content += f"**Lines:** {entity.line_start}-{entity.line_end}\n\n"
        
        # Add docstring if available
        if entity.docstring:
            content += f"{entity.docstring.strip()}\n\n"
        
        return content
    
    def _format_method_documentation(self, method: FunctionEntity) -> str:
        """
        Format documentation for a method.
        
        Args:
            method: The method to document
            
        Returns:
            Formatted method documentation
        """
        content = f"### `{method.name}`\n\n"
        
        # Add method signature
        method_str = self._format_function_signature(method)
        content += f"```python\n{method_str}\n```\n\n"
        
        # Add docstring if available
        if method.docstring:
            content += f"{method.docstring.strip()}\n\n"
        
        # Add parameters if available and configured
        if method.arguments and self.config.include_types:
            content += "#### Parameters\n\n"
            
            # Check if we have parameter descriptions in the docstring
            has_param_docs = False
            param_docs = {}
            if "args" in method.docstring_sections:
                has_param_docs = True
                # Create a mapping of parameter name to description
                for param in method.docstring_sections["args"]:
                    if "name" in param:
                        param_docs[param["name"]] = param.get("description", "")
            
            # Add each parameter (skip self/cls)
            for arg in method.arguments:
                if arg.name in ("self", "cls") and (method.is_method or method.is_class_method):
                    continue
                
                # Parameter name and type
                param_type = f": `{arg.type_annotation.name}`" if arg.type_annotation else ""
                default_value = f" = `{arg.default_value}`" if arg.default_value else ""
                
                # Format special parameter types
                param_prefix = ""
                if arg.is_variadic_positional:
                    param_prefix = "*"
                elif arg.is_variadic_keyword:
                    param_prefix = "**"
                
                content += f"- `{param_prefix}{arg.name}`{param_type}{default_value}"
                
                # Add parameter description if available
                if has_param_docs and arg.name in param_docs:
                    content += f": {param_docs[arg.name]}"
                
                content += "\n"
            
            content += "\n"
        
        # Add return type if available
        if method.return_type and self.config.include_types:
            content += "#### Returns\n\n"
            content += f"`{self._format_type(method.return_type)}`"
            
            # Add return description if available
            if "returns" in method.docstring_sections:
                for ret in method.docstring_sections["returns"]:
                    if "description" in ret:
                        content += f": {ret['description']}"
            
            content += "\n\n"
        
        return content
    
    def _format_function_signature(self, func: FunctionEntity) -> str:
        """
        Format a function signature.
        
        Args:
            func: The function to format
            
        Returns:
            Formatted function signature
        """
        # Start with the function name
        if func.is_method:
            # For methods, include the self parameter
            signature = f"def {func.name}(self"
            # Skip the first argument (self) when adding other arguments
            args = func.arguments[1:] if func.arguments else []
        elif func.is_class_method:
            # For class methods, include the cls parameter
            signature = f"def {func.name}(cls"
            # Skip the first argument (cls) when adding other arguments
            args = func.arguments[1:] if func.arguments else []
        else:
            # For regular functions, don't include self/cls
            signature = f"def {func.name}("
            args = func.arguments
        
        # Add arguments
        if args:
            if func.is_method or func.is_class_method:
                signature += ", "
            
            args_strs = []
            for arg in args:
                arg_str = ""
                
                # Add variadic markers if needed
                if arg.is_variadic_positional:
                    arg_str += "*"
                elif arg.is_variadic_keyword:
                    arg_str += "**"
                
                # Add argument name
                arg_str += arg.name
                
                # Add type annotation if available
                if arg.type_annotation and self.config.include_types:
                    arg_str += f": {self._format_type(arg.type_annotation)}"
                
                # Add default value if available
                if arg.default_value:
                    arg_str += f" = {arg.default_value}"
                
                args_strs.append(arg_str)
            
            signature += ", ".join(args_strs)
        
        signature += ")"
        
        # Add return type if available
        if func.return_type and self.config.include_types:
            signature += f" -> {self._format_type(func.return_type)}"
        
        return signature
    
    def _format_type(self, type_info: TypeInfo) -> str:
        """
        Format a type annotation.
        
        Args:
            type_info: The type information to format
            
        Returns:
            Formatted type annotation
        """
        if not type_info.is_container or not type_info.container_types:
            return type_info.name
        
        # Format container types
        container_types_str = ", ".join(
            self._format_type(t) for t in type_info.container_types
        )
        
        return f"{type_info.name}[{container_types_str}]"
    
    def _get_summary(self, docstring: str) -> str:
        """
        Get a summary of a docstring (first paragraph).
        
        Args:
            docstring: The docstring to summarize
            
        Returns:
            First paragraph of the docstring
        """
        if not docstring:
            return ""
        
        # Get the first paragraph (up to the first blank line)
        paragraphs = docstring.strip().split("\n\n")
        if paragraphs:
            return paragraphs[0]
        
        return ""
    
    def _get_relative_path(self, target_path: Path, source_path: Path) -> str:
        """
        Get a relative path from source to target.
        
        Args:
            target_path: Target path
            source_path: Source path
            
        Returns:
            Relative path from source to target
        """
        try:
            return os.path.relpath(target_path, source_path.parent)
        except ValueError:
            # On different drives (Windows), use the absolute path
            return str(target_path)


def register_generator():
    """Register the Markdown generator with the registry."""
    from .generator_registry import GeneratorRegistry
    GeneratorRegistry.register(MarkdownGenerator) 