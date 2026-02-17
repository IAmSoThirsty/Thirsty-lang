"""
Thirsty-Lang Standard Library Tests
Comprehensive test suite for stdlib modules
"""

import sys
import os

# Add parent to path for testing
test_dir = os.path.dirname(__file__)
sys.path.insert(0, test_dir)

# Direct imports from local modules
import tarl_collections
import tarl_itertools
import tarl_datetime
import tarl_math

# Extract classes
Deque = tarl_collections.Deque
OrderedDict = tarl_collections.OrderedDict
Counter = tarl_collections.Counter
Heap = tarl_collections.Heap
Itertools = tarl_itertools.Itertools
DateTime = tarl_datetime.DateTime
TimeDelta = tarl_datetime.TimeDelta
Timezone = tarl_datetime.Timezone
Math = tarl_math.Math


def test_deque():
    """Test Deque operations"""
    print("Testing Deque...")
    d = Deque([1, 2, 3])
    d.append(4)
    d.appendleft(0)
    assert list(d._items) == [0, 1, 2, 3, 4], f"Expected [0,1,2,3,4], got {d._items}"
    
    assert d.pop() == 4
    assert d.popleft() == 0
    
    d.rotate(1)
    assert list(d._items) == [3, 1, 2], f"Expected [3,1,2], got {d._items}"
    print("✓ Deque tests passed")


def test_ordered_dict():
    """Test OrderedDict operations"""
    print("Testing OrderedDict...")
    od = OrderedDict()
    od.set('a', 1)
    od.set('b', 2)
    od.set('c', 3)
    
    assert od.keys() == ['a', 'b', 'c']
    assert od.values() == [1, 2, 3]
    
    od.move_to_end('a')
    assert od.keys() == ['b', 'c', 'a']
    print("✓ OrderedDict tests passed")


def test_counter():
    """Test Counter operations"""
    print("Testing Counter...")
    c = Counter(['a', 'b', 'a', 'c', 'b', 'a'])
    
    assert c.get('a') == 3
    assert c.get('b') == 2
    assert c.most_common(2) == [('a', 3), ('b', 2)]
    assert c.total() == 6
    print("✓ Counter tests passed")


def test_heap():
    """Test Heap operations"""
    print("Testing Heap...")
    h = Heap([5, 2, 8, 1, 9])
    
    assert h.peek() == 1
    assert h.pop() == 1
    assert h.pop() == 2
    
    h.push(0)
    assert h.peek() == 0
    print("✓ Heap tests passed")


def test_itertools():
    """Test Itertools utilities"""
    print("Testing Itertools...")
    
    # Map and filter
    result = Itertools.map(lambda x: x * 2, [1, 2, 3])
    assert result == [2, 4, 6]
    
    result = Itertools.filter(lambda x: x > 2, [1, 2, 3, 4])
    assert result == [3, 4]
    
    # Reduce
    result = Itertools.reduce(lambda a, b: a + b, [1, 2, 3, 4])
    assert result == 10
    
    # Zip
    result = Itertools.zip([1, 2], ['a', 'b'])
    assert result == [(1, 'a'), (2, 'b')]
    
    # Groupby
    result = Itertools.groupby([1, 1, 2, 2, 3], key=lambda x: x)
    assert result == [(1, [1, 1]), (2, [2, 2]), (3, [3])]
    print("✓ Itertools tests passed")


def test_datetime():
    """Test DateTime operations"""
    print("Testing DateTime...")
    
    # Create datetime
    dt = DateTime(2024, 1, 1, 12, 0, 0)
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 1
    
    # ISO formatting
    iso = dt.to_iso()
    dt2 = DateTime.from_iso(iso)
    assert dt2.year == dt.year
    
    # TimeDelta
    delta = TimeDelta(days=1, hours=2)
    assert delta.days == 1
    assert delta.total_seconds() == 86400 + 7200
    
    # Addition
    dt3 = dt.add(delta)
    assert dt3.day == 2
    print("✓ DateTime tests passed")


def test_math():
    """Test Math operations"""
    print("Testing Math...")
    
    # Basic
    assert Math.abs(-5) == 5
    assert Math.sign(-10) == -1
    assert Math.clamp(15, 0, 10) == 10
    
    # Statistics
    assert Math.mean([1, 2, 3, 4, 5]) == 3
    assert Math.median([1, 2, 3, 4, 5]) == 3
    assert Math.median([1, 2, 3, 4]) == 2.5
    
    # Combinatorics
    assert Math.factorial(5) == 120
    assert Math.gcd(12, 8) == 4
    assert Math.lcm(4, 6) == 12
    assert Math.combinations(5, 2) == 10
    print("✓ Math tests passed")


def run_all_tests():
    """Run all stdlib tests"""
    print("\n" + "="*50)
    print("THIRSTY-LANG STANDARD LIBRARY TEST SUITE")
    print("="*50 + "\n")
    
    try:
        test_deque()
        test_ordered_dict()
        test_counter()
        test_heap()
        test_itertools()
        test_datetime()
        test_math()
        
        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED")
        print("="*50)
        return True
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
