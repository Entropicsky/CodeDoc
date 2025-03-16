# Function `process_data`

**Lines:** 54-103

## Signature

```python
def process_data(data: List[Dict[str, Any]], max_items: Optional[int] = None, process_all: bool = False, callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Tuple[List[Dict[str, Any]], int]
```

## Description

Process a list of data items.

This function demonstrates:
- Complex type annotations
- Default parameter values
- Optional parameters
- Callable type hints

Parameters:
    data: List of data items to process
    max_items: Maximum number of items to process (None for all)
    process_all: Whether to process all items regardless of max_items
    callback: Optional callback function to call for each item

Returns:
    Tuple containing:
    - List of processed items
    - Count of processed items

Raises:
    ValueError: If data is empty

## Parameters

### `data`: `List`

### `max_items`: `Optional` = `None`

### `process_all`: `bool` = `False`

### `callback`: `Optional` = `None`

## Returns

`Tuple[List[Dict[str, Any]], int]`

## Raises

### `ValueError`

If data is empty

