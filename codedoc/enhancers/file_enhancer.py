"""
File enhancement module for improving code documentation.

This module provides functionality for enhancing code files with improved documentation,
comments, and explanations using Large Language Models.
"""

import os
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable

from codedoc.llm.base import LLMClient, LLMResponse, LLMError
from codedoc.llm.prompt_manager import PromptManager, create_default_manager

logger = logging.getLogger(__name__)


class FileEnhancer:
    """
    Enhances source code files with improved documentation using LLMs.
    """
    
    def __init__(self, 
                 llm_client: LLMClient,
                 output_dir: Union[str, Path],
                 prompt_manager: Optional[PromptManager] = None,
                 model: Optional[str] = None,
                 temperature: float = 0.2):
        """
        Initialize the file enhancer.
        
        Args:
            llm_client: LLM client for generating enhanced documentation
            output_dir: Directory where enhanced files will be saved
            prompt_manager: Prompt manager for rendering templates (if None, uses default)
            model: Model to use for LLM interactions (if None, uses client default)
            temperature: Temperature for LLM generations (lower for more consistent results)
        """
        self.llm_client = llm_client
        self.output_dir = Path(output_dir)
        self.prompt_manager = prompt_manager or create_default_manager()
        self.model = model
        self.temperature = temperature
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"File enhancer initialized with output directory: {self.output_dir}")
        
        # Track stats
        self.stats = {
            "files_processed": 0,
            "files_enhanced": 0,
            "files_failed": 0,
            "total_tokens_used": 0,
        }
    
    def enhance_file(self, 
                     file_path: Union[str, Path], 
                     preserve_structure: bool = True,
                     callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None) -> Optional[str]:
        """
        Enhance a single file with improved documentation.
        
        Args:
            file_path: Path to the file to enhance
            preserve_structure: Whether to preserve the original file structure
            callback: Optional callback function to call after enhancement
                     Signature: callback(input_path, output_path, metadata)
            
        Returns:
            Path to the enhanced file, or None if enhancement failed
        """
        file_path = Path(file_path)
        
        # Create output directory structure
        try:
            # Determine output path, handling both absolute and relative paths
            file_path_abs = file_path.absolute()
            input_basename = file_path.name
            
            if preserve_structure:
                # Create relative path structure
                try:
                    rel_path = file_path.relative_to(Path.cwd())
                    output_path = self.output_dir / rel_path
                except ValueError:
                    # If relative_to fails, use just the filename
                    logger.warning(f"Could not determine relative path for {file_path}, using filename only")
                    output_path = self.output_dir / input_basename
            else:
                # Just use the filename
                output_path = self.output_dir / input_basename
                
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Enhancing file: {file_path} -> {output_path}")
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                logger.warning(f"Skipping empty file: {file_path}")
                return None
                
            # Render the prompt template
            prompt_vars = {
                "file_path": str(file_path),
                "content": content
            }
            
            # Use the code_enhancement template with system prompt
            prompts = self.prompt_manager.render_with_system("code_enhancement", prompt_vars)
            
            # Generate enhanced content
            start_time = time.time()
            response = self.llm_client.generate_with_system_prompt(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                model=self.model,
                temperature=self.temperature
            )
            duration = time.time() - start_time
            
            # Write enhanced content to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.content)
                
            # Update stats
            self.stats["files_processed"] += 1
            self.stats["files_enhanced"] += 1
            self.stats["total_tokens_used"] += response.tokens_used
            
            # Call the callback if provided
            if callback:
                metadata = {
                    "tokens_used": {
                        "prompt_tokens": response.tokens_prompt,
                        "completion_tokens": response.tokens_completion,
                        "total_tokens": response.tokens_used
                    },
                    "model": response.model,
                    "duration": duration,
                    "original_size": len(content),
                    "enhanced_size": len(response.content)
                }
                callback(str(file_path), str(output_path), metadata)
                
            logger.info(f"Enhanced file saved to {output_path} ({duration:.2f}s)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error enhancing file {file_path}: {str(e)}")
            self.stats["files_failed"] += 1
            return None
    
    def enhance_directory(self,
                         input_dir: Union[str, Path],
                         file_patterns: List[str] = ["*.py", "*.js", "*.java"],
                         recursive: bool = True,
                         exclude_dirs: Optional[List[str]] = None,
                         max_files: Optional[int] = None,
                         callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Enhance all matching files in a directory.
        
        Args:
            input_dir: Directory containing files to enhance
            file_patterns: List of glob patterns for files to enhance
            recursive: Whether to recursively process subdirectories
            exclude_dirs: List of directory names to exclude
            max_files: Maximum number of files to process
            callback: Optional callback function to call after each file
                     Signature: callback(input_path, output_path, metadata)
            
        Returns:
            Dictionary with enhancement statistics
        """
        input_dir = Path(input_dir)
        if not input_dir.exists():
            raise ValueError(f"Input directory not found: {input_dir}")
            
        # Set default exclude dirs if not provided
        exclude_dirs = exclude_dirs or [".git", "__pycache__", "venv", "env"]
        
        # Find all matching files
        all_files = []
        for pattern in file_patterns:
            if recursive:
                files = list(input_dir.rglob(pattern))
            else:
                files = list(input_dir.glob(pattern))
                
            # Filter out excluded directories
            files = [f for f in files if not any(d in str(f) for d in exclude_dirs)]
            all_files.extend(files)
            
        # Limit number of files if specified
        if max_files:
            all_files = all_files[:max_files]
            
        logger.info(f"Found {len(all_files)} files to enhance in {input_dir}")
        
        # Process each file
        enhanced_files = []
        failed_files = []
        
        for file_path in all_files:
            output_path = self.enhance_file(file_path, callback=callback)
            if output_path:
                enhanced_files.append(output_path)
            else:
                failed_files.append(str(file_path))
                
        logger.info(f"Enhancement completed. Processed {len(all_files)} files: "
                   f"{len(enhanced_files)} enhanced, {len(failed_files)} failed.")
        
        return {
            "stats": {
                "files_processed": len(all_files),
                "files_enhanced": len(enhanced_files),
                "files_failed": len(failed_files),
                "total_tokens_used": self.stats["total_tokens_used"]
            },
            "enhanced_files": enhanced_files,
            "failed_files": failed_files
        }


if __name__ == "__main__":
    # Example usage
    import argparse
    import sys
    from codedoc.llm.openai_client import OpenAIClient
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    parser = argparse.ArgumentParser(description="Enhance code files with improved documentation")
    parser.add_argument("input_path", help="Path to input file or directory")
    parser.add_argument("--output-dir", "-o", default="enhanced-code", help="Output directory for enhanced files")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process directories recursively")
    parser.add_argument("--model", default=None, help="LLM model to use")
    parser.add_argument("--temperature", type=float, default=0.2, help="Temperature for LLM generations")
    parser.add_argument("--max-files", type=int, default=None, help="Maximum number of files to process")
    
    args = parser.parse_args()
    
    try:
        # Initialize OpenAI client
        client = OpenAIClient()
        
        # Initialize file enhancer
        enhancer = FileEnhancer(
            llm_client=client,
            output_dir=args.output_dir,
            model=args.model,
            temperature=args.temperature
        )
        
        input_path = Path(args.input_path)
        
        # Process file or directory
        if input_path.is_file():
            enhanced_path = enhancer.enhance_file(input_path)
            if enhanced_path:
                print(f"Enhanced file saved to: {enhanced_path}")
        elif input_path.is_dir():
            stats = enhancer.enhance_directory(
                input_dir=input_path,
                recursive=args.recursive,
                max_files=args.max_files
            )
            print(f"Enhancement completed. Stats: {stats}")
        else:
            print(f"Error: {input_path} is not a valid file or directory")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 