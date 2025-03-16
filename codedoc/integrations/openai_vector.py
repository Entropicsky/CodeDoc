"""
OpenAI Files and Vector Stores API integration.

This module provides classes and functions for interacting with OpenAI's Files and
Vector Stores APIs, which can be used to upload files and create vector stores
for semantic search.
"""

import os
import time
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable, TypedDict, Tuple, Type

import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

class VectorStoreStatus(TypedDict):
    """
    Status information about a vector store.
    """
    in_progress: int
    completed: int
    failed: int
    cancelled: int
    total: int


class OpenAIVectorClient:
    """
    Client for interacting with OpenAI's Files and Vector Stores APIs.
    
    This class provides a higher-level interface for managing files and vector stores,
    including uploading files, creating vector stores, and handling error conditions.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 organization: Optional[str] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 retry_delay: int = 2,
                 client_class: Type = OpenAI):
        """
        Initialize the OpenAI Vector client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY environment variable)
            organization: OpenAI organization ID (defaults to OPENAI_ORG_ID environment variable)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for API calls
            retry_delay: Base delay between retries in seconds (will be exponentially increased)
            client_class: The class to use for the OpenAI client (defaults to OpenAI, useful for testing)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.organization = organization or os.environ.get("OPENAI_ORG_ID")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Initialize the OpenAI client
        self.client = client_class(
            api_key=self.api_key,
            organization=self.organization,
            timeout=self.timeout,
        )
        
        logger.info("Initialized OpenAI Vector client")
    
    def upload_file(self, 
                   file_path: Union[str, Path], 
                   purpose: str = "assistants",
                   prefix: str = "") -> Optional[Any]:
        """
        Upload a file to OpenAI.
        
        Args:
            file_path: Path to the file to upload
            purpose: Purpose of the file (assistants, fine-tune, etc.)
            prefix: Prefix for log messages
            
        Returns:
            File object if successful, None if failed
            
        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the purpose is invalid
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        valid_purposes = ["assistants", "fine-tune", "vision", "batch", "user_data", "assistants_output"]
        if purpose not in valid_purposes:
            raise ValueError(f"Invalid purpose: {purpose}. Must be one of {valid_purposes}")
        
        logger.info(f"{prefix}Uploading file: {file_path}")
        
        for attempt in range(self.max_retries):
            try:
                with open(file_path, "rb") as file:
                    response = self.client.files.create(
                        file=file,
                        purpose=purpose
                    )
                
                logger.info(f"{prefix}File uploaded successfully: {response.id}")
                return response
                
            except openai.OpenAIError as e:
                logger.warning(f"{prefix}Error uploading file (attempt {attempt+1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    retry_seconds = self.retry_delay * (2 ** attempt)
                    logger.info(f"{prefix}Retrying in {retry_seconds} seconds...")
                    time.sleep(retry_seconds)
                else:
                    logger.error(f"{prefix}Failed to upload file after {self.max_retries} attempts")
                    return None
    
    def upload_directory(self, 
                        directory: Union[str, Path],
                        purpose: str = "assistants",
                        file_patterns: List[str] = ["*.py", "*.md", "*.txt", "*.js", "*.html"],
                        max_files: Optional[int] = None,
                        callback: Optional[Callable[[str, Any], None]] = None,
                        prefix: str = "") -> Dict[str, Any]:
        """
        Upload all files in a directory that match the given patterns.
        
        Args:
            directory: Directory containing files to upload
            purpose: Purpose of the files
            file_patterns: List of glob patterns for files to upload
            max_files: Maximum number of files to upload (None for no limit)
            callback: Optional callback function to call after each file upload
            prefix: Prefix for log messages
            
        Returns:
            Dictionary with upload statistics and file IDs
        """
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Invalid directory: {directory}")
        
        logger.info(f"{prefix}Uploading files from directory: {directory}")
        
        # Find all files matching the patterns
        all_files = []
        for pattern in file_patterns:
            files = list(directory.glob(f"**/{pattern}"))
            all_files.extend(files)
        
        # Limit the number of files if specified
        if max_files is not None:
            all_files = all_files[:max_files]
        
        logger.info(f"{prefix}Found {len(all_files)} files to upload")
        
        # Upload each file
        uploaded_files = []
        failed_files = []
        
        for i, file_path in enumerate(all_files):
            file_prefix = f"{prefix}[{i+1}/{len(all_files)}] "
            response = self.upload_file(file_path, purpose=purpose, prefix=file_prefix)
            
            if response:
                uploaded_files.append({
                    "file_id": response.id,
                    "file_path": str(file_path),
                    "bytes": response.bytes,
                    "created_at": response.created_at
                })
                
                if callback:
                    callback(str(file_path), response)
            else:
                failed_files.append(str(file_path))
        
        logger.info(f"{prefix}Upload completed. {len(uploaded_files)} files uploaded, {len(failed_files)} failed.")
        
        return {
            "stats": {
                "files_found": len(all_files),
                "files_uploaded": len(uploaded_files),
                "files_failed": len(failed_files),
                "total_bytes": sum(f["bytes"] for f in uploaded_files)
            },
            "uploaded_files": uploaded_files,
            "failed_files": failed_files
        }
    
    def list_files(self, 
                  purpose: Optional[str] = None,
                  limit: int = 100,
                  prefix: str = "") -> List[Any]:
        """
        List files available in the OpenAI API.
        
        Args:
            purpose: Filter by purpose (None for all)
            limit: Maximum number of files to return
            prefix: Prefix for log messages
            
        Returns:
            List of file objects
        """
        logger.info(f"{prefix}Listing files" + (f" with purpose: {purpose}" if purpose else ""))
        
        try:
            response = self.client.files.list(
                purpose=purpose,
                limit=limit
            )
            
            logger.info(f"{prefix}Found {len(response.data)} files")
            return response.data
            
        except openai.OpenAIError as e:
            logger.error(f"{prefix}Error listing files: {str(e)}")
            return []
    
    def delete_file(self, 
                   file_id: str,
                   prefix: str = "") -> bool:
        """
        Delete a file from OpenAI.
        
        Args:
            file_id: ID of the file to delete
            prefix: Prefix for log messages
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"{prefix}Deleting file: {file_id}")
        
        try:
            response = self.client.files.delete(file_id)
            logger.info(f"{prefix}File deleted successfully")
            return getattr(response, 'deleted', True)  # Default to True if 'deleted' attr is missing
            
        except openai.OpenAIError as e:
            logger.error(f"{prefix}Error deleting file: {str(e)}")
            return False
    
    def create_vector_store(self, 
                          name: str,
                          file_ids: Optional[List[str]] = None,
                          chunking_strategy: Optional[Dict[str, Any]] = None,
                          metadata: Optional[Dict[str, str]] = None,
                          prefix: str = "") -> Optional[Any]:
        """
        Create a vector store for semantic search.
        
        Args:
            name: Name of the vector store
            file_ids: Optional list of file IDs to include
            chunking_strategy: Optional chunking strategy configuration. Options include:
                - {"type": "fixed_size", "size": 300, "overlap": 20}: Fixed size chunks
                - {"type": "semantic_paragraph"}: Intelligent paragraph-based chunking
                - {"type": "semantic_chapter"}: Intelligent chapter/section chunking
                - {"type": "auto"}: Let OpenAI decide (default if not specified)
            metadata: Optional metadata for the vector store
            prefix: Prefix for log messages
            
        Returns:
            Vector store object if successful, None if failed
            
        Note:
            OpenAI's native chunking eliminates the need for custom chunking implementation.
            The chunking_strategy parameter directly controls how OpenAI divides documents
            for embedding and retrieval. This is more efficient and effective than
            pre-chunking documents before upload.
        """
        logger.info(f"{prefix}Creating vector store: {name}")
        
        try:
            create_args = {
                "name": name
            }
            
            if file_ids:
                create_args["file_ids"] = file_ids
                
            # Use default "auto" chunking if not specified
            if chunking_strategy is None:
                chunking_strategy = {"type": "auto"}
                
            create_args["chunking_strategy"] = chunking_strategy
                
            if metadata:
                create_args["metadata"] = metadata
            
            # Log the chunking strategy being used
            logger.info(f"{prefix}Using chunking strategy: {chunking_strategy}")
            
            response = self.client.beta.vector_stores.create(**create_args)
            
            logger.info(f"{prefix}Vector store created successfully: {response.id}")
            return response
            
        except openai.OpenAIError as e:
            logger.error(f"{prefix}Error creating vector store: {str(e)}")
            return None
    
    def add_files_to_vector_store(self, 
                                vector_store_id: str,
                                file_ids: List[str],
                                chunking_strategy: Optional[Dict[str, Any]] = None,
                                prefix: str = "") -> Optional[Any]:
        """
        Add files to an existing vector store.
        
        Args:
            vector_store_id: ID of the vector store
            file_ids: List of file IDs to add
            chunking_strategy: Optional chunking strategy configuration. Options include:
                - {"type": "fixed_size", "size": 300, "overlap": 20}: Fixed size chunks
                - {"type": "semantic_paragraph"}: Intelligent paragraph-based chunking
                - {"type": "semantic_chapter"}: Intelligent chapter/section chunking
                - {"type": "auto"}: Let OpenAI decide (default if not specified)
            prefix: Prefix for log messages
            
        Returns:
            Updated vector store object if successful, None if failed
        """
        logger.info(f"{prefix}Adding {len(file_ids)} files to vector store: {vector_store_id}")
        
        try:
            add_args = {
                "vector_store_id": vector_store_id,
                "file_ids": file_ids
            }
            
            # Add chunking strategy if specified
            if chunking_strategy is not None:
                add_args["chunking_strategy"] = chunking_strategy
                logger.info(f"{prefix}Using chunking strategy: {chunking_strategy}")
            
            response = self.client.beta.vector_stores.add_files(**add_args)
            
            logger.info(f"{prefix}Files added successfully")
            return response
            
        except openai.OpenAIError as e:
            logger.error(f"{prefix}Error adding files to vector store: {str(e)}")
            return None
    
    def check_vector_store_status(self, 
                                vector_store_id: str,
                                max_checks: int = 10,
                                check_interval: int = 5,
                                prefix: str = "") -> Tuple[bool, Optional[VectorStoreStatus]]:
        """
        Check the status of a vector store until it's ready or fails.
        
        Args:
            vector_store_id: ID of the vector store to check
            max_checks: Maximum number of status checks
            check_interval: Interval between checks in seconds
            prefix: Prefix for log messages
            
        Returns:
            Tuple of (is_ready, status) where status is the file counts
        """
        logger.info(f"{prefix}Checking vector store status: {vector_store_id}")
        
        for i in range(max_checks):
            try:
                response = self.client.beta.vector_stores.retrieve(vector_store_id)
                
                # Extract file counts
                if hasattr(response, 'file_counts'):
                    status = response.file_counts
                    total = status.get('total', 0)
                    completed = status.get('completed', 0)
                    failed = status.get('failed', 0)
                    in_progress = status.get('in_progress', 0)
                    
                    logger.info(f"{prefix}Vector store status: {completed}/{total} files processed, "
                              f"{in_progress} in progress, {failed} failed")
                    
                    # Check if processing is complete
                    if in_progress == 0 and (completed + failed) == total:
                        if failed == 0:
                            logger.info(f"{prefix}Vector store processing completed successfully")
                            return True, status
                        else:
                            logger.warning(f"{prefix}Vector store processing completed with {failed} failures")
                            return True, status
                
                # Continue checking if not complete
                if i < max_checks - 1:
                    logger.info(f"{prefix}Vector store still processing. Checking again in {check_interval} seconds...")
                    time.sleep(check_interval)
                
            except openai.OpenAIError as e:
                logger.error(f"{prefix}Error checking vector store status: {str(e)}")
                return False, None
        
        logger.warning(f"{prefix}Vector store processing did not complete after {max_checks} checks")
        return False, None
    
    def list_vector_stores(self, 
                         limit: int = 20,
                         prefix: str = "") -> List[Any]:
        """
        List available vector stores.
        
        Args:
            limit: Maximum number of vector stores to return
            prefix: Prefix for log messages
            
        Returns:
            List of vector store objects
        """
        logger.info(f"{prefix}Listing vector stores")
        
        try:
            response = self.client.beta.vector_stores.list(limit=limit)
            
            logger.info(f"{prefix}Found {len(response.data)} vector stores")
            return response.data
            
        except openai.OpenAIError as e:
            logger.error(f"{prefix}Error listing vector stores: {str(e)}")
            return []
    
    def delete_vector_store(self, 
                          vector_store_id: str,
                          prefix: str = "") -> bool:
        """
        Delete a vector store.
        
        Args:
            vector_store_id: ID of the vector store to delete
            prefix: Prefix for log messages
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"{prefix}Deleting vector store: {vector_store_id}")
        
        try:
            response = self.client.beta.vector_stores.delete(vector_store_id)
            
            logger.info(f"{prefix}Vector store deleted successfully")
            return getattr(response, 'deleted', True)  # Default to True if 'deleted' attr is missing
            
        except openai.OpenAIError as e:
            logger.error(f"{prefix}Error deleting vector store: {str(e)}")
            return False
    
    def search_vector_store(self, 
                          vector_store_id: str,
                          query: str,
                          max_results: int = 10,
                          filters: Optional[Dict[str, Any]] = None,
                          prefix: str = "") -> Dict[str, Any]:
        """
        Search a vector store for relevant content.
        
        Args:
            vector_store_id: ID of the vector store to search
            query: Search query
            max_results: Maximum number of results to return
            filters: Optional filters for search results
            prefix: Prefix for log messages
            
        Returns:
            Dictionary with search results
        """
        logger.info(f"{prefix}Searching vector store: {vector_store_id} for '{query}'")
        
        try:
            search_args = {
                "query": query,
                "max_num_results": max_results
            }
            
            if filters:
                search_args["filters"] = filters
            
            response = self.client.beta.vector_stores.search(
                vector_store_id=vector_store_id,
                **search_args
            )
            
            num_results = len(response.data) if hasattr(response, 'data') else 0
            logger.info(f"{prefix}Search returned {num_results} results")
            
            # Format response for easier consumption
            results = []
            if hasattr(response, 'data'):
                for item in response.data:
                    result = {
                        "file_id": item.file_id,
                        "filename": item.filename,
                        "score": item.score,
                        "content": []
                    }
                    
                    if hasattr(item, 'content'):
                        for content_item in item.content:
                            if hasattr(content_item, 'text'):
                                result["content"].append(content_item.text)
                    
                    results.append(result)
            
            return {
                "query": query,
                "results": results,
                "has_more": response.has_more if hasattr(response, 'has_more') else False
            }
            
        except openai.OpenAIError as e:
            logger.error(f"{prefix}Error searching vector store: {str(e)}")
            return {
                "query": query,
                "results": [],
                "has_more": False,
                "error": str(e)
            } 