"""
Test utilities for CodeDoc.

This module provides utility functions for testing the CodeDoc framework.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def create_temp_file(content: str, extension: str = ".py") -> Path:
    """Create a temporary file with the given content.
    
    Args:
        content: The content to write to the file
        extension: The file extension to use (default: .py)
        
    Returns:
        Path: Path to the created temporary file
    """
    fd, path = tempfile.mkstemp(suffix=extension)
    os.close(fd)
    
    file_path = Path(path)
    with open(file_path, "w") as f:
        f.write(content)
    
    return file_path


def create_temp_module(
    module_name: str,
    content: str,
    parent_dir: Optional[Path] = None
) -> Path:
    """Create a temporary Python module with the given content.
    
    Args:
        module_name: Name of the module (without .py extension)
        content: The content to write to the module
        parent_dir: Optional parent directory (uses tempdir if None)
        
    Returns:
        Path: Path to the created temporary module
    """
    if parent_dir is None:
        parent_dir = Path(tempfile.mkdtemp())
    else:
        parent_dir.mkdir(parents=True, exist_ok=True)
    
    module_path = parent_dir / f"{module_name}.py"
    with open(module_path, "w") as f:
        f.write(content)
    
    # Create __init__.py to make it a proper package
    init_path = parent_dir / "__init__.py"
    if not init_path.exists():
        init_path.touch()
    
    return module_path


def create_temp_project(
    structure: Dict[str, Any],
    base_dir: Optional[Path] = None
) -> Path:
    """Create a temporary project with the given structure.
    
    The structure should be a dictionary where:
    - Keys are file/directory names
    - Values are either:
      - String content for files
      - Nested dictionaries for directories
    
    Args:
        structure: Dictionary describing the project structure
        base_dir: Optional base directory (uses tempdir if None)
        
    Returns:
        Path: Path to the created temporary project
    """
    if base_dir is None:
        base_dir = Path(tempfile.mkdtemp())
    else:
        base_dir.mkdir(parents=True, exist_ok=True)
    
    for name, content in structure.items():
        path = base_dir / name
        
        if isinstance(content, dict):
            # This is a directory
            path.mkdir(exist_ok=True)
            create_temp_project(content, path)
        else:
            # This is a file
            with open(path, "w") as f:
                f.write(str(content))
    
    return base_dir


def compare_parsed_entities(entity1: Any, entity2: Any) -> List[str]:
    """Compare two parsed entities and return a list of differences.
    
    Args:
        entity1: First entity to compare
        entity2: Second entity to compare
        
    Returns:
        List[str]: List of differences, empty if entities are equal
    """
    differences = []
    
    # Convert to dictionaries for easier comparison
    dict1 = entity1.to_dict() if hasattr(entity1, "to_dict") else entity1
    dict2 = entity2.to_dict() if hasattr(entity2, "to_dict") else entity2
    
    # Check if both are dictionaries
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return ["Entities are not comparable"]
    
    # Compare keys
    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())
    
    if keys1 != keys2:
        missing_in_2 = keys1 - keys2
        missing_in_1 = keys2 - keys1
        
        if missing_in_2:
            differences.append(f"Keys missing in second entity: {missing_in_2}")
        if missing_in_1:
            differences.append(f"Keys missing in first entity: {missing_in_1}")
    
    # Compare values for common keys
    for key in keys1.intersection(keys2):
        value1 = dict1[key]
        value2 = dict2[key]
        
        if isinstance(value1, dict) and isinstance(value2, dict):
            # Recursive comparison for nested dictionaries
            nested_differences = compare_parsed_entities(value1, value2)
            if nested_differences:
                differences.extend([f"{key}.{diff}" for diff in nested_differences])
        elif isinstance(value1, list) and isinstance(value2, list):
            if len(value1) != len(value2):
                differences.append(f"Different list lengths for {key}: {len(value1)} vs {len(value2)}")
            else:
                # Compare list items
                for i, (item1, item2) in enumerate(zip(value1, value2)):
                    if isinstance(item1, dict) and isinstance(item2, dict):
                        nested_differences = compare_parsed_entities(item1, item2)
                        if nested_differences:
                            differences.extend([f"{key}[{i}].{diff}" for diff in nested_differences])
                    elif item1 != item2:
                        differences.append(f"Different values for {key}[{i}]: {item1} vs {item2}")
        elif value1 != value2:
            differences.append(f"Different values for {key}: {value1} vs {value2}")
    
    return differences


def cleanup_temp_files(paths: Union[Path, List[Path]]) -> None:
    """Clean up temporary files and directories.
    
    Args:
        paths: Path or list of paths to clean up
    """
    if not isinstance(paths, list):
        paths = [paths]
    
    for path in paths:
        path = Path(path)
        if path.is_dir():
            # Remove all files in the directory
            for file in path.glob("**/*"):
                if file.is_file():
                    file.unlink()
            # Remove the directory
            path.rmdir()
        elif path.is_file():
            path.unlink() 