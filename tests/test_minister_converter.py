"""
Test Phase 3.5 Minister Converter functionality.

This script tests the core functions of the minister conversion system
against sample doctrine data.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
SAMPLE_CHAPTER = {
    "chapter_index": 1,
    "chapter_title": "Introduction to Constraints",
    "domains": ["constraints", "psychology", "risk"],
    "principles": [
        "Constraint awareness enables adaptive strategy.",
        "Psychological limits define operational boundaries."
    ],
    "rules": [
        "Always assess constraints before planning.",
        "Document resource limitations explicitly."
    ],
    "claims": [
        "Most failures result from ignoring constraints.",
        "Constraint recognition reduces planning time."
    ],
    "warnings": [
        "Underestimating constraints leads to failure.",
        "Psychological constraints are invisible but critical."
    ]
}


def test_basic_structure():
    """Test basic minister structure creation."""
    print("\n=== TEST 1: Basic Structure Creation ===")
    
    # Create a temporary test directory
    with tempfile.TemporaryDirectory() as tmpdir:
        from minister_converter import ensure_minister_structure
        
        test_domain = os.path.join(tmpdir, "test_domain")
        ensure_minister_structure(test_domain)
        
        # Verify consolidated category files were created
        required_files = ["principles.json", "rules.json", "claims.json", "warnings.json", "doctrine.json"]
        
        for f in required_files:
            file_path = os.path.join(test_domain, f)
            assert os.path.isfile(file_path), f"Missing file: {f}"
            print(f"✓ File created: {f}")
        
        # Verify consolidated file structure
        with open(os.path.join(test_domain, "principles.json")) as f:
            principles_data = json.load(f)
        
        assert "domain" in principles_data
        assert "category" in principles_data
        assert "entries" in principles_data
        assert isinstance(principles_data["entries"], list)
        assert "meta" in principles_data
        print("✓ principles.json has correct consolidated structure")
        
    print("✓ TEST 1 PASSED\n")


def test_entry_creation():
    """Test entry creation in consolidated category files."""
    print("=== TEST 2: Entry Creation ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        from minister_converter import (
            ensure_minister_structure,
            add_category_entry
        )
        
        test_domain = os.path.join(tmpdir, "constraints")
        ensure_minister_structure(test_domain)
        
        # Add entries to consolidated file
        entry_id_1 = add_category_entry(
            test_domain,
            "principles",
            "Constraint awareness enables adaptive strategy.",
            "TestBook2026",
            1
        )
        
        entry_id_2 = add_category_entry(
            test_domain,
            "principles",
            "Psychological limits define operational boundaries.",
            "TestBook2026",
            1
        )
        
        assert entry_id_1 and entry_id_2, "No entry IDs returned"
        print(f"✓ Entries created with IDs: {entry_id_1[:8]}... and {entry_id_2[:8]}...")
        
        # Verify consolidated file
        principles_file = os.path.join(test_domain, "principles.json")
        assert os.path.isfile(principles_file), "Principles file not created"
        
        with open(principles_file) as f:
            principles_data = json.load(f)
        
        assert len(principles_data["entries"]) == 2, f"Expected 2 entries, got {len(principles_data['entries'])}"
        assert principles_data["entries"][0]["id"] == entry_id_1
        assert principles_data["entries"][1]["id"] == entry_id_2
        assert principles_data["meta"]["total_entries"] == 2
        print("✓ Entries correctly added to principles.json")
        
        # Verify entry structure
        entry = principles_data["entries"][0]
        assert "id" in entry
        assert "text" in entry
        assert "source" in entry
        assert "weight" in entry
        assert entry["source"]["book"] == "TestBook2026"
        assert entry["source"]["chapter"] == 1
        print("✓ Entries have correct structure and content")
        
    print("✓ TEST 2 PASSED\n")


def test_chapter_conversion():
    """Test converting a chapter's doctrine."""
    print("=== TEST 3: Chapter Conversion ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        from minister_converter import process_chapter_doctrine
        
        # Create data directory structure
        data_dir = os.path.join(tmpdir, "data")
        os.makedirs(data_dir)
        
        result = process_chapter_doctrine(
            SAMPLE_CHAPTER,
            book_slug="TestBook2026",
            data_root=data_dir
        )
        
        assert "constraints" in result
        assert "psychology" in result
        assert "risk" in result
        print(f"✓ Conversion processed 3 domains")
        
        # Verify entries were created in consolidated files
        constraints_path = os.path.join(data_dir, "ministers", "constraints")
        
        # Check that consolidated files exist and have entries
        principles_file = os.path.join(constraints_path, "principles.json")
        with open(principles_file) as f:
            principles_data = json.load(f)
        
        assert len(principles_data["entries"]) == 2  # 2 principles from sample
        print(f"✓ Created 2 principles in constraints domain")
        
        # Verify all categories have entries
        categories_with_data = 0
        for category in ["principles", "rules", "claims", "warnings"]:
            category_file = os.path.join(constraints_path, f"{category}.json")
            with open(category_file) as f:
                category_data = json.load(f)
            if len(category_data["entries"]) > 0:
                categories_with_data += 1
        
        assert categories_with_data == 4, f"Expected all 4 categories to have data"
        print(f"✓ All 4 categories have entries in consolidated files")
        
    print("✓ TEST 3 PASSED\n")


def test_combined_index_update():
    """Test updating combined vector index."""
    print("=== TEST 4: Combined Vector Index ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        from minister_converter import (
            process_chapter_doctrine,
            update_combined_vector_index
        )
        
        data_dir = os.path.join(tmpdir, "data")
        os.makedirs(data_dir)
        
        # Create initial structure
        process_chapter_doctrine(
            SAMPLE_CHAPTER,
            book_slug="TestBook2026",
            data_root=data_dir
        )
        
        # Update combined index
        update_combined_vector_index(data_root=data_dir)
        
        combined_index_file = os.path.join(data_dir, "combined_vector.index")
        assert os.path.isfile(combined_index_file), "combined_vector.index not created"
        print("✓ combined_vector.index created")
        
        with open(combined_index_file) as f:
            combined_index = json.load(f)
        
        assert combined_index["domain"] == "all"
        assert combined_index["combined"] is True
        assert "constraints" in combined_index["domains_included"]
        assert "psychology" in combined_index["domains_included"]
        assert "risk" in combined_index["domains_included"]
        print(f"✓ Index includes {len(combined_index['domains_included'])} domains")
        
        assert "constraints" in combined_index["domain_statistics"]
        stats = combined_index["domain_statistics"]["constraints"]
        assert stats["total_entries"] == 8  # 2×4 categories
        print(f"✓ Domain statistics tracked: constraints has {stats['total_entries']} entries")
        
    print("✓ TEST 4 PASSED\n")


def test_multiple_chapters():
    """Test converting multiple chapters."""
    print("=== TEST 5: Multiple Chapter Conversion ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        from minister_converter import convert_all_doctrines
        
        data_dir = os.path.join(tmpdir, "data")
        os.makedirs(data_dir)
        
        # Create multiple chapters with different domains
        chapter_2 = SAMPLE_CHAPTER.copy()
        chapter_2["chapter_index"] = 2
        chapter_2["domains"] = ["strategy", "power"]
        
        doctrines = [SAMPLE_CHAPTER, chapter_2]
        
        summary = convert_all_doctrines(
            doctrines,
            book_slug="MultiChapterBook",
            data_root=data_dir
        )
        
        assert summary["status"] == "success"
        assert summary["total_chapters_processed"] == 2
        print(f"✓ Processed {summary['total_chapters_processed']} chapters")
        
        assert summary["total_entries_created"] > 0
        print(f"✓ Created {summary['total_entries_created']} total entries")
        
        # Verify domains were populated
        populated_domains = set(summary["domain_statistics"].keys())
        expected_domains = {"constraints", "psychology", "risk", "strategy", "power"}
        assert expected_domains.issubset(populated_domains)
        print(f"✓ Populated {len(populated_domains)} domains")
        
    print("✓ TEST 5 PASSED\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 3.5 MINISTER CONVERTER - FUNCTIONAL TESTS")
    print("=" * 60)
    
    try:
        test_basic_structure()
        test_entry_creation()
        test_chapter_conversion()
        test_combined_index_update()
        test_multiple_chapters()
        
        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        return 0
    
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
