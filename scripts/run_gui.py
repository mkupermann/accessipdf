#!/usr/bin/env python3
"""Script to run the accessipdf Streamlit GUI."""

import subprocess
import sys


def main():
    """Run the Streamlit GUI."""
    print("Starting accessipdf GUI...")
    print("The application will be available at http://localhost:8501")
    print("Press Ctrl+C to stop")
    print()

    # Run Streamlit
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "gui/app.py",
            "--server.port=8501",
            "--server.address=0.0.0.0",
        ]
    )

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
