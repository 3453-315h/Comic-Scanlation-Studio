import pytest
import os
import sys
import multiprocessing
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.modules.translator import TranslationCache, CacheLockError


def _worker_write_keys(cache_file_str: str, worker_id: int, num_keys: int):
    """Worker process entrypoint writing unique keys to the shared cache file."""
    cache = TranslationCache(cache_file=Path(cache_file_str))
    for i in range(num_keys):
        cache.set(f"worker_{worker_id}_key_{i}", f"val_{worker_id}_{i}")


def test_concurrent_multiprocess_cache_writes_no_data_loss(tmp_path):
    """Multiple independent OS processes concurrently writing distinct keys do not corrupt cache or lose updates."""
    cache_file = tmp_path / "multi_proc_cache.json"
    num_workers = 4
    keys_per_worker = 25
    expected_total_keys = num_workers * keys_per_worker

    ctx = multiprocessing.get_context("spawn" if sys.platform == "win32" else "fork")
    processes = []
    for wid in range(num_workers):
        p = ctx.Process(
            target=_worker_write_keys,
            args=(str(cache_file), wid, keys_per_worker)
        )
        processes.append(p)

    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=30)
        assert p.exitcode == 0, f"Worker process {p.pid} failed with exit code {p.exitcode}"

    # Verify final on-disk cache state
    cache = TranslationCache(cache_file=cache_file)
    for wid in range(num_workers):
        for i in range(keys_per_worker):
            expected_key = f"worker_{wid}_key_{i}"
            expected_val = f"val_{wid}_{i}"
            assert cache.get(expected_key) == expected_val, f"Missing key {expected_key}"

    assert len(cache._in_memory) == expected_total_keys


def test_lock_failure_surfaces_cache_lock_error(tmp_path):
    """Acquiring lock failure must surface CacheLockError loudly rather than silently pretending lock succeeded."""
    cache_file = tmp_path / "lock_fail_cache.json"
    cache = TranslationCache(cache_file=cache_file)

    with patch.object(cache, "_acquire_file_lock", side_effect=CacheLockError("Simulated lock acquisition contention")):
        with pytest.raises(CacheLockError) as exc_info:
            cache.set("foo", "bar")
        assert "Simulated lock acquisition contention" in str(exc_info.value)


def test_windows_msvcrt_locking_dispatch(tmp_path):
    """On Windows platforms or win32 platform mock, msvcrt.locking is used for inter-process locking."""
    cache_file = tmp_path / "win_cache.json"
    cache = TranslationCache(cache_file=cache_file)

    mock_msvcrt = MagicMock()
    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"msvcrt": mock_msvcrt}):
        lock_fd = cache._acquire_file_lock()
        assert lock_fd > 0
        mock_msvcrt.locking.assert_called_once_with(lock_fd, mock_msvcrt.LK_LOCK, 1)

        cache._release_file_lock(lock_fd)
        assert mock_msvcrt.locking.call_count == 2
        mock_msvcrt.locking.assert_called_with(lock_fd, mock_msvcrt.LK_UNLCK, 1)


def test_windows_locking_failure_raises_cache_lock_error(tmp_path):
    """When msvcrt.locking fails on Windows, CacheLockError is raised and file descriptor is safely closed."""
    cache_file = tmp_path / "win_fail_cache.json"
    cache = TranslationCache(cache_file=cache_file)

    mock_msvcrt = MagicMock()
    mock_msvcrt.locking.side_effect = OSError("Lock violation")

    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"msvcrt": mock_msvcrt}), \
         patch("os.close") as mock_close:
        with pytest.raises(CacheLockError) as exc_info:
            cache._acquire_file_lock()
        assert "Windows file locking failed" in str(exc_info.value)
        mock_close.assert_called_once()
