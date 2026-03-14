"""Compatibility wrapper for minister conversion in v2 ingestion."""
from __future__ import annotations

from typing import Dict, Any, List

from minister_converter import convert_all_doctrines as _convert_all_doctrines
from minister_converter import update_combined_vector_index as _update_combined_vector_index


def convert_all_doctrines(doctrines: List[Dict[str, Any]], book_slug: str, data_root: str) -> Dict[str, Any]:
    return _convert_all_doctrines(doctrines, book_slug, data_root)


def update_combined_vector_index(data_root: str) -> None:
    _update_combined_vector_index(data_root)
