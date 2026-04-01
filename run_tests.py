#!/usr/bin/env python3
"""
Test runner for norad-sim-test
Runs all tests and generates coverage report

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --unit        # Run only unit tests
    python run_tests.py --coverage    # Run with coverage
    python run_tests.py --verbose     # Verbose output
    python run_tests.py --file test_ballistics.py  # Run specific file
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_tests(
    test_path: str = "tests/",
    verbose: bool = False,
    coverage: bool = True,
    specific_file: str = None,
    markers: str = None,
    failfast: bool = False,
    parallel: bool = False
) -> int:
    """Run pytest with specified options."""
    
    # Build command
    cmd = ["python", "-m", "pytest"]
    
    # Test path
    if specific_file:
        cmd.append(specific_file)
    else:
        cmd.append(test_path)
    
    # Verbose
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("--tb=short")
    
    # Coverage
    if coverage:
        cmd.extend([
            "--cov=simulator",
            "--cov-report=term-missing",
            "--cov-report=xml:coverage.xml",
            "--cov-report=html:htmlcov"
        ])
    
    # Markers (e.g., "unit", "integration", "slow")
    if markers:
        cmd.extend(["-m", markers])
    
    # Fail fast
    if failfast:
        cmd.append("-x")
    
    # Parallel execution
    if parallel:
        cmd.extend(["-n", "auto"])
    
    # JUnit XML for CI
    cmd.extend(["--junit-xml=test-results.xml"])
    
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)
    
    # Run tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    return result.returncode


def generate_report():
    """Generate test report summary."""
    
    print("\n" + "=" * 60)
    print("TEST REPORT")
    print("=" * 60)
    
    # Check for coverage report
    coverage_file = Path("coverage.xml")
    if coverage_file.exists():
        print("\nCoverage report generated:")
        print("  - htmlcov/index.html (HTML report)")
        print("  - coverage.xml (XML report)")
    
    # Check for test results
    results_file = Path("test-results.xml")
    if results_file.exists():
        print("\nTest results: test-results.xml")
    
    print("\n" + "=" * 60)
    print(f"Completed at: {datetime.now().isoformat()}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Run tests for norad-sim-test"
    )
    
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        default=True,
        help="Run with coverage (default: True)"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Run specific test file"
    )
    
    parser.add_argument(
        "-x", "--failfast",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "-p", "--parallel",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )
    
    args = parser.parse_args()
    
    # Determine markers
    markers = None
    if args.unit:
        markers = "unit"
    elif args.integration:
        markers = "integration"
    
    # Determine coverage
    coverage = args.coverage and not args.no_coverage
    
    # Run tests
    exit_code = run_tests(
        verbose=args.verbose,
        coverage=coverage,
        specific_file=args.file,
        markers=markers,
        failfast=args.failfast,
        parallel=args.parallel
    )
    
    # Generate report
    generate_report()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()