"""
Thirsty-Lang Tracks 4-6 Tests
Test suite for Database, Package Registry, and LSP modules
"""

import sys
import os
import tempfile

# Add modules to path
test_dir = os.path.dirname(__file__)
sys.path.insert(0, test_dir)

from tarl_db_interface import QueryBuilder
from tarl_db_sqlite import SQLiteDatabase
from tarl_package import Package, PackageVersion, Registry, DependencyResolver
from tarl_lsp import LSPServer, TarlFormatter


def test_sqlite_database():
    """Test SQLite database operations"""
    print("Testing SQLite Database...")
    
    # Create in-memory database
    db = SQLiteDatabase(':memory:')
    
    # Create table
    db.create_table('users', 'id INTEGER PRIMARY KEY, name TEXT, age INTEGER')
    
    # Insert
    user_id = db.insert('users', {'name': 'Alice', 'age': 30})
    assert user_id == 1
    
    # Select
    users = db.select('users')
    assert len(users) == 1
    assert users[0]['name'] == 'Alice'
    
    # Update
    db.update('users', {'age': 31}, 'id = 1')
    users = db.select('users', 'id = 1')
    assert users[0]['age'] == 31
    
    # Delete
    db.delete('users', 'id = 1')
    users = db.select('users')
    assert len(users) == 0
    
    db.close()
    print("✓ SQLite Database tests passed")


def test_query_builder():
    """Test SQL query builder"""
    print("Testing Query Builder...")
    
    # SELECT query
    query = QueryBuilder('users')\
        .select('name', 'age')\
        .where('age > 18')\
        .order_by('name')\
        .limit(10)\
        .build()
    
    assert 'SELECT name, age FROM users' in query
    assert 'WHERE age > 18' in query
    assert 'ORDER BY name' in query
    assert 'LIMIT 10' in query
    
    # INSERT query
    query, params = QueryBuilder.insert('users', {'name': 'Bob', 'age': 25})
    assert 'INSERT INTO users' in query
    assert params == ('Bob', 25)
    
    print("✓ Query Builder tests passed")


def test_package_registry():
    """Test package registry and dependency resolution"""
    print("Testing Package Registry...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create registry
        registry = Registry(tmpdir)
        
        # Create packages
        pkg_a = Package(
            name='package-a',
            version=PackageVersion(1, 0, 0),
            dependencies={'package-b': '>=1.0.0'}
        )
        
        pkg_b = Package(
            name='package-b',
            version=PackageVersion(1, 2, 0),
            dependencies={}
        )
        
        # Create dummy package files
        pkg_file_a = os.path.join(tmpdir, 'pkg_a.tpkg')
        pkg_file_b = os.path.join(tmpdir, 'pkg_b.tpkg')
        open(pkg_file_a, 'w').close()
        open(pkg_file_b, 'w').close()
        
        # Publish packages
        registry.publish(pkg_b, pkg_file_b)
        registry.publish(pkg_a, pkg_file_a)
        
        # Find package
        found = registry.find_package('package-a', '*')
        assert found is not None
        assert found.name == 'package-a'
        
        # Resolve dependencies
        resolver = DependencyResolver(registry)
        resolved = resolver.resolve('package-a')
        
        # Should resolve to [package-b, package-a] in order
        assert len(resolved) == 2
        assert resolved[0].name == 'package-b'
        assert resolved[1].name == 'package-a'
    
    print("✓ Package Registry tests passed")


def test_semantic_versioning():
    """Test semantic versioning"""
    print("Testing Semantic Versioning...")
    
    v1 = PackageVersion(1, 2, 3)
    v2 = PackageVersion(1, 3, 0)
    v3 = PackageVersion(2, 0, 0)
    
    # Comparison
    assert v1 < v2
    assert v2 < v3
    
    # Satisfies
    assert v1.satisfies('>=1.0.0')
    assert v1.satisfies('~1.2.0')  # ~1.2.0 = >=1.2.0 <1.3.0
    assert not v1.satisfies('~1.3.0')
    assert v1.satisfies('^1.0.0')  # ^1.0.0 = >=1.0.0 <2.0.0
    assert not v3.satisfies('^1.0.0')
    
    print("✓ Semantic Versioning tests passed")


def test_lsp_server():
    """Test LSP server"""
    print("Testing LSP Server...")
    
    lsp = LSPServer()
    
    # Initialize
    result = lsp.initialize({'processId': 1234})
    assert 'capabilities' in result
    
    # Open document with error
    code_with_error = """
def hello()
    print("Missing colon")
"""
    diagnostics = lsp.open_document('file:///test.py', code_with_error)
    assert len(diagnostics) > 0
    assert 'colon' in diagnostics[0]['message'].lower()
    
    # Get completions
    code = "def foo():\n    x = 10\n    "
    lsp.update_document('file:///test.py', code)
    completions = lsp.get_completions('file:///test.py', {'line': 2, 'character': 4})
    assert len(completions) > 0
    
    # Some completions should include keywords
    labels = [c['label'] for c in completions]
    assert 'if' in labels or 'for' in labels
    
    print("✓ LSP Server tests passed")


def test_code_formatter():
    """Test code formatter"""
    print("Testing Code Formatter...")
    
    unformatted = """
def hello():
print("Bad indent")
if True:
return 42
"""
    
    formatted = TarlFormatter.format(unformatted)
    
    # Check that indentation is fixed
    assert '    print("Bad indent")' in formatted
    assert '    if True:' in formatted
    
    print("✓ Code Formatter tests passed")


def run_all_tests():
    """Run all Track 4-6 tests"""
    print("\n" + "="*50)
    print("THIRSTY-LANG TRACKS 4-6 TEST SUITE")
    print("Database, Registry, LSP")
    print("="*50 + "\n")
    
    try:
        test_sqlite_database()
        test_query_builder()
        test_package_registry()
        test_semantic_versioning()
        test_lsp_server()
        test_code_formatter()
        
        print("\n" + "="*50)
        print("✓ ALL TRACKS 4-6 TESTS PASSED")
        print("="*50)
        return True
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
