"""
OpenAI API client implementation.

This module provides a client for interacting with OpenAI's API,
handling authentication, prompt formatting, and response processing.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union
import time
from functools import wraps

import tiktoken
import openai
from openai import OpenAI
from openai.types.chat import ChatCompletion

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


class OpenAIClient(LLMClient):
    """Client for interacting with OpenAI's API."""
    
    def __init__(self, api_key: Optional[str] = None, organization: Optional[str] = None, **kwargs):
        """
        Initialize the OpenAI client.
        
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
        
        logger.info(f"Initialized OpenAI client with model {self.default_model}")
    
    @retry_on_error()
    def generate(self, 
                prompt: str, 
                system_prompt: Optional[str] = None,
                model: Optional[str] = None, 
                max_tokens: Optional[int] = None,
                temperature: float = 0.7,
                **kwargs) -> LLMResponse:
        """
        Generate a response from the OpenAI API.
        
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
        
        # Prepare messages array
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            content = response.choices[0].message.content
            
            logger.debug(f"Response generated successfully. Using {response.usage.total_tokens} tokens")
            
            return LLMResponse(
                content=content,
                model=model,
                tokens_used=response.usage.total_tokens,
                tokens_prompt=response.usage.prompt_tokens,
                tokens_completion=response.usage.completion_tokens,
                finish_reason=response.choices[0].finish_reason,
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
        model = model or DEFAULT_MODEL
        max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        
        logger.debug(f"Generating response with system prompt, model {model}")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            logger.debug(f"Response generated successfully. Usage: {usage}")
            
            return LLMResponse(
                content=content,
                model=model,
                tokens_used=usage["total_tokens"],
                tokens_prompt=usage["prompt_tokens"],
                tokens_completion=usage["completion_tokens"],
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Error generating response with system prompt: {str(e)}")
            raise LLMError(f"Error generating response with system prompt: {str(e)}")
    
    def calculate_tokens(self, text: str) -> int:
        """
        Calculate the number of tokens in the given text using OpenAI's tokenizer.
        
        Args:
            text: The text to calculate tokens for
            
        Returns:
            The number of tokens in the text
        """
        try:
            encoding = tiktoken.encoding_for_model(DEFAULT_MODEL)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Error calculating tokens: {str(e)}. Using fallback approximation.")
            # Fallback: rough approximation (4 chars ≈ 1 token)
            return len(text) // 4
    
    def get_available_models(self) -> List[str]:
        """
        Get a list of available models from OpenAI.
        
        Returns:
            List of model identifiers that can be used with this client
        """
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Error retrieving available models: {str(e)}")
            raise LLMError(f"Error retrieving available models: {str(e)}")
    
    def validate_api_key(self) -> bool:
        """
        Validate that the OpenAI API key works.
        
        Returns:
            True if the API key is valid, False otherwise
        """
        try:
            # Just list models as a simple API call to check auth
            self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"API key validation failed: {str(e)}")
            return False
            
    @retry_on_error()
    def create_vector_store(self, name: str) -> Dict[str, Any]:
        """
        Create a new vector store in OpenAI.
        
        Args:
            name: Name for the vector store
            
        Returns:
            Dictionary with vector store details including ID
            
        Raises:
            LLMError: If creating the vector store fails
        """
        try:
            vector_store = self.client.beta.vector_stores.create(name=name)
            logger.info(f"Vector store created: {vector_store.id}")
            return {
                "id": vector_store.id,
                "name": name,
                "created_at": vector_store.created_at
            }
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            raise LLMError(f"Error creating vector store: {str(e)}")
    
    @retry_on_error()
    def upload_file(self, file_path: str, purpose: str = "assistants") -> str:
        """
        Upload a file to OpenAI.
        
        Args:
            file_path: Path to the file to upload
            purpose: Purpose of the file (default: "assistants")
            
        Returns:
            File ID of the uploaded file
            
        Raises:
            LLMError: If file upload fails
        """
        try:
            with open(file_path, "rb") as file:
                response = self.client.files.create(
                    file=file,
                    purpose=purpose
                )
            logger.info(f"File uploaded: {response.id}")
            return response.id
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise LLMError(f"Error uploading file {file_path}: {str(e)}")
    
    @retry_on_error()
    def add_files_to_vector_store(self, vector_store_id: str, file_ids: List[str]) -> str:
        """
        Add files to a vector store.
        
        Args:
            vector_store_id: ID of the vector store
            file_ids: List of file IDs to add
            
        Returns:
            File batch ID
            
        Raises:
            LLMError: If adding files fails
        """
        try:
            file_batch = self.client.beta.vector_stores.file_batches.create(
                vector_store_id=vector_store_id,
                file_ids=file_ids
            )
            logger.info(f"Files added to vector store. Batch ID: {file_batch.id}")
            return file_batch.id
        except Exception as e:
            logger.error(f"Error adding files to vector store: {str(e)}")
            raise LLMError(f"Error adding files to vector store: {str(e)}")
    
    @retry_on_error()
    def check_file_batch_status(self, vector_store_id: str, file_batch_id: str) -> Dict[str, Any]:
        """
        Check the status of a file batch.
        
        Args:
            vector_store_id: ID of the vector store
            file_batch_id: ID of the file batch
            
        Returns:
            Dictionary with status information
            
        Raises:
            LLMError: If checking status fails
        """
        try:
            status = self.client.beta.vector_stores.file_batches.retrieve(
                vector_store_id=vector_store_id,
                file_batch_id=file_batch_id
            )
            return {
                "id": status.id,
                "status": status.status,
                "file_counts": {
                    "succeeded": status.file_counts.succeeded,
                    "failed": status.file_counts.failed,
                    "total": status.file_counts.total
                }
            }
        except Exception as e:
            logger.error(f"Error checking file batch status: {str(e)}")
            raise LLMError(f"Error checking file batch status: {str(e)}")
    
    @retry_on_error()
    def create_response(self, vector_store_id: str, query: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a response using the OpenAI Response API with vector store search.
        
        Args:
            vector_store_id: ID of the vector store to search
            query: The user's query
            system_prompt: Optional system prompt to guide the response
            
        Returns:
            Dictionary with response details
            
        Raises:
            LLMError: If creating response fails
        """
        try:
            context = []
            if system_prompt:
                context.append({
                    "text": system_prompt,
                    "role": "system"
                })
            
            response = self.client.beta.responses.create(
                context=context,
                tools=[
                    {
                        "type": "file_search",
                        "vector_store_id": vector_store_id
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": query
                    }
                ]
            )
            
            content = response.choices[0].message.content
            
            return {
                "content": content,
                "response_id": response.id,
                "model": response.model
            }
        except Exception as e:
            logger.error(f"Error creating response: {str(e)}")
            raise LLMError(f"Error creating response: {str(e)}")

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens
        """
        return self.calculate_tokens(text)

    def get_model_name(self) -> str:
        """
        Get the name of the currently configured model.
        
        Returns:
            Model name as a string
        """
        return self.default_model 