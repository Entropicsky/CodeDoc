"""
Metadata generator for extracting metadata from files.

This module provides functionality for generating metadata about files
that can be used to enhance vector search and retrieval.
"""

import os
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Union, Optional, List
import mimetypes
import re

class MetadataGenerator:
    """
    Generates metadata for files to enhance vector search and retrieval.
    """
    
    def __init__(self):
        """
        Initialize the metadata generator.
        """
        # Initialize mimetypes
        mimetypes.init()
        
        # Define known file extensions and their language mappings
        self.language_by_extension = {
            # Python
            '.py': 'python',
            # JavaScript
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            # Web
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            # C-family
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            # Java
            '.java': 'java',
            '.kt': 'kotlin',
            '.kts': 'kotlin',
            # Go
            '.go': 'go',
            # Ruby
            '.rb': 'ruby',
            # PHP
            '.php': 'php',
            # Swift
            '.swift': 'swift',
            # Rust
            '.rs': 'rust',
            # Markdown/Text
            '.md': 'markdown',
            '.txt': 'text',
            '.rst': 'restructuredtext',
            # Config
            '.json': 'json',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.xml': 'xml',
            # Shell
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'zsh',
            '.fish': 'fish',
            '.bat': 'batch',
            '.ps1': 'powershell',
            # Other
            '.sql': 'sql',
            '.graphql': 'graphql',
            '.proto': 'protobuf',
        }

    def generate_metadata(self, file_path: Union[str, Path], content: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate metadata for a file.
        
        Args:
            file_path: Path to the file
            content: Optional pre-loaded content of the file
            
        Returns:
            Dictionary containing metadata about the file
        """
        file_path = Path(file_path)
        
        # Basic file metadata
        stat = file_path.stat()
        
        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size_bytes": stat.st_size,
            "created_at": stat.st_ctime,
            "modified_at": stat.st_mtime,
            "created_at_iso": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(stat.st_ctime)),
            "modified_at_iso": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(stat.st_mtime)),
        }
        
        # Try to determine mime type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            metadata["mime_type"] = mime_type
            
        # Determine language based on file extension
        if file_path.suffix.lower() in self.language_by_extension:
            metadata["language"] = self.language_by_extension[file_path.suffix.lower()]
            
        # If we have content, add more detailed metadata
        if content is not None:
            # Generate content hash
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            metadata["content_hash"] = content_hash
            
            # Basic content stats
            lines = content.split('\n')
            metadata["line_count"] = len(lines)
            metadata["character_count"] = len(content)
            metadata["word_count"] = len(re.findall(r'\b\w+\b', content))
            
            # Add language-specific metadata
            self._add_language_specific_metadata(metadata, content)
            
        return metadata
    
    def _add_language_specific_metadata(self, metadata: Dict[str, Any], content: str) -> None:
        """
        Add language-specific metadata based on the file's language.
        
        Args:
            metadata: Metadata dictionary to update
            content: File content to analyze
        """
        language = metadata.get("language")
        
        if not language:
            return
            
        # Process based on language
        if language == "python":
            self._process_python_metadata(metadata, content)
        elif language in ["javascript", "typescript"]:
            self._process_js_ts_metadata(metadata, content)
        elif language in ["java", "kotlin"]:
            self._process_java_metadata(metadata, content)
        elif language == "markdown":
            self._process_markdown_metadata(metadata, content)
    
    def _process_python_metadata(self, metadata: Dict[str, Any], content: str) -> None:
        """
        Extract Python-specific metadata.
        
        Args:
            metadata: Metadata dictionary to update
            content: File content to analyze
        """
        # Check for imports
        import_lines = re.findall(r'^import\s+([^\n]+)', content, re.MULTILINE)
        from_import_lines = re.findall(r'^from\s+([^\s]+)\s+import\s+([^\n]+)', content, re.MULTILINE)
        
        imports = []
        for line in import_lines:
            imports.extend([imp.strip() for imp in line.split(',')])
            
        for module, items in from_import_lines:
            module = module.strip()
            for item in items.split(','):
                item = item.strip()
                if item:  # Skip empty items
                    if ' as ' in item:
                        item = item.split(' as ')[0].strip()
                    imports.append(f"{module}.{item}")
        
        if imports:
            metadata["imports"] = sorted(list(set(imports)))
            
        # Check for class definitions
        classes = re.findall(r'^\s*class\s+([a-zA-Z0-9_]+)', content, re.MULTILINE)
        if classes:
            metadata["classes"] = classes
            
        # Check for function definitions
        functions = re.findall(r'^\s*def\s+([a-zA-Z0-9_]+)', content, re.MULTILINE)
        if functions:
            metadata["functions"] = functions
            
        # Check for docstring
        docstring_match = re.search(r'"""(.+?)"""', content, re.DOTALL)
        if docstring_match:
            docstring = docstring_match.group(1).strip()
            metadata["has_docstring"] = True
            
            # Extract module description from docstring
            first_line = docstring.split('\n')[0].strip()
            if first_line:
                metadata["description"] = first_line
    
    def _process_js_ts_metadata(self, metadata: Dict[str, Any], content: str) -> None:
        """
        Extract JavaScript/TypeScript-specific metadata.
        
        Args:
            metadata: Metadata dictionary to update
            content: File content to analyze
        """
        # Check for imports
        imports = []
        
        # ES6 imports
        import_from = re.findall(r'import\s+{([^}]+)}\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        for items, module in import_from:
            for item in items.split(','):
                item = item.strip()
                if item:
                    if ' as ' in item:
                        item = item.split(' as ')[0].strip()
                    imports.append(f"{module}/{item}")
                    
        # Default imports
        default_imports = re.findall(r'import\s+([a-zA-Z0-9_$]+)\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        for item, module in default_imports:
            imports.append(f"{module}/{item}")
            
        # Require imports
        require_imports = re.findall(r'(?:const|let|var)\s+([a-zA-Z0-9_${}]+)\s*=\s*require\s*\([\'"]([^\'"]+)[\'"]\)', content)
        for item, module in require_imports:
            item = item.strip('{}')
            imports.append(f"{module}/{item}")
            
        if imports:
            metadata["imports"] = sorted(list(set(imports)))
            
        # Check for class definitions
        classes = re.findall(r'class\s+([a-zA-Z0-9_$]+)', content)
        if classes:
            metadata["classes"] = classes
            
        # Check for function definitions
        functions = re.findall(r'function\s+([a-zA-Z0-9_$]+)', content)
        # Also look for arrow functions and method definitions
        functions.extend(re.findall(r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*\([^)]*\)\s*=>', content))
        functions.extend(re.findall(r'(?:async\s+)?([a-zA-Z0-9_$]+)\s*\(', content))
        
        if functions:
            # Filter out duplicates and common non-function matches (like if, for, etc.)
            non_functions = {'if', 'for', 'while', 'switch', 'catch', 'map', 'filter', 'reduce', 'forEach'}
            functions = [f for f in set(functions) if f not in non_functions]
            if functions:
                metadata["functions"] = sorted(functions)
    
    def _process_java_metadata(self, metadata: Dict[str, Any], content: str) -> None:
        """
        Extract Java/Kotlin-specific metadata.
        
        Args:
            metadata: Metadata dictionary to update
            content: File content to analyze
        """
        # Check for package
        package_match = re.search(r'package\s+([a-zA-Z0-9_.]+);', content)
        if package_match:
            metadata["package"] = package_match.group(1)
            
        # Check for imports
        imports = re.findall(r'import\s+([a-zA-Z0-9_.]+);', content)
        if imports:
            metadata["imports"] = sorted(imports)
            
        # Check for class definitions
        classes = re.findall(r'(?:public|private|protected)?\s*(?:final|abstract)?\s*class\s+([a-zA-Z0-9_]+)', content)
        interfaces = re.findall(r'(?:public|private|protected)?\s*interface\s+([a-zA-Z0-9_]+)', content)
        
        if classes:
            metadata["classes"] = classes
        if interfaces:
            metadata["interfaces"] = interfaces
            
        # Check for method definitions
        methods = re.findall(r'(?:public|private|protected)?\s*(?:static|final|abstract)?\s*(?:[a-zA-Z0-9_<>[\],\s]+)\s+([a-zA-Z0-9_]+)\s*\(', content)
        if methods:
            # Filter out constructor names (same as class name)
            class_names = set(classes) if classes else set()
            methods = [m for m in methods if m not in class_names or methods.count(m) > 1]
            if methods:
                metadata["methods"] = sorted(list(set(methods)))
    
    def _process_markdown_metadata(self, metadata: Dict[str, Any], content: str) -> None:
        """
        Extract Markdown-specific metadata.
        
        Args:
            metadata: Metadata dictionary to update
            content: File content to analyze
        """
        # Extract headings
        h1_matches = re.findall(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_matches:
            metadata["title"] = h1_matches[0].strip()
            
        # Get all headings
        headings = []
        for i in range(1, 7):  # h1 to h6
            pattern = r'^#{' + str(i) + r'}\s+(.+)$'
            matches = re.findall(pattern, content, re.MULTILINE)
            headings.extend([(i, heading.strip()) for heading in matches])
            
        if headings:
            # Format as {level: heading_text}
            metadata["headings"] = [{"level": level, "text": text} for level, text in headings]
            
            # Also create a flat list of just the heading text for easier searching
            metadata["heading_text"] = [text for _, text in headings]
            
        # Check for links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        if links:
            metadata["links"] = [{"text": text, "url": url} for text, url in links]
            
        # Count code blocks
        code_blocks = re.findall(r'```([a-zA-Z0-9]*)\n', content)
        if code_blocks:
            metadata["code_block_count"] = len(code_blocks)
            
            # Count by language
            language_counts = {}
            for lang in code_blocks:
                lang = lang.lower().strip() or "text"  # Default to "text" if no language specified
                language_counts[lang] = language_counts.get(lang, 0) + 1
                
            metadata["code_block_languages"] = language_counts 