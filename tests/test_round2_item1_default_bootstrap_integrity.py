import pytest
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.config import Config
from src.core.pipeline import ScanlationPipeline
from src.modules.detector import (
    acquire_detector_model,
    ModelNotFoundError,
    ModelAcquisitionError,
    TextDetector,
)
from src.modules.detector_onnx import ONNXTextDetector


def test_default_pipeline_attempts_acquisition_and_surfaces_error_before_inference(tmp_path, monkeypatch):
    """Instantiating default pipeline (yolo-onnx) with missing model attempts acquisition and fails loud."""
    models_dir = tmp_path / "models"
    monkeypatch.setattr(Config, "MODELS_DIR", models_dir)
    monkeypatch.setattr(Config, "DETECTOR_MODEL", "yolo-onnx")
    monkeypatch.setattr(Config, "YOLO_MODEL_PATH", "comic-speech-bubble-detector.pt")

    config = Config()
    pipeline = ScanlationPipeline(config)

    # Mock network failure during acquisition
    with patch("requests.get", side_effect=Exception("Connection refused (mocked CI offline)")):
        with pytest.raises((ModelNotFoundError, ModelAcquisitionError)) as exc_info:
            _ = pipeline.detector
        assert "comic-speech-bubble-detector.pt" in str(exc_info.value) or "could not be acquired" in str(exc_info.value)


def test_acquisition_with_verified_mocked_artifact_succeeds(tmp_path):
    """Mocked acquisition with valid size and correct SHA-256 succeeds and atomically places file."""
    dest = tmp_path / "models" / "yolo" / "test_model.pt"
    dummy_payload = b"VALID_MODEL_WEIGHTS_BINARY_BLOB" * 1000

    hasher = hashlib.sha256(dummy_payload)
    expected_sha = hasher.hexdigest()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": str(len(dummy_payload))}
    mock_resp.iter_content = lambda chunk_size: [dummy_payload[:5000], dummy_payload[5000:]]
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        result_path = acquire_detector_model(
            model_name="test_model.pt",
            target_path=dest,
            min_size=100,
            url="https://mock.repo/test_model.pt",
            expected_sha256=expected_sha,
        )
        assert result_path == dest
        assert dest.exists()
        assert dest.read_bytes() == dummy_payload


def test_bad_truncated_or_mismatched_sha_fails(tmp_path):
    """Acquisition with corrupted/mismatched SHA-256 or HTML fails loudly."""
    dest = tmp_path / "mismatch.pt"
    dummy_payload = b"CORRUPTED_BYTES" * 100

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": str(len(dummy_payload))}
    mock_resp.iter_content = lambda chunk_size: [dummy_payload]
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ModelAcquisitionError) as exc_info:
            acquire_detector_model(
                model_name="mismatch.pt",
                target_path=dest,
                min_size=10,
                url="https://mock.repo/mismatch.pt",
                expected_sha256="0000000000000000000000000000000000000000000000000000000000000000",
            )
        assert "integrity check failed" in str(exc_info.value).lower()
        # Verify failed target was not created
        assert not dest.exists()


def test_valid_existing_model_not_overwritten(tmp_path):
    """If a valid model already exists at destination, it is preserved and not overwritten."""
    dest = tmp_path / "existing.pt"
    original_content = b"ORIGINAL_VERIFIED_MODEL_CONTENT" * 100
    dest.write_bytes(original_content)

    hasher = hashlib.sha256(original_content)
    expected_sha = hasher.hexdigest()

    # Network call is mocked to fail, but acquire_detector_model should find the existing valid model
    with patch("requests.get", side_effect=Exception("Should not download when already valid")):
        result = acquire_detector_model(
            model_name="existing.pt",
            target_path=dest,
            min_size=10,
            url="https://mock.repo/existing.pt",
            expected_sha256=expected_sha,
        )
        assert result == dest
        assert dest.read_bytes() == original_content


def test_explicit_opencv_fallback_works_without_model():
    """Explicitly selecting DETECTOR_MODEL='opencv' loads the verified OpenCV contour detector cleanly."""
    config = Config()
    config.DETECTOR_MODEL = "opencv"
    pipeline = ScanlationPipeline(config)
    detector = pipeline.detector
    assert isinstance(detector, TextDetector)
    assert not isinstance(detector, ONNXTextDetector)
    assert detector.model_name in ("opencv-contour", "opencv-robust")
