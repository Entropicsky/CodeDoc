"""
Google Gemini API client implementation.

This module provides a client for interacting with Google's Gemini API,
handling authentication, prompt formatting, and response processing.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union
import time
from functools import wraps

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError

from codedoc.llm.base import LLMClient, LLMResponse, LLMError

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "gemini-1.5-pro"
DEFAULT_MAX_TOKENS = 8192
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
                except (GoogleAPIError, TimeoutError, ConnectionError) as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded: {str(e)}")
                        raise LLMError(f"Max retries exceeded: {str(e)}")
                    
                    wait_time = delay * (2 ** (retries - 1))  # Exponential backoff
                    logger.warning(f"API error: {str(e)}. Retrying in {wait_time}s (Attempt {retries}/{max_retries})")
                    time.sleep(wait_time)
                except Exception as e:
                    # Don't retry other types of exceptions
                    logger.error(f"Error in Gemini API call: {str(e)}")
                    raise LLMError(f"Gemini API error: {str(e)}")
        return wrapper
    return decorator


class GeminiClient(LLMClient):
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Google API key. If None, tries to load from GOOGLE_API_KEY env var.
            **kwargs: Additional client configuration options.
        
        Raises:
            LLMError: If no API key is found or initialization fails.
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise LLMError("Google API key not provided and not found in environment variables")
        
        try:
            genai.configure(api_key=self.api_key)
            self._safety_settings = kwargs.get("safety_settings", [])
            logger.debug("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise LLMError(f"Failed to initialize Gemini client: {str(e)}")
    
    @retry_on_error()
    def generate(self, 
                prompt: str, 
                model: Optional[str] = None, 
                max_tokens: Optional[int] = None,
                temperature: float = 0.7,
                **kwargs) -> LLMResponse:
        """
        Generate a response from the Gemini API.
        
        Args:
            prompt: The prompt to send to the model
            model: The specific model to use (defaults to DEFAULT_MODEL)
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            LLMResponse object containing the generated content and metadata
            
        Raises:
            LLMError: If the API call fails or returns an error
        """
        model_name = model or DEFAULT_MODEL
        max_output_tokens = max_tokens or DEFAULT_MAX_TOKENS
        
        logger.debug(f"Generating response with model {model_name}, max_tokens={max_output_tokens}, temp={temperature}")
        
        try:
            model = genai.GenerativeModel(model_name=model_name)
            
            generation_config = {
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
                **kwargs
            }
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=self._safety_settings
            )
            
            content = response.text
            
            # Gemini doesn't provide token usage directly, so we'll estimate
            prompt_tokens = self.calculate_tokens(prompt)
            completion_tokens = self.calculate_tokens(content)
            total_tokens = prompt_tokens + completion_tokens
            
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
            
            logger.debug(f"Response generated successfully. Estimated usage: {usage}")
            
            return LLMResponse(
                content=content,
                model=model_name,
                usage=usage,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise LLMError(f"Error generating response: {str(e)}")
    
    @retry_on_error()
    def generate_with_system_prompt(self,
                               system_prompt: str,
                               user_prompt: str,
                               model: Optional[str] = None,
                               max_tokens: Optional[int] = None,
                               temperature: float = 0.7,
                               **kwargs) -> LLMResponse:
        """
        Generate a response with a system prompt and user prompt.
        
        Args:
            system_prompt: Instructions to the model about how to behave
            user_prompt: The user's input/question
            model: The specific model to use (defaults to DEFAULT_MODEL)
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            LLMResponse object containing the generated content and metadata
            
        Raises:
            LLMError: If the API call fails or returns an error
        """
        model_name = model or DEFAULT_MODEL
        max_output_tokens = max_tokens or DEFAULT_MAX_TOKENS
        
        logger.debug(f"Generating response with system prompt, model {model_name}")
        
        try:
            model = genai.GenerativeModel(model_name=model_name)
            
            generation_config = {
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
                **kwargs
            }
            
            # Gemini uses chat format for system/user prompts
            chat = model.start_chat(history=[])
            
            # Add system prompt as a user message with special prefix
            response = chat.send_message(
                f"<system>\n{system_prompt}\n</system>\n\n{user_prompt}",
                generation_config=generation_config,
                safety_settings=self._safety_settings
            )
            
            content = response.text
            
            # Estimate token usage
            prompt_tokens = self.calculate_tokens(system_prompt) + self.calculate_tokens(user_prompt)
            completion_tokens = self.calculate_tokens(content)
            total_tokens = prompt_tokens + completion_tokens
            
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
            
            logger.debug(f"Response generated successfully. Estimated usage: {usage}")
            
            return LLMResponse(
                content=content,
                model=model_name,
                usage=usage,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Error generating response with system prompt: {str(e)}")
            raise LLMError(f"Error generating response with system prompt: {str(e)}")
    
    def calculate_tokens(self, text: str) -> int:
        """
        Calculate the number of tokens in the given text.
        
        Args:
            text: The text to calculate tokens for
            
        Returns:
            The number of tokens in the text
        """
        # Gemini doesn't provide a direct token counter
        # This is a rough approximation based on character count (1 token ≈ 4 chars)
        return len(text) // 4
    
    def get_available_models(self) -> List[str]:
        """
        Get a list of available Gemini models.
        
        Returns:
            List of model identifiers that can be used with this client
        """
        try:
            models = genai.list_models()
            return [model.name for model in models if "gemini" in model.name.lower()]
        except Exception as e:
            logger.error(f"Error retrieving available models: {str(e)}")
            raise LLMError(f"Error retrieving available models: {str(e)}")
    
    def validate_api_key(self) -> bool:
        """
        Validate that the Google API key works.
        
        Returns:
            True if the API key is valid, False otherwise
        """
        try:
            # Try to list models as a simple API call to check auth
            genai.list_models()
            return True
        except Exception as e:
            logger.warning(f"API key validation failed: {str(e)}")
            return False 