#!/usr/bin/env python3
"""
Script to move unused files to a deprecated folder.

This script reads a list of potentially unused files and moves them to a 
deprecated folder, maintaining the original directory structure.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path


def create_deprecated_folder(project_root, deprecated_folder):
    """Create the deprecated folder if it doesn't exist."""
    deprecated_path = os.path.join(project_root, deprecated_folder)
    os.makedirs(deprecated_path, exist_ok=True)
    
    # Create a README.md file explaining the purpose of the deprecated folder
    readme_path = os.path.join(deprecated_path, "README.md")
    with open(readme_path, "w") as f:
        f.write("""# Deprecated Files

This folder contains files that were identified as potentially unused in the project.
They have been moved here to clean up the main codebase while preserving them for reference.

Files were moved here based on static analysis of imports and may still have value.
Before permanently deleting any file, please verify that it is truly unused.

## Moving Back

If you find that a file is actually needed, you can move it back to its original location.
The original path is preserved in the directory structure.

## Generated on

This folder was generated on by the `move_to_deprecated.py` script.
""")
    
    return deprecated_path


def move_files_to_deprecated(file_list, project_root, deprecated_folder, dry_run=False):
    """Move files to the deprecated folder, maintaining directory structure."""
    deprecated_path = create_deprecated_folder(project_root, deprecated_folder)
    moved_files = []
    
    with open(file_list, 'r') as f:
        files = [line.strip() for line in f.readlines()]
    
    for rel_path in files:
        # Skip empty lines
        if not rel_path:
            continue
            
        # Skip files that are already in the deprecated folder
        if rel_path.startswith(deprecated_folder):
            print(f"Skipping {rel_path} (already in deprecated folder)")
            continue
        
        source_path = os.path.join(project_root, rel_path)
        target_path = os.path.join(deprecated_path, rel_path)
        
        # Create directory structure in the deprecated folder
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        if dry_run:
            print(f"Would move {rel_path} to {os.path.join(deprecated_folder, rel_path)}")
        else:
            try:
                # Only move if the source file exists
                if os.path.exists(source_path):
                    print(f"Moving {rel_path} to {os.path.join(deprecated_folder, rel_path)}")
                    shutil.move(source_path, target_path)
                    moved_files.append(rel_path)
                else:
                    print(f"Skipping {rel_path} (file not found)")
            except Exception as e:
                print(f"Error moving {rel_path}: {e}")
    
    return moved_files


def main():
    parser = argparse.ArgumentParser(description='Move unused files to a deprecated folder.')
    parser.add_argument('file_list', type=str, help='File containing list of unused files')
    parser.add_argument('--root-dir', type=str, default='.', help='Root directory of the project')
    parser.add_argument('--deprecated-folder', type=str, default='deprecated', 
                       help='Name of the folder to store deprecated files')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Just print what would be done without actually moving files')
    
    args = parser.parse_args()
    
    project_root = os.path.abspath(args.root_dir)
    
    print(f"Moving unused files to {args.deprecated_folder}")
    if args.dry_run:
        print("DRY RUN: No files will be moved")
    
    moved_files = move_files_to_deprecated(
        args.file_list, 
        project_root, 
        args.deprecated_folder,
        args.dry_run
    )
    
    if not args.dry_run:
        print(f"\nMoved {len(moved_files)} files to {args.deprecated_folder}")


if __name__ == '__main__':
    main() 