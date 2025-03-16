"""
Tests for the prompt template manager.
"""

import os
import tempfile
import pytest
from pathlib import Path

from codedoc.llm.prompt_manager import PromptManager, create_default_manager


class TestPromptManager:
    """Tests for the PromptManager class."""
    
    def test_init_with_default_templates(self):
        """Test initialization with default templates."""
        manager = PromptManager()
        
        # Verify default templates are loaded
        assert manager.templates is not None
        assert len(manager.templates) > 0
        
        # Check for some expected default templates
        assert "code_enhancement" in manager.templates
        assert "faq_generation" in manager.templates
        
    def test_init_with_custom_templates(self):
        """Test initialization with custom templates directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a custom template
            templates_dir = Path(tmp_dir) / "templates"
            templates_dir.mkdir()
            
            # Create a custom template file
            template_file = templates_dir / "custom_template.txt"
            with open(template_file, "w") as f:
                f.write("User: {{ name }}")
            
            # Initialize with custom templates directory
            manager = PromptManager(templates_dir=templates_dir)
            
            # Verify custom template is loaded
            assert "custom_template" in manager.templates
            assert manager.templates["custom_template"] == "User: {{ name }}"
    
    def test_render_template(self):
        """Test rendering a template with variables."""
        manager = PromptManager()
        
        # Add a simple template
        manager.templates["test_template"] = "Hello, {{ name }}!"
        
        # Render the template
        result = manager.render_template("test_template", {"name": "World"})
        
        assert result == "Hello, World!"
    
    def test_render_with_system(self):
        """Test rendering a template with system and user parts."""
        manager = PromptManager()
        
        # Add a template with system and user parts
        manager.templates["test_with_system"] = """
SYSTEM: You are helping {{ role }}.
===
USER: I need help with {{ task }}.
"""
        
        # Render the template
        result = manager.render_with_system("test_with_system", {
            "role": "a developer",
            "task": "testing"
        })
        
        assert "system" in result
        assert "user" in result
        assert result["system"] == "You are helping a developer."
        assert result["user"] == "I need help with testing."
    
    def test_render_missing_template(self):
        """Test error when rendering a missing template."""
        manager = PromptManager()
        
        with pytest.raises(ValueError) as exc_info:
            manager.render_template("non_existent_template", {})
        
        assert "not found" in str(exc_info.value)
    
    def test_render_with_missing_variables(self):
        """Test rendering with missing template variables."""
        manager = PromptManager()
        
        # Add a template with variables
        manager.templates["test_template"] = "Hello, {{ name }}!"
        
        # Render without the required variable
        # This should not raise an error as Jinja2 treats missing variables as empty strings
        result = manager.render_template("test_template", {})
        
        assert result == "Hello, !"
    
    def test_create_default_manager(self):
        """Test the create_default_manager function."""
        manager = create_default_manager()
        
        # Verify it's a PromptManager
        assert isinstance(manager, PromptManager)
        
        # Check for some expected default templates
        assert "code_enhancement" in manager.templates
        assert "faq_generation" in manager.templates 