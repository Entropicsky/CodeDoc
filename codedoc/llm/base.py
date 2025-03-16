"""
Base classes for LLM client implementations.

This module defines the abstract interfaces and common functionality for LLM clients,
including response handling, error management, and the core client interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union


class LLMError(Exception):
    """Exception raised for errors in LLM API interactions."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict] = None):
        """
        Initialize LLM error with details.
        
        Args:
            message: Error message
            status_code: HTTP status code if applicable
            details: Additional error details
        """
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


@dataclass
class LLMResponse:
    """Container for LLM API responses."""
    
    content: str
    model: str
    tokens_used: int
    tokens_prompt: int
    tokens_completion: int
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None
    
    @property
    def total_tokens(self) -> int:
        """Get the total number of tokens used."""
        return self.tokens_prompt + self.tokens_completion


class LLMClient(ABC):
    """Abstract base class for LLM API clients."""
    
    @abstractmethod
    def generate(self, 
                prompt: str, 
                system_prompt: Optional[str] = None,
                temperature: float = 0.7,
                max_tokens: Optional[int] = None,
                stop_sequences: Optional[List[str]] = None,
                **kwargs) -> LLMResponse:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The user prompt to send to the LLM
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            stop_sequences: Sequences that stop generation
            **kwargs: Additional model-specific parameters
            
        Returns:
            LLMResponse object containing the generated content and metadata
            
        Raises:
            LLMError: If the API request fails
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name of the currently configured model.
        
        Returns:
            Model name as a string
        """
        pass 