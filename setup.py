#!/usr/bin/env python
"""
RapidIdentity Library - Setup and Configuration Script

This script helps set up and test the RapidIdentity Python library.
"""

import os
import sys
import subprocess


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}\n")
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main setup function."""
    print_header("RapidIdentity Python Library Setup")

    # Check Python version
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False

    # Install the package in development mode
    print_header("Installing Package")
    if not run_command(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        "Install package in development mode"
    ):
        return False

    # Install dev dependencies
    print_header("Installing Development Dependencies")
    if not run_command(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        "Install development dependencies"
    ):
        print("⚠️  Warning: Some dev dependencies failed to install")

    # Run tests
    print_header("Running Tests")
    if not run_command(
        [sys.executable, "-m", "pytest", "tests/", "-v"],
        "Run test suite"
    ):
        print("⚠️  Warning: Some tests failed")
    else:
        print("✅ All tests passed!")

    # Print project structure
    print_header("Project Structure")
    print("""
rapididentity-tools/
├── rapididentity/                    # Main library package
│   ├── __init__.py                  # Package initialization
│   ├── client.py                    # Main API client
│   ├── auth.py                      # Authentication configurations
│   ├── exceptions.py                # Custom exceptions
│   └── utils/                       # Utility modules
│       ├── __init__.py
│       ├── validators.py            # Validation functions
│       ├── parsers.py               # Data parsing utilities
│       └── helpers.py               # Helper functions
├── examples/                         # Example scripts
│   ├── basic_usage.py               # Basic client usage
│   └── utilities_usage.py           # Utilities examples
├── tests/                            # Test suite
│   └── test_client.py               # Client tests
├── pyproject.toml                   # Project configuration
├── README.md                        # Project documentation
├── CONTRIBUTING.md                  # Contribution guidelines
└── .gitignore                       # Git ignore rules
    """)

    print_header("Quick Start")
    print("""
1. Create a RapidIdentity API client:

    from rapididentity import RapidIdentityClient

    with RapidIdentityClient.with_api_key(
        host="https://rapididentity.example.com",
        api_key="your-api-key"
    ) as client:
        users = client.get("/users")
        print(users)

2. Run tests:

    pytest tests/ -v

3. Check documentation:

    See README.md for detailed documentation
    See examples/ for usage examples

4. View RapidIdentity API docs:

    https://<your-rapididentity-host>/api/rest/api-docs
    """)

    print_header("Setup Complete!")
    print("✅ RapidIdentity Python library is ready to use!")
    print("\nNext steps:")
    print("  1. Review README.md for detailed usage")
    print("  2. Check examples/ folder for code examples")
    print("  3. Update pyproject.toml with your repository information")
    print("  4. Configure your RapidIdentity API credentials")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
