"""
Content generator module for creating supplementary documentation.

This module provides functionality for generating supplementary documentation like FAQs,
tutorials, architecture diagrams, and other explanatory content using LLMs.
"""

import os
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable

from codedoc.llm.base import LLMClient, LLMResponse, LLMError
from codedoc.llm.prompt_manager import PromptManager, create_default_manager

logger = logging.getLogger(__name__)


class ContentGenerator:
    """
    Generates supplementary documentation using LLMs.
    """
    
    def __init__(self, 
                 llm_client: LLMClient,
                 output_dir: Union[str, Path],
                 prompt_manager: Optional[PromptManager] = None,
                 model: Optional[str] = None,
                 temperature: float = 0.5):
        """
        Initialize the content generator.
        
        Args:
            llm_client: LLM client for generating content
            output_dir: Directory where generated content will be saved
            prompt_manager: Prompt manager for rendering templates (if None, uses default)
            model: Model to use for LLM interactions (if None, uses client default)
            temperature: Temperature for LLM generations (higher for more creative content)
        """
        self.llm_client = llm_client
        self.output_dir = Path(output_dir)
        self.prompt_manager = prompt_manager or create_default_manager()
        self.model = model
        self.temperature = temperature
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Content generator initialized with output directory: {self.output_dir}")
        
        # Track stats
        self.stats = {
            "faqs_generated": 0,
            "tutorials_generated": 0,
            "other_content_generated": 0,
            "total_tokens_used": 0,
        }
    
    def generate_faq(self, 
                    content: Union[str, Path],
                    output_filename: Optional[str] = None) -> Optional[str]:
        """
        Generate a FAQ document from code or documentation.
        
        Args:
            content: Content to generate FAQ from (file path or string)
            output_filename: Name for the output file (default: {input_basename}_faq.md)
            
        Returns:
            Path to the generated FAQ file, or None if generation failed
        """
        try:
            # Handle content as file path or string
            if isinstance(content, (str, Path)) and os.path.exists(content):
                file_path = Path(content)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content_text = f.read()
                
                if not output_filename:
                    output_filename = f"{file_path.stem}_faq.md"
            else:
                content_text = str(content)
                if not output_filename:
                    output_filename = "generated_faq.md"
            
            output_path = self.output_dir / output_filename
            logger.info(f"Generating FAQ to {output_path}")
            
            # Render the prompt template
            prompt_vars = {
                "content": content_text
            }
            
            # Use the faq_generation template with system prompt
            prompts = self.prompt_manager.render_with_system("faq_generation", prompt_vars)
            
            # Generate FAQ content
            start_time = time.time()
            response = self.llm_client.generate_with_system_prompt(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                model=self.model,
                temperature=self.temperature
            )
            duration = time.time() - start_time
            
            # Write FAQ to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# Frequently Asked Questions\n\n")
                f.write(response.content)
                
            # Update stats
            self.stats["faqs_generated"] += 1
            self.stats["total_tokens_used"] += response.tokens_used
                
            logger.info(f"FAQ generated and saved to {output_path} ({duration:.2f}s)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating FAQ: {str(e)}")
            return None
    
    def generate_tutorial(self, 
                         content: Union[str, Path],
                         tutorial_topic: str,
                         audience_level: str = "intermediate",
                         output_filename: Optional[str] = None) -> Optional[str]:
        """
        Generate a tutorial document from code or documentation.
        
        Args:
            content: Content to generate tutorial from (file path or string)
            tutorial_topic: Topic of the tutorial (e.g., "How to use the API")
            audience_level: Target audience level (beginner, intermediate, advanced)
            output_filename: Name for the output file (default: {topic}_tutorial.md)
            
        Returns:
            Path to the generated tutorial file, or None if generation failed
        """
        try:
            # Handle content as file path or string
            if isinstance(content, (str, Path)) and os.path.exists(content):
                file_path = Path(content)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content_text = f.read()
            else:
                content_text = str(content)
            
            # Create sanitized topic for filename
            if not output_filename:
                topic_slug = tutorial_topic.lower().replace(' ', '_')
                output_filename = f"{topic_slug}_tutorial.md"
            
            output_path = self.output_dir / output_filename
            logger.info(f"Generating tutorial on '{tutorial_topic}' to {output_path}")
            
            # Render the prompt template
            prompt_vars = {
                "content": content_text,
                "tutorial_topic": tutorial_topic,
                "audience_level": audience_level
            }
            
            # Use the tutorial_generation template with system prompt
            prompts = self.prompt_manager.render_with_system("tutorial_generation", prompt_vars)
            
            # Generate tutorial content
            start_time = time.time()
            response = self.llm_client.generate_with_system_prompt(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                model=self.model,
                temperature=self.temperature
            )
            duration = time.time() - start_time
            
            # Write tutorial to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {tutorial_topic}\n\n")
                f.write(response.content)
                
            # Update stats
            self.stats["tutorials_generated"] += 1
            self.stats["total_tokens_used"] += response.tokens_used
                
            logger.info(f"Tutorial on '{tutorial_topic}' generated and saved to {output_path} ({duration:.2f}s)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating tutorial: {str(e)}")
            return None
    
    def generate_custom_content(self, 
                              content: Union[str, Path],
                              system_prompt: str,
                              user_prompt: str,
                              output_filename: str,
                              content_type: Optional[str] = "other") -> Optional[str]:
        """
        Generate custom documentation content with custom prompts.
        
        Args:
            content: Content to use as reference (file path or string)
            system_prompt: System prompt for the LLM
            user_prompt: User prompt for the LLM
            output_filename: Name for the output file
            content_type: Type of content for stats tracking
            
        Returns:
            Path to the generated content file, or None if generation failed
        """
        try:
            # Handle content as file path or string
            if isinstance(content, (str, Path)) and os.path.exists(content):
                file_path = Path(content)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content_text = f.read()
            else:
                content_text = str(content)
            
            output_path = self.output_dir / output_filename
            logger.info(f"Generating custom content to {output_path}")
            
            # Format prompts with content
            formatted_user_prompt = user_prompt.replace("{content}", content_text)
            
            # Generate content
            start_time = time.time()
            response = self.llm_client.generate_with_system_prompt(
                system_prompt=system_prompt,
                user_prompt=formatted_user_prompt,
                model=self.model,
                temperature=self.temperature
            )
            duration = time.time() - start_time
            
            # Write content to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.content)
                
            # Update stats
            self.stats["other_content_generated"] += 1
            self.stats["total_tokens_used"] += response.tokens_used
                
            logger.info(f"Custom content generated and saved to {output_path} ({duration:.2f}s)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating custom content: {str(e)}")
            return None
    
    def generate_architecture_diagram(self,
                                   source_dir: Union[str, Path],
                                   project_name: str) -> Dict[str, Any]:
        """
        Generate an architecture diagram for a project.
        
        Args:
            source_dir: Directory containing the source code
            project_name: Name of the project
            
        Returns:
            Dictionary with generation statistics
        """
        try:
            source_dir = Path(source_dir)
            output_filename = f"{project_name.lower().replace(' ', '_')}_architecture.md"
            output_path = self.output_dir / output_filename
            
            logger.info(f"Generating architecture diagram for {project_name} to {output_path}")
            
            # Collect sample files to use as reference
            sample_files = []
            for ext in ['.py', '.js', '.java', '.md', '.rst', '.txt']:
                files = list(source_dir.glob(f"**/*{ext}"))
                sample_files.extend(files[:5])  # Take up to 5 files of each type
            
            # Read content from sample files
            content_samples = []
            file_structure = []
            
            for file_path in sample_files[:15]:  # Limit to 15 files total
                try:
                    rel_path = file_path.relative_to(source_dir)
                    file_structure.append(str(rel_path))
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content_samples.append(f"# File: {rel_path}\n{f.read()}")
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {str(e)}")
            
            combined_content = "\n\n".join(content_samples)
            
            # Also gather directory structure
            try:
                import subprocess
                find_cmd = f"find {source_dir} -type d | sort"
                result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
                directory_structure = result.stdout
            except Exception:
                directory_structure = "\n".join(str(d) for d in source_dir.glob("**/*") if d.is_dir())
            
            # Render the prompt template
            prompt_vars = {
                "project_name": project_name,
                "content_samples": combined_content,
                "file_structure": "\n".join(file_structure),
                "directory_structure": directory_structure
            }
            
            # Use the architecture_diagram template with system prompt
            prompts = self.prompt_manager.render_with_system("architecture_diagram", prompt_vars)
            
            # Generate architecture content
            start_time = time.time()
            response = self.llm_client.generate_with_system_prompt(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                model=self.model,
                temperature=self.temperature
            )
            duration = time.time() - start_time
            
            # Write architecture diagram to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {project_name} - Architecture\n\n")
                f.write(response.content)
                
            # Update stats
            self.stats["architecture_diagrams_generated"] = 1
            self.stats["total_tokens_used"] += response.tokens_used
                
            logger.info(f"Architecture diagram generated and saved to {output_path} ({duration:.2f}s)")
            
            return {
                "output_path": str(output_path),
                "tokens_used": response.tokens_used,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"Error generating architecture diagram: {str(e)}")
            return {
                "error": str(e),
                "generated": False
            }
    
    def batch_generate(self, 
                      input_files: List[Union[str, Path]],
                      content_types: List[str] = ["faq"],
                      topics: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate multiple content pieces for multiple input files.
        
        Args:
            input_files: List of file paths to process
            content_types: List of content types to generate ("faq", "tutorial", "diagram")
            topics: Dictionary mapping file paths to tutorial topics (for tutorials)
            
        Returns:
            Dictionary with generation statistics and results
        """
        results = {
            "generated_files": [],
            "failed_files": [],
            "stats": {
                "total_files_processed": 0,
                "total_content_pieces": 0
            }
        }
        
        topics = topics or {}
        
        for file_path in input_files:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                results["failed_files"].append(str(file_path))
                continue
                
            file_results = []
            
            # Generate each requested content type
            for content_type in content_types:
                try:
                    if content_type == "faq":
                        output_path = self.generate_faq(file_path)
                        if output_path:
                            file_results.append({"type": "faq", "path": output_path})
                            
                    elif content_type == "tutorial":
                        # Get topic for this file, or use a default
                        topic = topics.get(str(file_path), f"Using {file_path.stem}")
                        output_path = self.generate_tutorial(file_path, topic)
                        if output_path:
                            file_results.append({"type": "tutorial", "path": output_path})
                            
                    elif content_type == "diagram":
                        output_path = self.generate_file_architecture_diagram(file_path)
                        if output_path:
                            file_results.append({"type": "diagram", "path": output_path})
                            
                except Exception as e:
                    logger.error(f"Error generating {content_type} for {file_path}: {str(e)}")
            
            # Track results for this file
            if file_results:
                results["generated_files"].append({
                    "input_file": str(file_path),
                    "outputs": file_results
                })
            else:
                results["failed_files"].append(str(file_path))
                
            results["stats"]["total_files_processed"] += 1
            results["stats"]["total_content_pieces"] += len(file_results)
                
        # Add overall stats
        results["stats"].update(self.stats)
        
        return results

    # Add overloaded generate_faq method that matches the pipeline's call signature
    def generate_faq(self, 
                    source_dir: Union[str, Path],
                    project_name: str,
                    num_questions: int = 15) -> Dict[str, Any]:
        """
        Generate a FAQ document for a project.
        
        Args:
            source_dir: Directory containing the source code
            project_name: Name of the project
            num_questions: Number of questions to generate
            
        Returns:
            Dictionary with generation statistics
        """
        try:
            source_dir = Path(source_dir)
            output_filename = f"{project_name.lower().replace(' ', '_')}_faq.md"
            output_path = self.output_dir / output_filename
            
            logger.info(f"Generating project FAQ for {project_name} to {output_path}")
            
            # Collect sample files to use as reference
            sample_files = []
            for ext in ['.py', '.js', '.java', '.md', '.rst', '.txt']:
                files = list(source_dir.glob(f"**/*{ext}"))
                sample_files.extend(files[:5])  # Take up to 5 files of each type
            
            # Read content from sample files
            content_samples = []
            for file_path in sample_files[:10]:  # Limit to 10 files total
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content_samples.append(f.read())
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {str(e)}")
            
            combined_content = "\n\n".join(content_samples)
            
            # Render the prompt template
            prompt_vars = {
                "project_name": project_name,
                "content_samples": combined_content,
                "num_questions": num_questions
            }
            
            # Use the faq_generation template with system prompt
            prompts = self.prompt_manager.render_with_system("faq_generation", prompt_vars)
            
            # Generate FAQ content
            start_time = time.time()
            response = self.llm_client.generate_with_system_prompt(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                model=self.model,
                temperature=self.temperature
            )
            duration = time.time() - start_time
            
            # Write FAQ to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {project_name} - Frequently Asked Questions\n\n")
                f.write(response.content)
                
            # Update stats
            self.stats["faqs_generated"] += 1
            self.stats["total_tokens_used"] += response.tokens_used
                
            logger.info(f"Project FAQ generated and saved to {output_path} ({duration:.2f}s)")
            
            return {
                "output_path": str(output_path),
                "questions_generated": num_questions,
                "tokens_used": response.tokens_used,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"Error generating project FAQ: {str(e)}")
            return {
                "error": str(e),
                "questions_generated": 0
            }
    
    def generate_tutorials(self,
                         source_dir: Union[str, Path],
                         project_name: str,
                         num_tutorials: int = 3) -> Dict[str, Any]:
        """
        Generate tutorial documents for a project.
        
        Args:
            source_dir: Directory containing the source code
            project_name: Name of the project
            num_tutorials: Number of tutorials to generate
            
        Returns:
            Dictionary with generation statistics
        """
        try:
            source_dir = Path(source_dir)
            output_dir = self.output_dir / "tutorials"
            output_dir.mkdir(exist_ok=True)
            
            logger.info(f"Generating {num_tutorials} tutorials for {project_name}")
            
            # Collect sample files to use as reference
            sample_files = []
            for ext in ['.py', '.js', '.java', '.md', '.rst', '.txt']:
                files = list(source_dir.glob(f"**/*{ext}"))
                sample_files.extend(files[:3])  # Take up to 3 files of each type
            
            # Read content from sample files
            content_samples = []
            for file_path in sample_files[:10]:  # Limit to 10 files total
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content_samples.append(f.read())
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {str(e)}")
            
            combined_content = "\n\n".join(content_samples)
            
            # Determine tutorial topics
            prompt_vars = {
                "project_name": project_name,
                "content_samples": combined_content,
                "num_tutorials": num_tutorials
            }
            
            # Use the tutorial_topics template with system prompt
            prompts = self.prompt_manager.render_with_system("tutorial_topics", prompt_vars)
            
            topics_response = self.llm_client.generate_with_system_prompt(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                model=self.model,
                temperature=self.temperature
            )
            
            # Parse topics (expecting one per line)
            topics = topics_response.content.strip().split("\n")
            topics = [t.strip() for t in topics if t.strip()][:num_tutorials]
            
            # Generate each tutorial
            tutorials_generated = []
            for i, topic in enumerate(topics):
                try:
                    topic_slug = topic.lower().replace(' ', '_').replace('/', '_')
                    output_filename = f"{i+1:02d}_{topic_slug}.md"
                    output_path = output_dir / output_filename
                    
                    # Render the prompt template
                    prompt_vars = {
                        "project_name": project_name,
                        "content_samples": combined_content,
                        "tutorial_topic": topic
                    }
                    
                    # Use the tutorial_generation template with system prompt
                    prompts = self.prompt_manager.render_with_system("tutorial_generation", prompt_vars)
                    
                    # Generate tutorial content
                    start_time = time.time()
                    response = self.llm_client.generate_with_system_prompt(
                        system_prompt=prompts["system"],
                        user_prompt=prompts["user"],
                        model=self.model,
                        temperature=self.temperature
                    )
                    duration = time.time() - start_time
                    
                    # Write tutorial to output file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {project_name} - {topic}\n\n")
                        f.write(response.content)
                        
                    # Update stats
                    self.stats["tutorials_generated"] += 1
                    self.stats["total_tokens_used"] += response.tokens_used
                    
                    tutorials_generated.append({
                        "topic": topic,
                        "output_path": str(output_path),
                        "tokens_used": response.tokens_used,
                        "duration": duration
                    })
                    
                    logger.info(f"Tutorial on '{topic}' generated and saved to {output_path} ({duration:.2f}s)")
                    
                except Exception as e:
                    logger.error(f"Error generating tutorial on '{topic}': {str(e)}")
            
            return {
                "tutorials_generated": tutorials_generated,
                "total_generated": len(tutorials_generated),
                "total_tokens_used": sum(t["tokens_used"] for t in tutorials_generated)
            }
            
        except Exception as e:
            logger.error(f"Error generating tutorials: {str(e)}")
            return {
                "error": str(e),
                "total_generated": 0
            }

    # Single file version of architecture diagram generation
    def generate_file_architecture_diagram(self, 
                                     content: Union[str, Path],
                                     output_filename: Optional[str] = None,
                                     diagram_type: str = "component") -> Optional[str]:
        """
        Generate an architecture diagram description in Mermaid or PlantUML format for a single file.
        
        Args:
            content: Content to generate diagram from (file path or string)
            output_filename: Name for the output file (default: architecture_diagram.md)
            diagram_type: Type of diagram to generate (component, class, sequence, etc.)
            
        Returns:
            Path to the generated diagram file, or None if generation failed
        """
        try:
            # Handle content as file path or string
            if isinstance(content, (str, Path)) and os.path.exists(content):
                file_path = Path(content)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content_text = f.read()
                
                if not output_filename:
                    output_filename = f"{file_path.stem}_architecture.md"
            else:
                content_text = str(content)
                if not output_filename:
                    output_filename = "architecture_diagram.md"
            
            output_path = self.output_dir / output_filename
            logger.info(f"Generating architecture diagram to {output_path}")
            
            # Custom prompts for diagram generation
            system_prompt = f"""You are an expert software architect who specializes in creating {diagram_type} diagrams.
Your task is to analyze code and create a detailed {diagram_type} diagram in Mermaid format.
Focus on key components, their relationships, and the overall architecture.
The diagram should be clear, accurate, and reflect the actual structure of the code."""
            
            user_prompt = f"""Based on the following code, create a {diagram_type} diagram in Mermaid format.
Make sure to:
1. Include all important components/classes/entities
2. Show relationships between components
3. Include brief descriptions where helpful
4. Keep the diagram focused and readable

Code to analyze:

{{content}}

Start with a brief explanation of the architecture, then provide the Mermaid diagram code between ```mermaid and ``` tags."""
            
            # Format user prompt with content
            formatted_user_prompt = user_prompt.replace("{content}", content_text)
            
            # Generate diagram
            start_time = time.time()
            response = self.llm_client.generate_with_system_prompt(
                system_prompt=system_prompt,
                user_prompt=formatted_user_prompt,
                model=self.model,
                temperature=self.temperature
            )
            duration = time.time() - start_time
            
            # Write diagram to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Architecture Diagram ({diagram_type})\n\n")
                f.write(response.content)
                
            # Update stats
            self.stats["other_content_generated"] += 1
            self.stats["total_tokens_used"] += response.tokens_used
                
            logger.info(f"Architecture diagram generated and saved to {output_path} ({duration:.2f}s)")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating architecture diagram: {str(e)}")
            return None


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
    
    parser = argparse.ArgumentParser(description="Generate supplementary documentation")
    parser.add_argument("input", help="Path to input file or directory")
    parser.add_argument("--output-dir", "-o", default="supplementary-docs", help="Output directory")
    parser.add_argument("--content-type", "-t", choices=["faq", "tutorial", "diagram", "all"], 
                       default="faq", help="Type of content to generate")
    parser.add_argument("--topic", help="Topic for tutorial (required for tutorials)")
    parser.add_argument("--audience", default="intermediate", 
                       choices=["beginner", "intermediate", "advanced"], 
                       help="Target audience level for tutorials")
    parser.add_argument("--model", default=None, help="LLM model to use")
    
    args = parser.parse_args()
    
    try:
        # Initialize OpenAI client
        client = OpenAIClient()
        
        # Initialize content generator
        generator = ContentGenerator(
            llm_client=client,
            output_dir=args.output_dir,
            model=args.model
        )
        
        input_path = Path(args.input)
        
        if not input_path.exists():
            print(f"Error: {input_path} does not exist")
            sys.exit(1)
            
        if args.content_type == "faq" or args.content_type == "all":
            output_path = generator.generate_faq(input_path)
            if output_path:
                print(f"FAQ generated: {output_path}")
                
        if args.content_type == "tutorial" or args.content_type == "all":
            if not args.topic and args.content_type == "tutorial":
                print("Error: --topic is required for tutorials")
                sys.exit(1)
                
            topic = args.topic or f"Using {input_path.stem}"
            output_path = generator.generate_tutorial(
                input_path,
                tutorial_topic=topic,
                audience_level=args.audience
            )
            if output_path:
                print(f"Tutorial generated: {output_path}")
                
        if args.content_type == "diagram" or args.content_type == "all":
            output_path = generator.generate_file_architecture_diagram(input_path)
            if output_path:
                print(f"Architecture diagram generated: {output_path}")
                
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1) 