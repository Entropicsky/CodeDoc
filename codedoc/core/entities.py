#!/usr/bin/env python3
"""
Core entities for the CodeDoc framework.

This module defines the data structures used to represent code entities such as
modules, classes, functions, and variables. These entities form the basis of the
documentation and analysis capabilities of the CodeDoc framework.
"""

import uuid
from typing import Any, Dict, List, Optional, Union

class Entity:
    """
    Base class for all code entities.
    
    This class provides common attributes and methods for all code entities
    such as modules, classes, functions, and variables.
    """
    
    def __init__(
        self,
        name: str,
        docstring: str = "",
        parent_entity_id: Optional[str] = None,
        line_start: int = 0,
        line_end: int = 0,
        file_path: Optional[str] = None,
        docstring_sections: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a code entity.
        
        Args:
            name: Name of the entity
            docstring: Documentation string for the entity
            parent_entity_id: ID of the parent entity (if any)
            line_start: Starting line number in the source file
            line_end: Ending line number in the source file
            file_path: Path to the source file
            docstring_sections: Parsed sections from the docstring
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.docstring = docstring
        self.parent_entity_id = parent_entity_id
        self.line_start = line_start
        self.line_end = line_end
        self.file_path = file_path
        self.docstring_sections = docstring_sections or {}
        self.references: List[EntityReference] = []
    
    def add_reference(self, reference: 'EntityReference') -> None:
        """
        Add a reference to another entity.
        
        Args:
            reference: Reference to another entity
        """
        self.references.append(reference)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the entity to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the entity
        """
        result = {
            "id": self.id,
            "name": self.name,
            "type": self.__class__.__name__,
            "docstring": self.docstring,
            "parent_entity_id": self.parent_entity_id,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "file_path": self.file_path,
            "docstring_sections": self.docstring_sections,
            "references": [ref.to_dict() for ref in self.references],
        }
        return result

class EntityReference:
    """Reference between entities."""
    
    def __init__(
        self,
        source_id: str,
        target_id: str,
        reference_type: str,
        description: str = ""
    ):
        """
        Initialize an entity reference.
        
        Args:
            source_id: ID of the source entity
            target_id: ID of the target entity
            reference_type: Type of reference (e.g., "imports", "inherits", "calls")
            description: Description of the reference
        """
        self.source_id = source_id
        self.target_id = target_id
        self.reference_type = reference_type
        self.description = description
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convert the reference to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the reference
        """
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "reference_type": self.reference_type,
            "description": self.description,
        }

class TypeInfo:
    """Information about a type annotation."""
    
    def __init__(
        self,
        name: str,
        is_container: bool = False,
        container_types: Optional[List['TypeInfo']] = None,
    ):
        """
        Initialize type information.
        
        Args:
            name: Name of the type
            is_container: Whether this is a container type (e.g., List, Dict)
            container_types: Types contained in this container
        """
        self.name = name
        self.is_container = is_container
        self.container_types = container_types or []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the type info to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the type info
        """
        return {
            "name": self.name,
            "is_container": self.is_container,
            "container_types": [t.to_dict() for t in self.container_types],
        }

class Argument:
    """Function or method argument information."""
    
    def __init__(
        self,
        name: str,
        type_annotation: Optional[TypeInfo] = None,
        default_value: Optional[str] = None,
        is_positional_only: bool = False,
        is_keyword_only: bool = False,
        is_variadic: bool = False,
        is_variadic_positional: bool = False,
        is_variadic_keyword: bool = False,
    ):
        """
        Initialize argument information.
        
        Args:
            name: Name of the argument
            type_annotation: Type annotation if available
            default_value: Default value as a string if available
            is_positional_only: Whether this is a positional-only argument
            is_keyword_only: Whether this is a keyword-only argument
            is_variadic: Whether this is a variadic argument (*args or **kwargs)
            is_variadic_positional: Whether this is a *args argument
            is_variadic_keyword: Whether this is a **kwargs argument
        """
        self.name = name
        self.type_annotation = type_annotation
        self.default_value = default_value
        self.is_positional_only = is_positional_only
        self.is_keyword_only = is_keyword_only
        self.is_variadic = is_variadic
        self.is_variadic_positional = is_variadic_positional
        self.is_variadic_keyword = is_variadic_keyword
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the argument to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the argument
        """
        return {
            "name": self.name,
            "type_annotation": self.type_annotation.to_dict() if self.type_annotation else None,
            "default_value": self.default_value,
            "is_positional_only": self.is_positional_only,
            "is_keyword_only": self.is_keyword_only,
            "is_variadic": self.is_variadic,
            "is_variadic_positional": self.is_variadic_positional,
            "is_variadic_keyword": self.is_variadic_keyword,
        }

class Property:
    """Class property information."""
    
    def __init__(
        self,
        name: str,
        type_annotation: Optional[TypeInfo] = None,
        docstring: str = "",
        getter: Optional[str] = None,
        setter: Optional[str] = None,
        deleter: Optional[str] = None,
    ):
        """
        Initialize property information.
        
        Args:
            name: Name of the property
            type_annotation: Type annotation if available
            docstring: Documentation string for the property
            getter: Name of the getter method
            setter: Name of the setter method
            deleter: Name of the deleter method
        """
        self.name = name
        self.type_annotation = type_annotation
        self.docstring = docstring
        self.getter = getter
        self.setter = setter
        self.deleter = deleter
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the property to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the property
        """
        return {
            "name": self.name,
            "type_annotation": self.type_annotation.to_dict() if self.type_annotation else None,
            "docstring": self.docstring,
            "getter": self.getter,
            "setter": self.setter,
            "deleter": self.deleter,
        }

class ModuleEntity(Entity):
    """
    Represents a module (Python file, JavaScript file, etc.).
    
    A module contains functions, classes, variables, and imports.
    """
    
    def __init__(
        self,
        name: str,
        docstring: str = "",
        file_path: Optional[str] = None,
        line_start: int = 0,
        line_end: int = 0,
        docstring_sections: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a module entity.
        
        Args:
            name: Name of the module
            docstring: Documentation string for the module
            file_path: Path to the module file
            line_start: Starting line number in the source file
            line_end: Ending line number in the source file
            docstring_sections: Parsed sections from the docstring
        """
        super().__init__(
            name=name,
            docstring=docstring,
            parent_entity_id=None,
            line_start=line_start,
            line_end=line_end,
            file_path=file_path,
            docstring_sections=docstring_sections,
        )
        self.imports: List[ImportEntity] = []
        self.functions: List[FunctionEntity] = []
        self.classes: List[ClassEntity] = []
        self.variables: List[VariableEntity] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the module to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the module
        """
        result = super().to_dict()
        result.update({
            "imports": [imp.to_dict() for imp in self.imports],
            "functions": [func.to_dict() for func in self.functions],
            "classes": [cls.to_dict() for cls in self.classes],
            "variables": [var.to_dict() for var in self.variables],
        })
        return result

class ImportEntity(Entity):
    """Represents an import statement."""
    
    def __init__(
        self,
        module_name: str,
        imported_names: Optional[List[str]] = None,
        is_from: bool = False,
        parent_entity_id: Optional[str] = None,
        line_start: int = 0,
        line_end: int = 0,
    ):
        """
        Initialize an import entity.
        
        Args:
            module_name: Name of the imported module
            imported_names: List of imported names (for from imports)
            is_from: Whether this is a "from ... import ..." statement
            parent_entity_id: ID of the parent entity
            line_start: Starting line number in the source file
            line_end: Ending line number in the source file
        """
        super().__init__(
            name=module_name,
            docstring="",  # Imports don't have docstrings
            parent_entity_id=parent_entity_id,
            line_start=line_start,
            line_end=line_end,
        )
        self.module_name = module_name
        self.imported_names = imported_names
        self.is_from = is_from
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the import to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the import
        """
        result = super().to_dict()
        result.update({
            "module_name": self.module_name,
            "imported_names": self.imported_names,
            "is_from": self.is_from,
        })
        return result

class FunctionEntity(Entity):
    """Represents a function or method."""
    
    def __init__(
        self,
        name: str,
        docstring: str = "",
        arguments: Optional[List[Argument]] = None,
        return_type: Optional[TypeInfo] = None,
        is_method: bool = False,
        is_property: bool = False,
        is_static: bool = False,
        is_class_method: bool = False,
        parent_entity_id: Optional[str] = None,
        line_start: int = 0,
        line_end: int = 0,
        file_path: Optional[str] = None,
        docstring_sections: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a function entity.
        
        Args:
            name: Name of the function
            docstring: Documentation string for the function
            arguments: List of function arguments
            return_type: Return type annotation if available
            is_method: Whether this is a method (part of a class)
            is_property: Whether this is a property
            is_static: Whether this is a static method
            is_class_method: Whether this is a class method
            parent_entity_id: ID of the parent entity
            line_start: Starting line number in the source file
            line_end: Ending line number in the source file
            file_path: Path to the source file
            docstring_sections: Parsed sections from the docstring
        """
        super().__init__(
            name=name,
            docstring=docstring,
            parent_entity_id=parent_entity_id,
            line_start=line_start,
            line_end=line_end,
            file_path=file_path,
            docstring_sections=docstring_sections,
        )
        self.arguments = arguments or []
        self.return_type = return_type
        self.is_method = is_method
        self.is_property = is_property
        self.is_static = is_static
        self.is_class_method = is_class_method
        self.decorators: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the function to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the function
        """
        result = super().to_dict()
        result.update({
            "arguments": [arg.to_dict() for arg in self.arguments],
            "return_type": self.return_type.to_dict() if self.return_type else None,
            "is_method": self.is_method,
            "is_property": self.is_property,
            "is_static": self.is_static,
            "is_class_method": self.is_class_method,
            "decorators": self.decorators,
        })
        return result

class ClassEntity(Entity):
    """Represents a class or interface."""
    
    def __init__(
        self,
        name: str,
        docstring: str = "",
        base_classes: Optional[List[str]] = None,
        parent_entity_id: Optional[str] = None,
        line_start: int = 0,
        line_end: int = 0,
        file_path: Optional[str] = None,
        docstring_sections: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a class entity.
        
        Args:
            name: Name of the class
            docstring: Documentation string for the class
            base_classes: List of base class names
            parent_entity_id: ID of the parent entity
            line_start: Starting line number in the source file
            line_end: Ending line number in the source file
            file_path: Path to the source file
            docstring_sections: Parsed sections from the docstring
        """
        super().__init__(
            name=name,
            docstring=docstring,
            parent_entity_id=parent_entity_id,
            line_start=line_start,
            line_end=line_end,
            file_path=file_path,
            docstring_sections=docstring_sections,
        )
        self.base_classes = base_classes or []
        self.methods: List[FunctionEntity] = []
        self.properties: List[Property] = []
        self.class_variables: List[VariableEntity] = []
        self.decorators: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the class to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the class
        """
        result = super().to_dict()
        result.update({
            "base_classes": self.base_classes,
            "methods": [method.to_dict() for method in self.methods],
            "properties": [prop.to_dict() for prop in self.properties],
            "class_variables": [var.to_dict() for var in self.class_variables],
            "decorators": self.decorators,
        })
        return result

class VariableEntity(Entity):
    """Represents a variable or constant."""
    
    def __init__(
        self,
        name: str,
        docstring: str = "",
        value: Optional[str] = None,
        type_annotation: Optional[TypeInfo] = None,
        is_class_var: bool = False,
        parent_entity_id: Optional[str] = None,
        line_start: int = 0,
        line_end: int = 0,
        file_path: Optional[str] = None,
    ):
        """
        Initialize a variable entity.
        
        Args:
            name: Name of the variable
            docstring: Documentation string for the variable
            value: Value of the variable as a string
            type_annotation: Type annotation if available
            is_class_var: Whether this is a class variable
            parent_entity_id: ID of the parent entity
            line_start: Starting line number in the source file
            line_end: Ending line number in the source file
            file_path: Path to the source file
        """
        super().__init__(
            name=name,
            docstring=docstring,
            parent_entity_id=parent_entity_id,
            line_start=line_start,
            line_end=line_end,
            file_path=file_path,
        )
        self.value = value
        self.type_annotation = type_annotation
        self.is_class_var = is_class_var
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the variable to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the variable
        """
        result = super().to_dict()
        result.update({
            "value": self.value,
            "type_annotation": self.type_annotation.to_dict() if self.type_annotation else None,
            "is_class_var": self.is_class_var,
        })
        return result 