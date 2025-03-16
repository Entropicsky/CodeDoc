"""
Tests for the OpenAI LLM client.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from codedoc.llm.openai_client import OpenAIClient
from codedoc.llm.base import LLMResponse, LLMError


class TestOpenAIClient:
    """Tests for the OpenAIClient class."""
    
    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        with patch('codedoc.llm.openai_client.OpenAI') as mock_openai:
            client = OpenAIClient(api_key="test_api_key")
            
            # Verify OpenAI client was initialized with the API key
            mock_openai.assert_called_once_with(api_key="test_api_key")
            
            assert client.default_model == "gpt-4o"
    
    def test_init_with_env_var(self):
        """Test initialization with API key from environment variable."""
        with patch('codedoc.llm.openai_client.OpenAI') as mock_openai, \
             patch.dict(os.environ, {"OPENAI_API_KEY": "env_api_key"}):
            
            client = OpenAIClient()
            
            # Verify OpenAI client was initialized with the environment API key
            mock_openai.assert_called_once_with(api_key="env_api_key")
    
    def test_init_with_custom_model(self):
        """Test initialization with custom default model."""
        with patch('codedoc.llm.openai_client.OpenAI'):
            client = OpenAIClient(api_key="test_api_key", default_model="gpt-3.5-turbo")
            
            assert client.default_model == "gpt-3.5-turbo"
    
    @pytest.mark.parametrize("model", [None, "gpt-4-turbo"])
    def test_generate_with_system_prompt(self, model):
        """Test generating text with system prompt."""
        with patch('codedoc.llm.openai_client.OpenAI') as mock_openai:
            # Setup the mock response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Generated text"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage.total_tokens = 100
            mock_response.usage.prompt_tokens = 50
            mock_response.usage.completion_tokens = 50
            
            # Set up the mock client
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            # Initialize the client and call the method
            client = OpenAIClient(api_key="test_api_key")
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
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert call_kwargs["model"] == expected_model
            assert call_kwargs["temperature"] == 0.7
            assert len(call_kwargs["messages"]) == 2
            assert call_kwargs["messages"][0]["role"] == "system"
            assert call_kwargs["messages"][0]["content"] == "System instructions"
            assert call_kwargs["messages"][1]["role"] == "user"
            assert call_kwargs["messages"][1]["content"] == "User request"
    
    def test_api_error_handling(self):
        """Test handling of API errors."""
        with patch('codedoc.llm.openai_client.OpenAI') as mock_openai:
            # Set up the mock error
            mock_error = Exception("API error")
            
            # Set up the mock client to raise an error
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = mock_error
            mock_openai.return_value = mock_client
            
            # Initialize the client
            client = OpenAIClient(api_key="test_api_key")
            
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
            client = OpenAIClient()
        
        assert "API key" in str(exc_info.value) 