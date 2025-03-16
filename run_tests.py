#!/usr/bin/env python3
"""
Run all CodeDoc tests with detailed reporting.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run CodeDoc tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--package", default="codedoc", help="Package to test")
    parser.add_argument("--pattern", help="Test pattern to match (e.g., 'test_chunker')")
    return parser.parse_args()

def run_tests(args):
    """Run tests based on command line arguments."""
    # Build pytest command
    cmd = ["pytest"]
    
    # Add test selection
    if args.unit and not args.integration:
        cmd.append("-m")
        cmd.append("not integration")
    elif args.integration and not args.unit:
        cmd.append("-m")
        cmd.append("integration")
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage
    if args.coverage:
        cmd.extend(["--cov", args.package, "--cov-report", "term", "--cov-report", "html"])
    
    # Add pattern if specified
    if args.pattern:
        cmd.append(f"codedoc/tests/*{args.pattern}*")
    else:
        cmd.append("codedoc/tests/")
    
    # Run tests
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode

def main():
    """Main entry point."""
    args = parse_args()
    
    # Ensure we're running from the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Run tests
    return_code = run_tests(args)
    
    # Print coverage report location if generated
    if args.coverage:
        print("\nCoverage report generated in htmlcov/index.html")
    
    # Exit with test result code
    sys.exit(return_code)

if __name__ == "__main__":
    main() 