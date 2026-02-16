"""
Shared pytest configuration and fixtures for ERA Test Suite
"""

import pytest
import sys
import os
from pathlib import Path

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


def pytest_configure(config):
    """Register custom markers"""
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
