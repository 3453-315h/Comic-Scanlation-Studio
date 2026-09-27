import os
import sys
import json
import time
import shutil
import hashlib
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import numpy as np
from PySide6.QtWidgets import QMessageBox

from src.core.config import Config
from src.core.project import Project, Page
from src.core.pipeline import ScanlationPipeline
from src.modules.detector import (
    YOLOTextDetector,
    TextDetector,
    ModelNotFoundError,
    ModelAcquisitionError,
    acquire_detector_model,
    DETECTOR_MODEL_REGISTRY,
)
from src.modules.detector_onnx import ONNXTextDetector
from src.modules.translator import (
    TranslationCache,
    CacheLockError,
    CacheCorruptError,
    Translator,
)
from src.gui.dialogs.download_models_dialog import DownloadModelsDialog, DownloadThread
from src.gui.main_window import MainWindow


# =============================================================================
# ITEM 1: Default Detector Model Trust & Verification
# =============================================================================

def test_default_missing_model_fails_before_execution_without_trusted_hash(tmp_path):
    """Missing model without a pinned SHA-256 must fail loudly before network or weight execution."""
    with patch("requests.get") as mock_get:
        # Default detector model in registry has no pinned sha256 and trusted=False
        with pytest.raises((ModelNotFoundError, ModelAcquisitionError)) as exc_info:
            acquire_detector_model(
                model_name="comic-speech-bubble-detector.pt",
                target_dir=tmp_path,
                allow_unverified=False,
            )
        assert "unverified" in str(exc_info.value).lower()
        mock_get.assert_not_called()

        # Same loud rejection through YOLOTextDetector constructor
        with pytest.raises(ModelNotFoundError) as exc_info2:
            YOLOTextDetector(
                model_path="comic-speech-bubble-detector.pt",
                allow_unverified=False,
                auto_acquire=True,
            )
        assert "unverified" in str(exc_info2.value).lower()


def test_acquire_detector_model_preexisting_wrong_hash_rejected(tmp_path):
    """An existing file on disk with a mismatched pinned hash must be rejected."""
    model_file = tmp_path / "pinned-model.pt"
    dummy_bytes = b"wrong-weights-content-never-pickle-12345"
    model_file.write_bytes(dummy_bytes)

    expected_sha = hashlib.sha256(b"correct-expected-weights").hexdigest()

    with pytest.raises(ModelAcquisitionError) as exc_info:
        acquire_detector_model(
            url="http://dummy.url/pinned-model.pt",
            target_path=model_file,
            expected_sha256=expected_sha,
            min_size=10,
        )
    assert "mismatch" in str(exc_info.value).lower() or "integrity" in str(exc_info.value).lower()


def test_acquire_detector_model_bad_hash_from_download(tmp_path):
    """A downloaded file that fails hash verification must be rejected and cleaned up."""
    target = tmp_path / "weights" / "test-model.pt"
    dummy_payload = b"dummy-download-payload-bytes-abc-9999"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": str(len(dummy_payload))}
    mock_resp.iter_content.return_value = [dummy_payload]

    expected_sha = hashlib.sha256(b"completely-different-hash").hexdigest()

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ModelAcquisitionError) as exc_info:
            acquire_detector_model(
                url="http://fake.url/model.pt",
                target_path=target,
                expected_sha256=expected_sha,
                min_size=10,
            )
        assert "integrity" in str(exc_info.value).lower()
        assert not target.exists()


def test_acquire_detector_model_truncated_response(tmp_path):
    """Downloaded payload smaller than min_size must fail and leave no target."""
    target = tmp_path / "truncated.pt"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": "5"}
    mock_resp.iter_content.return_value = [b"12345"]

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ModelAcquisitionError) as exc_info:
            acquire_detector_model(
                url="http://fake.url/truncated.pt",
                target_path=target,
                min_size=500,
            )
        assert "minimum" in str(exc_info.value).lower()
        assert not target.exists()


def test_acquire_detector_model_interrupted_transfer_cleans_temp(tmp_path):
    """Interrupted download cleans up temporary files and does not create the destination file."""
    target = tmp_path / "interrupted.pt"

    def interrupted_iter(chunk_size=16384):
        yield b"chunk1"
        raise ConnectionResetError("Connection lost mid-download")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {}
    mock_resp.iter_content = interrupted_iter

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ModelAcquisitionError) as exc_info:
            acquire_detector_model(
                url="http://fake.url/interrupted.pt",
                target_path=target,
                min_size=2,
            )
        assert "connection" in str(exc_info.value).lower()
        assert not target.exists()
        # Verify no orphaned temp files
        tmp_files = list(tmp_path.glob("*.tmp.*"))
        assert len(tmp_files) == 0


def test_acquire_detector_model_preserves_existing_model_on_failed_download(tmp_path):
    """A failed download must never overwrite an existing valid model."""
    target = tmp_path / "existing.pt"
    good_bytes = b"preexisting-good-model-bytes-0000000000"
    target.write_bytes(good_bytes)
    good_sha = hashlib.sha256(good_bytes).hexdigest()

    # 1. Existing verified model is recognized and preserved immediately
    acquired = acquire_detector_model(
        url="http://fake.url/existing.pt",
        target_path=target,
        expected_sha256=good_sha,
        min_size=10,
    )
    assert acquired == target
    assert target.read_bytes() == good_bytes

    # 2. Even if download is triggered (e.g. to another path or if hash mismatch occurs in download)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": "20"}
    mock_resp.iter_content.return_value = [b"bad-downloaded-bytes"]

    different_sha = hashlib.sha256(b"some-other-hash").hexdigest()
    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ModelAcquisitionError):
            acquire_detector_model(
                url="http://fake.url/existing.pt",
                target_path=target,
                expected_sha256=different_sha,
                min_size=10,
            )
        # Verify existing file preserved exactly despite failed download
        assert target.exists()
        assert target.read_bytes() == good_bytes


def test_positive_mocked_verified_artifact(tmp_path):
    """Positive test: artifact matching expected SHA-256 is acquired atomically."""
    target = tmp_path / "models" / "verified.pt"
    payload = b"dummy-verified-model-binary-data-payload-xyz"
    expected_sha = hashlib.sha256(payload).hexdigest()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": str(len(payload))}
    mock_resp.iter_content.return_value = [payload]

    with patch("requests.get", return_value=mock_resp):
        acquired = acquire_detector_model(
            url="http://fake.url/verified.pt",
            target_path=target,
            expected_sha256=expected_sha,
            min_size=10,
        )
        assert acquired == target
        assert target.exists()
        assert target.read_bytes() == payload


def test_explicit_opt_in_allows_unverified_model(tmp_path):
    """Explicit opt-in (allow_unverified=True) permits downloading unverified models."""
    target = tmp_path / "unverified.pt"
    payload = b"dummy-unverified-weights-data-safe-bytes"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": str(len(payload))}
    mock_resp.iter_content.return_value = [payload]

    # Explicit opt-in = False raises
    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ModelAcquisitionError) as exc_info:
            acquire_detector_model(
                model_name="comic-speech-bubble-detector.pt",
                target_path=target,
                allow_unverified=False,
                min_size=10,
            )
        assert "unverified" in str(exc_info.value).lower()
        assert not target.exists()

    # Explicit opt-in = True succeeds
    with patch("requests.get", return_value=mock_resp):
        acquired = acquire_detector_model(
            model_name="comic-speech-bubble-detector.pt",
            target_path=target,
            allow_unverified=True,
            min_size=10,
        )
        assert acquired == target
        assert target.exists()
        assert target.read_bytes() == payload


# =============================================================================
# ITEM 2: Manual Model Download Dialog Routing & Safety
# =============================================================================

def test_download_dialog_unverified_opt_in_rejected(qtbot):
    """Dialog warns user about unverified model weights; if user declines, download does not start."""
    dialog = DownloadModelsDialog()
    qtbot.addWidget(dialog)

    row = next(i for i, m in enumerate(dialog.MODELS) if "Comic Bubble Detector" in m["name"])

    with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.No) as mock_warn:
        with patch.object(DownloadThread, "start") as mock_start:
            dialog._download_model(row)
            mock_warn.assert_called_once()
            mock_start.assert_not_called()


def test_download_dialog_unverified_opt_in_accepted(qtbot):
    """If user confirms the unverified model warning, DownloadThread is started with allow_unverified=True."""
    dialog = DownloadModelsDialog()
    qtbot.addWidget(dialog)

    row = next(i for i, m in enumerate(dialog.MODELS) if "Comic Bubble Detector" in m["name"])
    with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Yes) as mock_warn:
        with patch.object(DownloadThread, "start") as mock_start:
            dialog._download_model(row)
            mock_warn.assert_called_once()
            mock_start.assert_called_once()
            assert dialog.download_thread.allow_unverified is True


def test_download_thread_handles_acquisition_failure(tmp_path):
    """DownloadThread routes through acquire_detector_model and emits failure on error without crashing."""
    thread = DownloadThread("Comic Bubble Detector", "Detection", allow_unverified=True)

    results = []
    thread.finished_download.connect(lambda success, msg: results.append((success, msg)))

    with patch("src.modules.detector.acquire_detector_model", side_effect=ModelAcquisitionError("HTTP 404: Not Found")):
        thread.run()

    assert len(results) == 1
    success, msg = results[0]
    assert success is False
    assert "404" in msg


def test_download_thread_does_not_load_incomplete_bytes(tmp_path):
    """YOLO load is never executed on incomplete or failed download bytes."""
    thread = DownloadThread("Comic Bubble Detector", "Detection", allow_unverified=True)

    yolo_load_called = []
    mock_yolo = MagicMock(side_effect=lambda path: yolo_load_called.append(path))

    with patch("src.modules.detector.acquire_detector_model", side_effect=ModelAcquisitionError("Truncated file")):
        with patch.dict("sys.modules", {"ultralytics": MagicMock(YOLO=mock_yolo)}):
            thread.run()

    assert len(yolo_load_called) == 0


# =============================================================================
# ITEM 3: Inpaint and Imprint Failures are Page Failures
# =============================================================================

def _create_test_pipeline():
    """Helper to construct a ScanlationPipeline with mocked components."""
    pipeline = ScanlationPipeline()
    pipeline.detector = MagicMock()
    pipeline.ocr = MagicMock()
    pipeline.translator = MagicMock()
    pipeline.inpainter = MagicMock()
    pipeline.imprinter = MagicMock()
    return pipeline


def test_inpaint_failure_marks_page_failed_and_preserves_original_artwork(tmp_path):
    """Inpainting failure marks page as failed, keeps original source image, and skips imprint."""
    pipeline = _create_test_pipeline()

    # Create dummy source image
    img_path = tmp_path / "page1.png"
    orig_img = np.full((100, 100, 3), 200, dtype=np.uint8)
    import cv2
    cv2.imwrite(str(img_path), orig_img)

    project = Project("TestProj")
    page = project.add_page(img_path)

    # Mock detector to find a bubble
    from src.core.project import TextBubble
    bubble = TextBubble(id="b1", bbox=[10, 10, 50, 50], text_original="Hello", text_translated="Bonjour", status="translated")
    pipeline.detector.detect.return_value = [bubble]
    pipeline.ocr.recognize.return_value = "Hello"
    pipeline.translator.translate.return_value = "Bonjour"

    # Inject failure into inpainter
    pipeline.inpainter.inpaint_multiple.side_effect = RuntimeError("GPU OOM in inpainter")

    processed_page = pipeline.process_page(page, project)

    assert processed_page.status == "failed"
    assert "Inpainting failed" in processed_page.error
    assert processed_page.processed_image_path is None
    # Imprint must have been skipped
    pipeline.imprinter.imprint.assert_not_called()

    # Verify export safely exports original source pixels
    main_win = MainWindow()
    main_win.project = project
    main_win.image_viewer.current_page = page
    with patch("src.gui.main_window.QFileDialog.getSaveFileName", return_value=(str(tmp_path / "out.cbz"), "CBZ")):
        with patch("zipfile.ZipFile") as mock_zip:
            with patch.object(QMessageBox, "information"):
                main_win.export_project()
                for call in mock_zip.return_value.__enter__.return_value.write.call_args_list:
                    exported_path = Path(call[0][0])
                    assert exported_path == img_path
    main_win.close()


def test_imprint_failure_restores_original_and_marks_page_failed(tmp_path):
    """Imprint failure restores original source artwork, avoids text-erased export, marks failed."""
    pipeline = _create_test_pipeline()

    img_path = tmp_path / "page2.png"
    orig_img = np.full((100, 100, 3), 150, dtype=np.uint8)
    import cv2
    cv2.imwrite(str(img_path), orig_img)

    project = Project("TestProj")
    page = project.add_page(img_path)

    from src.core.project import TextBubble
    from src.modules.imprinter import FontStyle
    bubble = TextBubble(id="b1", bbox=[10, 10, 50, 50], text_original="Hi", text_translated="Salut", status="translated")
    pipeline.detector.detect.return_value = [bubble]
    pipeline.ocr.recognize.return_value = "Hi"
    pipeline.translator.translate.return_value = "Salut"
    pipeline.imprinter.analyze_style.return_value = FontStyle()

    # Inpaint succeeds (erasing text)
    erased_img = np.full((100, 100, 3), 255, dtype=np.uint8)
    pipeline.inpainter.inpaint_multiple.return_value = erased_img

    # Imprint fails
    pipeline.imprinter.imprint.side_effect = ValueError("Font style rendering error")

    processed_page = pipeline.process_page(page, project)

    assert processed_page.status == "failed"
    assert "Text imprinting failed" in processed_page.error
    assert processed_page.processed_image_path is None

    # Verify MainWindow batch outcomes
    main_win = MainWindow()
    main_win.project = project
    main_win.image_viewer.current_page = page
    with patch.object(project, "save"):
        with patch.object(QMessageBox, "warning") as mock_warn:
            main_win._on_batch_complete([processed_page])
            mock_warn.assert_called_once()
            assert "1 failed" in mock_warn.call_args[0][2]
    main_win.close()


def test_pipeline_stage_success_path(tmp_path):
    """When both inpaint and imprint succeed, page status is success and processed image is saved."""
    pipeline = _create_test_pipeline()

    img_path = tmp_path / "page3.png"
    orig_img = np.full((100, 100, 3), 100, dtype=np.uint8)
    import cv2
    cv2.imwrite(str(img_path), orig_img)

    project = Project("TestProj")
    page = project.add_page(img_path)

    from src.core.project import TextBubble
    bubble = TextBubble(id="b1", bbox=[10, 10, 50, 50], text_original="Hello", text_translated="Bonjour", status="translated")
    pipeline.detector.detect.return_value = [bubble]

    pipeline.inpainter.inpaint_multiple.return_value = orig_img
    pipeline.imprinter.imprint.return_value = orig_img

    processed_page = pipeline.process_page(page, project)

    assert processed_page.status == "success"
    assert processed_page.error is None
    assert processed_page.processed_image_path is not None
    assert processed_page.processed_image_path.exists()


# =============================================================================
# ITEM 4: Cache Unlock Failure is Raised Loudly (CacheLockError)
# =============================================================================

def test_posix_unlock_failure_raises_cache_lock_error_and_closes_fd(tmp_path):
    """POSIX unlock error raises CacheLockError while guaranteeing lock fd is closed."""
    cache = TranslationCache(tmp_path / "cache.json")
    lock_fd = cache._acquire_file_lock()

    closed_fds = []
    real_close = os.close
    def tracked_close(fd):
        closed_fds.append(fd)
        real_close(fd)

    with patch("sys.platform", "linux"):
        with patch("fcntl.flock", side_effect=OSError("Flock unlock simulated failure")):
            with patch("os.close", side_effect=tracked_close):
                with pytest.raises(CacheLockError) as exc_info:
                    cache._release_file_lock(lock_fd)
                assert "unlocking failed" in str(exc_info.value).lower()
                assert lock_fd in closed_fds


def test_windows_unlock_failure_raises_cache_lock_error_and_closes_fd(tmp_path):
    """Windows unlock error raises CacheLockError while guaranteeing lock fd is closed."""
    cache = TranslationCache(tmp_path / "cache.json")
    lock_fd = cache._acquire_file_lock()

    closed_fds = []
    real_close = os.close
    def tracked_close(fd):
        closed_fds.append(fd)
        real_close(fd)

    with patch("sys.platform", "win32"):
        mock_msvcrt = MagicMock()
        mock_msvcrt.LK_UNLCK = 2
        mock_msvcrt.locking.side_effect = OSError("msvcrt unlock simulated failure")
        with patch.dict("sys.modules", {"msvcrt": mock_msvcrt}):
            with patch("os.close", side_effect=tracked_close):
                with pytest.raises(CacheLockError) as exc_info:
                    cache._release_file_lock(lock_fd)
                assert "unlocking failed" in str(exc_info.value).lower()
                assert lock_fd in closed_fds


def test_write_exception_not_masked_by_subsequent_unlock_error(tmp_path):
    """If disk write fails AND lock unlock fails, write exception is not masked."""
    cache = TranslationCache(tmp_path / "cache.json")

    with patch("json.dump", side_effect=IOError("Simulated disk write error")):
        with patch.object(cache, "_release_file_lock", side_effect=CacheLockError("Simulated unlock error")):
            with pytest.raises(IOError) as exc_info:
                cache.set("key", "val")
            assert "disk write error" in str(exc_info.value).lower()
            # Verify lock release error was attached and not discarded
            assert hasattr(exc_info.value, "lock_release_error")
            assert isinstance(exc_info.value.lock_release_error, CacheLockError)


# =============================================================================
# ITEM 5: Corrupt Cache JSON Quarantine & Uncached Translation
# =============================================================================

def test_corrupt_cache_json_quarantined_on_init(tmp_path):
    """Malformed cache JSON before initialization is quarantined and raises CacheCorruptError."""
    cache_file = tmp_path / "cache.json"
    corrupt_bytes = b'{"broken": true, missing_closing_bracket'
    cache_file.write_bytes(corrupt_bytes)

    with pytest.raises(CacheCorruptError) as exc_info:
        TranslationCache(cache_file)

    assert "corrupt" in str(exc_info.value).lower()
    # Active cache file unlinked
    assert not cache_file.exists()

    # Corrupt backup exists and preserves original bytes
    quarantine_files = list(tmp_path.glob("cache_corrupt_*.json"))
    assert len(quarantine_files) == 1
    assert quarantine_files[0].read_bytes() == corrupt_bytes


def test_corrupt_cache_json_on_disk_before_set_quarantined_without_overwrite(tmp_path):
    """External corruption appearing on disk before set() is quarantined rather than overwritten."""
    cache_file = tmp_path / "cache.json"
    cache = TranslationCache(cache_file)
    cache.set("initial_key", "initial_val")
    assert cache_file.exists()

    # Corrupt the cache file on disk
    corrupt_bytes = b'NOT_A_VALID_JSON_OBJECT_123'
    cache_file.write_bytes(corrupt_bytes)

    with pytest.raises(CacheCorruptError) as exc_info:
        cache.set("new_key", "new_val")

    assert "corrupt" in str(exc_info.value).lower()
    assert cache.is_durable is False
    assert cache.is_persistent is False

    # Corrupt bytes must be preserved in quarantine backup
    quarantined = list(tmp_path.glob("cache_corrupt_*.json"))
    assert len(quarantined) == 1
    assert quarantined[0].read_bytes() == corrupt_bytes


def test_translator_initializes_and_translates_uncached_when_cache_corrupt(tmp_path):
    """When cache is corrupt, Translator logs error and proceeds with uncached translation."""
    cache_file = tmp_path / "cache.json"
    cache_file.write_bytes(b'{"malformed": [')

    translator = Translator(api="offline", cache_file=cache_file)
    assert translator.cache.is_durable is False
    assert translator.cache.is_persistent is False

    # Translation succeeds uncached without error
    with patch.object(translator, "_nllb_translate", return_value="Bonjour"):
        result = translator.translate("Hello world")
        assert result == "Bonjour"
