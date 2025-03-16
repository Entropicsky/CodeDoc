#!/usr/bin/env python3
"""
Script to identify potentially unused files in the CodeDoc project.

This script analyzes the Python imports across the codebase and identifies files 
that don't appear to be imported or used anywhere.
"""

import os
import sys
import re
import argparse
from pathlib import Path
from collections import defaultdict


def find_python_files(root_dir, exclude_dirs=None):
    """Find all Python files in the specified directory, excluding directories."""
    if exclude_dirs is None:
        exclude_dirs = []
    
    exclude_dirs = [os.path.normpath(d) for d in exclude_dirs]
    python_files = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if os.path.normpath(os.path.join(root, d)) not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    return python_files


def extract_imports(file_path):
    """Extract all imports from a Python file."""
    import_patterns = [
        # Standard import pattern: import module or import module.submodule
        r'^import\s+([\w\.]+)',
        
        # From import pattern: from module import item1, item2
        r'^from\s+([\w\.]+)\s+import\s+',
        
        # Relative import pattern: from . import module or from .submodule import item
        r'^from\s+(\.+)([\w\.]*)\s+import\s+'
    ]
    
    imports = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split content into lines
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            for pattern in import_patterns:
                match = re.match(pattern, line)
                if match:
                    if pattern == import_patterns[0]:  # Standard import
                        imports.append(match.group(1))
                    elif pattern == import_patterns[1]:  # From import
                        imports.append(match.group(1))
                    elif pattern == import_patterns[2]:  # Relative import
                        dots = match.group(1)
                        module = match.group(2)
                        if module:  # If there's a module specified
                            imports.append(module)
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return imports


def map_module_to_file(python_files, project_root):
    """Map module names to their file paths."""
    module_to_file = {}
    
    for file_path in python_files:
        # Get relative path from project root
        rel_path = os.path.relpath(file_path, project_root)
        
        # Convert path to module path (replace / with . and remove .py)
        module_path = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
        
        # Add mapping
        module_to_file[module_path] = file_path
        
        # For __init__.py files, also add the directory as a module
        if os.path.basename(file_path) == '__init__.py':
            dir_module_path = os.path.dirname(rel_path).replace(os.path.sep, '.')
            module_to_file[dir_module_path] = os.path.dirname(file_path)
    
    return module_to_file


def find_used_files(python_files, module_to_file, project_root):
    """Find which files are imported by other files."""
    used_files = set()
    
    # Consider files in tests, test_code, and samples as used
    for file_path in python_files:
        rel_path = os.path.relpath(file_path, project_root)
        if (rel_path.startswith('tests') or 
            rel_path.startswith('test_code') or
            rel_path.startswith('codedoc/tests')):
            used_files.add(file_path)
    
    # Also consider any Python file that's imported by another file as used
    for file_path in python_files:
        imports = extract_imports(file_path)
        
        for import_path in imports:
            if import_path in module_to_file:
                used_files.add(module_to_file[import_path])
            
            # Handle submodule imports
            for module in module_to_file:
                if module.startswith(import_path + '.'):
                    used_files.add(module_to_file[module])
    
    # Add files imported by main entry points
    entry_points = [
        'codedoc/pipeline.py',
        'codedoc/main.py',
        'run_tests.py'
    ]
    
    for entry_point in entry_points:
        entry_path = os.path.join(project_root, entry_point)
        if os.path.exists(entry_path):
            used_files.add(entry_path)
    
    return used_files


def main():
    parser = argparse.ArgumentParser(description='Find unused Python files in the project.')
    parser.add_argument('--root-dir', type=str, default='.', help='Root directory of the project')
    parser.add_argument('--exclude-dirs', type=str, nargs='*', default=['venv', 'env', '.git', '.github', 'deprecated'],
                        help='Directories to exclude from search')
    parser.add_argument('--output', type=str, help='Output file for unused files list')
    
    args = parser.parse_args()
    
    project_root = os.path.abspath(args.root_dir)
    exclude_dirs = [os.path.join(project_root, d) for d in args.exclude_dirs]
    
    print(f"Analyzing project at: {project_root}")
    print(f"Excluding directories: {', '.join(args.exclude_dirs)}")
    
    # Find all Python files
    python_files = find_python_files(project_root, exclude_dirs)
    print(f"Found {len(python_files)} Python files")
    
    # Map module names to file paths
    module_to_file = map_module_to_file(python_files, project_root)
    
    # Find used files
    used_files = find_used_files(python_files, module_to_file, project_root)
    print(f"Found {len(used_files)} used Python files")
    
    # Find unused files
    unused_files = set(python_files) - used_files
    print(f"Found {len(unused_files)} potentially unused Python files")
    
    # Output results
    if unused_files:
        print("\nPotentially unused files:")
        for file in sorted(unused_files):
            rel_path = os.path.relpath(file, project_root)
            print(f"  {rel_path}")
        
        if args.output:
            with open(args.output, 'w') as f:
                for file in sorted(unused_files):
                    rel_path = os.path.relpath(file, project_root)
                    f.write(f"{rel_path}\n")
            print(f"\nUnused files list written to {args.output}")
    else:
        print("\nNo unused files found!")


if __name__ == '__main__':
    main() 