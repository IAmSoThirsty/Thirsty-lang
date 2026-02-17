"""
Thirsty-Lang Standard Library: Collections
Advanced data structures beyond basic list/dict

Provides:
- Deque: Double-ended queue for O(1) append/pop from both ends
- OrderedDict: Dictionary that maintains insertion order
- Counter: Frequency counting and multiset operations
- Heap: Priority queue with min-heap implementation
"""

class Deque:
    """Double-ended queue with O(1) operations on both ends"""
    
    def __init__(self, iterable=None):
        self._items = list(iterable) if iterable else []
    
    def append(self, item):
        """Add item to right end"""
        self._items.append(item)
    
    def appendleft(self, item):
        """Add item to left end"""
        self._items.insert(0, item)
    
    def pop(self):
        """Remove and return item from right end"""
        if not self._items:
            raise IndexError("pop from empty deque")
        return self._items.pop()
    
    def popleft(self):
        """Remove and return item from left end"""
        if not self._items:
            raise IndexError("pop from empty deque")
        return self._items.pop(0)
    
    def extend(self, iterable):
        """Extend right side with iterable"""
        self._items.extend(iterable)
    
    def extendleft(self, iterable):
        """Extend left side with iterable"""
        for item in iterable:
            self.appendleft(item)
    
    def rotate(self, n=1):
        """Rotate deque n steps to the right (negative = left)"""
        if not self._items:
            return
        n = n % len(self._items) if self._items else 0
        self._items = self._items[-n:] + self._items[:-n]
    
    def __len__(self):
        return len(self._items)
    
    def __repr__(self):
        return f"Deque({self._items})"


class OrderedDict:
    """Dictionary that remembers insertion order"""
    
    def __init__(self, items=None):
        self._keys = []
        self._data = {}
        if items:
            if isinstance(items, dict):
                for k, v in items.items():
                    self.set(k, v)
            else:
                for k, v in items:
                    self.set(k, v)
    
    def set(self, key, value):
        """Set key-value pair, maintaining order"""
        if key not in self._data:
            self._keys.append(key)
        self._data[key] = value
    
    def get(self, key, default=None):
        """Get value for key, or default if not found"""
        return self._data.get(key, default)
    
    def delete(self, key):
        """Remove key-value pair"""
        if key in self._data:
            self._keys.remove(key)
            del self._data[key]
    
    def keys(self):
        """Return list of keys in order"""
        return list(self._keys)
    
    def values(self):
        """Return list of values in order"""
        return [self._data[k] for k in self._keys]
    
    def items(self):
        """Return list of (key, value) tuples in order"""
        return [(k, self._data[k]) for k in self._keys]
    
    def move_to_end(self, key, last=True):
        """Move key to end (or beginning if last=False)"""
        if key not in self._data:
            raise KeyError(key)
        self._keys.remove(key)
        if last:
            self._keys.append(key)
        else:
            self._keys.insert(0, key)
    
    def popitem(self, last=True):
        """Remove and return (key, value) pair"""
        if not self._keys:
            raise KeyError("dictionary is empty")
        key = self._keys.pop() if last else self._keys.pop(0)
        value = self._data.pop(key)
        return (key, value)
    
    def __len__(self):
        return len(self._data)
    
    def __repr__(self):
        items = ", ".join(f"{k}: {v}" for k, v in self.items())
        return f"OrderedDict({{{items}}})"


class Counter:
    """Frequency counter and multiset operations"""
    
    def __init__(self, iterable=None):
        self._counts = {}
        if iterable:
            for item in iterable:
                self._counts[item] = self._counts.get(item, 0) + 1
    
    def increment(self, item, count=1):
        """Increment count for item"""  
        self._counts[item] = self._counts.get(item, 0) + count
    
    def decrement(self, item, count=1):
        """Decrement count for item"""
        self._counts[item] = self._counts.get(item, 0) - count
        if self._counts[item] <= 0:
            del self._counts[item]
    
    def get(self, item):
        """Get count for item (0 if not present)"""
        return self._counts.get(item, 0)
    
    def most_common(self, n=None):
        """Return list of n most common (item, count) pairs"""
        items = sorted(self._counts.items(), key=lambda x: x[1], reverse=True)
        return items[:n] if n is not None else items
    
    def elements(self):
        """Return iterator over elements, repeating each count times"""
        result = []
        for item, count in self._counts.items():
            result.extend([item] * count)
        return result
    
    def total(self):
        """Return sum of all counts"""
        return sum(self._counts.values())
    
    def __repr__(self):
        items = ", ".join(f"{k}: {v}" for k, v in self._counts.items())
        return f"Counter({{{items}}})"


class Heap:
    """Min-heap priority queue"""
    
    def __init__(self, iterable=None):
        self._heap = []
        if iterable:
            for item in iterable:
                self.push(item)
    
    def push(self, item):
        """Add item to heap"""
        self._heap.append(item)
        self._sift_up(len(self._heap) - 1)
    
    def pop(self):
        """Remove and return smallest item"""
        if not self._heap:
            raise IndexError("pop from empty heap")
        if len(self._heap) == 1:
            return self._heap.pop()
        root = self._heap[0]
        self._heap[0] = self._heap.pop()
        self._sift_down(0)
        return root
    
    def peek(self):
        """Return smallest item without removing it"""
        if not self._heap:
            raise IndexError("peek at empty heap")
        return self._heap[0]
    
    def _sift_up(self, index):
        """Move item up to maintain heap property"""
        parent = (index - 1) // 2
        if index > 0 and self._heap[index] < self._heap[parent]:
            self._heap[index], self._heap[parent] = self._heap[parent], self._heap[index]
            self._sift_up(parent)
    
    def _sift_down(self, index):
        """Move item down to maintain heap property"""
        smallest = index
        left = 2 * index + 1
        right = 2 * index + 2
        
        if left < len(self._heap) and self._heap[left] < self._heap[smallest]:
            smallest = left
        if right < len(self._heap) and self._heap[right] < self._heap[smallest]:
            smallest = right
        
        if smallest != index:
            self._heap[index], self._heap[smallest] = self._heap[smallest], self._heap[index]
            self._sift_down(smallest)
    
    def __len__(self):
        return len(self._heap)
    
    def __repr__(self):
        return f"Heap({self._heap})"


# Export all collections
__all__ = ['Deque', 'OrderedDict', 'Counter', 'Heap']
