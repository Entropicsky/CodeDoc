# Class `Configuration`

**Lines:** 172-192

**Decorators:**
```python
@dataclass
```

Configuration class using dataclass.

Attributes:
    name: Configuration name
    enabled: Whether the configuration is enabled
    values: Dictionary of configuration values
    options: List of configuration options

## Class Variables

### `name`: `str`

### `enabled`: `bool` = `True`

### `values`: `Dict` = `field(...)`

### `options`: `List` = `field(...)`

## Methods

### `is_valid`

```python
def is_valid(self) -> bool
```

Check if the configuration is valid.

Returns:
    True if the configuration is valid, False otherwise

#### Returns

`bool`

