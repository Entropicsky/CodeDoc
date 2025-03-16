"""
Tests for the OpenAI Responses API client.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from codedoc.llm.responses_client import ResponsesClient
from codedoc.llm.base import LLMResponse, LLMError


class TestResponsesClient:
    """Tests for the ResponsesClient class."""
    
    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        with patch('codedoc.llm.responses_client.OpenAI') as mock_openai:
            client = ResponsesClient(api_key="test_api_key")
            
            # Verify OpenAI client was initialized with the API key
            mock_openai.assert_called_once_with(api_key="test_api_key")
            
            assert client.default_model == "gpt-4o"
    
    def test_init_with_env_var(self):
        """Test initialization with API key from environment variable."""
        with patch('codedoc.llm.responses_client.OpenAI') as mock_openai, \
             patch.dict(os.environ, {"OPENAI_API_KEY": "env_api_key"}):
            
            client = ResponsesClient()
            
            # Verify OpenAI client was initialized with the environment API key
            mock_openai.assert_called_once_with(api_key="env_api_key")
    
    def test_init_with_custom_model(self):
        """Test initialization with custom default model."""
        with patch('codedoc.llm.responses_client.OpenAI'):
            client = ResponsesClient(api_key="test_api_key", default_model="gpt-3.5-turbo")
            
            assert client.default_model == "gpt-3.5-turbo"
    
    @pytest.mark.parametrize("model", [None, "gpt-4-turbo"])
    def test_generate_with_system_prompt(self, model):
        """Test generating text with system prompt."""
        with patch('codedoc.llm.responses_client.OpenAI') as mock_openai:
            # Create mock response for the Responses API
            mock_content_item = MagicMock()
            mock_content_item.type = "output_text"
            mock_content_item.text = "Generated text"
            
            mock_message = MagicMock()
            mock_message.type = "message"
            mock_message.content = [mock_content_item]
            
            mock_response = MagicMock()
            mock_response.output = [mock_message]
            mock_response.usage.total_tokens = 100
            mock_response.usage.input_tokens = 50
            mock_response.usage.output_tokens = 50
            
            # Set up the mock client
            mock_client = MagicMock()
            mock_client.responses.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            # Initialize the client and call the method
            client = ResponsesClient(api_key="test_api_key")
            response = client.generate(
                prompt="User request",
                system_prompt="System instructions",
                model=model,
                temperature=0.7
            )
            
            # Verify the response
            assert isinstance(response, LLMResponse)
            assert response.content == "Generated text"
            assert response.tokens_used == 100
            
            # Verify the API call
            expected_model = model if model else client.default_model
            mock_client.responses.create.assert_called_once()
            call_kwargs = mock_client.responses.create.call_args.kwargs
            assert call_kwargs["model"] == expected_model
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["input"] == "User request"
            assert call_kwargs["instructions"] == "System instructions"
    
    def test_api_error_handling(self):
        """Test handling of API errors."""
        with patch('codedoc.llm.responses_client.OpenAI') as mock_openai:
            # Set up the mock error
            mock_error = Exception("API error")
            
            # Set up the mock client to raise an error
            mock_client = MagicMock()
            mock_client.responses.create.side_effect = mock_error
            mock_openai.return_value = mock_client
            
            # Initialize the client
            client = ResponsesClient(api_key="test_api_key")
            
            # Call the method and expect an LLMError
            with pytest.raises(LLMError) as exc_info:
                client.generate(
                    prompt="User request",
                    system_prompt="System instructions"
                )
            
            # Verify the error
            assert "API error" in str(exc_info.value)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key(self):
        """Test error when API key is missing."""
        with pytest.raises(ValueError) as exc_info:
            client = ResponsesClient()
        
        assert "API key" in str(exc_info.value)
    
    def test_count_tokens(self):
        """Test token counting functionality."""
        with patch('codedoc.llm.responses_client.tiktoken.encoding_for_model') as mock_encoding:
            # Mock encoding to return a fixed number of tokens
            mock_encode = MagicMock()
            mock_encode.encode.return_value = [1, 2, 3, 4, 5]
            mock_encoding.return_value = mock_encode
            
            client = ResponsesClient(api_key="test_api_key")
            token_count = client.count_tokens("Sample text")
            
            assert token_count == 5 