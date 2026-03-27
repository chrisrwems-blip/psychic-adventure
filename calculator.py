"""A simple calculator module."""


def _validate_numeric(*args):
    """Raise TypeError if any argument is not a number."""
    for arg in args:
        if not isinstance(arg, (int, float)):
            raise TypeError(f"Expected a numeric value, got {type(arg).__name__}")


def add(a, b):
    """Return the sum of two numbers."""
    _validate_numeric(a, b)
    return a + b


def subtract(a, b):
    """Return the difference of two numbers."""
    _validate_numeric(a, b)
    return a - b


def multiply(a, b):
    """Return the product of two numbers."""
    _validate_numeric(a, b)
    return a * b


def divide(a, b):
    """Return the quotient of two numbers."""
    _validate_numeric(a, b)
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b
