#!/usr/bin/env python3
"""
Pre-commit hook to ensure spec.py and models.py files have at most one import line.
This enforces the DSL pattern of consolidating imports for demo purposes.
"""

import sys
from pathlib import Path


def count_import_lines(file_path: Path) -> int:
    """Count the number of import lines in a file."""
    with open(file_path, "r") as f:
        lines = f.readlines()

    import_count = 0
    for line in lines:
        stripped = line.strip()
        # Count lines that start with 'from' or 'import' (excluding comments)
        if stripped and not stripped.startswith("#"):
            if stripped.startswith("from ") or stripped.startswith("import "):
                import_count += 1

    return import_count


def main() -> int:
    """Check all provided spec.py and models.py files."""
    exit_code = 0
    checked_files = {"spec.py", "models.py"}

    for file_arg in sys.argv[1:]:
        file_path = Path(file_arg)

        # Only check files named spec.py or models.py
        if file_path.name not in checked_files:
            continue

        import_count = count_import_lines(file_path)
        file_type = file_path.name

        if import_count > 1:
            print(
                f"❌ {file_path}: Found {import_count} import lines, but {file_type} files "
                f"should have at most 1 import line."
            )
            if file_type == "spec.py":
                print(
                    "   Consider consolidating imports using a local dsl.py or nxd_spec.py file."
                )
            elif file_type == "models.py":
                print(
                    "   Consider consolidating imports using a local nxd_models.py file."
                )
            exit_code = 1
        elif import_count == 1:
            print(f"✅ {file_path}: Valid (1 import line)")
        else:
            print(f"✅ {file_path}: Valid (0 import lines)")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
