#!/usr/bin/env python3
"""
Context Generator for CodeDoc.

This module provides functionality to generate contextual information
about code entities to enhance documentation for LLM comprehension.
"""

import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple, Union
import logging

from codedoc.core.entities import (
    Entity, ModuleEntity, ClassEntity, FunctionEntity, VariableEntity, ImportEntity
)
from codedoc.utils.text_formatter import TextFormatter

logger = logging.getLogger(__name__)


class ContextGenerator:
    """
    Generates contextual information about code entities.
    
    This class analyzes code entities and generates human-readable
    contextual information that helps LLMs and developers understand 
    the purpose, behavior, and usage patterns of the code.
    
    The contextual information includes:
    - Implementation notes
    - Runtime behavior descriptions
    - Usage patterns and examples
    - Complexity analysis
    """
    
    def __init__(self, relationship_mapper=None):
        """
        Initialize the context generator.
        
        Args:
            relationship_mapper: The relationship mapper to use for entity relationships
        """
        self.relationship_mapper = relationship_mapper
        self.entities = {}
        if relationship_mapper:
            self.entities = relationship_mapper.entities
        
        # Map of entity IDs to implementation notes
        self.implementation_notes: Dict[str, str] = {}
        
        # Map of entity IDs to runtime behavior descriptions
        self.runtime_behavior: Dict[str, Dict[str, Any]] = {}
        
        # Map of entity IDs to examples
        self.examples: Dict[str, str] = {}

    def generate_context(self, entity: Entity) -> Dict[str, Any]:
        """
        Generate context information for an entity.
        
        Args:
            entity: The entity to generate context for
            
        Returns:
            A dictionary containing context information
        """
        entity_id = self._get_entity_id(entity)
        
        # Generate the different types of context
        impl_notes = self.generate_implementation_notes(entity)
        runtime = self.generate_runtime_behavior(entity)
        examples = self.generate_examples(entity)
        
        # Cache the results
        if impl_notes:
            self.implementation_notes[entity_id] = impl_notes
        
        if runtime:
            self.runtime_behavior[entity_id] = runtime
            
        if examples:
            self.examples[entity_id] = examples
        
        # Return the complete context
        return {
            'implementation_notes': impl_notes,
            'runtime_behavior': runtime,
            'examples': examples
        }

    def _get_entity_id(self, entity: Entity) -> str:
        """
        Get a unique identifier for an entity.
        
        Args:
            entity: The entity to get an ID for
            
        Returns:
            A unique identifier string
        """
        if isinstance(entity, ModuleEntity):
            return entity.name
        elif hasattr(entity, 'module_name') and entity.module_name:
            if isinstance(entity, ClassEntity):
                return f"{entity.module_name}.{entity.name}"
            elif isinstance(entity, FunctionEntity):
                if entity.is_method and hasattr(entity, 'parent_class') and entity.parent_class:
                    return f"{entity.module_name}.{entity.parent_class}.{entity.name}"
                return f"{entity.module_name}.{entity.name}"
            elif isinstance(entity, VariableEntity):
                return f"{entity.module_name}.{entity.name}"
        
        # Default case - use type and name
        return f"{type(entity).__name__}:{entity.name}"

    def generate_implementation_notes(self, entity: Entity) -> str:
        """Generate implementation notes for a code entity.

        Args:
            entity: The entity to generate notes for.

        Returns:
            Implementation notes as a string.
        """
        notes = ""
        
        try:
            if isinstance(entity, ModuleEntity):
                notes = self._get_module_implementation_notes(entity)
            elif isinstance(entity, ClassEntity):
                notes = self._get_class_implementation_notes(entity)
            elif isinstance(entity, FunctionEntity):
                notes = self._get_function_implementation_notes(entity)
            elif isinstance(entity, VariableEntity):
                notes = self._get_variable_implementation_notes(entity)
        except Exception as e:
            logger.error(f"Error generating implementation notes for {entity.name}: {str(e)}")
            notes = "No implementation notes available due to an error."
        
        return notes

    def _get_module_implementation_notes(self, entity: ModuleEntity) -> str:
        """Generate implementation notes for a module.

        Args:
            entity: The module entity.

        Returns:
            Implementation notes as a string.
        """
        notes = []

        # External dependencies
        external_imports = self._get_external_dependencies(entity)
        if external_imports:
            notes.append(f"External Dependencies: {', '.join(external_imports)}")

        # Internal dependencies
        internal_imports = self._get_internal_dependencies(entity)
        if internal_imports:
            notes.append(f"Internal Dependencies: {', '.join(internal_imports)}")

        # Classes
        classes = self._get_classes(entity)
        if classes:
            notes.append(f"Classes: {', '.join(classes)}")

        # Functions
        functions = self._get_functions(entity)
        if functions:
            notes.append(f"Functions: {', '.join(functions)}")

        # Variables
        variables = self._get_variables(entity)
        if variables:
            notes.append(f"Variables: {', '.join(variables)}")

        # Return formatted notes
        formatted_notes = "\n".join(notes)
        return TextFormatter.format_module_implementation_notes(formatted_notes)

    def _get_class_implementation_notes(self, entity: ClassEntity) -> str:
        """Generate implementation notes for a class.

        Args:
            entity: The class entity.

        Returns:
            Implementation notes as a string.
        """
        notes = []

        # Base classes
        if entity.bases:
            notes.append(f"Base Classes: {', '.join(entity.bases)}")

        # Methods
        methods = self._get_methods(entity)
        if methods:
            notes.append(f"Methods: {', '.join(methods)}")

        # Properties
        properties = self._get_properties(entity)
        if properties:
            notes.append(f"Properties: {', '.join(properties)}")

        # Class variables
        class_vars = self._get_class_variables(entity)
        if class_vars:
            notes.append(f"Class Variables: {', '.join(class_vars)}")

        # Instance variables
        instance_vars = self._get_instance_variables(entity)
        if instance_vars:
            notes.append(f"Instance Variables: {', '.join(instance_vars)}")

        # Return formatted notes
        formatted_notes = "\n".join(notes)
        return TextFormatter.format_class_implementation_notes(formatted_notes)

    def _get_function_implementation_notes(self, entity: FunctionEntity) -> str:
        """Generate implementation notes for a function.

        Args:
            entity: The function entity.

        Returns:
            Implementation notes as a string.
        """
        notes = []

        # Function complexity
        complexity = self._get_function_complexity(entity)
        if complexity:
            notes.append(f"Complexity: {complexity}")

        # Function calls
        calls = self._get_function_calls(entity)
        if calls:
            notes.append(f"Function Calls: {', '.join(calls)}")

        # Return values
        return_vals = self._get_return_values(entity)
        if return_vals:
            notes.append(f"Return Values: {', '.join(return_vals)}")

        # Local variables
        local_vars = self._get_local_variables(entity)
        if local_vars:
            notes.append(f"Local Variables: {', '.join(local_vars)}")

        # Return formatted notes
        formatted_notes = "\n".join(notes)
        return TextFormatter.format_function_implementation_notes(formatted_notes)

    def _get_variable_implementation_notes(self, entity: VariableEntity) -> str:
        """Generate implementation notes for a variable.

        Args:
            entity: The variable entity.

        Returns:
            Implementation notes as a string.
        """
        notes = []

        # Variable type
        if entity.type_annotation:
            notes.append(f"Type: {entity.type_annotation}")

        # Variable value
        if entity.value:
            notes.append(f"Value: {entity.value}")

        # Return formatted notes
        formatted_notes = "\n".join(notes)
        return TextFormatter.format_variable_implementation_notes(formatted_notes)

    def generate_runtime_behavior(self, entity: Entity) -> Dict[str, Any]:
        """
        Generate runtime behavior information for an entity.
        
        Args:
            entity: The entity to analyze
            
        Returns:
            Dictionary of runtime behavior information
        """
        behavior: Dict[str, Any] = {}
        
        if isinstance(entity, ModuleEntity):
            behavior = self._generate_module_runtime_behavior(entity)
        elif isinstance(entity, ClassEntity):
            behavior = self._generate_class_runtime_behavior(entity)
        elif isinstance(entity, FunctionEntity):
            behavior = self._generate_function_runtime_behavior(entity)
        
        return behavior

    def _generate_module_runtime_behavior(self, entity: ModuleEntity) -> Dict[str, Any]:
        """
        Generate runtime behavior for a module.
        
        Args:
            entity: The module entity
            
        Returns:
            Dictionary of runtime behavior information
        """
        behavior = {}
        
        # Check for module-level code execution
        has_execution_code = False
        module_code = entity.code if hasattr(entity, 'code') else ""
        
        if module_code:
            # Look for code outside functions and classes
            lines = module_code.split('\n')
            in_def = False
            in_class = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('def '):
                    in_def = True
                elif stripped.startswith('class '):
                    in_class = True
                elif stripped == '':
                    continue
                elif in_def and re.match(r'^[^ \t]', line):
                    in_def = False
                elif in_class and re.match(r'^[^ \t]', line):
                    in_class = False
                elif not in_def and not in_class and not stripped.startswith('#') and not stripped.startswith('import ') and not stripped.startswith('from '):
                    has_execution_code = True
                    break
        
        if has_execution_code:
            behavior['initialization'] = "This module contains code that executes when the module is imported."
        
        # Check for common error handling patterns
        has_error_handling = False
        if module_code and ('try:' in module_code and 'except' in module_code):
            has_error_handling = True
        
        if has_error_handling:
            behavior['error_handling'] = "This module implements error handling using try-except blocks."
        
        return behavior

    def _generate_class_runtime_behavior(self, entity: ClassEntity) -> Dict[str, Any]:
        """
        Generate runtime behavior for a class.
        
        Args:
            entity: The class entity
            
        Returns:
            Dictionary of runtime behavior information
        """
        behavior = {}
        state_transitions = []
        
        # Check for lifecycle methods
        lifecycle_methods = [
            method for method in entity.methods
            if method.name in ('__init__', '__enter__', '__exit__', '__del__', 'close', 'shutdown', 'start', 'stop')
        ]
        
        if lifecycle_methods:
            # Create state transitions for lifecycle methods
            if any(method.name == '__init__' for method in lifecycle_methods):
                state_transitions.append("Initial --> Initialized : __init__")
            
            if any(method.name == '__enter__' for method in lifecycle_methods):
                state_transitions.append("Initialized --> Active : __enter__")
            
            if any(method.name == '__exit__' for method in lifecycle_methods):
                state_transitions.append("Active --> Closed : __exit__")
            
            if any(method.name == 'start' for method in lifecycle_methods):
                state_transitions.append("Initialized --> Running : start")
            
            if any(method.name == 'stop' for method in lifecycle_methods):
                state_transitions.append("Running --> Stopped : stop")
            
            if any(method.name == '__del__' for method in lifecycle_methods):
                state_transitions.append("* --> Destroyed : __del__")
            
            if any(method.name == 'close' for method in lifecycle_methods):
                state_transitions.append("* --> Closed : close")
            
            if any(method.name == 'shutdown' for method in lifecycle_methods):
                state_transitions.append("* --> Shutdown : shutdown")
        
        # Detect resource management
        resource_methods = [
            method for method in entity.methods
            if method.name in ('__enter__', '__exit__', 'close', 'release')
        ]
        
        if resource_methods:
            behavior['resource_management'] = "This class manages resources and should be used with context managers (with statement) when possible."
        
        # Check for thread safety
        thread_keywords = ['threading', 'Lock', 'RLock', 'Semaphore', 'Event', 'Condition']
        is_thread_safe = False
        
        for method in entity.methods:
            if hasattr(method, 'code') and method.code and any(keyword in method.code for keyword in thread_keywords):
                is_thread_safe = True
                break
        
        if is_thread_safe:
            behavior['thread_safety'] = "This class implements thread synchronization mechanisms and may be thread-safe."
        
        # Add state transitions if found
        if state_transitions:
            behavior['state_transitions'] = state_transitions
        
        # Check for error handling
        error_handling = []
        for method in entity.methods:
            if hasattr(method, 'code') and method.code and ('try:' in method.code and 'except' in method.code):
                error_handling.append(f"The {method.name} method implements error handling with try-except blocks.")
        
        if error_handling:
            behavior['error_handling'] = "\n".join(error_handling)
        
        return behavior

    def _generate_function_runtime_behavior(self, entity: FunctionEntity) -> Dict[str, str]:
        """
        Generate runtime behavior information for a function.
        
        Args:
            entity: The function entity
            
        Returns:
            Dictionary of runtime behavior information
        """
        behavior = {}
        
        # Check for error handling
        if hasattr(entity, 'code') and entity.code and ('try:' in entity.code and 'except' in entity.code):
            behavior['error_handling'] = "This function implements error handling using try-except blocks."
        
        # Check for asynchronous behavior
        is_async = (hasattr(entity, 'is_async') and entity.is_async) or (hasattr(entity, 'code') and entity.code and ('await ' in entity.code))
        if is_async:
            behavior['async_behavior'] = "This is an asynchronous function and should be awaited when called."
        
        # Estimate performance characteristics
        if hasattr(entity, 'code') and entity.code:
            performance = []
            
            # Check for potential performance issues
            if any(loop in entity.code for loop in ('for ', 'while ')):
                if any(nested in entity.code for nested in ('for ', 'while ')):
                    performance.append("Contains nested loops which may have O(n²) or higher complexity.")
                else:
                    performance.append("Contains loops which typically have O(n) complexity.")
            
            # Check for recursion
            if hasattr(entity, 'name') and entity.name and entity.name in entity.code:
                performance.append("This function appears to be recursive, which can affect stack usage.")
            
            # Check for IO operations
            io_indicators = ['open(', '.read(', '.write(', 'input(', 'print(', 'requests.', 'urlopen']
            if any(indicator in entity.code for indicator in io_indicators):
                performance.append("Performs I/O operations which may block execution.")
            
            if performance:
                behavior['performance'] = "\n".join(performance)
        
        return behavior

    def generate_examples(self, entity: Entity) -> str:
        """
        Generate usage examples for an entity.
        
        Args:
            entity: The entity to generate examples for
            
        Returns:
            Examples as a string
        """
        # For now, provide basic examples
        if isinstance(entity, ClassEntity):
            return self._generate_class_example(entity)
        elif isinstance(entity, FunctionEntity):
            return self._generate_function_example(entity)
        
        return ""

    def _generate_class_example(self, entity: ClassEntity) -> str:
        """Generate example code for a class.

        Args:
            entity: The class entity.

        Returns:
            Example code as a string.
        """
        example_lines = []
        
        # Import statement
        if hasattr(entity, 'module_name') and entity.module_name:
            example_lines.append(f"from {entity.module_name} import {entity.name}")
            example_lines.append("")
        
        # Find init parameters
        init_params = []
        init_method = None
        
        # Look for __init__ method
        if hasattr(entity, 'methods') and entity.methods:
            regular_methods = [method for method in entity.methods 
                              if hasattr(method, 'name') and not method.name.startswith('__')]
            
            init_methods = [method for method in entity.methods 
                           if hasattr(method, 'name') and method.name == '__init__']
            
            if init_methods:
                init_method = init_methods[0]
                
                # Get parameters for init
                if hasattr(init_method, 'parameters') and init_method.parameters:
                    # Skip self parameter
                    for param in init_method.parameters[1:]:
                        if hasattr(param, 'type') and param.type:
                            if 'str' in param.type.lower():
                                init_params.append(f'"{param.name}_value"')
                            elif 'int' in param.type.lower():
                                init_params.append('42')
                            elif 'float' in param.type.lower():
                                init_params.append('3.14')
                            elif 'bool' in param.type.lower():
                                init_params.append('True')
                            elif 'list' in param.type.lower():
                                init_params.append('[]')
                            elif 'dict' in param.type.lower():
                                init_params.append('{}')
                            else:
                                init_params.append(f'{param.name}_value')
                        else:
                            init_params.append(f'{param.name}_value')
        
        # Create instance
        example_lines.append(f"# Create an instance of {entity.name}")
        example_lines.append(f"instance = {entity.name}({', '.join(init_params)})")
        example_lines.append("")
        
        # Show usage of a couple methods if available
        if hasattr(entity, 'methods') and entity.methods:
            regular_methods = [method for method in entity.methods 
                              if hasattr(method, 'name') and not method.name.startswith('__')]
            
            # Show up to 2 regular methods
            for method in regular_methods[:2]:
                if hasattr(method, 'parameters') and method.parameters:
                    # Skip self parameter
                    method_params = []
                    for param in method.parameters:
                        if param.name == 'self':
                            continue
                        
                        if hasattr(param, 'type') and param.type:
                            if 'str' in param.type.lower():
                                method_params.append(f'"{param.name}_value"')
                            elif 'int' in param.type.lower():
                                method_params.append('42')
                            elif 'float' in param.type.lower():
                                method_params.append('3.14')
                            elif 'bool' in param.type.lower():
                                method_params.append('True')
                            elif 'list' in param.type.lower():
                                method_params.append('[]')
                            elif 'dict' in param.type.lower():
                                method_params.append('{}')
                            else:
                                method_params.append(f'{param.name}_value')
                        else:
                            method_params.append(f'{param.name}_value')
                    
                    example_lines.append(f"# Call {method.name} method")
                    example_lines.append(f"result = instance.{method.name}({', '.join(method_params)})")
                else:
                    example_lines.append(f"# Call {method.name} method")
                    example_lines.append(f"result = instance.{method.name}()")
                
                example_lines.append("")
        
        # Apply text formatting
        return TextFormatter.fix_character_spacing("\n".join(example_lines).rstrip())

    def _generate_function_example(self, entity: FunctionEntity) -> str:
        """Generate example code for a function.

        Args:
            entity: The function entity

        Returns:
            Example code as a string
        """
        # Get the function name
        function_name = entity.name

        # Generate parameter values for the function call
        param_values = []
        if hasattr(entity, 'parameters') and entity.parameters:
            for param in entity.parameters:
                # Generate appropriate example values based on parameter type
                if hasattr(param, 'type') and param.type:
                    if 'str' in param.type.lower():
                        param_values.append(f'"{param.name}_value"')
                    elif 'int' in param.type.lower():
                        param_values.append('42')
                    elif 'float' in param.type.lower():
                        param_values.append('3.14')
                    elif 'bool' in param.type.lower():
                        param_values.append('True')
                    elif 'list' in param.type.lower():
                        param_values.append('[]')
                    elif 'dict' in param.type.lower():
                        param_values.append('{}')
                    else:
                        param_values.append(f'{param.name}_value')
                else:
                    param_values.append(f'{param.name}_value')

        # Create the function call example
        param_str = ', '.join(param_values)
        
        # Create the example
        example_lines = [
            f"# Call the {function_name} function",
            f"result = {function_name}({param_str})"
        ]

        # Apply text formatting
        return TextFormatter.fix_character_spacing("\n".join(example_lines))

    def _generate_function_complexity(self, entity: FunctionEntity) -> str:
        """Generate a description of function complexity."""
        complexity = "Simple"
        complexity_factors = []
        
        # Check parameter count
        if hasattr(entity, 'parameters') and entity.parameters:
            param_count = len(entity.parameters)
            if param_count > 5:
                complexity = "Complex"
                complexity_factors.append(f"takes {param_count} parameters")
            elif param_count > 3:
                complexity = "Moderate"
                complexity_factors.append(f"takes {param_count} parameters")
            
            # Check for default parameters
            default_params = [param for param in entity.parameters if hasattr(param, 'default_value') and param.default_value is not None]
            if default_params:
                complexity_factors.append(f"has {len(default_params)} optional parameters")
        
        # Check for return type complexity
        if hasattr(entity, 'return_type') and entity.return_type:
            if 'list' in entity.return_type.lower() or 'dict' in entity.return_type.lower():
                complexity_factors.append("returns a complex data structure")
                if complexity == "Simple":
                    complexity = "Moderate"
        
        # Generate description
        if complexity_factors:
            return f"{complexity} function that {', '.join(complexity_factors)}."
        return f"{complexity} function."

    def _generate_method_example(self, entity: FunctionEntity) -> str:
        """Generate example code for a method.

        Args:
            entity: The method entity

        Returns:
            Example code as a string
        """
        # Get the class name and method name
        class_name = entity.parent_class if hasattr(entity, 'parent_class') else "MyClass"
        method_name = entity.name

        # Generate parameter values for the method call
        param_values = []
        if hasattr(entity, 'parameters') and entity.parameters:
            for param in entity.parameters:
                # Skip self parameter
                if param.name == 'self':
                    continue
                
                # Generate appropriate example values based on parameter type
                if hasattr(param, 'type') and param.type:
                    if 'str' in param.type.lower():
                        param_values.append(f'"{param.name}_value"')
                    elif 'int' in param.type.lower():
                        param_values.append('42')
                    elif 'float' in param.type.lower():
                        param_values.append('3.14')
                    elif 'bool' in param.type.lower():
                        param_values.append('True')
                    elif 'list' in param.type.lower():
                        param_values.append('[]')
                    elif 'dict' in param.type.lower():
                        param_values.append('{}')
                    else:
                        param_values.append(f'{param.name}_value')
                else:
                    param_values.append(f'{param.name}_value')

        # Create the method call example
        param_str = ', '.join(param_values)
        
        # Create a simple instance initialization
        example_lines = [
            f"# Create an instance of {class_name}",
            f"instance = {class_name}()",
            "",
            f"# Call the {method_name} method",
            f"result = instance.{method_name}({param_str})"
        ]

        # Apply text formatting
        return TextFormatter.fix_character_spacing("\n".join(example_lines))

    def _get_external_dependencies(self, entity: ModuleEntity) -> List[str]:
        """Get external dependencies of a module.
        
        Args:
            entity: The module entity.
            
        Returns:
            List of external dependency names.
        """
        if not hasattr(entity, 'imports') or not entity.imports:
            return []
        
        # Handle ImportEntity objects
        if all(isinstance(imp, ImportEntity) for imp in entity.imports):
            return [imp.module_name for imp in entity.imports 
                    if not imp.module_name.startswith('.')]
        
        # Handle string imports (legacy)
        return [imp for imp in entity.imports 
                if not imp.startswith('from .') and not imp.startswith('import .')]

    def _get_internal_dependencies(self, entity: ModuleEntity) -> List[str]:
        """Get internal dependencies of a module.
        
        Args:
            entity: The module entity.
            
        Returns:
            List of internal dependency names.
        """
        if not hasattr(entity, 'imports') or not entity.imports:
            return []
        
        # Handle ImportEntity objects
        if all(isinstance(imp, ImportEntity) for imp in entity.imports):
            return [imp.module_name for imp in entity.imports 
                    if imp.module_name.startswith('.')]
        
        # Handle string imports (legacy)
        return [imp for imp in entity.imports 
                if imp.startswith('from .') or imp.startswith('import .')]

    def _get_classes(self, entity: ModuleEntity) -> List[str]:
        """Get classes defined in a module.
        
        Args:
            entity: The module entity.
            
        Returns:
            List of class names with their base classes.
        """
        class_entities = [e for e in self.relationship_mapper.entities.values() 
                          if isinstance(e, ClassEntity) and 
                          hasattr(e, 'module_name') and 
                          e.module_name == entity.name]
        
        if not class_entities:
            return []
        
        class_notes = []
        for cls in class_entities:
            if hasattr(cls, 'bases') and cls.bases:
                base_classes_str = ', '.join(cls.bases)
                class_notes.append(f"{cls.name} (inherits from {base_classes_str})")
            else:
                class_notes.append(cls.name)
        
        return class_notes

    def _get_functions(self, entity: ModuleEntity) -> List[str]:
        """Get functions defined in a module.
        
        Args:
            entity: The module entity.
            
        Returns:
            List of function names.
        """
        function_entities = [e for e in self.relationship_mapper.entities.values() 
                            if isinstance(e, FunctionEntity) and 
                            not hasattr(e, 'is_method') and 
                            hasattr(e, 'module_name') and 
                            e.module_name == entity.name]
        
        if not function_entities:
            return []
        
        return [f.name for f in function_entities]

    def _get_variables(self, entity: ModuleEntity) -> List[str]:
        """Get variables defined in a module.
        
        Args:
            entity: The module entity.
            
        Returns:
            List of variable names.
        """
        variable_entities = [e for e in self.relationship_mapper.entities.values() 
                            if isinstance(e, VariableEntity) and 
                            hasattr(e, 'module_name') and 
                            e.module_name == entity.name]
        
        if not variable_entities:
            return []
        
        return [v.name for v in variable_entities]

    def _get_methods(self, entity: ClassEntity) -> List[str]:
        """Get methods defined in a class.
        
        Args:
            entity: The class entity.
            
        Returns:
            List of method names.
        """
        if not hasattr(entity, 'methods') or not entity.methods:
            return []
        
        return [m.name for m in entity.methods]

    def _get_properties(self, entity: ClassEntity) -> List[str]:
        """Get properties defined in a class.
        
        Args:
            entity: The class entity.
            
        Returns:
            List of property names.
        """
        if not hasattr(entity, 'properties') or not entity.properties:
            return []
        
        return [p.name for p in entity.properties]

    def _get_class_variables(self, entity: ClassEntity) -> List[str]:
        """Get class variables defined in a class.
        
        Args:
            entity: The class entity.
            
        Returns:
            List of class variable names.
        """
        if not hasattr(entity, 'class_variables') or not entity.class_variables:
            return []
        
        return [v.name for v in entity.class_variables]

    def _get_instance_variables(self, entity: ClassEntity) -> List[str]:
        """Get instance variables defined in a class.
        
        Args:
            entity: The class entity.
            
        Returns:
            List of instance variable names.
        """
        if not hasattr(entity, 'instance_variables') or not entity.instance_variables:
            return []
        
        return [v.name for v in entity.instance_variables]

    def _get_function_complexity(self, entity: FunctionEntity) -> Optional[str]:
        """Get complexity estimation for a function.
        
        Args:
            entity: The function entity.
            
        Returns:
            Complexity description or None.
        """
        if not hasattr(entity, 'code') or not entity.code:
            return None
        
        # Count branching structures
        if_count = len(re.findall(r'\bif\b', entity.code))
        for_count = len(re.findall(r'\bfor\b', entity.code))
        while_count = len(re.findall(r'\bwhile\b', entity.code))
        
        # Make a simple assessment
        branch_count = if_count + for_count + while_count
        
        if branch_count == 0:
            return "Simple (linear execution)"
        elif branch_count <= 2:
            return "Low (few branches)"
        elif branch_count <= 5:
            return "Moderate"
        else:
            return "Complex (many branches)"

    def _get_function_calls(self, entity: FunctionEntity) -> List[str]:
        """Get function calls made by a function.
        
        Args:
            entity: The function entity.
            
        Returns:
            List of function call names.
        """
        if not hasattr(entity, 'calls') or not entity.calls:
            return []
        
        return entity.calls

    def _get_return_values(self, entity: FunctionEntity) -> List[str]:
        """Get return value types of a function.
        
        Args:
            entity: The function entity.
            
        Returns:
            List of return value descriptions.
        """
        if not hasattr(entity, 'returns') or not entity.returns:
            return []
        
        if hasattr(entity.returns, 'type') and entity.returns.type:
            return [entity.returns.type]
        
        return []

    def _get_local_variables(self, entity: FunctionEntity) -> List[str]:
        """Get local variables defined in a function.
        
        Args:
            entity: The function entity.
            
        Returns:
            List of local variable names.
        """
        if not hasattr(entity, 'local_variables') or not entity.local_variables:
            return []
        
        return [v.name for v in entity.local_variables]


if __name__ == "__main__":
    # Example usage
    context_generator = ContextGenerator()
    
    # To use, you would generate context for an entity
    # context = context_generator.generate_context(some_entity) 