#!/usr/bin/env python

import sys
import os
import argparse
import subprocess
import time
import stat
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
import signal
import traceback
from collections import defaultdict, Counter
import cProfile
import pstats
import io
import ast

from graphlib import TopologicalSorter
from modulegraph.modulegraph import ModuleGraph

# Always resolve project root (directory containing 'tests' folder)
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent if SCRIPT_PATH.parent.name == 'tests' else SCRIPT_PATH.parent
PYTHON_DIRS = [PROJECT_ROOT / d for d in ["bin", "utils", "backend", "tests"]]
TEST_DIR = PROJECT_ROOT / "tests"
TMP_DIR = PROJECT_ROOT / "tmp"
XML_DIR = TMP_DIR / "xml"
WORK_DIR = TMP_DIR / "work"
LOGS_DIR = WORK_DIR / "logs"
RESOURCES_DIR = TEST_DIR / "resources"

def read_resource(filename: str) -> str:
    """Read a resource file from tests/resources/ directory"""
    resource_path = RESOURCES_DIR / filename
    with open(resource_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_last_success_time() -> float:
    LAST_SUCCESS_FILE = PROJECT_ROOT / ".last_test_success"
    if LAST_SUCCESS_FILE.exists():
        return float(LAST_SUCCESS_FILE.read_text())
    return 0.0

def _get_file_timestamps() -> dict[str, float]:
    """Get modification timestamps for all Python files"""
    timestamps = {}
    for file_path in collect_python_files():
        try:
            timestamps[str(file_path)] = file_path.stat().st_mtime
        except Exception:
            pass
    return timestamps

def set_last_success_time() -> None:
    LAST_SUCCESS_FILE = PROJECT_ROOT / ".last_test_success"
    LAST_SUCCESS_FILE.write_text(str(time.time()))

def get_modified_files(since: float, exclude_paths: Optional[set[str]] = None) -> list[Path]:
    """Get modified Python files with better filtering"""
    if exclude_paths is None:
        exclude_paths = {'.pytest_cache', '__pycache__', '.git', 'node_modules'}
    
    modified = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_paths]
        
        for f in files:
            if f.endswith('.py'):
                p = Path(root) / f
                try:
                    # Only consider files modified after since time and skip backup/temp files
                    if (p.stat().st_mtime > since and 
                        not f.endswith('.bak') and 
                        not f.startswith('.') and
                        p.stat().st_size > 0):  # Skip empty files
                        modified.append(p)
                except (OSError, PermissionError):
                    continue
    return modified

def get_test_modules_for_files(files: list[Path]) -> list[Path]:
    test_modules = set()
    for f in files:
        # test_runner.py는 테스트 실행기이므로 제외
        if f.name == "test_runner.py":
            continue
        if f.name.startswith("test_") and f.suffix == ".py":
            test_modules.add(f)
        else:
            test_name = f"test_{f.stem}.py"
            test_path = TEST_DIR / test_name
            if test_path.exists():
                test_modules.add(test_path)
    return list(test_modules)

def get_failed_or_skipped_tests() -> list[str]:
    """Get actually failed or skipped tests from pytest cache"""
    # Check if pytest cache exists and has failed tests
    cache_dir = Path(".pytest_cache/v/cache")
    lastfailed_file = cache_dir / "lastfailed"
    
    if not lastfailed_file.exists():
        # No cache file means no failed tests
        return []
    
    try:
        import json
        with open(lastfailed_file, 'r') as f:
            failed_data = json.load(f)
        
        # If the cache is empty or all tests passed, return empty list
        if not failed_data:
            return []
        
        # Extract test paths from the cache
        test_paths = []
        for test_key in failed_data.keys():
            if test_key.startswith("tests/") and "::" in test_key:
                test_paths.append(test_key)
        
        return test_paths
        
    except (json.JSONDecodeError, FileNotFoundError, Exception):
        # If there's any issue reading the cache, assume no failed tests
        return []

def is_test_actually_failed(test_path: Path) -> bool:
    """Check if a test file actually failed based on pytest cache"""
    failed_tests = get_failed_or_skipped_tests()
    test_file_str = str(test_path.relative_to(PROJECT_ROOT))
    
    for failed_test in failed_tests:
        if failed_test.startswith(test_file_str):
            return True
    return False

def clean_test_data() -> None:
    """Clean up existing test data completely"""
    test_dirs_to_clean = [
        TMP_DIR,
        PROJECT_ROOT / "capture_item_naverwebtoon.py",
    ]
    
    for path in test_dirs_to_clean:
        if path.exists():
            if path.is_file():
                path.unlink()
            else:
                import shutil
                shutil.rmtree(path)

def create_test_directories() -> None:
    """Create basic test directory structure"""
    test_dirs = [
        XML_DIR,
        XML_DIR / "img",
        XML_DIR / "pdf",
        WORK_DIR,
        LOGS_DIR,
    ]

    for dir_path in test_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)

def setup_test_environment() -> None:
    """Setup test environment variables and create basic test structure"""
    clean_test_data()
    create_test_directories()
    # Note: Individual test modules should create their own test data

def collect_python_files() -> list[Path]:
    files: list[Path] = []
    for dir_path in PYTHON_DIRS:
        if dir_path.exists():
            files.extend([f.resolve() for f in dir_path.rglob("*.py")])
    return files

def load_modules_to_graph(mg: ModuleGraph, files: list[Path]) -> None:
    """Load Python files into the module graph"""
    for py_file in files:
        try:
            # 파일 경로를 모듈 이름으로 변환
            rel_path = py_file.relative_to(PROJECT_ROOT)
            module_name = '.'.join(rel_path.with_suffix('').parts)

            # import_hook을 사용하여 모듈을 그래프에 추가
            mg.import_hook(module_name, None, None)
        except RuntimeError as e:
            print(f"Warning: Could not load {py_file}: {e}")
        except Exception as e:
            print(f"Warning: Could not load {py_file}: {e}")

def is_test_file(file_path: Path) -> bool:
    """Check if a file is a test file (excluding test_runner.py)"""
    return (file_path.parent == TEST_DIR and
            file_path.name.startswith("test_") and
            file_path.name != "test_runner.py")

def extract_dependencies_from_graph(mg: ModuleGraph) -> dict[Path, set[Path]]:
    """Extract dependencies between test files from the module graph"""
    deps = {}
    for node in mg.flatten():
        if (node.filename and
            is_test_file(Path(node.filename))):
            src = Path(node.filename)
            targets = set()
            _, out_edges = mg.get_edges(node)
            for edge in out_edges:
                if edge is None:
                    continue
                if isinstance(edge, tuple) and len(edge) >= 2:
                    dep = edge[1]
                    if (hasattr(dep, "filename") and
                        dep.filename and
                        is_test_file(Path(dep.filename))):
                        targets.add(Path(dep.filename))
            deps[src] = targets
    return deps

def print_dependency_analysis(deps: dict[Path, set[Path]]) -> None:
    """Print dependency analysis results"""
    print("\n=== Dependency Analysis Results ===")
    for src, targets in deps.items():
        if targets:
            print(f"{src.name} -> {[t.name for t in targets]}")
        else:
            print(f"{src.name} -> (no dependencies)")

def print_execution_order(ordered: list[Path]) -> None:
    """Print test execution order"""
    print("\n=== Test Execution Order ===")
    for i, path in enumerate(ordered, 1):
        print(f"{i:2d}. {path.name}")

def analyze_test_dependencies() -> list[Path]:
    """Analyze dependencies between test files and determine execution order"""
    if not TEST_DIR.exists():
        print(f"Error: {TEST_DIR} directory not found")
        return []

    mg = ModuleGraph()

    # Load test files first
    test_files = [f for f in TEST_DIR.glob("test_*.py") if f.name != "test_runner.py"]
    load_modules_to_graph(mg, test_files)

    # Load other Python files
    other_files = [f for f in collect_python_files() if f not in test_files]
    load_modules_to_graph(mg, other_files)

    # Extract dependencies
    deps = extract_dependencies_from_graph(mg)
    print_dependency_analysis(deps)

    # Topological sort
    try:
        ts = TopologicalSorter(deps)
        ordered = list(ts.static_order())
        print_execution_order(ordered)
        return ordered
    except RuntimeError as e:
        print(f"Error in topological sort: {e}")
        print("Falling back to alphabetical order...")
        return sorted(deps.keys(), key=lambda x: x.name)


def get_test_methods(test_file: Path) -> list[str]:
    """Extract all test methods from a test file"""
    result = subprocess.run([
        sys.executable, "-m", "pytest", str(test_file), "--collect-only"
    ], capture_output=True, text=True, check=False)
    
    # 모든 테스트 메서드 수집 (Test*::test_* 패턴)
    test_methods = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and "::test_" in line:
            test_methods.append(line)
    
    return test_methods


def run_test_modules_sequentially(test_targets: list[Path]) -> tuple[bool, int, int]:
    """Run test modules sequentially and return (success, passed_count, failed_count)"""
    passed_count = 0
    failed_count = 0
    
    for idx, t in enumerate(test_targets, 1):
        print(f"--- [{idx}/{len(test_targets)}] Running: {t} ---")
        # Use absolute path to avoid issues with working directory changes
        absolute_path = t.resolve()

        # Measure execution time
        start_time = time.time()
        result = subprocess.run([sys.executable, "-m", "pytest", "--tb=no", "--disable-warnings", str(absolute_path)],
                              capture_output=True, text=True, check=False)
        end_time = time.time()
        execution_time = end_time - start_time

        # Filter output to remove session start info and show only test results
        filtered_output = []
        in_session_start = False
        for line in result.stdout.splitlines():
            if "test session starts" in line:
                in_session_start = True
                continue
            if in_session_start and ("collected" in line or "platform" in line or "rootdir" in line or
                                   "configfile" in line or "plugins" in line or "cachedir" in line or
                                   "hypothesis profile" in line):
                continue
            if in_session_start and line.strip() == "":
                in_session_start = False
                continue
            if not in_session_start:
                filtered_output.append(line)

        # Print filtered output
        if filtered_output:
            print("\n".join(filtered_output))

        # Update performance cache with actual execution time
        test_file_name = t.name
        update_test_performance_cache(test_file_name, execution_time)

        if result.returncode != 0:
            print(f"❌ {t.name} FAILED.")
            failed_count += 1
        else:
            print(f"✅ {t.name} PASSED.")
            passed_count += 1
    
    overall_success = failed_count == 0
    if overall_success:
        print(f"✅ All {len(test_targets)} tests passed.")
    else:
        print(f"❌ {failed_count} out of {len(test_targets)} tests failed.")
    
    return overall_success, passed_count, failed_count

def run_specific_test_file(test_file: str) -> bool:
    """Run a specific test file"""
    print(f"=== Running Specific Test File: {test_file} ===")
    test_path = Path(test_file)
    if not test_path.exists():
        print(f"Error: Test file {test_file} not found")
        return False

    # Measure execution time
    start_time = time.time()
    result = subprocess.run([
        sys.executable, "-m", "pytest", str(test_path), "-v"
    ], check=False)
    end_time = time.time()
    execution_time = end_time - start_time

    # Update performance cache with actual execution time
    test_file_name = test_path.name
    update_test_performance_cache(test_file_name, execution_time)

    return result.returncode == 0

def get_actual_execution_duration() -> float:
    """Get actual execution duration from cache or return 0 if not available"""
    performance_cache_file = PROJECT_ROOT / ".test_performance_cache"
    
    if performance_cache_file.exists():
        try:
            import json
            with open(performance_cache_file, 'r') as f:
                cached_data = json.load(f)
                # 실제 실행 시간이 저장되어 있다면 반환
                if 'actual_total_duration' in cached_data:
                    return cached_data['actual_total_duration']
        except Exception:
            pass
    
    return 0.0

def update_actual_execution_duration(duration: float) -> None:
    """Update actual execution duration in cache"""
    performance_cache_file = PROJECT_ROOT / ".test_performance_cache"
    
    # Load existing cache
    cached_data = {}
    if performance_cache_file.exists():
        try:
            import json
            with open(performance_cache_file, 'r') as f:
                cached_data = json.load(f)
        except Exception:
            cached_data = {}
    
    # Update actual execution duration
    cached_data['actual_total_duration'] = duration
    cached_data['last_actual_execution'] = time.time()
    
    # Save updated cache
    try:
        import json
        with open(performance_cache_file, 'w') as f:
            json.dump(cached_data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Failed to save actual execution duration: {e}")

def run_all_tests() -> bool:
    """Run all tests in dependency order (개별 파일별로 실행 및 시간 측정)"""
    print("=== Test Dependency Analysis and Execution (All Tests) ===")
    test_files = [f for f in TEST_DIR.glob("test_*.py") if f.name != "test_runner.py"]
    ordered_tests = sorted(test_files, key=lambda x: x.name)
    if not ordered_tests:
        print("No tests to run")
        return False

    total_start = time.time()
    all_passed = True
    for idx, t in enumerate(ordered_tests, 1):
        print(f"--- [{idx}/{len(ordered_tests)}] Running: {t.name} ---")
        start = time.time()
        result = subprocess.run([sys.executable, "-m", "pytest", "--tb=no", "--disable-warnings", str(t)],
                              capture_output=True, text=True, check=False)
        end = time.time()

        # Filter output to remove session start info and show only test results
        filtered_output = []
        in_session_start = False
        for line in result.stdout.splitlines():
            if "test session starts" in line:
                in_session_start = True
                continue
            if in_session_start and ("collected" in line or "platform" in line or "rootdir" in line or
                                   "configfile" in line or "plugins" in line or "cachedir" in line or
                                   "hypothesis profile" in line):
                continue
            if in_session_start and line.strip() == "":
                in_session_start = False
                continue
            if not in_session_start:
                filtered_output.append(line)

        # Print filtered output
        if filtered_output:
            print("\n".join(filtered_output))

        update_test_performance_cache(t.name, end - start)
        if result.returncode != 0:
            all_passed = False
    total_end = time.time()
    update_actual_execution_duration(total_end - total_start)
    print(f"⏱️  실제 총 수행 시간: {total_end - total_start:.1f}초")
    return all_passed

def run_failed_tests() -> bool:
    """Run only failed tests"""
    failed_tests = get_failed_or_skipped_tests()
    if not failed_tests:
        return True

    # Extract test file paths and convert to absolute paths
    test_files: list[Path] = []
    for t in failed_tests:
        file_path = t.split("::")[0]  # Remove test method part
        if file_path.startswith("tests/"):
            # Convert relative path to absolute path
            absolute_path = PROJECT_ROOT / file_path
            if absolute_path.resolve() != Path(__file__).resolve():
                test_files.append(absolute_path)

    # Remove duplicates while preserving order
    unique_test_files: list[Path] = []
    seen: set[Path] = set()
    for t in test_files:
        if t not in seen:
            unique_test_files.append(t)
            seen.add(t)

    print("Running only failed test modules:")
    for t in unique_test_files:
        print(f"  - {t}")

    if not run_test_modules_sequentially(unique_test_files):
        return False

    print("All failed tests passed. Now running changed test modules (if any)...")
    return True

def run_changed_tests() -> bool:
    """Run tests for changed files with dependency consideration"""
    success, _, _ = run_changed_tests_with_results()
    return success

def run_changed_tests_with_results() -> tuple[bool, int, int]:
    """Run tests for changed files and return detailed results"""
    last_success = get_last_success_time()
    modified_files = get_modified_files(last_success)

    # test_runner.py는 테스트 실행기이므로 무시
    modified_files = [f for f in modified_files if f.name != "test_runner.py"]

    if not modified_files:
        print("✅ 변경된 테스트가 없습니다. 아무 테스트도 실행하지 않습니다.")
        return True, 0, 0

    # Get test targets considering import dependencies
    test_targets = get_test_targets_with_dependencies(modified_files)

    if not test_targets:
        print("No test targets found for changed files.")
        return True, 0, 0

    print("\n🎯 Running tests for changed files (with dependency analysis)...")
    print(f"📋 Found {len(test_targets)} test targets for {len(modified_files)} modified files")

    return run_test_modules_sequentially(test_targets)

def get_test_statistics() -> dict[str, Any]:
    """Get comprehensive test performance statistics"""
    # Get all test files
    test_files = [f for f in TEST_DIR.glob("test_*.py") if f.name != "test_runner.py"]

    # Get last success time
    last_success = get_last_success_time()
    last_success_str = "Never" if last_success == 0 else datetime.fromtimestamp(last_success).strftime("%Y-%m-%d %H:%M:%S")

    # Check for failed tests
    failed_tests = get_failed_or_skipped_tests()

    # Get performance data from last pytest run if available
    performance_data = get_pytest_performance_data()

    return {
        "total_test_files": len(test_files),
        "last_success_time": last_success_str,
        "failed_tests_count": len(failed_tests),
        "failed_tests": failed_tests,
        "performance_data": performance_data
    }

def get_pytest_performance_data() -> dict[str, Any]:
    """Extract performance data from actual pytest execution"""
    # Get all test files
    test_files = [f for f in TEST_DIR.glob("test_*.py") if f.name != "test_runner.py"]

    # Try to get actual performance data from pytest cache or recent runs
    performance_cache_file = PROJECT_ROOT / ".test_performance_cache"

    # Default estimated durations (fallback)
    estimated_durations = {
        "test_backend.py": 25.0,
        "test_problem_manager.py": 28.0,
        "test_access_log_manager.py": 28.0,
        "test_headless_browser.py": 14.0,
        "test_crawler.py": 13.0,
        "test_html_file_manager.py": 10.0,
        "test_feed_manager.py": 9.0,
        "test_feed_maker.py": 6.0,
        "test_feed_maker_runner.py": 5.0,
        "test_download_merge_split.py": 2.0,
        "test_download_image.py": 1.0,
    }

    # Try to load cached performance data
    file_durations = {}
    if performance_cache_file.exists():
        try:
            import json
            with open(performance_cache_file, 'r') as f:
                cached_data = json.load(f)
                file_durations = cached_data.get('file_durations', {})
                print(f"📊 Loaded cached performance data for {len(file_durations)} test files")
        except Exception as e:
            print(f"⚠️  Failed to load performance cache: {e}")

    # Fill in missing durations with estimates
    for test_file in test_files:
        file_name = test_file.name
        if file_name not in file_durations:
            file_durations[file_name] = estimated_durations.get(file_name, 0.5)

    # Calculate test counts and average times per test
    file_test_counts = {}
    file_avg_times = {}
    
    for test_file in test_files:
        file_name = test_file.name
        try:
            test_methods = get_test_methods(test_file)
            test_count = len(test_methods)
            file_test_counts[file_name] = test_count
            
            if test_count > 0:
                avg_time = file_durations[file_name] / test_count
                file_avg_times[file_name] = avg_time
            else:
                file_avg_times[file_name] = file_durations[file_name]  # No tests found
        except Exception as e:
            print(f"⚠️  Failed to get test count for {file_name}: {e}")
            file_test_counts[file_name] = 1  # Default to 1
            file_avg_times[file_name] = file_durations[file_name]

    total_duration = sum(file_durations.values())

    return {
        "total_duration": total_duration,
        "file_durations": file_durations,
        "file_test_counts": file_test_counts,
        "file_avg_times": file_avg_times,
        "slowest_files": sorted(file_durations.items(), key=lambda x: x[1], reverse=True)[:10],
        "slowest_avg_times": sorted(file_avg_times.items(), key=lambda x: x[1], reverse=True)[:10]
    }

def update_test_performance_cache(test_file: str, execution_time: float) -> None:
    """Update performance cache with actual test execution time"""
    performance_cache_file = PROJECT_ROOT / ".test_performance_cache"

    # Load existing cache
    cached_data = {}
    if performance_cache_file.exists():
        try:
            import json
            with open(performance_cache_file, 'r') as f:
                cached_data = json.load(f)
        except Exception:
            cached_data = {}

    # Update with new execution time (use exponential moving average)
    file_durations = cached_data.get('file_durations', {})
    alpha = 0.3  # Smoothing factor (30% new, 70% old)

    if test_file in file_durations:
        old_time = file_durations[test_file]
        new_time = alpha * execution_time + (1 - alpha) * old_time
    else:
        new_time = execution_time

    file_durations[test_file] = new_time
    cached_data['file_durations'] = file_durations
    cached_data['last_updated'] = time.time()

    # Save updated cache
    try:
        import json
        with open(performance_cache_file, 'w') as f:
            json.dump(cached_data, f, indent=2)
        print(f"📊 Updated performance cache: {test_file} = {new_time:.2f}s")
    except Exception as e:
        print(f"⚠️  Failed to save performance cache: {e}")

def print_test_statistics(stats: dict[str, Any]) -> None:
    """Print comprehensive test performance statistics"""
    print("\n" + "="*60)
    print("⚡ TEST PERFORMANCE STATISTICS")
    print("="*60)

    perf_data = stats['performance_data']

    print(f"📊 총 테스트 파일 수: {stats['total_test_files']}개")
    print(f"⏰ 마지막 성공 시간: {stats['last_success_time']}")
    print(f"🕐 예상 총 수행 시간: {perf_data['total_duration']:.1f}초")
    
    # 실제 수행 시간 표시 (캐시에서 가져오기)
    actual_duration = get_actual_execution_duration()
    if actual_duration > 0:
        print(f"⏱️  실제 총 수행 시간: {actual_duration:.1f}초")
        if perf_data['total_duration'] > 0:
            improvement = ((perf_data['total_duration'] - actual_duration) / perf_data['total_duration']) * 100
            print(f"📈 성능 개선율: {improvement:.1f}% (예상 대비 {actual_duration/perf_data['total_duration']:.1f}배 빠름)")
    
    print(f"📈 평균 파일당 수행 시간: {perf_data['total_duration']/stats['total_test_files']:.1f}초")

    # Calculate total test count
    total_test_count = sum(perf_data['file_test_counts'].values())
    if total_test_count > 0:
        print(f"🧪 총 테스트 개수: {total_test_count}개")
        print(f"📊 평균 테스트당 수행 시간: {perf_data['total_duration']/total_test_count:.2f}초")

    if stats['failed_tests_count'] > 0:
        print(f"❌ 실패한 테스트: {stats['failed_tests_count']}개")
    else:
        print("✅ 실패한 테스트: 없음")

    print(f"\n🐌 수행 시간이 긴 테스트 파일 TOP 10:")
    for i, (file_name, duration) in enumerate(perf_data['slowest_files'], 1):
        test_count = perf_data['file_test_counts'].get(file_name, 1)
        avg_time = perf_data['file_avg_times'].get(file_name, duration)
        
        if duration >= 10:
            icon = "🔥"  # Very slow
        elif duration >= 5:
            icon = "⚠️ "  # Slow
        elif duration >= 1:
            icon = "📝"  # Medium
        else:
            icon = "⚡"  # Fast

        print(f"   {i:2d}. {icon} {file_name:<35} {duration:>6.1f}초 ({test_count}개 테스트, 평균 {avg_time:.2f}초)")

    print(f"\n🐌 평균 테스트 수행시간이 긴 파일 TOP 10:")
    for i, (file_name, avg_time) in enumerate(perf_data['slowest_avg_times'], 1):
        test_count = perf_data['file_test_counts'].get(file_name, 1)
        total_time = perf_data['file_durations'].get(file_name, 0)
        
        if avg_time >= 5:
            icon = "🔥"  # Very slow per test
        elif avg_time >= 2:
            icon = "⚠️ "  # Slow per test
        elif avg_time >= 0.5:
            icon = "📝"  # Medium per test
        else:
            icon = "⚡"  # Fast per test

        print(f"   {i:2d}. {icon} {file_name:<35} 평균 {avg_time:>6.2f}초 ({test_count}개 테스트, 총 {total_time:.1f}초)")

    # Performance recommendations
    slow_files = [f for f, d in perf_data['file_durations'].items() if d >= 10]
    slow_avg_files = [f for f, avg in perf_data['file_avg_times'].items() if avg >= 2]
    
    if slow_files:
        print(f"\n💡 성능 개선 권장사항:")
        print(f"   • {len(slow_files)}개 파일이 10초 이상 소요됩니다")
        print(f"   • Docker 컨테이너나 네트워크 호출이 있는 테스트 최적화 검토")
    
    if slow_avg_files:
        print(f"   • {len(slow_avg_files)}개 파일의 평균 테스트 시간이 2초 이상입니다")
        print(f"   • 개별 테스트 최적화 검토 필요")

    fast_ratio = len([d for d in perf_data['file_durations'].values() if d < 1]) / len(perf_data['file_durations']) * 100
    fast_avg_ratio = len([avg for avg in perf_data['file_avg_times'].values() if avg < 0.5]) / len(perf_data['file_avg_times']) * 100
    
    print(f"\n📊 성능 지표:")
    print(f"   • 빠른 테스트 비율 (<1초): {fast_ratio:.1f}%")
    print(f"   • 빠른 평균 테스트 비율 (<0.5초): {fast_avg_ratio:.1f}%")
    print(f"   • 병렬 실행 시 예상 시간: {max(perf_data['file_durations'].values()):.1f}초")

    print("="*60)

def profile_slow_tests() -> None:
    """Profile the slowest test files to identify bottlenecks"""
    print("\n🔬 STATISTICAL PROFILING MODE")
    print("=" * 60)
    print("소스코드 변경 없이 통계적 샘플링으로 성능 분석을 수행합니다.")
    print("0.5초마다 실행 지점을 샘플링하여 핫스팟을 찾습니다.")

    # Get estimated slow tests
    perf_data = get_pytest_performance_data()
    slow_tests = [name for name, duration in perf_data['slowest_files'][:5] if duration >= 5.0]

    print(f"\n📋 분석 대상 테스트 파일 ({len(slow_tests)}개):")
    for test_name in slow_tests:
        print(f"   • {test_name}")

    print(f"\n🚀 프로파일링 시작...")

    all_analyses = []

    for test_name in slow_tests:
        test_path = TEST_DIR / test_name
        if not test_path.exists():
            print(f"⚠️  파일을 찾을 수 없음: {test_name}")
            continue

        success, analysis = run_test_with_profiling(test_path)
        all_analyses.append(analysis)

        if analysis['total_samples'] > 0:
            print_profiling_analysis(analysis)
        else:
            print(f"⚡ {test_name}: 너무 빨라서 샘플링되지 않음 ({analysis['execution_time']:.2f}초)")

    # Overall summary
    print(f"\n📈 전체 프로파일링 요약:")
    total_samples = sum(a['total_samples'] for a in all_analyses)
    total_time = sum(a['execution_time'] for a in all_analyses)

    print(f"   • 총 실행 시간: {total_time:.2f}초")
    print(f"   • 총 샘플 수: {total_samples}개")
    if total_time > 0:
        print(f"   • 평균 샘플링 밀도: {total_samples/total_time:.1f} 샘플/초")

def run_test_with_profiling(test_file: Path) -> tuple[bool, dict[str, Any]]:
    """Run a single test file with profiling"""
    print(f"🔬 Profiling: {test_file.name}")

    # Create a cProfile profiler
    profiler = cProfile.Profile()

    start_time = time.time()

    try:
        # Start profiling
        profiler.enable()

        # Import pytest to run tests in the same process
        import pytest

        # Run pytest with the test file in the current process
        exit_code = pytest.main([
            str(test_file),
            "-v",
            "--tb=short"  # Quiet mode to reduce output noise
        ])

        success = exit_code == 0

    except Exception as e:
        print(f"Error running test: {e}")
        success = False
    finally:
        # Stop profiling
        profiler.disable()

    end_time = time.time()
    execution_time = end_time - start_time

    # Analyze profiling results
    analysis = analyze_cprofile_results(profiler, execution_time, test_file.name)
    analysis['success'] = success

    return success, analysis

def analyze_cprofile_results(profiler: cProfile.Profile, execution_time: float, test_file: str) -> dict[str, Any]:
    """Analyze cProfile results and extract meaningful insights"""

    # Create string buffer to capture pstats output
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)

    # Sort by cumulative time and get stats
    ps.sort_stats('cumulative')

    # Get total calls and primitive calls from stats
    total_calls = 0
    for func_data in ps.stats.values():
        total_calls += func_data[0]  # primitive calls

    # Extract function statistics
    function_stats = []
    for func, (cc, nc, tt, ct, callers) in ps.stats.items():
        filename, line_number, function_name = func

        # Only include relevant files (skip standard library)
        if any(path in filename for path in ['/tests/', '/bin/', '/utils/', 'test_', 'crawler', 'feed_maker']):
            function_stats.append({
                'filename': Path(filename).name,
                'line': line_number,
                'function': function_name,
                'calls': nc,  # primitive calls
                'total_calls': cc,  # total calls including recursive
                'total_time': tt,  # total time spent in function
                'cumulative_time': ct,  # cumulative time including subcalls
                'time_per_call': tt / nc if nc > 0 else 0,
                'cum_time_per_call': ct / nc if nc > 0 else 0
            })

    # Sort by cumulative time
    function_stats.sort(key=lambda x: x['cumulative_time'], reverse=True)

    # Find hotspots (functions taking most time)
    hotspots = function_stats[:15]

    # Find most called functions
    most_called = sorted(function_stats, key=lambda x: x['calls'], reverse=True)[:10]

    # Find functions with highest time per call
    slowest_per_call = sorted(
        [f for f in function_stats if f['calls'] > 0],
        key=lambda x: x['time_per_call'],
        reverse=True
    )[:10]

    # File-level aggregation with type annotation
    file_stats: dict[str, dict[str, float | int]] = defaultdict(lambda: {
        'total_time': 0,
        'cumulative_time': 0,
        'calls': 0,
        'functions': 0
    })

    for func_stat in function_stats:
        filename = func_stat['filename']
        file_stats[filename]['total_time'] += func_stat['total_time']
        file_stats[filename]['cumulative_time'] += func_stat['cumulative_time']
        file_stats[filename]['calls'] += func_stat['calls']
        file_stats[filename]['functions'] += 1

    # Convert to list and sort
    file_stats_list = [
        {
            'filename': filename,
            **stats
        }
        for filename, stats in file_stats.items()
    ]
    file_stats_list.sort(key=lambda x: x['cumulative_time'], reverse=True)

    return {
        'test_file': test_file,
        'execution_time': execution_time,
        'total_calls': total_calls,
        'function_count': len(function_stats),
        'hotspots': hotspots,
        'most_called': most_called,
        'slowest_per_call': slowest_per_call,
        'file_stats': file_stats_list[:10]
    }

def print_profiling_analysis(analysis: dict[str, Any]) -> None:
    """Print profiling analysis results"""
    print(f"\n🔬 PROFILING ANALYSIS: {analysis['test_file']}")
    print(f"{'='*80}")

    print(f"⏱️  총 실행 시간: {analysis['execution_time']:.3f}초")
    print(f"📞 총 함수 호출: {analysis['total_calls']:,}회")
    print(f"🔧 분석된 함수: {analysis['function_count']}개")

    # Top hotspots by cumulative time
    print(f"\n🔥 성능 핫스팟 (누적 시간 기준 TOP 15):")
    print(f"{'Rank':<4} {'File':<25} {'Function':<25} {'Calls':<8} {'Total(s)':<8} {'Cumul(s)':<8} {'Per Call(ms)':<12}")
    print("-" * 100)
    for i, func in enumerate(analysis['hotspots'], 1):
        print(f"{i:<4} {func['filename']:<25} {func['function']:<25} "
              f"{func['calls']:<8} {func['total_time']:<8.3f} {func['cumulative_time']:<8.3f} "
              f"{func['time_per_call']*1000:<12.2f}")

    # Most called functions
    print(f"\n📞 가장 많이 호출된 함수 TOP 10:")
    print(f"{'Rank':<4} {'Calls':<10} {'File':<25} {'Function':<25} {'Total(s)':<8}")
    print("-" * 80)
    for i, func in enumerate(analysis['most_called'], 1):
        print(f"{i:<4} {func['calls']:<10} {func['filename']:<25} {func['function']:<25} "
              f"{func['total_time']:<8.3f}")

    # Slowest functions per call
    print(f"\n🐌 호출당 가장 느린 함수 TOP 10:")
    print(f"{'Rank':<4} {'Per Call(ms)':<12} {'Calls':<8} {'File':<25} {'Function':<25}")
    print("-" * 80)
    for i, func in enumerate(analysis['slowest_per_call'], 1):
        print(f"{i:<4} {func['time_per_call']*1000:<12.2f} {func['calls']:<8} "
              f"{func['filename']:<25} {func['function']:<25}")

    # File-level summary
    print(f"\n📁 파일별 성능 요약:")
    print(f"{'Rank':<4} {'File':<30} {'Functions':<9} {'Calls':<10} {'Total(s)':<8} {'Cumul(s)':<8}")
    print("-" * 80)
    for i, file_stat in enumerate(analysis['file_stats'], 1):
        print(f"{i:<4} {file_stat['filename']:<30} {file_stat['functions']:<9} "
              f"{file_stat['calls']:<10} {file_stat['total_time']:<8.3f} {file_stat['cumulative_time']:<8.3f}")

    # Performance recommendations
    print(f"\n💡 성능 개선 권장사항:")
    top_hotspot = analysis['hotspots'][0] if analysis['hotspots'] else None
    if top_hotspot:
        print(f"   • 최대 병목점: {top_hotspot['filename']}::{top_hotspot['function']}")
        print(f"     - 누적 시간: {top_hotspot['cumulative_time']:.3f}초 "
              f"({top_hotspot['cumulative_time']/analysis['execution_time']*100:.1f}%)")

    top_called = analysis['most_called'][0] if analysis['most_called'] else None
    if top_called and top_called['calls'] > 1000:
        print(f"   • 과도한 호출: {top_called['filename']}::{top_called['function']}")
        print(f"     - {top_called['calls']:,}회 호출, 캐싱 또는 최적화 고려")

    slow_per_call = analysis['slowest_per_call'][0] if analysis['slowest_per_call'] else None
    if slow_per_call and slow_per_call['time_per_call'] > 0.001:
        print(f"   • 느린 함수: {slow_per_call['filename']}::{slow_per_call['function']}")
        print(f"     - 호출당 {slow_per_call['time_per_call']*1000:.2f}ms, 내부 로직 최적화 필요")

    print(f"{'='*80}")

def get_status_emoji(path: Path, executed_tests: Optional[set[Path]] = None,
                    target_tests: Optional[set[Path]] = None, failed_tests: Optional[set[Path]] = None,
                    passed_tests: Optional[set[Path]] = None, deps: Optional[dict[Path, set[Path]]] = None,
                    reverse_deps: Optional[dict[Path, set[Path]]] = None,
                    modified_files: Optional[set[Path]] = None,
                    affected_files: Optional[set[Path]] = None,
                    all_mode: bool = False) -> str:
    """Unified function to get status emoji for a file (일반 모듈도 테스트 상태 반영)"""
    if executed_tests is None:
        executed_tests = set()
    if target_tests is None:
        target_tests = set()
    if failed_tests is None:
        failed_tests = set()
    if passed_tests is None:
        passed_tests = set()
    if modified_files is None:
        modified_files = set()
    if affected_files is None:
        affected_files = set()

    # 테스트 모듈인 경우
    if is_test_module(path):
        if path in failed_tests:
            return "🔴"
        if path in passed_tests:
            return "🟢"
        if path in modified_files:
            return "🔵"  # 실제로 수정된 테스트 파일
        if all_mode and path not in modified_files:
            return "🟣"  # -a 옵션일 때 전체 테스트 대상
        if path in target_tests and path not in modified_files:
            return "🟣"  # 의존성으로 인해 실행되는 테스트 대상
        return "⚪"  # Untested

    # 일반 모듈인 경우: 더 명확한 상태 표시
    if not is_test_module(path):
        if path in modified_files:
            return "🔵"  # Modified
        test_modules = set()
        if deps and reverse_deps:
            test_modules = _get_test_modules_for_file(path, deps, reverse_deps)
        if test_modules:
            has_failed = any(test in failed_tests for test in test_modules)
            has_passed = any(test in passed_tests for test in test_modules)
            if has_failed:
                return "🔴"
            elif has_passed:
                return "🟢"
            else:
                if path in affected_files:
                    return "🟡"  # Included due to dependency
                else:
                    return "⚪"
        else:
            if path in affected_files:
                return "🟡"
            else:
                return "⚪"
    return "⚪"


def is_test_module(path: Path) -> bool:
    """테스트 모듈 판별 함수 (Path.resolve()된 경로도 지원)"""
    resolved_path = path.resolve()
    resolved_test_dir = TEST_DIR.resolve()
    return (resolved_path.name.startswith("test_") and 
            resolved_path.suffix == ".py" and 
            resolved_path.parent == resolved_test_dir and 
            resolved_path.name != "test_runner.py")


def _get_test_modules_for_file(file_path: Path, deps: dict[Path, set[Path]], 
                              reverse_deps: dict[Path, set[Path]]) -> set[Path]:
    """파일을 테스트하는 테스트 모듈들을 찾기"""
    test_modules = set()
    
    # 1. 직접적인 테스트 모듈 찾기 (test_파일명.py)
    possible_test_names = [
        f"test_{file_path.stem}.py",
        f"test_{file_path.name}",
        f"test_{file_path.stem.replace('feed_maker_util_', 'feed_maker_util_')}.py"
    ]
    
    for test_name in possible_test_names:
        test_path = TEST_DIR / test_name
        if is_test_module(test_path) and test_path.exists():
            test_modules.add(test_path)
    
    # 2. 의존성 그래프에서 이 파일을 import하는 테스트 모듈들 찾기
    if file_path in reverse_deps:
        for importing_file in reverse_deps[file_path]:
            if is_test_module(importing_file):
                test_modules.add(importing_file)
    
    return test_modules


def extract_imports_from_file(file_path: Path) -> set[str]:
    """Extract all import statements from a Python file using AST"""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except Exception as e:
        print(f"Warning: Could not parse imports from {file_path}: {e}")

    return imports

def build_dependency_graph() -> dict[Path, set[Path]]:
    """Build dependency graph by parsing import statements in all Python files"""
    deps = {}
    all_files = collect_python_files()

    # Create a mapping from module name to file path
    module_to_path = {}
    for file_path in all_files:
        rel_path = file_path.relative_to(PROJECT_ROOT)
        module_name = '.'.join(rel_path.with_suffix('').parts)
        module_to_path[module_name] = file_path

    # Parse imports for each file
    for file_path in all_files:
        deps[file_path] = set()
        imports = extract_imports_from_file(file_path)

        for import_name in imports:
            # Handle relative imports
            if import_name.startswith('.'):
                # Convert relative import to absolute
                rel_path = file_path.relative_to(PROJECT_ROOT)
                parts = list(rel_path.with_suffix('').parts)
                dots = len(import_name) - len(import_name.lstrip('.'))
                if dots <= len(parts):
                    parts = parts[:-dots]
                    import_name = '.'.join(parts + [import_name.lstrip('.')])

            # Find the corresponding file
            if import_name in module_to_path:
                deps[file_path].add(module_to_path[import_name])

    return deps

def analyze_all_dependencies() -> tuple[dict[Path, set[Path]], dict[Path, set[Path]]]:
    """Analyze dependencies between all Python files with performance optimization"""
    if not TEST_DIR.exists():
        print(f"Error: {TEST_DIR} directory not found")
        return {}, {}

    # Performance optimization: Cache dependency analysis
    cache_file = PROJECT_ROOT / ".dependency_cache"
    cache_data = {}
    
    # Try to load cached dependencies
    if cache_file.exists():
        try:
            import json
            import pickle
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Check if cache is still valid (based on file modification times)
            if _is_dependency_cache_valid(cache_data):
                print("📦 Using cached dependency analysis (performance optimized)")
                return cache_data.get('deps', {}), cache_data.get('reverse_deps', {})

        except Exception:
            pass

    print("🔍 Performing fresh dependency analysis...")
    start_time = time.time()
    
    # Use AST-based dependency analysis instead of ModuleGraph
    deps = build_dependency_graph()
    reverse_deps = get_reverse_dependencies(deps)
    
    elapsed = time.time() - start_time
    print(f"✅ Dependency analysis completed in {elapsed:.2f}s")

    # Cache the results
    try:
        import pickle
        cache_data = {
            'deps': deps,
            'reverse_deps': reverse_deps,
            'timestamp': time.time(),
            'file_timestamps': _get_file_timestamps()
        }
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
    except Exception as e:
        print(f"⚠️  Failed to cache dependencies: {e}")

    return deps, reverse_deps

def get_reverse_dependencies(deps: dict[Path, set[Path]]) -> dict[Path, set[Path]]:
    """Get reverse dependencies (who imports this file)"""
    reverse_deps: dict[Path, set[Path]] = {}
    
    for src, targets in deps.items():
        for target in targets:
            if target not in reverse_deps:
                reverse_deps[target] = set()
            reverse_deps[target].add(src)
    
    return reverse_deps

def get_affected_files(modified_files: list[Path], deps: dict[Path, set[Path]], 
                      reverse_deps: dict[Path, set[Path]], max_depth: int = 2) -> set[Path]:
    """Get all files affected by the modified files (limited recursive dependency tracking)"""
    affected = set(modified_files)
    to_process = [(f, 0) for f in modified_files]  # (file, depth)
    processed = set()
    
    # 제한된 깊이로 영향을 받는 파일을 찾기
    while to_process:
        current_file, depth = to_process.pop(0)
        if current_file in processed or depth >= max_depth:
            continue
            
        processed.add(current_file)
        
        # 현재 파일을 import하는 파일들을 찾기 (한 단계만)
        if current_file in reverse_deps:
            importers = reverse_deps[current_file]
            for importer in importers:
                if importer not in affected:
                    affected.add(importer)
                    to_process.append((importer, depth + 1))
    
    return affected

def print_simple_dependency_tree(deps: dict[Path, set[Path]], 
                                focus_files: Optional[set[Path]] = None,
                                max_depth: int = 2,
                                executed_tests: Optional[set[Path]] = None,
                                target_tests: Optional[set[Path]] = None,
                                failed_tests: Optional[set[Path]] = None,
                                passed_tests: Optional[set[Path]] = None,
                                reverse_deps: Optional[dict[Path, set[Path]]] = None,
                                modified_files: Optional[set[Path]] = None,
                                affected_files: Optional[set[Path]] = None) -> None:
    """Print dependency tree with test modules as root and general modules as children (multi-level, branch lines)"""
    print("\n" + "="*80)
    print("🌳 TEST-ROOTED DEPENDENCY TREE (with branches)")
    print("="*80)
    print(f"📋 의존성을 최대 {max_depth}단계까지 나무 형태로 출력합니다.")
    print("-"*80)
    print("  🟢 Success  🔴 Failed  🔵 Modified  🟡 Included  ⚪ Untested")
    print("  (일반 모듈도 해당 테스트의 성공/실패 상태를 반영)")
    print("-"*80)

    if executed_tests is None:
        executed_tests = set()
    if target_tests is None:
        target_tests = set()
    if failed_tests is None:
        failed_tests = set()
    if passed_tests is None:
        passed_tests = set()
    if modified_files is None:
        modified_files = set()
    if affected_files is None:
        affected_files = set()

    # 트리의 루트는 항상 테스트 모듈로 제한
    if focus_files:
        # focus_files 중 테스트 모듈만
        files_to_show = sorted([f.resolve() for f in focus_files if is_test_module(f)], key=lambda x: str(x))
        title = f"FOCUSED TESTS ({len(files_to_show)} files)"
    else:
        # 전체 테스트 모듈
        all_files = set(deps.keys())
        test_modules = [f.resolve() for f in all_files if is_test_module(f)]
        files_to_show = sorted(test_modules, key=lambda x: str(x))
        title = f"ALL TEST MODULES ({len(files_to_show)} files)"

    print(f"🎯 {title}")
    print("-"*80)

    for idx, file_path in enumerate(files_to_show):
        if file_path in deps:
            is_last = (idx == len(files_to_show) - 1)
            # 각 테스트 모듈별로 visited 집합 분리
            _print_branch_tree_node(file_path, deps, max_depth, 0, set(),
                                  executed_tests, target_tests, failed_tests, passed_tests,
                                  prefix="", is_last=is_last, reverse_deps=reverse_deps,
                                  modified_files=modified_files, affected_files=affected_files)

    print("-"*80)
    print(f"📊 Summary: {len(files_to_show)} test modules (max depth: {max_depth})")
    print("="*80)


def _print_branch_tree_node(node: Path, deps: dict[Path, set[Path]], 
                           max_depth: int, current_depth: int, visited: set[Path],
                           executed_tests: set[Path], target_tests: set[Path], 
                           failed_tests: set[Path], passed_tests: set[Path],
                           prefix: str = "", is_last: bool = True,
                           reverse_deps: Optional[dict[Path, set[Path]]] = None,
                           modified_files: Optional[set[Path]] = None,
                           affected_files: Optional[set[Path]] = None) -> None:
    """Print a tree node with branches (─, └─, ├─, │ 등) - 일반 모듈도 테스트 상태 반영"""
    node = node.resolve()
    if current_depth > max_depth or node in visited:
        return
    
    visited.add(node)
    
    # Get status emoji (일반 모듈도 테스트 상태 반영)
    status = get_status_emoji(node, executed_tests, target_tests, failed_tests, passed_tests,
                             deps, reverse_deps, modified_files, affected_files)
    
    # Handle invalid paths
    try:
        node_rel = node.relative_to(PROJECT_ROOT)
    except ValueError:
        # Skip invalid paths
        return
    
    branch = prefix[:-4] + ("└── " if is_last else "├── ") if current_depth > 0 else ""
    print(f"{prefix}{branch}{status} {node_rel}")
    
    if current_depth >= max_depth:
        return
    
    dependencies = sorted([dep.resolve() for dep in deps.get(node, set())], key=lambda x: str(x))
    unvisited_deps = [dep for dep in dependencies if dep not in visited]
    for i, dep in enumerate(unvisited_deps):
        is_last_dep = (i == len(unvisited_deps) - 1)
        child_prefix = prefix + ("    " if is_last else "│   ")
        _print_branch_tree_node(dep, deps, max_depth, current_depth + 1, visited.copy(),
                               executed_tests, target_tests, failed_tests, passed_tests,
                               child_prefix, is_last_dep, reverse_deps, modified_files, affected_files)


def get_test_targets_with_dependencies(modified_files: list[Path]) -> list[Path]:
    """Get test targets considering import dependencies (실패한 테스트 또는 미수행 테스트만 포함)"""
    deps, reverse_deps = analyze_all_dependencies()

    # test_runner.py는 테스트 실행기이므로 무시
    modified_files = [f for f in modified_files if f.name != "test_runner.py"]

    if not modified_files:
        print("📋 No relevant files changed (test_runner.py changes are ignored)")
        return []

    # Get all affected files with limited depth
    affected_files = get_affected_files(modified_files, deps, reverse_deps, max_depth=2)

    # Get failed tests to include their dependencies
    failed_tests = get_failed_or_skipped_tests()
    failed_test_paths = set()
    for failed_test in failed_tests:
        if "::" in failed_test:
            test_file = failed_test.split("::")[0]
            test_path = Path(test_file)
            if test_path.exists():
                failed_test_paths.add(test_path)

    # pytest 캐시에서 이미 성공한 테스트 모듈 추출 (개선된 버전)
    def get_passed_tests() -> set[Path]:
        cache_dir = Path(".pytest_cache/v/cache")
        lastfailed_file = cache_dir / "lastfailed"
        
        # 실패한 테스트 파일 수집
        failed_files = set()
        if lastfailed_file.exists():
            try:
                import json
                with open(lastfailed_file, 'r') as f:
                    failed_data = json.load(f)
                for test_key in failed_data.keys():
                    if test_key.startswith("tests/") and "::" in test_key:
                        test_file_path = PROJECT_ROOT / test_key.split("::")[0]
                        if test_file_path.exists():
                            failed_files.add(test_file_path.resolve())
            except Exception:
                pass
        
        # 전체 테스트 목록
        all_tests = set()
        for test_file in TEST_DIR.glob("test_*.py"):
            if test_file.name != "test_runner.py":
                all_tests.add(test_file.resolve())
        
        # 성공한 테스트 = 전체 - 실패 하지만, 너무 공격적이면 빈 set 반환
        passed_tests = all_tests - failed_files
        
        # 만약 실패한 테스트가 2개 이하라면 대부분 성공한 것으로 간주
        if len(failed_files) <= 2:
            return passed_tests
        else:
            # 너무 많이 실패하면 전체 재실행 필요
            return set()

    # Convert affected files to test targets (테스트 모듈만)
    test_targets = []
    for file_path in affected_files:
        if is_test_module(file_path):
            test_targets.append(file_path)
        else:
            # For non-test files, find corresponding test file
            possible_test_names = [
                f"test_{file_path.stem}.py",
                f"test_{file_path.name}",
                f"test_{file_path.stem.replace('feed_maker_util_', 'feed_maker_util_')}.py"
            ]
            for test_name in possible_test_names:
                test_path = TEST_DIR / test_name
                if is_test_module(test_path) and test_path.exists():
                    test_targets.append(test_path)
                    break

    # Add tests for failed test modules
    for failed_test_path in failed_test_paths:
        if is_test_module(failed_test_path):
            test_targets.append(failed_test_path)

    # Add tests for general modules that have failed tests
    for file_path in affected_files:
        if not is_test_module(file_path):
            test_modules = _get_test_modules_for_file(file_path, deps, reverse_deps)
            for test_module in test_modules:
                if test_module in failed_test_paths:
                    test_targets.append(test_module)

    # Remove duplicates and test_runner.py
    unique_targets = []
    seen = set()
    for target in test_targets:
        if target.name != "test_runner.py" and target not in seen:
            unique_targets.append(target)
            seen.add(target)

    # 이미 성공한 테스트 모듈은 제외
    passed_tests = get_passed_tests()
    unique_targets = [t for t in unique_targets if t not in passed_tests]

    # Debug output (improved)
    print(f"🔍 Debug: Modified files ({len(modified_files)}): {[f.name for f in modified_files[:5]]}{'...' if len(modified_files) > 5 else ''}")
    print(f"🔍 Debug: Affected files ({len(affected_files)}): {[f.name for f in list(affected_files)[:5]]}{'...' if len(affected_files) > 5 else ''}")
    print(f"🔍 Debug: Failed tests ({len(failed_test_paths)}): {[f.name for f in failed_test_paths]}")
    print(f"🔍 Debug: Test targets ({len(unique_targets)}): {[f.name for f in unique_targets]}")
    
    if len(unique_targets) > 10:
        print(f"⚠️  Warning: {len(unique_targets)} tests selected. This might be too many. Consider running with -f flag for specific tests.")

    return unique_targets


def print_global_dependency_tree(deps: dict[Path, set[Path]], max_depth: int = 10,
                                 executed_tests: Optional[set[Path]] = None, target_tests: Optional[set[Path]] = None,
                                 failed_tests: Optional[set[Path]] = None, passed_tests: Optional[set[Path]] = None,
                                 reverse_deps: Optional[dict[Path, set[Path]]] = None,
                                 modified_files: Optional[set[Path]] = None,
                                 affected_files: Optional[set[Path]] = None,
                                 all_mode: bool = False):
    """테스트 파일을 루트로 하여 전체 import chain을 트리로 출력"""
    test_modules = [f for f in deps.keys() if is_test_module(f)]
    print("\n=== GLOBAL DEPENDENCY TREE ===")
    for idx, test_file in enumerate(sorted(test_modules, key=str)):
        status = get_status_emoji(test_file, executed_tests, target_tests, failed_tests, passed_tests,
                                 deps, reverse_deps, modified_files, affected_files, all_mode=all_mode)
        print(f"{status} {test_file.name}")
        _print_global_branch_tree_node(test_file, deps, max_depth, 1, set([test_file]), "    ",
                                      executed_tests, target_tests, failed_tests, passed_tests,
                                      reverse_deps, modified_files, affected_files, all_mode=all_mode)

def _print_global_branch_tree_node(node: Path, deps: dict[Path, set[Path]], max_depth: int, current_depth: int, visited: set[Path], prefix: str,
                                  executed_tests: Optional[set[Path]] = None, target_tests: Optional[set[Path]] = None,
                                  failed_tests: Optional[set[Path]] = None, passed_tests: Optional[set[Path]] = None,
                                  reverse_deps: Optional[dict[Path, set[Path]]] = None,
                                  modified_files: Optional[set[Path]] = None,
                                  affected_files: Optional[set[Path]] = None,
                                  all_mode: bool = False):
    if current_depth > max_depth:
        return
    for dep in sorted(deps.get(node, set()), key=str):
        if dep in visited:
            continue
        status = get_status_emoji(dep, executed_tests, target_tests, failed_tests, passed_tests,
                                 deps, reverse_deps, modified_files, affected_files, all_mode=all_mode)
        print(f"{prefix}└─ {status} {dep.name}")
        visited.add(dep)
        _print_global_branch_tree_node(dep, deps, max_depth, current_depth + 1, visited, prefix + "    ",
                                      executed_tests, target_tests, failed_tests, passed_tests,
                                      reverse_deps, modified_files, affected_files, all_mode=all_mode)

def main() -> bool:
    """Main function"""
    # Change working directory to tests directory for consistent test execution
    os.chdir(TEST_DIR)

    parser = argparse.ArgumentParser(description="Test runner with dependency analysis")
    parser.add_argument("-a", "--all", action="store_true",
                       help="Run all tests in dependency order (default: run changed modules + previously failed tests)")
    parser.add_argument("-f", "--file", type=str,
                       help="Run a specific test file (e.g., test_feed_maker_util_path_util.py)")
    parser.add_argument("-p", "--profile", type=str, metavar="TEST_MODULE",
                       help="Profile a specific test module using detailed cProfile analysis (e.g., test_crawler.py)")
    args = parser.parse_args()

    # Setup test environment first, before any imports that might depend on environment variables
    setup_test_environment()

    # Always perform dependency analysis first and print the graph
    print("🔍 Analyzing dependencies...")
    deps, reverse_deps = analyze_all_dependencies()

    # Initialize test status tracking
    executed_tests = set()
    target_tests = set()
    failed_tests = set()
    passed_tests = set()

    # Calculate modified and affected files
    last_success = get_last_success_time()
    modified_files = set(get_modified_files(last_success))
    affected_files = get_affected_files(list(modified_files), deps, reverse_deps, max_depth=2) if modified_files else set()

    # Print dependency graph based on the mode
    if args.file:
        # For specific file, show dependencies of that file
        test_path = Path(args.file)
        if test_path.exists():
            target_tests = {test_path}
            print(f"🎯 Running test: {args.file}")
            print(f"📋 Dependencies: {len(deps.get(test_path, set()))} modules")
        else:
            print(f"❌ Test file not found: {args.file}")
            return False
    elif args.all:
        # For all tests, show all test dependencies
        test_files = [f for f in TEST_DIR.glob("test_*.py") if f.name != "test_runner.py"]
        target_tests = set(test_files)
        print(f"🎯 Running all tests: {len(target_tests)} files")
    else:
        # For default mode, show dependencies for changed files
        if modified_files:
            test_targets = get_test_targets_with_dependencies(list(modified_files))
            target_tests = set(test_targets)
            print(f"🎯 Running tests for modified files: {len(target_tests)} files")
            print(f"📋 Modified files: {[f.name for f in modified_files]}")
        else:
            print("📋 No changed files detected")
            target_tests = set()

    # === Global dependency tree 출력 (한 번만) ===
    # test_runner.py가 수정된 경우에도 실제 의존성만 표시 (all_mode=False)
    print_global_dependency_tree(deps, max_depth=10, executed_tests=executed_tests, target_tests=target_tests,
                                 failed_tests=failed_tests, passed_tests=passed_tests, reverse_deps=reverse_deps,
                                 modified_files=modified_files, affected_files=affected_files, all_mode=args.all)
    # === 끝 ===

    success = False
    
    if args.profile:
        # Profile the specified test module
        test_module = args.profile
        if not test_module.endswith('.py'):
            test_module += '.py'

        test_path = TEST_DIR / test_module
        if not test_path.exists():
            print(f"❌ 테스트 모듈을 찾을 수 없습니다: {test_module}")
            print(f"   경로: {test_path}")
            return False

        print(f"\n🔬 DETAILED PROFILING MODE")
        print("=" * 80)
        print(f"대상 모듈: {test_module}")
        print("Python cProfile을 사용한 정밀한 성능 분석을 수행합니다.")
        print("모든 함수 호출과 실행 시간을 추적하여 상세한 프로파일링 결과를 제공합니다.")

        success, analysis = run_test_with_profiling(test_path)

        if analysis.get('function_count', 0) > 0:
            print_profiling_analysis(analysis)
        else:
            print("⚠️  프로파일링 데이터를 수집할 수 없었습니다.")

        return success
    elif args.file:
        success = run_specific_test_file(args.file)
        # Update test status after execution
        if success:
            executed_tests.add(Path(args.file))
            passed_tests.add(Path(args.file))
        else:
            executed_tests.add(Path(args.file))
            failed_tests.add(Path(args.file))
    elif args.all:
        success = run_all_tests()
        # Update test status after execution
        test_files = [f for f in TEST_DIR.glob("test_*.py") if f.name != "test_runner.py"]
        for test_file in test_files:
            executed_tests.add(test_file)
            if success:
                passed_tests.add(test_file)
            else:
                failed_tests.add(test_file)
    else:
        # Default behavior: run failed tests first, then changed tests
        failed_tests_success = run_failed_tests()
        if not failed_tests_success:
            return False
        
        # Run changed tests and get detailed results
        success, passed_count, failed_count = run_changed_tests_with_results()
        
        print(f"\n📋 Test execution completed: {passed_count} passed, {failed_count} failed")
        
        # Update test status after execution
        last_success = get_last_success_time()
        modified_files = get_modified_files(last_success)
        if modified_files:
            test_targets = get_test_targets_with_dependencies(modified_files)
            for test_target in test_targets:
                executed_tests.add(test_target)
                # Check actual test result from pytest cache
                if is_test_actually_failed(test_target):
                    failed_tests.add(test_target)
                else:
                    passed_tests.add(test_target)
        
        # Override success based on actual results
        success = failed_count == 0
    
    # Update last success time if tests passed
    if success:
        set_last_success_time()
        print_test_statistics(get_test_statistics())
    
    # Print final dependency tree with actual test results (간결하게)
    if executed_tests:
        print("\n" + "="*80)
        print("🎯 TEST RESULTS SUMMARY")
        print("="*80)
        print(f"✅ Passed: {len(passed_tests)} tests")
        print(f"❌ Failed: {len(failed_tests)} tests")
        print(f"📋 Total executed: {len(executed_tests)} tests")
        
        if len(passed_tests) > 0:
            print(f"✅ Passed tests: {[t.name for t in list(passed_tests)[:5]]}{'...' if len(passed_tests) > 5 else ''}")
        if len(failed_tests) > 0:
            print(f"❌ Failed tests: {[t.name for t in failed_tests]}")

        # 실패한 테스트가 있을 때만 상세 트리 출력
        if failed_tests:
            print("\n🔴 FAILED TESTS DEPENDENCY TREE:")
            print_simple_dependency_tree(deps, focus_files=failed_tests, max_depth=3,
                                       target_tests=target_tests, reverse_deps=reverse_deps,
                                       executed_tests=executed_tests, failed_tests=failed_tests, passed_tests=passed_tests,
                                       modified_files=modified_files, affected_files=affected_files)
    
    return success


if __name__ == "__main__":
    test_success = main()
    sys.exit(0 if test_success else 1)

def _is_dependency_cache_valid(cache_data: dict[str, Any]) -> bool:
    """Check if cached dependency data is still valid"""
    if 'timestamp' not in cache_data or 'file_timestamps' not in cache_data:
        return False

    # Cache is valid for 1 hour
    if time.time() - cache_data['timestamp'] > 3600:
        return False

    # Check if any Python files have been modified since cache creation
    current_timestamps = _get_file_timestamps()
    cached_timestamps = cache_data['file_timestamps']

    for file_path, current_time in current_timestamps.items():
        if file_path not in cached_timestamps or cached_timestamps[file_path] != current_time:
            return False

    return True
