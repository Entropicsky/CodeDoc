"""
Vector Store integrations for CodeDoc.

This module provides classes for interacting with various vector stores,
including OpenAI's vector store API, for storing and retrieving code
and documentation fragments.
"""

from codedoc.vectorstore.openai_vectorstore import OpenAIVectorStore

__all__ = [
    'OpenAIVectorStore'
] 