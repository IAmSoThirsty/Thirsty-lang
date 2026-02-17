"""
Thirsty-Lang Standard Library: Archives
Archive file support (zip, tar)

Provides:
- ZipArchive: Create and extract ZIP files
- TarArchive: Create and extract TAR files
- Auto-detection of archive types
"""

import zipfile
import tarfile
import os
from typing import List, Optional


class ZipArchive:
    """ZIP archive operations"""
    
    @staticmethod
    def create(archive_path: str, files: List[str], base_dir: Optional[str] = None):
        """Create ZIP archive"""
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                arcname = os.path.relpath(file, base_dir) if base_dir else file
                zf.write(file, arcname)
    
    @staticmethod
    def extract(archive_path: str, extract_to: str = '.'):
        """Extract ZIP archive"""
        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extractall(extract_to)
    
    @staticmethod
    def extract_file(archive_path: str, filename: str, extract_to: str = '.'):
        """Extract single file from ZIP"""
        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extract(filename, extract_to)
    
    @staticmethod
    def list_contents(archive_path: str) -> List[str]:
        """List files in ZIP archive"""
        with zipfile.ZipFile(archive_path, 'r') as zf:
            return zf.namelist()
    
    @staticmethod
    def add_file(archive_path: str, file_path: str, arcname: Optional[str] = None):
        """Add file to existing ZIP"""
        with zipfile.ZipFile(archive_path, 'a', zipfile.ZIP_DEFLATED) as zf:
            zf.write(file_path, arcname or os.path.basename(file_path))
    
    @staticmethod
    def read_file(archive_path: str, filename: str) -> bytes:
        """Read file from ZIP without extracting"""
        with zipfile.ZipFile(archive_path, 'r') as zf:
            return zf.read(filename)
    
    @staticmethod
    def is_valid(archive_path: str) -> bool:
        """Check if file is a valid ZIP archive"""
        return zipfile.is_zipfile(archive_path)


class TarArchive:
    """TAR archive operations"""
    
    @staticmethod
    def create(
        archive_path: str,
        files: List[str],
        compression: Optional[str] = None,
        base_dir: Optional[str] = None
    ):
        """Create TAR archive
        
        compression: None, 'gz', 'bz2', or 'xz'
        """
        mode = 'w'
        if compression:
            mode = f'w:{compression}'
        
        with tarfile.open(archive_path, mode) as tf:
            for file in files:
                arcname = os.path.relpath(file, base_dir) if base_dir else file
                tf.add(file, arcname)
    
    @staticmethod
    def extract(archive_path: str, extract_to: str = '.'):
        """Extract TAR archive"""
        with tarfile.open(archive_path, 'r:*') as tf:
            tf.extractall(extract_to)
    
    @staticmethod
    def extract_file(archive_path: str, filename: str, extract_to: str = '.'):
        """Extract single file from TAR"""
        with tarfile.open(archive_path, 'r:*') as tf:
            member = tf.getmember(filename)
            tf.extract(member, extract_to)
    
    @staticmethod
    def list_contents(archive_path: str) -> List[str]:
        """List files in TAR archive"""
        with tarfile.open(archive_path, 'r:*') as tf:
            return tf.getnames()
    
    @staticmethod
    def add_file(
        archive_path: str,
        file_path: str,
        arcname: Optional[str] = None,
        compression: Optional[str] = None
    ):
        """Add file to existing TAR"""
        mode = 'a'
        if compression:
            mode = f'a:{compression}'
        
        with tarfile.open(archive_path, mode) as tf:
            tf.add(file_path, arcname or os.path.basename(file_path))
    
    @staticmethod
    def read_file(archive_path: str, filename: str) -> bytes:
        """Read file from TAR without extracting"""
        with tarfile.open(archive_path, 'r:*') as tf:
            member = tf.getmember(filename)
            f = tf.extractfile(member)
            return f.read() if f else b''
    
    @staticmethod
    def is_valid(archive_path: str) -> bool:
        """Check if file is a valid TAR archive"""
        return tarfile.is_tarfile(archive_path)


class Archive:
    """Auto-detecting archive operations"""
    
    @staticmethod
    def detect_type(archive_path: str) -> Optional[str]:
        """Detect archive type"""
        if ZipArchive.is_valid(archive_path):
            return 'zip'
        elif TarArchive.is_valid(archive_path):
            return 'tar'
        return None
    
    @staticmethod
    def extract(archive_path: str, extract_to: str = '.'):
        """Auto-detect and extract archive"""
        archive_type = Archive.detect_type(archive_path)
        
        if archive_type == 'zip':
            ZipArchive.extract(archive_path, extract_to)
        elif archive_type == 'tar':
            TarArchive.extract(archive_path, extract_to)
        else:
            raise ValueError(f"Unknown archive type for: {archive_path}")
    
    @staticmethod
    def list_contents(archive_path: str) -> List[str]:
        """Auto-detect and list archive contents"""
        archive_type = Archive.detect_type(archive_path)
        
        if archive_type == 'zip':
            return ZipArchive.list_contents(archive_path)
        elif archive_type == 'tar':
            return TarArchive.list_contents(archive_path)
        else:
            raise ValueError(f"Unknown archive type for: {archive_path}")


# Export archive classes
__all__ = ['ZipArchive', 'TarArchive', 'Archive']
