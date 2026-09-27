"""Unit tests for Round 4: Scoped, revocable model trust records, ONNX trust gating,
tamper resistance, cascade revocation, and pipeline fail-closed semantics.
"""

import json
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from PySide6.QtWidgets import QMessageBox

from src.core.config import Config
from src.core.security import (
    compute_file_sha256,
    load_trust_records,
    save_trust_records,
    record_approved_model,
    revoke_approved_model,
    is_model_trusted,
    is_registered_detector,
    get_model_trust_file,
)
from src.modules.detector import (
    YOLOTextDetector,
    ModelNotFoundError,
    DETECTOR_MODEL_REGISTRY,
    acquire_detector_model,
)
from src.modules.detector_onnx import ONNXTextDetector


@pytest.fixture
def clean_trust_environment(tmp_path, monkeypatch):
    """Ensure tests run against an isolated models directory and trust file."""
    fake_models_dir = tmp_path / "models"
    fake_models_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Config, "MODELS_DIR", fake_models_dir)
    return fake_models_dir


def test_record_and_verify_approved_model_persisted(clean_trust_environment):
    """Approval persists exact file hash, source URL, and size to model_trust.json."""
    model_file = clean_trust_environment / "comic-speech-bubble-detector.pt"
    content = b"valid-simulated-model-weights-bytes-12345"
    model_file.write_bytes(content)
    expected_sha = hashlib.sha256(content).hexdigest().lower()

    # Initially untrusted
    assert not is_model_trusted(model_file, "comic-speech-bubble-detector.pt")

    # Record approval
    recorded_sha = record_approved_model(
        model_name="comic-speech-bubble-detector.pt",
        file_path=model_file,
        source_url="https://huggingface.co/fake/detector.pt"
    )
    assert recorded_sha == expected_sha
    assert is_model_trusted(model_file, "comic-speech-bubble-detector.pt")

    # Verify atomic disk persistence
    trust_file = get_model_trust_file()
    assert trust_file.exists()
    records = json.loads(trust_file.read_text(encoding="utf-8"))
    assert "comic-speech-bubble-detector.pt" in records
    entry = records["comic-speech-bubble-detector.pt"]
    assert entry["sha256"] == expected_sha
    assert entry["source_url"] == "https://huggingface.co/fake/detector.pt"
    assert entry["file_size"] == len(content)
    assert "approved_at" in entry


def test_tampered_or_replaced_model_fails_closed(clean_trust_environment):
    """Modifying or replacing an approved model causes immediate trust failure and fails closed."""
    model_file = clean_trust_environment / "comic-speech-bubble-detector.pt"
    original_bytes = b"legitimate-approved-model-bytes"
    model_file.write_bytes(original_bytes)

    # Approve original file
    record_approved_model("comic-speech-bubble-detector.pt", model_file, "https://source/test.pt")
    assert is_model_trusted(model_file, "comic-speech-bubble-detector.pt")

    # Tamper with the file (e.g. injected payload or corrupted bytes)
    model_file.write_bytes(b"tampered-modified-weights-payload")
    assert not is_model_trusted(model_file, "comic-speech-bubble-detector.pt")

    # Attempting to load via YOLOTextDetector fails closed
    with pytest.raises(ModelNotFoundError) as exc_info:
        YOLOTextDetector(model_path=str(model_file), allow_unverified=False)
    assert "explicit user approval" in str(exc_info.value).lower() or "trust" in str(exc_info.value).lower()


def test_scoped_trust_does_not_approve_other_models(clean_trust_environment):
    """Approval of one model does not grant trust to a different model artifact."""
    model1 = clean_trust_environment / "comic-speech-bubble-detector.pt"
    model1.write_bytes(b"model-1-bytes")
    model2 = clean_trust_environment / "different-detector.pt"
    model2.write_bytes(b"model-2-bytes")

    record_approved_model("comic-speech-bubble-detector.pt", model1, "https://source/m1.pt")

    assert is_model_trusted(model1, "comic-speech-bubble-detector.pt")
    assert not is_model_trusted(model2, "different-detector.pt")


def test_restart_preserves_trust_decision(clean_trust_environment):
    """Trust record remains valid across simulated application restarts."""
    model_file = clean_trust_environment / "comic-speech-bubble-detector.pt"
    model_file.write_bytes(b"restart-persisted-weights")

    record_approved_model("comic-speech-bubble-detector.pt", model_file, "https://source/m.pt")
    assert is_model_trusted(model_file, "comic-speech-bubble-detector.pt")

    # Reload fresh from disk (simulate process restart)
    loaded = load_trust_records()
    assert "comic-speech-bubble-detector.pt" in loaded
    assert is_model_trusted(model_file, "comic-speech-bubble-detector.pt")


def test_onnx_derived_model_provenance_and_validation(clean_trust_environment):
    """ONNX export links cryptographically to parent .pt; invalid parent invalidates ONNX."""
    pt_file = clean_trust_environment / "comic-speech-bubble-detector.pt"
    pt_bytes = b"parent-pytorch-checkpoint-bytes"
    pt_file.write_bytes(pt_bytes)
    parent_sha = record_approved_model("comic-speech-bubble-detector.pt", pt_file, "https://source/pt")

    onnx_file = clean_trust_environment / "comic-speech-bubble-detector.onnx"
    onnx_bytes = b"derived-onnx-exported-graph-bytes"
    onnx_file.write_bytes(onnx_bytes)

    # Record derived ONNX with parent SHA linkage
    record_approved_model(
        "comic-speech-bubble-detector.onnx",
        onnx_file,
        source_url="local_export",
        parent_sha256=parent_sha
    )

    # Both are trusted
    assert is_model_trusted(pt_file, "comic-speech-bubble-detector.pt")
    assert is_model_trusted(onnx_file, "comic-speech-bubble-detector.onnx")

    # If parent file is tampered, ONNX derived check rejects execution
    pt_file.write_bytes(b"corrupted-parent-bytes")
    assert not is_model_trusted(onnx_file, "comic-speech-bubble-detector.onnx")


def test_unapproved_onnx_cannot_bypass_gate_by_expected_name(clean_trust_environment):
    """An unapproved .onnx file matching the registered detector name is strictly rejected."""
    yolo_dir = clean_trust_environment / "yolo"
    yolo_dir.mkdir(parents=True, exist_ok=True)
    unapproved_onnx = yolo_dir / "comic-speech-bubble-detector.onnx"
    unapproved_onnx.write_bytes(b"unauthorized-injected-onnx-weights")

    assert is_registered_detector("comic-speech-bubble-detector.onnx")
    assert not is_model_trusted(unapproved_onnx, "comic-speech-bubble-detector.onnx")

    # Refuses to execute weights without explicit approval
    with pytest.raises(ModelNotFoundError) as exc_info:
        ONNXTextDetector(
            model_path=str(unapproved_onnx),
            allow_unverified=False
        )
    assert "approved cryptographic trust record" in str(exc_info.value)


def test_revocation_cascades_from_parent_to_child(clean_trust_environment):
    """Revoking trust for parent model cascades to revoke derived ONNX model."""
    pt_file = clean_trust_environment / "comic-speech-bubble-detector.pt"
    pt_file.write_bytes(b"parent-weights")
    parent_sha = record_approved_model("comic-speech-bubble-detector.pt", pt_file, "https://source/pt")

    onnx_file = clean_trust_environment / "comic-speech-bubble-detector.onnx"
    onnx_file.write_bytes(b"onnx-weights")
    record_approved_model("comic-speech-bubble-detector.onnx", onnx_file, "local_export", parent_sha256=parent_sha)

    assert is_model_trusted(pt_file, "comic-speech-bubble-detector.pt")
    assert is_model_trusted(onnx_file, "comic-speech-bubble-detector.onnx")

    # Revoke parent
    revoked = revoke_approved_model("comic-speech-bubble-detector.pt")
    assert revoked is True

    # Both parent and derived ONNX are revoked
    records = load_trust_records()
    assert "comic-speech-bubble-detector.pt" not in records
    assert "comic-speech-bubble-detector.onnx" not in records
    assert not is_model_trusted(pt_file, "comic-speech-bubble-detector.pt")
    assert not is_model_trusted(onnx_file, "comic-speech-bubble-detector.onnx")


def test_pipeline_process_all_fails_closed_when_unapproved(clean_trust_environment):
    """Pipeline fails closed with ModelNotFoundError if detector weights are unapproved."""
    from src.core.pipeline import ScanlationPipeline
    from src.core.config import Config

    conf = Config()
    conf.DETECTOR_MODEL = "yolo"
    conf.YOLO_MODEL_PATH = "comic-speech-bubble-detector.pt"

    pipeline = ScanlationPipeline(conf)
    with pytest.raises(ModelNotFoundError):
        _ = pipeline.detector


def test_download_models_dialog_revoke_trust_gui_action(qtbot, clean_trust_environment):
    """DownloadModelsDialog 'Revoke Model Trust' button clears records after confirmation."""
    from src.gui.dialogs.download_models_dialog import DownloadModelsDialog

    model_file = clean_trust_environment / "comic-speech-bubble-detector.pt"
    model_file.write_bytes(b"sample-approved-bytes")
    record_approved_model("comic-speech-bubble-detector.pt", model_file, "https://hf.co/model.pt")
    assert len(load_trust_records()) == 1

    dialog = DownloadModelsDialog()
    qtbot.addWidget(dialog)

    # Click Revoke Trust, confirm Yes
    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes) as mock_q:
        with patch.object(QMessageBox, "information") as mock_info:
            dialog._revoke_trust()
            mock_q.assert_called_once()
            mock_info.assert_called_once()

    assert len(load_trust_records()) == 0
