import pytest
from unittest.mock import MagicMock, patch

from src.modules.detector_onnx import (
    YOLOONNXDetector,
    DirectMLError
)

def test_directml_raises_when_dml_provider_missing(tmp_path):
    """When DirectML is requested but DmlExecutionProvider is missing, raise DirectMLError."""
    # Create fake model file
    fake_model = tmp_path / "model.onnx"
    fake_model.write_bytes(b"dummy onnx content")
    
    detector = YOLOONNXDetector(model_path=str(fake_model), device="cpu")
    
    # Mock ort.get_available_providers() returning only CPUExecutionProvider
    with patch("onnxruntime.get_available_providers", return_value=["CPUExecutionProvider"]):
        with pytest.raises(DirectMLError) as exc_info:
            detector._configure_onnx_providers("directml")
        assert "'dmlexecutionprovider' is not available" in str(exc_info.value).lower()
        # Verify provider never reverted to CPU while claiming DirectML
        assert detector.active_providers != ["CPUExecutionProvider"] or detector.device != "directml"

def test_directml_configured_when_provider_present(tmp_path):
    """When DmlExecutionProvider is available, providers list includes DmlExecutionProvider."""
    fake_model = tmp_path / "model.onnx"
    fake_model.write_bytes(b"dummy onnx content")
    
    mock_session = MagicMock()
    mock_session.get_providers.return_value = ["DmlExecutionProvider", "CPUExecutionProvider"]
    
    detector = YOLOONNXDetector(model_path=str(fake_model), device="cpu")
    
    with patch("onnxruntime.get_available_providers", return_value=["DmlExecutionProvider", "CPUExecutionProvider"]), \
         patch("onnxruntime.InferenceSession", return_value=mock_session):
        providers = detector._configure_onnx_providers("directml")
        assert providers == ["DmlExecutionProvider", "CPUExecutionProvider"]

def test_onnx_session_init_with_directml_mocked(tmp_path):
    """Test full session creation with mocked DirectML provider."""
    fake_model = tmp_path / "model.onnx"
    fake_model.write_bytes(b"dummy onnx content")
    
    mock_session = MagicMock()
    mock_session.get_providers.return_value = ["DmlExecutionProvider", "CPUExecutionProvider"]
    
    with patch("onnxruntime.get_available_providers", return_value=["DmlExecutionProvider", "CPUExecutionProvider"]), \
         patch("onnxruntime.InferenceSession", return_value=mock_session):
        detector = YOLOONNXDetector(model_path=str(fake_model), device="directml")
        assert detector.device == "directml"
        assert "DmlExecutionProvider" in detector.active_providers
