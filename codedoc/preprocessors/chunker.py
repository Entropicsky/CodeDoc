"""
Document chunking strategies and implementation.

This module provides functionality for splitting documents into chunks suitable
for vector embedding and storage, using various chunking strategies.
"""

import re
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable, Tuple

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Enumeration of chunking strategies."""
    FIXED_SIZE = "fixed_size"  # Fixed size chunks with optional overlap
    PARAGRAPH = "paragraph"  # Split on paragraphs
    SEMANTIC = "semantic"  # Semantic boundaries like sections
    CODE_BLOCK = "code_block"  # Code-specific chunks (classes, functions)
    HYBRID = "hybrid"  # Combination of strategies


class Chunker:
    """
    Splits documents into chunks suitable for vector embedding.
    """
    
    def __init__(self, 
                strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE,
                chunk_size: int = 1500,
                chunk_overlap: int = 200,
                max_chunks: Optional[int] = None):
        """
        Initialize the chunker.
        
        Args:
            strategy: Chunking strategy to use
            chunk_size: Target size of chunks in tokens/characters
            chunk_overlap: Overlap between chunks in tokens/characters
            max_chunks: Maximum number of chunks to generate (None for unlimited)
        """
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunks = max_chunks
        
        logger.info(f"Chunker initialized with strategy: {strategy.value}, "
                  f"chunk_size: {chunk_size}, overlap: {chunk_overlap}")
    
    def chunk_document(self, 
                      content: str, 
                      metadata: Optional[Dict[str, Any]] = None,
                      file_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """
        Split a document into chunks.
        
        Args:
            content: Document content to chunk
            metadata: Optional metadata to include with each chunk
            file_path: Optional file path (used for some chunking strategies)
            
        Returns:
            List of dictionaries containing chunks and their metadata
        """
        chunks = []
        base_metadata = metadata or {}
        file_ext = Path(file_path).suffix.lower() if file_path else None
        
        if self.strategy == ChunkingStrategy.FIXED_SIZE:
            chunks = self._chunk_fixed_size(content)
        elif self.strategy == ChunkingStrategy.PARAGRAPH:
            chunks = self._chunk_paragraphs(content)
        elif self.strategy == ChunkingStrategy.SEMANTIC:
            chunks = self._chunk_semantic(content)
        elif self.strategy == ChunkingStrategy.CODE_BLOCK:
            chunks = self._chunk_code_blocks(content, file_ext)
        elif self.strategy == ChunkingStrategy.HYBRID:
            # First try code block chunking for code files
            if file_ext in ['.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.ts', '.go']:
                chunks = self._chunk_code_blocks(content, file_ext)
            
            # If code block chunking didn't work well or it's not a code file, use semantic
            if not chunks or len(chunks) <= 1:
                chunks = self._chunk_semantic(content)
                
            # Fallback to paragraph chunking if semantic didn't work well
            if not chunks or len(chunks) <= 1:
                chunks = self._chunk_paragraphs(content)
                
            # Final fallback to fixed size chunking
            if not chunks:
                chunks = self._chunk_fixed_size(content)
        
        # Apply max_chunks limit if specified
        if self.max_chunks is not None and len(chunks) > self.max_chunks:
            logger.warning(f"Limiting from {len(chunks)} to {self.max_chunks} chunks")
            chunks = chunks[:self.max_chunks]
        
        # Add metadata to chunks
        result = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "chunk_index": i,
                "total_chunks": len(chunks),
                "strategy": self.strategy.value,
                **base_metadata
            }
            
            result.append({
                "content": chunk,
                "metadata": chunk_metadata
            })
        
        logger.info(f"Created {len(result)} chunks using {self.strategy.value} strategy")
        return result
    
    def _chunk_fixed_size(self, content: str) -> List[str]:
        """
        Split content into fixed-size chunks with overlap.
        
        Args:
            content: Text to split into chunks
            
        Returns:
            List of text chunks
        """
        if not content:
            return []
            
        chunks = []
        start = 0
        content_len = len(content)
        
        while start < content_len:
            end = min(start + self.chunk_size, content_len)
            
            # If we're not at the end and this isn't the first chunk,
            # try to find a natural break point like a newline
            if end < content_len and start > 0:
                # Look for newline or period within the last 20% of the chunk
                search_start = end - int(self.chunk_size * 0.2)
                search_text = content[search_start:end]
                
                # Try to find a newline
                last_newline = search_text.rfind('\n')
                if last_newline != -1:
                    end = search_start + last_newline + 1
                else:
                    # Try to find a period followed by space or newline
                    last_period = search_text.rfind('. ')
                    if last_period != -1:
                        end = search_start + last_period + 2
            
            # Add the chunk
            chunks.append(content[start:end])
            
            # Move start position for next chunk, accounting for overlap
            start = end - self.chunk_overlap
            
            # Make sure we make progress
            if start >= end:
                start = end
        
        return chunks
    
    def _chunk_paragraphs(self, content: str) -> List[str]:
        """
        Split content into paragraph-based chunks, merging small paragraphs.
        
        Args:
            content: Text to split into chunks
            
        Returns:
            List of text chunks
        """
        if not content:
            return []
            
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', content)
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # Skip empty paragraphs
            if not para.strip():
                continue
                
            # If adding this paragraph would exceed the chunk size and we already have content,
            # save the current chunk and start a new one
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = para
            else:
                # Add separator if we already have content
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += para
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_semantic(self, content: str) -> List[str]:
        """
        Split content based on semantic boundaries like headings.
        
        Args:
            content: Text to split into chunks
            
        Returns:
            List of text chunks
        """
        if not content:
            return []
            
        # Look for Markdown headings or other semantic boundaries
        heading_pattern = r'(?:^|\n)(#{1,6}\s+[^\n]+|\n[^\n]+\n[=-]+)'
        headings = list(re.finditer(heading_pattern, content))
        
        if not headings:
            # Fallback to paragraph chunking if no headings found
            return self._chunk_paragraphs(content)
        
        chunks = []
        for i, match in enumerate(headings):
            # Determine section start and end
            start = match.start()
            end = headings[i+1].start() if i < len(headings) - 1 else len(content)
            
            section = content[start:end]
            
            # If section is too big, split it further
            if len(section) > self.chunk_size:
                # Split oversized sections into paragraphs
                sub_chunks = self._chunk_paragraphs(section)
                chunks.extend(sub_chunks)
            else:
                chunks.append(section)
        
        # If we have no chunks yet, handle the case where there's content before the first heading
        if not chunks and headings:
            if headings[0].start() > 0:
                chunks.append(content[:headings[0].start()])
                
        # If we still have no chunks, fall back to fixed size
        if not chunks:
            return self._chunk_fixed_size(content)
        
        return chunks
    
    def _chunk_code_blocks(self, content: str, file_ext: Optional[str] = None) -> List[str]:
        """
        Split code into logical blocks like classes and functions.
        
        Args:
            content: Code content to split
            file_ext: File extension to determine language
            
        Returns:
            List of code chunks
        """
        if not content:
            return []
            
        # Choose chunking strategy based on file extension
        if file_ext == '.py':
            return self._chunk_python_code(content)
        elif file_ext in ['.js', '.ts']:
            return self._chunk_javascript_code(content)
        elif file_ext in ['.java', '.cs']:
            return self._chunk_java_code(content)
        elif file_ext in ['.cpp', '.c', '.h']:
            return self._chunk_c_code(content)
        else:
            # Fallback to a generic code chunking approach
            return self._chunk_generic_code(content)
    
    def _chunk_python_code(self, content: str) -> List[str]:
        """Split Python code into classes and functions."""
        if not content:
            return []
            
        # Look for class and function definitions
        patterns = [
            r'(?:^|\n)(?:\s*@.*\n)*\s*class\s+[^\n(]+[^\n]*:',  # Class definitions
            r'(?:^|\n)(?:\s*@.*\n)*\s*def\s+[^\n(]+\([^)]*\)\s*(?:->.*?)?:',  # Function definitions
        ]
        
        return self._chunk_by_patterns(content, patterns)
    
    def _chunk_javascript_code(self, content: str) -> List[str]:
        """Split JavaScript/TypeScript code into classes, functions and modules."""
        if not content:
            return []
            
        # Look for various JS/TS constructs
        patterns = [
            r'(?:^|\n)class\s+[^\n{]+\s*{',  # Class definitions
            r'(?:^|\n)(?:function|const|let|var)\s+[^=\n]+\s*(?:=\s*(?:function\s*)?\([^)]*\)|[^\n]*=>\s*(?:{|\())',  # Functions including arrow functions
            r'(?:^|\n)(?:export|import)\s+(?:{[^}]+}|[^;{\n]+)\s+(?:from\s+)?[\'"][^\'"]+[\'"];?',  # Import/export statements
        ]
        
        return self._chunk_by_patterns(content, patterns)
    
    def _chunk_java_code(self, content: str) -> List[str]:
        """Split Java/C# code into classes and methods."""
        if not content:
            return []
            
        # Look for class, interface, and method definitions
        patterns = [
            r'(?:^|\n)(?:public|private|protected|internal|static|abstract|final|sealed|partial)*\s+(?:class|interface|enum|record)\s+[^\n{]+\s*{',  # Class/interface definitions
            r'(?:^|\n)(?:public|private|protected|internal|static|abstract|final|virtual|override|async)*\s+(?:[A-Za-z0-9_<>[\],\s]+)\s+[A-Za-z0-9_]+\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\s*{',  # Method definitions
        ]
        
        return self._chunk_by_patterns(content, patterns)
    
    def _chunk_c_code(self, content: str) -> List[str]:
        """Split C/C++ code into functions and structs."""
        if not content:
            return []
            
        # Look for function, struct, and class definitions
        patterns = [
            r'(?:^|\n)(?:class|struct|enum|union)\s+[^\n{;]+\s*{',  # Class/struct definitions
            r'(?:^|\n)(?:[A-Za-z0-9_*:<>\[\]\s,]+)\s+[A-Za-z0-9_]+\s*\([^;]*\)\s*(?:const|noexcept|override|final)?\s*{',  # Function definitions
        ]
        
        return self._chunk_by_patterns(content, patterns)
    
    def _chunk_generic_code(self, content: str) -> List[str]:
        """Generic code chunking for unsupported languages."""
        if not content:
            return []
            
        # Look for common code structures across languages
        patterns = [
            r'(?:^|\n)(?:class|function|def|interface|struct|enum)\s+[^\n{(]+',  # Class/function like definitions
            r'(?:^|\n)(?:\/\/|#|\/\*|\*|\s*\*\s@)\s*[A-Z][A-Za-z\s]+',  # Comments that might indicate section starts
            r'(?:^|\n)(?:export|import|include|require|use|using|from|module)',  # Import statements
        ]
        
        chunks = self._chunk_by_patterns(content, patterns)
        
        # If we didn't find good chunks, fall back to paragraph chunking
        if not chunks or len(chunks) <= 2:
            chunks = self._chunk_paragraphs(content)
            
        return chunks
    
    def _chunk_by_patterns(self, content: str, patterns: List[str]) -> List[str]:
        """
        Split content by regex patterns that identify chunk boundaries.
        
        Args:
            content: Text to split
            patterns: List of regex patterns marking chunk starts
            
        Returns:
            List of chunks
        """
        if not content:
            return []
            
        # Find all matches for all patterns
        matches = []
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                matches.append(match.start())
        
        # Sort matches by position
        matches.sort()
        
        # No matches found, return the whole content if it's not too big
        if not matches:
            if len(content) <= self.chunk_size:
                return [content]
            else:
                # Content too big with no patterns found, fall back to fixed size chunking
                return self._chunk_fixed_size(content)
        
        # Create chunks based on matches
        chunks = []
        
        # Add the content before the first match if it's substantial
        if matches[0] > 100:  # Only include if more than 100 chars
            chunks.append(content[:matches[0]])
        
        # Add chunks between matches and after the last match
        for i, start in enumerate(matches):
            # Determine end of this chunk
            end = matches[i+1] if i < len(matches) - 1 else len(content)
            
            # Skip chunks that are too small
            if end - start < 50:  # Only include if more than 50 chars
                continue
                
            # If chunk is too big, split it further using fixed size
            if end - start > self.chunk_size:
                sub_content = content[start:end]
                sub_chunks = self._chunk_fixed_size(sub_content)
                chunks.extend(sub_chunks)
            else:
                chunks.append(content[start:end])
        
        return chunks


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text string.
    This is a rough approximation based on character count.
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    # Average ratio of characters to tokens (approx. 4 chars per token)
    char_to_token_ratio = 4.0
    
    # Clean text (remove extra whitespace)
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    
    # Estimate token count
    estimated_tokens = max(1, int(len(cleaned_text) / char_to_token_ratio))
    
    return estimated_tokens


if __name__ == "__main__":
    # Example usage
    import argparse
    import sys
    import json
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    parser = argparse.ArgumentParser(description="Chunk documents for vector storage")
    parser.add_argument("input_file", help="Path to input file to chunk")
    parser.add_argument("--strategy", "-s", choices=[s.value for s in ChunkingStrategy],
                       default="hybrid", help="Chunking strategy")
    parser.add_argument("--chunk-size", "-c", type=int, default=1500,
                       help="Target chunk size in characters/tokens")
    parser.add_argument("--overlap", "-o", type=int, default=200,
                       help="Overlap between chunks in characters/tokens")
    parser.add_argument("--output", help="Output JSON file for chunks")
    
    args = parser.parse_args()
    
    try:
        file_path = Path(args.input_file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Create chunker with specified strategy
        strategy = ChunkingStrategy(args.strategy)
        chunker = Chunker(
            strategy=strategy,
            chunk_size=args.chunk_size,
            chunk_overlap=args.overlap
        )
        
        # Create base metadata
        metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "file_type": file_path.suffix.lstrip('.'),
            "chunk_size": args.chunk_size,
            "chunk_overlap": args.overlap
        }
        
        # Generate chunks
        chunks = chunker.chunk_document(content, metadata, file_path)
        
        # Output results
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, indent=2)
            print(f"Chunks saved to {args.output}")
        else:
            print(f"Generated {len(chunks)} chunks")
            for i, chunk in enumerate(chunks):
                print(f"\nChunk {i+1}/{len(chunks)} (approx. {estimate_tokens(chunk['content'])} tokens):")
                print("---------------------------------------------------")
                # Print first 150 chars of the chunk
                preview = chunk['content'][:150].replace('\n', ' ')
                if len(chunk['content']) > 150:
                    preview += "..."
                print(preview)
                print("---------------------------------------------------")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 