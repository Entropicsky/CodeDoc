"""
Preprocessor modules for preparing content for vector stores.

This package contains modules for preprocessing files, including chunking strategies,
metadata generation, and output formatting.
"""

from codedoc.preprocessors.chunker import Chunker, ChunkingStrategy
from codedoc.preprocessors.metadata_generator import MetadataGenerator
from codedoc.preprocessors.file_processor import FileProcessor
from codedoc.preprocessors.output_formatter import OutputFormatter

__all__ = [
    'Chunker',
    'ChunkingStrategy',
    'MetadataGenerator',
    'FileProcessor',
    'OutputFormatter',
] 