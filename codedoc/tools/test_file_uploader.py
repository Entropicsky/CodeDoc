"""
Test Harness for File Uploader

This script tests the functionality of the FileUploader class
by processing a sample directory and verifying the results.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path

# Add parent directory to path
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from codedoc.tools.file_uploader import FileUploader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_harness")


def create_test_files(test_dir: Path, num_files: int = 5) -> None:
    """Create sample test files."""
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create Python files
    for i in range(num_files):
        py_file = test_dir / f"test_file_{i}.py"
        with open(py_file, 'w') as f:
            f.write(f'''"""
Test file {i} for file_uploader testing.
"""

def test_function_{i}():
    """Sample function for testing."""
    print("Hello from test file {i}")
    return {i}
''')
    
    # Create a markdown file
    md_file = test_dir / "README.md"
    with open(md_file, 'w') as f:
        f.write(f'''# Test Files

This directory contains test files for the file_uploader module.

## Generated Files

- {num_files} Python files
- This README.md file

## Testing Strategy

These files are used to test the file upload and vector store creation functionality.
''')
    
    logger.info(f"Created {num_files} Python files and 1 markdown file in {test_dir}")


def test_file_uploader(
    test_dir: Path,
    vector_store_name: str = "test_vector_store",
    batch_size: int = 10,
    debug: bool = False
) -> bool:
    """
    Test the FileUploader class.
    
    Args:
        test_dir: Directory containing test files
        vector_store_name: Name for the test vector store
        batch_size: Batch size for file uploads
        debug: Enable debug logging
        
    Returns:
        True if all tests pass, False otherwise
    """
    logger.info("Starting file uploader test")
    
    # Create output directory
    output_dir = test_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Create uploader with debug logging
    uploader = FileUploader(
        batch_size=batch_size,
        output_dir=output_dir,
        debug=debug
    )
    
    # Reset state to ensure clean test
    uploader.reset_state()
    
    # Step 1: Test file finding
    logger.info("Testing file finding...")
    files = uploader.find_files(test_dir)
    if not files:
        logger.error("No files found in test directory")
        return False
    logger.info(f"Found {len(files)} files")
    
    # Step 2: Test file upload
    logger.info("Testing file upload...")
    file_ids = uploader.upload_files(files)
    if not file_ids:
        logger.error("Failed to upload any files")
        return False
    logger.info(f"Uploaded {len(file_ids)} files")
    
    # Step 3: Test vector store creation
    logger.info("Testing vector store creation...")
    vector_store_id = uploader.create_vector_store(
        name=vector_store_name,
        files=files
    )
    
    if not vector_store_id:
        logger.error("Failed to create vector store")
        return False
    
    logger.info(f"Successfully created vector store: {vector_store_id}")
    
    # Check statistics
    stats = uploader.get_statistics()
    logger.info(f"Statistics: {stats}")
    
    if stats["files_failed"] > 0:
        logger.warning(f"{stats['files_failed']} files failed to upload")
    
    if stats["batches_failed"] > 0:
        logger.warning(f"{stats['batches_failed']} batches failed")
    
    return True


def main():
    """Run the test harness."""
    parser = argparse.ArgumentParser(description='Test harness for FileUploader')
    parser.add_argument('--create-files', '-c', action='store_true', help='Create test files')
    parser.add_argument('--num-files', '-n', type=int, default=5, help='Number of test files to create')
    parser.add_argument('--test-dir', '-d', default='test_files', help='Test directory')
    parser.add_argument('--vector-store-name', '-v', default='test_vector_store', help='Vector store name')
    parser.add_argument('--batch-size', '-b', type=int, default=10, help='Batch size')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Create test directory
    test_dir = Path(args.test_dir).resolve()
    
    # Create test files if requested
    if args.create_files:
        create_test_files(test_dir, args.num_files)
    
    # Run tests
    result = test_file_uploader(
        test_dir=test_dir,
        vector_store_name=args.vector_store_name,
        batch_size=args.batch_size,
        debug=args.debug
    )
    
    if result:
        logger.info("All tests passed successfully")
        return 0
    else:
        logger.error("Tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 