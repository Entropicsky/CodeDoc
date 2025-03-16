# Class `BaseProcessor`

**Lines:** 196-230

**Inherits from:** `abc.ABC`

Abstract base class for all processors.

This class demonstrates abstract methods and class-level docstrings.

## Class Methods

### `create`

```python
def create(self) -> 'BaseProcessor'
```

Factory method to create a processor.

Args:
    config: Configuration dictionary
    
Returns:
    A processor instance

#### Parameters

- `config`: `Dict`: Configuration dictionary

#### Returns

`'BaseProcessor'`

## Methods

### `process`

```python
def process(self) -> Any
```

Process the given data.

Args:
    data: Data to process
    
Returns:
    Processed data

#### Parameters

- `data`: `Any`: Data to process

#### Returns

`Any`

