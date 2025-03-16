#!/usr/bin/env python3
"""
Generator configuration for the CodeDoc framework.

This module defines configuration options for documentation generators, allowing
customization of the generation process and output format.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class GeneratorConfig:
    """
    Configuration options for documentation generators.
    
    This class provides options to customize how documentation is generated,
    such as what entities to include, formatting options, and output settings.
    """
    
    # Output format (e.g., "markdown", "html", "rst")
    format: str = "markdown"
    
    # Include private entities (those starting with _)
    include_private: bool = False
    
    # Include source code in documentation
    include_source: bool = True
    
    # Include type information in documentation
    include_types: bool = True
    
    # Include examples in documentation
    include_examples: bool = True
    
    # Include inheritance information
    include_inheritance: bool = True
    
    # Include references to other entities
    include_references: bool = True
    
    # Include table of contents
    include_toc: bool = True
    
    # Include metadata (line numbers, file paths, etc.)
    include_metadata: bool = True
    
    # Output directory for generated documentation
    output_dir: str = "docs"
    
    # Title for the documentation
    title: str = "API Documentation"
    
    # Custom CSS file to include (for HTML output)
    custom_css: Optional[str] = None
    
    # Custom templates directory
    template_dir: Optional[str] = None
    
    # Entity types to include
    include_entity_types: Set[str] = field(default_factory=lambda: {
        "module", "class", "function", "method", "property", "variable"
    })
    
    # Additional format-specific options
    options: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default values for optional fields."""
        if self.options is None:
            self.options = {}
    
    def with_option(self, key: str, value: Any) -> 'GeneratorConfig':
        """
        Create a new config with an additional option.
        
        Args:
            key: Option key
            value: Option value
            
        Returns:
            New GeneratorConfig with the added option
        """
        new_config = GeneratorConfig(
            format=self.format,
            include_private=self.include_private,
            include_source=self.include_source,
            include_types=self.include_types,
            include_examples=self.include_examples,
            include_inheritance=self.include_inheritance,
            include_references=self.include_references,
            include_toc=self.include_toc,
            include_metadata=self.include_metadata,
            output_dir=self.output_dir,
            title=self.title,
            custom_css=self.custom_css,
            template_dir=self.template_dir,
            include_entity_types=self.include_entity_types.copy(),
            options=dict(self.options)
        )
        new_config.options[key] = value
        return new_config
    
    def get_option(self, key: str, default: Any = None) -> Any:
        """
        Get an option value.
        
        Args:
            key: Option key
            default: Default value if the key is not found
            
        Returns:
            Option value or default
        """
        return self.options.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            "format": self.format,
            "include_private": self.include_private,
            "include_source": self.include_source,
            "include_types": self.include_types,
            "include_examples": self.include_examples,
            "include_inheritance": self.include_inheritance,
            "include_references": self.include_references,
            "include_toc": self.include_toc,
            "include_metadata": self.include_metadata,
            "output_dir": self.output_dir,
            "title": self.title,
            "custom_css": self.custom_css,
            "template_dir": self.template_dir,
            "include_entity_types": list(self.include_entity_types),
            "options": self.options
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeneratorConfig':
        """
        Create a configuration from a dictionary.
        
        Args:
            data: Dictionary with configuration values
            
        Returns:
            GeneratorConfig instance
        """
        # Handle entity types set conversion
        if "include_entity_types" in data and isinstance(data["include_entity_types"], list):
            data["include_entity_types"] = set(data["include_entity_types"])
            
        return cls(**data) 