"""
File processor for preparing files for vector storage.

This module provides functionality for processing files before uploading them to
vector stores, including chunking, metadata extraction, and formatting.
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable, Set

from codedoc.preprocessors.chunker import Chunker, ChunkingStrategy
from codedoc.preprocessors.metadata_generator import MetadataGenerator

logger = logging.getLogger(__name__)


class FileProcessor:
    """
    Processes files for vector embedding and storage.
    """
    
    def __init__(self, 
                 output_dir: Union[str, Path],
                 chunker: Optional[Chunker] = None,
                 metadata_generator: Optional[MetadataGenerator] = None,
                 chunk_strategy: ChunkingStrategy = ChunkingStrategy.HYBRID,
                 chunk_size: int = 1500,
                 chunk_overlap: int = 200):
        """
        Initialize the file processor.
        
        Args:
            output_dir: Directory where processed files will be saved
            chunker: Chunker to use for splitting files (if None, creates a new one)
            metadata_generator: Metadata generator (if None, creates a new one)
            chunk_strategy: Chunking strategy to use if creating a new chunker
            chunk_size: Chunk size if creating a new chunker
            chunk_overlap: Chunk overlap if creating a new chunker
        """
        self.output_dir = Path(output_dir)
        self.chunks_dir = self.output_dir / "chunks"
        self.metadata_dir = self.output_dir / "metadata"
        
        # Create chunker if not provided
        self.chunker = chunker or Chunker(
            strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Create metadata generator if not provided
        self.metadata_generator = metadata_generator or MetadataGenerator()
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
        
        logger.info(f"File processor initialized with output directory: {self.output_dir}")
        
        # Track stats
        self.stats = {
            "files_processed": 0,
            "chunks_created": 0,
            "total_content_size": 0,
        }
    
    def process_file(self, 
                    file_path: Union[str, Path],
                    file_id: Optional[str] = None,
                    custom_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a single file for vector storage.
        
        Args:
            file_path: Path to the file to process
            file_id: Optional unique ID for the file (if None, uses filename)
            custom_metadata: Optional additional metadata to include
            
        Returns:
            Dictionary with file processing results
            
        Raises:
            FileNotFoundError: If the input file doesn't exist
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Generate file ID if not provided
        if file_id is None:
            # Use a relative path if possible, otherwise just the filename
            try:
                file_id = str(file_path.relative_to(Path.cwd()))
            except ValueError:
                file_id = file_path.name
                
        # Replace slashes and spaces in file_id to make it filename-safe
        safe_file_id = file_id.replace('/', '_').replace('\\', '_').replace(' ', '_')
            
        # Output paths
        chunks_file = self.chunks_dir / f"{safe_file_id}_chunks.json"
        metadata_file = self.metadata_dir / f"{safe_file_id}_metadata.json"
        
        logger.info(f"Processing file: {file_path} -> {chunks_file}")
        
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                logger.warning(f"Skipping empty file: {file_path}")
                return {
                    "file_id": file_id,
                    "file_path": str(file_path),
                    "status": "skipped",
                    "reason": "empty file"
                }
            
            # Generate metadata
            base_metadata = self.metadata_generator.generate_metadata(file_path, content)
            
            # Add custom metadata if provided
            if custom_metadata:
                base_metadata.update(custom_metadata)
                
            # Add file_id to metadata
            base_metadata["file_id"] = file_id
                
            # Generate chunks
            start_time = time.time()
            chunks = self.chunker.chunk_document(content, base_metadata, file_path)
            duration = time.time() - start_time
            
            # Save chunks to file
            with open(chunks_file, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, indent=2)
                
            # Save metadata to file
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(base_metadata, f, indent=2)
                
            # Update stats
            self.stats["files_processed"] += 1
            self.stats["chunks_created"] += len(chunks)
            self.stats["total_content_size"] += len(content)
                
            logger.info(f"File processed and saved to {chunks_file} ({duration:.2f}s), "
                      f"created {len(chunks)} chunks")
            
            return {
                "file_id": file_id,
                "file_path": str(file_path),
                "chunks_file": str(chunks_file),
                "metadata_file": str(metadata_file),
                "num_chunks": len(chunks),
                "status": "success",
                "processing_time": duration
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return {
                "file_id": file_id,
                "file_path": str(file_path),
                "status": "error",
                "error": str(e)
            }
    
    def process_directory(self, 
                         input_dir: Union[str, Path],
                         file_patterns: List[str] = ["*.py", "*.js", "*.ts", "*.java", "*.cpp", "*.h", "*.c", "*.cs", "*.md"],
                         recursive: bool = True,
                         exclude_dirs: Optional[List[str]] = None,
                         max_files: Optional[int] = None,
                         custom_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process all matching files in a directory.
        
        Args:
            input_dir: Directory containing files to process
            file_patterns: Glob patterns for files to include
            recursive: Whether to recursively process subdirectories
            exclude_dirs: List of directory names to exclude
            max_files: Maximum number of files to process
            custom_metadata: Optional additional metadata to include
            
        Returns:
            Dictionary with processing statistics and results
        """
        input_dir = Path(input_dir)
        if not input_dir.exists() or not input_dir.is_dir():
            raise ValueError(f"Invalid input directory: {input_dir}")
            
        exclude_dirs = exclude_dirs or [".git", "__pycache__", "venv", "env", "node_modules"]
        
        # Reset stats
        self.stats = {
            "files_processed": 0,
            "chunks_created": 0,
            "total_content_size": 0,
        }
        
        # Find all matching files
        all_files = []
        
        if recursive:
            for pattern in file_patterns:
                for file_path in input_dir.glob(f"**/{pattern}"):
                    # Check if file is in an excluded directory
                    if any(excl in file_path.parts for excl in exclude_dirs):
                        continue
                    all_files.append(file_path)
        else:
            for pattern in file_patterns:
                for file_path in input_dir.glob(pattern):
                    if any(excl in file_path.parts for excl in exclude_dirs):
                        continue
                    all_files.append(file_path)
                    
        # Limit the number of files if max_files is specified
        if max_files is not None:
            all_files = all_files[:max_files]
            
        logger.info(f"Found {len(all_files)} files to process in {input_dir}")
        
        # Process each file
        results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
        
        for file_path in all_files:
            try:
                # Generate file_id as relative path from input_dir
                try:
                    file_id = str(file_path.relative_to(input_dir))
                except ValueError:
                    file_id = str(file_path.relative_to(Path.cwd()))
                    
                result = self.process_file(file_path, file_id, custom_metadata)
                
                if result["status"] == "success":
                    results["success"].append(result)
                elif result["status"] == "skipped":
                    results["skipped"].append(result)
                else:
                    results["failed"].append(result)
                    
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                results["failed"].append({
                    "file_path": str(file_path),
                    "status": "error",
                    "error": str(e)
                })
                
        # Generate summary file
        summary_file = self.output_dir / "processing_summary.json"
        
        summary = {
            "input_directory": str(input_dir),
            "output_directory": str(self.output_dir),
            "files_processed": self.stats["files_processed"],
            "chunks_created": self.stats["chunks_created"],
            "successful_files": len(results["success"]),
            "failed_files": len(results["failed"]),
            "skipped_files": len(results["skipped"]),
            "stats": self.stats
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Directory processing completed. "
                  f"Processed {self.stats['files_processed']} files, "
                  f"created {self.stats['chunks_created']} chunks.")
        
        return {
            "summary": summary,
            "results": results
        }
    
    def create_openai_batch_file(self, 
                               output_file: Union[str, Path],
                               include_files: Optional[List[Union[str, Path]]] = None,
                               exclude_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a batch file for OpenAI vector store uploads.
        
        Args:
            output_file: Path to save the batch file
            include_files: List of chunk files to include (if None, includes all)
            exclude_patterns: Patterns to exclude from chunk files
            
        Returns:
            Dictionary with batch creation results
        """
        output_file = Path(output_file)
        
        # Find all chunk files
        if include_files:
            # Use provided file list
            chunk_files = [Path(f) for f in include_files]
        else:
            # Use all chunk files in the chunks directory
            chunk_files = list(self.chunks_dir.glob("*_chunks.json"))
            
        # Apply exclusion patterns if provided
        if exclude_patterns:
            filtered_files = []
            for file_path in chunk_files:
                if not any(pattern in str(file_path) for pattern in exclude_patterns):
                    filtered_files.append(file_path)
            chunk_files = filtered_files
            
        logger.info(f"Creating batch file from {len(chunk_files)} chunk files")
        
        # Collect all chunks
        all_chunks = []
        
        for chunk_file in chunk_files:
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                    all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Error reading chunk file {chunk_file}: {str(e)}")
                
        # Format for OpenAI batch format
        batch_chunks = []
        
        for chunk in all_chunks:
            batch_chunks.append({
                "text": chunk["content"],
                "metadata": chunk["metadata"]
            })
            
        # Write batch file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(json.dumps(chunk) for chunk in batch_chunks))
            
        logger.info(f"Batch file created at {output_file} with {len(batch_chunks)} chunks")
        
        return {
            "batch_file": str(output_file),
            "num_chunks": len(batch_chunks),
            "chunk_files": [str(f) for f in chunk_files]
        }


if __name__ == "__main__":
    # Example usage
    import argparse
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    parser = argparse.ArgumentParser(description="Process files for vector storage")
    parser.add_argument("input", help="Path to input file or directory")
    parser.add_argument("--output-dir", "-o", default="codedoc-output", 
                       help="Output directory")
    parser.add_argument("--strategy", "-s", choices=[s.value for s in ChunkingStrategy],
                       default="hybrid", help="Chunking strategy")
    parser.add_argument("--chunk-size", "-c", type=int, default=1500,
                       help="Target chunk size in characters/tokens")
    parser.add_argument("--overlap", "-o", type=int, default=200,
                       help="Overlap between chunks in characters/tokens")
    parser.add_argument("--recursive", "-r", action="store_true",
                       help="Process directories recursively")
    parser.add_argument("--create-batch", "-b", action="store_true",
                       help="Create OpenAI batch file after processing")
    parser.add_argument("--batch-file", default="openai_batch.jsonl",
                       help="Output path for batch file")
    
    args = parser.parse_args()
    
    try:
        # Initialize chunker with specified strategy
        strategy = ChunkingStrategy(args.strategy)
        chunker = Chunker(
            strategy=strategy,
            chunk_size=args.chunk_size,
            chunk_overlap=args.overlap
        )
        
        # Initialize file processor
        processor = FileProcessor(
            output_dir=args.output_dir,
            chunker=chunker
        )
        
        input_path = Path(args.input)
        
        # Process file or directory
        if input_path.is_file():
            result = processor.process_file(input_path)
            print(f"File processing result: {result}")
            
            if args.create_batch:
                batch_result = processor.create_openai_batch_file(args.batch_file)
                print(f"Batch file created: {batch_result['batch_file']}")
                
        elif input_path.is_dir():
            result = processor.process_directory(
                input_dir=input_path,
                recursive=args.recursive
            )
            print(f"Processed {result['summary']['successful_files']} files successfully")
            
            if args.create_batch:
                batch_result = processor.create_openai_batch_file(args.batch_file)
                print(f"Batch file created: {batch_result['batch_file']} "
                     f"with {batch_result['num_chunks']} chunks")
                     
        else:
            print(f"Error: {input_path} is not a valid file or directory")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 