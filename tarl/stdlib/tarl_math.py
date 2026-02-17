"""
Thirsty-Lang Standard Library: Math
Extended mathematical operations including statistics

Provides:
- Basic operations: abs, sign, clamp
- Statistics: mean, median, mode, stdev, variance
- Advanced: GCD, LCM, factorial, combinations, permutations
"""

import math as py_math


class Math:
    """Extended mathematical operations"""
    
    # Constants
    PI = py_math.pi
    E = py_math.e
    TAU = py_math.tau
    INF = py_math.inf
    NAN = py_math.nan
    
    # Basic operations
    @staticmethod
    def abs(x):
        """Absolute value"""
        return abs(x)
    
    @staticmethod
    def sign(x):
        """Sign of number: -1, 0, or 1"""
        if x > 0:
            return 1
        elif x < 0:
            return -1
        return 0
    
    @staticmethod
    def clamp(x, min_val, max_val):
        """Clamp value between min and max"""
        return max(min_val, min(max_val, x))
    
    # Power and roots
    @staticmethod
    def pow(x, y):
        """x raised to power y"""
        return x ** y
    
    @staticmethod
    def sqrt(x):
        """Square root"""
        return py_math.sqrt(x)
    
    @staticmethod
    def cbrt(x):
        """Cube root"""
        return x ** (1/3)
    
    # Rounding
    @staticmethod
    def floor(x):
        """Round down to integer"""
        return py_math.floor(x)
    
    @staticmethod
    def ceil(x):
        """Round up to integer"""
        return py_math.ceil(x)
    
    @staticmethod
    def round(x, digits=0):
        """Round to nearest with digits precision"""
        return round(x, digits)
    
    # Min/Max
    @staticmethod
    def min(*args):
        """Minimum value"""
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            return min(args[0])
        return min(args)
    
    @staticmethod
    def max(*args):
        """Maximum value"""
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            return max(args[0])
        return max(args)
    
    # Trigonometry
    @staticmethod
    def sin(x):
        return py_math.sin(x)
    
    @staticmethod
    def cos(x):
        return py_math.cos(x)
    
    @staticmethod
    def tan(x):
        return py_math.tan(x)
    
    @staticmethod
    def asin(x):
        return py_math.asin(x)
    
    @staticmethod
    def acos(x):
        return py_math.acos(x)
    
    @staticmethod
    def atan(x):
        return py_math.atan(x)
    
    @staticmethod
    def atan2(y, x):
        return py_math.atan2(y, x)
    
    # Logarithms
    @staticmethod
    def log(x, base=py_math.e):
        """Logarithm with optional base"""
        return py_math.log(x, base)
    
    @staticmethod
    def log10(x):
        return py_math.log10(x)
    
    @staticmethod
    def log2(x):
        return py_math.log2(x)
    
    # Statistics
    @staticmethod
    def mean(numbers):
        """Arithmetic mean (average)"""
        if not numbers:
            raise ValueError("mean requires at least one number")
        return sum(numbers) / len(numbers)
    
    @staticmethod
    def median(numbers):
        """Middle value when sorted"""
        if not numbers:
            raise ValueError("median requires at least one number")
        sorted_nums = sorted(numbers)
        n = len(sorted_nums)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2
        return sorted_nums[mid]
    
    @staticmethod
    def mode(numbers):
        """Most common value"""
        if not numbers:
            raise ValueError("mode requires at least one number")
        # Manual frequency counting to avoid import conflict
        counts = {}
        for num in numbers:
            counts[num] = counts.get(num, 0) + 1
        max_count = max(counts.values())
        modes = [num for num, count in counts.items() if count == max_count]
        return modes[0] if len(modes) == 1 else modes
    
    @staticmethod
    def variance(numbers, sample=True):
        """Variance of numbers"""
        if len(numbers) < 2:
            raise ValueError("variance requires at least two numbers")
        mean_val = Math.mean(numbers)
        squared_diffs = [(x - mean_val) ** 2 for x in numbers]
        n = len(numbers) - 1 if sample else len(numbers)
        return sum(squared_diffs) / n
    
    @staticmethod
    def stdev(numbers, sample=True):
        """Standard deviation"""
        return Math.sqrt(Math.variance(numbers, sample))
    
    # Combinatorics
    @staticmethod
    def factorial(n):
        """Factorial of n"""
        if n < 0:
            raise ValueError("factorial not defined for negative numbers")
        return py_math.factorial(n)
    
    @staticmethod
    def gcd(*args):
        """Greatest common divisor"""
        if len(args) == 0:
            raise ValueError("gcd requires at least one argument")
        if len(args) == 1:
            return args[0]
        result = args[0]
        for num in args[1:]:
            result = py_math.gcd(result, num)
        return result
    
    @staticmethod
    def lcm(*args):
        """Least common multiple"""
        if len(args) == 0:
            raise ValueError("lcm requires at least one argument")
        if len(args) == 1:
            return args[0]
        result = args[0]
        for num in args[1:]:
            result = abs(result * num) // py_math.gcd(result, num)
        return result
    
    @staticmethod
    def combinations(n, r):
        """Number of combinations: n choose r"""
        return Math.factorial(n) // (Math.factorial(r) * Math.factorial(n - r))
    
    @staticmethod
    def permutations(n, r=None):
        """Number of permutations"""
        if r is None:
            r = n
        return Math.factorial(n) // Math.factorial(n - r)


# Export Math class
__all__ = ['Math']
