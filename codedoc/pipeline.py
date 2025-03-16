"""
Main pipeline for CodeDoc.

This module provides the main pipeline that orchestrates the entire process
from code and documentation enhancement to vector store upload.
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable

from codedoc.enhancers.file_enhancer import FileEnhancer
from codedoc.enhancers.content_generator import ContentGenerator
from codedoc.enhancers.code_analyzer import CodeAnalyzer
from codedoc.preprocessors.direct_file_processor import DirectFileProcessor
from codedoc.integrations.openai_vector import OpenAIVectorClient
from codedoc.llm.base import LLMClient
from codedoc.llm.openai_client import OpenAIClient
from codedoc.llm.gemini_client import GeminiClient
from codedoc.llm.prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Main pipeline that orchestrates the code enhancement and vector upload process.
    """
    
    def __init__(self, 
                 output_dir: Union[str, Path],
                 llm_provider: str = "openai",
                 openai_api_key: Optional[str] = None,
                 gemini_api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 temperature: float = 0.2):
        """
        Initialize the pipeline.
        
        Args:
            output_dir: Base directory for all output
            llm_provider: LLM provider to use ('openai' or 'gemini')
            openai_api_key: OpenAI API key (defaults to environment variable)
            gemini_api_key: Gemini API key (defaults to environment variable)
            model: Model to use for enhancements (provider-specific)
            temperature: Temperature for LLM generation
        """
        self.output_dir = Path(output_dir)
        self.enhanced_code_dir = self.output_dir / "enhanced-codebase"
        self.supplementary_docs_dir = self.output_dir / "supplementary-docs"
        self.compiled_dir = self.output_dir / "compiled"
        self.metadata_dir = self.output_dir / "metadata"
        
        # Create all output directories
        for directory in [self.output_dir, self.enhanced_code_dir, 
                         self.supplementary_docs_dir, self.compiled_dir,
                         self.metadata_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        # Set up LLM client
        self.llm_provider = llm_provider.lower()
        
        # Default models based on provider
        if model is None:
            if self.llm_provider == "openai":
                model = "gpt-4o"
            elif self.llm_provider == "gemini":
                model = "gemini-1.5-pro"
            else:
                raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
                
        self.model = model
        self.temperature = temperature
                
        # Initialize LLM client
        if self.llm_provider == "openai":
            self.llm_client = OpenAIClient(api_key=openai_api_key)
        elif self.llm_provider == "gemini":
            self.llm_client = GeminiClient(api_key=gemini_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
            
        # Initialize prompt manager with templates directory
        templates_dir = Path(__file__).parent / "templates"
        if templates_dir.exists() and templates_dir.is_dir():
            self.prompt_manager = PromptManager(templates_dir=templates_dir)
            logger.debug(f"Using templates from: {templates_dir}")
        else:
            self.prompt_manager = PromptManager()
            logger.warning("Templates directory not found, using default templates")
        
        # Initialize components
        self.file_enhancer = FileEnhancer(
            llm_client=self.llm_client,
            output_dir=self.enhanced_code_dir,
            prompt_manager=self.prompt_manager,
            model=self.model,
            temperature=self.temperature
        )
        
        self.content_generator = ContentGenerator(
            llm_client=self.llm_client,
            output_dir=self.supplementary_docs_dir,
            prompt_manager=self.prompt_manager,
            model=self.model,
            temperature=self.temperature
        )
        
        self.code_analyzer = CodeAnalyzer(
            llm_client=self.llm_client,
            output_dir=self.metadata_dir,
            prompt_manager=self.prompt_manager,
            model=self.model,
            temperature=self.temperature
        )
        
        # Initialize OpenAI Vector client
        self.vector_client = OpenAIVectorClient(
            api_key=openai_api_key
        )
        
        # Initialize direct file processor
        self.file_processor = DirectFileProcessor(
            output_dir=self.compiled_dir,
            vector_client=self.vector_client
        )
        
        # Store the latest input directory
        self.input_dir = None
        
        # Initialize stats
        self.stats = {
            "files_enhanced": 0,
            "files_analyzed": 0,
            "supplementary_docs": 0,
            "files_processed": 0,
            "errors": []
        }
        
        logger.info(f"Pipeline initialized with output directory: {self.output_dir}")
        logger.info(f"Using LLM provider: {self.llm_provider}, model: {self.model}")
    
    def enhance_codebase(self, 
                        input_dir: Union[str, Path],
                        file_patterns: List[str] = ["*.py", "*.js", "*.java", "*.cpp", "*.h"],
                        recursive: bool = True,
                        exclude_dirs: Optional[List[str]] = None,
                        max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Enhance the codebase with improved documentation.
        
        Args:
            input_dir: Directory containing source code
            file_patterns: Glob patterns for files to enhance
            recursive: Whether to recursively process subdirectories
            exclude_dirs: List of directory names to exclude
            max_files: Maximum number of files to process
            
        Returns:
            Dictionary with enhancement statistics
        """
        logger.info(f"Enhancing codebase from: {input_dir}")
        
        # Store the input directory for later use
        self.input_dir = Path(input_dir)
        
        # Set default exclude dirs if not provided
        exclude_dirs = exclude_dirs or [".git", "__pycache__", "venv", "env", "node_modules", 
                                        "dist", "build", ".vscode", ".idea"]
        
        # Enhance files
        result = self.file_enhancer.enhance_directory(
            input_dir=input_dir,
            file_patterns=file_patterns,
            recursive=recursive,
            exclude_dirs=exclude_dirs,
            max_files=max_files
        )
        
        # Update statistics
        self.stats["files_enhanced"] += result["stats"]["files_enhanced"]
        self.stats["errors"].extend(result["failed_files"])
        
        return {
            "enhanced_files": result["stats"]["files_enhanced"],
            "total_files": result["stats"]["files_processed"],
            "failed_files": len(result["failed_files"]),
            "success_count": result["stats"]["files_enhanced"]
        }
    
    def analyze_codebase(self, 
                       input_dir: Union[str, Path],
                       file_patterns: List[str] = ["*.py", "*.js", "*.java", "*.cpp", "*.h"],
                       recursive: bool = True,
                       exclude_dirs: Optional[List[str]] = None,
                       max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze the codebase to identify patterns and extract complexity metrics.
        
        Args:
            input_dir: Directory containing source code
            file_patterns: Glob patterns for files to analyze
            recursive: Whether to recursively process subdirectories
            exclude_dirs: List of directory names to exclude
            max_files: Maximum number of files to process
            
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing codebase from: {input_dir}")
        
        # Set default exclude dirs if not provided
        exclude_dirs = exclude_dirs or [".git", "__pycache__", "venv", "env", "node_modules", 
                                        "dist", "build", ".vscode", ".idea"]
        
        # Analyze files
        result = self.code_analyzer.analyze_directory(
            input_dir=input_dir,
            file_patterns=file_patterns,
            recursive=recursive,
            exclude_dirs=exclude_dirs,
            max_files=max_files
        )
        
        # Update statistics
        self.stats["files_analyzed"] = result["stats"]["files_analyzed"]
        self.stats["errors"].extend(result.get("failed", []))
        
        logger.info(f"Codebase analysis completed: {result['stats']['files_analyzed']} files analyzed")
        
        return result
    
    def generate_supplementary_content(self, 
                                     source_dir: Union[str, Path],
                                     project_name: str,
                                     content_types: List[str] = ["faq", "tutorial", "architecture"],
                                     num_faqs: int = 15,
                                     num_tutorials: int = 3) -> Dict[str, Any]:
        """
        Generate supplementary documentation content based on the codebase.
        
        Args:
            source_dir: Directory containing the source code
            project_name: Name of the project
            content_types: Types of content to generate
            num_faqs: Number of FAQs to generate
            num_tutorials: Number of tutorials to generate
            
        Returns:
            Dictionary with generation statistics
        """
        logger.info(f"Generating supplementary content for project: {project_name}")
        
        results = {}
        
        # Generate each content type
        for content_type in content_types:
            if content_type.lower() == "faq":
                result = self.content_generator.generate_faq(
                    source_dir=source_dir,
                    project_name=project_name,
                    num_questions=num_faqs
                )
                results["faq"] = result
                
            elif content_type.lower() == "tutorial":
                result = self.content_generator.generate_tutorials(
                    source_dir=source_dir,
                    project_name=project_name,
                    num_tutorials=num_tutorials
                )
                results["tutorials"] = result
                
            elif content_type.lower() == "architecture":
                result = self.content_generator.generate_architecture_diagram(
                    source_dir=source_dir,
                    project_name=project_name
                )
                results["architecture"] = result
                
            else:
                logger.warning(f"Unknown content type: {content_type}")
                
        # Update statistics
        self.stats["supplementary_docs"] += len(results)
        
        logger.info(f"Supplementary content generation completed: {len(results)} items generated")
        
        return results
    
    def process_files_for_vectorization(self):
        """Process files for vectorization and upload to OpenAI."""
        if not self.input_dir:
            logger.error("No input directory specified.")
            return None
        
        logger.info("Processing files for vectorization...")
        processor = DirectFileProcessor(
            output_dir=self.output_compiled_dir,
            purpose=self.args.purpose if hasattr(self.args, 'purpose') else 'assistants',
            file_patterns=self.file_patterns
        )
        
        file_results = processor.process_directory(self.input_dir)
        
        logger.info(f"File processing completed: {file_results['summary']['successful_files']} files processed successfully, {file_results['summary']['failed_files']} failed")
        
        if file_results['summary']['successful_files'] == 0:
            logger.warning("No files were successfully processed. Skipping vector store creation.")
            return None
        
        logger.info(f"Uploaded {file_results['summary']['successful_files']} files to OpenAI")
        
        if hasattr(self.args, 'skip_upload') and self.args.skip_upload:
            logger.info("Skipping vector store creation as requested.")
            return None
        
        logger.info(f"Creating vector store with {len(file_results['summary']['uploaded_file_ids'])} uploaded files")
        
        logger.info("Creating OpenAI vector store")
        vector_store = processor.create_vector_store(
            name=f'"{self.args.project_name}"',
            file_ids=file_results['summary']['uploaded_file_ids']
        )
        
        if not vector_store:
            logger.info("Vector store creation failed")
            return None
        
        # Wait for files to be processed
        logger.info(f"Vector store created with ID: {vector_store.id}. Checking processing status...")
        is_ready, status = processor.vector_client.check_vector_store_status(
            vector_store_id=vector_store.id,
            max_checks=30,  # Increased for larger file counts
            check_interval=5  # Longer interval for larger batches
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
        
        logger.info(f"Vector store processing status: {status_dict}")
        if is_ready:
            logger.info(f"Vector store {vector_store.id} is ready for use!")
        else:
            logger.warning(f"Vector store {vector_store.id} is still processing. Check status manually later.")
        
        return vector_store.id
    
    def run_pipeline(self, 
                   input_dir: Union[str, Path],
                   project_name: str,
                   skip_enhancement: bool = False,
                   skip_analysis: bool = False,
                   skip_supplementary: bool = False,
                   skip_processing: bool = False,
                   skip_upload: bool = False,
                   file_patterns: List[str] = ["*.py", "*.js", "*.java", "*.cpp", "*.h"],
                   exclude_dirs: Optional[List[str]] = None,
                   max_files: Optional[int] = None,
                   openai_api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the full pipeline.
        
        Args:
            input_dir: Directory containing source code
            project_name: Name of the project
            skip_enhancement: Whether to skip code enhancement
            skip_analysis: Whether to skip code analysis
            skip_supplementary: Whether to skip supplementary content generation
            skip_processing: Whether to skip file processing for vectorization
            skip_upload: Whether to skip upload to vector store
            file_patterns: Glob patterns for files to enhance
            exclude_dirs: List of directory names to exclude
            max_files: Maximum number of files to process
            openai_api_key: OpenAI API key for vector store upload
            
        Returns:
            Dictionary with pipeline results
        """
        start_time = time.time()
        logger.info(f"Starting pipeline for project: {project_name}")
        
        results = {
            "enhancement": None,
            "analysis": None,
            "supplementary": None,
            "processing": None,
            "upload": None,
            "stats": None
        }
        
        # Step 1: Enhance codebase
        if not skip_enhancement:
            results["enhancement"] = self.enhance_codebase(
                input_dir=input_dir,
                file_patterns=file_patterns,
                exclude_dirs=exclude_dirs,
                max_files=max_files
            )
        else:
            logger.info("Skipping code enhancement")
            
        # Step 2: Analyze codebase
        if not skip_analysis:
            results["analysis"] = self.analyze_codebase(
                input_dir=input_dir,
                file_patterns=file_patterns,
                exclude_dirs=exclude_dirs,
                max_files=max_files
            )
        else:
            logger.info("Skipping code analysis")
            
        # Step 3: Generate supplementary content
        if not skip_supplementary:
            results["supplementary"] = self.generate_supplementary_content(
                source_dir=input_dir,
                project_name=project_name
            )
        else:
            logger.info("Skipping supplementary content generation")
            
        # Step 4: Process files for vectorization
        if not skip_processing:
            results["processing"] = self.process_files_for_vectorization()
        else:
            logger.info("Skipping file processing for vectorization")
            
        # Step 5: Create vector store with the uploaded files
        if not skip_upload and not skip_processing:
            # Check if we have uploaded files
            if results["processing"] and "uploaded_file_ids" in results["processing"] and results["processing"]["uploaded_file_ids"]:
                file_ids = results["processing"]["uploaded_file_ids"]
                logger.info(f"Creating vector store with {len(file_ids)} uploaded files")
                
                results["upload"] = self.upload_to_vector_store(
                    file_ids=file_ids,
                    name=project_name,
                    chunking_strategy={"type": "auto"},
                    metadata={"project": project_name}
                )
            else:
                logger.warning("No files were uploaded, skipping vector store creation")
                results["upload"] = {"status": "skipped", "reason": "no files uploaded"}
        else:
            logger.info("Skipping vector store creation")
            if skip_upload:
                results["upload"] = {"status": "skipped", "reason": "upload explicitly skipped"}
            else:
                results["upload"] = {"status": "skipped", "reason": "processing skipped"}
            
        # Update final statistics
        self.stats["total_duration"] = time.time() - start_time
        results["stats"] = self.stats
        
        logger.info(f"Pipeline completed in {self.stats['total_duration']:.2f} seconds")
        
        return results


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("codedoc_pipeline.log")
        ]
    )
    
    parser = argparse.ArgumentParser(description="CodeDoc Pipeline")
    
    # Required arguments
    parser.add_argument("input_dir", help="Directory containing source code")
    parser.add_argument("--project-name", "-p", required=True, help="Name of the project")
    parser.add_argument("--output-dir", "-o", default="codedoc-output", help="Output directory")
    
    # LLM provider options
    parser.add_argument("--llm-provider", choices=["openai", "gemini"], default="openai",
                      help="LLM provider to use")
    parser.add_argument("--model", help="Model to use for LLM (provider-specific)")
    parser.add_argument("--temperature", type=float, default=0.2,
                      help="Temperature for LLM generation")
    
    # Skip options
    parser.add_argument("--skip-enhancement", action="store_true", 
                      help="Skip code enhancement")
    parser.add_argument("--skip-analysis", action="store_true",
                      help="Skip code analysis")
    parser.add_argument("--skip-supplementary", action="store_true",
                      help="Skip supplementary content generation")
    parser.add_argument("--skip-processing", action="store_true",
                      help="Skip file processing for vectorization")
    parser.add_argument("--skip-upload", action="store_true",
                      help="Skip upload to vector store")
    
    # File selection options
    parser.add_argument("--file-patterns", nargs="+", 
                      default=["*.py", "*.js", "*.java", "*.cpp", "*.h", "*.md"],
                      help="Glob patterns for files to process")
    parser.add_argument("--exclude-dirs", nargs="+",
                      default=[".git", "__pycache__", "venv", "env", "node_modules"],
                      help="Directories to exclude")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process")
    
    args = parser.parse_args()
    
    try:
        # Initialize pipeline
        pipeline = Pipeline(
            output_dir=args.output_dir,
            llm_provider=args.llm_provider,
            model=args.model,
            temperature=args.temperature
        )
        
        # Run pipeline
        results = pipeline.run_pipeline(
            input_dir=args.input_dir,
            project_name=args.project_name,
            skip_enhancement=args.skip_enhancement,
            skip_analysis=args.skip_analysis,
            skip_supplementary=args.skip_supplementary,
            skip_processing=args.skip_processing,
            skip_upload=args.skip_upload,
            file_patterns=args.file_patterns,
            exclude_dirs=args.exclude_dirs,
            max_files=args.max_files
        )
        
        # Report final statistics
        stats = results["stats"]
        
        print("\nCodeDoc Pipeline Completed")
        print("========================")
        print(f"Total Duration: {stats['total_duration']:.2f} seconds")
        print(f"Files Enhanced: {stats.get('files_enhanced', 0)}")
        print(f"Files Analyzed: {stats.get('files_analyzed', 0)}")
        print(f"Content Items Generated: {stats.get('supplementary_docs', 0)}")
        print(f"Files Processed: {stats.get('files_processed', 0)}")
        
        # Print vector store information if available
        if 'vector_store_id' in stats:
            print(f"Vector Store ID: {stats['vector_store_id']}")
            print(f"Vector Store Name: {stats.get('vector_store_name', '')}")
            print(f"Vector Store Files: {stats.get('vector_store_completed', 0)} completed, "
                 f"{stats.get('vector_store_in_progress', 0)} in progress")
        
        print(f"Errors: {len(stats.get('errors', []))}")
        
        # Save results to file
        result_file = Path(args.output_dir) / "pipeline_results.json"
        import json
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump({
                "project_name": args.project_name,
                "input_directory": args.input_dir,
                "output_directory": args.output_dir,
                "stats": stats,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }, f, indent=2)
            
        print(f"\nResults saved to: {result_file}")
        print(f"Output directory: {args.output_dir}")
        
    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        sys.exit(1) 