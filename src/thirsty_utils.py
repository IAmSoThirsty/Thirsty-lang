#!/usr/bin/env python3
"""
Thirsty-Lang Python Utilities
Common utility functions for Thirsty-Lang Python implementation
"""

import os
import sys
from typing import List, Optional


def read_file(filename: str) -> str:
    """Read a Thirsty-Lang source file.

    Args:
        filename: Path to the file

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()


def get_file_extension(filename: str) -> str:
    """Get the file extension.

    Args:
        filename: Path to the file

    Returns:
        File extension (e.g., '.thirsty')
    """
    return os.path.splitext(filename)[1]


def is_thirsty_file(filename: str) -> bool:
    """Check if a file is a Thirsty-Lang file.

    Args:
        filename: Path to the file

    Returns:
        True if file has Thirsty-Lang extension
    """
    valid_extensions = [
        ".thirsty",
        ".tog",
        ".tarl",
        ".shadow",
    ]
    return get_file_extension(filename).lower() in valid_extensions


def find_thirsty_files(directory: str) -> List[str]:
    """Find all Thirsty-Lang files in a directory.

    Args:
        directory: Path to search

    Returns:
        List of Thirsty-Lang file paths
    """
    thirsty_files = []
    for root, _dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            if is_thirsty_file(filepath):
                thirsty_files.append(filepath)
    return thirsty_files


def format_error(
    message: str, line_num: Optional[int] = None
) -> str:
    """Format an error message.

    Args:
        message: Error message
        line_num: Optional line number

    Returns:
        Formatted error string
    """
    if line_num:
        return f"Error on line {line_num}: {message}"
    return f"Error: {message}"


def print_banner(title: str) -> None:
    """Print a formatted banner.

    Args:
        title: Banner title
    """
    width = 60
    border = "═" * (width - 2)
    print(f"╔{border}╗")
    pad = (width - len(title) - 2) // 2
    right = width - len(title) - pad - 2
    print(f"║{' ' * pad}{title}{' ' * right}║")
    print(f"╚{border}╝")


def check_version() -> str:
    """Get Python and Thirsty-Lang version info.

    Returns:
        Version string
    """
    major = sys.version_info.major
    minor = sys.version_info.minor
    micro = sys.version_info.micro
    py_ver = f"{major}.{minor}.{micro}"
    return f"Python {py_ver} | Thirsty-Lang 2.0.0"


if __name__ == "__main__":
    # Test utilities
    print_banner("Thirsty-Lang Python Utilities")
    print(f"\n{check_version()}\n")
