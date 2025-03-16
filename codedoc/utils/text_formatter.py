#!/usr/bin/env python3
"""
Text Formatter for CodeDoc.

This module provides utilities for formatting text in documentation,
including fixing character-by-character spacing issues and
standardizing text formats.
"""

import re
import logging
from typing import List, Dict, Optional, Any, Set, Tuple, Union

logger = logging.getLogger(__name__)


class TextFormatter:
    """
    Utilities for formatting text in documentation.
    
    This class provides methods to fix common formatting issues,
    particularly character-by-character spacing that can occur
    in implementation notes or other generated text.
    """
    
    @staticmethod
    def fix_character_spacing(text: str, verbose: bool = False) -> str:
        """
        Fix character-by-character spacing issues in text.
        
        Args:
            text: The text to fix spacing in
            verbose: Whether to log before and after text
            
        Returns:
            Text with spacing issues fixed
        """
        if not text:
            return text
            
        # Store original text for logging
        original_text = text
        
        # Common patterns to fix directly
        common_replacements = {
            'E x t e r n a l': 'External',
            'D e p e n d e n c i e s': 'Dependencies',
            'I n t e r n a l': 'Internal',
            't y p i n g': 'typing',
            't e s t _ m o d u l e': 'test_module',
            'i m p o r t': 'import',
            'f r o m': 'from',
            'm o d u l e': 'module',
            'c l a s s': 'class',
            'f u n c t i o n': 'function',
            'm e t h o d': 'method',
            'v a r i a b l e': 'variable',
            'c o n s t a n t': 'constant',
            'C l a s s e s': 'Classes',
            'F u n c t i o n s': 'Functions',
            'M e t h o d s': 'Methods',
            'V a r i a b l e s': 'Variables',
            'C o n s t a n t s': 'Constants'
        }
        
        # Apply direct replacements
        for pattern, replacement in common_replacements.items():
            text = text.replace(pattern, replacement)
        
        # Apply regex replacements for general cases
        # This matches sequences of single characters separated by spaces
        # and replaces them with joined characters
        patterns = [
            (r'(\w) (\w) (\w) (\w) (\w) (\w) (\w) (\w) (\w) (\w)', r'\1\2\3\4\5\6\7\8\9\10'),
            (r'(\w) (\w) (\w) (\w) (\w) (\w) (\w) (\w) (\w)', r'\1\2\3\4\5\6\7\8\9'),
            (r'(\w) (\w) (\w) (\w) (\w) (\w) (\w) (\w)', r'\1\2\3\4\5\6\7\8'),
            (r'(\w) (\w) (\w) (\w) (\w) (\w) (\w)', r'\1\2\3\4\5\6\7'),
            (r'(\w) (\w) (\w) (\w) (\w) (\w)', r'\1\2\3\4\5\6'),
            (r'(\w) (\w) (\w) (\w) (\w)', r'\1\2\3\4\5'),
            (r'(\w) (\w) (\w) (\w)', r'\1\2\3\4'),
            (r'(\w) (\w) (\w)', r'\1\2\3'),
            (r'(\w) (\w)', r'\1\2')
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        
        # Clean up any remaining excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        if verbose and original_text != text:
            logger.info(f"Text before formatting: {original_text}")
            logger.info(f"Text after formatting: {text}")
            
        return text
    
    @staticmethod
    def format_module_implementation_notes(notes: str, verbose: bool = False) -> str:
        """
        Format implementation notes for a module.
        
        Args:
            notes: The implementation notes to format
            verbose: Whether to log before and after text
            
        Returns:
            Formatted implementation notes
        """
        return TextFormatter.fix_character_spacing(notes, verbose)
    
    @staticmethod
    def format_class_implementation_notes(notes: str, verbose: bool = False) -> str:
        """
        Format implementation notes for a class.
        
        Args:
            notes: The implementation notes to format
            verbose: Whether to log before and after text
            
        Returns:
            Formatted implementation notes
        """
        return TextFormatter.fix_character_spacing(notes, verbose)
    
    @staticmethod
    def format_function_implementation_notes(notes: str, verbose: bool = False) -> str:
        """
        Format implementation notes for a function.
        
        Args:
            notes: The implementation notes to format
            verbose: Whether to log before and after text
            
        Returns:
            Formatted implementation notes
        """
        return TextFormatter.fix_character_spacing(notes, verbose)
    
    @staticmethod
    def format_variable_implementation_notes(notes: str, verbose: bool = False) -> str:
        """
        Format implementation notes for a variable.
        
        Args:
            notes: The implementation notes to format
            verbose: Whether to log before and after text
            
        Returns:
            Formatted implementation notes
        """
        return TextFormatter.fix_character_spacing(notes, verbose)


# Simple test code
if __name__ == "__main__":
    # Test with some examples
    examples = [
        "E x t e r n a l D e p e n d e n c i e s : t y p i n g",
        "I n t e r n a l D e p e n d e n c i e s : t e s t _ m o d u l e",
        "C l a s s e s : BaseClass, TestClass",
        "F u n c t i o n s : test_function, another_function"
    ]
    
    for example in examples:
        fixed = TextFormatter.fix_character_spacing(example, verbose=True)
        print(f"Original: {example}")
        print(f"Fixed: {fixed}")
        print() 