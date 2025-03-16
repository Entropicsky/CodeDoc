"""
OpenAI Vector Store integration for CodeDoc.

This module provides functionality for interacting with OpenAI's vector store API,
including uploading files, managing embeddings, and retrieving information.
"""

import os
import json
import time
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable
import requests
from tqdm import tqdm

from openai import OpenAI, APIError

logger = logging.getLogger(__name__)


class OpenAIVectorStore:
    """
    Client for interacting with OpenAI's vector store API.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 organization: Optional[str] = None,
                 base_url: Optional[str] = None):
        """
        Initialize the OpenAI vector store client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY environment variable)
            organization: OpenAI organization ID (defaults to OPENAI_ORG_ID environment variable)
            base_url: OpenAI API base URL (defaults to OPENAI_API_BASE environment variable or 
                     the standard OpenAI API URL)
        """
        # Use environment variables if parameters not provided
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.organization = organization or os.environ.get("OPENAI_ORG_ID")
        self.base_url = base_url or os.environ.get("OPENAI_API_BASE")
        
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided or set as OPENAI_API_KEY environment variable")
            
        # Initialize the OpenAI client
        client_kwargs = {"api_key": self.api_key}
        if self.organization:
            client_kwargs["organization"] = self.organization
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
            
        self.client = OpenAI(**client_kwargs)
        
        logger.info("OpenAI vector store client initialized")
    
    def list_files(self) -> List[Dict[str, Any]]:
        """
        List all files in the OpenAI vector store.
        
        Returns:
            List of file metadata
        """
        try:
            response = self.client.files.list(purpose="assistants")
            return response.data
        except APIError as e:
            logger.error(f"Error listing vector store files: {str(e)}")
            raise
    
    def upload_file(self, file_path: Union[str, Path], purpose: str = "assistants", 
                    retry_limit: int = 3, retry_delay: float = 2.0) -> Dict[str, Any]:
        """
        Upload a file to the OpenAI vector store.
        
        Args:
            file_path: Path to the file to upload
            purpose: Purpose of the file, must be "assistants"
            retry_limit: Number of retries on error
            retry_delay: Delay between retries in seconds
            
        Returns:
            File metadata from OpenAI
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is empty or not supported
            APIError: If the OpenAI API returns an error
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Check file size
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ValueError(f"File is empty: {file_path}")
            
        # Check if file is too large (100MB limit)
        if file_size > 100 * 1024 * 1024:
            raise ValueError(f"File is too large: {file_size} bytes (limit is 100MB)")
            
        # Check if file has valid extension for OpenAI
        valid_extensions = [".jsonl", ".txt", ".pdf", ".doc", ".docx", ".md"]
        if file_path.suffix.lower() not in valid_extensions:
            logger.warning(f"File extension {file_path.suffix} may not be supported by OpenAI vector store")
            
        # Attempt to upload with retries
        attempts = 0
        last_error = None
        
        while attempts < retry_limit:
            try:
                logger.info(f"Uploading file {file_path} to OpenAI vector store")
                with open(file_path, "rb") as file:
                    response = self.client.files.create(
                        file=file,
                        purpose=purpose
                    )
                    
                logger.info(f"File uploaded successfully: {response.id}")
                return {
                    "id": response.id,
                    "filename": response.filename,
                    "purpose": response.purpose,
                    "bytes": response.bytes,
                    "created_at": response.created_at,
                    "status": response.status
                }
                
            except APIError as e:
                last_error = e
                attempts += 1
                logger.warning(f"Upload attempt {attempts} failed: {str(e)}")
                
                if attempts < retry_limit:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    # Increase the delay for subsequent retries
                    retry_delay *= 1.5
                    
        # If we've exhausted all retries, raise the last error
        logger.error(f"Upload failed after {retry_limit} attempts")
        raise last_error
    
    def upload_batch(self, batch_file_path: Union[str, Path], batch_size: int = 100, 
                     progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, Any]:
        """
        Upload a batch of documents from a JSONL file to the OpenAI vector store.
        
        The JSONL file should contain one document per line, with each line being a JSON object
        with at least a "text" field and optionally a "metadata" field.
        
        Example format:
        {"text": "Document content", "metadata": {"source": "file1.py", "line": 10}}
        
        Args:
            batch_file_path: Path to the JSONL batch file
            batch_size: Number of documents to process in each batch
            progress_callback: Optional callback function to report progress
            
        Returns:
            Dictionary with upload statistics
        """
        batch_file_path = Path(batch_file_path)
        if not batch_file_path.exists():
            raise FileNotFoundError(f"Batch file not found: {batch_file_path}")
            
        # Read and validate the batch file
        with open(batch_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        if not lines:
            raise ValueError(f"Batch file is empty: {batch_file_path}")
            
        # Validate and parse each line
        documents = []
        invalid_lines = []
        
        for i, line in enumerate(lines):
            try:
                doc = json.loads(line.strip())
                if "text" not in doc:
                    invalid_lines.append((i, "Missing 'text' field"))
                else:
                    documents.append(doc)
            except json.JSONDecodeError:
                invalid_lines.append((i, "Invalid JSON"))
                
        if invalid_lines:
            logger.warning(f"Found {len(invalid_lines)} invalid lines in batch file")
            for line_num, reason in invalid_lines[:10]:  # Show only first 10 errors
                logger.warning(f"  Line {line_num + 1}: {reason}")
            if len(invalid_lines) > 10:
                logger.warning(f"  ... and {len(invalid_lines) - 10} more issues")
                
        if not documents:
            raise ValueError("No valid documents found in batch file")
            
        logger.info(f"Uploading {len(documents)} documents in batches of {batch_size}")
        
        # Process in batches
        results = {
            "total_documents": len(documents),
            "total_batches": (len(documents) + batch_size - 1) // batch_size,
            "successful_documents": 0,
            "failed_documents": 0,
            "file_ids": [],
            "errors": []
        }
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            # Create a temporary batch file
            temp_file = batch_file_path.parent / f"temp_batch_{batch_num}_{int(time.time())}.jsonl"
            
            try:
                # Write the batch to a temporary file
                with open(temp_file, "w", encoding="utf-8") as f:
                    for doc in batch:
                        f.write(json.dumps(doc) + "\n")
                        
                # Upload the temporary file
                logger.info(f"Uploading batch {batch_num}/{results['total_batches']} "
                          f"({len(batch)} documents)")
                
                file_result = self.upload_file(temp_file)
                
                # Record the result
                results["file_ids"].append(file_result["id"])
                results["successful_documents"] += len(batch)
                
                # Report progress if callback provided
                if progress_callback:
                    progress_callback(batch_num, results["total_batches"])
                    
            except Exception as e:
                logger.error(f"Error uploading batch {batch_num}: {str(e)}")
                results["failed_documents"] += len(batch)
                results["errors"].append({"batch": batch_num, "error": str(e)})
                
            finally:
                # Clean up temporary file
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception as e:
                        logger.warning(f"Could not delete temporary file {temp_file}: {str(e)}")
                        
        logger.info(f"Batch upload complete: {results['successful_documents']} documents uploaded successfully, "
                  f"{results['failed_documents']} failed")
        
        return results
    
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get information about a specific file in the vector store.
        
        Args:
            file_id: ID of the file to retrieve
            
        Returns:
            File metadata
            
        Raises:
            APIError: If the file is not found or another API error occurs
        """
        try:
            response = self.client.files.retrieve(file_id)
            return {
                "id": response.id,
                "filename": response.filename,
                "purpose": response.purpose,
                "bytes": response.bytes,
                "created_at": response.created_at,
                "status": response.status
            }
        except APIError as e:
            logger.error(f"Error retrieving file {file_id}: {str(e)}")
            raise
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from the vector store.
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            APIError: If the file is not found or another API error occurs
        """
        try:
            response = self.client.files.delete(file_id)
            return response.deleted
        except APIError as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            raise
    
    def wait_for_file_processing(self, file_id: str, polling_interval: int = 5, 
                               timeout: int = 600) -> Dict[str, Any]:
        """
        Wait for a file to finish processing in the vector store.
        
        Args:
            file_id: ID of the file to wait for
            polling_interval: How often to check the file status in seconds
            timeout: Maximum time to wait in seconds
            
        Returns:
            File metadata once processing is complete
            
        Raises:
            TimeoutError: If the file does not finish processing within the timeout
            APIError: If an API error occurs
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                file_info = self.get_file_info(file_id)
                status = file_info.get("status")
                
                if status == "processed":
                    logger.info(f"File {file_id} has been processed successfully")
                    return file_info
                elif status == "error":
                    error_message = f"File {file_id} processing failed with status: {status}"
                    logger.error(error_message)
                    raise ValueError(error_message)
                    
                logger.info(f"File {file_id} is still processing (status: {status}). "
                          f"Checking again in {polling_interval} seconds...")
                time.sleep(polling_interval)
                
            except APIError as e:
                logger.error(f"Error checking file status for {file_id}: {str(e)}")
                raise
                
        raise TimeoutError(f"File {file_id} did not finish processing within {timeout} seconds")

    def search_vector_store(self, query: str, file_ids: Optional[List[str]] = None,
                          max_results: int = 10, metadata_filter: Optional[Dict[str, Any]] = None,
                          model: str = "text-embedding-3-small") -> List[Dict[str, Any]]:
        """
        Search the vector store using a natural language query.
        
        Args:
            query: Search query text
            file_ids: Optional list of file IDs to search within
            max_results: Maximum number of results to return
            metadata_filter: Optional filter for metadata fields
            model: Embedding model to use
            
        Returns:
            List of search results with document content and metadata
        """
        try:
            # Build the request
            request_args = {
                "query": query,
                "max_results": max_results,
                "model": model
            }
            
            if file_ids:
                request_args["file_ids"] = file_ids
                
            if metadata_filter:
                request_args["filter"] = metadata_filter
                
            # Execute the search
            logger.info(f"Searching vector store with query: '{query}'")
            response = self.client.vector_stores.file_search(**request_args)
            
            # Format the results
            results = []
            for match in response.data:
                results.append({
                    "text": match.text,
                    "metadata": match.metadata,
                    "score": match.score,
                    "file_id": match.file_id
                })
                
            logger.info(f"Search returned {len(results)} results")
            return results
            
        except APIError as e:
            logger.error(f"Error searching vector store: {str(e)}")
            raise


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
    
    parser = argparse.ArgumentParser(description="OpenAI Vector Store Utility")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Upload file command
    upload_parser = subparsers.add_parser("upload", help="Upload a file to the vector store")
    upload_parser.add_argument("file_path", help="Path to file to upload")
    
    # Upload batch command
    batch_parser = subparsers.add_parser("upload-batch", help="Upload a batch file to the vector store")
    batch_parser.add_argument("batch_file", help="Path to JSONL batch file")
    batch_parser.add_argument("--batch-size", type=int, default=100, help="Batch size for uploads")
    
    # List files command
    list_parser = subparsers.add_parser("list", help="List files in the vector store")
    
    # Get file info command
    info_parser = subparsers.add_parser("info", help="Get information about a file")
    info_parser.add_argument("file_id", help="ID of the file")
    
    # Delete file command
    delete_parser = subparsers.add_parser("delete", help="Delete a file from the vector store")
    delete_parser.add_argument("file_id", help="ID of the file to delete")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search the vector store")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--file-ids", nargs="+", help="File IDs to search within")
    search_parser.add_argument("--max-results", type=int, default=10, help="Maximum number of results")
    
    args = parser.parse_args()
    
    # Check for command
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    try:
        # Initialize the vector store client
        vector_store = OpenAIVectorStore()
        
        # Execute the command
        if args.command == "upload":
            result = vector_store.upload_file(args.file_path)
            print(f"File uploaded: {result['id']}")
            print(f"Status: {result['status']}")
            
        elif args.command == "upload-batch":
            def progress_callback(current, total):
                print(f"Progress: {current}/{total} batches processed")
                
            result = vector_store.upload_batch(args.batch_file, args.batch_size, progress_callback)
            print(f"Batch upload completed:")
            print(f"  Documents uploaded: {result['successful_documents']}/{result['total_documents']}")
            print(f"  Files created: {len(result['file_ids'])}")
            if result['failed_documents'] > 0:
                print(f"  Failed documents: {result['failed_documents']}")
                
        elif args.command == "list":
            files = vector_store.list_files()
            print(f"Found {len(files)} files:")
            for file in files:
                print(f"  {file.id}: {file.filename} ({file.status})")
                
        elif args.command == "info":
            file_info = vector_store.get_file_info(args.file_id)
            print(f"File: {file_info['id']}")
            print(f"Filename: {file_info['filename']}")
            print(f"Purpose: {file_info['purpose']}")
            print(f"Size: {file_info['bytes']} bytes")
            print(f"Created: {file_info['created_at']}")
            print(f"Status: {file_info['status']}")
            
        elif args.command == "delete":
            result = vector_store.delete_file(args.file_id)
            if result:
                print(f"File {args.file_id} deleted successfully")
            else:
                print(f"File deletion returned: {result}")
                
        elif args.command == "search":
            results = vector_store.search_vector_store(
                args.query,
                file_ids=args.file_ids,
                max_results=args.max_results
            )
            print(f"Search results for '{args.query}':")
            for i, result in enumerate(results, 1):
                print(f"\nResult {i} (score: {result['score']:.4f}):")
                print(f"File: {result['file_id']}")
                print(f"Source: {result['metadata'].get('file_path', 'Unknown')}")
                print("-" * 40)
                # Print a truncated version of the text
                text = result['text']
                if len(text) > 300:
                    text = text[:300] + "..."
                print(text)
                
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 