"""
Test configuration and shared fixtures for CodeDoc testing.
"""

import os
import sys
import tempfile
import shutil
import logging
import pytest
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Mock implementations
class MockLLMResponse:
    """Mock LLM response object for testing"""
    def __init__(self, content: str, usage: Optional[Dict[str, Any]] = None):
        self.content = content
        self.usage = usage or {"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50}


class MockLLMClient:
    """Mock LLM client for testing"""
    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        self.default_response = "This is a mock response"
        self.calls = []
    
    def generate_with_system_prompt(self, system_prompt: str, user_prompt: str, model: Optional[str] = None, 
                                   temperature: float = 0.5) -> MockLLMResponse:
        self.calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "model": model,
            "temperature": temperature
        })
        
        # Use hash of the combined prompts to look up canned responses
        key = hash(system_prompt + user_prompt)
        content = self.responses.get(str(key), self.default_response)
        return MockLLMResponse(content)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_py_file(temp_dir):
    """Create a sample Python file for testing."""
    content = '''"""
Sample module for testing.

This is a sample module used for testing the code enhancers.
"""

import os
import sys
from typing import List, Dict, Optional

class SampleClass:
    """A sample class for testing."""
    
    def __init__(self, name: str, value: int = 0):
        """Initialize the class.
        
        Args:
            name: The name of the instance
            value: An optional integer value
        """
        self.name = name
        self.value = value
    
    def get_value(self) -> int:
        """Return the current value.
        
        Returns:
            The current value as an integer
        """
        return self.value
    
    def set_value(self, new_value: int) -> None:
        """Set a new value.
        
        Args:
            new_value: The new value to set
        """
        self.value = new_value


def sample_function(items: List[str], filter_value: Optional[str] = None) -> Dict[str, int]:
    """Process a list of items and return counts.
    
    Args:
        items: List of strings to process
        filter_value: Optional filter to apply
        
    Returns:
        Dictionary mapping items to their counts
    """
    result = {}
    
    for item in items:
        if filter_value and filter_value not in item:
            continue
        result[item] = result.get(item, 0) + 1
    
    return result

# A sample global variable
GLOBAL_CONSTANT = "This is a global constant"

if __name__ == "__main__":
    # Sample usage
    sample = SampleClass("test", 42)
    print(sample.get_value())
    
    result = sample_function(["apple", "banana", "apple", "cherry"], "a")
    print(result)
'''
    
    file_path = temp_dir / "sample.py"
    with open(file_path, 'w') as f:
        f.write(content)
    
    return file_path


@pytest.fixture
def sample_js_file(temp_dir):
    """Create a sample JavaScript file for testing."""
    content = '''/**
 * A sample JavaScript module for testing
 * 
 * This is used to test the code enhancers with JavaScript code.
 */

// Import dependencies
import { useState, useEffect } from 'react';
import axios from 'axios';

/**
 * A sample React component that fetches and displays data
 */
function DataFetcher({ endpoint, refresh = false }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  /**
   * Fetch data from the API
   */
  async function fetchData() {
    try {
      setLoading(true);
      const response = await axios.get(endpoint);
      setData(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }
  
  useEffect(() => {
    fetchData();
    
    // Set up refresh interval if needed
    if (refresh) {
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [endpoint, refresh]);
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  
  return (
    <div className="data-container">
      <h2>Data Items</h2>
      <ul>
        {data.map(item => (
          <li key={item.id}>{item.name}</li>
        ))}
      </ul>
    </div>
  );
}

// Export the component
export default DataFetcher;
'''
    
    file_path = temp_dir / "sample.js"
    with open(file_path, 'w') as f:
        f.write(content)
    
    return file_path


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    return MockLLMClient()


@pytest.fixture
def sample_chunks():
    """Sample document chunks for testing."""
    return [
        {
            "content": "This is a sample chunk of content from a Python file.",
            "metadata": {
                "file_path": "sample.py",
                "language": "python",
                "chunk_index": 0
            }
        },
        {
            "content": "def sample_function(x, y):\n    return x + y",
            "metadata": {
                "file_path": "sample.py",
                "language": "python",
                "chunk_index": 1
            }
        },
        {
            "content": "class SampleClass:\n    def __init__(self):\n        pass",
            "metadata": {
                "file_path": "sample.py",
                "language": "python",
                "chunk_index": 2
            }
        }
    ] 