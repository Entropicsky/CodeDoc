"""
Tests for the metadata generator.
"""

import os
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from codedoc.preprocessors.metadata_generator import MetadataGenerator


class TestMetadataGenerator:
    """Tests for the MetadataGenerator class."""
    
    def test_init(self):
        """Test initialization."""
        generator = MetadataGenerator()
        
        # Verify language mappings are initialized
        assert len(generator.language_by_extension) > 0
        assert generator.language_by_extension['.py'] == 'python'
        assert generator.language_by_extension['.js'] == 'javascript'
    
    def test_generate_metadata_basic(self, temp_dir):
        """Test generating basic metadata for a file."""
        # Create a sample file
        file_path = temp_dir / "test.txt"
        with open(file_path, "w") as f:
            f.write("Sample content.")
        
        # Generate metadata
        generator = MetadataGenerator()
        metadata = generator.generate_metadata(file_path)
        
        # Verify basic metadata
        assert metadata["file_path"] == str(file_path)
        assert metadata["file_name"] == "test.txt"
        assert metadata["file_extension"] == ".txt"
        assert metadata["file_size_bytes"] > 0
        assert "created_at" in metadata
        assert "modified_at" in metadata
        assert "created_at_iso" in metadata
        assert "modified_at_iso" in metadata
    
    def test_generate_metadata_with_language(self, temp_dir):
        """Test language detection in metadata."""
        # Create sample files with different languages
        python_file = temp_dir / "test.py"
        js_file = temp_dir / "test.js"
        unknown_file = temp_dir / "test.xyz"
        
        for file_path in [python_file, js_file, unknown_file]:
            with open(file_path, "w") as f:
                f.write("Sample content.")
        
        # Generate metadata for each file
        generator = MetadataGenerator()
        py_metadata = generator.generate_metadata(python_file)
        js_metadata = generator.generate_metadata(js_file)
        unknown_metadata = generator.generate_metadata(unknown_file)
        
        # Verify language detection
        assert py_metadata["language"] == "python"
        assert js_metadata["language"] == "javascript"
        assert "language" not in unknown_metadata  # Unknown extension
    
    def test_generate_metadata_with_content(self, temp_dir):
        """Test generating metadata with content analysis."""
        # Create a Python file with content
        file_path = temp_dir / "test.py"
        content = """
import os
import sys
from typing import List

class TestClass:
    def __init__(self):
        pass
        
    def test_method(self):
        return True

def test_function(x: int) -> bool:
    return x > 0
"""
        with open(file_path, "w") as f:
            f.write(content)
        
        # Generate metadata with content
        generator = MetadataGenerator()
        metadata = generator.generate_metadata(file_path, content)
        
        # Verify content-based metadata
        assert "content_hash" in metadata
        assert metadata["line_count"] > 1
        assert metadata["character_count"] > 0
        assert metadata["word_count"] > 0
        
        # Verify Python-specific metadata
        assert "imports" in metadata
        assert "os" in metadata["imports"]
        assert "sys" in metadata["imports"]
        assert "classes" in metadata
        assert "TestClass" in metadata["classes"]
        assert "functions" in metadata
        assert "test_function" in metadata["functions"]
    
    def test_process_python_metadata(self):
        """Test Python-specific metadata processing."""
        generator = MetadataGenerator()
        
        # Python content with imports, classes, functions, and docstring
        content = '''"""
Sample Python module.

This is a sample module for testing.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict

class SampleClass:
    """A sample class."""
    
    def __init__(self):
        pass
    
    def method(self):
        return True

def sample_function(x):
    return x
'''
        
        # Empty metadata to be filled by the method
        metadata = {"language": "python"}
        
        # Process Python metadata
        generator._process_python_metadata(metadata, content)
        
        # Verify imports are extracted
        assert "imports" in metadata
        assert "os" in metadata["imports"]
        assert "sys" in metadata["imports"]
        assert "pathlib.Path" in metadata["imports"]
        
        # Verify classes are extracted
        assert "classes" in metadata
        assert "SampleClass" in metadata["classes"]
        
        # Verify functions are extracted
        assert "functions" in metadata
        assert "sample_function" in metadata["functions"]
        
        # Verify docstring is detected
        assert metadata["has_docstring"] is True
        assert metadata["description"] == "Sample Python module."
    
    def test_process_js_ts_metadata(self):
        """Test JavaScript/TypeScript metadata processing."""
        generator = MetadataGenerator()
        
        # JavaScript content with imports, classes, and functions
        content = '''// Sample JavaScript module
        
import { useState, useEffect } from 'react';
import axios from 'axios';
const fs = require('fs');

class ApiClient {
    constructor() {
        this.baseUrl = '/api';
    }
    
    async fetchData() {
        return axios.get(this.baseUrl);
    }
}

function processData(data) {
    return data.map(item => item.id);
}

const processItems = (items) => {
    return items.filter(item => item.active);
};
'''
        
        # Empty metadata to be filled by the method
        metadata = {"language": "javascript"}
        
        # Process JavaScript metadata
        generator._process_js_ts_metadata(metadata, content)
        
        # Verify imports are extracted
        assert "imports" in metadata
        assert any("react/useState" in imp for imp in metadata["imports"])
        assert any("react/useEffect" in imp for imp in metadata["imports"])
        assert any("axios" in imp for imp in metadata["imports"])
        
        # Verify classes are extracted
        assert "classes" in metadata
        assert "ApiClient" in metadata["classes"]
        
        # Verify functions are extracted
        assert "functions" in metadata
        assert "processData" in metadata["functions"]
        assert "processItems" in metadata["functions"]
    
    def test_process_markdown_metadata(self):
        """Test Markdown metadata processing."""
        generator = MetadataGenerator()
        
        # Markdown content with headings, links, and code blocks
        content = '''# Sample Document
        
## Introduction
This is an introduction to the document.

## Section 1
Content for section 1.

### Subsection 1.1
More detailed content.

Check out [this link](https://example.com) for more information.

```python
def sample_function():
    return True
```

```javascript
function processData() {
    return true;
}
```
'''
        
        # Empty metadata to be filled by the method
        metadata = {"language": "markdown"}
        
        # Process Markdown metadata
        generator._process_markdown_metadata(metadata, content)
        
        # Verify title is extracted
        assert "title" in metadata
        assert metadata["title"] == "Sample Document"
        
        # Verify headings are extracted
        assert "headings" in metadata
        assert len(metadata["headings"]) >= 4  # At least 4 headings
        assert any(h["text"] == "Introduction" for h in metadata["headings"])
        assert any(h["text"] == "Section 1" for h in metadata["headings"])
        
        # Verify links are extracted
        assert "links" in metadata
        assert len(metadata["links"]) >= 1
        assert metadata["links"][0]["text"] == "this link"
        assert metadata["links"][0]["url"] == "https://example.com"
        
        # Verify code blocks are extracted
        assert "code_block_count" in metadata
        assert metadata["code_block_count"] == 2
        assert "code_block_languages" in metadata
        assert "python" in metadata["code_block_languages"]
        assert "javascript" in metadata["code_block_languages"] 