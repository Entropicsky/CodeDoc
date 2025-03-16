"""
Tests for the base LLM client.
"""

import pytest
from codedoc.llm.base import LLMClient, LLMResponse, LLMError


class TestLLMResponse:
    """Tests for the LLMResponse class."""
    
    def test_init(self):
        """Test initialization of LLMResponse."""
        content = "Test content"
        
        response = LLMResponse(
            content=content,
            model="test-model",
            tokens_used=100,
            tokens_prompt=50,
            tokens_completion=50
        )
        
        assert response.content == content
        assert response.model == "test-model"
        assert response.tokens_used == 100
        assert response.total_tokens == 100


class TestLLMError:
    """Tests for the LLMError class."""
    
    def test_init(self):
        """Test initialization of LLMError."""
        message = "Test error message"
        details = {"error_type": "rate_limit", "retry_after": 30}
        
        error = LLMError(message=message, details=details)
        
        assert str(error) == message
        assert error.details == details
        

class TestLLMClient:
    """Tests for the abstract LLMClient class."""
    
    def test_abstract_methods(self):
        """Test that LLMClient requires implementation of abstract methods."""
        class ConcreteLLMClient(LLMClient):
            """Concrete implementation that doesn't override abstract methods."""
            pass
        
        # Should raise TypeError when instantiating without implementing abstract methods
        with pytest.raises(TypeError):
            client = ConcreteLLMClient()
    
    def test_concrete_implementation(self):
        """Test a concrete implementation of LLMClient."""
        class ConcreteLLMClient(LLMClient):
            """Concrete implementation with required methods."""
            
            def generate(self, prompt, system_prompt=None, temperature=0.7, 
                         max_tokens=None, stop_sequences=None, **kwargs):
                return LLMResponse(
                    content="Test response",
                    model="test-model",
                    tokens_used=100,
                    tokens_prompt=50,
                    tokens_completion=50
                )
                
            def count_tokens(self, text):
                return len(text.split())
                
            def get_model_name(self):
                return "test-model"
        
        client = ConcreteLLMClient()
        response = client.generate(prompt="Test prompt")
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test response"
        assert response.tokens_used == 100 