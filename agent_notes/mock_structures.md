# Mock Structures Reference

This document provides reference structures for properly mocking components in the CodeDoc system. Use these structures to ensure your mocks return data in the expected format.

## LLM Client Mocks

### OpenAI Client - `generate_with_system_prompt` Method

```python
# Example mock return structure
mock_response = {
    "content": "Enhanced code description or analysis here",
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 250,
        "total_tokens": 400
    }
}
```

Code to create this mock:

```python
from unittest.mock import MagicMock, patch

# Mock at method level (recommended)
with patch.object(OpenAIClient, 'generate_with_system_prompt', return_value={
    "content": "Enhanced code description or analysis here",
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 250,
        "total_tokens": 400
    }
}) as mock_generate:
    # Your test code here
    # ...
    # Verify the mock was called
    mock_generate.assert_called_once()
```

## ContentGenerator Mocks

### `generate_faq` Method

```python
# Example mock return structure
mock_faq_response = {
    "content": "# Frequently Asked Questions\n\n1. Question 1?\nAnswer 1.\n\n2. Question 2?\nAnswer 2.",
    "usage": {
        "prompt_tokens": 200,
        "completion_tokens": 300,
        "total_tokens": 500
    }
}
```

### `generate_tutorial` Method

```python
# Example mock return structure
mock_tutorial_response = {
    "content": "# Tutorial\n\nThis tutorial explains how to use the component...",
    "usage": {
        "prompt_tokens": 250,
        "completion_tokens": 450,
        "total_tokens": 700
    }
}
```

### `generate_architecture_diagram` Method

```python
# Example mock return structure
mock_architecture_response = {
    "content": "# Architecture Overview\n\nThe system consists of the following components...",
    "usage": {
        "prompt_tokens": 300,
        "completion_tokens": 500,
        "total_tokens": 800
    }
}
```

## CodeAnalyzer Mocks

### Pattern Recognition Mock

```python
# Example mock return structure
mock_analyze_pattern_response = {
    "patterns_found": [
        {"name": "Singleton", "location": "src/main.py:10-25", "description": "Implementation of Singleton pattern"},
        {"name": "Factory", "location": "src/factory.py:15-45", "description": "Implementation of Factory pattern"}
    ],
    "usage": {
        "prompt_tokens": 200,
        "completion_tokens": 150,
        "total_tokens": 350
    }
}
```

### Complexity Analysis Mock

```python
# Example mock return structure
mock_analyze_complexity_response = {
    "complexity": {
        "cyclomatic": 8,
        "cognitive": 12,
        "maintainability_index": 65
    },
    "suggestions": [
        "Break down the method into smaller functions",
        "Simplify nested conditionals"
    ],
    "usage": {
        "prompt_tokens": 180,
        "completion_tokens": 120,
        "total_tokens": 300
    }
}
```

## File Enhancer Mocks

### File Enhancement Mock

```python
# Example mock return structure
mock_enhance_response = {
    "enhanced_content": "# Enhanced Source Code\n\n```python\ndef example():\n    \"\"\"This function does X by implementing Y algorithm.\"\"\"\n    pass\n```",
    "usage": {
        "prompt_tokens": 220,
        "completion_tokens": 180,
        "total_tokens": 400
    }
}
```

## Pipeline Results Structure

When mocking the entire pipeline, use this structure:

```python
mock_pipeline_results = {
    "enhancement": {
        "files_processed": 5,
        "enhanced_files": 5,
        "failed_files": 0,
        "total_tokens_used": 2000
    },
    "analysis": {
        "files_analyzed": 5,
        "patterns_identified": 10,
        "complexity_analyses": 5,
        "total_tokens_used": 1500
    },
    "supplementary": {
        "faqs_generated": 2,
        "tutorials_generated": 1,
        "diagrams_generated": 1,
        "total_tokens_used": 3000
    },
    "stats": {
        "total_files": 5,
        "total_tokens": 6500,
        "execution_time": 45.5
    }
}
```

## Best Practices for Mocking

1. **Always mock at the method level** for precise control
2. **Include all expected fields** in the mock response
3. **Verify the mock was called** with expected arguments
4. **Use reasonable values** that mimic real-world responses
5. **Document any changes** to expected structures 