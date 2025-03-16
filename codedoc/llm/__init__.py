"""
LLM integration module for CodeDoc.

This module provides interfaces and implementations for interacting with Large Language Models
like OpenAI GPT and Google Gemini, handling authentication, prompt management, and response processing.
"""

from codedoc.llm.base import LLMClient, LLMResponse, LLMError
from codedoc.llm.openai_client import OpenAIClient
from codedoc.llm.responses_client import ResponsesClient
from codedoc.llm.gemini_client import GeminiClient
from codedoc.llm.prompt_manager import PromptManager

__all__ = [
    'LLMClient',
    'LLMResponse',
    'LLMError',
    'OpenAIClient',
    'ResponsesClient',
    'GeminiClient',
    'PromptManager',
] 