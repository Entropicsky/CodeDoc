"""
Language detector for CodeDoc.

This module provides functionality to detect the programming language of a file
based on its extension, shebang line, and content analysis.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

# Language-specific file extensions
LANGUAGE_EXTENSIONS: Dict[str, str] = {
    # Python
    ".py": "python",
    ".pyi": "python",
    ".pyx": "python",
    ".pxd": "python",
    ".pyw": "python",
    
    # JavaScript
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    
    # TypeScript
    ".ts": "typescript",
    ".tsx": "typescript",
    
    # Configuration files
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    
    # Markup
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "restructuredtext",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    
    # Shell scripts
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    
    # C/C++
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    
    # Java
    ".java": "java",
    
    # Go
    ".go": "go",
    
    # Ruby
    ".rb": "ruby",
    
    # Rust
    ".rs": "rust",
    
    # Others
    ".sql": "sql",
    ".dockerfile": "dockerfile",
    ".tf": "terraform",
    ".hcl": "hcl",
}

# Shebang patterns for language detection
SHEBANG_PATTERNS: Dict[str, str] = {
    r"^#!.*\bpython3?\b": "python",
    r"^#!.*\bnode\b": "javascript",
    r"^#!.*\bbash\b": "shell",
    r"^#!.*\bzsh\b": "shell",
    r"^#!.*\bruby\b": "ruby",
    r"^#!.*\bperl\b": "perl",
    r"^#!.*\bsh\b": "shell",
}

# Content patterns for language detection
CONTENT_PATTERNS: Dict[str, Dict[str, int]] = {
    # Keywords that strongly indicate language, with weights
    "python": {
        r"\bdef\s+\w+\s*\(": 5,
        r"\bimport\s+\w+": 3,
        r"\bfrom\s+\w+\s+import\b": 5,
        r"\bclass\s+\w+\s*(\(.*\))?:": 5,
        r"\bif\s+__name__\s*==\s*['\"]__main__['\"]\s*:": 10,
    },
    "javascript": {
        r"\bconst\s+\w+\s*=": 3,
        r"\blet\s+\w+\s*=": 3,
        r"\bvar\s+\w+\s*=": 3,
        r"\bfunction\s+\w+\s*\(": 5,
        r"\bexport\s+(default\s+)?": 5,
        r"\bimport\s+{.*}\s+from\b": 5,
        r"\breturn\s+.*;": 2,
    },
    "typescript": {
        r"\binterface\s+\w+\s*{": 8,
        r"\btype\s+\w+\s*=": 8,
        r"\bclass\s+\w+\s*implements\b": 8,
        r":\s*\w+(\[\])?\s*=>": 5,
        r":\s*\w+(\[\])?\s*[,;=)]": 3,
    },
    "shell": {
        r"\becho\s+": 2,
        r"\bexport\s+\w+\s*=": 3,
        r"if\s+\[\s+": 3,
        r"\bfor\s+\w+\s+in\b": 3,
        r"\$\(\(.*\)\)": 5,
    },
}

# Files that should be ignored by the parser
IGNORED_FILES: Set[str] = {
    "LICENSE",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "README.md",
    ".gitignore",
    ".dockerignore",
    ".editorconfig",
}

# Directories that should be ignored by the parser
IGNORED_DIRS: Set[str] = {
    ".git",
    ".github",
    ".vscode",
    ".idea",
    "node_modules",
    "venv",
    "env",
    "build",
    "dist",
    "__pycache__",
}


def detect_language_from_extension(file_path: Union[str, Path]) -> Optional[str]:
    """Detect the programming language of a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Detected language or None if unknown
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    # Check if the file has a known extension
    if ext in LANGUAGE_EXTENSIONS:
        return LANGUAGE_EXTENSIONS[ext]
    
    # Check for special files
    if file_path.name.lower() == "dockerfile":
        return "dockerfile"
    
    return None


def detect_language_from_shebang(file_content: str) -> Optional[str]:
    """Detect the programming language of a file based on its shebang line.
    
    Args:
        file_content: Content of the file
        
    Returns:
        str: Detected language or None if unknown
    """
    # Get the first line of the file
    first_line = file_content.strip().split("\n")[0] if file_content else ""
    
    # Check if the file has a shebang line
    for pattern, language in SHEBANG_PATTERNS.items():
        if re.match(pattern, first_line):
            return language
    
    return None


def detect_language_from_content(file_content: str) -> Optional[str]:
    """Detect the programming language of a file based on content analysis.
    
    Args:
        file_content: Content of the file
        
    Returns:
        str: Detected language or None if unknown
    """
    # Skip empty files
    if not file_content or len(file_content) < 10:
        return None
    
    # Score each language based on content patterns
    scores: Dict[str, int] = {lang: 0 for lang in CONTENT_PATTERNS}
    
    for language, patterns in CONTENT_PATTERNS.items():
        for pattern, weight in patterns.items():
            matches = re.findall(pattern, file_content)
            scores[language] += len(matches) * weight
    
    # Get the language with the highest score
    if not scores:
        return None
    
    best_language = max(scores.items(), key=lambda x: x[1])
    
    # Only return a language if the score is above a threshold
    if best_language[1] > 5:
        return best_language[0]
    
    return None


def detect_language(file_path: Union[str, Path]) -> Optional[str]:
    """Detect the programming language of a file using multiple methods.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Detected language or None if unknown
    """
    file_path = Path(file_path)
    
    # Skip ignored files
    if file_path.name in IGNORED_FILES:
        return None
    
    # Try to detect based on extension first (fastest)
    language = detect_language_from_extension(file_path)
    if language:
        return language
    
    # If extension detection fails, try content analysis
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Try shebang detection
        language = detect_language_from_shebang(content)
        if language:
            return language
        
        # Try content analysis
        language = detect_language_from_content(content)
        if language:
            return language
    except Exception as e:
        # If there's an error reading the file, skip it
        return None
    
    return None


def is_binary_file(file_path: Union[str, Path]) -> bool:
    """Check if a file is binary.
    
    Args:
        file_path: Path to the file
        
    Returns:
        bool: True if the file is binary, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1024)  # Try to read as text
        return False
    except UnicodeDecodeError:
        return True


def find_parsable_files(dir_path: Union[str, Path]) -> Dict[str, List[Path]]:
    """Find all parsable files in a directory grouped by language.
    
    Args:
        dir_path: Path to the directory
        
    Returns:
        Dict[str, List[Path]]: Dictionary mapping languages to file paths
    """
    dir_path = Path(dir_path)
    result: Dict[str, List[Path]] = {}
    
    for root, dirs, files in os.walk(dir_path):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        
        for file in files:
            file_path = Path(root) / file
            
            # Skip binary files
            if is_binary_file(file_path):
                continue
            
            # Detect the language
            language = detect_language(file_path)
            if language:
                if language not in result:
                    result[language] = []
                result[language].append(file_path)
    
    return result 