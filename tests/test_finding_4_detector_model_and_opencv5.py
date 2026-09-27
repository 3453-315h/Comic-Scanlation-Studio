import pytest
import cv2
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.modules.detector import (
    YOLOTextDetector,
    TextDetector,
    ModelNotFoundError,
    ModelAcquisitionError,
    acquire_detector_model
)

def test_opencv5_installed_and_api_matrix():
    """Verify that OpenCV 5 (>=5.0.0.93) is installed and core cv2 contour APIs function."""
    version = cv2.__version__
    assert version.startswith("5."), f"Expected OpenCV 5.x, got {version}"
    
    # Check requirements.txt contains opencv-python>=5.0.0.93
    req_file = Path(__file__).parent.parent / "requirements.txt"
    with open(req_file, "r", encoding="utf-8") as f:
        reqs = f.read()
    assert "opencv-python>=5.0.0.93" in reqs
    
    # Test cv2 contour detection API in OpenCV 5
    img = np.zeros((100, 100), dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (60, 60), 255, -1)
    contours, hierarchy = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    assert len(contours) == 1
    x, y, w, h = cv2.boundingRect(contours[0])
    assert w > 0 and h > 0

def test_opencv_detector_explicit_mode():
    """Test explicit OpenCV detector mode with OpenCV 5."""
    detector = TextDetector(backend="opencv")
    assert detector.backend == "opencv"
    
    # Synthetic image with a white bubble
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.circle(img, (100, 100), 40, (255, 255, 255), -1)
    
    bubbles = detector.detect(img)
    assert isinstance(bubbles, list)
    # Should detect the drawn contour bubble
    b = bubbles[0]
    bbox = b.bbox if hasattr(b, 'bbox') else b
    x1, y1, x2, y2 = bbox
    assert x2 > x1 and y2 > y1

def test_yolo_missing_model_raises_loudly(tmp_path):
    """Missing model weights must raise ModelNotFoundError loudly without silent fallback."""
    non_existent = tmp_path / "non_existent_weights.pt"
    
    with pytest.raises(ModelNotFoundError) as exc_info:
        YOLOTextDetector(model_path=str(non_existent), auto_download=False)
    
    assert "not found" in str(exc_info.value).lower()
    
    # Also verify that TextDetector in yolo mode does not silently fall back
    with pytest.raises(ModelNotFoundError):
        TextDetector(backend="yolo", model_path=str(non_existent))

def test_acquire_detector_model_corrupt_or_html(tmp_path):
    """Test model acquisition fails on corrupt or HTML response (e.g. error page)."""
    target = tmp_path / "model.pt"
    
    # Mock requests to return HTML error page
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Length": "100"}
    mock_resp.iter_content.return_value = [b"<!DOCTYPE html><html><body>Error 404</body></html>"]
    
    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ModelAcquisitionError) as exc_info:
            acquire_detector_model(url="http://fake.url/model.pt", target_path=target, min_size=50)
        assert "html" in str(exc_info.value).lower()
        assert not target.exists()

def test_acquire_detector_model_http_error(tmp_path):
    """Test model acquisition fails on HTTP error status."""
    target = tmp_path / "model.pt"
    
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    
    with patch("requests.get", return_value=mock_resp):
        with pytest.raises(ModelAcquisitionError) as exc_info:
            acquire_detector_model(url="http://fake.url/model.pt", target_path=target)
        assert "http 404" in str(exc_info.value).lower()
        assert not target.exists()

def test_acquire_detector_model_successful_mocked(tmp_path):
    """Test successful atomic model acquisition."""
    target = tmp_path / "weights" / "valid_model.pt"
    
    payload = b"PK\x03\x04" + b"x" * 1024  # Mock zip/pt header
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Length": str(len(payload))}
    mock_resp.iter_content.return_value = [payload]
    
    with patch("requests.get", return_value=mock_resp):
        acquired_path = acquire_detector_model(
            url="http://fake.url/model.pt", 
            target_path=target, 
            min_size=100
        )
        assert acquired_path.exists()
        assert acquired_path.read_bytes() == payload
