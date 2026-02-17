"""
Thirsty-Lang File I/O Tests
Test suite for Track 3 modules
"""

import sys
import os
import time

# Add modules to path
test_dir = os.path.dirname(__file__)
sys.path.insert(0, test_dir)

from tarl_path import Path
from tarl_filesystem import File, Directory, Permissions
from tarl_streams import FileStream, MemoryStream, BinaryMemoryStream
from tarl_tempfiles import TempFile, TempDir
from tarl_archives import ZipArchive, TarArchive, Archive


def test_path():
    """Test Path operations"""
    print("Testing Path...")
    
    # Create path
    p = Path('test', 'subdir', 'file.txt')
    assert 'file.txt' in str(p)
    assert p.name == 'file.txt'
    assert p.stem == 'file'
    assert p.suffix == '.txt'
    
    # Path operations
    p2 = p.with_suffix('.json')
    assert p2.suffix == '.json'
    
    # Current directory
    cwd = Path.cwd()
    assert cwd.exists()
    assert cwd.is_dir()
    
    print("✓ Path tests passed")


def test_file_operations():
    """Test File operations"""
    print("Testing File operations...")
    
    with TempDir() as tmpdir:
        test_file = os.path.join(tmpdir.name, 'test.txt')
        
        # Write text
        File.write(test_file, 'Hello, World!')
        assert File.exists(test_file)
        
        # Read text
        content = File.read(test_file)
        assert content == 'Hello, World!'
        
        # Append
        File.append(test_file, '\nLine 2')
        content = File.read(test_file)
        assert 'Line 2' in content
        
        # JSON
        json_file = os.path.join(tmpdir.name, 'data.json')
        File.write_json(json_file, {'key': 'value'})
        data = File.read_json(json_file)
        assert data['key'] == 'value'
        
        # Copy
        copy_file = os.path.join(tmpdir.name, 'copy.txt')
        File.copy(test_file, copy_file)
        assert File.exists(copy_file)
    
    print("✓ File operation tests passed")


def test_directory_operations():
    """Test Directory operations"""
    print("Testing Directory operations...")
    
    with TempDir() as tmpdir:
        # Create subdirectory
        subdir = os.path.join(tmpdir.name, 'subdir')
        Directory.create(subdir)
        assert Directory.exists(subdir)
        
        # Create files
        File.write(os.path.join(tmpdir.name, 'file1.txt'), 'test')
        File.write(os.path.join(subdir, 'file2.txt'), 'test')
        
        # List contents
        files = Directory.list_files(tmpdir.name, recursive=True)
        assert len(files) == 2
        
        # Copy directory
        copy_dir = os.path.join(tmpdir.name, 'copy')
        Directory.copy(subdir, copy_dir)
        assert Directory.exists(copy_dir)
    
    print("✓ Directory operation tests passed")


def test_streams():
    """Test Stream operations"""
    print("Testing Streams...")
    
    # Memory stream
    mem = MemoryStream()
    mem.write('Hello')
    mem.write(' World')
    content = mem.getvalue()
    assert content == 'Hello World'
    mem.close()
    
    # Binary memory stream
    bin_mem = BinaryMemoryStream()
    bin_mem.write(b'Binary data')
    data = bin_mem.getvalue()
    assert data == b'Binary data'
    bin_mem.close()
    
    # File stream
    with TempFile(delete=False) as tmp:
        tmp.write('Test data')
        tmp_path = tmp.name
    
    try:
        with FileStream(tmp_path, 'r') as stream:
            content = stream.read()
            assert content == 'Test data'
    finally:
        os.unlink(tmp_path)
    
    print("✓ Stream tests passed")


def test_temp_files():
    """Test temporary files"""
    print("Testing Temporary Files...")
    
    # Temp file
    with TempFile() as tmp:
        tmp.write('Temporary')
        tmp_name = tmp.name
        assert os.path.exists(tmp_name)
    
    # File should be deleted after context
    # (may not work if delete=True, which is default)
    
    # Temp directory
    with TempDir() as tmpdir:
        assert os.path.exists(tmpdir.name)
        test_file = os.path.join(tmpdir.name, 'test.txt')
        File.write(test_file, 'test')
    
    # Directory should be cleaned up
    assert not os.path.exists(tmpdir.name)
    
    print("✓ Temporary file tests passed")


def test_archives():
    """Test archive operations"""
    print("Testing Archives...")
    
    with TempDir() as tmpdir:
        # Create test files
        file1 = os.path.join(tmpdir.name, 'file1.txt')
        file2 = os.path.join(tmpdir.name, 'file2.txt')
        File.write(file1, 'Content 1')
        File.write(file2, 'Content 2')
        
        # ZIP archive
        zip_path = os.path.join(tmpdir.name, 'archive.zip')
        ZipArchive.create(zip_path, [file1, file2], base_dir=tmpdir.name)
        assert os.path.exists(zip_path)
        
        # List contents
        files = ZipArchive.list_contents(zip_path)
        assert len(files) == 2
        
        # Extract
        extract_dir = os.path.join(tmpdir.name, 'extracted')
        os.makedirs(extract_dir)
        ZipArchive.extract(zip_path, extract_dir)
        assert os.path.exists(os.path.join(extract_dir, 'file1.txt'))
        
        # TAR archive
        tar_path = os.path.join(tmpdir.name, 'archive.tar.gz')
        TarArchive.create(tar_path, [file1, file2], compression='gz', base_dir=tmpdir.name)
        assert os.path.exists(tar_path)
        
        # Auto-detect
        archive_type = Archive.detect_type(zip_path)
        assert archive_type == 'zip'
    
    print("✓ Archive tests passed")


def run_all_tests():
    """Run all file I/O tests"""
    print("\n" + "="*50)
    print("THIRSTY-LANG FILE I/O TEST SUITE")
    print("="*50 + "\n")
    
    try:
        test_path()
        test_file_operations()
        test_directory_operations()
        test_streams()
        test_temp_files()
        test_archives()
        
        print("\n" + "="*50)
        print("✓ ALL FILE I/O TESTS PASSED")
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
