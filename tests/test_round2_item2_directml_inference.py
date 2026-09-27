import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.modules.detector_onnx import ONNXTextDetector, DirectMLError


def test_actual_detect_dispatches_through_mocked_dml_session(tmp_path):
    """Calling detect() on ONNXTextDetector actively runs inference through the DML ONNX session."""
    fake_model = tmp_path / "detector.onnx"
    fake_model.write_bytes(b"MOCK_ONNX_BYTES")

    # Mock ONNX Runtime session with DML provider
    mock_session = MagicMock()
    mock_session.get_providers.return_value = ["DmlExecutionProvider", "CPUExecutionProvider"]
    
    mock_input = MagicMock()
    mock_input.name = "images"
    mock_input.shape = [1, 3, 640, 640]
    mock_session.get_inputs.return_value = [mock_input]

    # Mock output tensor: shape (1, 5, 2)
    # Box 1: cx=320, cy=320, w=100, h=100, score=0.95 (Valid bubble)
    # Box 2: cx=100, cy=100, w=10, h=10, score=0.01 (Below confidence)
    mock_output = np.zeros((1, 5, 2), dtype=np.float32)
    mock_output[0, 0, 0] = 320.0
    mock_output[0, 1, 0] = 320.0
    mock_output[0, 2, 0] = 100.0
    mock_output[0, 3, 0] = 100.0
    mock_output[0, 4, 0] = 0.95

    mock_output[0, 0, 1] = 100.0
    mock_output[0, 1, 1] = 100.0
    mock_output[0, 2, 1] = 10.0
    mock_output[0, 3, 1] = 10.0
    mock_output[0, 4, 1] = 0.01

    mock_session.run.return_value = [mock_output]

    with patch("onnxruntime.get_available_providers", return_value=["DmlExecutionProvider", "CPUExecutionProvider"]), \
         patch("onnxruntime.InferenceSession", return_value=mock_session):
        detector = ONNXTextDetector(model_path=str(fake_model), device="directml", confidence_threshold=0.5)
        assert detector.active_provider == "DmlExecutionProvider"

        # Run detection on a 640x640 dummy image
        img = np.zeros((640, 640, 3), dtype=np.uint8)
        bubbles = detector.detect(img)

        # Assert inference was dispatched to the ONNX session
        mock_session.run.assert_called_once()
        assert len(bubbles) == 1
        bubble = bubbles[0]
        # Padded coordinate unscaling for 640x640 -> bbox ~ [270, 270, 370, 370]
        assert bubble.bbox[0] >= 260 and bubble.bbox[2] <= 380
        assert bubble.confidence == pytest.approx(0.95, rel=1e-2)


def test_absence_of_dml_provider_raises_loudly(tmp_path):
    """Requesting DirectML when DmlExecutionProvider is missing from ORT raises DirectMLError."""
    fake_model = tmp_path / "model.onnx"
    fake_model.write_bytes(b"MOCK_ONNX_BYTES")

    with patch("onnxruntime.get_available_providers", return_value=["CPUExecutionProvider"]):
        with pytest.raises(DirectMLError) as exc_info:
            _ = ONNXTextDetector(model_path=str(fake_model), device="directml")
        assert "'dmlexecutionprovider' is not available" in str(exc_info.value).lower()


def test_detect_raises_when_no_session_and_no_model():
    """If neither an ONNX session nor a PyTorch model is loaded, detect() raises loud RuntimeError."""
    detector = ONNXTextDetector.__new__(ONNXTextDetector)
    detector.session = None
    detector.model = None
    detector.device_setting = "cpu"

    img = np.zeros((100, 100, 3), dtype=np.uint8)
    with pytest.raises(RuntimeError) as exc_info:
        detector.detect(img)
    assert "not loaded" in str(exc_info.value).lower()


def test_no_false_cpu_fallback_label(tmp_path):
    """When DirectML is requested but ORT falls back to CPU, DirectMLError is raised and never labeled DML."""
    fake_model = tmp_path / "model.onnx"
    fake_model.write_bytes(b"MOCK_ONNX_BYTES")

    mock_session = MagicMock()
    mock_session.get_providers.return_value = ["CPUExecutionProvider"]

    with patch("onnxruntime.get_available_providers", return_value=["DmlExecutionProvider", "CPUExecutionProvider"]), \
         patch("onnxruntime.InferenceSession", return_value=mock_session):
        with pytest.raises(DirectMLError) as exc_info:
            _ = ONNXTextDetector(model_path=str(fake_model), device="directml")
        assert "cannot label a cpu fallback as directml" in str(exc_info.value).lower()
