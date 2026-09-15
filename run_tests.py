#!/usr/bin/env python3
"""
Script to run all tests for the Lenny Growth Assistant
"""
import os
import sys
import subprocess

def run_tests():
    """Run all tests"""
    # Change to the project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Run tests with pytest
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short"
        ], check=True, capture_output=True, text=True)

        print("Tests passed!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("Tests failed!")
        print(e.stdout)
        print(e.stderr)
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)