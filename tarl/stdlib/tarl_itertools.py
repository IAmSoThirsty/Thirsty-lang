"""
Thirsty-Lang Standard Library: Itertools
Lazy iterators and functional programming utilities

Provides composable iterator functions for efficient data processing:
- map, filter, reduce
- zip, enumerate, chain
- takewhile, dropwhile, groupby
"""

class Itertools:
    """Collection of functional programming utilities"""
    
    @staticmethod
    def map(func, iterable):
        """Apply function to every item"""
        return [func(item) for item in iterable]
    
    @staticmethod
    def filter(predicate, iterable):
        """Return items where predicate is true"""
        return [item for item in iterable if predicate(item)]
    
    @staticmethod
    def reduce(func, iterable, initial=None):
        """Apply function cumulatively to items"""
        it = iter(iterable)
        if initial is None:
            try:
                value = next(it)
            except StopIteration:
                raise TypeError("reduce() of empty sequence with no initial value")
        else:
            value = initial
        
        for item in it:
            value = func(value, item)
        return value
    
    @staticmethod
    def zip(*iterables):
        """Zip multiple iterables together"""
        min_len = min(len(it) for it in iterables)
        return [tuple(it[i] for it in iterables) for i in range(min_len)]
    
    @staticmethod
    def enumerate(iterable, start=0):
        """Return (index, value) pairs"""
        return [(i + start, item) for i, item in enumerate(iterable)]
    
    @staticmethod
    def chain(*iterables):
        """Chain multiple iterables into one"""
        result = []
        for iterable in iterables:
            result.extend(iterable)
        return result
    
    @staticmethod
    def takewhile(predicate, iterable):
        """Take items while predicate is true"""
        result = []
        for item in iterable:
            if not predicate(item):
                break
            result.append(item)
        return result
    
    @staticmethod
    def dropwhile(predicate, iterable):
        """Drop items while predicate is true"""
        it = iter(iterable)
        result = []
        dropping = True
        for item in it:
            if dropping and predicate(item):
                continue
            dropping = False
            result.append(item)
        return result
    
    @staticmethod
    def groupby(iterable, key=None):
        """Group consecutive items by key function"""
        if key is None:
            key = lambda x: x
        
        groups = []
        current_key = None
        current_group = []
        
        for item in iterable:
            item_key = key(item)
            if item_key != current_key:
                if current_group:
                    groups.append((current_key, current_group))
                current_key = item_key
                current_group = [item]
            else:
                current_group.append(item)
        
        if current_group:
            groups.append((current_key, current_group))
        
        return groups
    
    @staticmethod
    def flatten(iterable):
        """Flatten one level of nesting"""
        result = []
        for item in iterable:
            if isinstance(item, (list, tuple)):
                result.extend(item)
            else:
                result.append(item)
        return result
    
    @staticmethod
    def partition(predicate, iterable):
        """Partition items into (true, false) based on predicate"""
        true_items = []
        false_items = []
        for item in iterable:
            if predicate(item):
                true_items.append(item)
            else:
                false_items.append(item)
        return (true_items, false_items)
    
    @staticmethod
    def unique(iterable):
        """Return unique items preserving order"""
        seen = set()
        result = []
        for item in iterable:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
    
    @staticmethod
    def chunks(iterable, size):
        """Split iterable into chunks of given size"""
        result = []
        for i in range(0, len(iterable), size):
            result.append(iterable[i:i + size])
        return result
    
    @staticmethod
    def pairwise(iterable):
        """Return successive overlapping pairs"""
        if len(iterable) < 2:
            return []
        return [(iterable[i], iterable[i + 1]) for i in range(len(iterable) - 1)]


# Export all functions
__all__ = ['Itertools']
