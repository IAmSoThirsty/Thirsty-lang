"""
Thirsty-Lang Standard Library (__init__)
Central import point for all stdlib modules

Usage:
    from tarl.stdlib import tarl_collections, tarl_itertools, tarl_datetime, tarl_math
    
    # Or import specific classes
    from tarl.stdlib.tarl_collections import Deque, Counter
    from tarl.stdlib.tarl_datetime import DateTime
"""

# Import all stdlib modules
from . import tarl_collections
from . import tarl_itertools
from . import tarl_datetime
from . import tarl_math

# Re-export commonly used classes for convenience
from .tarl_collections import Deque, OrderedDict, Counter, Heap
from .tarl_itertools import Itertools
from .tarl_datetime import DateTime, TimeDelta, Timezone
from .tarl_math import Math

__all__ = [
    # Modules
    'tarl_collections',
    'tarl_itertools', 
    'tarl_datetime',
    'tarl_math',
    # Classes
    'Deque',
    'OrderedDict',
    'Counter',
    'Heap',
    'Itertools',
    'DateTime',
    'TimeDelta',
    'Timezone',
    'Math',
]

__version__ = '1.0.0'
