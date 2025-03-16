#!/usr/bin/env python3
"""
Parser registry for the CodeDoc framework.

This module defines the ParserRegistry class that manages language-specific
parsers and provides methods to find the appropriate parser for a file.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Type, Union

from .base_parser import BaseParser
from .parser_config import ParserConfig

logger = logging.getLogger(__name__)


class ParserRegistry:
    """
    Registry for language parsers.
    
    This class maintains a registry of parser classes for different languages
    and provides methods to find the appropriate parser for a file.
    """
    
    # Registry of parser classes by language
    _parsers: Dict[str, Type[BaseParser]] = {}
    
    # Mapping of file extensions to parser languages
    _extension_map: Dict[str, str] = {}
    
    @classmethod
    def register(cls, parser_class: Type[BaseParser]) -> None:
        """
        Register a parser class.
        
        Args:
            parser_class: Parser class to register
        """
        language = parser_class.get_language()
        
        # Register the parser by language
        cls._parsers[language] = parser_class
        
        # Register file extensions
        for ext in parser_class.get_file_extensions():
            ext_lower = ext.lower()
            if ext_lower in cls._extension_map and cls._extension_map[ext_lower] != language:
                logger.warning(
                    f"File extension '{ext}' is already registered for language "
                    f"'{cls._extension_map[ext_lower]}', overriding with '{language}'"
                )
            cls._extension_map[ext_lower] = language
        
        logger.debug(f"Registered parser for language '{language}'")
    
    @classmethod
    def get_parser_for_language(cls, language: str, config: Optional[ParserConfig] = None) -> Optional[BaseParser]:
        """
        Get a parser instance for the specified language.
        
        Args:
            language: Language identifier
            config: Parser configuration
            
        Returns:
            Parser instance or None if no parser is registered for the language
        """
        parser_class = cls._parsers.get(language)
        if parser_class:
            return parser_class(config)
        return None
    
    @classmethod
    def get_parser_for_file(cls, file_path: Union[str, Path], config: Optional[ParserConfig] = None) -> Optional[BaseParser]:
        """
        Get a parser instance for the specified file.
        
        Args:
            file_path: Path to the file
            config: Parser configuration
            
        Returns:
            Parser instance or None if no suitable parser is found
        """
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        ext = file_path.suffix.lower()
        
        # Try to find a parser based on file extension
        if ext in cls._extension_map:
            language = cls._extension_map[ext]
            return cls.get_parser_for_language(language, config)
        
        # If no parser found by extension, try each parser's supports_file method
        for parser_class in cls._parsers.values():
            parser = parser_class(config)
            if parser.supports_file(file_path):
                return parser
        
        return None
    
    @classmethod
    def get_registered_languages(cls) -> List[str]:
        """
        Get a list of registered languages.
        
        Returns:
            List of registered language identifiers
        """
        return list(cls._parsers.keys())
    
    @classmethod
    def get_registered_extensions(cls) -> Dict[str, str]:
        """
        Get a mapping of registered file extensions to languages.
        
        Returns:
            Dictionary mapping file extensions to language identifiers
        """
        return dict(cls._extension_map) 