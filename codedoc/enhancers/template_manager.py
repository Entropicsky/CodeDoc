#!/usr/bin/env python3
"""
Template Manager for CodeDoc documentation.

This module provides functionality to manage and render templates for
LLM-optimized documentation.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from codedoc.core.entities import (
    Entity, ModuleEntity, ClassEntity, FunctionEntity, VariableEntity
)


class TemplateManager:
    """
    Manages documentation templates for different entity types.
    
    This class loads, customizes, and renders templates for generating
    LLM-optimized documentation. It supports both file-based templates
    and embedded templates.
    """
    
    # Default embedded templates
    DEFAULT_TEMPLATES = {
        "module": """# Module `{{ entity.name }}`

{% if frontmatter %}---
type: module
name: {{ entity.name }}
path: {{ entity.file_path }}
{% if last_modified %}last_modified: {{ last_modified }}{% endif %}
{% if version %}version: {{ version }}{% endif %}
{% if stability %}stability: {{ stability }}{% endif %}
{% if tags %}tags: {{ tags }}{% endif %}
---{% endif %}

{% if entity.docstring %}{{ entity.docstring }}{% endif %}

{% if include_metadata %}
## Metadata

- **Path**: `{{ entity.file_path }}`
{% if last_modified %}- **Last Modified**: {{ last_modified }}{% endif %}
{% if version %}- **Version**: {{ version }}{% endif %}
{% if stability %}- **Stability**: {{ stability }}{% endif %}
{% endif %}

{% if include_imports and entity.imports %}
## Imports

```python
{% for imp in entity.imports %}{{ imp }}
{% endfor %}```
{% endif %}

{% if include_variables and entity.variables %}
## Variables

{% for var in entity.variables %}
### `{{ var.name }}` {% if var.type %}({{ var.type }}){% endif %}

{% if var.docstring %}{{ var.docstring }}{% endif %}
{% endfor %}
{% endif %}

{% if include_functions and entity.functions %}
## Functions

{% for func in entity.functions %}
### [`{{ func.name }}`]({{ func.name }}.md)

```python
{{ func.signature }}
```

{% if func.docstring %}{{ func.docstring }}{% endif %}
{% endfor %}
{% endif %}

{% if include_classes and entity.classes %}
## Classes

{% for class in entity.classes %}
### [`{{ class.name }}`]({{ class.name }}.md)

{% if class.base_classes %}Inherits from: {% for base in class.base_classes %}`{{ base }}`{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}

{% if class.docstring %}{{ class.docstring }}{% endif %}

#### Methods

{% for method in class.methods %}
- `{{ method.signature }}`
{% endfor %}
{% endfor %}
{% endif %}

{% if include_relationships and relationships %}
## Relationships

{% if relationships.imports or relationships.imported_by %}
### Dependencies
{% if relationships.imports %}- **Imports**: {% for imp in relationships.imports %}{{ imp }}{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
{% if relationships.imported_by %}- **Imported By**: {% for imp in relationships.imported_by %}{{ imp }}{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
{% endif %}

{% if relationships.class_hierarchy and include_diagrams %}
### Class Hierarchy
```mermaid
classDiagram
{% for rel in relationships.class_hierarchy %}    {{ rel }}
{% endfor %}```
{% endif %}

{% if relationships.function_calls %}
### Function Calls
{% for func, calls in relationships.function_calls.items() %}- **Function `{{ func }}`**:
  {% if calls.calls %}- Calls: {% for call in calls.calls %}`{{ call }}`{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
  {% if calls.called_by %}- Called By: {% for call in calls.called_by %}`{{ call }}`{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
{% endfor %}
{% endif %}
{% endif %}

{% if include_runtime and runtime_behavior %}
## Runtime Behavior

{% if runtime_behavior.error_handling %}
### Error Handling
{{ runtime_behavior.error_handling }}
{% endif %}

{% if runtime_behavior.performance %}
### Performance Characteristics
{{ runtime_behavior.performance }}
{% endif %}

{% if runtime_behavior.state_transitions and include_diagrams %}
### State Transitions
```mermaid
stateDiagram-v2
{% for transition in runtime_behavior.state_transitions %}    {{ transition }}
{% endfor %}```
{% endif %}
{% endif %}
""",

        "class": """# Class `{{ entity.name }}`

{% if frontmatter %}---
type: class
name: {{ entity.name }}
module: {{ entity.module_name }}
path: {{ entity.file_path }}
{% if last_modified %}last_modified: {{ last_modified }}{% endif %}
{% if version %}version: {{ version }}{% endif %}
{% if stability %}stability: {{ stability }}{% endif %}
{% if tags %}tags: {{ tags }}{% endif %}
---{% endif %}

{% if entity.base_classes %}Inherits from: {% for base in entity.base_classes %}[`{{ base }}`]({{ base }}.md){% if not loop.last %}, {% endif %}{% endfor %}{% endif %}

{% if entity.docstring %}{{ entity.docstring }}{% endif %}

{% if include_metadata %}
## Metadata

- **Module**: [`{{ entity.module_name }}`]({{ entity.module_path }})
- **Path**: `{{ entity.file_path }}:{{ entity.line_number }}`
{% if last_modified %}- **Last Modified**: {{ last_modified }}{% endif %}
{% if version %}- **Version**: {{ version }}{% endif %}
{% if stability %}- **Stability**: {{ stability }}{% endif %}
{% endif %}

{% if include_implementation_notes and implementation_notes %}
## Implementation Notes

{{ implementation_notes }}
{% endif %}

{% if include_variables and entity.class_variables %}
## Class Variables

{% for var in entity.class_variables %}
### `{{ var.name }}` {% if var.type %}({{ var.type }}){% endif %}

{% if var.docstring %}{{ var.docstring }}{% endif %}
{% endfor %}
{% endif %}

{% if include_methods and entity.methods %}
## Methods

{% for method in entity.methods %}
### `{{ method.name }}`

```python
{{ method.signature }}
```

{% if method.docstring %}{{ method.docstring }}{% endif %}

{% if method.parameters %}
#### Parameters

{% for param in method.parameters %}
- `{{ param.name }}`: {% if param.type %}`{{ param.type }}`{% endif %}{% if param.description %}: {{ param.description }}{% endif %}
{% endfor %}
{% endif %}

{% if method.returns and method.returns.type %}
#### Returns

`{{ method.returns.type }}`{% if method.returns.description %}: {{ method.returns.description }}{% endif %}
{% endif %}

{% if method.raises %}
#### Raises

{% for exc in method.raises %}
- `{{ exc.type }}`{% if exc.description %}: {{ exc.description }}{% endif %}
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}

{% if include_relationships and relationships %}
## Relationships

{% if relationships.inherits_from or relationships.inherited_by %}
### Inheritance
{% if relationships.inherits_from %}- **Inherits From**: {% for cls in relationships.inherits_from %}[`{{ cls }}`]({{ cls }}.md){% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
{% if relationships.inherited_by %}- **Inherited By**: {% for cls in relationships.inherited_by %}[`{{ cls }}`]({{ cls }}.md){% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
{% endif %}

{% if relationships.class_hierarchy and include_diagrams %}
### Class Hierarchy
```mermaid
classDiagram
{% for rel in relationships.class_hierarchy %}    {{ rel }}
{% endfor %}```
{% endif %}

{% if relationships.uses or relationships.used_by %}
### Usage
{% if relationships.uses %}- **Uses**: {% for use in relationships.uses %}[`{{ use }}`]({{ use.replace('.', '/') }}.md){% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
{% if relationships.used_by %}- **Used By**: {% for use in relationships.used_by %}[`{{ use }}`]({{ use.replace('.', '/') }}.md){% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
{% endif %}
{% endif %}

{% if include_examples and examples %}
## Examples

```python
{{ examples }}
```
{% endif %}

{% if include_runtime and runtime_behavior %}
## Runtime Behavior

{% if runtime_behavior.error_handling %}
### Error Handling
{{ runtime_behavior.error_handling }}
{% endif %}

{% if runtime_behavior.performance %}
### Performance Characteristics
{{ runtime_behavior.performance }}
{% endif %}

{% if runtime_behavior.state_transitions and include_diagrams %}
### State Transitions
```mermaid
stateDiagram-v2
{% for transition in runtime_behavior.state_transitions %}    {{ transition }}
{% endfor %}```
{% endif %}
{% endif %}
""",

        "function": """# Function `{{ entity.name }}`

{% if frontmatter %}---
type: function
name: {{ entity.name }}
module: {{ entity.module_name }}
path: {{ entity.file_path }}
{% if last_modified %}last_modified: {{ last_modified }}{% endif %}
{% if version %}version: {{ version }}{% endif %}
{% if stability %}stability: {{ stability }}{% endif %}
{% if tags %}tags: {{ tags }}{% endif %}
---{% endif %}

## Signature

```python
{{ entity.signature }}
```

{% if entity.docstring %}{{ entity.docstring }}{% endif %}

{% if include_metadata %}
## Metadata

- **Module**: [`{{ entity.module_name }}`]({{ entity.module_path }})
- **Path**: `{{ entity.file_path }}:{{ entity.line_number }}`
{% if last_modified %}- **Last Modified**: {{ last_modified }}{% endif %}
{% if version %}- **Version**: {{ version }}{% endif %}
{% if stability %}- **Stability**: {{ stability }}{% endif %}
{% endif %}

{% if include_implementation_notes and implementation_notes %}
## Implementation Notes

{{ implementation_notes }}
{% endif %}

{% if entity.parameters %}
## Parameters

{% for param in entity.parameters %}
- `{{ param.name }}`: {% if param.type %}`{{ param.type }}`{% endif %}{% if param.description %}: {{ param.description }}{% endif %}
{% endfor %}
{% endif %}

{% if entity.returns and entity.returns.type %}
## Returns

`{{ entity.returns.type }}`{% if entity.returns.description %}: {{ entity.returns.description }}{% endif %}
{% endif %}

{% if entity.raises %}
## Raises

{% for exc in entity.raises %}
- `{{ exc.type }}`{% if exc.description %}: {{ exc.description }}{% endif %}
{% endfor %}
{% endif %}

{% if include_relationships and relationships %}
## Relationships

{% if relationships.function_calls %}
### Function Calls
{% if relationships.function_calls.calls %}- **Calls**: {% for call in relationships.function_calls.calls %}[`{{ call }}`]({{ call.replace('.', '/') }}.md){% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
{% if relationships.function_calls.called_by %}- **Called By**: {% for call in relationships.function_calls.called_by %}[`{{ call }}`]({{ call.replace('.', '/') }}.md){% if not loop.last %}, {% endif %}{% endfor %}{% endif %}
{% endif %}

{% if relationships.function_calls and include_diagrams %}
### Call Graph
```mermaid
flowchart TD
{% for rel in relationships.call_graph %}    {{ rel }}
{% endfor %}```
{% endif %}
{% endif %}

{% if include_examples and examples %}
## Examples

```python
{{ examples }}
```
{% endif %}

{% if include_runtime and runtime_behavior %}
## Runtime Behavior

{% if runtime_behavior.error_handling %}
### Error Handling
{{ runtime_behavior.error_handling }}
{% endif %}

{% if runtime_behavior.performance %}
### Performance Characteristics
{{ runtime_behavior.performance }}
{% endif %}

{% if runtime_behavior.async_behavior %}
### Asynchronous Behavior
{{ runtime_behavior.async_behavior }}
{% endif %}
{% endif %}
""",

        "variable": """# Variable `{{ entity.name }}`

{% if frontmatter %}---
type: variable
name: {{ entity.name }}
module: {{ entity.module_name }}
path: {{ entity.file_path }}
{% if last_modified %}last_modified: {{ last_modified }}{% endif %}
{% if version %}version: {{ version }}{% endif %}
{% if stability %}stability: {{ stability }}{% endif %}
{% if tags %}tags: {{ tags }}{% endif %}
---{% endif %}

{% if entity.type %}**Type**: `{{ entity.type }}`{% endif %}

{% if entity.docstring %}{{ entity.docstring }}{% endif %}

{% if include_metadata %}
## Metadata

- **Module**: [`{{ entity.module_name }}`]({{ entity.module_path }})
- **Path**: `{{ entity.file_path }}:{{ entity.line_number }}`
{% if last_modified %}- **Last Modified**: {{ last_modified }}{% endif %}
{% if version %}- **Version**: {{ version }}{% endif %}
{% if stability %}- **Stability**: {{ stability }}{% endif %}
{% endif %}

{% if include_implementation_notes and implementation_notes %}
## Implementation Notes

{{ implementation_notes }}
{% endif %}

{% if include_value and entity.value %}
## Value

```python
{{ entity.value }}
```
{% endif %}

{% if include_relationships and relationships %}
## Relationships

{% if relationships.used_by %}
### Usage
- **Used By**: {% for use in relationships.used_by %}[`{{ use }}`]({{ use.replace('.', '/') }}.md){% if not loop.last %}, {% endif %}{% endfor %}
{% endif %}
{% endif %}
""",

        "index": """# {{ title }}

{% if frontmatter %}---
type: index
title: {{ title }}
{% if version %}version: {{ version }}{% endif %}
{% if last_modified %}last_modified: {{ last_modified }}{% endif %}
---{% endif %}

## Table of Contents

{% if modules %}
### Modules

{% for module in modules %}
- [`{{ module.name }}`]({{ module.doc_path }})
{% endfor %}
{% endif %}

{% if classes %}
### Classes

{% for class in classes %}
- [`{{ class.name }}`]({{ class.doc_path }})
{% endfor %}
{% endif %}

{% if functions %}
### Functions

{% for function in functions %}
- [`{{ function.name }}`]({{ function.doc_path }})
{% endfor %}
{% endif %}
""",

        "relationship": """# Relationships for {{ entity_type }} `{{ entity_name }}`

{% if frontmatter %}---
type: relationship
entity_type: {{ entity_type }}
entity_name: {{ entity_name }}
{% if last_modified %}last_modified: {{ last_modified }}{% endif %}
---{% endif %}

{% if imports or imported_by %}
## Module Dependencies

{% if imports %}
### Imports

{% for imp in imports %}
- [`{{ imp }}`]({{ imp.replace('.', '/') }}.md)
{% endfor %}
{% endif %}

{% if imported_by %}
### Imported By

{% for imp in imported_by %}
- [`{{ imp }}`]({{ imp.replace('.', '/') }}.md)
{% endfor %}
{% endif %}
{% endif %}

{% if inherits_from or inherited_by %}
## Class Inheritance

{% if inherits_from %}
### Inherits From

{% for cls in inherits_from %}
- [`{{ cls }}`]({{ cls }}.md)
{% endfor %}
{% endif %}

{% if inherited_by %}
### Inherited By

{% for cls in inherited_by %}
- [`{{ cls }}`]({{ cls }}.md)
{% endfor %}
{% endif %}
{% endif %}

{% if calls or called_by %}
## Function Calls

{% if calls %}
### Calls

{% for call in calls %}
- [`{{ call }}`]({{ call.replace('.', '/') }}.md)
{% endfor %}
{% endif %}

{% if called_by %}
### Called By

{% for call in called_by %}
- [`{{ call }}`]({{ call.replace('.', '/') }}.md)
{% endfor %}
{% endif %}
{% endif %}

{% if include_diagrams %}
## Diagrams

{% if class_hierarchy %}
### Class Hierarchy

```mermaid
classDiagram
{% for rel in class_hierarchy %}    {{ rel }}
{% endfor %}```
{% endif %}

{% if call_graph %}
### Call Graph

```mermaid
flowchart TD
{% for rel in call_graph %}    {{ rel }}
{% endfor %}```
{% endif %}
{% endif %}
"""
    }

    def __init__(self, template_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the template manager.
        
        Args:
            template_dir: Optional directory containing custom templates.
                          If None, uses the embedded default templates.
        """
        self.template_dir = Path(template_dir) if template_dir else None
        self.env = None
        self.templates: Dict[str, Template] = {}
        
        if self.template_dir and self.template_dir.exists():
            # Load templates from files
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
            self._load_templates_from_dir()
        else:
            # Use default embedded templates
            self.env = Environment(autoescape=select_autoescape(['html', 'xml']))
            self._load_default_templates()

    def _load_templates_from_dir(self):
        """Load templates from the template directory."""
        if not self.template_dir or not self.env:
            return
        
        # Look for template files
        template_files = list(self.template_dir.glob('*.md')) + list(self.template_dir.glob('*.j2'))
        
        for template_file in template_files:
            name = template_file.stem
            try:
                self.templates[name] = self.env.get_template(template_file.name)
            except Exception as e:
                print(f"Error loading template {template_file}: {e}")

    def _load_default_templates(self):
        """Load the default embedded templates."""
        for name, template_str in self.DEFAULT_TEMPLATES.items():
            try:
                self.templates[name] = self.env.from_string(template_str)
            except Exception as e:
                print(f"Error loading default template {name}: {e}")

    def get_template(self, entity_type: str) -> Optional[Template]:
        """
        Get a template for the specified entity type.
        
        Args:
            entity_type: Type of entity ('module', 'class', 'function', 'variable')
            
        Returns:
            The template or None if not found
        """
        return self.templates.get(entity_type.lower())

    def get_template_for_entity(self, entity: Entity) -> Optional[Template]:
        """
        Get the appropriate template for an entity.
        
        Args:
            entity: The entity to get a template for
            
        Returns:
            The template or None if not found
        """
        if isinstance(entity, ModuleEntity):
            return self.get_template('module')
        elif isinstance(entity, ClassEntity):
            return self.get_template('class')
        elif isinstance(entity, FunctionEntity):
            return self.get_template('function')
        elif isinstance(entity, VariableEntity):
            return self.get_template('variable')
        return None

    def render_template(self, 
                       template_name: str, 
                       context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template to render
            context: Context variables for the template
            
        Returns:
            The rendered template as a string
            
        Raises:
            ValueError: If the template is not found
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        return template.render(**context)

    def render_for_entity(self, 
                         entity: Entity, 
                         context: Optional[Dict[str, Any]] = None) -> str:
        """
        Render documentation for an entity.
        
        Args:
            entity: The entity to render documentation for
            context: Additional context variables for the template
            
        Returns:
            The rendered documentation as a string
            
        Raises:
            ValueError: If no template is found for the entity type
        """
        template = self.get_template_for_entity(entity)
        if not template:
            raise ValueError(f"No template found for entity type: {type(entity).__name__}")
        
        # Create context with the entity
        ctx = {'entity': entity}
        
        # Add additional context if provided
        if context:
            ctx.update(context)
        
        return template.render(**ctx)

    def save_templates_to_dir(self, output_dir: Union[str, Path]):
        """
        Save the default templates to a directory.
        
        Args:
            output_dir: Directory to save templates to
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for name, template_str in self.DEFAULT_TEMPLATES.items():
            template_path = output_path / f"{name}_template.md"
            with open(template_path, 'w') as f:
                f.write(template_str)


if __name__ == "__main__":
    # Example usage
    template_manager = TemplateManager()
    
    # Save default templates to the templates directory
    templates_dir = Path(__file__).parent.parent / "templates"
    template_manager.save_templates_to_dir(templates_dir)
    
    print(f"Templates saved to {templates_dir}") 