#!/usr/bin/env python3
"""
Relationship Mapper for CodeDoc.

This module provides functionality to analyze code and extract relationships
between different entities such as inheritance hierarchies, function calls,
and module dependencies.
"""

import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple, Union
import networkx as nx

from codedoc.core.entities import (
    Entity, ModuleEntity, ClassEntity, FunctionEntity, VariableEntity
)


class RelationshipMapper:
    """
    Analyzes code to extract relationships between entities.
    
    This class identifies and maps relationships such as:
    - Class inheritance hierarchies
    - Function call graphs
    - Module dependencies
    - Variable usage patterns
    
    These relationships are used to enrich documentation with contextual
    information that helps understand how code components interact.
    """
    
    def __init__(self):
        """
        Initialize the relationship mapper.
        """
        self.entities: Dict[str, Entity] = {}
        self.entity_ids: Dict[str, str] = {}  # Maps entity objects to their IDs
        self.relationships: List[Tuple[str, str, str]] = []  # (source_id, target_id, relationship_type)
        self.import_graph = nx.DiGraph()
        self.inheritance_graph = nx.DiGraph()
        self.call_graph = nx.DiGraph()
        
        # Map of file paths to ModuleEntity objects
        self.modules: Dict[str, ModuleEntity] = {}
        
        # Track parent-child relationships for nested entities
        self.parent_map: Dict[str, str] = {}

    def register_entities(self, entities: List[Entity]) -> None:
        """
        Register entities to be analyzed for relationships.
        
        Args:
            entities: List of entities to register
        """
        for entity in entities:
            self._register_entity(entity)
    
    def _register_entity(self, entity: Entity) -> None:
        """
        Register a single entity.
        
        Args:
            entity: The entity to register
        """
        # Register by full name
        full_name = self._get_full_name(entity)
        self.entities[full_name] = entity
        
        # Register modules separately
        if isinstance(entity, ModuleEntity):
            self.modules[entity.file_path] = entity
            
            # Add module to import graph
            self.import_graph.add_node(full_name, entity=entity)
            
            # Process imports
            for imp in entity.imports:
                # Extract the module being imported
                imported_module = self._extract_module_from_import(imp)
                if imported_module:
                    self.import_graph.add_edge(full_name, imported_module)
        
        # Add class to inheritance graph
        if isinstance(entity, ClassEntity):
            self.inheritance_graph.add_node(full_name, entity=entity)
            
            # Process base classes
            for base in entity.base_classes:
                # If base class is a direct name, try to resolve it within the same module
                if '.' not in base and hasattr(entity, 'module_name') and entity.module_name:
                    qualified_base = f"{entity.module_name}.{base}"
                    if qualified_base in self.entities:
                        self.inheritance_graph.add_edge(full_name, qualified_base)
                    else:
                        self.inheritance_graph.add_edge(full_name, base)
                else:
                    self.inheritance_graph.add_edge(full_name, base)
        
        # Add function to call graph
        if isinstance(entity, FunctionEntity):
            self.call_graph.add_node(full_name, entity=entity)
            
            # For methods, track parent class
            if entity.is_method and hasattr(entity, 'parent_class') and entity.parent_class:
                class_name = self._get_full_name_for_parent(entity)
                self.parent_map[full_name] = class_name

    def _get_full_name(self, entity: Entity) -> str:
        """
        Get the fully qualified name for an entity.
        
        Args:
            entity: The entity to get the name for
            
        Returns:
            The fully qualified name
        """
        # For modules, use the module name
        if isinstance(entity, ModuleEntity):
            return entity.name
        
        # For other entities, use module.name
        if hasattr(entity, 'module_name') and entity.module_name:
            # For methods, include the class name
            if isinstance(entity, FunctionEntity) and entity.is_method and hasattr(entity, 'parent_class') and entity.parent_class:
                return f"{entity.module_name}.{entity.parent_class}.{entity.name}"
            return f"{entity.module_name}.{entity.name}"
        
        # If no module name, just use the entity name
        return entity.name

    def _get_full_name_for_parent(self, entity: Entity) -> str:
        """
        Get the fully qualified name for a parent entity.
        
        Args:
            entity: The entity to get the parent's name for
            
        Returns:
            The fully qualified parent name
        """
        if isinstance(entity, FunctionEntity) and hasattr(entity, 'parent_class') and entity.parent_class and hasattr(entity, 'module_name') and entity.module_name:
            return f"{entity.module_name}.{entity.parent_class}"
        return ""

    def _extract_module_from_import(self, import_stmt: str) -> str:
        """
        Extract the module name from an import statement.
        
        Args:
            import_stmt: The import statement as a string or ImportEntity
            
        Returns:
            The extracted module name
        """
        # Handle ImportEntity objects
        if hasattr(import_stmt, 'module'):
            return import_stmt.module.split('.')[0]
            
        # Handle string import statements
        if isinstance(import_stmt, str):
            # Handle "import x"
            if import_stmt.startswith('import '):
                parts = import_stmt[7:].split()
                if parts and parts[0] != 'as':
                    return parts[0].split('.')[0]
            
            # Handle "from x import y"
            elif import_stmt.startswith('from '):
                parts = import_stmt[5:].split(' import ')
                if len(parts) > 0:
                    return parts[0]
        
        return ""

    def analyze_function_calls(self):
        """
        Analyze function calls within functions to identify relationships.
        """
        for entity_id, entity in self.entities.items():
            if isinstance(entity, FunctionEntity) and hasattr(entity, 'ast_node') and entity.ast_node:
                visitor = FunctionCallVisitor()
                visitor.visit(entity.ast_node)
                
                for call_name in visitor.function_calls:
                    # Check if the call is to a known function
                    for target_id, target_entity in self.entities.items():
                        if isinstance(target_entity, FunctionEntity) and target_entity.name == call_name:
                            self._add_relationship(entity_id, target_id, "calls")
                            break

    def _resolve_call_target(self, call: str, caller: Entity) -> Optional[str]:
        """
        Resolve a function call to a fully qualified target name.
        
        Args:
            call: The function call as a string
            caller: The entity making the call
            
        Returns:
            The fully qualified name of the target function, or None if it can't be resolved
        """
        # If call already has a full path
        if call in self.entities:
            return call
        
        # If call has a dot, it might be a module.function or class.method
        if '.' in call:
            # Split into parts
            parts = call.split('.')
            
            # Check if it's a call to a method of a known class
            if len(parts) == 2:
                class_name, method_name = parts
                
                # If caller is in a module, try module.class.method
                if caller.module_name:
                    qualified_name = f"{caller.module_name}.{class_name}.{method_name}"
                    if qualified_name in self.entities:
                        return qualified_name
                    
                    # Also try as a direct reference to a module.function
                    qualified_name = f"{class_name}.{method_name}"
                    if qualified_name in self.entities:
                        return qualified_name
        
        # If it's a simple name, it might be in the same module
        elif caller.module_name:
            # Check if it's a function in the same module
            qualified_name = f"{caller.module_name}.{call}"
            if qualified_name in self.entities:
                return qualified_name
            
            # If caller is a method, check if it's a method in the same class
            if isinstance(caller, FunctionEntity) and caller.is_method and caller.parent_class:
                qualified_name = f"{caller.module_name}.{caller.parent_class}.{call}"
                if qualified_name in self.entities:
                    return qualified_name
        
        return None

    def get_module_relationships(self, module_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all relationships for a specific module.
        
        Args:
            module_name: The name of the module
            
        Returns:
            A dictionary with relationship types as keys and lists of related entities as values
        """
        # Find all classes in this module
        module_classes = [
            entity for entity_id, entity in self.entities.items()
            if isinstance(entity, ClassEntity) and hasattr(entity, 'module_name') and entity.module_name == module_name
        ]
        
        # Find all functions in this module
        module_functions = [
            entity for entity_id, entity in self.entities.items()
            if isinstance(entity, FunctionEntity) and 
               not entity.is_method and 
               hasattr(entity, 'module_name') and 
               entity.module_name == module_name
        ]
        
        # Find all variables in this module
        module_variables = [
            entity for entity_id, entity in self.entities.items()
            if isinstance(entity, VariableEntity) and 
               hasattr(entity, 'module_name') and 
               entity.module_name == module_name
        ]
        
        # Collect all relationships
        relationships = {
            "imports": [],
            "imported_by": [],
            "classes": [self._entity_to_dict(cls) for cls in module_classes],
            "functions": [self._entity_to_dict(func) for func in module_functions],
            "variables": [self._entity_to_dict(var) for var in module_variables],
        }
        
        # Add import relationships
        for source, target, rel_type in self.relationships:
            source_entity = self.entities.get(source)
            target_entity = self.entities.get(target)
            
            if not source_entity or not target_entity:
                continue
                
            if rel_type == "imports":
                # This module imports another module
                if isinstance(source_entity, ModuleEntity) and source_entity.name == module_name:
                    relationships["imports"].append(self._entity_to_dict(target_entity))
                
                # This module is imported by another module
                if isinstance(target_entity, ModuleEntity) and target_entity.name == module_name:
                    relationships["imported_by"].append(self._entity_to_dict(source_entity))
        
        return relationships

    def get_class_relationships(self, class_name: str) -> Dict[str, Any]:
        """
        Get relationships for a class.
        
        Args:
            class_name: The fully qualified name of the class
            
        Returns:
            A dictionary containing relationship information
        """
        results = {
            'inherits_from': [],
            'inherited_by': [],
            'uses': [],
            'used_by': [],
            'class_hierarchy': []
        }
        
        # Get inheritance relationships
        if class_name in self.inheritance_graph:
            results['inherits_from'] = [
                str(base) for base in self.inheritance_graph.successors(class_name)
            ]
            results['inherited_by'] = [
                str(derived) for derived in self.inheritance_graph.predecessors(class_name)
                if derived != class_name  # Skip self-inheritance
            ]
            
            # Generate Mermaid class diagram statements
            class_short = class_name.split('.')[-1]
            
            # Add base classes
            for base in results['inherits_from']:
                base_short = base.split('.')[-1]
                results['class_hierarchy'].append(f"{base_short} <|-- {class_short}")
            
            # Add derived classes
            for derived in results['inherited_by']:
                derived_short = derived.split('.')[-1]
                results['class_hierarchy'].append(f"{class_short} <|-- {derived_short}")
        
        # Find method calls
        class_methods = [
            name for name, entity in self.entities.items()
            if isinstance(entity, FunctionEntity) and 
               entity.is_method and 
               self._get_full_name_for_parent(entity) == class_name
        ]
        
        # Collect all uses (what this class's methods call)
        uses = set()
        for method in class_methods:
            if method in self.call_graph:
                for target in self.call_graph.successors(method):
                    if self._is_external_call(method, target):
                        uses.add(target)
        
        # Collect all used_by (what calls this class's methods)
        used_by = set()
        for method in class_methods:
            if method in self.call_graph:
                for source in self.call_graph.predecessors(method):
                    if self._is_external_call(source, method):
                        used_by.add(source)
        
        results['uses'] = list(uses)
        results['used_by'] = list(used_by)
        
        return results

    def get_function_relationships(self, function_name: str) -> Dict[str, Any]:
        """
        Get relationships for a function.
        
        Args:
            function_name: The fully qualified name of the function
            
        Returns:
            A dictionary containing relationship information
        """
        results = {
            'function_calls': {
                'calls': [],
                'called_by': []
            },
            'call_graph': []
        }
        
        # Get call relationships
        if function_name in self.call_graph:
            # Get calls made by this function
            calls = [str(target) for target in self.call_graph.successors(function_name)]
            
            # Get calls to this function
            called_by = [str(source) for source in self.call_graph.predecessors(function_name)]
            
            results['function_calls']['calls'] = calls
            results['function_calls']['called_by'] = called_by
            
            # Generate Mermaid flow diagram statements
            func_short = self._get_short_name(function_name)
            
            # Add function calls
            for call in calls:
                call_short = self._get_short_name(call)
                results['call_graph'].append(f"{func_short} --> {call_short}")
            
            # Add callers
            for caller in called_by:
                caller_short = self._get_short_name(caller)
                results['call_graph'].append(f"{caller_short} --> {func_short}")
        
        return results

    def get_variable_relationships(self, variable_name: str) -> Dict[str, Any]:
        """
        Get relationships for a variable.
        
        Args:
            variable_name: The fully qualified name of the variable
            
        Returns:
            A dictionary containing relationship information
        """
        # Currently, we don't track detailed variable usage
        # This can be enhanced in future versions
        return {
            'used_by': []
        }

    def _is_external_call(self, source: str, target: str) -> bool:
        """
        Check if a call is between different entities.
        
        Args:
            source: The source of the call
            target: The target of the call
            
        Returns:
            True if the call is between different entities
        """
        # If the source is in parent_map (a method), compare the class with the target
        if source in self.parent_map:
            source_parent = self.parent_map[source]
            
            # If target is also a method, check if they have different parent classes
            if target in self.parent_map:
                target_parent = self.parent_map[target]
                return source_parent != target_parent
            
            # If target is not a method, it's external
            return True
        
        # If source is not a method but target is, it's external
        if target in self.parent_map:
            return True
        
        # If neither is a method, check if they're in different modules
        source_parts = source.split('.')
        target_parts = target.split('.')
        
        if len(source_parts) > 1 and len(target_parts) > 1:
            source_module = '.'.join(source_parts[:-1])
            target_module = '.'.join(target_parts[:-1])
            return source_module != target_module
        
        # If we can't determine, consider it external
        return True

    def _get_short_name(self, full_name: str) -> str:
        """
        Get a shortened name for display in diagrams.
        
        Args:
            full_name: The fully qualified name
            
        Returns:
            A shortened name suitable for display
        """
        parts = full_name.split('.')
        
        # For methods (module.class.method), return class.method
        if len(parts) >= 3:
            return f"{parts[-2]}.{parts[-1]}"
        
        # For other entities, return the last part
        return parts[-1]

    def get_relationships_for_entity(self, entity: Entity) -> Dict[str, Any]:
        """
        Get relationships for an entity.
        
        Args:
            entity: The entity to get relationships for
            
        Returns:
            A dictionary containing relationship information
        """
        full_name = self._get_full_name(entity)
        
        if isinstance(entity, ModuleEntity):
            return self.get_module_relationships(full_name)
        elif isinstance(entity, ClassEntity):
            return self.get_class_relationships(full_name)
        elif isinstance(entity, FunctionEntity):
            return self.get_function_relationships(full_name)
        elif isinstance(entity, VariableEntity):
            return self.get_variable_relationships(full_name)
        else:
            return {}

    def _entity_to_dict(self, entity: Entity) -> Dict[str, Any]:
        """
        Convert an entity to a dictionary representation.
        
        Args:
            entity: The entity to convert
            
        Returns:
            A dictionary representation of the entity
        """
        result = {
            "name": entity.name,
            "type": type(entity).__name__,
        }
        
        # Add module name if available
        if hasattr(entity, "module_name") and entity.module_name:
            result["module_name"] = entity.module_name
            
        # Add class-specific attributes
        if isinstance(entity, ClassEntity):
            if hasattr(entity, "base_classes") and entity.base_classes:
                result["base_classes"] = entity.base_classes
                
        # Add function-specific attributes
        if isinstance(entity, FunctionEntity):
            if hasattr(entity, "is_method") and entity.is_method:
                result["is_method"] = entity.is_method
            if hasattr(entity, "parent_class") and entity.parent_class:
                result["parent_class"] = entity.parent_class
                
        return result

    def _add_relationship(self, source_id: str, target_id: str, relationship_type: str) -> None:
        """
        Add a relationship between two entities.
        
        Args:
            source_id: The ID of the source entity
            target_id: The ID of the target entity
            relationship_type: The type of relationship
        """
        # Add to the appropriate graph
        if relationship_type == "inherits":
            self.inheritance_graph.add_edge(source_id, target_id)
        elif relationship_type == "calls":
            self.call_graph.add_edge(source_id, target_id)
        elif relationship_type == "imports":
            self.import_graph.add_edge(source_id, target_id)
            
        # Add to the general relationships list
        self.relationships.append((source_id, target_id, relationship_type))


class FunctionCallVisitor(ast.NodeVisitor):
    """
    AST visitor that identifies function calls in code.
    """
    
    def __init__(self):
        """
        Initialize the visitor.
        """
        self.function_calls: Set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        """
        Visit a function call node in the AST.
        
        Args:
            node: The AST node representing a function call
        """
        # Extract the call target
        if isinstance(node.func, ast.Name):
            # Simple function call: func()
            self.function_calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Attribute call: obj.method()
            # Convert to a dotted path
            path = self._get_attribute_path(node.func)
            if path:
                self.function_calls.add(path)
        
        # Continue visiting children
        self.generic_visit(node)

    def _get_attribute_path(self, node: ast.Attribute) -> str:
        """
        Convert an attribute node to a dotted path.
        
        Args:
            node: The attribute node
            
        Returns:
            The dotted path as a string
        """
        parts = []
        
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        
        if isinstance(current, ast.Name):
            parts.append(current.id)
        else:
            # If it's not a simple chain of attributes, return just the method name
            return node.attr
        
        # Reverse and join with dots
        return '.'.join(reversed(parts))


if __name__ == "__main__":
    # Example usage
    mapper = RelationshipMapper()
    
    # To use, you would register entities and then analyze relationships
    # mapper.register_entities(entities)
    # mapper.analyze_function_calls()
    # 
    # Then retrieve relationships for specific entities
    # relationships = mapper.get_relationships_for_entity(some_entity) 