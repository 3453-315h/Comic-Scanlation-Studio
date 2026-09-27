import os
import pytest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from src.modules.translator import TranslationCache, Translator
from src.core.config import Config

def test_cache_location_and_working_dir_independence(tmp_path, monkeypatch):
    """Translation cache should use absolute configured path regardless of current working directory."""
    cache_file = tmp_path / "app_cache" / "cache.json"
    
    # Instantiate cache pointing to cache_file
    cache = TranslationCache(cache_file=cache_file)
    cache.set("key1", "val1")
    
    assert cache_file.exists()
    assert cache.get("key1") == "val1"
    
    # Change working directory to a different folder
    workdir1 = tmp_path / "workdir1"
    workdir1.mkdir()
    monkeypatch.chdir(workdir1)
    
    cache2 = TranslationCache(cache_file=cache_file)
    assert cache2.get("key1") == "val1"
    cache2.set("key2", "val2")
    
    # Ensure no cache files were written in cwd
    assert not (workdir1 / "bck").exists()
    assert not (workdir1 / "translation_cache.json").exists()
    
    # Reload and verify both keys exist in configured path
    cache3 = TranslationCache(cache_file=cache_file)
    assert cache3.get("key1") == "val1"
    assert cache3.get("key2") == "val2"

def test_concurrent_cache_writes_no_corruption_or_lost_entries(tmp_path):
    """Multiple threads/workers writing concurrently must not corrupt JSON or lose entries."""
    cache_file = tmp_path / "concurrent_cache.json"
    
    def worker_write(index):
        # Create separate TranslationCache instance per worker to simulate separate Translator instances
        worker_cache = TranslationCache(cache_file=cache_file)
        worker_cache.set(f"key_{index}", f"value_{index}")
        return index
        
    num_workers = 20
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker_write, i) for i in range(num_workers)]
        for f in futures:
            f.result()
            
    final_cache = TranslationCache(cache_file=cache_file)
    for i in range(num_workers):
        assert final_cache.get(f"key_{i}") == f"value_{i}", f"Missing key_{i} in concurrent cache"
