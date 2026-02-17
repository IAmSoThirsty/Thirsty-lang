"""
Thirsty-Lang Standard Library: Streams
Buffered and unbuffered I/O streams

Provides:
- FileStream: Buffered file I/O
- BinaryStream: Binary file I/O
- MemoryStream: In-memory stream
- StreamReader/StreamWriter: Text streaming
"""

from typing import Optional
import io


class FileStream:
    """Buffered text file stream"""
    
    def __init__(self, path: str, mode='r', encoding='utf-8', buffer_size=8192):
        self.path = path
        self.mode = mode
        self.encoding = encoding
        self.buffer_size = buffer_size
        self._file = None
    
    def open(self):
        """Open file stream"""
        self._file = open(
            self.path,
            self.mode,
            encoding=self.encoding,
            buffering=self.buffer_size
        )
        return self
    
    def close(self):
        """Close file stream"""
        if self._file:
            self._file.close()
    
    def read(self, size=-1) -> str:
        """Read from stream"""
        return self._file.read(size)
    
    def readline(self) -> str:
        """Read single line"""
        return self._file.readline()
    
    def readlines(self) -> list:
        """Read all lines"""
        return self._file.readlines()
    
    def write(self, data: str) -> int:
        """Write to stream"""
        return self._file.write(data)
    
    def writelines(self, lines: list):
        """Write multiple lines"""
        self._file.writelines(lines)
    
    def flush(self):
        """Flush buffer"""
        self._file.flush()
    
    def seek(self, offset: int, whence=0):
        """Seek to position"""
        self._file.seek(offset, whence)
    
    def tell(self) -> int:
        """Get current position"""
        return self._file.tell()
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __iter__(self):
        """Iterate over lines"""
        return iter(self._file)


class BinaryStream:
    """Binary file stream"""
    
    def __init__(self, path: str, mode='rb', buffer_size=8192):
        self.path = path
        self.mode = mode
        self.buffer_size = buffer_size
        self._file = None
    
    def open(self):
        """Open binary stream"""
        self._file = open(self.path, self.mode, buffering=self.buffer_size)
        return self
    
    def close(self):
        """Close stream"""
        if self._file:
            self._file.close()
    
    def read(self, size=-1) -> bytes:
        """Read bytes"""
        return self._file.read(size)
    
    def write(self, data: bytes) -> int:
        """Write bytes"""
        return self._file.write(data)
    
    def flush(self):
        """Flush buffer"""
        self._file.flush()
    
    def seek(self, offset: int, whence=0):
        """Seek to position"""
        self._file.seek(offset, whence)
    
    def tell(self) -> int:
        """Get current position"""
        return self._file.tell()
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MemoryStream:
    """In-memory stream"""
    
    def __init__(self, initial_data: Optional[str] = None):
        self._stream = io.StringIO(initial_data or '')
    
    def read(self, size=-1) -> str:
        """Read from memory"""
        return self._stream.read(size)
    
    def write(self, data: str) -> int:
        """Write to memory"""
        return self._stream.write(data)
    
    def getvalue(self) -> str:
        """Get entire contents"""
        return self._stream.getvalue()
    
    def seek(self, offset: int, whence=0):
        """Seek to position"""
        self._stream.seek(offset, whence)
    
    def tell(self) -> int:
        """Get current position"""
        return self._stream.tell()
    
    def close(self):
        """Close stream"""
        self._stream.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class BinaryMemoryStream:
    """In-memory binary stream"""
    
    def __init__(self, initial_data: Optional[bytes] = None):
        self._stream = io.BytesIO(initial_data or b'')
    
    def read(self, size=-1) -> bytes:
        """Read from memory"""
        return self._stream.read(size)
    
    def write(self, data: bytes) -> int:
        """Write to memory"""
        return self._stream.write(data)
    
    def getvalue(self) -> bytes:
        """Get entire contents"""
        return self._stream.getvalue()
    
    def seek(self, offset: int, whence=0):
        """Seek to position"""
        self._stream.seek(offset, whence)
    
    def tell(self) -> int:
        """Get current position"""
        return self._stream.tell()
    
    def close(self):
        """Close stream"""
        self._stream.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class StreamReader:
    """Text stream reader"""
    
    def __init__(self, stream):
        self._stream = stream
    
    def read_line(self) -> Optional[str]:
        """Read next line"""
        line = self._stream.readline()
        return line if line else None
    
    def read_all(self) -> str:
        """Read entire stream"""
        return self._stream.read()
    
    def read_chunk(self, size: int) -> str:
        """Read chunk of specific size"""
        return self._stream.read(size)


class StreamWriter:
    """Text stream writer"""
    
    def __init__(self, stream):
        self._stream = stream
    
    def write_line(self, text: str):
        """Write line with newline"""
        self._stream.write(text + '\n')
    
    def write(self, text: str):
        """Write text"""
        self._stream.write(text)
    
    def flush(self):
        """Flush buffer"""
        self._stream.flush()


# Export stream classes
__all__ = [
    'FileStream',
    'BinaryStream',
    'MemoryStream',
    'BinaryMemoryStream',
    'StreamReader',
    'StreamWriter'
]
