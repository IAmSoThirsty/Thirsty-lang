"""
Thirsty-Lang Standard Library: Temporary Files
Secure temporary file and directory creation

Provides:
- TempFile: Temporary file creation
- TempDir: Temporary directory creation
- Automatic cleanup on context exit
"""

import tempfile
import os
from typing import Optional


class TempFile:
    """Temporary file with automatic cleanup"""
    
    def __init__(
        self,
        mode='w+',
        suffix='',
        prefix='tmp',
        dir=None,
        delete=True,
        encoding='utf-8'
    ):
        self.mode = mode
        self.suffix = suffix
        self.prefix = prefix
        self.dir = dir
        self.delete = delete
        self.encoding = encoding if 'b' not in mode else None
        self._file = None
        self.name = None
    
    def create(self):
        """Create temporary file"""
        if 'b' in self.mode:
            self._file = tempfile.NamedTemporaryFile(
                mode=self.mode,
                suffix=self.suffix,
                prefix=self.prefix,
                dir=self.dir,
                delete=self.delete
            )
        else:
            self._file = tempfile.NamedTemporaryFile(
                mode=self.mode,
                suffix=self.suffix,
                prefix=self.prefix,
                dir=self.dir,
                delete=self.delete,
                encoding=self.encoding
            )
        self.name = self._file.name
        return self
    
    def write(self, content):
        """Write to temp file"""
        self._file.write(content)
        self._file.flush()
    
    def read(self):
        """Read from temp file"""
        self._file.seek(0)
        return self._file.read()
    
    def close(self):
        """Close and delete temp file"""
        if self._file:
            self._file.close()
    
    def __enter__(self):
        self.create()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    @staticmethod
    def create_named(suffix='', prefix='tmp', dir=None) -> str:
        """Create named temporary file and return path"""
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
        os.close(fd)
        return path


class TempDir:
    """Temporary directory with automatic cleanup"""
    
    def __init__(self, suffix='', prefix='tmp', dir=None):
        self.suffix = suffix
        self.prefix = prefix
        self.dir = dir
        self.name = None
        self._cleanup = None
    
    def create(self):
        """Create temporary directory"""
        self.name = tempfile.mkdtemp(
            suffix=self.suffix,
            prefix=self.prefix,
            dir=self.dir
        )
        return self
    
    def cleanup(self):
        """Remove temporary directory"""
        if self.name and os.path.exists(self.name):
            import shutil
            shutil.rmtree(self.name)
    
    def __enter__(self):
        self.create()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    @staticmethod
    def get_temp_dir() -> str:
        """Get system temp directory"""
        return tempfile.gettempdir()


# Export temp file classes
__all__ = ['TempFile', 'TempDir']
