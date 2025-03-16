#!/usr/bin/env python3
"""
Documentation generator registry for the CodeDoc framework.

This module defines the GeneratorRegistry class that manages documentation
generators for different output formats and provides methods to find the
appropriate generator.
"""

import logging
from typing import Dict, List, Optional, Type, Union

from .base_generator import BaseGenerator
from .generator_config import GeneratorConfig

logger = logging.getLogger(__name__)


class GeneratorRegistry:
    """
    Registry for documentation generators.
    
    This class maintains a registry of generator classes for different output
    formats and provides methods to find the appropriate generator.
    """
    
    # Registry of generator classes by format
    _generators: Dict[str, Type[BaseGenerator]] = {}
    
    @classmethod
    def register(cls, generator_class: Type[BaseGenerator]) -> None:
        """
        Register a generator class.
        
        Args:
            generator_class: Generator class to register
        """
        format_id = generator_class.get_format()
        
        # Register the generator by format
        cls._generators[format_id] = generator_class
        
        logger.debug(f"Registered documentation generator for format '{format_id}'")
    
    @classmethod
    def get_generator(cls, format_id: str, config: Optional[GeneratorConfig] = None) -> Optional[BaseGenerator]:
        """
        Get a generator instance for the specified format.
        
        Args:
            format_id: Format identifier (e.g., "markdown", "html")
            config: Generator configuration
            
        Returns:
            Generator instance or None if no generator is registered for the format
        """
        generator_class = cls._generators.get(format_id)
        if generator_class:
            return generator_class(config)
        return None
    
    @classmethod
    def get_default_generator(cls, config: Optional[GeneratorConfig] = None) -> Optional[BaseGenerator]:
        """
        Get the default generator instance.
        
        The default is "markdown" if available, otherwise the first registered generator.
        
        Args:
            config: Generator configuration
            
        Returns:
            Generator instance or None if no generators are registered
        """
        # Try to get the markdown generator first
        if "markdown" in cls._generators:
            return cls.get_generator("markdown", config)
        
        # Otherwise use the first registered generator
        if cls._generators:
            format_id = next(iter(cls._generators.keys()))
            return cls.get_generator(format_id, config)
        
        return None
    
    @classmethod
    def get_registered_formats(cls) -> List[str]:
        """
        Get a list of registered output formats.
        
        Returns:
            List of registered format identifiers
        """
        return list(cls._generators.keys()) 