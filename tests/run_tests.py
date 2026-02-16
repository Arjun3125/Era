#!/usr/bin/env python3
"""
ERA Test Runner - Execute and report on all tests and verifications

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --verify-only      # Run verification suite only
    python run_tests.py --unit-only        # Run unit tests only
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --report           # Generate comprehensive report
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import json


class TestRunner:
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.root_dir = self.test_dir.parent
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "suites": {},
            "summary": {}
        }

    def run_all_tests(self, options=""):
        """Run all tests"""
        print("=" * 80)
        print("RUNNING ALL TESTS")
        print("=" * 80)
        cmd = f"pytest {self.test_dir} -v --tb=short {options}"
        return self._execute_command(cmd)

    def run_verification_only(self, options=""):
        """Run verification tests only"""
        print("=" * 80)
        print("RUNNING VERIFICATION SUITE")
        print("=" * 80)
        cmd = f"pytest {self.test_dir}/verification -v --tb=short {options}"
        return self._execute_command(cmd)

    def run_unit_tests_only(self, options=""):
        """Run unit tests only (exclude verification)"""
        print("=" * 80)
        print("RUNNING UNIT TESTS")
        print("=" * 80)
        cmd = f"pytest {self.test_dir} --ignore={self.test_dir}/verification -v --tb=short {options}"
        return self._execute_command(cmd)

    def run_by_marker(self, marker, options=""):
        """Run tests by marker"""
        print("=" * 80)
        print(f"RUNNING TESTS WITH MARKER: {marker}")
        print("=" * 80)
        cmd = f"pytest {self.test_dir} -m {marker} -v --tb=short {options}"
        return self._execute_command(cmd)

    def run_with_coverage(self):
        """Run tests with coverage report"""
        print("=" * 80)
        print("RUNNING TESTS WITH COVERAGE")
        print("=" * 80)
        cmd = f"pytest {self.test_dir} -v --cov={self.root_dir} --cov-report=html --cov-report=term"
        return self._execute_command(cmd)

    def _execute_command(self, cmd):
        """Execute command and return result"""
        try:
            os.chdir(self.root_dir)
            result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"ERROR: {e}")
            return False

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("GENERATING COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        test_count = len(list(self.test_dir.glob("test_*.py")))
        verify_count = len(list(self.test_dir.glob("verification/*.py")))
        total_count = test_count + verify_count
        
        report = f"""
TEST SUITE REPORT
=================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

INVENTORY:
  Core Tests: {test_count}
  Verification Tests: {verify_count}
  Total Test Files: {total_count}

TEST STRUCTURE:
  Location: {self.test_dir}
  Test Discovery: pytest.ini configured
  Fixtures: conftest.py
  Documentation: TEST_MANIFEST.md
  
RUN COMMANDS:
  All tests:          pytest tests/ -v
  Verification only:  pytest tests/verification/ -v
  Unit tests:         pytest tests/ --ignore=tests/verification -v
  By marker:          pytest tests/ -m embedding -v
  With coverage:      pytest tests/ --cov=./ --cov-report=html
  
AVAILABLE MARKERS:
  - unit: Unit tests for components
  - integration: Integration tests
  - e2e: End-to-end tests
  - async: Asynchronous tests
  - embedding: Vector embedding tests
  - ingestion: Data ingestion tests
  - generation: LLM generation tests
  - verification: System verification
  - smoke: Quick smoke tests

NEXT STEPS:
  1. Run: pytest tests/ -v
  2. View results and coverage reports
  3. Check TEST_MANIFEST.md for detailed info
"""
        
        print(report)
        
        # Save report
        report_file = self.test_dir / "TEST_REPORT_GENERATION.txt"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {report_file}")


def main():
    runner = TestRunner()
    
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg == "--verify-only":
            runner.run_verification_only()
        elif arg == "--unit-only":
            runner.run_unit_tests_only()
        elif arg == "--coverage":
            runner.run_with_coverage()
        elif arg == "--report":
            runner.generate_report()
        elif arg.startswith("--marker="):
            marker = arg.replace("--marker=", "")
            runner.run_by_marker(marker)
        else:
            print(f"Unknown option: {arg}")
            print("Use: --verify-only, --unit-only, --coverage, --report, or --marker=<name>")
    else:
        # Default: run all tests
        runner.run_all_tests()


if __name__ == "__main__":
    main()
