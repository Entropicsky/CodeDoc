"""
Base parser interface for CodeDoc.

This module defines the base interfaces for all language-specific parsers.
"""

import abc
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class ParsedEntity:
    """Base class for all parsed entities (functions, classes, etc.)."""
    
    def __init__(
        self,
        name: str,
        entity_type: str,
        file_path: Path,
        start_line: int,
        end_line: int,
        docstring: Optional[str] = None,
    ):
        """Initialize a parsed entity.
        
        Args:
            name: Name of the entity
            entity_type: Type of entity (function, class, etc.)
            file_path: Path to the file containing the entity
            start_line: Starting line number of the entity
            end_line: Ending line number of the entity
            docstring: Optional docstring for the entity
        """
        self.name = name
        self.entity_type = entity_type
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.docstring = docstring
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary representation."""
        return {
            "name": self.name,
            "type": self.entity_type,
            "file_path": str(self.file_path),
            "start_line": self.start_line,
            "end_line": self.end_line,
            "docstring": self.docstring,
            "metadata": self.metadata,
        }


class ParsedFunction(ParsedEntity):
    """Representation of a parsed function or method."""
    
    def __init__(
        self,
        name: str,
        file_path: Path,
        start_line: int,
        end_line: int,
        docstring: Optional[str] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        return_type: Optional[str] = None,
        return_description: Optional[str] = None,
        is_method: bool = False,
        is_static: bool = False,
        is_class_method: bool = False,
        is_abstract: bool = False,
        decorators: Optional[List[str]] = None,
    ):
        """Initialize a parsed function.
        
        Args:
            name: Function name
            file_path: Path to the file containing the function
            start_line: Starting line number
            end_line: Ending line number
            docstring: Function docstring
            parameters: List of parameter dictionaries with name, type, default, description
            return_type: Return type annotation
            return_description: Description of the return value
            is_method: Whether this is a class method
            is_static: Whether this is a static method
            is_class_method: Whether this is a @classmethod
            is_abstract: Whether this is an abstract method
            decorators: List of decorators applied to the function
        """
        super().__init__(
            name=name,
            entity_type="function",
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            docstring=docstring,
        )
        self.parameters = parameters or []
        self.return_type = return_type
        self.return_description = return_description
        self.is_method = is_method
        self.is_static = is_static
        self.is_class_method = is_class_method
        self.is_abstract = is_abstract
        self.decorators = decorators or []
        self.calls: List[str] = []  # List of function names called by this function
        self.called_by: List[str] = []  # List of functions that call this function
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert function to dictionary representation."""
        base_dict = super().to_dict()
        function_dict = {
            "parameters": self.parameters,
            "return_type": self.return_type,
            "return_description": self.return_description,
            "is_method": self.is_method,
            "is_static": self.is_static,
            "is_class_method": self.is_class_method,
            "is_abstract": self.is_abstract,
            "decorators": self.decorators,
            "calls": self.calls,
            "called_by": self.called_by,
        }
        base_dict.update(function_dict)
        return base_dict


class ParsedClass(ParsedEntity):
    """Representation of a parsed class."""
    
    def __init__(
        self,
        name: str,
        file_path: Path,
        start_line: int,
        end_line: int,
        docstring: Optional[str] = None,
        superclasses: Optional[List[str]] = None,
        is_abstract: bool = False,
        decorators: Optional[List[str]] = None,
    ):
        """Initialize a parsed class.
        
        Args:
            name: Class name
            file_path: Path to the file containing the class
            start_line: Starting line number
            end_line: Ending line number
            docstring: Class docstring
            superclasses: List of superclass names
            is_abstract: Whether this is an abstract class
            decorators: List of decorators applied to the class
        """
        super().__init__(
            name=name,
            entity_type="class",
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            docstring=docstring,
        )
        self.superclasses = superclasses or []
        self.is_abstract = is_abstract
        self.decorators = decorators or []
        self.methods: List[ParsedFunction] = []
        self.properties: List[str] = []
        self.subclasses: List[str] = []  # Classes that inherit from this class
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert class to dictionary representation."""
        base_dict = super().to_dict()
        class_dict = {
            "superclasses": self.superclasses,
            "is_abstract": self.is_abstract,
            "decorators": self.decorators,
            "methods": [method.to_dict() for method in self.methods],
            "properties": self.properties,
            "subclasses": self.subclasses,
        }
        base_dict.update(class_dict)
        return base_dict


class ParsedModule(ParsedEntity):
    """Representation of a parsed module (file)."""
    
    def __init__(
        self,
        name: str,
        file_path: Path,
        docstring: Optional[str] = None,
    ):
        """Initialize a parsed module.
        
        Args:
            name: Module name
            file_path: Path to the module file
            docstring: Module docstring
        """
        super().__init__(
            name=name,
            entity_type="module",
            file_path=file_path,
            start_line=1,
            end_line=-1,  # Will be set when the file is fully parsed
            docstring=docstring,
        )
        self.imports: List[Dict[str, str]] = []
        self.functions: List[ParsedFunction] = []
        self.classes: List[ParsedClass] = []
        self.variables: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert module to dictionary representation."""
        base_dict = super().to_dict()
        module_dict = {
            "imports": self.imports,
            "functions": [func.to_dict() for func in self.functions],
            "classes": [cls.to_dict() for cls in self.classes],
            "variables": self.variables,
        }
        base_dict.update(module_dict)
        return base_dict


class BaseParser(abc.ABC):
    """Base interface for all language parsers."""
    
    @abc.abstractmethod
    def parse_file(self, file_path: Union[str, Path]) -> ParsedModule:
        """Parse a single file and return a ParsedModule.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            ParsedModule: Representation of the parsed file
        """
        pass
    
    @abc.abstractmethod
    def parse_directory(self, dir_path: Union[str, Path]) -> List[ParsedModule]:
        """Parse all relevant files in a directory.
        
        Args:
            dir_path: Path to the directory to parse
            
        Returns:
            List[ParsedModule]: List of parsed modules
        """
        pass
    
    @abc.abstractmethod
    def get_imports(self, module: ParsedModule) -> List[Dict[str, str]]:
        """Extract imports and dependencies from a module.
        
        Args:
            module: The parsed module
            
        Returns:
            List[Dict[str, str]]: List of import dictionaries with name and path
        """
        pass
    
    @abc.abstractmethod
    def get_classes(self, module: ParsedModule) -> List[ParsedClass]:
        """Extract classes and their relationships from a module.
        
        Args:
            module: The parsed module
            
        Returns:
            List[ParsedClass]: List of parsed classes
        """
        pass
    
    @abc.abstractmethod
    def get_functions(self, module: ParsedModule) -> List[ParsedFunction]:
        """Extract functions and their details from a module.
        
        Args:
            module: The parsed module
            
        Returns:
            List[ParsedFunction]: List of parsed functions
        """
        pass
    
    @classmethod
    def can_parse(cls, file_path: Union[str, Path]) -> bool:
        """Check if this parser can parse the given file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if this parser can parse the file, False otherwise
        """
        return False 