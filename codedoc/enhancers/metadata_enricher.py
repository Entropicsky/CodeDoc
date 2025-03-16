#!/usr/bin/env python3
"""
Metadata Enricher for CodeDoc.

This module provides functionality to enrich entities with additional
metadata such as file modification dates, version information, and tags.
"""

import os
import re
import time
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple, Union
import logging

from codedoc.core.entities import (
    Entity, ModuleEntity, ClassEntity, FunctionEntity, VariableEntity
)

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """
    Enriches entities with additional metadata.
    
    This class analyzes and adds useful metadata to entities to enhance
    documentation, including:
    - File modification timestamps
    - Version information
    - Stability indicators
    - Tags and categories
    - Author information
    
    This metadata helps LLMs understand the context, maturity, and
    purpose of code elements.
    """
    
    def __init__(self, 
                repo_root: Optional[Union[str, Path]] = None,
                config: Optional[Dict[str, Any]] = None):
        """
        Initialize the metadata enricher.
        
        Args:
            repo_root: Optional root directory of the repository
            config: Optional configuration dictionary
        """
        self.repo_root = Path(repo_root) if repo_root else None
        self.config = config or {}
        
        # Cache for file modification times
        self.file_mod_times: Dict[str, str] = {}
        
        # Cache for file authors
        self.file_authors: Dict[str, str] = {}
        
        # Cache for file versions (from git tags)
        self.file_versions: Dict[str, str] = {}
        
        # Extract package version if available
        self.package_version = self._detect_package_version()
        
        # Detect repository URL if available
        self.repo_url = self._detect_repo_url()

    def _detect_package_version(self) -> Optional[str]:
        """
        Detect the version of the package.
        
        Returns:
            The detected version or None if not found
        """
        if not self.repo_root:
            return None
        
        # Check for version in setup.py
        setup_py = self.repo_root / 'setup.py'
        if setup_py.exists():
            with open(setup_py, 'r') as f:
                content = f.read()
                version_match = re.search(r'version\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                if version_match:
                    return version_match.group(1)
        
        # Check for version in pyproject.toml
        pyproject_toml = self.repo_root / 'pyproject.toml'
        if pyproject_toml.exists():
            with open(pyproject_toml, 'r') as f:
                content = f.read()
                version_match = re.search(r'version\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                if version_match:
                    return version_match.group(1)
        
        # Check for version in __init__.py files
        if self.repo_root:
            for init_file in self.repo_root.glob('**/__init__.py'):
                with open(init_file, 'r') as f:
                    content = f.read()
                    version_match = re.search(r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                    if version_match:
                        return version_match.group(1)
        
        return None

    def _detect_repo_url(self) -> Optional[str]:
        """
        Detect the URL of the repository.
        
        Returns:
            The repository URL or None if not found
        """
        if not self.repo_root:
            return None
        
        try:
            # Try to get the remote URL from git
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                url = result.stdout.strip()
                
                # Convert SSH URLs to HTTPS URLs
                if url.startswith('git@'):
                    # Convert git@github.com:user/repo.git to https://github.com/user/repo
                    url = url.replace(':', '/')
                    url = url.replace('git@', 'https://')
                
                # Remove .git suffix if present
                if url.endswith('.git'):
                    url = url[:-4]
                
                return url
        except Exception as e:
            logger.warning(f"Failed to detect repository URL: {e}")
        
        return None

    def get_file_modification_time(self, file_path: Union[str, Path]) -> str:
        """
        Get the last modification time of a file in ISO format.
        
        Args:
            file_path: Path to the file
            
        Returns:
            ISO formatted date string
        """
        path_str = str(file_path)
        
        # Check cache first
        if path_str in self.file_mod_times:
            return self.file_mod_times[path_str]
        
        try:
            # Try to get the modification time from git
            if self.repo_root:
                rel_path = Path(file_path).relative_to(self.repo_root)
                result = subprocess.run(
                    ['git', 'log', '-1', '--format=%ai', '--', str(rel_path)],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    # Parse the git date format and convert to ISO
                    date_str = result.stdout.strip()
                    dt = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z')
                    iso_date = dt.isoformat()
                    self.file_mod_times[path_str] = iso_date
                    return iso_date
        except Exception as e:
            logger.warning(f"Failed to get git modification time for {file_path}: {e}")
        
        # Fall back to file system modification time
        try:
            mtime = os.path.getmtime(file_path)
            dt = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
            iso_date = dt.isoformat()
            self.file_mod_times[path_str] = iso_date
            return iso_date
        except Exception as e:
            logger.warning(f"Failed to get file system modification time for {file_path}: {e}")
            
            # Return current time as fallback
            now = datetime.datetime.now(datetime.timezone.utc)
            return now.isoformat()

    def get_file_author(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Get the author of a file from git history.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Author name and email, or None if not found
        """
        path_str = str(file_path)
        
        # Check cache first
        if path_str in self.file_authors:
            return self.file_authors[path_str]
        
        try:
            # Try to get the author from git
            if self.repo_root:
                rel_path = Path(file_path).relative_to(self.repo_root)
                result = subprocess.run(
                    ['git', 'log', '-1', '--format=%an <%ae>', '--', str(rel_path)],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    author = result.stdout.strip()
                    self.file_authors[path_str] = author
                    return author
        except Exception as e:
            logger.warning(f"Failed to get git author for {file_path}: {e}")
        
        return None

    def get_file_version(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Get the version associated with a file.
        
        This attempts to find the latest git tag that affects this file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Version string or None if not found
        """
        path_str = str(file_path)
        
        # Check cache first
        if path_str in self.file_versions:
            return self.file_versions[path_str]
        
        # If we have a package version, use that
        if self.package_version:
            self.file_versions[path_str] = self.package_version
            return self.package_version
        
        try:
            # Try to get the version from git tags
            if self.repo_root:
                rel_path = Path(file_path).relative_to(self.repo_root)
                result = subprocess.run(
                    ['git', 'tag', '--sort=-creatordate', '--points-at', 'HEAD'],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    # Use the most recent tag
                    tag = result.stdout.strip().split('\n')[0]
                    self.file_versions[path_str] = tag
                    return tag
                
                # If no tag at HEAD, try to find the most recent tag
                result = subprocess.run(
                    ['git', 'describe', '--tags', '--abbrev=0'],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    tag = result.stdout.strip()
                    self.file_versions[path_str] = tag
                    return tag
        except Exception as e:
            logger.warning(f"Failed to get git version for {file_path}: {e}")
        
        return None

    def detect_stability(self, entity: Entity) -> Optional[str]:
        """
        Detect the stability of an entity based on various heuristics.
        
        Args:
            entity: The entity to analyze
            
        Returns:
            Stability indicator ('stable', 'experimental', 'deprecated', etc.) or None
        """
        # Check for stability markers in docstring or code
        docstring = entity.docstring or ""
        
        # Check for explicit stability markers
        if "deprecated" in docstring.lower():
            return "deprecated"
        
        if "experimental" in docstring.lower():
            return "experimental"
        
        if "alpha" in docstring.lower():
            return "alpha"
        
        if "beta" in docstring.lower():
            return "beta"
        
        if "stable" in docstring.lower():
            return "stable"
        
        # For functions and methods, check for usage of warnings.warn
        if isinstance(entity, FunctionEntity) and entity.code:
            if "warnings.warn" in entity.code or "DeprecationWarning" in entity.code:
                return "deprecated"
        
        # For classes, check if any methods use warnings
        if isinstance(entity, ClassEntity):
            for method in entity.methods:
                if hasattr(method, 'code') and method.code and ("warnings.warn" in method.code or "DeprecationWarning" in method.code):
                    return "deprecated"
        
        # Check for underscore prefixes in name (internal/private API)
        if entity.name.startswith('_') and not (entity.name.startswith('__') and entity.name.endswith('__')):
            return "internal"
        
        # Default to stable for public APIs with good test coverage
        return "stable"

    def extract_tags(self, entity: Entity) -> List[str]:
        """
        Extract tags from an entity's docstring or other attributes.
        
        Args:
            entity: The entity to analyze
            
        Returns:
            List of extracted tags
        """
        tags = []
        docstring = entity.docstring or ""
        
        # Look for explicit tag markers in docstring
        tag_matches = re.findall(r'[Tt]ags?\s*:\s*([^\n]+)', docstring)
        for match in tag_matches:
            # Split by commas and clean up each tag
            for tag in match.split(','):
                clean_tag = tag.strip().lower()
                if clean_tag:
                    tags.append(clean_tag)
        
        # Add category-based tags
        if isinstance(entity, ClassEntity):
            tags.append("class")
            
            # Check for common patterns in class names
            if entity.name.endswith('Exception') or entity.name.endswith('Error'):
                tags.append("exception")
            elif entity.name.endswith('Manager'):
                tags.append("manager")
            elif entity.name.endswith('Factory'):
                tags.append("factory")
            elif entity.name.endswith('Service'):
                tags.append("service")
            
            # Check for base classes patterns
            if any('test' in base.lower() for base in entity.base_classes):
                tags.append("test")
            
        elif isinstance(entity, FunctionEntity):
            if entity.is_method:
                tags.append("method")
            else:
                tags.append("function")
            
            # Check for test functions
            if entity.name.startswith('test_'):
                tags.append("test")
            
            # Check for async functions
            if entity.is_async:
                tags.append("async")
        
        # Check for specific keywords in the docstring
        keyword_to_tag = {
            "thread-safe": "threadsafe",
            "thread safe": "threadsafe",
            "deprecated": "deprecated",
            "experimental": "experimental",
            "example": "example",
            "utility": "utility",
            "helper": "helper",
            "performance": "performance",
            "optimization": "optimization"
        }
        
        for keyword, tag in keyword_to_tag.items():
            if keyword in docstring.lower():
                tags.append(tag)
        
        return list(set(tags))  # Deduplicate tags

    def enrich_entity(self, entity: Entity) -> Dict[str, Any]:
        """
        Enrich an entity with additional metadata.
        
        Args:
            entity: The entity to enrich
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        # Get file-based metadata if we have a file path
        if hasattr(entity, 'file_path') and entity.file_path:
            # Get modification time
            metadata['last_modified'] = self.get_file_modification_time(entity.file_path)
            
            # Get author information
            author = self.get_file_author(entity.file_path)
            if author:
                metadata['author'] = author
            
            # Get version information
            version = self.get_file_version(entity.file_path)
            if version:
                metadata['version'] = version
        
        # Add stability indicator
        stability = self.detect_stability(entity)
        if stability:
            metadata['stability'] = stability
        
        # Add tags
        tags = self.extract_tags(entity)
        if tags:
            metadata['tags'] = tags
        
        # Add repository information
        if self.repo_url:
            metadata['repository'] = self.repo_url
            
            # If we have a file path, add a direct link to the file
            if hasattr(entity, 'file_path') and entity.file_path and self.repo_root:
                try:
                    rel_path = Path(entity.file_path).relative_to(self.repo_root)
                    
                    # Format URL based on common hosting providers
                    if 'github.com' in self.repo_url:
                        file_url = f"{self.repo_url}/blob/main/{rel_path}"
                        if hasattr(entity, 'line_number') and entity.line_number:
                            file_url += f"#L{entity.line_number}"
                        metadata['source_url'] = file_url
                    elif 'gitlab.com' in self.repo_url:
                        file_url = f"{self.repo_url}/-/blob/main/{rel_path}"
                        if hasattr(entity, 'line_number') and entity.line_number:
                            file_url += f"#L{entity.line_number}"
                        metadata['source_url'] = file_url
                except Exception as e:
                    logger.warning(f"Failed to generate source URL: {e}")
        
        # Check for deprecation warnings in method code
        for method in entity.methods:
            if hasattr(method, 'code') and method.code and ("warnings.warn" in method.code or "DeprecationWarning" in method.code):
                metadata['stability'] = 'deprecated'
                metadata['deprecation_message'] = f"This class contains deprecated methods ({method.name})."
                break
        
        return metadata

    def enrich_entities(self, entities: List[Entity]) -> Dict[str, Dict[str, Any]]:
        """
        Enrich multiple entities with additional metadata.
        
        Args:
            entities: List of entities to enrich
            
        Returns:
            Dictionary mapping entity IDs to metadata dictionaries
        """
        result = {}
        
        for entity in entities:
            entity_id = self._get_entity_id(entity)
            metadata = self.enrich_entity(entity)
            result[entity_id] = metadata
        
        return result

    def _get_entity_id(self, entity: Entity) -> str:
        """
        Get a unique identifier for an entity.
        
        Args:
            entity: The entity to get an ID for
            
        Returns:
            A unique identifier string
        """
        if entity.module_name:
            if isinstance(entity, ModuleEntity):
                return entity.name
            elif isinstance(entity, ClassEntity):
                return f"{entity.module_name}.{entity.name}"
            elif isinstance(entity, FunctionEntity):
                if entity.is_method and entity.parent_class:
                    return f"{entity.module_name}.{entity.parent_class}.{entity.name}"
                return f"{entity.module_name}.{entity.name}"
            elif isinstance(entity, VariableEntity):
                return f"{entity.module_name}.{entity.name}"
        
        # Default case - use type and name
        return f"{type(entity).__name__}:{entity.name}"

    def get_metadata(self, entity: Entity) -> Dict[str, Any]:
        """
        Get metadata for an entity.
        
        Args:
            entity: The entity to get metadata for
            
        Returns:
            A dictionary of metadata
        """
        return self.enrich_entity(entity)

    def _get_entity_path(self, entity: Entity) -> str:
        """Get the path to the entity in the documentation."""
        if isinstance(entity, ModuleEntity):
            return entity.name.replace('.', '/')
        
        if isinstance(entity, ClassEntity):
            if hasattr(entity, 'module_name') and entity.module_name:
                return f"{entity.module_name.replace('.', '/')}/{entity.name}"
            return entity.name
        
        if isinstance(entity, FunctionEntity):
            if hasattr(entity, 'is_method') and entity.is_method and hasattr(entity, 'parent_class') and entity.parent_class:
                if hasattr(entity, 'module_name') and entity.module_name:
                    return f"{entity.module_name.replace('.', '/')}/{entity.parent_class}/{entity.name}"
                return f"{entity.parent_class}/{entity.name}"
            
            if hasattr(entity, 'module_name') and entity.module_name:
                return f"{entity.module_name.replace('.', '/')}/{entity.name}"
            return entity.name
        
        if isinstance(entity, VariableEntity):
            if hasattr(entity, 'module_name') and entity.module_name:
                return f"{entity.module_name.replace('.', '/')}/{entity.name}"
            return entity.name
        
        return str(entity.name)


if __name__ == "__main__":
    # Example usage
    enricher = MetadataEnricher()
    
    # To use, you would enrich entities with metadata
    # metadata = enricher.enrich_entity(some_entity) 