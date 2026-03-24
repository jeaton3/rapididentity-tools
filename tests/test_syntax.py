"""
Syntax validation tests for all Python files in the project.

This test ensures all Python files can be compiled without syntax errors.
This catches issues that might not be exercised by other unit tests.
"""

import sys
import os
import py_compile
from pathlib import Path

# ensure local package is available when running tests directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def get_python_files():
    """Get all Python files in the project (excluding __pycache__, .venv, etc)."""
    project_root = Path(__file__).parent.parent
    exclude_dirs = {".venv", ".git", "__pycache__", ".egg-info", "rapididentity.egg-info"}
    
    python_files = []
    for py_file in project_root.rglob("*.py"):
        # Skip if any part of the path is in exclude_dirs
        if any(part in exclude_dirs for part in py_file.parts):
            continue
        python_files.append(py_file)
    
    return sorted(python_files)


class TestSyntax:
    """Test syntax of all Python files."""

    def test_all_files_compile(self):
        """Ensure all Python files can be compiled without syntax errors."""
        python_files = get_python_files()
        assert len(python_files) > 0, "No Python files found"
        
        failed_files = []
        for py_file in python_files:
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                failed_files.append((py_file, str(e)))
        
        if failed_files:
            error_msg = "Syntax errors found in:\n"
            for file_path, error in failed_files:
                error_msg += f"\n{file_path}:\n{error}"
            assert False, error_msg
    
    def test_core_modules_importable(self):
        """Ensure core modules can be imported."""
        try:
            import rapididentity
            from rapididentity import RapidIdentityClient, Config
            from rapididentity.connect import RapidIdentityConnect
            from rapididentity.exceptions import AuthenticationError, APIError
        except ImportError as e:
            assert False, f"Failed to import core modules: {e}"
    
    def test_examples_importable(self):
        """Ensure example modules can be imported."""
        try:
            # Add examples to path
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples"))
            import connect_file_utils
        except ImportError as e:
            assert False, f"Failed to import examples.connect_file_utils: {e}"
        except SyntaxError as e:
            assert False, f"Syntax error in examples.connect_file_utils: {e}"
