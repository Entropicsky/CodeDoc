"""
Direct file processor for OpenAI Files and Vector Stores API.

This module provides functionality for direct file processing and upload to OpenAI,
bypassing custom chunking by leveraging OpenAI's native chunking capabilities.
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable, Set

from codedoc.integrations.openai_vector import OpenAIVectorClient
from codedoc.preprocessors.metadata_generator import MetadataGenerator

logger = logging.getLogger(__name__)


class DirectFileProcessor:
    """
    Processes and uploads files directly to OpenAI, bypassing custom chunking.
    """
    
    def __init__(self, 
                 output_dir: Union[str, Path],
                 metadata_generator: Optional[MetadataGenerator] = None,
                 vector_client: Optional[OpenAIVectorClient] = None,
                 api_key: Optional[str] = None,
                 organization: Optional[str] = None):
        """
        Initialize the direct file processor.
        
        Args:
            output_dir: Directory where metadata will be saved
            metadata_generator: Metadata generator (if None, creates a new one)
            vector_client: OpenAI Vector client (if None, creates a new one)
            api_key: OpenAI API key
            organization: OpenAI organization ID
        """
        self.output_dir = Path(output_dir)
        self.metadata_dir = self.output_dir / "metadata"
        
        # Create metadata generator if not provided
        self.metadata_generator = metadata_generator or MetadataGenerator()
        
        # Create vector client if not provided
        self.vector_client = vector_client or OpenAIVectorClient(
            api_key=api_key,
            organization=organization
        )
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
        
        logger.info(f"Direct file processor initialized with output directory: {self.output_dir}")
        
        # Track stats
        self.stats = {
            "files_processed": 0,
            "files_uploaded": 0,
            "total_content_size": 0,
            "failed_files": 0,
        }
    
    def process_file(self, 
                    file_path: Union[str, Path],
                    file_id: Optional[str] = None,
                    purpose: str = "assistants",
                    custom_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process and upload a single file to OpenAI.
        
        Args:
            file_path: Path to the file to process
            file_id: Optional unique ID for the file (if None, uses filename)
            purpose: Purpose of the file (vector_search, assistants, etc.)
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
        metadata_file = self.metadata_dir / f"{safe_file_id}_metadata.json"
        
        logger.info(f"Processing file: {file_path}")
        
        try:
            # Read the file content for metadata generation
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                logger.warning(f"Skipping empty file: {file_path}")
                self.stats["failed_files"] += 1
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
                
            # Save metadata to file
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(base_metadata, f, indent=2)
                
            # Upload file to OpenAI
            start_time = time.time()
            prefix = f"[{file_id}] "
            
            response = self.vector_client.upload_file(
                file_path=file_path,
                purpose=purpose,
                prefix=prefix
            )
            
            duration = time.time() - start_time
                
            if response:
                # Update stats
                self.stats["files_processed"] += 1
                self.stats["files_uploaded"] += 1
                self.stats["total_content_size"] += len(content)
                    
                logger.info(f"File processed and uploaded successfully ({duration:.2f}s)")
                
                return {
                    "file_id": file_id,
                    "openai_file_id": response.id,
                    "file_path": str(file_path),
                    "metadata_file": str(metadata_file),
                    "status": "success",
                    "processing_time": duration,
                    "size_bytes": response.bytes,
                    "created_at": response.created_at
                }
            else:
                self.stats["failed_files"] += 1
                logger.error(f"Failed to upload file: {file_path}")
                
                return {
                    "file_id": file_id,
                    "file_path": str(file_path),
                    "status": "failed",
                    "reason": "upload failed"
                }
            
        except Exception as e:
            self.stats["failed_files"] += 1
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
                         purpose: str = "assistants",
                         custom_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process and upload all matching files in a directory.
        
        Args:
            input_dir: Directory containing files to process
            file_patterns: Glob patterns for files to include
            recursive: Whether to recursively process subdirectories
            exclude_dirs: List of directory names to exclude
            max_files: Maximum number of files to process
            purpose: Purpose of the files (vector_search, assistants, etc.)
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
            "files_uploaded": 0,
            "total_content_size": 0,
            "failed_files": 0,
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
        
        for i, file_path in enumerate(all_files):
            try:
                # Generate file_id as relative path from input_dir
                try:
                    file_id = str(file_path.relative_to(input_dir))
                except ValueError:
                    file_id = str(file_path.relative_to(Path.cwd()))
                    
                logger.info(f"Processing file {i+1}/{len(all_files)}: {file_id}")
                    
                result = self.process_file(
                    file_path=file_path, 
                    file_id=file_id, 
                    purpose=purpose,
                    custom_metadata=custom_metadata
                )
                
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
                
        # Generate summary
        summary = {
            "total_files": len(all_files),
            "successful_files": len(results["success"]),
            "skipped_files": len(results["skipped"]),
            "failed_files": len(results["failed"]),
            "uploaded_file_ids": [r.get("openai_file_id") for r in results["success"] if "openai_file_id" in r],
            "total_bytes": sum(r.get("size_bytes", 0) for r in results["success"]),
            "total_processing_time": sum(r.get("processing_time", 0) for r in results["success"]),
        }
        
        logger.info(f"Directory processing completed: {summary['successful_files']} files uploaded successfully, "
                  f"{summary['failed_files']} failed, {summary['skipped_files']} skipped")
        
        return {
            "success": results["success"],
            "failed": results["failed"],
            "skipped": results["skipped"],
            "summary": summary
        }
        
    def create_vector_store(self,
                          name: str,
                          file_ids: List[str],
                          chunking_strategy: Optional[Dict[str, Any]] = None,
                          metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create a vector store with the uploaded files.
        
        Args:
            name: Name of the vector store
            file_ids: List of file IDs to include in the vector store
            chunking_strategy: Optional chunking strategy configuration
            metadata: Optional metadata for the vector store
            
        Returns:
            Dictionary with vector store creation results
        """
        logger.info(f"Creating vector store '{name}' with {len(file_ids)} files")
        
        # Create vector store
        vector_store = self.vector_client.create_vector_store(
            name=name,
            file_ids=file_ids,
            chunking_strategy=chunking_strategy,
            metadata=metadata
        )
        
        if not vector_store:
            logger.error(f"Failed to create vector store '{name}'")
            return {
                "status": "failed",
                "reason": "vector store creation failed"
            }
            
        logger.info(f"Vector store created successfully: {vector_store.id}")
        
        # Wait for files to be processed
        is_ready, status = self.vector_client.check_vector_store_status(
            vector_store_id=vector_store.id,
            max_checks=20,
            check_interval=3
        )
        
        # Convert the FileCounts object to a dictionary for easier handling
        status_dict = {}
        if hasattr(status, 'total'):
            status_dict['total'] = status.total
        if hasattr(status, 'completed'):
            status_dict['completed'] = status.completed
        if hasattr(status, 'failed'):
            status_dict['failed'] = status.failed
        if hasattr(status, 'in_progress'):
            status_dict['in_progress'] = status.in_progress
        if hasattr(status, 'cancelled'):
            status_dict['cancelled'] = status.cancelled
        
        return {
            "status": "success" if is_ready else "in_progress",
            "vector_store_id": vector_store.id,
            "name": name,
            "file_count": len(file_ids),
            "processing_status": status_dict
        } 