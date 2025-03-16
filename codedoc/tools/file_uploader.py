"""
File Uploader Utility

This standalone utility provides functionality for:
1. Uploading files to OpenAI
2. Creating vector stores
3. Managing file batches
4. Recovering from failures

It's designed to be used both programmatically and as a CLI tool.
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Set, Tuple
from datetime import datetime

# Add parent directory to path to allow imports when run directly
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from codedoc.integrations.openai_vector import OpenAIVectorClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('file_uploader.log')
    ]
)

logger = logging.getLogger("file_uploader")


class FileUploader:
    """
    Uploads files to OpenAI and creates vector stores using the file batching API.
    
    Features:
    - Recursive directory traversal
    - File filtering
    - Batched uploads
    - Progress tracking
    - Resumability
    - Vector store creation
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        batch_size: int = 100,
        file_patterns: List[str] = ["*.py", "*.js", "*.java", "*.md", "*.txt", "*.html", "*.css", "*.json", "*.xml", "*.yml", "*.yaml"],
        exclude_dirs: List[str] = [".git", "__pycache__", "venv", "env", "node_modules", ".vscode", ".idea"],
        purpose: str = "assistants",
        output_dir: Optional[Union[str, Path]] = None,
        debug: bool = False
    ):
        """
        Initialize the file uploader.
        
        Args:
            api_key: OpenAI API key (defaults to env var)
            organization: OpenAI organization (defaults to env var)
            batch_size: Number of files per batch (max 100)
            file_patterns: File patterns to include
            exclude_dirs: Directories to exclude
            purpose: Purpose for file uploads (assistants, etc.)
            output_dir: Directory for state files and logs
            debug: Enable debug logging
        """
        # Set debug level if requested
        if debug:
            logger.setLevel(logging.DEBUG)
            # Add a debug file handler
            debug_handler = logging.FileHandler('file_uploader_debug.log')
            debug_handler.setLevel(logging.DEBUG)
            debug_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_handler.setFormatter(debug_formatter)
            logger.addHandler(debug_handler)
            
        logger.info("Initializing File Uploader")
        logger.debug(f"Parameters: batch_size={batch_size}, purpose={purpose}, debug={debug}")
        
        # Check for API key in environment if not provided
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key is None:
                logger.error("No API key provided and OPENAI_API_KEY environment variable not set")
                raise ValueError("OpenAI API key is required. Either pass api_key to the constructor or set the OPENAI_API_KEY environment variable.")
        
        # Initialize the OpenAI client
        try:
            self.vector_client = OpenAIVectorClient(
                api_key=api_key,
                organization=organization
            )
            logger.debug("Successfully initialized OpenAI Vector client")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI Vector client: {str(e)}")
            raise
        
        # Store configuration
        self.batch_size = min(batch_size, 100)  # Max 100 per OpenAI limits
        self.file_patterns = file_patterns
        self.exclude_dirs = exclude_dirs
        self.purpose = purpose
        
        # Setup output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path("file_uploader_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize state
        self.state_file = self.output_dir / "upload_state.json"
        self.state = self._load_state()
        
        # Statistics
        self.stats = {
            "files_found": 0,
            "files_uploaded": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "batches_created": 0,
            "batches_completed": 0,
            "batches_failed": 0,
            "vector_stores_created": 0,
            "start_time": time.time(),
            "end_time": None,
            "elapsed_time": 0
        }
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from file if it exists, otherwise initialize."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded state file: {self.state_file}")
                return state
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        
        # Initialize empty state
        return {
            "uploaded_files": {},  # Map of filepath -> OpenAI file ID
            "pending_files": [],   # List of files to upload
            "active_batches": {},  # Map of batch ID -> files
            "completed_batches": [],  # List of completed batch IDs
            "vector_stores": {}    # Map of vector store name -> ID
        }
    
    def _save_state(self):
        """Save current state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"Saved state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")
    
    def find_files(self, input_dir: Union[str, Path], recursive: bool = True) -> List[Path]:
        """
        Find all files in the input directory that match the patterns.
        
        Args:
            input_dir: Directory to search
            recursive: Whether to search subdirectories
            
        Returns:
            List of file paths
        """
        input_dir = Path(input_dir)
        if not input_dir.exists() or not input_dir.is_dir():
            raise ValueError(f"Invalid input directory: {input_dir}")
        
        logger.info(f"Finding files in {input_dir}")
        
        all_files = []
        
        if recursive:
            for pattern in self.file_patterns:
                for file_path in input_dir.glob(f"**/{pattern}"):
                    # Check if file is in an excluded directory
                    if any(excl in file_path.parts for excl in self.exclude_dirs):
                        continue
                    all_files.append(file_path)
        else:
            for pattern in self.file_patterns:
                for file_path in input_dir.glob(pattern):
                    all_files.append(file_path)
        
        logger.info(f"Found {len(all_files)} files matching patterns")
        self.stats["files_found"] = len(all_files)
        return all_files
    
    def upload_file(self, file_path: Path) -> Optional[str]:
        """
        Upload a single file to OpenAI.
        
        Args:
            file_path: Path to the file
            
        Returns:
            OpenAI file ID or None if upload failed
        """
        try:
            # Check if file was already uploaded
            rel_path = str(file_path)
            if rel_path in self.state["uploaded_files"]:
                logger.debug(f"File already uploaded: {rel_path} -> {self.state['uploaded_files'][rel_path]}")
                return self.state["uploaded_files"][rel_path]
            
            # Upload file to OpenAI
            response = self.vector_client.upload_file(
                file_path=file_path,
                purpose=self.purpose
            )
            
            if response:
                logger.debug(f"Uploaded file: {rel_path} -> {response.id}")
                self.state["uploaded_files"][rel_path] = response.id
                self._save_state()
                self.stats["files_uploaded"] += 1
                return response.id
            else:
                logger.error(f"Failed to upload file: {rel_path}")
                self.stats["files_failed"] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {str(e)}")
            self.stats["files_failed"] += 1
            return None
    
    def upload_files(self, files: List[Path]) -> List[str]:
        """
        Upload multiple files to OpenAI.
        
        Args:
            files: List of file paths
            
        Returns:
            List of successful OpenAI file IDs
        """
        logger.info(f"Uploading {len(files)} files")
        
        file_ids = []
        for i, file_path in enumerate(files):
            logger.info(f"Uploading file {i+1}/{len(files)}: {file_path}")
            file_id = self.upload_file(file_path)
            if file_id:
                file_ids.append(file_id)
        
        logger.info(f"Uploaded {len(file_ids)}/{len(files)} files successfully")
        return file_ids
    
    def create_file_batch(
        self, 
        vector_store_id: str, 
        file_ids: List[str],
        chunking_strategy: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a file batch for a vector store using the batching API.
        
        Args:
            vector_store_id: ID of the vector store
            file_ids: List of file IDs to add (max 100)
            chunking_strategy: Chunking strategy to use
            
        Returns:
            Batch information or None if creation failed
        """
        if len(file_ids) > 100:
            logger.warning(f"Too many files for one batch ({len(file_ids)}), limiting to 100")
            file_ids = file_ids[:100]
        
        if not chunking_strategy:
            chunking_strategy = {"type": "auto"}
            
        try:
            logger.info(f"Creating file batch with {len(file_ids)} files for vector store {vector_store_id}")
            
            response = self.vector_client.client.vector_stores.file_batches.create(
                vector_store_id=vector_store_id,
                file_ids=file_ids,
                chunking_strategy=chunking_strategy
            )
            
            if response:
                batch_id = response.id
                logger.info(f"Created file batch: {batch_id}")
                
                # Update state
                self.state["active_batches"][batch_id] = {
                    "vector_store_id": vector_store_id,
                    "file_ids": file_ids,
                    "status": response.status,
                    "created_at": response.created_at
                }
                self._save_state()
                
                self.stats["batches_created"] += 1
                return {
                    "batch_id": batch_id,
                    "vector_store_id": vector_store_id,
                    "status": response.status,
                    "file_counts": {
                        "in_progress": response.file_counts.in_progress if hasattr(response.file_counts, 'in_progress') else 0,
                        "completed": response.file_counts.completed if hasattr(response.file_counts, 'completed') else 0,
                        "failed": response.file_counts.failed if hasattr(response.file_counts, 'failed') else 0,
                        "cancelled": response.file_counts.cancelled if hasattr(response.file_counts, 'cancelled') else 0,
                        "total": response.file_counts.total if hasattr(response.file_counts, 'total') else 0
                    }
                }
            else:
                logger.error(f"Failed to create file batch for vector store {vector_store_id}")
                self.stats["batches_failed"] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error creating file batch: {str(e)}")
            self.stats["batches_failed"] += 1
            return None
    
    def check_batch_status(self, vector_store_id: str, batch_id: str) -> Dict[str, Any]:
        """
        Check the status of a file batch.
        
        Args:
            vector_store_id: ID of the vector store
            batch_id: ID of the batch
            
        Returns:
            Batch status information
        """
        try:
            logger.debug(f"Checking status of batch {batch_id}")
            
            response = self.vector_client.client.vector_stores.file_batches.retrieve(
                vector_store_id=vector_store_id,
                batch_id=batch_id
            )
            
            if response:
                status = response.status
                
                # Update state if complete
                if status in ["completed", "failed", "cancelled"]:
                    if batch_id in self.state["active_batches"]:
                        if status == "completed":
                            self.state["completed_batches"].append(batch_id)
                            self.stats["batches_completed"] += 1
                        elif status == "failed":
                            self.stats["batches_failed"] += 1
                            
                        self.state["active_batches"][batch_id]["status"] = status
                        self._save_state()
                
                return {
                    "batch_id": batch_id,
                    "vector_store_id": vector_store_id,
                    "status": status,
                    "file_counts": {
                        "in_progress": response.file_counts.in_progress if hasattr(response.file_counts, 'in_progress') else 0,
                        "completed": response.file_counts.completed if hasattr(response.file_counts, 'completed') else 0,
                        "failed": response.file_counts.failed if hasattr(response.file_counts, 'failed') else 0,
                        "cancelled": response.file_counts.cancelled if hasattr(response.file_counts, 'cancelled') else 0,
                        "total": response.file_counts.total if hasattr(response.file_counts, 'total') else 0
                    }
                }
            else:
                logger.error(f"Failed to retrieve batch {batch_id}")
                return {
                    "batch_id": batch_id,
                    "vector_store_id": vector_store_id,
                    "status": "unknown",
                    "error": "Failed to retrieve batch"
                }
                
        except Exception as e:
            logger.error(f"Error checking batch status: {str(e)}")
            return {
                "batch_id": batch_id,
                "vector_store_id": vector_store_id,
                "status": "error",
                "error": str(e)
            }
    
    def wait_for_batches(
        self, 
        batches: List[Dict[str, Any]], 
        max_checks: int = 30, 
        check_interval: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Wait for batches to complete processing.
        
        Args:
            batches: List of batch information dictionaries
            max_checks: Maximum number of status checks
            check_interval: Seconds between checks
            
        Returns:
            List of final batch statuses
        """
        logger.info(f"Waiting for {len(batches)} batches to complete")
        
        # Track active batches
        active_batches = {b["batch_id"]: b for b in batches}
        completed_batches = {}
        
        # Check status until all complete or max checks reached
        for check in range(max_checks):
            if not active_batches:
                logger.info("All batches completed")
                break
                
            logger.info(f"Check {check+1}/{max_checks}: {len(active_batches)} batches still active")
            
            # Check status of each active batch
            for batch_id, batch in list(active_batches.items()):
                status = self.check_batch_status(
                    vector_store_id=batch["vector_store_id"],
                    batch_id=batch_id
                )
                
                # Update batch info
                active_batches[batch_id].update(status)
                
                # Check if batch is complete
                if status["status"] in ["completed", "failed", "cancelled"]:
                    logger.info(f"Batch {batch_id} {status['status']}")
                    completed_batches[batch_id] = active_batches.pop(batch_id)
            
            # Sleep between checks if any batches still active
            if active_batches and check < max_checks - 1:
                time.sleep(check_interval)
        
        # Add any remaining active batches to completed list
        for batch_id, batch in active_batches.items():
            logger.warning(f"Batch {batch_id} still in progress after {max_checks} checks")
            completed_batches[batch_id] = batch
        
        logger.info(f"Batch processing complete: {len(completed_batches)} total")
        return list(completed_batches.values())
    
    def create_vector_store(
        self,
        name: str,
        files: List[Path],
        chunking_strategy: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Create a vector store from a list of files.
        
        This method:
        1. Uploads all files
        2. Creates an empty vector store
        3. Adds files in batches
        4. Waits for processing to complete
        
        Args:
            name: Name of the vector store
            files: List of file paths to include
            chunking_strategy: Chunking strategy to use
            max_retries: Maximum number of retries for failures
            
        Returns:
            Vector store ID or None if creation failed
        """
        logger.info(f"Creating vector store '{name}' with {len(files)} files")
        
        # Reset statistics
        self.stats["files_found"] = len(files)
        self.stats["files_uploaded"] = 0
        self.stats["files_skipped"] = 0
        self.stats["files_failed"] = 0
        self.stats["batches_created"] = 0
        self.stats["batches_completed"] = 0
        self.stats["batches_failed"] = 0
        self.stats["start_time"] = time.time()
        
        # Step 1: Upload all files
        file_ids = self.upload_files(files)
        
        if not file_ids:
            logger.error("No files were successfully uploaded")
            return None
        
        logger.info(f"Successfully uploaded {len(file_ids)} files")
        
        # Step 2: Create an empty vector store
        try:
            vector_store = self.vector_client.client.vector_stores.create(
                name=name
            )
            vector_store_id = vector_store.id
            
            # Update state
            self.state["vector_stores"][name] = vector_store_id
            self._save_state()
            
            logger.info(f"Created empty vector store: {vector_store_id}")
            self.stats["vector_stores_created"] += 1
            
        except Exception as e:
            logger.error(f"Failed to create vector store: {str(e)}")
            return None
        
        # Step 3: Add files in batches
        batches = []
        
        for i in range(0, len(file_ids), self.batch_size):
            batch_file_ids = file_ids[i:i + self.batch_size]
            logger.info(f"Creating batch {i//self.batch_size + 1}/{(len(file_ids) + self.batch_size - 1)//self.batch_size} with {len(batch_file_ids)} files")
            
            batch_result = self.create_file_batch(
                vector_store_id=vector_store_id,
                file_ids=batch_file_ids,
                chunking_strategy=chunking_strategy
            )
            
            if batch_result:
                batches.append(batch_result)
            else:
                logger.error(f"Failed to create batch {i//self.batch_size + 1}")
        
        if not batches:
            logger.error("No batches were successfully created")
            return vector_store_id
        
        logger.info(f"Created {len(batches)} batches")
        
        # Step 4: Wait for batches to complete
        batch_results = self.wait_for_batches(batches)
        
        # Step 5: Update statistics
        self.stats["end_time"] = time.time()
        self.stats["elapsed_time"] = self.stats["end_time"] - self.stats["start_time"]
        
        # Count completed batches
        completed_count = 0
        for batch in batch_results:
            if batch["status"] == "completed":
                completed_count += 1
                
        logger.info(f"Vector store creation complete: {completed_count}/{len(batches)} batches successful")
        logger.info(f"Vector store ID: {vector_store_id}")
        logger.info(f"Total time: {self.stats['elapsed_time']:.2f} seconds")
        
        return vector_store_id
    
    def process_directory(
        self,
        input_dir: Union[str, Path],
        vector_store_name: str,
        recursive: bool = True,
        chunking_strategy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an entire directory, creating a vector store.
        
        Args:
            input_dir: Directory containing files to process
            vector_store_name: Name for the vector store
            recursive: Whether to recursively process subdirectories
            chunking_strategy: Chunking strategy to use
            
        Returns:
            Dictionary with processing statistics and results
        """
        start_time = time.time()
        logger.info(f"Processing directory: {input_dir}")
        
        # Find all matching files
        files = self.find_files(input_dir, recursive=recursive)
        
        if not files:
            logger.warning(f"No matching files found in {input_dir}")
            return {
                "status": "error",
                "message": "No matching files found",
                "stats": self.stats
            }
        
        # Create vector store
        vector_store_id = self.create_vector_store(
            name=vector_store_name,
            files=files,
            chunking_strategy=chunking_strategy
        )
        
        if not vector_store_id:
            logger.error("Failed to create vector store")
            return {
                "status": "error",
                "message": "Failed to create vector store",
                "stats": self.stats
            }
        
        # Return results
        elapsed_time = time.time() - start_time
        
        return {
            "status": "success",
            "vector_store_id": vector_store_id,
            "vector_store_name": vector_store_name,
            "file_count": len(files),
            "uploaded_count": self.stats["files_uploaded"],
            "elapsed_time": elapsed_time,
            "stats": self.stats
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics."""
        return self.stats
    
    def reset_state(self) -> None:
        """Reset the state file."""
        self.state = {
            "uploaded_files": {},
            "pending_files": [],
            "active_batches": {},
            "completed_batches": [],
            "vector_stores": {}
        }
        self._save_state()
        logger.info("State reset")


def main():
    """Run the file uploader as a command-line tool."""
    parser = argparse.ArgumentParser(description='OpenAI File Uploader and Vector Store Creator')
    parser.add_argument('--input-dir', '-i', required=True, help='Input directory containing files to process')
    parser.add_argument('--vector-store-name', '-n', required=True, help='Name for the vector store')
    parser.add_argument('--output-dir', '-o', help='Output directory for logs and state')
    parser.add_argument('--batch-size', '-b', type=int, default=100, help='Batch size (max 100)')
    parser.add_argument('--api-key', help='OpenAI API key (defaults to env var)')
    parser.add_argument('--organization', help='OpenAI organization (defaults to env var)')
    parser.add_argument('--purpose', default='assistants', help='Purpose for file uploads')
    parser.add_argument('--patterns', nargs='+', help='File patterns to include')
    parser.add_argument('--exclude-dirs', nargs='+', help='Directories to exclude')
    parser.add_argument('--no-recursive', action='store_true', help='Disable recursive directory traversal')
    parser.add_argument('--reset-state', action='store_true', help='Reset state before processing')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Create uploader
    uploader = FileUploader(
        api_key=args.api_key,
        organization=args.organization,
        batch_size=args.batch_size,
        file_patterns=args.patterns if args.patterns else None,
        exclude_dirs=args.exclude_dirs if args.exclude_dirs else None,
        purpose=args.purpose,
        output_dir=args.output_dir,
        debug=args.debug
    )
    
    # Reset state if requested
    if args.reset_state:
        uploader.reset_state()
    
    # Process directory
    result = uploader.process_directory(
        input_dir=args.input_dir,
        vector_store_name=args.vector_store_name,
        recursive=not args.no_recursive
    )
    
    # Print result
    if result["status"] == "success":
        print(f"\nSuccess! Vector store created: {result['vector_store_id']}")
        print(f"Files processed: {result['file_count']}")
        print(f"Files uploaded: {result['uploaded_count']}")
        print(f"Time taken: {result['elapsed_time']:.2f} seconds")
    else:
        print(f"\nError: {result['message']}")
    
    # Print stats
    stats = uploader.get_statistics()
    print("\nStatistics:")
    for key, value in stats.items():
        if key not in ["start_time", "end_time"]:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main() 