"""
Fibonacci Sequence Demonstrations

This module demonstrates various ways to generate and work with the Fibonacci sequence.
The Fibonacci sequence is a series where each number is the sum of the two preceding ones:
0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, ...
"""


def fibonacci_recursive(n: int) -> int:
    """
    Calculate the nth Fibonacci number using recursion.
    
    Args:
        n: Position in the Fibonacci sequence (0-indexed)
        
    Returns:
        The nth Fibonacci number
        
    Note:
        This is inefficient for large n due to repeated calculations.
        Time complexity: O(2^n)
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_iterative(n: int) -> int:
    """
    Calculate the nth Fibonacci number using iteration.
    
    Args:
        n: Position in the Fibonacci sequence (0-indexed)
        
    Returns:
        The nth Fibonacci number
        
    Note:
        Much more efficient than recursive approach.
        Time complexity: O(n), Space complexity: O(1)
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    
    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    return curr


def fibonacci_generator(count: int):
    """
    Generate Fibonacci sequence up to count numbers.
    
    Args:
        count: Number of Fibonacci numbers to generate
        
    Yields:
        Next Fibonacci number in sequence
        
    Example:
        >>> list(fibonacci_generator(10))
        [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    """
    if count < 0:
        raise ValueError("count must be non-negative")
    
    a, b = 0, 1
    for _ in range(count):
        yield a
        a, b = b, a + b


def fibonacci_memoized(n: int, memo: dict = None) -> int:
    """
    Calculate the nth Fibonacci number using memoization.
    
    Args:
        n: Position in the Fibonacci sequence (0-indexed)
        memo: Dictionary to store previously calculated values
        
    Returns:
        The nth Fibonacci number
        
    Note:
        Combines recursion elegance with iteration efficiency.
        Time complexity: O(n), Space complexity: O(n)
    """
    if memo is None:
        memo = {}
    
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    if n in memo:
        return memo[n]
    
    memo[n] = fibonacci_memoized(n - 1, memo) + fibonacci_memoized(n - 2, memo)
    return memo[n]


def fibonacci_sequence(count: int) -> list[int]:
    """
    Generate a list of Fibonacci numbers.
    
    Args:
        count: Number of Fibonacci numbers to generate
        
    Returns:
        List of Fibonacci numbers
    """
    return list(fibonacci_generator(count))


def is_fibonacci(num: int) -> bool:
    """
    Check if a number is a Fibonacci number.
    
    A number is Fibonacci if one or both of (5*n^2 + 4) or (5*n^2 - 4) is a perfect square.
    
    Args:
        num: Number to check
        
    Returns:
        True if num is a Fibonacci number, False otherwise
    """
    if num < 0:
        return False
    
    def is_perfect_square(n: int) -> bool:
        root = int(n ** 0.5)
        return root * root == n
    
    return is_perfect_square(5 * num * num + 4) or is_perfect_square(5 * num * num - 4)


def main():
    """Demonstrate various Fibonacci implementations."""
    print("=" * 60)
    print("FIBONACCI SEQUENCE DEMONSTRATIONS")
    print("=" * 60)
    
    # Generate sequence using generator
    print("\n1. First 15 Fibonacci numbers (using generator):")
    fib_list = list(fibonacci_generator(15))
    print(f"   {fib_list}")
    
    # Calculate specific positions
    print("\n2. Specific positions (using iterative method):")
    for i in [10, 15, 20]:
        print(f"   F({i}) = {fibonacci_iterative(i)}")
    
    # Compare recursive vs iterative for small n
    print("\n3. Recursive vs Iterative (n=10):")
    n = 10
    print(f"   Recursive: F({n}) = {fibonacci_recursive(n)}")
    print(f"   Iterative: F({n}) = {fibonacci_iterative(n)}")
    print(f"   Memoized:  F({n}) = {fibonacci_memoized(n)}")
    
    # Check if numbers are Fibonacci numbers
    print("\n4. Checking if numbers are in Fibonacci sequence:")
    test_numbers = [0, 1, 8, 13, 15, 21, 34, 35, 89]
    for num in test_numbers:
        result = "✓" if is_fibonacci(num) else "✗"
        print(f"   {num:3d}: {result}")
    
    # Generate larger Fibonacci numbers
    print("\n5. Larger Fibonacci numbers:")
    for i in [30, 40, 50]:
        print(f"   F({i}) = {fibonacci_iterative(i):,}")
    
    # Golden ratio approximation
    print("\n6. Golden Ratio (φ) approximation:")
    print("   The ratio of consecutive Fibonacci numbers approaches φ ≈ 1.618...")
    for i in range(10, 21):
        fib_i = fibonacci_iterative(i)
        fib_i_plus_1 = fibonacci_iterative(i + 1)
        ratio = fib_i_plus_1 / fib_i
        print(f"   F({i+1})/F({i}) = {fib_i_plus_1}/{fib_i} = {ratio:.10f}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
