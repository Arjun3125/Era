"""
Cache Cleanup & Rotation Policy for ERA System

Implements automatic cleanup of old cache files to prevent disk space issues.
Runs on system startup and periodically during operation.
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import shutil


class CacheManager:
    """Manages cache cleanup, rotation, and disk space monitoring."""
    
    # Configuration
    CACHE_DIRS = {
        'ml_cache': 'ml/cache',
        'rag_cache': 'rag_cache',
        'conversations': 'data/conversations',
        'sessions': 'data/sessions/completed'
    }
    
    # Cleanup policies (in days)
    RETENTION_DAYS = {
        'ml_cache': 7,           # ML cache: keep 7 days
        'rag_cache': 14,         # RAG cache: keep 14 days
        'conversations': 30,     # Conversations: keep 30 days
        'sessions': 90           # Sessions: keep 90 days (preserve learning)
    }
    
    # Maximum cache size (bytes) - trigger cleanup if exceeded
    MAX_CACHE_SIZE = {
        'ml_cache': 500 * 1024 * 1024,    # 500 MB
        'rag_cache': 2 * 1024 * 1024 * 1024,  # 2 GB
        'conversations': 1 * 1024 * 1024 * 1024,  # 1 GB
    }
    
    def __init__(self, era_root: str = 'c:\\era'):
        """Initialize cache manager with ERA root directory."""
        self.era_root = Path(era_root)
        self.stats = {}
    
    def validate_cache_dirs(self) -> bool:
        """Validate that cache directories exist or create them."""
        for cache_name, rel_path in self.CACHE_DIRS.items():
            cache_path = self.era_root / rel_path
            if not cache_path.exists():
                try:
                    cache_path.mkdir(parents=True, exist_ok=True)
                    print(f"[OK] Created cache directory: {cache_name} -> {rel_path}")
                except Exception as e:
                    print(f"[WARN] Failed to create cache dir {cache_name}: {e}")
                    return False
        return True
    
    def get_cache_size(self, cache_name: str) -> int:
        """Get total size of cache directory in bytes."""
        if cache_name not in self.CACHE_DIRS:
            return 0
        
        cache_path = self.era_root / self.CACHE_DIRS[cache_name]
        if not cache_path.exists():
            return 0
        
        total = 0
        for dirpath, dirnames, filenames in os.walk(cache_path):
            for fname in filenames:
                try:
                    fpath = os.path.join(dirpath, fname)
                    total += os.path.getsize(fpath)
                except (OSError, FileNotFoundError):
                    pass
        
        return total
    
    def cleanup_old_files(self, cache_name: str, max_age_days: int) -> int:
        """
        Remove files older than max_age_days.
        Returns: number of files deleted
        """
        if cache_name not in self.CACHE_DIRS:
            return 0
        
        cache_path = self.era_root / self.CACHE_DIRS[cache_name]
        if not cache_path.exists():
            return 0
        
        cutoff_time = time.time() - (max_age_days * 86400)
        deleted_count = 0
        
        for dirpath, dirnames, filenames in os.walk(cache_path):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    if os.path.getmtime(fpath) < cutoff_time:
                        os.remove(fpath)
                        deleted_count += 1
                except (OSError, FileNotFoundError):
                    pass
        
        return deleted_count
    
    def cleanup_by_size(self, cache_name: str, max_size_bytes: int) -> int:
        """
        Remove oldest files until cache is under max_size.
        Returns: number of files deleted
        """
        if cache_name not in self.CACHE_DIRS:
            return 0
        
        cache_path = self.era_root / self.CACHE_DIRS[cache_name]
        if not cache_path.exists():
            return 0
        
        # Get all files with modification times
        files_with_times = []
        for dirpath, dirnames, filenames in os.walk(cache_path):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    size = os.path.getsize(fpath)
                    files_with_times.append((fpath, mtime, size))
                except (OSError, FileNotFoundError):
                    pass
        
        # Sort by modification time (oldest first)
        files_with_times.sort(key=lambda x: x[1])
        
        # Delete oldest files until under limit
        current_size = sum(f[2] for f in files_with_times)
        deleted_count = 0
        
        for fpath, _, fsize in files_with_times:
            if current_size <= max_size_bytes:
                break
            
            try:
                os.remove(fpath)
                current_size -= fsize
                deleted_count += 1
            except (OSError, FileNotFoundError):
                pass
        
        return deleted_count
    
    def run_cleanup(self, verbose: bool = True) -> Dict[str, int]:
        """
        Run full cleanup cycle on all caches.
        Returns: dict with cleanup stats per cache
        """
        if verbose:
            print("=" * 80)
            print("CACHE CLEANUP POLICY - Running maintenance cycle")
            print("=" * 80)
        
        results = {}
        
        for cache_name in self.CACHE_DIRS:
            if verbose:
                print(f"\n[{cache_name}]")
            
            # 1. Remove files older than retention period
            max_age = self.RETENTION_DAYS.get(cache_name, 30)
            old_deleted = self.cleanup_old_files(cache_name, max_age)
            
            if verbose:
                print(f"  Removed {old_deleted} files older than {max_age} days")
            
            # 2. If still over size limit, remove more
            max_size = self.MAX_CACHE_SIZE.get(cache_name)
            size_deleted = 0
            
            if max_size:
                current_size = self.get_cache_size(cache_name)
                if current_size > max_size:
                    size_deleted = self.cleanup_by_size(cache_name, max_size)
                    if verbose:
                        print(f"  Size-based cleanup: removed {size_deleted} files")
            
            # 3. Report final state
            final_size = self.get_cache_size(cache_name)
            if verbose:
                size_mb = final_size / (1024 * 1024)
                print(f"  Final cache size: {size_mb:.1f} MB")
            
            results[cache_name] = {
                'old_deleted': old_deleted,
                'size_deleted': size_deleted,
                'total_deleted': old_deleted + size_deleted,
                'final_size_bytes': final_size
            }
        
        if verbose:
            print("\n" + "=" * 80)
            print("Cache cleanup complete")
            print("=" * 80)
        
        return results
    
    def get_cache_report(self) -> Dict[str, Dict]:
        """Generate cache statistics report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'caches': {}
        }
        
        total_size = 0
        for cache_name in self.CACHE_DIRS:
            size = self.get_cache_size(cache_name)
            retention = self.RETENTION_DAYS.get(cache_name, 30)
            max_size = self.MAX_CACHE_SIZE.get(cache_name)
            
            report['caches'][cache_name] = {
                'size_bytes': size,
                'size_mb': size / (1024 * 1024),
                'retention_days': retention,
                'max_size_gb': max_size / (1024 * 1024 * 1024) if max_size else None,
                'over_limit': size > max_size if max_size else False
            }
            total_size += size
        
        report['total_size_bytes'] = total_size
        report['total_size_gb'] = total_size / (1024 * 1024 * 1024)
        
        return report
    
    def print_report(self):
        """Print formatted cache report."""
        report = self.get_cache_report()
        
        print("\n" + "=" * 80)
        print("CACHE STATUS REPORT")
        print("=" * 80)
        print(f"Generated: {report['timestamp']}\n")
        
        for cache_name, stats in report['caches'].items():
            status = "[OVER]" if stats['over_limit'] else "[OK]"
            print(f"{status} {cache_name}")
            print(f"    Size: {stats['size_mb']:.1f} MB")
            print(f"    Retention: {stats['retention_days']} days")
            if stats['max_size_gb']:
                print(f"    Max: {stats['max_size_gb']:.1f} GB")
            print()
        
        print(f"Total Cache Size: {report['total_size_gb']:.2f} GB")
        print("=" * 80 + "\n")


def main():
    """Run cache cleanup when executed directly."""
    manager = CacheManager()
    
    # Validate directories
    if not manager.validate_cache_dirs():
        print("[ERROR] Failed to validate cache directories")
        return
    
    # Print initial report
    manager.print_report()
    
    # Run cleanup
    results = manager.run_cleanup(verbose=True)
    
    # Print final report
    manager.print_report()


if __name__ == '__main__':
    main()
