# Module `sample`

**File:** `/Users/stewchisam/CodeDoc/examples/../codedoc/tests/fixtures/python/sample.py`

Sample Python module for testing the parser.

This module contains various Python features that the parser should handle:
- Functions with different parameter types
- Classes with inheritance
- Decorators
- Type annotations
- Docstrings in different formats
- Various import styles

## Imports

```python
import os
import sys
import abc
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, field
import yaml
from .. import utils
from .constants import DEFAULT_VALUE
```

## Variables

### `DEBUG` = `os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')`

### `MAX_ITEMS` = `100`

### `VERSION` = `'1.0.0'`

## Classes

### [`Item`](../../../../../../../Item.md)

Base class for all items.

#### Methods

- `def __init__(self, value: float)`
- `def __str__(self) -> str`
- `def get_value(self) -> float`

### [`SpecialItem`](../../../../../../../SpecialItem.md)

Inherits from: `Item`

A special item with additional properties.

#### Methods

- `def __init__(self, value: float, special: bool)`
- `def get_value(self) -> float`

### [`Configuration`](../../../../../../../Configuration.md)

Configuration class using dataclass.

#### Methods

- `def is_valid(self) -> bool`

### [`BaseProcessor`](../../../../../../../BaseProcessor.md)

Inherits from: `abc.ABC`

Abstract base class for all processors.

#### Methods

- `def process(self) -> Any`
- `def create(self) -> 'BaseProcessor'`

### [`DefaultProcessor`](../../../../../../../DefaultProcessor.md)

Inherits from: `BaseProcessor`

Default implementation of BaseProcessor.

#### Methods

- `def __init__(self)`
- `def process(self) -> Any`

### [`SpecialProcessor`](../../../../../../../SpecialProcessor.md)

Inherits from: `BaseProcessor`

Special implementation of BaseProcessor with decorators.

#### Methods

- `def __init__(self)`
- `def name(self) -> str`
- `def get_version(self) -> str`
- `def from_config_file(self) -> 'SpecialProcessor'`
- `def process(self) -> Any`

## Functions

### [`calculate_sum`](../../../../../../../calculate_sum.md)

```python
def calculate_sum(a: int, b: int) -> int
```

Calculate the sum of two integers.

### [`process_data`](../../../../../../../process_data.md)

```python
def process_data(data: List[Dict[str, Any]], max_items: Optional[int] = None, process_all: bool = False, callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Tuple[List[Dict[str, Any]], int]
```

Process a list of data items.

### [`complex_function`](../../../../../../../complex_function.md)

```python
def complex_function(items: List[Item], config: Optional[Configuration] = None, processors: Optional[List[BaseProcessor]] = None) -> Dict[str, Any]
```

Process a list of items using the specified configuration and processors.

