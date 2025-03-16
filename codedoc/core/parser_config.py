#!/usr/bin/env python3
"""
Parser configuration for the CodeDoc framework.

This module defines configuration options for the parsers, allowing customization
of parsing behavior such as what entities to include or exclude.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ParserConfig:
    """
    Configuration options for parsers.
    
    This class provides options to customize how parsers extract information
    from source code files, such as what types of entities to include or exclude.
    """
    
    # Include private members (those starting with _)
    include_private_members: bool = False
    
    # Include local variables inside functions
    include_local_variables: bool = False
    
    # Maximum depth to analyze (e.g., for handling nested functions)
    max_depth: int = 5
    
    # Additional language-specific options
    options: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default values for optional fields."""
        if self.options is None:
            self.options = {}
    
    def with_option(self, key: str, value: Any) -> 'ParserConfig':
        """
        Create a new config with an additional option.
        
        Args:
            key: Option key
            value: Option value
            
        Returns:
            New ParserConfig with the added option
        """
        new_config = ParserConfig(
            include_private_members=self.include_private_members,
            include_local_variables=self.include_local_variables,
            max_depth=self.max_depth,
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