# Class `SpecialItem`

**Lines:** 138-167

**Inherits from:** `Item`

A special item with additional properties.

This class demonstrates inheritance and method overrides.

Attributes:
    name: The name of the item
    value: The value of the item
    special: Whether the item is special

## Constructor

### `__init__`

```python
def __init__(self, value: float, special: bool)
```

Initialize the special item.

Args:
    name: The name of the item
    value: The value of the item
    special: Whether the item is special

#### Parameters

- `name`: `str`: The name of the item
- `value`: `float`: The value of the item
- `special`: `bool`: Whether the item is special

## Methods

### `get_value`

```python
def get_value(self) -> float
```

Get the item's value with a special multiplier.

Returns:
    The value of the item multiplied by 2 if special

#### Returns

`float`

