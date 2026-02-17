"""
Thirsty-Lang Standard Library: Path
Cross-platform path manipulation

Provides:
- Path: Pathlib-style path manipulation
- Cross-platform path operations
- Glob matching and directory traversal
"""

import os
import pathlib
import glob as py_glob
from typing import List, Optional


class Path:
    """Cross-platform path manipulation"""
    
    def __init__(self, *parts):
        """Create path from parts"""
        self._path = pathlib.Path(*parts)
    
    @property
    def path(self) -> str:
        """Get path as string"""
        return str(self._path)
    
    @property
    def name(self) -> str:
        """File name including extension"""
        return self._path.name
    
    @property
    def stem(self) -> str:
        """File name without extension"""
        return self._path.stem
    
    @property
    def suffix(self) -> str:
        """File extension including dot"""
        return self._path.suffix
    
    @property
    def parent(self) -> 'Path':
        """Parent directory"""
        return Path(self._path.parent)
    
    @property
    def parts(self) -> tuple:
        """Path components"""
        return self._path.parts
    
    def join(self, *other) -> 'Path':
        """Join with other path components"""
        return Path(self._path, *other)
    
    def absolute(self) -> 'Path':
        """Get absolute path"""
        return Path(self._path.absolute())
    
    def resolve(self) -> 'Path':
        """Resolve symlinks and make absolute"""
        return Path(self._path.resolve())
    
    def relative_to(self, other) -> 'Path':
        """Get relative path from other"""
        return Path(self._path.relative_to(other))
    
    def exists(self) -> bool:
        """Check if path exists"""
        return self._path.exists()
    
    def is_file(self) -> bool:
        """Check if path is a file"""
        return self._path.is_file()
    
    def is_dir(self) -> bool:
        """Check if path is a directory"""
        return self._path.is_dir()
    
    def is_absolute(self) -> bool:
        """Check if path is absolute"""
        return self._path.is_absolute()
    
    def glob(self, pattern: str) -> List['Path']:
        """Glob matching"""
        return [Path(p) for p in self._path.glob(pattern)]
    
    def rglob(self, pattern: str) -> List['Path']:
        """Recursive glob matching"""
        return [Path(p) for p in self._path.rglob(pattern)]
    
    def mkdir(self, parents=False, exist_ok=False):
        """Create directory"""
        self._path.mkdir(parents=parents, exist_ok=exist_ok)
    
    def rmdir(self):
        """Remove empty directory"""
        self._path.rmdir()
    
    def unlink(self, missing_ok=False):
        """Delete file"""
        self._path.unlink(missing_ok=missing_ok)
    
    def rename(self, target) -> 'Path':
        """Rename file/directory"""
        return Path(self._path.rename(target))
    
    def replace(self, target) -> 'Path':
        """Replace file/directory"""
        return Path(self._path.replace(target))
    
    def with_name(self, name: str) -> 'Path':
        """Return path with different name"""
        return Path(self._path.with_name(name))
    
    def with_suffix(self, suffix: str) -> 'Path':
        """Return path with different suffix"""
        return Path(self._path.with_suffix(suffix))
    
    def stat(self):
        """Get file statistics"""
        return self._path.stat()
    
    def __str__(self):
        return str(self._path)
    
    def __repr__(self):
        return f"Path('{self._path}')"
    
    def __truediv__(self, other):
        """Path / 'subdir' syntax"""
        return Path(self._path / other)
    
    def __eq__(self, other):
        if isinstance(other, Path):
            return self._path == other._path
        return self._path == pathlib.Path(other)
    
    @staticmethod
    def cwd() -> 'Path':
        """Get current working directory"""
        return Path(pathlib.Path.cwd())
    
    @staticmethod
    def home() -> 'Path':
        """Get user home directory"""
        return Path(pathlib.Path.home())
    
    @staticmethod
    def glob_match(pattern: str, path: str) -> bool:
        """Check if path matches glob pattern"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)


# Export Path class
__all__ = ['Path']
