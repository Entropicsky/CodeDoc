#!/usr/bin/env python3
"""
CodeDoc: A framework for deep code documentation and codebase understanding.

This tool analyzes a codebase, extracts deep semantic understanding, and generates
comprehensive documentation optimized for vector search and AI-assisted exploration.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from codedoc.config import settings
from codedoc.parsers import language_detector
from codedoc.parsers.python_parser import PythonParser, register_parser
from codedoc.exporters import GeneratorConfig, GeneratorRegistry
from codedoc.exporters.markdown_generator import MarkdownGenerator, register_generator
from codedoc.core.parser_config import ParserConfig
from codedoc.core.entities import ModuleEntity


def setup_logging():
    """Configure logging for the application."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[logging.StreamHandler()],
    )
    return logging.getLogger("codedoc")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CodeDoc: Deep code documentation and understanding framework."
    )
    
    parser.add_argument(
        "codebase_path",
        type=str,
        help="Path to the codebase to analyze",
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="./docs_output",
        help="Output directory for documentation (default: ./docs_output)",
    )
    
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include private members in documentation",
    )
    
    parser.add_argument(
        "--format",
        choices=["markdown"],
        default="markdown",
        help="Documentation format to generate (default: markdown)",
    )
    
    return parser.parse_args()


def main():
    """Main entry point for CodeDoc."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    logger = setup_logging()
    if args.verbose:
        logging.getLogger("codedoc").setLevel(logging.DEBUG)
    
    # Log startup information
    logger.info("CodeDoc starting up...")
    logger.info(f"Analyzing codebase at: {args.codebase_path}")
    logger.info(f"Documentation will be generated at: {args.output}")
    
    # Ensure the codebase path exists
    codebase_path = Path(args.codebase_path)
    if not codebase_path.exists():
        logger.error(f"Codebase path does not exist: {args.codebase_path}")
        sys.exit(1)
    
    # Ensure the output directory exists
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Register parsers and generators
    register_parser()
    register_generator()
    
    # Create parser configuration
    parser_config = ParserConfig(
        include_private_members=args.include_private,
        include_local_variables=False,
        max_depth=5,
        options={
            "include_docstrings": True,
            "include_source_code": True
        }
    )
    
    # Create documentation generator configuration
    generator_config = GeneratorConfig(
        format=args.format,
        include_private=args.include_private,
        include_source=True,
        include_types=True,
        include_examples=True,
        include_inheritance=True,
        include_references=True,
        include_toc=True,
        include_metadata=True,
        output_dir=str(output_path),
        title=f"Documentation for {codebase_path.name}"
    )
    
    # Create Python parser
    parser = PythonParser(parser_config)
    
    # Create documentation generator
    generator = MarkdownGenerator(generator_config)
    
    # Find all Python files in the codebase
    python_files = []
    for root, dirs, files in os.walk(codebase_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() == '.py':
                python_files.append(file_path)
    
    logger.info(f"Found {len(python_files)} Python files in the codebase")
    
    # Parse all Python files
    modules = []
    for file_path in python_files:
        try:
            logger.info(f"Parsing file: {file_path}")
            module = parser.parse_file(file_path)
            modules.append(module)
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
    
    # Generate documentation
    logger.info(f"Generating documentation in: {output_path}")
    
    for module in modules:
        try:
            doc_path = generator.generate_documentation(module, output_path)
            logger.debug(f"Generated documentation for {module.name} at {doc_path}")
        except Exception as e:
            logger.error(f"Error generating documentation for {module.name}: {e}")
    
    # Generate index
    if modules:
        try:
            index_path = generator.generate_index(
                modules, 
                output_path, 
                title=f"Documentation for {codebase_path.name}"
            )
            logger.info(f"Generated index at {index_path}")
        except Exception as e:
            logger.error(f"Error generating index: {e}")
    
    # Log completion
    logger.info("CodeDoc execution completed")


if __name__ == "__main__":
    main() 