#!/usr/bin/env python3
"""
Base documentation generator interface for the CodeDoc framework.

This module defines the BaseGenerator abstract base class that all documentation
generators must implement. It provides the contract for generating documentation
from parsed code entities.
"""

import abc
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from ..core.entities import Entity, ModuleEntity, ClassEntity, FunctionEntity
from .generator_config import GeneratorConfig


class BaseGenerator(abc.ABC):
    """
    Abstract base class for documentation generators.
    
    All documentation generators must implement this interface to provide a
    consistent way to generate documentation from parsed code entities.
    """
    
    # Output format identifier (e.g., "markdown", "html", "rst")
    FORMAT = "base"
    
    # File extension for the generated documentation (e.g., ".md", ".html")
    FILE_EXTENSION = ""
    
    def __init__(self, config: Optional[GeneratorConfig] = None):
        """
        Initialize the generator with optional configuration.
        
        Args:
            config: Generator configuration options
        """
        self.config = config or GeneratorConfig()
        self._processed_entities: Set[str] = set()  # Track processed entity IDs
    
    @abc.abstractmethod
    def generate_documentation(
        self, 
        entity: Entity, 
        output_dir: Union[str, Path],
        relative_path: Optional[str] = None
    ) -> Path:
        """
        Generate documentation for an entity.
        
        Args:
            entity: The entity to generate documentation for
            output_dir: Directory where documentation should be saved
            relative_path: Optional relative path within output_dir
            
        Returns:
            Path to the generated documentation file
            
        Raises:
            ValueError: If documentation cannot be generated
        """
        pass
    
    @abc.abstractmethod
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
            
        Raises:
            ValueError: If the index cannot be generated
        """
        pass
    
    def generate_project_documentation(
        self,
        modules: List[ModuleEntity],
        output_dir: Union[str, Path],
        project_name: str = "Project",
        project_description: str = ""
    ) -> Path:
        """
        Generate documentation for an entire project.
        
        Args:
            modules: List of module entities in the project
            output_dir: Directory where documentation should be saved
            project_name: Name of the project
            project_description: Description of the project
            
        Returns:
            Path to the generated project index file
            
        Raises:
            ValueError: If project documentation cannot be generated
        """
        output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Reset processed entities tracker
        self._processed_entities = set()
        
        # Process all modules and their contents
        for module in modules:
            self.generate_documentation(module, output_dir)
        
        # Generate the project index
        return self.generate_index(modules, output_dir, title=project_name)
    
    def _get_output_path(
        self, 
        entity: Entity, 
        output_dir: Path,
        relative_path: Optional[str] = None
    ) -> Path:
        """
        Get the output path for an entity's documentation.
        
        Args:
            entity: The entity to get the path for
            output_dir: Base output directory
            relative_path: Optional relative path within output_dir
            
        Returns:
            Path where the entity's documentation should be saved
        """
        # Create a suitable filename from the entity's name
        filename = f"{entity.name.replace('.', '_')}{self.FILE_EXTENSION}"
        
        if relative_path:
            # If a relative path is provided, use it
            rel_dir = output_dir / relative_path
            rel_dir.mkdir(parents=True, exist_ok=True)
            return rel_dir / filename
        
        # Otherwise use a path based on the entity type
        if isinstance(entity, ModuleEntity):
            # Use module path structure
            if entity.file_path:
                # Create directory structure mirroring the module's location
                rel_dir = Path(entity.file_path).parent.relative_to(Path(entity.file_path).anchor)
                doc_dir = output_dir / rel_dir
                doc_dir.mkdir(parents=True, exist_ok=True)
                return doc_dir / filename
        
        # Default: place directly in the output directory
        return output_dir / filename
    
    def _should_include_entity(self, entity: Entity) -> bool:
        """
        Check if an entity should be included in the documentation.
        
        Args:
            entity: The entity to check
            
        Returns:
            True if the entity should be included, False otherwise
        """
        # Skip already processed entities to avoid duplication
        if hasattr(self, 'processed_entities') and entity.id in self.processed_entities:
            return False
        
        # Check entity type
        entity_type = entity.__class__.__name__.lower().replace("entity", "")
        if entity_type not in self.config.include_entity_types:
            return False
        
        # Check if private entities should be included
        if not self.config.include_private and entity.name.startswith("_"):
            # Skip private entities if not configured to include them
            return False
        
        return True
    
    @classmethod
    def get_format(cls) -> str:
        """
        Get the output format identifier for this generator.
        
        Returns:
            Output format identifier string
        """
        return cls.FORMAT 