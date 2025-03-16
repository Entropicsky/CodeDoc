"""
Configuration settings for CodeDoc.

This module handles loading configuration from various sources:
1. Default settings
2. Configuration file
3. Environment variables
4. Command line arguments
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union


class Settings:
    """Settings class for CodeDoc configuration."""
    
    def __init__(self):
        """Initialize with default settings."""
        # Default settings
        self.defaults = {
            # General settings
            "verbose": False,
            "output_dir": "./docs_output",
            "temp_dir": "./temp",
            
            # Parser settings
            "supported_languages": ["python", "javascript", "yaml", "json"],
            "exclude_dirs": [".git", "__pycache__", "venv", "node_modules", ".vscode"],
            "exclude_files": [".DS_Store", "*.pyc", "*.pyo", "*.pyd", "*.so", "*.dll"],
            
            # Documentation settings
            "doc_formats": ["json", "markdown"],
            "include_diagrams": True,
            "diagram_format": "mermaid",
            
            # Analysis settings
            "analyze_imports": True,
            "analyze_inheritance": True,
            "analyze_calls": True,
            "analyze_data_flow": True,
            "analyze_api_endpoints": True,
            
            # Enhancement settings
            "enhance_with_llm": False,
            "llm_api_key": None,
            "llm_model": "gpt-4",
            
            # Output settings
            "vector_db_ready": True,
            "chunk_size": 1000,
            "chunk_overlap": 200,
        }
        
        # Current settings (will be updated from config files, env vars, etc.)
        self.current = self.defaults.copy()
    
    def from_file(self, config_path: Union[str, Path]) -> None:
        """Load settings from a YAML configuration file."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, "r") as f:
            file_config = yaml.safe_load(f)
        
        self.update_from_dict(file_config)
    
    def from_env(self) -> None:
        """Load settings from environment variables."""
        # Look for environment variables with the prefix CODEDOC_
        env_config = {}
        for key, value in os.environ.items():
            if key.startswith("CODEDOC_"):
                # Remove prefix and convert to lowercase
                setting_key = key[8:].lower()
                
                # Convert string value to appropriate type based on default
                if setting_key in self.defaults:
                    default_value = self.defaults[setting_key]
                    if isinstance(default_value, bool):
                        env_config[setting_key] = value.lower() in ('true', 'yes', '1')
                    elif isinstance(default_value, int):
                        try:
                            env_config[setting_key] = int(value)
                        except ValueError:
                            pass
                    elif isinstance(default_value, float):
                        try:
                            env_config[setting_key] = float(value)
                        except ValueError:
                            pass
                    elif isinstance(default_value, list):
                        env_config[setting_key] = value.split(',')
                    else:
                        env_config[setting_key] = value
        
        self.update_from_dict(env_config)
    
    def from_args(self, args: Dict[str, Any]) -> None:
        """Update settings from command line arguments."""
        args_config = {}
        for key, value in args.items():
            if value is not None:  # Only update if argument was provided
                args_config[key] = value
        
        self.update_from_dict(args_config)
    
    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """Update current settings from a dictionary."""
        for key, value in config_dict.items():
            if key in self.current:
                self.current[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.current.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self.current[key] = value
    
    def as_dict(self) -> Dict[str, Any]:
        """Return the current settings as a dictionary."""
        return self.current.copy()


# Create a global settings instance
settings = Settings()


def load_config(config_path: Optional[str] = None) -> Settings:
    """
    Load configuration from all sources.
    
    Order of precedence:
    1. Command line arguments (highest)
    2. Environment variables
    3. Configuration file
    4. Default settings (lowest)
    """
    # Start with default settings
    settings = Settings()
    
    # Load from config file if provided
    if config_path:
        try:
            settings.from_file(config_path)
        except Exception as e:
            print(f"Error loading config file: {e}")
    
    # Load from environment variables
    settings.from_env()
    
    return settings 