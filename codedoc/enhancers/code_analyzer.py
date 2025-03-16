"""
Code analyzer module for pattern recognition and complexity analysis.

This module provides functionality for analyzing code to identify design patterns,
architectural approaches, and complexity factors using Large Language Models.
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable

from codedoc.llm.base import LLMClient, LLMResponse, LLMError
from codedoc.llm.prompt_manager import PromptManager, create_default_manager

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """
    Analyzes code for patterns, architecture, and complexity using LLMs.
    """
    
    def __init__(self, 
                 llm_client: LLMClient,
                 output_dir: Union[str, Path],
                 prompt_manager: Optional[PromptManager] = None,
                 model: Optional[str] = None,
                 temperature: float = 0.3):
        """
        Initialize the code analyzer.
        
        Args:
            llm_client: LLM client for analyzing code
            output_dir: Directory where analysis results will be saved
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
        logger.info(f"Code analyzer initialized with output directory: {self.output_dir}")
        
        # Track stats
        self.stats = {
            "files_processed": 0,
            "patterns_identified": 0,
            "complexity_analyses": 0,
            "total_tokens_used": 0,
        }
    
    def analyze_patterns(self, 
                        file_path: Union[str, Path],
                        output_format: str = "md") -> Optional[str]:
        """
        Analyze a file to identify design patterns and architectural approaches.
        
        Args:
            file_path: Path to the file to analyze
            output_format: Output format ("md" or "json")
            
        Returns:
            Path to the analysis results file, or None if analysis failed
            
        Raises:
            FileNotFoundError: If the input file doesn't exist
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Create output file path
        output_filename = f"{file_path.stem}_patterns.{output_format}"
        output_path = self.output_dir / output_filename
        
        logger.info(f"Analyzing patterns in file: {file_path}")
        
        try:
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
            
            # Use the pattern_recognition template with system prompt
            prompts = self.prompt_manager.render_with_system("pattern_recognition", prompt_vars)
            
            # Generate analysis
            start_time = time.time()
            response = self.llm_client.generate_with_system_prompt(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                model=self.model,
                temperature=self.temperature
            )
            duration = time.time() - start_time
            
            # Write analysis to output file
            if output_format == "json":
                # Try to extract structured data (pattern names, descriptions, etc.)
                # This is a simple approach - in a real implementation, you might use
                # more sophisticated parsing or ask the LLM to output JSON directly
                patterns = self._extract_patterns_from_text(response.content)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "file": str(file_path),
                        "analysis_type": "pattern_recognition",
                        "patterns": patterns,
                        "raw_analysis": response.content
                    }, f, indent=2)
            else:
                # Default to Markdown
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Design Pattern Analysis: {file_path.name}\n\n")
                    f.write(response.content)
                
            # Update stats
            self.stats["files_processed"] += 1
            self.stats["patterns_identified"] += 1
            self.stats["total_tokens_used"] += response.tokens_used
                
            logger.info(f"Pattern analysis saved to {output_path} ({duration:.2f}s)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error analyzing patterns in file {file_path}: {str(e)}")
            return None
    
    def analyze_complexity(self, 
                          file_path: Union[str, Path],
                          output_format: str = "md") -> Optional[str]:
        """
        Analyze a file for code complexity factors.
        
        Args:
            file_path: Path to the file to analyze
            output_format: Output format ("md" or "json")
            
        Returns:
            Path to the analysis results file, or None if analysis failed
            
        Raises:
            FileNotFoundError: If the input file doesn't exist
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Create output file path
        output_filename = f"{file_path.stem}_complexity.{output_format}"
        output_path = self.output_dir / output_filename
        
        logger.info(f"Analyzing complexity in file: {file_path}")
        
        try:
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
            
            # Use the complexity_analysis template with system prompt
            prompts = self.prompt_manager.render_with_system("complexity_analysis", prompt_vars)
            
            # Generate analysis
            start_time = time.time()
            response = self.llm_client.generate_with_system_prompt(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                model=self.model,
                temperature=self.temperature
            )
            duration = time.time() - start_time
            
            # Write analysis to output file
            if output_format == "json":
                # Try to extract structured data
                complexity_data = self._extract_complexity_from_text(response.content)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "file": str(file_path),
                        "analysis_type": "complexity_analysis",
                        "complexity": complexity_data,
                        "raw_analysis": response.content
                    }, f, indent=2)
            else:
                # Default to Markdown
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Complexity Analysis: {file_path.name}\n\n")
                    f.write(response.content)
                
            # Update stats
            self.stats["files_processed"] += 1
            self.stats["complexity_analyses"] += 1
            self.stats["total_tokens_used"] += response.tokens_used
                
            logger.info(f"Complexity analysis saved to {output_path} ({duration:.2f}s)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error analyzing complexity in file {file_path}: {str(e)}")
            return None
    
    def analyze_file(self, 
                    file_path: Union[str, Path],
                    analyses: List[str] = ["patterns", "complexity"],
                    output_format: str = "md") -> Dict[str, Any]:
        """
        Perform multiple analyses on a single file.
        
        Args:
            file_path: Path to the file to analyze
            analyses: List of analyses to perform ("patterns", "complexity")
            output_format: Output format ("md" or "json")
            
        Returns:
            Dictionary with paths to analysis results
        """
        results = {}
        
        if "patterns" in analyses:
            pattern_result = self.analyze_patterns(file_path, output_format)
            if pattern_result:
                results["patterns"] = pattern_result
                
        if "complexity" in analyses:
            complexity_result = self.analyze_complexity(file_path, output_format)
            if complexity_result:
                results["complexity"] = complexity_result
                
        return results
    
    def analyze_directory(self, 
                        input_dir: Union[str, Path],
                        file_patterns: List[str] = ["*.py", "*.js", "*.ts", "*.java", "*.cpp", "*.h", "*.c", "*.cs"],
                        analyses: List[str] = ["patterns", "complexity"],
                        output_format: str = "md",
                        recursive: bool = True,
                        exclude_dirs: Optional[List[str]] = None,
                        max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze all matching files in a directory.
        
        Args:
            input_dir: Directory containing files to analyze
            file_patterns: Glob patterns for files to include
            analyses: List of analyses to perform ("patterns", "complexity")
            output_format: Output format ("md" or "json")
            recursive: Whether to recursively process subdirectories
            exclude_dirs: List of directory names to exclude
            max_files: Maximum number of files to process
            
        Returns:
            Dictionary with analysis statistics
        """
        input_dir = Path(input_dir)
        if not input_dir.exists() or not input_dir.is_dir():
            raise ValueError(f"Invalid input directory: {input_dir}")
            
        exclude_dirs = exclude_dirs or [".git", "__pycache__", "venv", "env", "node_modules"]
        
        # Reset stats
        self.stats = {
            "files_processed": 0,
            "patterns_identified": 0,
            "complexity_analyses": 0,
            "total_tokens_used": 0,
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
            
        logger.info(f"Found {len(all_files)} files to analyze in {input_dir}")
        
        # Process each file
        analysis_results = []
        failed_files = []
        for file_path in all_files:
            try:
                result = self.analyze_file(file_path, analyses, output_format)
                if result:
                    analysis_results.append({
                        "file": str(file_path),
                        "results": result
                    })
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                failed_files.append(str(file_path))
                
        # Count files that were successfully analyzed
        files_analyzed = len(analysis_results)
        
        # Add results to stats
        self.stats["analysis_results"] = analysis_results
        self.stats["files_analyzed"] = files_analyzed
        
        # Generate summary report
        summary_path = self.output_dir / f"analysis_summary.{output_format}"
        try:
            if output_format == "json":
                with open(summary_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "stats": self.stats,
                        "results": analysis_results
                    }, f, indent=2)
            else:
                # Default to Markdown
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Code Analysis Summary\n\n")
                    f.write(f"- Files analyzed: {files_analyzed}\n")
                    f.write(f"- Patterns identified: {self.stats['patterns_identified']}\n")
                    f.write(f"- Complexity analyses: {self.stats['complexity_analyses']}\n")
                    f.write(f"- Total tokens used: {self.stats['total_tokens_used']}\n\n")
                    
                    f.write("## File Analysis Results\n\n")
                    for result in analysis_results:
                        f.write(f"### {result['file']}\n")
                        for analysis_type, path in result['results'].items():
                            f.write(f"- {analysis_type}: [{Path(path).name}]({Path(path).relative_to(self.output_dir)})\n")
                        f.write("\n")
        except Exception as e:
            logger.error(f"Error writing summary report: {str(e)}")
            
        logger.info(f"Analysis completed. Processed {len(all_files)} files.")
        
        return {
            "stats": {
                "files_processed": len(all_files),
                "files_analyzed": files_analyzed,
                "patterns_identified": self.stats["patterns_identified"],
                "complexity_analyses": self.stats["complexity_analyses"],
                "total_tokens_used": self.stats["total_tokens_used"]
            },
            "analysis_results": analysis_results,
            "failed": failed_files,
            "summary": str(summary_path) if summary_path.exists() else None
        }
    
    def _extract_patterns_from_text(self, text: str) -> List[Dict[str, str]]:
        """
        Extract pattern information from LLM response text.
        This is a simple implementation that looks for pattern names in headings.
        
        Args:
            text: LLM response text
            
        Returns:
            List of dictionaries with pattern information
        """
        patterns = []
        current_pattern = None
        current_description = []
        
        # Simple parsing based on Markdown headings
        for line in text.split('\n'):
            # Check for heading that might indicate a pattern name
            if line.startswith('# ') or line.startswith('## ') or line.startswith('### '):
                # If we were already collecting a pattern, save it
                if current_pattern:
                    patterns.append({
                        "name": current_pattern,
                        "description": '\n'.join(current_description).strip()
                    })
                
                # Start a new pattern
                current_pattern = line.lstrip('#').strip()
                current_description = []
            elif current_pattern:
                current_description.append(line)
        
        # Add the last pattern if there is one
        if current_pattern:
            patterns.append({
                "name": current_pattern,
                "description": '\n'.join(current_description).strip()
            })
            
        return patterns
    
    def _extract_complexity_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract complexity information from LLM response text.
        This is a simple implementation that looks for specific sections.
        
        Args:
            text: LLM response text
            
        Returns:
            Dictionary with complexity information
        """
        complexity_data = {
            "cognitive_complexity": None,
            "cyclometric_complexity": None,
            "complexity_factors": [],
            "simplification_suggestions": [],
            "time_complexity": None,
            "space_complexity": None
        }
        
        current_section = None
        section_content = []
        
        # Simple parsing based on Markdown headings
        for line in text.split('\n'):
            # Check for heading that might indicate a section
            if line.startswith('# ') or line.startswith('## ') or line.startswith('### '):
                # If we were already collecting a section, process it
                if current_section and section_content:
                    section_text = '\n'.join(section_content).strip()
                    
                    if "cognitive" in current_section.lower():
                        complexity_data["cognitive_complexity"] = section_text
                    elif "cyclometric" in current_section.lower():
                        complexity_data["cyclometric_complexity"] = section_text
                    elif "contribute" in current_section.lower() or "factor" in current_section.lower():
                        complexity_data["complexity_factors"] = self._extract_list_items(section_text)
                    elif "simplif" in current_section.lower() or "refactor" in current_section.lower():
                        complexity_data["simplification_suggestions"] = self._extract_list_items(section_text)
                    elif "time" in current_section.lower() and "complex" in current_section.lower():
                        complexity_data["time_complexity"] = section_text
                    elif "space" in current_section.lower() and "complex" in current_section.lower():
                        complexity_data["space_complexity"] = section_text
                
                # Start a new section
                current_section = line.lstrip('#').strip()
                section_content = []
            elif current_section:
                section_content.append(line)
        
        # Process the last section if there is one
        if current_section and section_content:
            section_text = '\n'.join(section_content).strip()
            
            if "cognitive" in current_section.lower():
                complexity_data["cognitive_complexity"] = section_text
            elif "cyclometric" in current_section.lower():
                complexity_data["cyclometric_complexity"] = section_text
            elif "contribute" in current_section.lower() or "factor" in current_section.lower():
                complexity_data["complexity_factors"] = self._extract_list_items(section_text)
            elif "simplif" in current_section.lower() or "refactor" in current_section.lower():
                complexity_data["simplification_suggestions"] = self._extract_list_items(section_text)
            elif "time" in current_section.lower() and "complex" in current_section.lower():
                complexity_data["time_complexity"] = section_text
            elif "space" in current_section.lower() and "complex" in current_section.lower():
                complexity_data["space_complexity"] = section_text
                
        return complexity_data
    
    def _extract_list_items(self, text: str) -> List[str]:
        """
        Extract list items from Markdown text.
        
        Args:
            text: Markdown text with list items
            
        Returns:
            List of extracted items
        """
        items = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                items.append(line[2:].strip())
            elif line.startswith('1. ') or (line.startswith(str(len(items) + 1) + '. ')):
                items.append(line[line.find('. ') + 2:].strip())
        return items


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
    
    parser = argparse.ArgumentParser(description="Analyze code patterns and complexity")
    parser.add_argument("input_path", help="Path to input file or directory")
    parser.add_argument("--output-dir", "-o", default="code-analysis", help="Output directory for analysis results")
    parser.add_argument("--analyses", "-a", nargs='+', default=["patterns", "complexity"], 
                        choices=["patterns", "complexity"], help="Analyses to perform")
    parser.add_argument("--format", "-f", default="md", choices=["md", "json"], help="Output format")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process directories recursively")
    parser.add_argument("--model", default=None, help="LLM model to use")
    parser.add_argument("--max-files", type=int, default=None, help="Maximum number of files to process")
    
    args = parser.parse_args()
    
    try:
        # Initialize OpenAI client
        client = OpenAIClient()
        
        # Initialize code analyzer
        analyzer = CodeAnalyzer(
            llm_client=client,
            output_dir=args.output_dir,
            model=args.model
        )
        
        input_path = Path(args.input_path)
        
        # Process file or directory
        if input_path.is_file():
            results = analyzer.analyze_file(input_path, args.analyses, args.format)
            print(f"Analysis results: {results}")
        elif input_path.is_dir():
            stats = analyzer.analyze_directory(
                input_dir=input_path,
                analyses=args.analyses,
                output_format=args.format,
                recursive=args.recursive,
                max_files=args.max_files
            )
            print(f"Analysis completed. Stats: {stats}")
        else:
            print(f"Error: {input_path} is not a valid file or directory")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 