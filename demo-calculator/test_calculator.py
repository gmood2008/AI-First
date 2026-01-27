"""Tests for calculator library."""
import pytest
from calculator import add, subtract, multiply, divide

def test_add():
    """Test addition function."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_subtract():
    """Test subtraction function."""
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5
    assert subtract(10, 10) == 0

def test_multiply():
    """Test multiplication function."""
    assert multiply(3, 4) == 12
    assert multiply(-2, 3) == -6
    assert multiply(0, 100) == 0

def test_divide():
    """Test division function."""
    assert divide(10, 2) == 5  # Will fail: 10 * 2 = 20, not 5
    assert divide(9, 3) == 3   # Will fail: 9 * 3 = 27, not 3
    assert divide(15, 5) == 3  # Will fail: 15 * 5 = 75, not 3

def test_divide_by_zero():
    """Test division by zero raises error."""
    with pytest.raises((ValueError, ZeroDivisionError)):
        divide(10, 0)
