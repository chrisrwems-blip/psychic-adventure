"""Tests for the calculator module."""

import pytest
from calculator import add, subtract, multiply, divide


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0.1, 0.2) == pytest.approx(0.3)


def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5


def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(-2, 3) == -6
    assert multiply(0, 100) == 0


def test_divide():
    assert divide(10, 2) == 5
    assert divide(7, 2) == 3.5


def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError, match="Cannot divide by zero"):
        divide(1, 0)


def test_invalid_input():
    with pytest.raises(TypeError, match="Expected a numeric value"):
        add("a", 1)
    with pytest.raises(TypeError, match="Expected a numeric value"):
        subtract(1, None)
    with pytest.raises(TypeError, match="Expected a numeric value"):
        multiply([], 2)
    with pytest.raises(TypeError, match="Expected a numeric value"):
        divide(1, "b")
