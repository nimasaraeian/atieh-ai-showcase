"""
Path resolution utilities for handling Persian filenames on Windows.
"""
from pathlib import Path
from typing import Optional
import os


def find_repo_root() -> Path:
    """
    Find repository root by looking for 'data' folder or '.git' directory.
    Searches upward from current directory.
    """
    current = Path.cwd()
    
    # Try up to 10 levels up
    for _ in range(10):
        # Check for markers
        if (current / 'data').exists() or (current / '.git').exists():
            return current
        
        # Go up one level
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent
    
    # Fallback: use current working directory
    return Path.cwd()


def resolve_repo_path(rel_path: str) -> Path:
    """
    Resolve a relative path to absolute path from repository root.
    Handles Persian filenames correctly on Windows.
    
    Args:
        rel_path: Relative path (can use forward slashes)
    
    Returns:
        Resolved absolute Path object
    
    Raises:
        FileNotFoundError: If resolved path doesn't exist
        ValueError: If path is invalid
    
    Example:
        path = resolve_repo_path("data/inputs/history/1404/نوبت_دهی_1404.xlsx")
    """
    if not rel_path:
        raise ValueError("Path cannot be empty")
    
    # Convert forward slashes to OS-specific separators
    rel_path = rel_path.replace('/', os.sep)
    
    # Find repo root
    repo_root = find_repo_root()
    
    # Construct full path
    full_path = repo_root / rel_path
    
    # Resolve to absolute path (handles .. and . and symlinks)
    try:
        resolved = full_path.resolve()
    except Exception as e:
        raise ValueError(f"Invalid path '{rel_path}': {e}")
    
    # Check if exists
    if not resolved.exists():
        raise FileNotFoundError(
            f"Path does not exist: {resolved}\n"
            f"Repository root: {repo_root}\n"
            f"Relative path: {rel_path}"
        )
    
    return resolved


def ensure_dir_exists(dir_path: str) -> Path:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        dir_path: Relative path to directory
    
    Returns:
        Resolved Path object
    """
    repo_root = find_repo_root()
    dir_path = dir_path.replace('/', os.sep)
    full_path = repo_root / dir_path
    
    # Create directory if it doesn't exist
    full_path.mkdir(parents=True, exist_ok=True)
    
    return full_path.resolve()


def list_files_in_dir(dir_path: str, pattern: str = "*") -> list[Path]:
    """
    List all files matching pattern in directory.
    
    Args:
        dir_path: Relative directory path
        pattern: Glob pattern (default: "*" for all files)
    
    Returns:
        List of resolved Path objects
    """
    try:
        resolved_dir = resolve_repo_path(dir_path)
    except FileNotFoundError:
        return []
    
    if not resolved_dir.is_dir():
        return []
    
    return list(resolved_dir.glob(pattern))
