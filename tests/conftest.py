"""
Shared pytest configuration and fixtures for ERA Test Suite
"""

import pytest
import sys
import os
import asyncio
import inspect
import tempfile
import shutil
from pathlib import Path

# Ensure temp dirs are writable inside the repo
_tmp_root = Path(__file__).parent.parent / "_pytest_tmp_run"
_tmp_root.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("TMPDIR", str(_tmp_root))
os.environ.setdefault("TEMP", str(_tmp_root))
os.environ.setdefault("TMP", str(_tmp_root))
tempfile.tempdir = str(_tmp_root)

# Ensure temp dirs are writable on Windows by providing a custom mkdtemp.
from uuid import uuid4


def _mkdtemp(*args, **kwargs):
    base_dir = kwargs.get("dir") or tempfile.gettempdir()
    prefix = kwargs.get("prefix", "tmp")
    for _ in range(1000):
        name = f"{prefix}{uuid4().hex[:8]}"
        path = Path(base_dir) / name
        try:
            os.mkdir(path)
            return str(path)
        except FileExistsError:
            continue
    raise FileExistsError("Could not create temporary directory")


tempfile.mkdtemp = _mkdtemp

# Avoid pytest temp cleanup failures on restricted directories.
try:
    import _pytest.pathlib as _pytest_pathlib
    import _pytest.tmpdir as _pytest_tmpdir

    _orig_cleanup_dead_symlinks = _pytest_pathlib.cleanup_dead_symlinks
    _orig_rm_rf = _pytest_pathlib.rm_rf

    def _safe_cleanup_dead_symlinks(root):  # type: ignore[override]
        try:
            return _orig_cleanup_dead_symlinks(root)
        except PermissionError:
            return None

    def _safe_rm_rf(*args, **kwargs):  # type: ignore[override]
        try:
            return _orig_rm_rf(*args, **kwargs)
        except PermissionError:
            return None

    _pytest_pathlib.cleanup_dead_symlinks = _safe_cleanup_dead_symlinks  # type: ignore[assignment]
    _pytest_tmpdir.cleanup_dead_symlinks = _safe_cleanup_dead_symlinks  # type: ignore[assignment]
    _pytest_pathlib.rm_rf = _safe_rm_rf  # type: ignore[assignment]
    if hasattr(_pytest_tmpdir, "rm_rf"):
        _pytest_tmpdir.rm_rf = _safe_rm_rf  # type: ignore[assignment]
except Exception:
    pass

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "persona"))
sys.path.insert(0, str(Path(__file__).parent.parent / "runtime"))
sys.path.insert(0, str(Path(__file__).parent.parent / "multi_agent_sim"))


@pytest.fixture(scope="session")
def era_root():
    """Fixture providing the ERA root directory path"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir(era_root):
    """Fixture providing path to test data directory"""
    test_data = era_root / "data"
    test_data.mkdir(parents=True, exist_ok=True)
    return test_data


@pytest.fixture(scope="session")
def rag_storage_dir(era_root):
    """Fixture providing path to RAG storage directory"""
    rag_dir = era_root / "rag_storage"
    rag_dir.mkdir(parents=True, exist_ok=True)
    return rag_dir


@pytest.fixture(scope="session")
def ingestion_dir(era_root):
    """Fixture providing path to ingestion directory"""
    ingest_dir = era_root / "ingestion"
    ingest_dir.mkdir(parents=True, exist_ok=True)
    return ingest_dir


@pytest.fixture
def temp_test_dir(tmp_path):
    """Fixture providing temporary directory for individual tests"""
    return tmp_path


@pytest.fixture
def tmp_path():  # type: ignore[override]
    """Provide a writable temp path without relying on pytest's tmpdir plugin."""
    path = Path(_mkdtemp(dir=_tmp_root, prefix="pytest-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def pytest_configure(config):
    """Register custom markers"""
    try:
        if not getattr(config.option, "basetemp", None):
            base_temp = _tmp_root / f"pytest-{uuid4().hex[:8]}"
            base_temp.mkdir(parents=True, exist_ok=True)
            config.option.basetemp = str(base_temp)
    except Exception:
        pass
    config.addinivalue_line("markers", "requires_ollama: mark test as requiring Ollama service")
    config.addinivalue_line("markers", "requires_embeddings: mark test as requiring embedding service")


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection"""
    for item in items:
        # Auto-categorize tests based on filename
        if "embedding" in item.nodeid or "embed" in item.nodeid:
            item.add_marker(pytest.mark.embedding)
        if "async" in item.nodeid:
            item.add_marker(pytest.mark.async_)
        if "ingest" in item.nodeid or "ingestion" in item.nodeid:
            item.add_marker(pytest.mark.ingestion)
        if "verify" in item.nodeid or "verification" in item.nodeid:
            item.add_marker(pytest.mark.verification)
        if "smoke" in item.nodeid:
            item.add_marker(pytest.mark.smoke)
        if "e2e" in item.nodeid or "end_to_end" in item.nodeid:
            item.add_marker(pytest.mark.e2e)


def pytest_pyfunc_call(pyfuncitem):
    """Run async test functions without requiring pytest-asyncio."""
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        asyncio.run(pyfuncitem.obj(**pyfuncitem.funcargs))
        return True
