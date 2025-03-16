#!/usr/bin/env python3
"""
Sample Python module for testing the parser.

This module contains various Python features that the parser should handle:
- Functions with different parameter types
- Classes with inheritance
- Decorators
- Type annotations
- Docstrings in different formats
- Various import styles
"""

import os
import sys
import abc
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, field

# Third-party imports
import yaml
try:
    import numpy as np
except ImportError:
    np = None

# Relative imports
from . import utils
from .constants import DEFAULT_VALUE


# Module level variables
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")
MAX_ITEMS = 100
VERSION = "1.0.0"


# Simple function with docstring
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers.
    
    Args:
        a: First integer
        b: Second integer
        
    Returns:
        Sum of a and b
    """
    return a + b


# Function with default parameters and type annotations
def process_data(
    data: List[Dict[str, Any]],
    max_items: Optional[int] = None,
    process_all: bool = False,
    callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """Process a list of data items.
    
    This function demonstrates:
    - Complex type annotations
    - Default parameter values
    - Optional parameters
    - Callable type hints
    
    Parameters:
        data: List of data items to process
        max_items: Maximum number of items to process (None for all)
        process_all: Whether to process all items regardless of max_items
        callback: Optional callback function to call for each item
    
    Returns:
        Tuple containing:
        - List of processed items
        - Count of processed items
    
    Raises:
        ValueError: If data is empty
    """
    if not data:
        raise ValueError("Data cannot be empty")
    
    # Calculate the number of items to process
    items_to_process = len(data) if process_all else (max_items or MAX_ITEMS)
    items_to_process = min(items_to_process, len(data))
    
    # Process the items
    processed_items = []
    for i, item in enumerate(data):
        if i >= items_to_process:
            break
        
        # Apply some transformation
        processed_item = {**item, "processed": True}
        processed_items.append(processed_item)
        
        # Call the callback if provided
        if callback is not None:
            callback(processed_item)
    
    return processed_items, len(processed_items)


# Simple class
class Item:
    """Base class for all items.
    
    Attributes:
        name: The name of the item
        value: The value of the item
    """
    
    def __init__(self, name: str, value: float):
        """Initialize the item.
        
        Args:
            name: The name of the item
            value: The value of the item
        """
        self.name = name
        self.value = value
    
    def __str__(self) -> str:
        return f"{self.name}: {self.value}"
    
    def get_value(self) -> float:
        """Get the item's value.
        
        Returns:
            The value of the item
        """
        return self.value


# Class with inheritance
class SpecialItem(Item):
    """A special item with additional properties.
    
    This class demonstrates inheritance and method overrides.
    
    Attributes:
        name: The name of the item
        value: The value of the item
        special: Whether the item is special
    """
    
    def __init__(self, name: str, value: float, special: bool = True):
        """Initialize the special item.
        
        Args:
            name: The name of the item
            value: The value of the item
            special: Whether the item is special
        """
        super().__init__(name, value)
        self.special = special
    
    def get_value(self) -> float:
        """Get the item's value with a special multiplier.
        
        Returns:
            The value of the item multiplied by 2 if special
        """
        multiplier = 2 if self.special else 1
        return super().get_value() * multiplier


# Class with dataclass
@dataclass
class Configuration:
    """Configuration class using dataclass.
    
    Attributes:
        name: Configuration name
        enabled: Whether the configuration is enabled
        values: Dictionary of configuration values
        options: List of configuration options
    """
    name: str
    enabled: bool = True
    values: Dict[str, Any] = field(default_factory=dict)
    options: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """Check if the configuration is valid.
        
        Returns:
            True if the configuration is valid, False otherwise
        """
        return bool(self.name and (self.values or self.options))


# Class with complex inheritance and abstract methods
class BaseProcessor(abc.ABC):
    """Abstract base class for all processors.
    
    This class demonstrates abstract methods and class-level docstrings.
    """
    
    @abc.abstractmethod
    def process(self, data: Any) -> Any:
        """Process the given data.
        
        Args:
            data: Data to process
            
        Returns:
            Processed data
        """
        pass
    
    @classmethod
    def create(cls, config: Dict[str, Any]) -> 'BaseProcessor':
        """Factory method to create a processor.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            A processor instance
        """
        processor_type = config.get("type", "default")
        if processor_type == "default":
            return DefaultProcessor(**config)
        elif processor_type == "special":
            return SpecialProcessor(**config)
        else:
            raise ValueError(f"Unknown processor type: {processor_type}")


# Class that implements an abstract class
class DefaultProcessor(BaseProcessor):
    """Default implementation of BaseProcessor."""
    
    def __init__(self, **kwargs):
        self.config = kwargs
    
    def process(self, data: Any) -> Any:
        """Process the given data using the default strategy.
        
        Args:
            data: Data to process
            
        Returns:
            Processed data
        """
        # Simple implementation
        return data


# Class with decorators
class SpecialProcessor(BaseProcessor):
    """Special implementation of BaseProcessor with decorators."""
    
    def __init__(self, **kwargs):
        self.config = kwargs
        self.processed_count = 0
    
    @property
    def name(self) -> str:
        """Get the processor name."""
        return self.config.get("name", "SpecialProcessor")
    
    @staticmethod
    def get_version() -> str:
        """Get the processor version.
        
        Returns:
            The processor version
        """
        return VERSION
    
    @classmethod
    def from_config_file(cls, path: Union[str, Path]) -> 'SpecialProcessor':
        """Create a processor from a configuration file.
        
        Args:
            path: Path to the configuration file
            
        Returns:
            A processor instance
        """
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        return cls(**config)
    
    def process(self, data: Any) -> Any:
        """Process the given data using the special strategy.
        
        Args:
            data: Data to process
            
        Returns:
            Processed data
        """
        # Special implementation
        self.processed_count += 1
        if isinstance(data, dict):
            return {**data, "processed_by": self.name, "count": self.processed_count}
        elif isinstance(data, list):
            return [self.process(item) for item in data]
        return data


# Function with complex logic for testing
def complex_function(
    items: List[Item],
    config: Optional[Configuration] = None,
    processors: Optional[List[BaseProcessor]] = None
) -> Dict[str, Any]:
    """Process a list of items using the specified configuration and processors.
    
    This function demonstrates complex code with various features:
    - Multiple classes and inheritance
    - Function calls
    - Control flow
    - Error handling
    - Type annotations
    
    Args:
        items: List of items to process
        config: Optional configuration
        processors: Optional list of processors
        
    Returns:
        Dictionary with processing results
        
    Raises:
        ValueError: If items is empty
    """
    if not items:
        raise ValueError("Items cannot be empty")
    
    # Use default configuration if not provided
    if config is None:
        config = Configuration(
            name="default",
            enabled=True,
            values={"max_items": MAX_ITEMS},
            options=["process_all"]
        )
    
    # Skip processing if configuration is disabled
    if not config.enabled:
        return {"status": "disabled", "processed": 0, "items": []}
    
    # Get the list of processors
    if processors is None:
        processors = [DefaultProcessor()]
    
    # Process the items
    processed_items = []
    for item in items:
        # Skip if max items reached
        if len(processed_items) >= config.values.get("max_items", MAX_ITEMS):
            break
        
        # Get the item value
        value = item.get_value()
        
        # Apply all processors
        processed_value = value
        for processor in processors:
            processed_value = processor.process(processed_value)
        
        # Add to the results
        processed_items.append({
            "name": item.name,
            "original_value": value,
            "processed_value": processed_value
        })
    
    # Return the results
    return {
        "status": "success",
        "processed": len(processed_items),
        "items": processed_items,
        "config": config.name
    }


# Main entry point
if __name__ == "__main__":
    # Create some items
    items = [
        Item("Item 1", 10.5),
        SpecialItem("Special Item", 20.0),
        Item("Item 3", 15.0)
    ]
    
    # Process the items
    result = complex_function(items)
    
    # Print the results
    print(f"Processed {result['processed']} items:")
    for item in result["items"]:
        print(f"- {item['name']}: {item['original_value']} -> {item['processed_value']}") 