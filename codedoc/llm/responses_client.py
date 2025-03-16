"""
OpenAI Responses API client implementation.

This module provides a client for interacting with OpenAI's Responses API,
which is their most advanced interface for generating model responses.
It supports text and image inputs, stateful interactions, and built-in tools.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union
import time
from functools import wraps

import tiktoken
import openai
from openai import OpenAI

from codedoc.llm.base import LLMClient, LLMResponse, LLMError

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "gpt-4o"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 60  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def retry_on_error(max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Decorator to retry API calls on certain errors."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError) as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded: {str(e)}")
                        raise LLMError(f"Max retries exceeded: {str(e)}")
                    
                    wait_time = delay * (2 ** (retries - 1))  # Exponential backoff
                    logger.warning(f"API error: {str(e)}. Retrying in {wait_time}s (Attempt {retries}/{max_retries})")
                    time.sleep(wait_time)
                except Exception as e:
                    # Don't retry other types of exceptions
                    logger.error(f"Error in OpenAI API call: {str(e)}")
                    raise LLMError(f"OpenAI API error: {str(e)}")
        return wrapper
    return decorator


class ResponsesClient(LLMClient):
    """Client for interacting with OpenAI's Responses API."""
    
    def __init__(self, api_key: Optional[str] = None, organization: Optional[str] = None, **kwargs):
        """
        Initialize the OpenAI Responses client.
        
        Args:
            api_key: OpenAI API key (optional, will use OPENAI_API_KEY env var if not provided)
            organization: OpenAI organization ID (optional)
            **kwargs: Additional configuration options
                - default_model: Default model to use (defaults to DEFAULT_MODEL)
                - max_tokens: Default max tokens (defaults to DEFAULT_MAX_TOKENS)
                - timeout: API timeout in seconds (defaults to DEFAULT_TIMEOUT)
        """
        # Get API key from environment if not provided
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("API key must be provided or set as OPENAI_API_KEY environment variable")
        
        # Initialize client
        client_kwargs = {"api_key": api_key}
        if organization:
            client_kwargs["organization"] = organization
            
        self.client = OpenAI(**client_kwargs)
        
        # Store configuration
        self.default_model = kwargs.get("default_model", DEFAULT_MODEL)
        self.max_tokens = kwargs.get("max_tokens", DEFAULT_MAX_TOKENS)
        self.timeout = kwargs.get("timeout", DEFAULT_TIMEOUT)
        
        logger.info(f"Initialized OpenAI Responses client with model {self.default_model}")
    
    @retry_on_error()
    def generate(self, 
                prompt: str, 
                system_prompt: Optional[str] = None,
                model: Optional[str] = None, 
                max_tokens: Optional[int] = None,
                temperature: float = 0.7,
                **kwargs) -> LLMResponse:
        """
        Generate a response using the OpenAI Responses API.
        
        Args:
            prompt: The prompt to send to the model
            system_prompt: Optional system instructions
            model: The specific model to use (defaults to default_model)
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            LLMResponse object containing the generated content and metadata
            
        Raises:
            LLMError: If the API call fails or returns an error
        """
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens
        
        logger.debug(f"Generating response with model {model}, max_tokens={max_tokens}, temp={temperature}")
        
        # Prepare request parameters
        request_params = {
            "model": model,
            "input": prompt,
            "temperature": temperature,
            "text": {"format": {"type": "text"}},
        }
        
        # Add optional parameters
        if system_prompt:
            request_params["instructions"] = system_prompt
            
        if max_tokens:
            request_params["max_output_tokens"] = max_tokens
            
        # Add any additional parameters
        for key, value in kwargs.items():
            if key not in request_params:
                request_params[key] = value
        
        try:
            # Call the Responses API
            response = self.client.responses.create(**request_params)
            
            # Extract the content from the response
            # The output format from Responses API is different from chat completions
            content = ""
            if response.output and len(response.output) > 0:
                for output_item in response.output:
                    if output_item.type == "message" and output_item.content:
                        for content_item in output_item.content:
                            if content_item.type == "output_text":
                                content += content_item.text
            
            # Extract usage information
            tokens_used = response.usage.total_tokens
            tokens_prompt = response.usage.input_tokens
            tokens_completion = response.usage.output_tokens
            
            logger.debug(f"Response generated successfully. Using {tokens_used} tokens")
            
            return LLMResponse(
                content=content,
                model=model,
                tokens_used=tokens_used,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                finish_reason="stop",  # The Responses API doesn't provide this explicitly
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise LLMError(f"Error generating response: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens
        """
        try:
            encoding = tiktoken.encoding_for_model(self.default_model)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Error calculating tokens: {str(e)}. Using fallback approximation.")
            # Fallback: rough approximation (4 chars ≈ 1 token)
            return len(text) // 4
    
    def get_model_name(self) -> str:
        """
        Get the name of the currently configured model.
        
        Returns:
            Model name as a string
        """
        return self.default_model 