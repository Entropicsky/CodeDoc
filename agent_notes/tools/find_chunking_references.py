#!/usr/bin/env python3
"""
Utility script to analyze the codebase and find all references to chunking.
This helps identify all areas that need to be modified when removing custom chunking.
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

# Patterns to search for
CHUNKING_PATTERNS = [
    r"\bchunk", 
    r"\bChunk",
    r"chunking",
    r"Chunking",
    r"CHUNK",
]

# Directories to search
DIRECTORIES = [
    "codedoc",
]

# Directories to exclude
EXCLUDE_DIRS = [
    "__pycache__",
    ".git",
    "venv",
    "env",
]

# File extensions to include
FILE_EXTENSIONS = [
    ".py",
    ".md",
]

def search_file(file_path, patterns):
    """Search for patterns in a file and return matches with line numbers."""
    matches = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        matches.append({
                            "line_num": i,
                            "pattern": pattern,
                            "line": line.strip(),
                        })
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        
    return matches

def search_directory(base_dir, patterns, exclude_dirs, file_extensions):
    """Recursively search directory for pattern matches."""
    results = defaultdict(list)
    base_path = Path(base_dir)
    
    for root, dirs, files in os.walk(base_path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = Path(root) / file
            
            # Check file extension
            if file_path.suffix not in file_extensions:
                continue
                
            # Search for patterns
            matches = search_file(file_path, patterns)
            
            if matches:
                # Store relative path instead of absolute
                try:
                    rel_path = file_path.relative_to(base_path.parent)
                except ValueError:
                    rel_path = file_path
                    
                results[str(rel_path)] = matches
                
    return results

def main():
    """Main entry point."""
    print("Searching for chunking references...")
    
    all_results = {}
    
    for directory in DIRECTORIES:
        print(f"Searching in {directory}...")
        results = search_directory(directory, CHUNKING_PATTERNS, EXCLUDE_DIRS, FILE_EXTENSIONS)
        all_results.update(results)
    
    # Count total references
    total_files = len(all_results)
    total_references = sum(len(matches) for matches in all_results.values())
    
    print(f"Found {total_references} chunking references in {total_files} files.")
    
    # Save results to file
    output_file = "chunking_references.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)
        
    print(f"Results saved to {output_file}")
    
    # Print summary of most affected files
    print("\nMost affected files:")
    file_counts = [(file, len(matches)) for file, matches in all_results.items()]
    file_counts.sort(key=lambda x: x[1], reverse=True)
    
    for file, count in file_counts[:10]:  # Top 10 files
        print(f"{file}: {count} references")

if __name__ == "__main__":
    main() 