"""
Thirsty-Lang Standard Library: Filesystem
File and directory operations

Provides:
- File: High-level file operations
- Directory: Directory operations
- Watch: File system monitoring
- Permissions: File permission management
"""

import os
import shutil
import json as py_json
from typing import List, Optional, Callable
import threading
import time


class File:
    """High-level file operations"""
    
    @staticmethod
    def read(path: str, encoding='utf-8') -> str:
        """Read entire file as text"""
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    
    @staticmethod
    def read_bytes(path: str) -> bytes:
        """Read entire file as bytes"""
        with open(path, 'rb') as f:
            return f.read()
    
    @staticmethod
    def read_lines(path: str, encoding='utf-8') -> List[str]:
        """Read file as list of lines"""
        with open(path, 'r', encoding=encoding) as f:
            return f.readlines()
    
    @staticmethod
    def read_json(path: str, encoding='utf-8'):
        """Read and parse JSON file"""
        with open(path, 'r', encoding=encoding) as f:
            return py_json.load(f)
    
    @staticmethod
    def write(path: str, content: str, encoding='utf-8'):
        """Write text to file"""
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
    
    @staticmethod
    def write_bytes(path: str, content: bytes):
        """Write bytes to file"""
        with open(path, 'wb') as f:
            f.write(content)
    
    @staticmethod
    def write_lines(path: str, lines: List[str], encoding='utf-8'):
        """Write lines to file"""
        with open(path, 'w', encoding=encoding) as f:
            f.writelines(lines)
    
    @staticmethod
    def write_json(path: str, data, encoding='utf-8', indent=2):
        """Write data as JSON"""
        with open(path, 'w', encoding=encoding) as f:
            py_json.dump(data, f, indent=indent)
    
    @staticmethod
    def append(path: str, content: str, encoding='utf-8'):
        """Append text to file"""
        with open(path, 'a', encoding=encoding) as f:
            f.write(content)
    
    @staticmethod
    def exists(path: str) -> bool:
        """Check if file exists"""
        return os.path.isfile(path)
    
    @staticmethod
    def size(path: str) -> int:
        """Get file size in bytes"""
        return os.path.getsize(path)
    
    @staticmethod
    def delete(path: str):
        """Delete file"""
        os.remove(path)
    
    @staticmethod
    def copy(src: str, dst: str):
        """Copy file"""
        shutil.copy2(src, dst)
    
    @staticmethod
    def move(src: str, dst: str):
        """Move/rename file"""
        shutil.move(src, dst)
    
    @staticmethod
    def stat(path: str):
        """Get file statistics"""
        return os.stat(path)


class Directory:
    """Directory operations"""
    
    @staticmethod
    def create(path: str, parents=True, exist_ok=True):
        """Create directory"""
        os.makedirs(path, exist_ok=exist_ok)
    
    @staticmethod
    def delete(path: str):
        """Delete empty directory"""
        os.rmdir(path)
    
    @staticmethod
    def delete_recursive(path: str):
        """Delete directory and all contents"""
        shutil.rmtree(path)
    
    @staticmethod
    def exists(path: str) -> bool:
        """Check if directory exists"""
        return os.path.isdir(path)
    
    @staticmethod
    def list(path: str) -> List[str]:
        """List directory contents"""
        return os.listdir(path)
    
    @staticmethod
    def list_files(path: str, recursive=False) -> List[str]:
        """List all files in directory"""
        if not recursive:
            return [
                os.path.join(path, f)
                for f in os.listdir(path)
                if os.path.isfile(os.path.join(path, f))
            ]
        else:
            files = []
            for root, dirs, filenames in os.walk(path):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
            return files
    
    @staticmethod
    def list_dirs(path: str) -> List[str]:
        """List all subdirectories"""
        return [
            os.path.join(path, d)
            for d in os.listdir(path)
            if os.path.isdir(os.path.join(path, d))
        ]
    
    @staticmethod
    def copy(src: str, dst: str):
        """Copy directory and contents"""
        shutil.copytree(src, dst)
    
    @staticmethod
    def move(src: str, dst: str):
        """Move directory"""
        shutil.move(src, dst)
    
    @staticmethod
    def size(path: str) -> int:
        """Get total size of directory"""
        total = 0
        for root, dirs, files in os.walk(path):
            for file in files:
                filepath = os.path.join(root, file)
                if os.path.exists(filepath):
                    total += os.path.getsize(filepath)
        return total


class FileWatcher:
    """Simple file watcher (polling-based)"""
    
    def __init__(self, path: str, callback: Callable, interval=1.0):
        self.path = path
        self.callback = callback
        self.interval = interval
        self._running = False
        self._thread = None
        self._last_mtime = None
        
        if os.path.exists(path):
            self._last_mtime = os.path.getmtime(path)
    
    def start(self):
        """Start watching"""
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop)
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        """Stop watching"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _watch_loop(self):
        """Watch loop"""
        while self._running:
            try:
                if os.path.exists(self.path):
                    mtime = os.path.getmtime(self.path)
                    if self._last_mtime is None or mtime > self._last_mtime:
                        self._last_mtime = mtime
                        self.callback(self.path)
            except Exception:
                pass
            
            time.sleep(self.interval)


class Permissions:
    """File permission management"""
    
    @staticmethod
    def chmod(path: str, mode: int):
        """Change file permissions (Unix mode)"""
        os.chmod(path, mode)
    
    @staticmethod
    def is_readable(path: str) -> bool:
        """Check if file is readable"""
        return os.access(path, os.R_OK)
    
    @staticmethod
    def is_writable(path: str) -> bool:
        """Check if file is writable"""
        return os.access(path, os.W_OK)
    
    @staticmethod
    def is_executable(path: str) -> bool:
        """Check if file is executable"""
        return os.access(path, os.X_OK)
    
    @staticmethod
    def make_executable(path: str):
        """Make file executable"""
        import stat
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)


# Export filesystem classes
__all__ = ['File', 'Directory', 'FileWatcher', 'Permissions']
