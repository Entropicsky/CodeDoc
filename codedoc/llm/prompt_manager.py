"""
Prompt template management for LLM interactions.

This module provides a system for creating, managing, and rendering prompt templates
with variable substitution and consistent formatting.
"""

import os
import json
import yaml
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Set

import jinja2

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manager for LLM prompt templates with variable substitution.
    """
    
    def __init__(self, templates_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the prompt manager.
        
        Args:
            templates_dir: Optional path to a directory containing template files.
                           If provided, templates will be loaded from this directory.
                           If not provided, default templates will be loaded.
        """
        self.templates = {}
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader("."),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Load templates if directory is provided
        if templates_dir:
            self._load_templates_from_directory(templates_dir)
        else:
            # Load default templates if no directory is provided
            self._load_default_templates()
    
    def _load_default_templates(self) -> None:
        """Load default templates for code enhancement and FAQ generation."""
        # Add default templates
        self.templates["code_enhancement"] = """
SYSTEM: You are an expert software documentation engineer. Your task is to enhance the documentation and comments in a code file. Follow these guidelines:
1. Keep all functional code unchanged.
2. Improve docstrings and comments to be more descriptive and helpful.
3. Follow the existing documentation style if present.
4. Add parameter descriptions and return type information if missing.
5. Document classes, methods, and functions appropriately.
6. Add comments for complex logic and explain why certain approaches were taken.
7. Document potential edge cases.
8. DO NOT add any Markdown or summary text at the end of the file - if you want to add summary notes, use proper code comments for the language
9. Ensure all comments use the correct syntax for the programming language (e.g., # for Python, // for JavaScript, /* */ for multi-line comments in C-like languages)
===
USER: Please enhance the documentation in the following code file:

{{ file_path }}

Code content:
{{ content }}

Return the fully enhanced file with improved documentation. DO NOT change any functional code, only add or enhance comments and docstrings. If you want to include summary notes or key enhancement points, make sure they are formatted as proper code comments using the correct syntax for this programming language. DO NOT add any Markdown or raw text at the end of the file.
"""
    
        self.templates["faq_generation"] = """
SYSTEM: You are an expert technical writer who specializes in creating clear, concise FAQs for software components. Your task is to generate a comprehensive FAQ for a code module.
===
USER: Please create a FAQ document for the following code:

{{ file_path }}

Code content:
{{ content }}

Generate 5-10 frequently asked questions and their answers that would be helpful for developers working with this code.
"""

        self.templates["pattern_recognition"] = """
SYSTEM: You are an expert software architect specializing in code pattern recognition. Your task is to analyze a code file and identify common design patterns, architectural approaches, and coding patterns used.

Focus on recognizing and explaining:
1. Design patterns (e.g., Factory, Singleton, Observer, etc.)
2. Architectural patterns (e.g., MVC, MVVM, layered architecture)
3. Code organization patterns (e.g., separation of concerns, dependency injection)
4. Common idioms for the programming language
5. API design patterns
6. Concurrency patterns if present
7. Error handling strategies

For each pattern identified, explain:
- What the pattern is
- Where it's used in the code
- Why this pattern is appropriate (or not) for this use case
- How the implementation could be improved if applicable
===
USER: Please analyze the following code file and identify design patterns and architectural approaches used:

File path: {{ file_path }}

Code content:
{{ content }}

Return a structured analysis of the patterns used in this code. Focus on architectural and design patterns, but also include language-specific patterns where relevant.
"""

        self.templates["complexity_analysis"] = """
SYSTEM: You are an expert software engineer specializing in code complexity analysis. Your task is to analyze a code file and provide insights on its complexity and quality characteristics.

Focus on analyzing:
1. Cyclomatic complexity - identify complex functions and methods
2. Cognitive complexity - areas that are difficult to understand
3. Code smell detection - identify anti-patterns and potential issues
4. Maintainability challenges - factors that make code difficult to maintain
5. Testability concerns - aspects that make the code difficult to test
6. Performance considerations - potential bottlenecks or inefficient algorithms
7. Security implications - potential security vulnerabilities

For each area of concern, provide:
- Specific locations in the code
- Explanation of the issue
- Severity level (low, medium, high)
- Suggestions for improvement
===
USER: Please analyze the complexity of the following code file:

File path: {{ file_path }}

Code content:
{{ content }}

Provide a detailed complexity analysis including cyclomatic complexity, cognitive load, maintainability concerns, and suggestions for improvement. Be specific about where complex sections are located and explain why they are complex.
"""

        logger.debug("Loaded default templates")
        
    def _load_templates_from_directory(self, directory: Union[str, Path]) -> None:
        """
        Load templates from a directory.
        
        Args:
            directory: Path to directory containing template files.
        """
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Templates directory not found: {directory}")
            return
        
        # Load .txt files (plain text templates)
        for file_path in directory.glob("*.txt"):
            template_name = file_path.stem
            with open(file_path, "r") as f:
                content = f.read()
                self.templates[template_name] = content
                logger.debug(f"Loaded template: {template_name}")
                
        # Load .yaml files (YAML templates with system/user structure)
        for file_path in directory.glob("*.yaml"):
            template_name = file_path.stem
            try:
                with open(file_path, "r") as f:
                    yaml_content = yaml.safe_load(f)
                    
                # Check if the YAML has system and user fields
                if "system" in yaml_content and "user" in yaml_content:
                    # Convert to the expected format with === separator
                    content = f"SYSTEM: {yaml_content['system']}\n===\nUSER: {yaml_content['user']}"
                    self.templates[template_name] = content
                    logger.debug(f"Loaded YAML template: {template_name}")
            except Exception as e:
                logger.error(f"Error loading YAML template {file_path}: {str(e)}")
    
    def render_template(self, name: str, variables: Dict[str, Any]) -> str:
        """
        Render a template with the provided variables.
        
        Args:
            name: Name of the template
            variables: Dictionary of variable values
            
        Returns:
            Rendered template string
            
        Raises:
            ValueError: If template with given name is not found
        """
        if name not in self.templates:
            raise ValueError(f"Template '{name}' not found")
        
        template_str = self.templates[name]
        template = self.jinja_env.from_string(template_str)
        return template.render(**variables)
    
    def render_with_system(self, name: str, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        Render a template with system and user parts.
        
        Args:
            name: Name of the template
            variables: Dictionary of variable values
            
        Returns:
            Dictionary with 'system' and 'user' keys containing rendered templates
            
        Raises:
            ValueError: If template with given name is not found or missing system/user parts
        """
        if name not in self.templates:
            raise ValueError(f"Template '{name}' not found")
        
        template_str = self.templates[name]
        
        # Split template into system and user parts
        parts = re.split(r'\n===\n', template_str, maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"Template '{name}' does not have valid system/user split (use '==='')")
        
        system_part, user_part = parts
        
        # Remove "SYSTEM:" and "USER:" prefixes if present
        system_part = re.sub(r'^SYSTEM:\s*', '', system_part.strip())
        user_part = re.sub(r'^USER:\s*', '', user_part.strip())
        
        # Render both parts
        system_template = self.jinja_env.from_string(system_part)
        user_template = self.jinja_env.from_string(user_part)
        
        return {
            "system": system_template.render(**variables).strip(),
            "user": user_template.render(**variables).strip()
        }


def create_default_manager() -> PromptManager:
    """
    Create a PromptManager with default templates.
    
    Returns:
        PromptManager with preloaded default templates
    """
    manager = PromptManager()
    
    # Default templates are already loaded in the constructor
    logger.info("Created default prompt manager with standard templates")
    return manager 