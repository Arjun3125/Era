#!/usr/bin/env python3
"""
Clean up old atomic entry directories after consolidation to consolidated JSON files.
Removes the subdirectories (principles/, rules/, claims/, warnings/) from each domain
since they are now replaced by consolidated JSON files.
"""
import os
import shutil
import sys

def cleanup_domain(domain_path: str) -> dict:
    """
    Remove old atomic entry directories from a domain.
    
    Args:
        domain_path: Path to the domain folder
    
    Returns:
        Statistics about cleanup
    """
    domain_name = os.path.basename(domain_path)
    stats = {
        "domain": domain_name,
        "directories_removed": 0,
        "errors": []
    }
    
    for category in ["principles", "rules", "claims", "warnings"]:
        category_dir = os.path.join(domain_path, category)
        
        if os.path.isdir(category_dir):
            try:
                # Count files before deletion (for reporting)
                num_files = len(os.listdir(category_dir))
                
                # Remove directory and all contents
                shutil.rmtree(category_dir)
                stats["directories_removed"] += 1
                print(f"  [OK] Removed {category}/ ({num_files} files)")
            except Exception as e:
                stats["errors"].append(f"Error removing {category}: {str(e)}")
                print(f"  [ERROR] Failed to remove {category}: {str(e)}")
    
    return stats

def main():
    """Clean up all domains."""
    data_root = "data"
    ministers_root = os.path.join(data_root, "ministers")
    
    if not os.path.exists(ministers_root):
        print(f"[ERROR] Ministers directory not found: {ministers_root}")
        sys.exit(1)
    
    print("Starting cleanup of old atomic entry directories")
    print("-" * 60)
    
    total_removed = 0
    total_errors = 0
    
    # Process each domain
    for domain_name in sorted(os.listdir(ministers_root)):
        domain_path = os.path.join(ministers_root, domain_name)
        if os.path.isdir(domain_path):
            print(f"\nCleaning domain: {domain_name}")
            stats = cleanup_domain(domain_path)
            total_removed += stats["directories_removed"]
            total_errors += len(stats["errors"])
    
    # Summary
    print("\n" + "=" * 60)
    print("CLEANUP COMPLETE")
    print("=" * 60)
    print(f"Directories removed: {total_removed}")
    if total_errors > 0:
        print(f"[WARNING] Errors: {total_errors}")
    else:
        print("No errors - all cleanup successful!")

if __name__ == "__main__":
    main()
