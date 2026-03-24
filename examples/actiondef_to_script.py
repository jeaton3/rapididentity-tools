"""Convert a single actionDef XML file into a readable actionscript text file.

Usage:
    python examples/actiondef_to_script.py <input.xml> [output.txt]

If no output path is given the script prints to stdout.
"""

import sys
import os

# ensure the project package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rapididentity.utils import actiondef_file_to_script


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python actiondef_to_script.py <input.xml> [output.txt]")
        sys.exit(1)

    result = actiondef_file_to_script(sys.argv[1])

    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w") as f:
            f.write(result)
        print(f"Written to {sys.argv[2]}")
    else:
        print(result)
